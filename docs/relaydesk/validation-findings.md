# RelayDesk validation findings

Current disposition (17 October): **release remains blocked; corrective engineering fixes are implemented and revalidated.** The user authorized fixes after the original test-only findings. The failure descriptions below are retained historical reproductions, not assertions that every defect is still present. [Original measured report](aggressive-validation-2026-10-16.md), [corrective report](corrective-validation-2026-10-17.md), [regressions](../../tests/test_relaydesk_aggressive_regressions.py).

## Corrective disposition

| ID | Implemented mitigation and current evidence |
| --- | --- |
| RD-V001 | Transactional source-active/hash/revision/state recheck before vector publication; stale-batch regressions and corpus invariants pass |
| RD-V002 | Canonical source digest and exact-span validation at source reads, prompt/publication and backup/recovery boundaries; injected corruption rejected |
| RD-V003 | Store/backup bound to independent-ledger identity and per-store registration; wrong existing ledger rejected before restore copy; explicit legacy enrollment |
| RD-V004 | Removed naïve phrase ban in favor of exact attributed factual quotation and neutral server narrative; negative quotation regression passes |
| RD-V005 | Schema-valid unsupported paraphrases rejected; model narrative not factual authority. Human semantic/relevance/critical-fact quality gate remains open |
| RD-V006 | Serialized text/metadata budgets, at most eight omission samples plus count/hash/ledger reference, projected turn-only buffer; 10k summary 5,926 characters |
| RD-V007 | Active-question episode excluded; selected compression evidence joins citable pool; one original quote/source per factual claim; seven natural corpus live jobs have zero turn-source hits |
| RD-V008 | Authorized batched vector access and call-local matrix scoring; 10k probes 217.84/216.22 ms on macOS, not target Windows acceptance |

Seven original defect regressions now pass without expected-failure markers. Seven additional corrective tests cover narrative isolation, CRLF offsets, nested buffer artifacts, migration, ledger replacement and corrupt-source publication. The first complete post-fix Python run reports 283 passed. Eleven frozen-build live jobs complete the AI stage with attributed quotations; this is not independently measured answer accuracy.

Residual boundaries: exact quotation does not establish truth, applicability, relevance or completeness; an identity binding cannot prove freshness of a stale same-identity ledger clone; historical retrieval may degrade at model egress for inactive source revisions. Full independent quality, browser, Windows and customer-usefulness gates remain open.

## Original findings and reproductions

| ID | Finding | Priority / impact |
| --- | --- | --- |
| RD-V003 | Restore accepts an unrelated existing erasure ledger | P0 privacy/recovery: later erasures can be resurrected under a plausible operator path mistake |
| RD-V007 | Current question retrieved as supporting evidence; real claims cite it | P1 grounding: valid IDs do not lead to the actual supporting record |
| RD-V005 | Fabricated outcome with an allowed citation passes structural validation | P1 quality gap: semantic support is not established, despite AI-stage completion |
| RD-V002 | Corrupted source body can be cited under its original hash | P1 integrity: source corruption is not rejected before evidence presentation |
| RD-V006 | Omitted-ID metadata exceeds the entire model-context ceiling | P1 availability: large histories cannot reach the AI reply stage with this summary representation |
| RD-V004 | Negated verification language triggers the unsafe-phrase ban | P2 availability: legitimate qualified answers consume repair attempts and fall back |
| RD-V001 | Source edit does not fence late old-source vector publication | P2 index correctness: stale rows can be written; normal current recall still filters superseded records |
| RD-V008 | 1k/5k/10k recall misses the provisional 500-ms target | Capacity gate: 10k measured at 5.7–7.2 seconds on macOS; not Windows acceptance |

Priorities are engineering triage, not CVSS scores or claims of a remote exploit.

## RD-V003 — wrong ledger accepted

Take a valid backup, erase a source using the correct ledger, create an unrelated valid store/ledger, and restore the old backup using that unrelated ledger. Restore succeeds and the erased text is present. Missing-ledger checks work; identity/currentness checks for an unrelated existing ledger do not.

Affected boundary: `backup.restore`, `Store.__init__/reconcile_erasures`. Required direction: bind a store to a stable independent-ledger identity, validate it before exposing restored data, handle migration explicitly, and fail closed on mismatches. Keep the current ledger outside ordinary restorable snapshots. Preserve the existing correct-ledger restore success case.

## RD-V007 — self-citation

`Store.enqueue` immediately stores the current question as a proposed episode. `RecallEngine.search` then retrieves that exact question at high similarity; it can be the only hit. The Reply schema permits its memory ID, and actual generated claims used it for facts drawn from other summary records.

Required direction: distinguish user intent from source evidence; prevent the active question from supporting its own answer; unify recall/compression evidence references so each typed claim identifies its actual supporting sources. Test natural examples and reviewer links, not only allowed-ID membership. Do not indiscriminately delete prior user-reported facts from long-term memory.

## RD-V005 — unsupported claim acceptance

A labelled controlled provider returned universal recovery/customer-confirmation claims with an allowed memory ID. The worker accepted the structured answer. This is **not** a measured natural-model hallucination rate. It demonstrates that shape, enum, exact-source and selected phrase checks do not establish entailment.

Required direction: explicit claim-support/qualification review gates and independent labelled source-support evaluation; improve machine checks without claiming perfect automatic entailment. Preserve mandatory human review/export boundaries. A high semantic score or successful repair cannot supply missing evidence.

## RD-V002 — integrity mismatch

In an isolated store, mutate a source body without changing its stored digest. Retrieval returns the altered quote with the old hash instead of rejecting corruption. Reproduced with the genuine encoder over real payloads and a lightweight lexical regression.

Required direction: validate the canonical source digest and span/version dependencies at read, prompt, publish and recovery boundaries as appropriate. This is injected database corruption, not an observed unauthorized public API write. Do not confuse a structurally valid SQLite file with semantically intact source records.

## RD-V006 — summary metadata overflow

Compression budgets selected text but includes every omitted memory ID. Serialized summaries reached 186,068 characters at 5,000 objects and 366,025 at 10,000, exceeding the complete 48,000-character prompt/schema allowance before other context. No legitimate omission may be silently hidden to make the test green.

Required direction: bounded serialized accounting including IDs/metadata, compact coverage/ranges or paged omission-ledger references, preserved critical-item provenance, explicit partial states, and actual model-stage revalidation at scale. Keep full original history outside the prompt.

## RD-V004 — negation false positive

The safe statement “There is no evidence that tests passed” matches the same substring ban as a positive verification claim. Two replies are rejected and an AI fallback is published. A strict regression preserves this exact case.

Required direction: validate assertion/attribution/negation in context. Do not remove safeguards by simply accepting all verification phrases. Natural live rejections were stage-logged but their discarded raw responses were not retained; they cannot all be classified as this false positive retrospectively.

## RD-V001 — stale publication

Compute an old source's vectors, edit/import the source before publication, then finish the old batch. The memory is marked superseded but the publication predicate checks only revision, erased/suppressed state and source hash—not current source eligibility. Two/four stale chunks were published in the corpus/long reproductions.

Required direction: explicit current-versus-historical indexing semantics and source-active/supersession fences. Preserve legitimate historical recall deliberately. This finding does not establish a current-answer privacy leak: current retrieval filters superseded source state, and erasure-during-index protection is a separate boundary.

## RD-V008 — scale behavior

The bounded capacity fixture uses labelled replicas of actual payloads. At 1k, probes were 611–781 ms; 5k, 2.8–3.7 s; 10k, 5.7–7.2 s. SQLite remained structurally intact. Per-memory connection/query work is a likely contributor based on code inspection, not an isolated causal benchmark yet.

Required direction: profile authorized batched vector/source access, preserve pre-filter isolation and numeric validation, then repeat warm/cold and concurrent benchmarks with distributions on the target Windows laptop. Do not weaken scope filters to improve a timing number.

## Regression policy

Initially seven correctness/availability tests used `xfail(strict=True)` to expose known defects. After reproductions passed with `--runxfail`, those markers were removed; the tests are now ordinary mandatory regressions. Timing remains in reports rather than a hardware-flaky unit assertion.

Corrective runs preserve original failures and use fresh stores with unchanged product hashes throughout the final campaign. Same-corpus retesting is regression evidence, not a blind evaluation. Fresh acquisition expands the real inputs, but does not supply independent human labels or pass unavailable browser/Windows gates.
