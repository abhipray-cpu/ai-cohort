"""Owned RepairClaim development lifecycle; never borrows other product settings."""

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import dev_stack

ROOT = Path(__file__).resolve().parents[1]


def configure():
    dev_stack.PRODUCT = "RepairClaim"
    dev_stack.PREFIX = "REPAIRCLAIM"
    dev_stack.STATE_DIR = ROOT / "var" / "repairclaim-dev"
    dev_stack.STATE_FILE = dev_stack.STATE_DIR / "processes.json"
    dev_stack.COMMANDS = {
        "api": ["-m", "uvicorn", "repairclaim_api.api:app_from_env", "--factory"],
        "worker": ["-m", "repairclaim_api.worker"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["up", "down", "status"])
    args = parser.parse_args()
    configure()
    if args.action == "down":
        dev_stack.down()
        return
    state = dev_stack.read_state()
    if args.action == "status":
        for role in dev_stack.COMMANDS:
            print(
                f"{role}: {'running' if state.get(role) and dev_stack.process_matches(state[role], role) else 'stopped'}"
            )
        return
    if any(dev_stack.process_matches(pid, role) for role, pid in state.items()):
        raise RuntimeError("RepairClaim is already managed; stop it first")
    env = os.environ.copy()
    root = Path(env.get("REPAIRCLAIM_DATA_DIR", ROOT / "var" / "repairclaim")).resolve()
    if not (root / "repairclaim.sqlite3").is_file():
        raise RuntimeError(
            "Provision an account first: python -m repairclaim_api.cli --data-dir <dedicated directory> provision <username>"
        )
    port = int(env.get("REPAIRCLAIM_PORT", "8011"))
    env["REPAIRCLAIM_DATA_DIR"] = str(root)
    env.setdefault("REPAIRCLAIM_PUBLIC_ORIGIN", f"http://127.0.0.1:{port}")
    if not (ROOT / "apps" / "repairclaim-web" / "dist" / "index.html").is_file():
        raise RuntimeError("Build RepairClaim web first")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    env["PYTHONPATH"] = (
        str(ROOT / "apps" / "repairclaim-api" / "src") + os.pathsep + env.get("PYTHONPATH", "")
    )
    dev_stack.STATE_DIR.mkdir(parents=True, exist_ok=True)
    started = {}
    try:
        for role, arguments in dev_stack.COMMANDS.items():
            command = [sys.executable, *arguments]
            if role == "api":
                command += ["--host", "127.0.0.1", "--port", str(port), "--no-access-log"]
            with (dev_stack.STATE_DIR / f"{role}.log").open("ab") as log:
                process = subprocess.Popen(
                    command,
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=log,
                    start_new_session=os.name != "nt",
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                )
            started[role] = process.pid
        import json

        dev_stack.STATE_FILE.write_text(json.dumps(started))
        for _ in range(60):
            if dev_stack.healthy(port):
                print(
                    f"RepairClaim ready at {env['REPAIRCLAIM_PUBLIC_ORIGIN']}. No model or source calls are enabled by default."
                )
                return
            time.sleep(0.5)
        raise RuntimeError("RepairClaim did not become ready; inspect its dedicated logs")
    except BaseException:
        for role, pid in started.items():
            dev_stack.stop_process(pid, role)
        dev_stack.STATE_FILE.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError) as error:
        raise SystemExit(str(error)) from error
