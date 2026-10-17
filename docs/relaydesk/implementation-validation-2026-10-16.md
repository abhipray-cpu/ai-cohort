# RelayDesk engineering validation — 16 October 2026

Historical initial smoke/engineering results. Subsequent [aggressive validation](aggressive-validation-2026-10-16.md) found release-blocking defects and scale failures; this earlier small run must not be used as current sign-off.

Implemented pilot evidence, not production certification or independent gold-set evaluation. The [earlier source-feasibility report](validation-2026-10-16.md) records the pre-implementation baseline. Timestamps below are UTC; the document uses the user-provided challenge date.

## Commands and retained artifacts

```sh
make relaydesk-test
.venv/bin/python -m pytest -q
.venv/bin/ruff check apps/relaydesk-api packages/contracts/src/contracts/relaydesk.py tests/test_relaydesk*.py scripts/*relaydesk*
.venv/bin/python scripts/validate_relaydesk.py --output var/validation/relaydesk-2026-10-16-implementation --live
.venv/bin/python scripts/validate_relaydesk_http.py --capture var/validation/relaydesk-2026-10-16-implementation/raw --output var/validation/relaydesk-2026-10-16-http.json
```

Ignored `var/validation/` contains immutable URL/time/hash captures, an independent validation database and reports. Nothing was written upstream. Public-message redistribution/retention requires separate review. Replay uses `--capture <raw-directory>` with a new `--output` path and no `--live` for offline source replay. No evidence files are silently overwritten.

## Actual data volume

Acquisition: `2026-10-16T16:47:25Z–16:51:15Z`. Bodies count as messages. “Human” below means provider-attributed non-bot, not guaranteed absence of AI-assisted writing.

| Public issue | Messages | Non-bot | Selected semantic hits |
| --- | ---: | ---: | ---: |
| [elastic/elasticsearch #90216](https://github.com/elastic/elasticsearch/issues/90216) | 10 | 10 | 3 |
| [microsoft/vscode #255749](https://github.com/microsoft/vscode/issues/255749) | 34 | 34 | 4 |
| [pallets/flask #1361](https://github.com/pallets/flask/issues/1361) | 58 | 58 | 7 |
| [pallets/flask #1575](https://github.com/pallets/flask/issues/1575) | 47 | 47 | 9 |
| [pallets/flask #1421](https://github.com/pallets/flask/issues/1421) | 44 | 44 | 7 |
| [fastapi/fastapi #1228](https://github.com/fastapi/fastapi/issues/1228) | 94 | 32 | 1 |
| [fastapi/fastapi #1663](https://github.com/fastapi/fastapi/issues/1663) | 91 | 90 | 10 |
| [fastapi/fastapi #1218](https://github.com/fastapi/fastapi/issues/1218) | 89 | 84 | 6 |
| **Total** | **467** | **399** | **47** |

All eight captures reported comment-counter correspondence, idempotent replay, full non-bot raw-episode indexing, exact selected quote spans, and unauthorized recall rejection. Listing discovery also queried PostgreSQL/Redis but selected no eligible issue bodies under the bounded rule: neither counts as a represented corpus repository. Four repositories, not six. Selected hits are not labelled relevant answers; 47 span checks are not 47 independent questions.

## Genuine semantic model

Local CPU `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. 384 float32 dimensions, attention-mask mean pooling then L2 normalization; 220-wordpiece chunks, ≤256 encoded tokens, batch ≤16, 2 intra/1 inter CPU threads.

- ONNX SHA-256: `6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452`
- Tokenizer SHA-256: `be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037`
- Run namespace: `c3d4942692999130c0bb51d04feb11a64d692577e813e7d51fb99015b8d74b85`

Controlled paraphrase “Credentials rejected during login” retrieves a persisted password/connection episode after store reopen with real embeddings; lexical-only recall returns no hit. This is narrow engineering evidence, not general recall accuracy. No remote embedding API or fabricated hash vectors.

## Live installed Codex

Two explicit-egress live jobs used the isolated installed adapter. Elasticsearch: two calls, AI-assisted **partial** handover. VS Code: two calls, extraction completed but reply timed out; source-linked **partial fallback**, **not an AI-answer pass**. Sources/proposed memories survived and the timeout/degradation events identify the failed stage. Neither job establishes verified technical resolution.

## HTTP acceptance

`16:58:48Z–16:58:50Z`: 19 checks passed against the built loopback service, with a dedicated account/case and ten-message captured Elasticsearch thread: static delivery; auth/session separation; import/replay; CSRF/origin guards; asynchronous semantic readiness; distinct interactive sessions; fresh-session semantic recall with zero model calls under denied egress; review/export limitations; revision-bound correction and stale concurrent-edit rejection; second-session latest revision; old-export blocking; test-user provisioning; other-user source/case rejection.

The test case remains inspectable in the workspace. Its final manual correction is a labelled HTTP validation proposal, not upstream evidence.

## TDD and regressions

Failing tests preceded fixes for correction-derived text surviving source erasure, stale generated context being relabelled current, missing historical request propagation, promoted-source output permission revocation, multibyte byte limits, model proposals being backdated into the past, and unaudited provider acceptance. Tests also exercise semantic persistence/paraphrase, invalid vectors, idle index progress, immutable corrections, queue fencing/reservations, later-stage timeouts and erasure reconciliation after restoring an old snapshot.

Final verification: **32 RelayDesk backend tests**, **3 RelayDesk frontend state tests**, and **261 full-monorepo Python tests** passed. Repository-wide Ruff and `git diff --check` passed; TypeScript/Vite production build passed. Existing ResolveDesk/PropertyBrief/PatchDesk frontend state suites passed (5/4/4 tests); TenderLens has no frontend `test` script, so no such suite is claimed. Existing PDF/HTTP dependency deprecation warnings remain. These are not browser-rendered component tests.

Final captured-data replay at `17:12:15Z–17:12:22Z` again processed all eight threads/399 non-bot messages with zero errors on the updated implementation, without upstream requests or Codex calls. Report: `var/validation/relaydesk-2026-10-16-final-replay/report.json`. After restarting the final service, all 19 HTTP checks passed again at `17:13:42Z–17:13:46Z`; report: `var/validation/relaydesk-2026-10-16-http-final.json`. Repeated runs are **not additional unique data**. Managed API/worker process identities were verified running after restart.

## Unpassed release gates

Browser selection returned `No browser is available`; discovery returned `[]`. No visual screenshots, keyboard/accessibility, responsive viewport or real two-browser acceptance is claimed. Windows service/reboot/Codex identity/Cloudflare, five-product old-laptop capacity, disk-full/ACL and process-tree drills remain unrun here.

The 200-thread/20-repository/5,000-message cohort, independent two-reviewer 300-question labels, calibration, blind held-out entailment/retrieval scores, full ablations and paid-pilot value remain **open**, without silently lowering [evaluation targets](data-and-evaluation.md).
