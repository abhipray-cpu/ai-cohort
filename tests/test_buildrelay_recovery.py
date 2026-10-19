# ruff: noqa: F811
# Imported pytest fixture intentionally matches function parameter names.
from buildrelay_api.reconcile import reconcile
from buildrelay_api.worker import provider_from_env
from test_buildrelay_core import store  # noqa: F401
from test_buildrelay_transports import payload


def test_reconciliation_uses_same_inbox_identity_and_records_coverage(store):
    class Source:
        def recent_runs(self, repo, page=1):
            return {"workflow_runs": [payload()["workflow_run"]], "total_count": 1}

    reconcile(store, Source(), store.repo("repo"))
    reconcile(store, Source(), store.repo("repo"), force=True)
    assert len(store.events()) == 1
    assert any(a["action"] == "reconciliation_completed" for a in store.audit())


def test_reconciliation_page_cap_is_visible_not_claimed_complete(store):
    class Source:
        def recent_runs(self, repo, page=1):
            return {"workflow_runs": [payload()["workflow_run"]] * 100, "total_count": 10000}

    reconcile(store, Source(), store.repo("repo"), page_limit=2)
    assert any(a["action"] == "reconciliation_coverage_gap" for a in store.audit())


def test_repeated_worker_crashes_end_in_dead_letter(store):
    from test_buildrelay_core import event

    store.accept("repo", event(), "queue", "a")
    for n in range(4):
        assert store.claim(now=100 + n * 11, lease=10)
    assert store.claim(now=145, lease=10) is None
    assert store.events()[0]["state"] == "dead"
    assert store.events()[0]["error"] == "lease_exhausted"


def test_provider_receives_no_product_credentials(monkeypatch):
    monkeypatch.setenv("BUILDRELAY_SHOP_TOKEN", "must-not-leak")
    p = provider_from_env()
    assert "BUILDRELAY_SHOP_TOKEN" not in p.environment
    assert p.isolated
    assert 'web_search="disabled"' in p.config_overrides
