"""Durable observer worker; no inference or new rollout on startup."""

import os
import signal
import threading

from .config import load_store
from .engine import Engine


def main():
    stopped = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    store = load_store()
    engine = Engine(store, lab_loopback=os.environ.get("RELEASEFENCE_LAB_LOOPBACK") == "1")
    while not stopped.is_set():
        cycle(store, engine, stopped)
        stopped.wait(1)


def cycle(store, engine, stopped):
    healthy = True
    with store.db() as db:
        tenants = [
            r["id"] for r in db.execute("SELECT id::text FROM organizations ORDER BY id LIMIT 1001")
        ]
    if len(tenants) > 1000:
        return False  # Never silently ignore overflow tenants.
    for tenant in tenants:
        if stopped.is_set():
            return False
        state = "healthy"
        category = None
        try:
            engine.scan(tenant)
            with store.db(tenant) as db:
                backends = store._rows(db, "backend")
            for backend in backends:
                if stopped.is_set():
                    return False
                store.export_backend(tenant, backend["id"])
            for _ in range(10):
                if stopped.is_set() or not engine.deliver(tenant):
                    break
        except Exception:  # noqa: BLE001 - outer worker boundary records safe status only
            healthy = False
            state = "error"
            category = "worker_iteration_failed"
        with store.db(tenant) as db:
            body = {"state": state, "category": category, "at": store.now()}
            if db.execute("SELECT 1 FROM records WHERE kind='health' AND id='worker'").fetchone():
                old = store._get(db, "health", "worker")
                old.update(body)
                store._save(db, "health", old)
            else:
                store._insert(db, "health", "worker", body)
    if healthy and not stopped.is_set():
        with store.db() as db:
            db.execute(
                "INSERT INTO worker_status VALUES('engine',%s) ON CONFLICT(id) DO UPDATE SET heartbeat=excluded.heartbeat",
                (store.now(),),
            )
    return healthy


if __name__ == "__main__":
    main()
