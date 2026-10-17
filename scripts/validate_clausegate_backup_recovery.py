"""Real-source concurrent backup, later erasure, quarantine and fresh authority drill."""

import argparse
import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from clausegate_api.backup import backup, provision, restore
from clausegate_api.common import byte_hash, now
from clausegate_api.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="var/validation/clausegate-corpus-v2")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root, corpus = Path(args.output), Path(args.corpus)
    root.mkdir(exist_ok=False)
    raw = corpus / "evaluator-only.json"
    manifest = json.loads((corpus / "manifest.json").read_text())
    if byte_hash(raw.read_bytes()) != manifest["normalized_sha256"]:
        raise ValueError("Corpus integrity mismatch")
    rows = [r for r in json.loads(raw.read_text()) if r["split"] == "train"][:2]
    store = Store(root / "store", ledger_dir=root / "authority")
    store.add_user("requester", secrets.token_urlsafe(24))
    workspace = store.create_workspace("requester", "Real-source recovery fixtures")
    cases = []
    for row in rows:
        c = store.create_case("requester", workspace["id"], "Real NDA " + str(row["id"]))
        cases.append(store.import_document("requester", c["id"], c["revision"], row["document"]))
    report = {
        "started_at": now(),
        "source_ids": [r["id"] for r in rows],
        "classification": "Real public source, concurrent domain writes and actual SQLite backup/restore; synthetic identities, no model or legal approval",
        "checks": [],
    }

    def check(name, passed):
        report["checks"].append({"name": name, "passed": bool(passed)})
        (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if not passed:
            raise AssertionError(name)

    def writer():
        revision = cases[1]["revision"]
        for i in range(100):
            current = store.set_context(
                "requester",
                cases[1]["id"],
                revision,
                "recipient",
                f"Legitimate backup-overlap update {i}",
            )
            revision = current["revision"]
        return revision

    with ThreadPoolExecutor(max_workers=1) as pool:
        write = pool.submit(writer)
        manifest = backup(store, root / "snapshot")
        final_revision = write.result(timeout=30)
    check(
        "backup completes while legitimate writes run", final_revision == cases[1]["revision"] + 100
    )
    check(
        "snapshot bytes match manifest",
        byte_hash((root / "snapshot" / "clausegate.sqlite3").read_bytes()) == manifest["sha256"],
    )
    # This snapshot clone is inspected before the source is erased; never reused as live authority.
    clone = Store(root / "snapshot", ledger_dir=store.ledger_dir)
    check(
        "both snapshot audits valid",
        all(clone.verify_audit("requester", c["id"])["valid"] for c in cases),
    )
    check(
        "both snapshot source texts preserved",
        all(
            clone.document("requester", c["document_id"])["text_hash"]
            == row["document"]["text_hash"]
            for c, row in zip(cases, rows, strict=True)
        ),
    )
    current = store.case("requester", cases[0]["id"])
    store.erase("requester", current["id"], current["revision"], "ERASE")
    result = restore(root / "snapshot", root / "restored", ledger_dir=store.ledger_dir)
    check("restore quarantined", result["status"] == "quarantined")
    recovered = Store(root / "restored", ledger_dir=store.ledger_dir)
    denied = False
    try:
        recovered.case("requester", cases[1]["id"])
    except PermissionError:
        denied = True
    check("restored memberships cannot authorize content", denied)
    with recovered.connect() as db:
        check(
            "later erased source not resurrected",
            db.execute(
                "SELECT count(*) FROM documents WHERE case_id=?", (cases[0]["id"],)
            ).fetchone()[0]
            == 0,
        )
        check(
            "unerased source remains available for fresh review",
            db.execute(
                "SELECT count(*) FROM documents WHERE case_id=?", (cases[1]["id"],)
            ).fetchone()[0]
            == 1,
        )
    provision(
        recovered.root,
        recovered.ledger_dir,
        username="fresh-operator",
        password=secrets.token_urlsafe(24),
    )
    check(
        "erased case remains erased after reprovision",
        recovered.case("fresh-operator", cases[0]["id"])["state"] == "erased",
    )
    check(
        "unerased case requires fresh review",
        recovered.case("fresh-operator", cases[1]["id"])["state"] == "stale",
    )
    check(
        "post-restore audit remains valid",
        all(recovered.verify_audit("fresh-operator", c["id"])["valid"] for c in cases),
    )
    report.update(finished_at=now(), passed=all(c["passed"] for c in report["checks"]))
    (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
