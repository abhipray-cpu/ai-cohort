"""Start and stop the local TenderLens API and worker as a development stack."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "var" / "tenderlens-dev"
STATE_FILE = STATE_DIR / "processes.json"
COMMANDS = {
    "api": ["-m", "uvicorn", "tenderlens_api.api:app_from_env", "--factory"],
    "worker": ["-m", "tenderlens_api.worker"],
}


def environment() -> dict[str, str]:
    env = os.environ.copy()
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"Invalid .env line: {line}")
            key, value = line.split("=", 1)
            key = key.strip()
            if not key.isidentifier():
                raise ValueError(f"Invalid .env key: {key}")
            env.setdefault(key, value.strip().strip('"').strip("'"))
    return env


def process_matches(pid: int, role: str) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            command = [
                "powershell", "-NoProfile", "-Command",
                f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}').CommandLine",
            ]
        else:
            command = ["ps", "-p", str(pid), "-o", "command="]
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        return result.returncode == 0 and " ".join(COMMANDS[role]) in result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def read_state() -> dict[str, int]:
    if not STATE_FILE.exists():
        return {}
    raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {role: int(raw[role]) for role in COMMANDS if role in raw}


def stop_process(pid: int, role: str) -> None:
    if not process_matches(pid, role):
        print(f"Skipping {role} PID {pid}: process is gone or no longer matches")
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=True)
    else:
        os.killpg(pid, signal.SIGTERM)
    print(f"Stopped {role} PID {pid}")


def down() -> None:
    state = read_state()
    if not state:
        print("TenderLens is not running under this launcher")
        return
    for role in ("worker", "api"):
        if role in state:
            stop_process(state[role], role)
    STATE_FILE.unlink(missing_ok=True)


def healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health/ready", timeout=1) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def up() -> None:
    existing = read_state()
    if any(process_matches(pid, role) for role, pid in existing.items()):
        raise RuntimeError("TenderLens is already running; use make down first")
    env = environment()
    if not env.get("TENDERLENS_USERNAME") or env.get("TENDERLENS_PASSWORD") in (
        None, "", "replace-me"
    ):
        raise RuntimeError("Set TENDERLENS_USERNAME and a real TENDERLENS_PASSWORD in .env")
    if not (ROOT / "apps/tenderlens-web/dist/index.html").exists():
        raise RuntimeError("Web build missing; run npm --prefix apps/tenderlens-web run build")
    host = env.get("TENDERLENS_HOST", "127.0.0.1")
    port = int(env.get("TENDERLENS_PORT", "8000"))
    if host != "127.0.0.1":
        raise RuntimeError("Development launcher only binds to 127.0.0.1")
    if healthy(port):
        raise RuntimeError(f"Port {port} already serves a healthy API; refusing to overlap")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    started: dict[str, int] = {}
    processes: dict[str, subprocess.Popen[bytes]] = {}
    try:
        for role in ("api", "worker"):
            log = STATE_DIR / f"{role}.log"
            command = [sys.executable, *COMMANDS[role]]
            if role == "api":
                command += ["--host", host, "--port", str(port)]
            with log.open("ab") as output:
                flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
                process = subprocess.Popen(
                    command,
                    cwd=ROOT,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    start_new_session=os.name != "nt",
                    creationflags=flags,
                )
            started[role] = process.pid
            processes[role] = process
            STATE_FILE.write_text(json.dumps(started), encoding="utf-8")
        for _ in range(50):
            if healthy(port):
                print(f"TenderLens is ready at http://127.0.0.1:{port}/")
                print(f"Logs: {STATE_DIR}")
                return
            if any(process.poll() is not None for process in processes.values()):
                break
            time.sleep(0.2)
        raise RuntimeError(f"Startup failed; inspect logs in {STATE_DIR}")
    except Exception:
        for process in reversed(list(processes.values())):
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False
                    )
                else:
                    os.killpg(process.pid, signal.SIGTERM)
        STATE_FILE.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("up", "down", "status"))
    action = parser.parse_args().action
    if action == "up":
        up()
    elif action == "down":
        down()
    else:
        state = read_state()
        for role in COMMANDS:
            pid = state.get(role)
            print(f"{role}: {'running' if pid and process_matches(pid, role) else 'stopped'}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from error
