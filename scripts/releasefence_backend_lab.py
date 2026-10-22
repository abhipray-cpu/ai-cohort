"""Owned, loopback-only real backend processes for explicit acceptance campaigns.

MLflow is upstream 3.17.2 with authentication and deny-by-default permissions.
Phoenix is upstream 20.23.0. This is not a production deployment installer.
"""

import os
import secrets
import socket
import subprocess
import time
from pathlib import Path

import httpx


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def eventually(fn, seconds=60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            value = fn()
            if value:
                return value
        except (httpx.HTTPError, OSError):
            pass
        time.sleep(0.2)
    raise RuntimeError("owned backend readiness timed out; inspect private lab logs")


class BackendLab:
    def __init__(self, root, mlflow_python, phoenix_python):
        self.root = Path(root).resolve()
        self.python = {
            "mlflow": str(Path(mlflow_python).resolve()),
            "phoenix": str(Path(phoenix_python).absolute()),
        }
        # Do not resolve a virtualenv Python symlink to the global interpreter.
        self.python["mlflow"] = str(Path(mlflow_python).absolute())
        self.urls = {kind: f"http://127.0.0.1:{port()}" for kind in self.python}
        self.password = secrets.token_urlsafe(30)
        self.env = {}
        self.processes = {}
        self.logs = []

    def __enter__(self):
        self.root.mkdir(parents=True, exist_ok=False)
        os.chmod(self.root, 0o700)
        base = {
            k: v
            for k, v in os.environ.items()
            if k in {"PATH", "HOME", "TMPDIR", "SYSTEMROOT", "WINDIR"}
        }
        config = self.root / "auth.ini"
        config.write_text(
            "[mlflow]\ndefault_permission = NO_PERMISSIONS\n"
            f"database_uri = sqlite:///{self.root / 'auth.db'}\n"
            "admin_username = rf-admin\ngrant_default_workspace_access = false\n"
        )
        os.chmod(config, 0o600)
        self.env["mlflow"] = {
            **base,
            "MLFLOW_AUTH_CONFIG_PATH": str(config),
            "MLFLOW_AUTH_ADMIN_PASSWORD": self.password,
            "MLFLOW_FLASK_SERVER_SECRET_KEY": secrets.token_urlsafe(32),
            "MLFLOW_DISABLE_TELEMETRY": "true",
            "MPLCONFIGDIR": str(self.root / "mpl"),
        }
        self.env["phoenix"] = {
            **base,
            "PHOENIX_HOST": "127.0.0.1",
            "PHOENIX_PORT": self.urls["phoenix"].rsplit(":", 1)[1],
            "PHOENIX_GRPC_PORT": str(port()),
            "PHOENIX_WORKING_DIR": str(self.root / "phoenix"),
            "PHOENIX_TELEMETRY_ENABLED": "false",
            "PHOENIX_DISABLE_AGENT_ASSISTANT": "true",
            "PHOENIX_ENABLE_MCP_SERVER": "false",
            "PHOENIX_ALLOW_EXTERNAL_RESOURCES": "false",
        }
        try:
            for kind, expected in [("mlflow", "3.17.2"), ("phoenix", "20.23.0")]:
                package = "mlflow" if kind == "mlflow" else "arize-phoenix"
                actual = subprocess.check_output(
                    [
                        self.python[kind],
                        "-c",
                        f"from importlib.metadata import version;print(version('{package}'))",
                    ],
                    text=True,
                ).strip()
                if actual != expected:
                    raise ValueError("backend version differs from the pinned qualification target")
                self.start(kind)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def start(self, kind):
        log = (self.root / f"{kind}-{len(self.logs)}.log").open("wb")
        self.logs.append(log)
        if kind == "mlflow":
            args = [
                self.python[kind],
                "-m",
                "mlflow",
                "server",
                "--host",
                "127.0.0.1",
                "--port",
                self.urls[kind].rsplit(":", 1)[1],
                "--workers",
                "1",
                "--backend-store-uri",
                f"sqlite:///{self.root / 'traces.db'}",
                "--artifacts-destination",
                str(self.root / "artifacts"),
                "--app-name",
                "basic-auth",
            ]
        else:
            args = [self.python[kind], "-m", "phoenix.server.main", "serve"]
        self.processes[kind] = subprocess.Popen(
            args, env=self.env[kind], cwd=self.root, stdout=log, stderr=log
        )
        path = "/health" if kind == "mlflow" else "/healthz"
        eventually(lambda: httpx.get(self.urls[kind] + path, timeout=3).status_code == 200)

    def stop(self, kind):
        process = self.processes.get(kind)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def provision(self, name):
        """A distinct experiment and non-admin identity for each ReleaseFence tenant."""
        username, password = "rf-" + secrets.token_hex(8), secrets.token_urlsafe(30)
        with httpx.Client(
            base_url=self.urls["mlflow"], auth=("rf-admin", self.password), timeout=15
        ) as client:

            def post(path, body):
                response = client.post(path, json=body)
                response.raise_for_status()
                return response.json()

            project = post("/api/2.0/mlflow/experiments/create", {"name": name})["experiment_id"]
            post("/api/2.0/mlflow/users/create", {"username": username, "password": password})
            role = post("/api/3.0/mlflow/roles/create", {"workspace": "default", "name": username})[
                "role"
            ]["id"]
            for resource_type, pattern, permission in [
                ("workspace", "*", "USE"),
                ("experiment", project, "EDIT"),
            ]:
                post(
                    "/api/3.0/mlflow/roles/permissions/add",
                    {
                        "role_id": role,
                        "resource_type": resource_type,
                        "resource_pattern": pattern,
                        "permission": permission,
                    },
                )
            post("/api/3.0/mlflow/roles/assign", {"username": username, "role_id": role})
        return {"project": project, "secret": username + ":" + password}

    def __exit__(self, *unused):
        for kind in self.processes:
            self.stop(kind)
        for log in self.logs:
            log.close()
