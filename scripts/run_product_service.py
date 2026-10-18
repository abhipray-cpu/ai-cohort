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
    parser.add_argument(
        "--product",
        choices=(
            "resolvedesk",
            "propertybrief",
            "patchdesk",
            "relaydesk",
            "clausegate",
            "catalogbridge",
        ),
        default="resolvedesk",
    )
    args = parser.parse_args()
    env = environment()
    prefix = args.product.upper()
    required = (f"{prefix}_USERNAME", f"{prefix}_PASSWORD")
    if any(not env.get(key) or env[key] == "replace-me" for key in required):
        raise SystemExit(
            f"Set explicit {args.product} service credentials in the service environment or .env"
        )
    directory = ROOT / f"var/{args.product}-service"
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"{args.product}-service")
    logger.setLevel(logging.INFO)
    logger.addHandler(
        RotatingFileHandler(directory / f"{args.role}.log", maxBytes=5_000_000, backupCount=3)
    )
    command = [sys.executable, "-m"]
    if args.role == "api":
        command += [
            "uvicorn",
            f"{args.product}_api.api:app_from_env",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            env.get(
                f"{prefix}_PORT",
                {
                    "propertybrief": "8002",
                    "patchdesk": "8003",
                    "resolvedesk": "8001",
                    "relaydesk": "8004",
                    "clausegate": "8005",
                    "catalogbridge": "8006",
                }[args.product],
            ),
        ]
    else:
        command += [f"{args.product}_api.worker"]
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
