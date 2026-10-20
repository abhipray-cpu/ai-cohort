"""Continue ONLY the approved six-case development campaign in its original store.

This is an operator/real-model continuation, not fresh HTTP/browser acceptance.
No automatic incident closure, source-rights renewal, human approval or budget reset.
"""

import argparse
import json
from pathlib import Path

from casecouncil_api import journal
from casecouncil_api.campaign import limit_store_calls, summarize_replay
from casecouncil_api.controller import Controller
from casecouncil_api.evaluation import audit_corpus, load_manifest, safe_path
from casecouncil_api.runtime import provider_from_env
from casecouncil_api.store import Store
from casecouncil_api.verification import verify_packet


def validate_selection(selection, manifest, inventory):
    ids = selection["ids"]
    approval = manifest.get("egress_approval", {})
    if (
        not manifest["permission"]["egress"]
        or not 1 <= len(ids) <= 6
        or len(set(ids)) != len(ids)
        or set(ids) != {c["id"] for c in manifest["cases"]}
        or any(c["split"] != "development" for c in manifest["cases"])
        or not set(ids) <= set(approval.get("ids", []))
        or not 22 <= selection["max_calls"] <= approval.get("max_calls", 0) <= 132
        or inventory["manifest_hash"] != selection["manifest_hash"]
    ):
        raise ValueError(
            "exact current approved six-case selection and original cumulative ceiling required"
        )


def observed_result(store, actor, cid, jid):
    run = store.job(actor, jid)
    packet = run["packet"] or {}
    receipts = [a["receipt"] for a in run["attempts"]]
    result = {
        "id": cid,
        "job": jid,
        "case": run["case_id"],
        "state": run["state"],
        "calls": run["calls"],
        "usage_known": sum(bool(r and r.get("usage")) for r in receipts),
        "all_tools_audited": all(r and r.get("tools_audited") for r in receipts),
        "proposers": sorted(packet.get("proposals", {})),
        "critic_available": packet.get("critique") is not None,
        "ballots": sorted(packet.get("ballots", {})),
        "synthesis_available": packet.get("synthesis") is not None,
        "unavailable": packet.get("unavailable", []),
        "packet_hash": run["packet_hash"],
        "incidents": run["incidents"],
        "consensus": packet.get("consensus"),
        "input_tokens_lower_bound": sum(
            (r.get("usage") or {}).get("input_tokens", 0) for r in receipts if r
        ),
        "output_tokens_lower_bound": sum(
            (r.get("usage") or {}).get("output_tokens", 0) for r in receipts if r
        ),
    }
    if packet.get("consensus"):
        result["mechanical_verification"] = verify_packet(packet, run["snapshot"], run["incidents"])
    else:
        result["mechanical_verification"] = {"not_verified": "no consensus packet available"}
    return result, packet


def continue_replay(args):
    if not args.live:
        raise ValueError("explicit --live required; approved actual-case payloads leave this host")
    run_root = Path(args.run).resolve()
    selection = json.loads((run_root / "selection.json").read_text())
    original = json.loads((run_root / "report.json").read_text())
    corpus, manifest = load_manifest(args.corpus)
    inventory = audit_corpus(corpus)
    validate_selection(selection, manifest, inventory)
    service = run_root / "service"
    if not (service / "casecouncil.sqlite3").is_file():
        raise ValueError("original existing service store required; no fresh workspace")
    store = Store(service, evaluation_only=True)
    by_id = {r["id"]: r for r in original["results"]}
    if not by_id or not set(by_id) <= set(selection["ids"]):
        raise ValueError("original campaign mapping required")
    first = next(iter(by_id.values()))
    with store.connect() as db:
        row = db.execute(
            "SELECT j.actor,c.workspace FROM jobs j JOIN cases c ON c.id=j.case_id WHERE j.id=?",
            (first["job"],),
        ).fetchone()
        actor, workspace = row["actor"], row["workspace"]
        rights = db.execute(
            "SELECT rights_id FROM sources WHERE case_id=? LIMIT 1", (first["case"],)
        ).fetchone()[0]
        journal.assert_current(db, store.journal_path)
        if db.execute("SELECT 1 FROM jobs WHERE state='running' LIMIT 1").fetchone():
            raise ValueError("another runtime may be active")
        for result in by_id.values():
            check = db.execute(
                "SELECT j.case_id,j.actor,c.workspace FROM jobs j JOIN cases c ON c.id=j.case_id WHERE j.id=?",
                (result["job"],),
            ).fetchone()
            if not check or tuple(check) != (result["case"], actor, workspace):
                raise ValueError("original mapping differs from runtime authority")
        from casecouncil_api.recovery import liabilities_resolved

        liabilities_resolved(store, db)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    limit_store_calls(
        store,
        actor,
        workspace,
        selection["max_calls"],
        "User-approved continuation of the same six-case campaign; retain every original attempt",
    )
    (output / "selection.json").write_text(json.dumps(selection, indent=2))
    controller = Controller(store, provider_from_env())
    records = {r["id"]: r for r in manifest["cases"]}
    results = []
    for cid in selection["ids"]:
        with store.connect() as db:
            events = journal.assert_current(db, store.journal_path)
        charged = sum(e["kind"] == "reserved" for e in events)
        if cid in by_id:
            jid = by_id[cid]["job"]
        else:
            if selection["max_calls"] - charged < 22 or store.workspace(actor, workspace)["hold"]:
                break
            record = records[cid]
            case = store.create_case(actor, workspace, record["context"], "continue:" + cid)["id"]
            for n, doc in enumerate(record["documents"]):
                path = safe_path(corpus, doc["path"], "inputs")
                store.add_source(
                    actor,
                    case,
                    n + 1,
                    path.name,
                    path.read_bytes(),
                    doc["kind"],
                    rights,
                    "continue:" + cid + ":" + str(n),
                )
            preview = store.preview(actor, case)
            jid = store.start(actor, case, preview["binding"], "continue:" + cid)["id"]
        run = store.job(actor, jid)
        if run["state"] == "queued":
            with store.connect() as db:
                if any(
                    r[0] != jid
                    for r in db.execute("SELECT id FROM jobs WHERE state IN ('queued','running')")
                ):
                    raise ValueError("stop unrelated dispatch before continuation")
            controller.once()
        result, packet = observed_result(store, actor, cid, jid)
        results.append(result)
        (output / (cid + ".packet.json")).write_text(json.dumps(packet, indent=2))
        (output / "progress.json").write_text(json.dumps(results, indent=2))
        print(
            json.dumps(
                {
                    "id": cid,
                    "state": result["state"],
                    "calls": result["calls"],
                    "incidents": len(result["incidents"]),
                }
            ),
            flush=True,
        )
        if store.workspace(actor, workspace)["hold"]:
            break
    with store.connect() as db:
        events = journal.assert_current(db, store.journal_path)
    report = {
        "scope": "same-store real-model continuation; pending intake uses operator Store, NOT browser or new HTTP acceptance",
        "service_path": str(service),
        "original_run": str(run_root),
        "manifest_hash": inventory["manifest_hash"],
        "results": results,
        "cumulative_calls": sum(e["kind"] == "reserved" for e in events),
        "max_calls": selection["max_calls"],
        "workspace_hold": store.workspace(actor, workspace)["hold"],
        **summarize_replay(selection["ids"], results),
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2), flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--live", action="store_true")
    result = continue_replay(parser.parse_args())
    raise SystemExit(0 if result["protocol_campaign_passed"] else 1)
