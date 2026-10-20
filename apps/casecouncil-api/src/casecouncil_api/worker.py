"""Single active local debate worker; no automatic source acquisition or egress grants."""

import os
import signal
import sqlite3
import threading

from .controller import Controller
from .runtime import provider_from_env
from .store import Store


def main():
    store = Store(os.environ.get("CASECOUNCIL_DATA_DIR", "var/casecouncil"))
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    provider = provider_from_env()

    def cancelled():
        if stop.is_set():
            return True
        with store.connect() as db:
            return not db.execute(
                "SELECT 1 FROM jobs WHERE state='running' AND lease_until>strftime('%s','now')"
            ).fetchone()

    provider.cancel_check = cancelled
    controller = Controller(store, provider)
    while not stop.is_set():
        try:
            if not controller.once():
                stop.wait(1)
        except (sqlite3.Error, OSError, ValueError):
            # No raw exception text: filenames, credentials and source bodies may
            # be carried by dependencies. Work stays fenced/reclaimable.
            stop.wait(2)


if __name__ == "__main__":
    main()
