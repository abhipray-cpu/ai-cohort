"""Single installed-Codex worker; no model request on boot or health checks."""

import os
import signal
import threading

from .runtime import CodexProvider
from .store import Store
from .workflow import Worker


def main():
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    store = Store(os.environ.get("SHELFPROOF_DATA_DIR", "var/shelfproof"))
    worker = Worker(
        store,
        CodexProvider(command=os.environ.get("SHELFPROOF_CODEX_COMMAND", "codex")),
        stop_check=stopped.is_set,
    )

    def heartbeat():
        while not stopped.wait(10):
            store.heartbeat()

    threading.Thread(target=heartbeat, daemon=True).start()
    while not stopped.is_set():
        store.heartbeat()
        if not worker.run_once():
            stopped.wait(1)


if __name__ == "__main__":
    main()
