# Public-PDF evaluation — 12 October 2026

This is an exploratory engineering test, not a human-adjudicated quality benchmark or release sign-off. It ran against public UNICEF sources on macOS 15.7.3 arm64, PyMuPDF 1.28.2, Tesseract 5.5.3 and Codex CLI 0.160.0. Source bytes are gitignored; their URLs, SHA-256 values and page counts are frozen in [`public-evaluation-sources.json`](../../data/tenderlens/manifests/public-evaluation-sources.json). Live claim-level JSON is in the gitignored `var/tenderlens-evaluation/` directory on the test machine.

This is the historical pre-recovery baseline. For current implementation and retests, see [13 October validation](validation-2026-10-13.md).

## Corpus and deterministic checks

Three public opportunities supplied six PDF files (98 pages): Montenegro (2), Serbia (29), and Nepal (36-page RFP, 27-page ToR, 2-page evaluation annex, 2-page price annex). All six downloaded with verified checksums, opened, matched expected page counts, and ingested as extractable-text pages. The real-document regression tests now check the Serbian date disagreement and the Nepal procurement-reference disagreement. The Nepal public page also offers XLSX/DOCX attachments that this PDF-only test did not ingest, so the four-PDF pack is not the entire published procurement package.

## Live Codex results

| Input | Result | Time | Calls | Claims | Validation events | Observation |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Montenegro RFP, 2 pages | Draft | 83.5 s | 1 | 27 | 0 | Key deadline, 70/30 scoring, two references, EUR/no tax and 120-day validity present; all claims cited. |
| Serbia RFP, 29 pages | Failed | 295.3 s | 2 | 0 final | 0 | Chunk 1 succeeded in 115.3 s; chunk 2 exceeded the 180 s Codex invocation timeout. |
| Nepal four-PDF pack, 67 pages | Failed | 316.7 s | 2 | 0 final | 0 | Chunk 1 succeeded in 136.7 s; chunk 2 exceeded the 180 s timeout. |
| Nepal evaluation annex alone, 2 pages | Draft | 92.4 s | 1 | 22 | 0 | 70 technical points, 49-point threshold and registration document extracted; 21 verified claims, one unresolved; all cited. |
| Nepal evaluation + price annexes, 4 pages | Draft | 136.4 s | 1 | 28 | 0 | Both procurement IDs preserved and conflict surfaced in an open question. One uncited claim correctly marked unresolved. |

These are single runs, not p50/p95 latency or accuracy estimates. Claim counts are not scores. The orchestrator enforced Pydantic schema and exact quote/page membership on completed drafts, but semantic scoring here covered selected facts only; no two-reviewer gold labels exist yet.

## Material findings

1. **Long packs are not currently usable end to end.** Eight-page chunks can exceed the fixed 180-second provider timeout. A later chunk failure leaves no partial draft despite earlier chunks succeeding. The run records `RuntimeError: Codex invocation timed out`, but no event is added to validation history for this provider exception. This is a release blocker for typical RFP packs.
2. **Source conflicts are real, not hypothetical.** The Serbia document says `18 February 2026` in its special notes on page 7, but says `9 March 2026` on pages 7–8 for the deadline; page 7 also gives `5 March 2026` for clarification questions. The full live run failed before a final brief could be assessed for conflict handling. Do not silently choose one date.
3. **Cross-document mismatch was surfaced in a focused test.** The Nepal evaluation annex names `9205846`; the price annex heading names `9203888`. The four-page run retained both cited values and asked which procurement ID applies. The current reviewer UI does not prominently expose `open_questions`, so a user could miss this signal.
4. **Short-source behavior is promising but limited.** Montenegro did not invent a budget or promote encouraged UNGM registration into a mandatory condition. The isolated Nepal annex did not invent a buyer, deadline, or ToR contents. These checks do not establish recall or precision on a full tender pack.
5. **Browser validation remains open.** The in-app browser had no available connection in this session. API tests and a web build passed, but no visual/interaction acceptance was performed.

## Reproduce

```bash
.venv/bin/python scripts/fetch_public_evaluation.py
.venv/bin/pytest -q tests/test_public_evaluation_pdfs.py
.venv/bin/python scripts/benchmark_public_evaluation.py --case montenegro
.venv/bin/python scripts/benchmark_public_evaluation.py --case serbia
.venv/bin/python scripts/benchmark_public_evaluation.py --case nepal
.venv/bin/python scripts/benchmark_public_evaluation.py --case nepal --only-source nepal-evaluation
.venv/bin/python scripts/benchmark_public_evaluation.py --case nepal --only-source nepal-evaluation --only-source nepal-price
```

The live commands require an authenticated Codex CLI and network access. The Serbia/Nepal failures describe the 12 October configuration, not the newer checkpointed worker. Do not count them as passing tests. Before a release claim, complete live long-pack acceptance, surface source conflicts/open questions in the UI, create human-adjudicated labels, and rerun on the target Windows host.
