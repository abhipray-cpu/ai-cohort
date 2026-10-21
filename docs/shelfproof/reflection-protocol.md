# Bounded execute–evaluate–reflect–regenerate protocol

Normative protocol, now implemented and engineering tested. See
[implementation notes](implementation-notes.md) for exact names and decisions.
Distinct revision identity is preserved even when text hashes are identical;
a revision is not free budget. Reflection does not alter model weights.

## Inputs and immutable authority

One row task binds workspace, source/import revision, mapped fact-pack hash,
optional existing draft, channel profile, brand brief, rubric, code/prompt/schema
versions, actor authority and source/egress grant. Input defects are not solved
by generation. Contradictory identity, unsupported scope, ambiguous nutrient basis,
unreviewed mappings and missing required data stop as `needs_data` or `out_of_scope`.

The model sees only approved facts and relevant brief/rules. It has no shell, web,
file, PIM, retailer-write or source-edit capability. Source text and draft content
are untrusted data, never policy instructions.

## States and stages

Task states: `queued`, `running`, `review_ready`, `needs_data`, `manual_required`,
`cancelled`, `stale`, `failed`. These are not publication states. A batch aggregates
row states without calling every terminal row a success.

1. **Execute:** `draft:0` produces title/description plus a bounded claim-to-fact map.
   In repair mode the imported copy is immutable version 0; no producer call is
   charged merely for reading it. Generation and repair cohorts stay separate.
2. **Evaluate:** deterministic checks run first, then `judge:0` independently inspects
   the entire draft, supplied facts, check results and fixed rubric. Persist both.
   Producer and judge receive the same immutable channel-profile constant. The
   independent judge does not receive producer reasoning or previous/desired scores.
   Evidence offsets use Unicode code points with an exclusive end; optional
   quote/start/end must all be null or exactly match the stated draft field.
3. **Stop if appropriate:** sufficient current quality and no blockers -> `review_ready`;
   missing source -> `needs_data`; invalid/unavailable judge -> `manual_required`.
4. **Critique reasoning:** `reflect:1` returns a concise finding-bound correction plan.
   Require references to every blocking finding, proposed operation and fact constraints.
   This is observable task rationale, not private chain-of-thought or a new authority.
5. **Regenerate:** `draft:1` uses the frozen facts, prior version and validated plan;
   the model may alter copy only. The controller—not the prompt—enforces the scope.
6. **Re-evaluate:** deterministic checks and `judge:1` assess the candidate anew.
7. **Select:** apply the deterministic incumbent/nonregression policy below. A rejected
   candidate stays in history with its failure reason. Do not overwrite version 0.
8. If needed and allowed, repeat `reflect:2 -> draft:2 -> judge:2`, then stop. No third
   revision, invented replacement source, indefinite repair or silent new task.

Imported version 0 is not an agent-executed generation; the UI/report identifies
that distinction. Both modes exercise evaluation/reflection when defects warrant it.

A parse/semantic validation failure permits one bounded replacement attempt, not
another revision. The replacement prompt preserves the original context and adds
allowlisted repair guidance (including exact evidence-span rules), not rejected
raw output, exception text or private reasoning. Its own prompt/schema hashes and
charged call are recorded. A second invalid response remains manual review; no
partial invalid model response can become a successful stage checkpoint.

## Hard gates precede scores

Deterministic findings include invalid source references, quantity/unit/basis
changes, forbidden claim phrases, wrong identity, invalid length/encoding, source
coverage gaps and output/provenance violations. Rule IDs and severities are owned
by code. LLM findings cannot delete, downgrade or self-resolve these.

All factual statements must declare supporting fact references or be flagged.
Automated coverage checks are conservative, not a proof that every implicit claim
in natural language was detected. Unknown mapping/support is a review blocker.
No certification, dietary/allergen-free or health claims are generated in v1.

Passing technical checks means consistency with approved inputs within tested
scope, not food safety or legal correctness. See [rubric](judge-and-rubric.md).

## Incumbent and nonregression policy

Retain version 0 as the initial incumbent, including its invalid/manual status.
For each evaluated candidate:

- Reject adoption if a new critical/material defect family appears, evidence
  coverage decreases, a source fact changes or an evaluation is missing/unassessable.
- Require mandatory finding coverage in the plan. `needs_data` findings cannot be
  “fixed” by asserting a missing fact, dropping a required disclosure or weakening rules.
- Among nonregressing versions, prefer fewer unresolved critical findings, then
  fewer material findings, then greater required-attribute coverage, then rubric score.
- A score-only adoption needs at least five score points; ties keep the incumbent.
  Cosmetic rewrites are not measured factual improvements.
- Finding comparisons use controller-defined defect families/targets, not arbitrary
  model IDs or similarity of explanation prose. Recompute checks on candidate text.

Eligibility for `review_ready` requires zero critical/material blockers, complete
required coverage, current known/audited runtime and a fully assessable rubric score
of at least 80/100. These are initial policy settings, not calibrated accuracy claims.
If iteration two ends below that bar, retain the best visible draft as `manual_required`
or `needs_data`, never relabel it passed. A healthy earlier eligible version may
remain `review_ready` with an explicit later-attempt failure/incident warning; no
unreviewed replacement or concealed unknown liability is permitted.

## Call, repair and scheduling bounds

| Allowance | Planned invariant |
| --- | --- |
| Revisions | At most two after version 0 |
| Normal generation calls | 8: initial producer + judge, then two plan/producer/judge triples |
| Normal repair-mode calls | At most 7: imported version 0 needs no producer call |
| Schema/evidence repair | At most one extra invocation per stage; does not add a revision |
| Absolute row cap | 16 invocations including malformed/failed/interrupted calls and restarts |
| Per invocation | 90-second deadline; pre-dispatch reservation |
| Charged time | At most 1,440 seconds per row; unknown call retains full reservation |
| Wall/claims | 30-minute initial wall window, at most four worker claims |
| Concurrency | One active provider invocation globally per ShelfProof store |
| Batch/campaign | Explicit cumulative call/row/deadline grant checked atomically before dispatch |

An expired wall window may receive a separate bounded owner resume window, not
new call/charged-time/claim allowances. Queue waiting cannot spend model calls;
admit only a small bounded batch and assign a row's wall window when it is claimed.
Queued rows recheck current rights/deadline before being claimed. Batch expiry
never extends because a laptop slept.

Schema failures may use the one stage repair only when usage/tool audit are known.
Provider/auth/quota/unknown-tool failures are not parse repairs. They stop or hold
dispatch and retain usable artifacts. Safe resume rules are in [recovery](audit-and-recovery.md).

## Improvement events

Record stage request/hash, attempt ID, actual checkpoint provenance, before/after
version hashes, resolved/unresolved/new findings, adoption/rejection reason, score
delta, coverage change, calls, elapsed time and known/unknown usage. Model-reported
“I improved” is not a metric. Human edits become new explicit revisions requiring
reevaluation and authorization, never a hidden overwrite or budget reset.
