# Alternative source and real-data checks — 19 October 2026

Latest: [20 October measured continuation](real-data-continuation-2026-10-20.md)
completed all six approved development artifact sets. Five histories are fully
audited; one retains an owner-accepted unknown receipt. This does not expand source
or egress scope, certify UK/domain quality or erase the historical findings below.

20 October update: user approved six development excerpts; actual-model execution
ran two full protocols and one partial packet, then stopped on unknown usage with
three cases unstarted. See the [approved run and recovery finding](approved-real-data-run-2026-10-19.md).
Earlier approval-blocked statements below are the preserved source-preflight history.

**Actual corpus acquired and locally checked. Real-model E2E has not run:** the
environment safety review rejected sending actual complaint excerpts to the model
service without explicit approval of that payload/destination. No bypass attempted.

## Source decision and conditions

Selected: Ireland's Financial Services and Pensions Ombudsman (FSPO), under its
[published reuse policy](https://fspo.ie/governance/reuse.asp). It permits reuse free
of charge in any format, subject to attribution/copyright acknowledgement, accurate
and non-misleading reproduction, no principal advertising/promotional purpose and
no illegal/dishonest use. This records the operational basis for **private attributed
validation**, not bespoke legal advice, unrestricted commercial clearance or endorsement.
Originals remain outside the public repository and must not become promotional material.

[FSPO describes its decision publication as anonymised](https://fspo.ie/complaint-outcomes/investigation-services/).
Contextual dates, amounts and events may still carry privacy risk. Published reuse
permission and external-model egress permission are separate. Installed Codex can
perform remote inference; source approval does not itself authorize that transfer.

Alternatives checked: [AFCA's decision notice](https://www.afca.org.au/what-to-expect/search-published-decisions)
limits its general reproduction authorization to personal/non-commercial purposes;
it was not assumed sufficient for commercial-product evaluation. The [CFPB database](https://www.consumerfinance.gov/data-research/consumer-complaints/)
is actual complaint data but not UK motor-insurance adjudication evidence. Original
[UK FOS restrictions](https://www.financial-ombudsman.org.uk/legal-policy) remain
unresolved; no FOS decisions were acquired in this work.

## Actual inventory

Official [Insurance/Motor query](https://www.fspo.ie/complaint-outcomes/investigation-services/legally-binding-decisions/display.asp?sector=2&product=11&conduct=0&outcome=0&dyear=0&mypage=1):

| Measure | Observed |
| --- | --- |
| Listed / downloaded | **132 / 132** official PDFs |
| Volume | **1,552 pages**, 95,833,935 PDF bytes |
| Usable / excluded | **122 / 10** |
| Years of usable decisions | 2018–2026 |
| Source outcomes | 68 rejected; 23 upheld; 22 partially upheld; 9 substantially upheld |
| Frozen hash-based splits | **74 development / 25 calibration / 23 held-out** |
| Exact/cross-split near-duplicate flags | None flagged by mechanical checks |

Distinct source references are not proven independent disputes. Related-case and
temporal grouping require domain review. This is not a certified temporal holdout,
the 500-case target is not reached, and there is no synthetic top-up.

Current local corpus: `var/validation/casecouncil-fspo-2026-10-19-v3/`.
It contains original PDFs/text under `raw/`, listing/permission snapshots under
`metadata/`, attributed excerpts under `inputs/`, evaluator-only outcomes under
`gold/`, attribution, manifest and exclusion report. Its manifest hash is
`61edf6340208eef8f91926873deac5c6e6e00dcaf5f7a46f190a4242148264d5`.
**Current external-model egress is false.** v1/v2 remain historical preparation
artifacts, not authority to use a provisional egress flag. Source expiry/review
reference and model-egress approval must remain independently current.

## Extraction and leakage controls

Packets are exact excerpts after the official body heading and before the standalone
Decision section. Cover outcome/reference metadata and all subsequent adjudicator
reasoning are excluded. Both attributed party sections are required; suspected
preliminary/final-outcome leakage is excluded. Source hashes/extracted-text offsets
are retained. No invented policy, witness statement or draft response was supplied.

The first pass admitted 75 cases: wrapped headings and plural “Complainants’ Case”
were being rejected. A failing regression reproduced this; a parser fix prepared
122 cases offline, preserving the earlier version and originals. Final exclusions:
four unrecognized party sections, two ambiguous/missing decision boundaries, four
potential leaks pending review. One original first page was rendered and visually
checked for cover/body separation, not all 1,552 pages independently reviewed.

These are **Irish retrospective party summaries**, not UK original case files,
verified allegations or complete policy packs. Missing originals are explicit
blockers in every case. Low confidence and requests for evidence are expected;
manufacturing a qualified recommendation would be a failure. Whole-complaint source
outcomes are not independent issue-level gold. Pretraining contamination remains possible.

## Executed checks and limits

| Check | Result | Evidence |
| --- | --- | --- |
| Actual PDF intake/extraction | 132/132 | Original hashes and acquisition report |
| Source manifest/path/hash/split/leak checks | 122 eligible, no duplicate flags | Local corpus manifest |
| Local in-process API/protocol checks on actual excerpts | **122 passed, 0 failed** | `var/validation/casecouncil-fspo-offline-api-v2/report.json` |
| Final product regression | **91 passed, 0 skipped** | `var/validation/casecouncil-fspo-product-final.xml` |
| Intermediate monorepo regression | **623 passed, 0 skipped** | `var/validation/casecouncil-fspo-regression-v1.xml` |
| Final monorepo regression after egress-gate fix | **624 passed, 0 skipped** | `var/validation/casecouncil-fspo-regression-final.xml` |
| Real-case installed-Codex HTTP replay | **Not started; execution rejected by safety review** | Explicit payload/model-destination approval required |

The 122 corpus checks use an explicitly imported **authored stand-in provider**:
**zero actual model calls, zero real complaint egress**. They cover real excerpt
uploads/previews, IE scope, idempotent start, exact source quotes, three-role/critic/
ballot/consensus/synthesis plumbing, denominator three, retained evidence blockers,
low confidence, unapproved JSON/HTML exports, reviewed-export refusal and unauthenticated
denial. No automated actor is described as an independent human reviewer.

These are local in-process HTTP checks, not actual-model/browser E2E or semantic
accuracy. Held-out inputs were mechanically checked, not used for real-model tuning.
No target Windows/Cloudflare, customer pilot or independent domain review ran.
`full_product_accepted` remains false.

## Implementation and reproduction

- `fspo.py`, `scripts/acquire_casecouncil_fspo.py`: bounded official-host acquisition,
  attributed excerpts, hash/split/exclusion reports, offline new-version preparation.
- Normal Store/API reject IE intake/publication. Only explicit isolated research
  `evaluation_only=True` accepts IE; no normal-service environment switch enables it.
- Offline audit now separates source rights from external-model permission. Actual
  campaigns and the replay launcher fail before inference when egress is false.
- `scripts/check_casecouncil_corpus_offline.py` never invokes Codex. Its local-only
  simulated grant exercises mechanics without changing the corpus manifest.
- `scripts/replay_casecouncil_http.py` prepares an isolated real loopback API/worker
  campaign, frozen selection, receipts/progress and bounded calls; live step is gated.

```sh
.venv/bin/python scripts/check_casecouncil_corpus_offline.py \
  --corpus var/validation/casecouncil-fspo-2026-10-19-v3 \
  --output var/validation/casecouncil-fspo-offline-another-run
```

## Required approval / next phase

Approve sending the **six selected development party-summary excerpts**, excluding
final outcomes/full decision PDFs, through installed Codex to its configured model
service, up to **132 cumulative calls** (22/case including repairs). Contextual dates,
amounts and events may remain despite published anonymisation/best-effort redaction.
Keep originals and gold local. This is not approval for promotional redistribution,
an endorsement claim, an unlimited campaign or UK domain certification.

After approval: create a new approved manifest version, freeze code/profile/selection,
run the bounded six-case actual HTTP campaign, inspect all failures and receipts,
then scope expansion and baseline comparison. Do not bypass the rejected action
through another launcher. Study/blog follow actual validation, not ahead of it.
