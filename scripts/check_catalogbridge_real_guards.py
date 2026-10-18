"""Real-input budget refusal and real-paid-state backup guards; no new model calls."""

import argparse
import json
import secrets
from pathlib import Path

from catalogbridge_api.api import create_app
from catalogbridge_api.backup import backup, restore
from catalogbridge_api.store import Store
from catalogbridge_api.worker import run_once
from fastapi.testclient import TestClient


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cohort", type=Path, required=True)
    p.add_argument("--paid-http", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("preserve earlier evidence")
    args.output.mkdir(parents=True)
    password = secrets.token_urlsafe(24)
    app = create_app(args.output / "budget-product", username="guard-owner", password=password)
    client = TestClient(app)
    r = client.post("/api/session", json={"username": "guard-owner", "password": password})
    r.raise_for_status()
    client.headers["X-CSRF-Token"] = r.json()["csrf"]
    gallery = json.loads((args.cohort / "gallery.json").read_text())
    queries = json.loads((args.cohort / "queries.json").read_text())
    ids = []
    for kind, rows in [("master", gallery), ("supplier", queries[:1])]:
        r = client.post(
            "/api/feeds", params={"kind": kind, "format": "json"}, content=json.dumps(rows)
        )
        r.raise_for_status()
        ids.append(r.json()["id"])
    strict = client.post(
        "/api/batches", json={"master_id": ids[0], "supplier_id": ids[1], "budget_mode": "strict"}
    )
    assert strict.status_code == 409 and "hard token" in strict.json()["detail"]
    r = client.post(
        "/api/batches",
        json={
            "master_id": ids[0],
            "supplier_id": ids[1],
            "token_budget": 1,
            "row_token_budget": 1,
            "egress": True,
        },
    )
    r.raise_for_status()
    bid = r.json()["id"]
    client.post(f"/api/batches/{bid}/start").raise_for_status()

    class NeverCall:
        called = False

        def generate_pair(self, *args, **kwargs):
            self.called = True
            raise AssertionError("budget refused input must not reach model")

    spy = NeverCall()
    run_once(app.state.store, spy)
    task = client.get(f"/api/batches/{bid}/tasks").json()[0]
    metrics = client.get(f"/api/batches/{bid}/analytics").json()
    assert not spy.called and metrics["attempts"] == 0 and task["state"] == "failed"
    assert task["result"]["reason"] == "budget exhausted"
    source = Store(args.paid_http / "product", args.paid_http / "usage-journal")
    live = json.loads((args.paid_http / "live-results.json").read_text())
    expected = sum(r["metrics"]["tokens"] for r in live)
    backup(source, args.output / "paid-snapshot")
    restored = restore(
        args.output / "paid-snapshot",
        args.output / "paid-restored",
        args.paid_http / "usage-journal",
    )
    recovered = Store(restored, args.paid_http / "usage-journal")
    actual = sum(recovered.analytics("default", r["batch_id"])["tokens"] for r in live)
    assert actual == expected and expected > 0
    blocked = 0
    for row in live:
        task = recovered.tasks("default", row["batch_id"])[0]
        try:
            recovered.reserve(row["batch_id"], task["id"], "economy", 100)
        except ValueError as exc:
            assert "quarantine" in str(exc)
            blocked += 1
    assert blocked == len(live)
    report = {
        "real_input_budget_refused_before_dispatch": True,
        "attempts_after_refusal": metrics["attempts"],
        "strict_hard_token_mode_refused": True,
        "guard_surface": "API TestClient plus actual store/worker; not a browser or separate network-server journey",
        "real_paid_state_restore_preserved_tokens": actual,
        "paid_batches_checked": len(live),
        "quarantined_dispatch_refusals": blocked,
        "new_model_calls": 0,
        "scope": "Source records are real; forced tiny budget is an explicit operational fault fixture",
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
