"""Outbound-only customer connector process. No arbitrary command execution."""

import json
import os
import signal
import threading
from pathlib import Path

from .connector import Connector, Router
from .crypto import private_key
from .network import request, resolve_destination
from .sdk import Spool


class Response:
    def __init__(self, status, body):
        self.status = status
        self.body = body

    def raise_for_status(self):
        if not 200 <= self.status < 300:
            raise OSError("control plane request unavailable")

    def json(self):
        self.raise_for_status()
        return json.loads(self.body)


class Client:
    def __init__(self, url, token, *, lab_loopback=False):
        resolve_destination(url, lab_loopback=lab_loopback)
        self.url = url.rstrip("/")
        self.token = token
        self.lab = lab_loopback

    def post(self, path, json=None):
        if not path.startswith(("/connector/v1/", "/ingest/v1/")):
            raise ValueError("unsupported connector path")
        status, body = request(
            self.url + path,
            body=__import__("json").dumps(json or {}, separators=(",", ":")).encode(),
            headers={"Authorization": "Bearer " + self.token},
            lab_loopback=self.lab,
        )
        return Response(status, body)

    def send(self, path, body):
        return self.post(path, json=body).json()


def main():
    # Explicit customer configuration file; startup only resumes enrolled work.
    config = json.loads(Path(os.environ["RELEASEFENCE_CONNECTOR_CONFIG"]).read_text())
    key = private_key(os.environ["RELEASEFENCE_RUNTIME_SIGNING_KEY"])
    root = Path(config["data_dir"])
    root.mkdir(parents=True, exist_ok=True)
    from .gateway import HTTPBundles

    for item in config["bundle_endpoints"].values():
        item["token"] = os.environ[item["token_env"]]
    bundles = HTTPBundles(
        config["bundle_endpoints"], lab_loopback=config.get("lab_loopback", False)
    )
    router = Router(
        root / "router.db",
        config["enrollment"],
        config["application"],
        config["environment"],
        config["server_public_key"],
        key,
        set(bundles.values),
        config["stable"],
        probe=bundles.probe,
    )
    client = Client(
        config["control_url"],
        os.environ["RELEASEFENCE_CONNECTOR_TOKEN"],
        lab_loopback=config.get("lab_loopback", False),
    )
    spool = Spool(root / "events.db")
    connector = Connector(router, client, config["enrollment"])
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    while not stopped.is_set():
        try:
            connector.tick()
            spool.flush(client.send)
            spool.prune_delivered()
        except (OSError, ValueError):
            # No URLs, tokens, event bodies or response text enter logs.
            print("releasefence_connector_iteration_unavailable", flush=True)
        stopped.wait(2)


if __name__ == "__main__":
    main()
