"""Exercise the shipped owned-process launcher in an isolated temporary root."""

import base64
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from test_releasefence_store import rf, rf_admin  # noqa: F401


def test_owned_launcher_up_status_duplicate_start_and_down(rf, tmp_path):
    s, _, _ = rf
    s.now = time.time
    root = Path(__file__).resolve().parents[1]
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    launcher = scripts / "dev_stack.py"
    shutil.copyfile(root / "scripts/dev_stack.py", launcher)
    web = tmp_path / "apps/releasefence-web"
    web.mkdir(parents=True)
    shutil.copytree(root / "apps/releasefence-web/dist", web / "dist")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {
        **os.environ,
        "RELEASEFENCE_USERNAME": "owner",
        "RELEASEFENCE_PASSWORD": "owned-password-123",
        "RELEASEFENCE_DATABASE_URL": s.dsn,
        "RELEASEFENCE_SCHEMA": s.schema,
        "RELEASEFENCE_ENCRYPTION_KEY": s.test_encryption_key.decode(),
        "RELEASEFENCE_SIGNING_KEY": base64.b64encode(s.key.private_bytes_raw()).decode(),
        "RELEASEFENCE_PORT": str(port),
        "RELEASEFENCE_ORIGIN": f"http://127.0.0.1:{port}",
    }

    def run(action):
        return subprocess.run(
            [sys.executable, str(launcher), "--product", "releasefence", action],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    try:
        started = run("up")
        assert started.returncode == 0, started.stdout + started.stderr
        assert f"http://127.0.0.1:{port}" in started.stdout
        status = run("status")
        assert status.returncode == 0 and "running" in status.stdout.lower()
        assert run("up").returncode != 0  # Do not replace managed processes.
        stopped = run("down")
        assert stopped.returncode == 0 and "does not stop customer agents" in stopped.stdout
        assert not (tmp_path / "var/releasefence-dev/processes.json").exists()
    finally:
        run("down")
