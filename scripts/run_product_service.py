"""Foreground service entrypoint with bounded rotating logs and .env loading."""

import argparse
import logging
import os
import signal
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dev_stack import environment

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("api", "worker"))
    args = parser.parse_args()
    env = environment()
    required = ("RESOLVEDESK_USERNAME", "RESOLVEDESK_PASSWORD")
    if any(not env.get(key) or env[key] == "replace-me" for key in required):
        raise SystemExit(
            "Set explicit ResolveDesk service credentials in the service environment or .env"
        )
    directory = ROOT / "var/resolvedesk-service"
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("resolvedesk-service")
    logger.setLevel(logging.INFO)
    logger.addHandler(
        RotatingFileHandler(directory / f"{args.role}.log", maxBytes=5_000_000, backupCount=3)
    )
    command = [sys.executable, "-m"]
    if args.role == "api":
        command += [
            "uvicorn",
            "resolvedesk_api.api:app_from_env",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            env.get("RESOLVEDESK_PORT", "8001"),
        ]
    else:
        command += ["resolvedesk_api.worker"]
    process = subprocess.Popen(
        command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    def stop(signum, frame):
        if process.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False)
            else:
                process.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        for line in process.stdout:
            logger.info(line.rstrip())
        raise SystemExit(process.wait())
    finally:
        stop(None, None)


if __name__ == "__main__":
    main()
