import threading

from releasefence_api.worker import cycle
from test_releasefence_store import rf, rf_admin  # noqa: F401


def test_failed_worker_cycle_does_not_publish_successful_observer_readiness(rf):
    s, t, _ = rf

    class Engine:
        def scan(self, tenant):
            raise ValueError("PRIVATE")

    assert not cycle(s, Engine(), threading.Event())
    with s.db() as db:
        assert db.execute("SELECT count(*) n FROM worker_status").fetchone()["n"] == 0
    assert s.list("owner", t, "health")[0]["state"] == "error"

    class Healthy:
        def scan(self, tenant):
            pass

        def deliver(self, tenant):
            return False

    assert cycle(s, Healthy(), threading.Event())
    with s.db() as db:
        assert db.execute("SELECT heartbeat FROM worker_status").fetchone()["heartbeat"] == 1000
    assert s.list("owner", t, "health")[0]["state"] == "healthy"
