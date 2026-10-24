"""Serialized, checkpointed casework worker. Real-data campaigns are separate opt-ins."""

import json
import os
import signal
import time
from pathlib import Path

from agent_core.provider import ProviderTimeoutError
from contracts.repairclaim import CaseSnapshot, Contract, EvidenceAnchor, Fact
from pydantic import Field, StrictBool, ValidationError

from repairclaim_api.core import evaluate_search, next_question, verify_anchor
from repairclaim_api.errors import DomainError
from repairclaim_api.parser import RestrictedParser
from repairclaim_api.store import Store


class AgentAdvice(Contract):
    candidate_family: str | None = Field(max_length=80)
    agrees_with_conditions: StrictBool
    needs_human_review: StrictBool
    confidence: float = Field(ge=0, le=1, strict=True)
    citations: tuple[EvidenceAnchor, ...] = Field(max_length=10)


def _parsed_response(raw, expected_hash):
    if (
        not isinstance(raw, dict)
        or raw.get("sha256") != expected_hash
        or not isinstance(raw.get("pages"), list)
        or not 1 <= len(raw["pages"]) <= 100
        or raw.get("page_count") != len(raw["pages"])
        or len(raw.get("proposals", [])) > 100
    ):
        raise DomainError("parser_tool_response_invalid", 422)
    for index, page in enumerate(raw["pages"], 1):
        if (
            page.get("page") != index
            or not isinstance(page.get("text"), str)
            or len(page["text"]) > 64000
        ):
            raise DomainError("parser_tool_response_invalid", 422)
    for proposal in raw.get("proposals", []):
        page = next((page for page in raw["pages"] if page["page"] == proposal.get("page")), None)
        if (
            page is None
            or not isinstance(proposal.get("quote"), str)
            or not proposal["quote"]
            or proposal["quote"] not in page["text"]
            or len(str(proposal.get("value", ""))) > 200
        ):
            raise DomainError("parser_tool_response_invalid", 422)
        proposal["status"] = "extracted"
        try:
            Fact(
                field=proposal["field"],
                value=proposal["value"],
                unit=proposal.get("unit"),
                status="extracted",
                anchor=EvidenceAnchor(
                    document_id="parser-result",
                    sha256=expected_hash,
                    page=proposal["page"],
                    quote=proposal["quote"],
                ),
            )
        except (ValidationError, KeyError) as error:
            raise DomainError("parser_tool_response_invalid", 422) from error
        if str(proposal["value"]).casefold().replace(",", "") not in proposal[
            "quote"
        ].casefold().replace(",", ""):
            raise DomainError("parser_tool_response_invalid", 422)
    return raw


def _parse(store, item, parser):
    with store._transaction() as db:
        current = store._object(db, item["id"])
        store._job_actor(db, current)
        document = store._object(db, current["data"]["document_id"])
        content, filename = (
            store._blob_read(document["data"]["blob_id"]),
            document["data"]["filename"],
        )
    parsed = _parsed_response(parser.run("parse", content, filename), document["data"]["sha256"])
    with store._transaction() as db:
        current = store._object(db, item["id"])
        actor = store._job_actor(db, current)
        if current["state"] != "running" or current["data"].get("lease") != item["data"]["lease"]:
            return
        document, case = store._scoped_object(
            db, actor, current["data"]["document_id"], "document", "edit"
        )
        document["data"]["parsed"] = parsed
        store._update_object(db, document, state="ready")
        store._audit(db, actor, case, "document_extracted_unconfirmed")
    store.commit_job(
        item, {"document_id": document["id"], "confirmation_required": True}, "review_ready"
    )


def _investigate(store, item, provider, jev_provider=None):
    snapshot = CaseSnapshot.model_validate(item["data"]["snapshot"])
    with store._transaction() as db:
        programmes, status, epoch = store._inventory(db)
    search = evaluate_search(snapshot, programmes, search_status=status)
    selected = next(
        (candidate for candidate in search.candidates if candidate.state == search.state), None
    )
    question = next_question(selected) if selected else None
    result = {
        "search": search.model_dump(mode="json"),
        "next_question": question.model_dump(mode="json") if question else None,
        "mode": item["data"]["mode"],
        "registry_epoch": epoch,
    }
    final_state = (
        "partial"
        if search.state is None
        else "manual_review"
        if search.state == "conflicting_information"
        else "awaiting_evidence"
        if search.state == "missing_evidence"
        else "review_ready"
    )
    store.checkpoint_job(item, result)
    if item["data"]["mode"] == "jev" and status == "complete":
        if jev_provider is None:
            store.commit_job(item, result, "partial", error="provider_not_configured")
            return
        attempt_id = store.reserve_attempt(item)
        try:
            advice = jev_provider.review(item["data"]["approved_context"])
            store.settle_attempt(
                item, attempt_id, "success", "validated_native_decision", receipt=advice["receipt"]
            )
            result["jev_advice"] = advice
            if (
                advice["assessment"]["choice"] != search.state
                or advice["assessment"]["confidence"] < 0.7
                or advice["human_review"]["noul"] >= 0.3
            ):
                final_state = "manual_review"
        except Exception:  # noqa: BLE001 — never retry unknown-usage native decisions
            store.settle_attempt(item, attempt_id, "provider_error", "unknown_usage")
            store.commit_job(item, result, "partial", error="provider_error_unknown_usage")
            return
    if item["data"]["mode"] == "codex" and status == "complete":
        if provider is None:
            store.commit_job(item, result, "partial", error="provider_not_configured")
            return
        context = item["data"]["approved_context"]
        for retry in range(2):
            attempt_id = store.reserve_attempt(item)
            try:
                output = provider.generate(
                    prompt=(
                        "Evaluate only the supplied typed facts and programme excerpts. "
                        "Do not use tools, infer eligibility, write correspondence or invent citations. "
                        "Report disagreement/uncertainty for human review.\n" + json.dumps(context)
                    ),
                    schema=AgentAdvice.model_json_schema(),
                )
                if output.exit_code != 0:
                    raise DomainError("provider_failed", 503)
                advice = AgentAdvice.model_validate_json(output.text)
                families = {programme.family_id for programme in programmes}
                if advice.candidate_family is not None and advice.candidate_family not in families:
                    raise ValueError("unknown_candidate")
                pages = context["source_pages"]
                if any(not verify_anchor(anchor, pages) for anchor in advice.citations):
                    raise ValueError("unsupported_citation")
                store.settle_attempt(item, attempt_id, "success", "validated_advisory_result")
                result["agent_advice"] = advice.model_dump(mode="json")
                if (
                    advice.needs_human_review
                    or not advice.agrees_with_conditions
                    or advice.confidence < 0.7
                ):
                    final_state = "manual_review"
                break
            except (ValidationError, ValueError) as error:
                store.settle_attempt(item, attempt_id, "validation_failure", type(error).__name__)
                if retry:
                    store.commit_job(item, result, "partial", error="output_validation_failed")
                    return
            except (ProviderTimeoutError, TimeoutError):
                store.settle_attempt(item, attempt_id, "provider_timeout", "unknown_usage")
                store.commit_job(item, result, "partial", error="provider_timeout_unknown_usage")
                return
            except Exception:  # noqa: BLE001 — provider boundary preserves unknown-usage receipt
                store.settle_attempt(item, attempt_id, "provider_error", "unknown_usage")
                store.commit_job(item, result, "partial", error="provider_error_unknown_usage")
                return
    store.commit_job(item, result, final_state)


def run_once(store, *, parser=None, provider=None, jev_provider=None):
    item = store.claim_job()
    if item is None:
        return None
    try:
        if item["data"]["operation"] == "parse":
            _parse(store, item, parser or RestrictedParser())
        elif item["data"]["operation"] == "investigate":
            _investigate(store, item, provider, jev_provider)
        elif item["data"]["operation"] == "render":
            packet = store.render_packet(
                None, item["data"]["packet_id"], parser=parser or RestrictedParser(), job=item
            )
            store.commit_job(item, {"packet_id": packet["id"]}, "review_ready")
        else:
            raise DomainError("unknown_job_operation", 422)
    except Exception as error:  # noqa: BLE001 — durable job boundary preserves partial checkpoint
        code = error.code if isinstance(error, DomainError) else "worker_stage_failed"
        with store._transaction() as db:
            try:
                current = store._object(db, item["id"])
            except DomainError:
                return item["id"]  # Erasure won the race; no object may be resurrected.
            try:
                actor = store._job_actor(db, current)
            except DomainError:
                current["data"]["error"] = "authority_expired"
                self_state = (
                    "awaiting_authority" if current["state"] == "running" else current["state"]
                )
                store._update_object(db, current, state=self_state)
                return item["id"]
            result = current["data"].get("result", {})
            if item["data"]["operation"] == "parse":
                document = store._object(db, item["data"]["document_id"])
                document["data"]["error"] = code
                store._update_object(db, document, state="partial")
                if code == "parser_tool_response_invalid":
                    actor = store._job_actor(db, current)
                    case = store._case(db, actor, current["case_id"], "edit")
                    store._audit(db, actor, case, "validation_failure")
        store.commit_job(item, result, "partial", error=code)
    return item["id"]


def main():
    root = os.environ.get("REPAIRCLAIM_DATA_DIR")
    if not root:
        raise ValueError("Set REPAIRCLAIM_DATA_DIR")
    store = Store(Path(root) / "repairclaim.sqlite3")
    parser = RestrictedParser(
        mode=os.environ.get("REPAIRCLAIM_PARSER", "auto"),
        engine=os.environ.get("REPAIRCLAIM_CONTAINER_ENGINE", "docker"),
    )
    import pymupdf

    with pymupdf.open() as probe:
        probe.new_page().insert_text((50, 70), "RepairClaim parser startup fixture")
        try:
            parser.run("parse", probe.tobytes(), "startup-fixture.pdf")
            parser_ready = "1"
        except DomainError:
            parser_ready = "0"
    with store._transaction() as db:
        db.execute("INSERT OR REPLACE INTO rc_meta VALUES('parser_ready',?)", (parser_ready,))
    provider = None
    jev_provider = None
    if os.environ.get("REPAIRCLAIM_ENABLE_JEV") == "1":
        from repairclaim_api.jev import JevGateway
        from repairclaim_api.jevmodel import JevModelProvider, route_config

        destination, _ = route_config()
        factory = JevModelProvider if destination == "jevmodel.org" else JevGateway
        options = (
            {"token_limit": int(os.environ.get("REPAIRCLAIM_JEVMODEL_TOKEN_LIMIT", "90000"))}
            if destination == "jevmodel.org"
            else {}
        )
        jev_provider = factory(
            os.environ["JEV_API_KEY"], os.environ["REPAIRCLAIM_JEV_BUDGET_DB"], **options
        )
    if os.environ.get("REPAIRCLAIM_ENABLE_CODEX") == "1":
        from agent_core.codex_local import LocalCodexProvider

        provider = LocalCodexProvider(
            timeout_seconds=120, isolated=True, config_overrides=("features.shell_tool=false",)
        )
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    next_tick = 0
    while not stopping:
        with store._transaction() as db:
            db.execute(
                "INSERT OR REPLACE INTO rc_meta VALUES('worker_heartbeat',?)", (str(store._now()),)
            )
        if time.monotonic() >= next_tick:
            store.tick()
            if os.environ.get("REPAIRCLAIM_ENABLE_SOURCE_CHECKS") == "1":
                store.check_sources(parser=parser)
            next_tick = time.monotonic() + 60
        if run_once(store, parser=parser, provider=provider, jev_provider=jev_provider) is None:
            time.sleep(0.25)


if __name__ == "__main__":
    main()
