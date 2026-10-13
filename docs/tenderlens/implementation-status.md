# Implementation status — 13 October 2026

This is a build status record, not a release sign-off.

## Implemented and verified locally

- Python 3.12 workspace, React/TypeScript web application, and local API serving the built UI.
- FastAPI opportunity/PDF/run/review/export routes with HTTP Basic authentication.
- SQLite document/page/job/claim/event/export persistence, stale job recovery, and durable per-chunk checkpoints.
- PDF text extraction, per-page source storage, tested Tesseract OCR path on this host, and explicit unreadable-page status.
- `LocalCodexProvider` invoking the installed CLI with a strict schema derived from Pydantic, read-only sandbox, temporary working directory, timeout, and final message file.
- Pydantic output and page lookup tool contracts, bounded parse/schema/evidence retries, and persisted validation failure events.
- Source citation verification, approval gate for uncited claims, and review values preserved separately from generated values.
- UI build, API HTTP response, 37 Python tests, Ruff lint, and one deterministic full API test, including an authenticated-PDF access check.
- Bounded four-page/12k-character initial chunks, adaptive split on multi-page timeout, durable checkpoint, partial read-only preview, same-run retry, and logged timeout/provider failures. Tests cover losing a later chunk, blocked partial review/export, same-run resume, and stale-worker recovery without regenerating saved chunks. The public benchmark harness now supports persistent evaluation sessions.
- Image-only scan test with embedded text confirmed absent; OCR recovered the technical-scoring text from a rasterized page of the public RFP. A separate self-contained OCR regression test now runs when Tesseract is installed.
- Live Codex schema smoke with TenderLens's Pydantic schema and one [public UNICEF RFP](https://www.unicef.org/montenegro/en/media/26051/file) run: 21 claims, 79.2 seconds, no validation failures; two source facts detected. See `data/tenderlens/manifests/seed-baseline.json`.
- A fresh three-opportunity, six-PDF public evaluation ingested 98 pages and ran live Codex on short and long inputs. Short inputs produced cited drafts; both full long packs timed out on chunk 2 under the original implementation. See [baseline findings](public-evaluation-2026-10-12.md) and [recovery follow-up](validation-2026-10-13.md).

## Still required before production release

- Human labeled, adjudicated corpus and held out metrics across native, scanned, and amended tender packs. Current seed facts are sanity checks, not gold labels.
- Browser visual/interaction checks and user usability sessions. Browser access was unavailable in this implementation session; TypeScript build and HTTP smoke passed.
- Full 67-page Nepal live draft and measured resource use. The 29-page Serbia pack did finish once with the recovery worker after a capacity-failed first invocation: 14 calls, 25.9 minutes, 291 cited claims. This is a functional completion, **not a quality pass**: 88 open questions include chunk-local false gaps, and `deadline` contains non-submission time periods. See the [follow-up](validation-2026-10-13.md).
- Prominent conflict and open-question display in the reviewer UI; the Nepal annex mismatch was detected by Codex but open questions are not prominently rendered.
- Larger scanned-document evaluation, including poor scans, multi-page packs, language variation, and measured OCR error rates. Tesseract is installed and one clean image-only scan now passes locally; this does not establish production OCR quality or Windows compatibility.
- Corrigendum precedence and organization profile fit assessment.
- Windows service account authentication, task/service packaging, restart/restore drill, and Cloudflare Access acceptance on the target laptop.
- Stronger user identity/roles, audit access control, and backup/restore automation.
- Page quote highlighting in the PDF viewer. The present UI navigates to the source page and shows the exact quote alongside it.
- Benchmark thresholds and latency measurements by document class; one successful run cannot establish quality or an SLA.
- Cross-chunk semantic reconciliation; the current merge deduplicates identical cited claims but can retain a question from one chunk that another chunk answers.
- Complete per-attempt telemetry for successful model calls, including CLI/model versions; the current event log concentrates on failures.

## Reproduce the current checks

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
npm --prefix apps/tenderlens-web run build
.venv/bin/python scripts/smoke_codex.py --brief
.venv/bin/python scripts/benchmark_seed.py
.venv/bin/python scripts/benchmark_public_evaluation.py --case serbia --session serbia-recovery
```

The last three commands require an authenticated Codex CLI and network access. The seed benchmark also requires the public PDF downloaded to the local path named in `data/tenderlens/manifests/seed-sources.json`. The Serbia benchmark requires `scripts/fetch_public_evaluation.py` first, can take multiple calls, and keeps an ignored SQLite session so a later invocation resumes pending work.
Use `.venv/bin/python scripts/fetch_seed.py` to fetch and verify that fixture on a new checkout.
