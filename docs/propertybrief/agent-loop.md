# ReAct loop and bounded execution

Status: implemented in [worker.py](../../apps/propertybrief-api/src/propertybrief_api/worker.py), with deterministic and actual-model evidence in [validation](validation-2026-10-15.md). ReAct means reasoning and acting; React is the frontend library. Behavior is controlled by application code, not a model's announcement that it followed an agent pattern.

## State carried between iterations

Each run carries a confirmed property identity, immutable case revision, investigation question, required coverage profile, evidence references, hypotheses, pending tasks, previous action/result, counters, and stop conditions. Conversation history supplies user intent; source snapshots supply authority. Only bounded history and selected evidence summaries enter model context. Full records remain available through typed inspection tools.

The visible decision summary explains which check was selected and why. Do not request or persist private chain-of-thought. Store concise hypotheses, expected observations, resulting revisions, and evidence links sufficient for audit.

## Iteration protocol

1. **Observe:** load the previous validated result and current coverage. Add deterministic counts and quality flags. Distinguish unavailable data from an empty complete result.
2. **Think:** obtain a schema-validated `AgentDecision` containing `action`, `tool`, concise `summary`, `reflection`, and `record_ids`. The first decision has no previous result. The generation schema restricts tool names and record IDs; dispatch separately verifies source-specific row membership.
3. **Act:** validate tool name, parameters, property identity, evidence scope, repeat signature, and budget in application code. Reserve counters and execute one allowed source query or record-inspection action.
4. **Reflect:** checkpoint the result; update deterministic coverage immediately. The next decision must account for the last result and may revise hypotheses or change tools. The final candidate includes reflection on the final observation before critique.
5. **Finish or continue:** accept `finish` only after coverage and evidence rules are checked. Otherwise return a bounded validation observation requesting a correction or stop with a qualified partial report.

Reflection can be part of the next structured decision; a dedicated model call after every tool action is unnecessary. Test reflection by changing a tool result while keeping initial input constant and verifying that the subsequent action/hypothesis changes appropriately.

The required sources form a coverage checklist, not a predetermined action script. The agent selects order, relevant captured-row inspections and comparisons. Query scope and filters are compiled by the application from confirmed identity, not chosen freely by the model. For example, water-related evidence may promote the underlying-condition check; conflicting identity or dates should promote verification. When it fails to cover a source, the controller reports that gap rather than fabricating success.

## Tools and restrictions

| Tool | Responsibility |
| --- | --- |
| `resolve_property` | Return candidates from official building records; resolution happens before factual investigation |
| `fetch_hpd_violations` | Acquire property-scoped violation records and source status |
| `fetch_hpd_complaints` | Acquire complaint/problem records with separate identifiers and statuses |
| `fetch_vacate_orders` | Acquire orders and flag invalid/missing date relationships |
| `fetch_underlying_conditions` | Check recorded program participation/status |
| `fetch_aep` | Check recorded alternative-enforcement participation/status |
| `fetch_dob_complaints` | Acquire complaints using confirmed building identity |
| `fetch_dob_violations` | Acquire violations and preserve disposition/identity conflicts |
| `fetch_dob_ecb` | Acquire ECB records with separate hearing/certification/payment fields |
| `inspect_records` | Read selected rows/fields from snapshots already supplied to the run |
| `compare_evidence` | Compare typed dates/status/identity observations with explicit evidence references |

The tool names above describe responsibilities; runtime decisions use `action=query` with registry keys `hpd_violations`, `hpd_complaints`, `vacate`, `underlying`, `aep`, `dob_complaints`, `dob_violations`, `dob_ecb`, or `action=inspect/compare`. Resolution happens via the API before a run. Registrations have a registered dataset definition but are not automatically queried during current identity resolution. Tools are read-only; application code persists results/events. The planner never supplies arbitrary URLs, SoQL, filesystem paths, Python or shell commands. Source descriptions are untrusted data and cannot add tools or alter policy.

## Starting budgets

These are implemented fixed policy limits, not environment-tunable values or response-time promises.

| Resource | Hard limit per budget grant |
| --- | --- |
| Tool/action attempts | 16 query/inspect/compare dispatch attempts; identity resolution happens before enqueue |
| Model invocations | 24 total, including planning, repair, synthesis, and critique |
| Reserved finalization allowance | 3 of the 24 calls: synthesis, critique, and one shared repair |
| Run wall-clock time | 900 seconds from first worker claim; queue wait reported separately |
| Model invocation timeout | Smaller of 120 seconds and remaining wall-clock allowance |
| HTTP attempts | 48 worker acquisition attempts, including metadata, pagination and retries; identity lookup has its own bounded client |
| HTTP timeout | Smaller of 15 seconds and remaining allowance |
| HTTP retries | At most 1 per failed request, counted in 48, only for eligible transient read failures |
| Pages per source query | 10 pages, initially 1,000 rows each; any cap sets `truncated` |
| Response bytes | 2 MiB per response; 20 MiB acquired bytes per run |
| Model evidence context | 20,000 source-text characters per call plus bounded metadata |
| Conversation context | Last 6 messages, at most 8,000 characters; immutable earlier reports remain accessible |
| Repeated actions | Stop dispatch after 2 identical signatures without new evidence or a transient-failure rationale |
| Critique revision cycle | At most 1, using remaining global action/model/time budgets |

Initial mandatory coverage has eight source checks. Query/inspect/compare actions share the 16-action limit; invalid structured decisions consume model calls but never dispatch. A paginated query consumes one action and multiple HTTP attempts. Source caps and byte/HTTP limits may prevent completion: show the gap, not a false no-result. Fetching selected older records does not establish current open-record coverage. The 20 MiB counter is process-local and resets on worker restart/new grant; persisted HTTP/action/model counters do not. It is not a lifetime case-download cap.

Reserve finalization calls before exploratory planning. Do not borrow them for more exploration. Provider retries and malformed output consume calls even when they do not advance the step number. A malformed decision gets at most one repair for that decision, subject to the global cap. Maintain separate counters for action attempts, completed observations, model calls, and HTTP attempts so logs cannot hide work in an “iteration.”

Use a monotonic deadline within a process and persisted UTC start/deadline across restart. Crash recovery cannot reset that deadline. An explicit user resume creates an auditable new budget grant; prior counters remain visible. Fixed cumulative ceilings are 32 actions, 48 model calls and 96 HTTP attempts, across at most two grants per run. Further work requires a new investigation run. Resume idempotency prevents duplicate grants.

## Self-critique

Before finalizing, supply the candidate findings, source coverage, and evidence map to a bounded critique call. Require:

- Unsupported or overbroad finding IDs and the exact missing evidence.
- Property identity mismatches, parcel/building scope mistakes, and unresolved candidates.
- Closed/historical records described as current, or complaints described as verified violations.
- Missing required checks and incomplete pagination presented as complete.
- Contradictory dates/statuses and source freshness problems.
- Follow-up tasks that fail to address the observed uncertainty or imply unsupported repair/legal conclusions.

Application validators independently enforce reference identity, source-status mappings, coverage, and budget limits. Model critique is advisory evidence assessment, not proof. A critique can trigger one bounded revision/recheck cycle. Remaining unresolved objections stay in the report; a failed critique never produces a “critique passed” label.

The report-generation schema specializes evidence references per captured source: allowed source key, actual row IDs and actual field names. An independent validator then checks the exact row/field/value tuple, task finding IDs and conservative status/scope rules. The critic receives the candidate's cited rows, not just an unrelated initial sample. If cited rows exceed the 20,000-character allowance, omitted-row accounting forces an `insufficient` critique. Same-model self-critique is not independent human validation. A revised candidate remains partial unless a later investigation earns a passing assessment; the revision is not silently treated as re-criticized.

Normal planning context allocates row space fairly across nonempty sources; empty checks retain metadata without reducing row allowance. After `inspect`, that source is processed first and receives half the remaining evidence allowance (all of it if it is the only nonempty source), with requested rows sorted first. `inspection_rows_omitted` explicitly reports requested rows still too large to include. This fixes a live-observed failure where inspection selected nine rows but the next prompt still showed just the original sample. Other sources retain metadata and the remaining shared allowance.

## Graceful degradation and recovery

After every successful observation, publish a deterministic preview containing the identity, source coverage, source-derived counts/statuses, conflict flags, and unresolved checks. It requires no model call. Label it “Recorded observations; narrative review pending.” This is the fallback if no validated narrative exists.

If planning, synthesis, critique, source acquisition, cancellation, or deadline handling stops the run, finalize from the latest validated checkpoints. A partial narrative may be retained alongside deterministic observations, but unsupported claims never enter either report. Preserve a final stop reason and an event for the failed stage. In particular, a later timeout must not erase earlier findings or exist only as a top-level run error.

On worker restart, fence the old lease, load checkpoints and original deadlines, reuse published evidence, and account for already reserved attempts. A request with no saved result can be replayed within the remaining budget. A resumed refresh creates a new snapshot rather than modifying reviewed evidence. Terminal storage failure may prevent new persistence; surface an operational error and preserve the last durable preview.

## Required behavioral evidence

Deterministic tests prove cap enforcement, no repeated-action spin, source-scope enforcement, checkpoint reuse, deadline propagation, and partial preservation. Scripted provider traces demonstrate data-dependent branching without pretending to measure real model quality. Actual Codex runs over frozen official records must separately show meaningful action selection, reflection, critique, and graceful partial output. Record full safe action traces and unsuccessful runs in the evaluation report.
