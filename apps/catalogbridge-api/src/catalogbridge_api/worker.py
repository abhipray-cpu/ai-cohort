"""Durable, budgeted matching; safe manual degradation without calibration."""

import json
import logging
import os
import signal
import time

from contracts.catalogbridge import Calibration, Proposal

from .local_router import configured_router
from .matching import binding, candidates, conflicts, draft_key, validate_proposal
from .model_boundary import InstalledModels
from .runtime import DispatchNotStarted, diagnostics
from .store import Store

log = logging.getLogger(__name__)


def finish(store, task, result, state, cache_key=None):
    try:
        store.checkpoint(task, result, state, draft_cache_key=cache_key)
    except ValueError:
        log.warning("Discarded stale CatalogBridge result; incurred usage retained")
    return True


def run_once(store: Store, provider=None, *, local_router=None):
    task = store.claim()
    if task is None:
        return False
    spec = task["spec"]
    result = {
        "candidate_id": None,
        "reason": "unprocessed",
        "attempts": [],
        "proposal_history": [],
        "binding": binding(spec),
        "budget_mode": spec.budget_mode,
        "calibrated": False,
    }
    state = "needs_review"
    cache_key = None
    try:
        master = store.feed(task["workspace"], spec.master_id)
        gallery = master["records"]
        selected = candidates(task["source"], gallery)
        result["candidates"] = [r.model_dump() for r in selected]
        result["conflicts"] = {r.id: conflicts(task["source"], r) for r in selected}
        if not selected:
            result["reason"] = "no verified match among retrieved candidates"
            state = "no_verified_match"
        elif not spec.egress:
            result["reason"] = "model egress not authorized; manual review available"
        elif store.runtime_status(task["workspace"])["open"]:
            result["reason"] = "runtime circuit open; inference blocked, manual review available"
            result["runtime_circuit"] = store.runtime_status(task["workspace"])
        else:
            if spec.routing_policy == "local_review_v1":
                try:
                    local = local_router or configured_router()
                    if local.fingerprint != spec.local_router_sha256:
                        raise ValueError("local routing profile changed")
                    draft = local.propose(task["source"], selected)
                except (ValueError, OSError, RecursionError):
                    draft = None
                    result["local_profile_unavailable"] = True
                    with store.write() as db:
                        store.event(
                            db,
                            task["batch_id"],
                            "local_route_unavailable",
                            {
                                "task": task["id"],
                                "reason": "missing, invalid or changed profile; budgeted LLM fallback only",
                            },
                        )
                if draft:
                    proposal, evidence = draft
                    result.update(
                        {
                            "proposal": proposal.model_dump(),
                            "candidate_id": proposal.candidate_id,
                            "reason": proposal.reason,
                            "exit_stage": "local_pair",
                            "local_routing": evidence,
                        }
                    )
                    with store.write() as db:
                        store.event(
                            db,
                            task["batch_id"],
                            "local_route_exit",
                            {"task": task["id"], **evidence},
                        )
                    return finish(store, task, result, "needs_review")
            if spec.reuse_validated_drafts:
                cache_key = draft_key(spec, task["source"], master["hash"], selected)
                cached = store.cached_draft(task["workspace"], cache_key)
                if cached:
                    try:
                        previous = json.loads(cached["result"])
                        proposal = Proposal.model_validate(previous["proposal"])
                        validate_proposal(proposal, task["source"], selected)
                        if proposal.outcome == "insufficient_evidence":
                            raise ValueError("uncertain draft cannot be reused")
                    except (ValueError, KeyError, TypeError):
                        with store.write() as db:
                            store.event(
                                db, task["batch_id"], "draft_cache_rejected", {"task": task["id"]}
                            )
                    else:
                        result.update(
                            {
                                "proposal": proposal.model_dump(),
                                "candidate_id": proposal.candidate_id,
                                "reason": "Exact-context draft reused; review required, no inference dispatched",
                                "cached_from": {
                                    "task_id": cached["id"],
                                    "batch_id": cached["batch_id"],
                                    "created": cached["created"],
                                    "expires": cached["expires"],
                                    "attempts": previous.get("attempts", []),
                                },
                            }
                        )
                        with store.write() as db:
                            store.event(
                                db,
                                task["batch_id"],
                                "draft_cache_hit",
                                {
                                    "task": task["id"],
                                    "source_task": cached["id"],
                                    "source_batch": cached["batch_id"],
                                    "automatic_acceptance": False,
                                },
                            )
                        return finish(store, task, result, "needs_review")
            cal = None
            with store.connect() as db:
                row = db.execute(
                    "SELECT body FROM calibrations WHERE id=?", (spec.calibration_id,)
                ).fetchone()
            if row:
                parsed = Calibration.model_validate_json(row[0])
                if (
                    parsed.binding == binding(spec)
                    and parsed.evidence_status == "empirically_verified"
                ):
                    cal = parsed
                else:
                    result["calibration_rejected"] = "unverified evidence or stale binding"
            models = provider or InstalledModels(
                os.environ.get("CATALOGBRIDGE_CODEX_COMMAND", "codex"),
                instruction_profile=spec.instruction_profile,
            )
            if hasattr(models, "preflight"):
                try:
                    models.preflight(task["source"], selected)
                except ValueError:
                    with store.write() as db:
                        store.event(
                            db,
                            task["batch_id"],
                            "preflight_refused",
                            {"task": task["id"], "reason": "unsupported prompt envelope"},
                        )
                    raise
            # Complex ambiguity can skip the economy call entirely.
            complex_case = len(selected) > 3 or (not task["source"].brand and len(selected) > 1)
            stages = (
                [("strong", spec.strong_model)]
                if complex_case
                else [("economy", spec.economy_model), ("strong", spec.strong_model)]
            )
            started = time.monotonic()
            for route, model in stages:
                if time.monotonic() - started >= 240:
                    raise ValueError("row active deadline exhausted")
                # Conservative advisory reserve; not a provider-side hard token cap.
                metrics = store.analytics(task["workspace"], task["batch_id"])
                if not metrics["journal_consistent"]:
                    raise ValueError("usage journal inconsistent")
                attempt = store.reserve(
                    task["batch_id"], task["id"], route, 12000, expected_lease=task["lease"]
                )
                result["attempts"].append(attempt)
                try:
                    generated = models.generate_pair(
                        task["source"], selected, model, min(90, 240 - (time.monotonic() - started))
                    )
                except Exception as exc:
                    evidence = getattr(exc, "diagnostics", diagnostics(exception=exc))
                    store.settle(attempt, getattr(exc, "usage", None), runtime_evidence=evidence)
                    if not isinstance(exc, DispatchNotStarted):
                        store.open_runtime_circuit(task["workspace"], task["batch_id"], evidence)
                    with store.write() as db:
                        store.event(
                            db,
                            task["batch_id"],
                            "provider_failure",
                            {
                                "attempt": attempt,
                                "error_type": type(exc).__name__,
                                "diagnostics": evidence,
                            },
                        )
                    raise ValueError(
                        "provider failed; recorded usage retained, unknown liability held"
                    ) from exc
                store.settle(attempt, generated.usage, runtime_evidence=generated.diagnostics)
                evidence = generated.diagnostics or {
                    "category": "runtime_failure",
                    "exit_code": generated.exit_code,
                }
                if generated.exit_code or not generated.audited or generated.usage is None:
                    if not generated.exit_code:
                        evidence = evidence | {
                            "category": "audit_unverified"
                            if not generated.audited
                            else "usage_unknown"
                        }
                    store.open_runtime_circuit(task["workspace"], task["batch_id"], evidence)
                    with store.write() as db:
                        store.event(
                            db,
                            task["batch_id"],
                            "provider_failure",
                            {"attempt": attempt, "diagnostics": evidence},
                        )
                    result["runtime_diagnostics"] = evidence
                    raise ValueError("provider runtime failed; inference circuit open")
                try:
                    proposal = Proposal.model_validate_json(generated.text)
                    validate_proposal(proposal, task["source"], selected)
                except ValueError as exc:
                    with store.write() as db:
                        store.event(
                            db,
                            task["batch_id"],
                            "validation_failure",
                            {"attempt": attempt, "error_type": type(exc).__name__},
                        )
                    result["reason"] = "proposal failed schema or source evidence validation"
                    continue
                result.update(
                    {
                        "proposal": proposal.model_dump(),
                        "candidate_id": proposal.candidate_id,
                        "reason": proposal.reason,
                        "exit_stage": route,
                        "model_requested": model,
                        "effective_model": generated.effective_model,
                    }
                )
                result["proposal_history"].append(
                    {
                        "attempt": attempt,
                        "stage": route,
                        "model_requested": model,
                        "effective_model": generated.effective_model,
                        "proposal": proposal.model_dump(),
                    }
                )
                score = (
                    (cal.economy_score if route == "economy" else cal.strong_score) if cal else None
                )
                # This initial profile only qualifies unique-candidate decisions.
                if (
                    cal
                    and generated.effective_model == model
                    and score >= cal.threshold
                    and len(selected) == 1
                    and proposal.outcome == "same_product"
                ):
                    result.update({"calibrated": True, "calibration_id": cal.id, "score": score})
                    state = "recommended_match"
                    with store.write() as db:
                        store.event(
                            db,
                            task["batch_id"],
                            "early_exit",
                            {"task": task["id"], "stage": route, "calibration": cal.id},
                        )
                    break
                result["reason"] = (
                    "proposal available; calibrated acceptance unavailable or insufficient"
                )
                # Missing acceptance calibration is not evidence that another
                # paid opinion will help. Escalate uncertainty/invalid output,
                # not every decisive, source-validated review draft.
                if proposal.outcome != "insufficient_evidence":
                    break
    except Exception as exc:  # noqa: BLE001 - persist terminal failures; never lose prior rows
        result["reason"] = (
            str(exc) if isinstance(exc, ValueError) else "internal processing failure"
        )
        if result.get("proposal"):
            state = "needs_review"
            result["degraded"] = True
            with store.write() as db:
                store.event(
                    db,
                    task["batch_id"],
                    "partial_proposal_retained",
                    {"task": task["id"], "error_type": type(exc).__name__},
                )
        else:
            state = "failed"
        log.warning("CatalogBridge task failed: %s", type(exc).__name__)
    reusable = (
        cache_key
        and not result.get("degraded")
        and result.get("proposal")
        and result["proposal"]["outcome"] != "insufficient_evidence"
    )
    return finish(store, task, result, state, cache_key if reusable else None)


def main():
    from .api import settings

    config = settings()
    store = Store(config["data_dir"], config["journal_dir"])
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while not stopping:
        if not run_once(store):
            time.sleep(0.5)


if __name__ == "__main__":
    main()
