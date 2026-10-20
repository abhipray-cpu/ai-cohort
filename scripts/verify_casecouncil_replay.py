"""Read-only verification of stored actual-model run artifacts. Never invokes Codex."""

import argparse
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from casecouncil_api.campaign import summarize_replay
from casecouncil_api.consensus import digest
from casecouncil_api.recovery import incident_notices
from casecouncil_api.verification import verify_packet


def verify(root, output=None, data_dir=None):
    root = Path(root).resolve()
    report = json.loads((root / "report.json").read_text())
    selected = json.loads((root / "selection.json").read_text())["ids"]
    results = []
    service = Path(data_dir).resolve() if data_dir else root / "service"
    authority = SimpleNamespace(journal_path=service / "authority/usage.jsonl")
    with sqlite3.connect(f"file:{service / 'casecouncil.sqlite3'}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        for result in report["results"]:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (result["job"],)).fetchone()
            packet, snapshot = json.loads(row["packet"]), json.loads(row["snapshot"])
            if digest(packet) != row["packet_hash"] or digest(snapshot) != row["snapshot_hash"]:
                raise ValueError("stored packet/snapshot integrity mismatch")
            notices = incident_notices(authority, db, row["id"])
            checked = verify_packet(packet, snapshot, notices)
            receipts = [
                json.loads(a[0]) if a[0] else None
                for a in db.execute("SELECT receipt FROM attempts WHERE job=?", (row["id"],))
            ]
            results.append(
                {
                    "id": result["id"],
                    **checked,
                    "calls": len(receipts),
                    "known_usage": sum(bool(r and r.get("usage")) for r in receipts),
                    "tools_audited": all(r and r.get("tools_audited") for r in receipts),
                    "state": row["state"],
                    "incidents": notices,
                    "qualified_issues": sum(i["qualified"] for i in packet["consensus"]["issues"]),
                    "confidence": packet["consensus"]["confidence_band"],
                    "statuses": [i["status"] for i in packet["consensus"]["issues"]],
                    "critique_findings": len((packet.get("critique") or {}).get("findings", [])),
                    "usage_known": sum(bool(r and r.get("usage")) for r in receipts),
                    "all_tools_audited": all(r and r.get("tools_audited") for r in receipts),
                    "proposers": sorted(packet.get("proposals", {})),
                    "critic_available": packet.get("critique") is not None,
                    "ballots": sorted(packet.get("ballots", {})),
                    "synthesis_available": packet.get("synthesis") is not None,
                    "revised": packet["revised"],
                    "unavailable": packet["unavailable"],
                }
            )
        failures = [
            {"action": r[0], "count": r[1]}
            for r in db.execute(
                "SELECT action,count(*) FROM audit WHERE action LIKE '%fail%' GROUP BY action"
            )
        ]
    checked = {
        "scope": "read-only mechanical recheck of stored actual-model outputs, not independent domain judgement",
        "cases": len(results),
        "calls": sum(r["calls"] for r in results),
        "exact_citations_rechecked": sum(r["exact_citations_rechecked"] for r in results),
        "audit_failures": failures,
        "results": results,
        "full_product_accepted": False,
        **summarize_replay(selected, results),
    }
    destination = Path(output) if output else root / "verification.json"
    with destination.open("x" if output else "w") as stream:
        stream.write(json.dumps(checked, indent=2) + "\n")
    print(json.dumps(checked, indent=2))
    return checked


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument(
        "--output", help="New-only output path; preserve original campaign artifacts"
    )
    parser.add_argument(
        "--data-dir", help="Explicit original store for a same-store continuation report"
    )
    args = parser.parse_args()
    checked = verify(args.run, args.output, args.data_dir)
    raise SystemExit(0 if checked["protocol_campaign_passed"] else 1)
