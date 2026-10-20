"""Local real-corpus API/protocol checks with an explicit authored provider stand-in.

NO installed Codex call, model egress, semantic scoring or independent human review.
"""

import argparse
import json
import sys
from pathlib import Path

from casecouncil_api.api import create_app
from casecouncil_api.controller import Controller
from casecouncil_api.evaluation import audit_corpus, load_manifest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_casecouncil_api import login, post
from test_casecouncil_protocol import ControlledProvider
from test_casecouncil_store import PASSWORD


def check(corpus, output):
    inventory = audit_corpus(corpus)
    if inventory["near_duplicate_warnings"]:
        raise ValueError("split warnings require review")
    root, manifest = load_manifest(corpus)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    app = create_app(output / "service", username="owner", password=PASSWORD, evaluation_only=True)
    client = TestClient(app)
    login(client)
    w = post(
        client, "/api/workspaces", json={"name": "Offline actual-corpus engineering checks"}
    ).json()["id"]
    assert (
        client.put(
            f"/api/workspaces/{w}/policy",
            json={
                "revision": 1,
                "policy": {
                    "name": "Offline replay scope",
                    "instructions": "Irish party-summary research only; no UK inference or automated final response.",
                    "required_documents": ["complaint"],
                    "egress_enabled": True,
                },
            },
        ).status_code
        == 200
    )
    # Exercise the grant mechanics against a local stand-in only. This is NOT
    # external-model permission and never changes the source manifest.
    local_only = {
        **manifest["permission"],
        "egress": True,
        "reference": "LOCAL-ONLY CONTROLLED PROVIDER EXERCISE; no external-model authority. Source reuse: https://fspo.ie/governance/reuse.asp",
    }
    right = post(client, f"/api/workspaces/{w}/rights", json=local_only).json()["id"]
    results = []
    for record in manifest["cases"]:
        result = {"id": record["id"], "split": record["split"]}
        try:
            response = post(
                client, "/api/cases", json={"workspace": w, "context": record["context"]}
            )
            assert response.status_code == 201
            c = response.json()["id"]
            for n, doc in enumerate(record["documents"]):
                path = root / doc["path"]
                response = post(
                    client,
                    f"/api/cases/{c}/sources",
                    data={"revision": n + 1, "kind": doc["kind"], "rights_id": right},
                    files={"file": (path.name, path.read_bytes(), "text/plain")},
                )
                assert response.status_code == 201
            preview = client.get(f"/api/cases/{c}/egress-preview").json()
            assert preview["context"]["jurisdiction"] == "IE" and preview["blockers"]
            key = "start_" + record["id"]
            response = client.post(
                f"/api/cases/{c}/runs",
                json={"binding": preview["binding"]},
                headers={"Idempotency-Key": key},
            )
            assert response.status_code == 202
            job = response.json()["id"]
            repeat = client.post(
                f"/api/cases/{c}/runs",
                json={"binding": preview["binding"]},
                headers={"Idempotency-Key": key},
            )
            assert repeat.status_code == 202 and repeat.json()["id"] == job
            provider = ControlledProvider()  # Authored stand-in; never real inference.
            assert Controller(app.state.store, provider).once()
            run = client.get(f"/api/runs/{job}").json()
            packet = run["packet"]
            assert run["state"] == "draft_ready" and not packet["unavailable"]
            assert len(packet["proposals"]) == len(packet["ballots"]) == 3
            assert packet["critique"] is not None and packet["synthesis"] is not None
            assert packet["consensus"]["confidence_band"] == "low"
            assert all(
                not i["qualified"] and i["denominator"] == 3 for i in packet["consensus"]["issues"]
            )
            assert not client.get(f"/api/runs/{job}/export").json()["approved"]
            assert client.get(f"/api/runs/{job}/export?reviewed=true").status_code == 409
            assert client.get(f"/api/runs/{job}/export?format=html").status_code == 200
            assert TestClient(app).get(f"/api/runs/{job}").status_code == 401
            assert all("Outcome:" not in json.dumps(p) for p in provider.prompts)
            for proposal in packet["proposals"].values():
                for issue in proposal["issues"]:
                    for citation in issue["citations"]:
                        source = client.get(f"/api/sources/{citation['source_id']}").json()
                        assert (
                            source["text"][citation["start"] : citation["end"]] == citation["quote"]
                        )
            result.update(
                status="passed",
                authored_provider_invocations=len(provider.prompts),
                actual_model_invocations=0,
                qualified=False,
            )
        except (AssertionError, KeyError, ValueError) as exc:
            result.update(status="failed", error=type(exc).__name__)
        results.append(result)
        (output / "progress.json").write_text(json.dumps(results, indent=2))
    report = {
        "scope": "actual corpus; local in-process HTTP/API and protocol engineering with authored stand-in, NOT real-model E2E",
        "inventory": inventory,
        "cases": len(results),
        "passed": sum(r["status"] == "passed" for r in results),
        "failed": sum(r["status"] != "passed" for r in results),
        "actual_model_invocations": 0,
        "independent_semantic_accuracy": "not_measured",
        "full_product_accepted": False,
        "live_model_gate": "blocked pending explicit real-payload/model-destination approval",
        "results": results,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(
        json.dumps({k: v for k, v in report.items() if k not in {"results", "inventory"}}, indent=2)
    )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    report = check(args.corpus, args.output)
    raise SystemExit(bool(report["failed"]))
