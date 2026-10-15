# Building a ReAct agent that can admit its investigation is incomplete

*Day 3 of our 14-day AI product challenge: PropertyBrief, a public-record diligence workspace. This is a draft for publication, not a production launch announcement. Results below were measured during implementation on 14–15 October 2026.*

An acquisition analyst does not need another chatbot that confidently summarizes a building. They need to know what the records say, which property those records actually describe, and what to ask the seller, inspector or attorney next.

That is the product hypothesis behind PropertyBrief. An analyst creates a NYC property case, confirms its official building identity, and asks a diligence question. The application investigates public housing/building records, produces cited findings and a prioritized follow-up plan, and keeps uncertainties attached through review and export.

The intended buyer is a small residential acquisition team or buyer's broker. We have not established paid demand, pricing or time savings. A useful workflow is the first step toward validating a product—not proof of a business.

## An agent loop, not just a chat screen

[ReAct](https://arxiv.org/abs/2210.03629) interleaves decisions, actions and external observations. In PropertyBrief, application code owns that loop.

The worker observes captured evidence and coverage, asks for one structured next action, validates it, executes a read-only source query or record inspection, and persists the result. The next decision includes a concise reflection on what changed. We store useful action summaries, not private chain-of-thought.

Eight official record sources form a mandatory checklist: HPD violations, complaints/problems, repair/vacate orders, underlying conditions and alternative enforcement, plus DOB complaints, violations and ECB records. Building records resolve identity. The model can choose source order and relevant inspections/comparisons; it cannot invent endpoints, run arbitrary SQL or decide to investigate another building.

That boundary matters. The model proposes a next step. The application decides whether the step is valid, affordable and within scope.

## The first hard problem was identifiers

We acquired a frozen development corpus from [official NYC Open Data](https://data.cityofnewyork.us/): 12 buildings across all five boroughs, 3,346 source records, and metadata for ten registered datasets. Raw payloads, queries, timestamps and hashes remain available locally for replay.

The data exposed a bug that a polished fictional demo would have missed. DOB violations can match the confirmed building's BIN while retaining an older parcel number. Our current-parcel-only filter omitted legitimate historical records. We changed it to prefer the confirmed BIN and use parcel fallback for missing-BIN rows, preserving historical parcel differences as flags.

There was also a format trap: DOB query lot values use five digits, while the lot component embedded in a BBL uses four. Both look like reasonable identifiers. Only one matches the actual source query.

Another source could match an HPD building ID but disagree in BIN/BBL. We did not silently drop the row or pretend the disagreement was resolved. We preserved it, flagged the conflict and marked affected coverage unknown.

Of the corpus's 96 source checks, 91 completed for their executed queries and five remained unknown. Unknown is not “no issues.” An empty successful query is not a safety certificate either.

## Structured output was necessary—and insufficient

Every model decision and report crosses a strict Pydantic boundary. We derive JSON Schema from the contracts, then specialize the allowed tools, record IDs and citation field names using captured evidence.

That last part came from a real failure. A model may write a plausible generic `status` citation when the dataset's field is actually `ecb_violation_status`. We now constrain generation to the source's actual fields, then independently verify every cited source/row/field/value tuple.

We also had to make confirmed identity citable. The official building row now has its own snapshot and appears in the report manifest alongside investigation sources. A model-created `identity` source alias is rejected.

Still, exact citation equality does not establish that the surrounding prose is justified. A real field can support an overbroad interpretation. Schema validity, provenance integrity and semantic adequacy are different checks.

## Self-critique needs the right evidence

After synthesis, a separate call challenges the candidate's identity, status language, scope, coverage and proposed follow-ups. It can identify unsupported finding IDs, request revision or declare insufficient evidence. Rejected findings and dependent tasks are removed; a bounded conservative revision may follow. Unresolved objections keep the report partial.

The critic must see the candidate's cited rows, not an unrelated initial sample. We added explicit citation-priority context and reject a passing assessment when cited evidence cannot fit the context allowance.

We also learned not to confuse prompt sampling with missing source data. A row absent from the critic's prompt can still exist in the stored snapshot. Citation review cannot establish exhaustive material-finding recall; that remains an independent evaluation task.

Same-model critique is useful feedback, not expert certification. We have no calibrated critique precision/recall score yet.

## A tool result can succeed while the next prompt fails

One of the most instructive bugs was in context allocation. The agent requested inspection of captured records, and the application selected them—but a small per-source prompt allowance could omit those same records again. The model repeatedly asked to recover evidence the application already held.

Empty sources made this worse by consuming a share of the row-text allowance despite having no rows to show.

We wrote failing regression tests. Inspected sources now get priority; empty sources no longer reduce nonempty-source allowance; any requested rows still omitted are counted explicitly. In a real recovery trace, the planner subsequently recognized both property records and zero omitted inspection rows.

The later report call timed out. That distinction is important: the context fix worked, but that investigation still did not produce a successful complete narrative.

## Budgets are enforced by code

The loop has independent action, model-call, HTTP-attempt and wall-clock limits. The starting grant permits 16 actions, 24 model calls and 48 worker HTTP attempts, with a default 900-second deadline. Planning reserves a finalization allowance rather than using every call for exploration.

Retries and malformed output consume budget. Repeated actions stop. Crash recovery retains the original deadline and counters. Explicit resume permits one further bounded grant, not unlimited retries disguised as fresh attempts.

Persistence is part of the agent design. SQLite WAL stores observations, events, reports and exports. Lease fencing prevents stale workers from publishing over recovered work. Idempotency keys handle repeated browser requests, while revision checks prevent silent reviewer overwrites.

## Partial work must remain useful

After each valid observation, the application can display a deterministic preview without another model call. If planning, synthesis or critique fails later, saved evidence survives. The failed stage gets an event and the run gets a qualified stop reason.

A human can review and export a partial pack with explicit acknowledgment. Coverage gaps, acquisition times, critique status and source hashes remain attached. A later recovery creates another report revision without erasing the previous one.

This is graceful degradation. It is not permission to label an incomplete investigation successful.

## What testing actually showed

The final implementation passed 153 Python tests across the monorepo, including 59 PropertyBrief tests, and four frontend presentation tests. TypeScript, the production web build and lint passed. We verified the authenticated HTTP workflow from actual identity resolution through source acquisition, review/export and a persistent follow-up. Backup/restore preserved the current store's cases, runs, snapshots, reports and exports.

The model results were less tidy. The first ten initial frozen-source investigations all remained partial, with provider failures, rejected arguments, citation problems or critique objections. We preserved them while fixing the issues they exposed.

The final small actual-data case completed all eight required checks in 181.32 seconds, using eight actions and 11 model calls. It produced four findings with 23 exact field references and a passing advisory critique. It treated a historical electrical complaint as a complaint, distinguished occupant-reported correction from present physical condition, and proposed concrete seller, inspector and document-verification steps.

Across that development series, the result was one completed investigation and ten partial investigations—not eleven passes. Different code/corpus revisions and repeated properties mean this is not a controlled failure-rate benchmark. One successful sparse case does not establish reliability for dense, conflicting property-record packs.

## Why this is still a pilot

PropertyBrief has a working API, conversational reviewer interface, worker, evidence validation and export workflow. It is intended to run as a service on an old Windows laptop behind protected Cloudflare access. AI generation goes through the installed Codex CLI adapter, not a direct model API in product code; Codex still needs network and authentication for inference.

Windows startup, reboot, resource use and protected tunnel behavior still need target-host testing. The supported browser tool was unavailable during this session, so we have not claimed a visual, accessibility or full browser-interaction pass. A successful frontend build is not premium-UI acceptance.

We also still need independently adjudicated quality labels, repeatable dense-case completion, simpler workflow baselines and paired analyst-effort measurements. Public records do not establish title, current building safety, repair cost or investment suitability. Those are outside this release's promise.

The lesson from Day 3 is not that an agent becomes trustworthy when it can explain itself. It becomes more inspectable when identity, execution limits, evidence, critique and failure recovery are enforced independently of its prose. Whether that inspectable workflow delivers enough customer value is the next experiment.

*Implementation evidence, failed-session references and reproduction commands: [validation report](validation-2026-10-15.md). Learn the concepts through the actual code: [study guide](study-guide.md). Nothing in this draft has been published externally.*
