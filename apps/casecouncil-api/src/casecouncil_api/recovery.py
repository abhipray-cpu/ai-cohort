"""Explicit operator recovery; original unknown receipts are never overwritten."""

import json
import time

from . import journal
from .consensus import canonical, digest
from .runtime import receipt_from_events, safe_diagnostic
from .runtime_guard import runtime_guard

MAX_INCIDENT_CLOSURES = 1  # lifetime of the independent store authority, not per workspace


def unsafe(receipt):
    diagnostic = receipt.get("diagnostic") or {}
    return (
        diagnostic.get("unsafe_tool_event") is True or diagnostic.get("category") == "unsafe_tool"
    )


def checked_incident(attempt, body, authority):
    original = json.loads(attempt["receipt"]) if attempt["receipt"] else None
    if (
        original is None
        or original.get("usage") is not None
        or unsafe(original)
        or body.get("attempt_id") != attempt["id"]
        or body.get("prompt_hash") != attempt["prompt_hash"]
        or body.get("original_receipt_hash") != digest(original)
        or body.get("reserved_seconds_retained") != attempt["reserved"]
        or body.get("basis") != "owner_accepted_irrecoverable_incident"
        or body.get("usage_remains_unknown") is not True
        or body.get("tool_safety_unverified") is not True
        or body.get("runtime_isolation_attested") is not True
        or body.get("original_reservation_retained") is not True
        or digest(body)
        not in {digest(e["incident"]) for e in authority if e["kind"] == "incident_closed"}
    ):
        raise ValueError("invalid or unbound incident closure")
    if sum(e["kind"] == "incident_closed" for e in authority) > MAX_INCIDENT_CLOSURES:
        raise ValueError("store lifetime incident allowance exceeded")
    return body


def incident_notices(store, db, jid):
    rows = db.execute(
        "SELECT i.body,i.hash,a.* FROM attempt_incidents i JOIN attempts a ON a.id=i.attempt_id WHERE a.job=? ORDER BY i.rowid",
        (jid,),
    ).fetchall()
    if not rows:
        return []
    meta = db.execute("SELECT store_id FROM meta WHERE id=1").fetchone()
    _, events = journal.read(store.journal_path, meta[0])
    notices = []
    for row in rows:
        body = json.loads(row["body"])
        if digest(body) != row["hash"]:
            raise ValueError("incident integrity mismatch")
        checked_incident(row, body, events)
        notices.append(body)
    return notices


def close_incident(
    store,
    actor,
    aid,
    expected_head,
    reason,
    isolation_reference,
    acknowledge_unknown,
    runtime_isolated,
    key,
):
    """Owner/filesystem-operator risk acceptance, never a replacement receipt."""
    from .store import ident

    if (
        acknowledge_unknown is not True
        or runtime_isolated is not True
        or not isinstance(reason, str)
        or not 20 <= len(reason) <= 2000
        or not isinstance(isolation_reference, str)
        or not 20 <= len(isolation_reference) <= 2000
    ):
        raise ValueError(
            "explicit unknown-risk acceptance and process isolation attestation required"
        )
    with runtime_guard(store.root), store.write() as db:
        row = db.execute(
            "SELECT a.*,c.workspace FROM attempts a JOIN jobs j ON j.id=a.job JOIN cases c ON c.id=j.case_id WHERE a.id=?",
            (aid,),
        ).fetchone()
        if not row:
            raise KeyError("attempt not found")
        store._access(db, actor, row["workspace"], {"owner"})

        def commit():
            head_matches(store, db, expected_head)
            if db.execute("SELECT 1 FROM reviews WHERE job=?", (row["job"],)).fetchone():
                raise ValueError("cannot add risk acceptance after a human-reviewed packet")
            if db.execute(
                "SELECT 1 FROM jobs WHERE state IN ('queued','running') LIMIT 1"
            ).fetchone():
                raise ValueError("stop all dispatch before incident closure")
            if db.execute("SELECT 1 FROM attempts WHERE receipt IS NULL LIMIT 1").fetchone():
                raise ValueError("possibly live invocations require separate investigation")
            hold = db.execute(
                "SELECT hold FROM workspaces WHERE id=?", (row["workspace"],)
            ).fetchone()[0]
            if hold not in {"unknown usage or unsafe runtime", "unresolved interrupted call"}:
                raise ValueError(
                    "only unknown-runtime holds are eligible, not integrity or restore incidents"
                )
            original = json.loads(row["receipt"])
            if original.get("usage") is not None or unsafe(original):
                raise ValueError(
                    "only irrecoverable unknown receipts without explicit unsafe events are eligible"
                )
            if db.execute(
                "SELECT 1 FROM attempt_reconciliations WHERE attempt_id=?", (aid,)
            ).fetchone():
                raise ValueError("verified evidence already exists; use evidence recovery")
            meta = db.execute("SELECT store_id FROM meta WHERE id=1").fetchone()
            _, events = journal.read(store.journal_path, meta[0])
            if sum(e["kind"] == "incident_closed" for e in events) >= MAX_INCIDENT_CLOSURES:
                raise ValueError("store lifetime incident allowance exhausted")
            if not any(
                e["kind"] == "settled" and e["attempt"] == aid and e["receipt"] == original
                for e in events
            ):
                raise ValueError("original settlement differs from independent authority")
            body = {
                "id": ident(),
                "attempt_id": aid,
                "prompt_hash": row["prompt_hash"],
                "original_receipt_hash": digest(original),
                "actor": actor,
                "reason_hash": digest(reason),
                "isolation_reference_hash": digest(isolation_reference),
                "basis": "owner_accepted_irrecoverable_incident",
                "recorded": time.time(),
                "usage_remains_unknown": True,
                "tool_safety_unverified": True,
                "runtime_isolation_attested": True,
                "original_reservation_retained": True,
                "reserved_seconds_retained": row["reserved"],
                "lifetime_incident_limit": MAX_INCIDENT_CLOSURES,
            }
            db.execute(
                "INSERT INTO attempt_incidents VALUES(?,?,?,?)",
                (body["id"], aid, canonical(body), digest(body)),
            )
            journal.append(db, store.journal_path, {"kind": "incident_closed", "incident": body})
            store.record(
                db,
                actor,
                "irrecoverable_incident_closed",
                row["workspace"],
                detail={
                    "attempt": aid,
                    "incident": body["id"],
                    "usage_remains_unknown": True,
                    "tool_safety_unverified": True,
                    "reason_hash": body["reason_hash"],
                },
            )
            return body

        return store._idem(
            db,
            actor,
            row["workspace"],
            "incident_close",
            key,
            {
                "attempt": aid,
                "head": expected_head,
                "reason_hash": digest(reason),
                "isolation_reference_hash": digest(isolation_reference),
            },
            commit,
        )


def checked_evidence(attempt, evidence):
    if not isinstance(evidence, dict) or set(evidence) != {"attempt_id", "prompt_hash", "receipt"}:
        raise ValueError("bounded, attempt-bound provider evidence required")
    if evidence["attempt_id"] != attempt["id"] or evidence["prompt_hash"] != attempt["prompt_hash"]:
        raise ValueError("evidence belongs to another invocation")
    receipt = evidence["receipt"]
    if not isinstance(receipt, dict) or set(receipt) - {
        "status",
        "usage",
        "tools_audited",
        "elapsed_ms",
        "diagnostic",
    }:
        raise ValueError("unsupported provider evidence")
    if receipt.get("status") != "returned" or receipt.get("tools_audited") is not True:
        raise ValueError("completed provider receipt and verified tool audit required")
    ms = receipt.get("elapsed_ms")
    if type(ms) is not int or not 0 <= ms <= 1800000:
        raise ValueError("invalid provider elapsed time")
    observed = receipt_from_events(
        canonical({"type": "turn.completed", "usage": receipt.get("usage")}), ms, True, "returned"
    )
    if observed["usage"] is None:
        raise ValueError("known usage evidence required; acknowledgement is insufficient")
    diagnostic = safe_diagnostic(receipt.get("diagnostic"))
    if diagnostic["unsafe_tool_event"] or diagnostic["category"] == "unsafe_tool":
        raise ValueError("unsafe tool evidence requires separate incident handling")
    observed["diagnostic"] = diagnostic
    return observed


def head_matches(store, db, expected):
    journal.assert_current(db, store.journal_path)
    if db.execute("SELECT journal_head FROM meta WHERE id=1").fetchone()[0] != expected:
        raise ValueError("usage authority changed; inspect current state")


def reconcile_attempt(store, actor, aid, expected_head, evidence, reference, key):
    from .store import ident

    if not isinstance(reference, str) or not 20 <= len(reference) <= 2000:
        raise ValueError("verified provider evidence reference required")
    with store.write() as db:
        row = db.execute(
            "SELECT a.*,c.workspace FROM attempts a JOIN jobs j ON j.id=a.job JOIN cases c ON c.id=j.case_id WHERE a.id=?",
            (aid,),
        ).fetchone()
        if not row:
            raise KeyError("attempt not found")
        store._access(db, actor, row["workspace"], {"owner"})

        def commit():
            head_matches(store, db, expected_head)
            if row["receipt"] is None:
                raise ValueError("pending call cannot be reconciled while potentially live")
            original = json.loads(row["receipt"])
            if (
                original.get("diagnostic", {}).get("unsafe_tool_event")
                or original.get("diagnostic", {}).get("category") == "unsafe_tool"
            ):
                raise ValueError("unsafe tool incident requires separate handling")
            if isinstance(original.get("usage"), dict) and original.get("tools_audited"):
                raise ValueError("original invocation already has known audited usage")
            proof = checked_evidence(row, evidence)
            rid = ident()
            body = {
                "id": rid,
                "attempt_id": aid,
                "prompt_hash": row["prompt_hash"],
                "actor": actor,
                "reference_hash": digest(reference),
                "evidence_hash": digest(evidence),
                "original_receipt_hash": digest(original),
                "receipt": proof,
                "recorded": time.time(),
                "basis": "operator_verified_provider_evidence",
                "usage_observed_by_original_call": False,
                "original_reservation_retained": True,
            }
            db.execute(
                "INSERT INTO attempt_reconciliations VALUES(?,?,?,?)",
                (rid, aid, canonical(body), digest(body)),
            )
            journal.append(
                db, store.journal_path, {"kind": "attempt_reconciled", "reconciliation": body}
            )
            store.record(
                db,
                actor,
                "attempt_reconciled",
                row["workspace"],
                detail={
                    "attempt": aid,
                    "reconciliation": rid,
                    "evidence_hash": body["evidence_hash"],
                    "original_receipt_unchanged": True,
                },
            )
            return body

        return store._idem(
            db,
            actor,
            row["workspace"],
            "attempt_reconcile",
            key,
            {
                "attempt": aid,
                "head": expected_head,
                "evidence": evidence,
                "reference_hash": digest(reference),
            },
            commit,
        )


def liabilities_resolved(store, db, workspace=None):
    rows = db.execute(
        "SELECT a.* FROM attempts a JOIN jobs j ON j.id=a.job JOIN cases c ON c.id=j.case_id WHERE (? IS NULL OR c.workspace=?)",
        (workspace, workspace),
    ).fetchall()
    for attempt in rows:
        if attempt["receipt"] is None:
            raise ValueError("unsettled invocation remains")
        original = json.loads(attempt["receipt"])
        if unsafe(original):
            raise ValueError("unsafe tool incident requires separate handling")
        if isinstance(original.get("usage"), dict) and original.get("tools_audited"):
            continue
        r = db.execute(
            "SELECT * FROM attempt_reconciliations WHERE attempt_id=?", (attempt["id"],)
        ).fetchone()
        if not r:
            incident = db.execute(
                "SELECT body,hash FROM attempt_incidents WHERE attempt_id=?", (attempt["id"],)
            ).fetchone()
            if not incident:
                raise ValueError(
                    "unknown usage requires verified evidence or explicit bounded incident closure"
                )
            body = json.loads(incident["body"])
            if digest(body) != incident["hash"]:
                raise ValueError("incident integrity mismatch")
            meta = db.execute("SELECT store_id FROM meta WHERE id=1").fetchone()
            _, events = journal.read(store.journal_path, meta[0])
            checked_incident(attempt, body, events)
            continue
        body = json.loads(r["body"])
        if digest(body) != r["hash"] or body["original_receipt_hash"] != digest(original):
            raise ValueError("reconciliation integrity mismatch")
        checked_evidence(
            attempt,
            {
                "attempt_id": body["attempt_id"],
                "prompt_hash": body["prompt_hash"],
                "receipt": body["receipt"],
            },
        )


def resume_job(store, actor, jid, packet_hash, expected_head, wall_seconds, reason, key):
    from .store import ident

    if (
        type(wall_seconds) is not int
        or not 90 <= wall_seconds <= 1800
        or not isinstance(reason, str)
        or not 20 <= len(reason) <= 2000
    ):
        raise ValueError("explicit bounded recovery window and reason required")
    with store.write() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        if not row:
            raise KeyError("job not found")
        case = store._case(db, actor, row["case_id"], {"owner"})

        def commit():
            head_matches(store, db, expected_head)
            if db.execute(
                "SELECT 1 FROM jobs WHERE state IN ('queued','running') LIMIT 1"
            ).fetchone():
                raise ValueError("stop other dispatch before recovery")
            if db.execute("SELECT 1 FROM attempts WHERE receipt IS NULL LIMIT 1").fetchone():
                raise ValueError("a possibly live invocation remains unsettled")
            hold = db.execute(
                "SELECT hold FROM workspaces WHERE id=?", (case["workspace"],)
            ).fetchone()[0]
            if hold not in {None, "unknown usage or unsafe runtime", "unresolved interrupted call"}:
                raise ValueError("integrity/restore holds cannot be bypassed by resume")
            if (
                row["state"] != "manual_required"
                or row["error"]
                or not row["packet"]
                or row["packet_hash"] != packet_hash
                or digest(json.loads(row["packet"])) != packet_hash
            ):
                raise ValueError("current degraded packet required")
            if db.execute("SELECT 1 FROM reviews WHERE job=?", (jid,)).fetchone():
                raise ValueError("reviewed packet cannot be rewritten by recovery")
            current = store._snapshot(db, row["actor"], row["case_id"])
            if (
                current["binding"] != row["binding"]
                or canonical(current) != row["snapshot"]
                or digest(current) != row["snapshot_hash"]
            ):
                raise ValueError("source, authority or snapshot changed")
            liabilities_resolved(store, db)
            stages = store._checkpoints(db, jid)
            retry = [
                name
                for name, value in stages.items()
                if value.get("error")
                in {
                    "provider_unavailable",
                    "provider_audit_exit_or_usage",
                    "allowance_or_runtime_hold",
                }
                and value.get("value") is None
            ]
            if not retry or row["calls"] >= 22 or row["seconds"] + 90 > 1800 or row["claims"] >= 4:
                raise ValueError("no retryable stage or remaining allowance")
            for name in retry:
                if (
                    db.execute(
                        "SELECT count(*) FROM attempts WHERE job=? AND stage=?", (jid, name)
                    ).fetchone()[0]
                    >= 2
                ):
                    raise ValueError("stage allowance exhausted; recovery cannot add retries")
            recovery = ident()
            db.execute(
                "INSERT INTO packet_history VALUES(?,?,?,?,?)",
                (ident(), jid, row["packet"], packet_hash, recovery),
            )
            for name in retry + [
                s for s in ("consensus", "synthesis") if s in stages and s not in retry
            ]:
                body = canonical(stages[name])
                db.execute(
                    "INSERT INTO checkpoint_history VALUES(?,?,?,?,?,?)",
                    (ident(), jid, name, body, digest(stages[name]), recovery),
                )
                db.execute("DELETE FROM checkpoints WHERE job=? AND stage=?", (jid, name))
            db.execute(
                "UPDATE jobs SET state='queued',deadline=?,packet=NULL,packet_hash=NULL,token=NULL,lease_until=0 WHERE id=?",
                (time.time() + wall_seconds, jid),
            )
            db.execute("UPDATE workspaces SET hold=NULL WHERE id=?", (case["workspace"],))
            journal.append(
                db,
                store.journal_path,
                {
                    "kind": "job_resume_authorized",
                    "job": jid,
                    "recovery": recovery,
                    "calls_retained": row["calls"],
                    "seconds_retained": row["seconds"],
                    "wall_seconds": wall_seconds,
                    "actor": actor,
                    "reason_hash": digest(reason),
                },
            )
            store.record(
                db,
                actor,
                "job_resume_authorized",
                case["workspace"],
                row["case_id"],
                {
                    "job": jid,
                    "recovery": recovery,
                    "prior_packet_hash": packet_hash,
                    "retry_stages": retry,
                    "reason_hash": digest(reason),
                    "calls_retained": row["calls"],
                },
            )
            return {
                "job": jid,
                "recovery": recovery,
                "calls_retained": row["calls"],
                "state": "queued",
            }

        return store._idem(
            db,
            actor,
            case["workspace"],
            "job_resume",
            key,
            {
                "job": jid,
                "packet_hash": packet_hash,
                "head": expected_head,
                "wall_seconds": wall_seconds,
                "reason_hash": digest(reason),
            },
            commit,
        )
