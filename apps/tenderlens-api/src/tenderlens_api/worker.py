"""Durable extraction job runner."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from agent_core.codex_local import LocalCodexProvider
from agent_core.orchestrator import ExtractionFailed, ExtractionOrchestrator
from contracts.tenderlens import DraftBrief

from tenderlens_api.store import Store


def plan_chunks(store: Store, pages: list[tuple[str, int]]):
    """Keep initial model calls bounded by pages and extracted text size."""
    groups: list[list[tuple[str, int]]] = []
    current: list[tuple[str, int]] = []
    characters = 0
    for document_id, page in pages:
        size = len(store.page(document_id, page)["text"])
        if current and (len(current) >= 4 or characters + size > 12_000):
            groups.append(current)
            current = []
            characters = 0
        current.append((document_id, page))
        characters += size
    if current:
        groups.append(current)
    return groups


def merge_briefs(briefs: list[DraftBrief], fallback_title: str) -> DraftBrief:
    unique = {}
    for brief in briefs:
        for claim in brief.claims:
            key = (
                claim.kind,
                claim.value,
                tuple((c.document_id, c.page, c.quote) for c in claim.citations),
            )
            unique[key] = claim
    return DraftBrief(
        schema_version="1.0",
        title=briefs[0].title if briefs else fallback_title,
        claims=list(unique.values()),
        open_questions=list(dict.fromkeys(q for brief in briefs for q in brief.open_questions)),
    )


def run_once(store: Store, provider=None) -> str | None:
    run = store.claim_next_run()
    if not run:
        return None
    run_id = run["id"]
    provider = provider or LocalCodexProvider(command=os.getenv("CODEX_COMMAND", "codex"))
    try:
        pinned_hashes = json.loads(run["document_hashes"])
        documents = [
            document
            for document in store.documents_for(run["opportunity_id"])
            if document["id"] in pinned_hashes
        ]
        if len(documents) != len(pinned_hashes) or any(
            document["sha256"] != pinned_hashes[document["id"]] for document in documents
        ):
            raise RuntimeError("Pinned document set is missing or has changed")
        all_pages = [
            (document["id"], page)
            for document in documents
            for page in range(1, document["page_count"] + 1)
        ]
        unreadable = [
            f"{doc_id} page {page}"
            for doc_id, page in all_pages
            if store.page(doc_id, page)["quality"] == "needs_ocr"
            and not store.page(doc_id, page)["text"].strip()
        ]
        if unreadable:
            raise RuntimeError("Unreadable pages require OCR: " + ", ".join(unreadable[:10]))
        store.ensure_chunks(run_id, plan_chunks(store, all_pages))
        while pending := store.pending_chunks(run_id):
            chunk_key, pages = pending[0]
            store.touch_run(run_id)
            orchestrator = ExtractionOrchestrator(provider, store, store.add_event)
            try:
                brief = orchestrator.run(
                    run_id=f"{run_id}:{chunk_key}",
                    pages=pages,
                    prompt=(
                        "Extract tender obligations from these pages. Include only claims supported "
                        "by exact source quotes. For a deadline, retain the original text and avoid "
                        "guessing a timezone. Include buyer, procurement ID, scope, eligibility, "
                        "mandatory documents, technical requirements, evaluation criteria, "
                        "disqualifiers and financial terms when present."
                    ),
                )
            except ExtractionFailed as error:
                if error.stage == "provider_timeout" and len(pages) > 1:
                    store.split_chunk(run_id, chunk_key)
                    continue
                raise
            store.save_chunk(run_id, chunk_key, brief)
        merged = merge_briefs(
            store.completed_briefs(run_id), store.opportunity(run["opportunity_id"])["title"]
        )
        store.finish_run(run_id, merged)
    except Exception as error:  # noqa: BLE001 - job boundary must persist every failure
        message = f"{type(error).__name__}: {error}"
        completed = store.completed_briefs(run_id)
        if completed:
            partial = merge_briefs(completed, store.opportunity(run["opportunity_id"])["title"])
            store.finish_run(run_id, partial, status="partial", error=message)
        else:
            store.fail_run(run_id, message)
    return run_id


def main():
    parser = argparse.ArgumentParser(description="TenderLens extraction worker")
    parser.add_argument("--once", action="store_true", help="Process one queued run and exit")
    args = parser.parse_args()
    store = Store(Path(os.getenv("APP_DATA_DIR", "var/tenderlens")))
    if args.once:
        run_once(store)
        return
    while True:
        if run_once(store) is None:
            time.sleep(2)


if __name__ == "__main__":
    main()
