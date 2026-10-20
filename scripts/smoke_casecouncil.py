"""Bounded actual-Codex engineering smoke on personally authored fictional material.

Not real-world semantic validation and never an FOS acquisition utility.
"""

import argparse
import json
import secrets
import time
from pathlib import Path

from casecouncil_api.controller import Controller
from casecouncil_api.runtime import provider_from_env
from casecouncil_api.store import Store


def smoke(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    s = Store(output / "service")
    s.bootstrap("smoke-author", secrets.token_urlsafe(24))
    w = s.create_workspace("smoke-author", "Owned engineering fixture", "workspace")
    s.set_policy(
        "smoke-author",
        w,
        1,
        {
            "name": "Fictional test-only policy",
            "instructions": "Use only the authored test text. Do not apply real legal rules. A missing recording prevents a verified finding about what the agent said.",
            "required_documents": ["complaint", "policy"],
            "egress_enabled": True,
        },
    )
    rid = s.add_rights(
        "smoke-author",
        w,
        {
            "basis": "owned_test",
            "reference": "Original fictional material authored for this implementation smoke; not customer data or a public decision.",
            "expires": time.time() + 86400,
            "egress": True,
        },
    )
    c = s.create_case(
        "smoke-author",
        w,
        {
            "title": "Fictional premium communication complaint",
            "issues": [{"id": "premium", "title": "Premium deduction and alleged refund promise"}],
            "facts": "The fictional customer alleges a refund promise. No original recording is available.",
            "draft": "No complaint issue exists because premiums remain payable.",
            "missing": ["Original agent recording or written refund promise"],
        },
        "case",
    )["id"]
    for n, kind, body in (
        (
            1,
            "complaint",
            b"FICTIONAL ENGINEERING FIXTURE. The customer alleges an agent promised a premium refund after a total-loss claim. No call recording or written promise is available.",
        ),
        (
            2,
            "policy",
            b"FICTIONAL ENGINEERING FIXTURE. Annual premiums remain payable after a total-loss claim. Alleged service errors require a separate evidence review. No compensation amount or binding resolution is authorized by this fixture.",
        ),
    ):
        s.add_source("smoke-author", c, n, kind + ".txt", body, kind, rid, "source" + str(n))
    preview = s.preview("smoke-author", c)
    j = s.start("smoke-author", c, preview["binding"], "run")
    Controller(s, provider_from_env()).once()
    run = s.job("smoke-author", j["id"])
    usage = [
        a["receipt"]["usage"] for a in run["attempts"] if a["receipt"] and a["receipt"].get("usage")
    ]
    report = {
        "scope": "actual installed Codex; authored fictional engineering fixture, NOT real-data accuracy",
        "state": run["state"],
        "calls": run["calls"],
        "packet_hash": run["packet_hash"],
        "unavailable": run["packet"].get("unavailable", []) if run["packet"] else ["packet"],
        "all_tools_audited": bool(run["attempts"])
        and all(a["receipt"] and a["receipt"].get("tools_audited") for a in run["attempts"]),
        "known_receipts": len(usage),
        "input_tokens": sum(u["input_tokens"] for u in usage),
        "output_tokens": sum(u["output_tokens"] for u in usage),
        "full_product_accepted": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument("--live", action="store_true")
    args = p.parse_args()
    if not args.live:
        p.error("--live explicitly authorizes up to 22 actual model invocations")
    r = smoke(args.output)
    raise SystemExit(
        0 if r["state"] == "draft_ready" and not r["unavailable"] and r["all_tools_audited"] else 1
    )
