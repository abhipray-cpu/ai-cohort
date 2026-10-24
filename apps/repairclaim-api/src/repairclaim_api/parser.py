"""OS/container-restricted PDF/image runner. No unsafe production fallback."""

import base64
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from repairclaim_api.errors import DomainError


@contextmanager
def parser_slot():
    """Cross-process admission: worker and web previews cannot exhaust the host."""
    root = Path(os.environ.get("REPAIRCLAIM_DATA_DIR", tempfile.gettempdir()))
    lock = root / "repairclaim-parser.lock"
    if lock.is_symlink():
        raise DomainError("parser_lock_invalid", 503)
    descriptor = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, "r+b") as stream:
        try:
            if os.name == "nt":
                import msvcrt

                if stream.seek(0, 2) == 0:
                    stream.write(b"0")
                    stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise DomainError("parser_busy_retry", 503) from error
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


class RestrictedParser:
    def __init__(self, *, mode="auto", engine="docker", image="repairclaim-parser:0.1"):
        self.mode = (
            "macos"
            if mode == "auto" and platform.system() == "Darwin"
            else ("container" if mode == "auto" else mode)
        )
        self.engine, self.image = engine, image

    def command(self, temporary):
        if self.mode == "container" and shutil.which(self.engine):
            if self.engine not in {"docker", "podman"}:
                raise DomainError("container_engine_denied", 503)
            # Never inherit a remote context and silently disclose documents.
            endpoint = (
                "npipe:////./pipe/docker_engine"
                if os.name == "nt"
                else "unix:///var/run/docker.sock"
            )
            prefix = (
                [self.engine, "--host", endpoint]
                if self.engine == "docker"
                else [self.engine, "--remote=false"]
            )
            return [
                *prefix,
                "run",
                "--rm",
                "--pull=never",
                "--log-driver=none",
                "-i",
                "--network=none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--pids-limit=32",
                "--memory=512m",
                "--cpus=1",
                "--user=65534:65534",
                "--tmpfs=/tmp:rw,noexec,nosuid,size=64m",
                self.image,
            ]
        if self.mode == "macos" and shutil.which("sandbox-exec"):
            script = Path(__file__).with_name("parser_child.py").resolve()
            reads = {
                "/System",
                "/usr",
                "/opt/homebrew",
                "/Library/Apple",
                "/dev",
                "/private/etc",
                str(Path(sys.prefix).resolve()),
                str(Path(sys.base_prefix).resolve()),
                str(script.parents[1]),
                str(Path(temporary).resolve()),
            }
            clauses = " ".join(f"(subpath {json.dumps(path)})" for path in reads)
            profile = (
                f"(version 1)(deny default)(allow process*)(allow sysctl-read)(allow mach-lookup)(allow file-read-metadata)"
                f'(allow file-read* (literal "/") {clauses})(allow file-write* (subpath {json.dumps(str(Path(temporary).resolve()))}))'
                "(deny network*)"
            )
            return ["sandbox-exec", "-p", profile, sys.executable, "-I", str(script)]
        raise DomainError("restricted_parser_unavailable", 503)

    def run(self, operation, data, filename, **options):
        with parser_slot():
            return self._run(operation, data, filename, **options)

    def _run(self, operation, data, filename, **options):
        if operation not in {"parse", "sanitize", "preview"} or len(data) > 20 * 1024 * 1024:
            raise DomainError("parser_input_limit", 413)
        request = json.dumps(
            {
                "operation": operation,
                "data": base64.b64encode(data).decode("ascii"),
                "filename": filename,
                **options,
            }
        ).encode("utf-8")
        with tempfile.TemporaryDirectory(prefix="rc-parse-") as temporary:
            command = self.command(temporary)
            environment = {
                key: value
                for key, value in os.environ.items()
                if key in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC"}
            }
            with (
                tempfile.TemporaryFile(dir=temporary) as output,
                tempfile.TemporaryFile(dir=temporary) as errors,
            ):
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=output,
                    stderr=errors,
                    cwd=temporary,
                    env=environment,
                    start_new_session=os.name != "nt",
                )
                try:
                    process.communicate(request, timeout=60)
                except BaseException:  # noqa: BLE001 — always stop this owned child, including cancellation
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            capture_output=True,
                            timeout=5,
                            check=False,
                        )
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                    raise DomainError("parser_timeout", 503) from None
                if process.returncode or output.tell() > 32 * 1024 * 1024:
                    raise DomainError("restricted_parser_failed", 503)
                output.seek(0)
                try:
                    result = json.load(output)
                    if "error" in result:
                        code = result["error"]
                        if (
                            not isinstance(code, str)
                            or not code.replace("_", "").isalnum()
                            or len(code) > 80
                        ):
                            code = "parser_failed"
                        raise DomainError(code, 422)
                    value = result["ok"]
                    return (
                        base64.b64decode(value["bytes"], validate=True)
                        if "bytes" in value
                        else value
                    )
                except (ValueError, KeyError, TypeError) as error:
                    raise DomainError("parser_protocol_failed", 503) from error
