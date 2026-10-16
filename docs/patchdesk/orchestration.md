# Multi-tool orchestration design

Status: implemented pilot. The five concepts are enforced by application code, not merely named in a prompt. Broader requirements below remain targets where qualified; [validation](implementation-validation-2026-10-15.md) records observed evidence.

`registry.py` owns descriptors, pinned hashes, package filters and live enablement; `worker.py` owns scoped expansion/model requests; `scheduler.py` owns bounded DAG dispatch; `store.py` owns counters/checkpoints; `reconcile.py` owns deterministic decisions. Eight trusted installed adapters are registered; admin can disable/re-enable them live. Adding an implementation requires trusted code/deployment, not arbitrary plugin upload.

Current descriptors contain ID/version, capabilities, provider, optional package allowlist, permission, enabled flag, priority and schema version. Hosts/credentials/limits/semantics live in trusted adapter code. Health/cost-aware routing and automatic circuits remain targets. Current ranking is configured priority then stable ID, with server-only preferred providers for explicit comparisons.

## 1. Dynamic trusted registry

An installed adapter supplies a validated descriptor: stable ID/version, capabilities, ecosystem/input/output schema IDs and hashes, supported operations, required permissions, credential reference, effect kind, egress destinations, rate/concurrency policy and health state. Registration is an administrator-controlled operation over an allowlisted implementation, never model-generated Python, imported arbitrary modules or downloaded plugins.

At startup and approved configuration reload, build an immutable registry revision. Invalid/duplicate descriptors fail registration explicitly. Disabled or unconfigured adapters stay visible to administrators as unavailable; unauthorized users see only appropriately redacted capability availability. No secrets enter registry responses/model prompts.

A run pins its registry revision and descriptor hashes. Adding an adapter affects new runs, not silently changing old report provenance. Revocation/disablement can remove live eligibility from old runs. A changed implementation/schema requires a new version/revision, not mutation under the old ID.

Implemented reader capabilities and adjacent non-registry operations:

| Adapter | Capability | Required status / effect |
| --- | --- | --- |
| Uploaded snapshot parser | Local input operation, not routed | Required local read; authorized stored inputs only |
| Authorized GitHub content reader | `repository.snapshot.read` | Optional input connector; fixed configured repo/path/commit |
| OSV package/version client | `advisories.lookup`, `advisories.detail` | Required public egress for approved npm identities |
| GitHub reviewed/publisher readers | `advisories.detail` | Detail alternative; publisher adapter currently Axios only; imports not independent votes |
| npm metadata reader | `releases.lookup` | Required for supported candidate checks; no installs |
| deps.dev reader | `dependency.context` | Optional context; never substitutes the captured project graph |
| FIRST reader | `threat.epss` | Optional CVE enrichment |
| CISA KEV reader | `threat.kev` | Optional catalog; final live acceptance still open |
| Local reviewed-pack exporter | Separate API operation | Local persisted effect, revision-bound review required |
| Scoped GitHub issue publisher | Separate serialized publication API | Default disabled; exact approval and live authorization required |

At least two eligible detail providers should be implemented/tested to prove capability routing and safe failover, rather than renaming a fixed switch statement. Graph context and actual graph are different capabilities precisely to prevent a semantically invalid fallback.

## 2. Capability routing

The planner emits typed requests for a capability, input artifact/package/CVE IDs and task dependencies. Actor, project, registry, allowed egress and credential bindings are injected by the server, never trusted from model output.

Routing pipeline:

1. Validate request/schema, object ownership, supported ecosystem and dependency readiness.
2. Match registry descriptors by capability and contract semantics.
3. Filter by live permission, package-identity egress grants, credential availability, health and budget.
4. Rank eligible candidates deterministically: semantic suitability and configured project preference first, then compatible health/cache/cost/latency policy. No invented numeric confidence ranking.
5. Record selected adapter, descriptor/policy version and safe reasons for selections/rejections.
6. Recheck authorization before dispatch. If none qualifies, return typed denied/unavailable/unsupported, never broaden scope to make the call succeed.

Read failover may select a contract-compatible provider within the same allowed scope and remaining budget, recording separate provenance. It cannot bypass a permission denial, silently use stale evidence, send private names to public services or switch to arbitrary web search. Publication has no automatic provider failover.

## 3. Task DAG and parallel execution

Initial deterministic graph: input validation → inventory/graph → approved advisory/package-metadata fan-out → advisory detail/alias normalization → CVE threat fan-out → per-package reconciliation/candidate checks → maintenance plan → validation/review. The agent can request useful additional detail/candidate comparisons within this graph model; it cannot create cycles, change project scope or publish without approval.

Required capability coverage is enforced by the controller. Detect missing prerequisites and cycles before dispatch. A capability node can perform bounded batched I/O; a node is not necessarily one HTTP request. Only independent ready read nodes run concurrently. Model generation remains serial initially. Publication is a separate serialized outbox workflow.

Use a semaphore for global/per-provider concurrency and a bounded queue. Reserve task/HTTP/model attempts transactionally before work. Never enqueue every package into unbounded `gather`. Persist node results as each succeeds; publish a deterministic preview immediately. Sibling exceptions are converted to typed node outcomes and cannot discard earlier results.

Reduce results in a stable package/location/advisory order. Test with reversed completion order and duplicate deliveries: report assertions/conflicts must be equivalent, apart from timestamps/attempt metadata. Cancel unscheduled tasks promptly and allow in-flight read operations only their remaining timeout; persist cancellation/failure events.

## 4. Starting resource policy

These are implemented ceilings, not throughput measurements or independently configurable settings. The actual cohort exceeds some limits and remains partial.

| Resource | Implemented limit per run grant |
| --- | --- |
| Active investigation runs | 1 per pilot instance |
| Ready/in-flight read nodes | 4 globally, 2 per upstream provider |
| Model calls | 8 including repairs; normally 2 stages, each repaired at most once |
| DAG nodes / expanded tasks | 128 maximum; requests coalesced by typed identity |
| HTTP attempts | 128, including pages, retries and metadata |
| Retry policy | One eligible transient read retry, bounded backoff and `Retry-After`; no generic write retry |
| Run deadline / model timeout / HTTP timeout | 900 / 120 / 20 seconds, each capped by remaining deadline |
| Input / response / acquired source bytes | 10 MiB per input file / 4 MiB per HTTP response / 64 MiB per grant |
| Inventory | 5,000 location entries, 2,000 public package/version queries per grant; unsupported/capped remainder visible |
| Advisory detail / source paging | 60 records / 10 pages per paged operation, subject to HTTP budget |
| Metadata/enrichment | First 12 installed release lookups, 8 CVEs, 16 fixed-version targets; caps explicit |
| Context | Samples of 40 packages/60 advisory IDs/30 CVEs for planning, 30 findings/20 conflicts for narrative; findings reduce to 10 when context exceeds 20,000 characters. Not a universal token-limit guarantee |
| Queue | 20 pending investigations |
| Resume | At most 2 grants per run, cumulative task/HTTP/model ceilings twice the initial grant |

The model need not choose one tool per package. Parse/match/collate deterministically; use AI for bounded capability planning and qualified explanation. A 1,204-entry lockfile must not cause 1,204 model calls. Preserve full evidence outside prompt samples and account for omitted/capped data separately.

Budget exhaustion stops new exploration, finalizes from captured evidence and records a stage event/partial reason. Crash recovery retains original deadlines and reserved counters. Resume is explicit, idempotent and auditable, never an unlimited hidden retry loop. Do not automatically replay an unknown-outcome write on restart.

## 5. Conflict resolution

Conflicts are structured records, not prose the model can silently smooth over. Implemented range disagreements retain source memberships and `needs_investigation`; unsupported/withdrawn records become unknown. Declared-range/engine checks and peer-verification-pending are separate candidate checks, not a full peer solver. Broader identity/policy/staleness taxonomy remains a target; gaps retain unavailable evidence.

Normalize aliases within ecosystem/package context, preserving every source assertion and upstream lineage. OSV importing GitHub data does not supply two independent votes. Separate 0.x/1.x fixed branches and separate CVSS metric/version from EPSS likelihood. Dependency location determines which installed instance is affected.

The reducer applies a versioned policy. On unsupported range syntax, missing source detail or irreconcilable affected ranges, mark `needs_investigation`; a conservative alert may remain without claiming confirmed application exploitation. Do not claim a candidate resolves a finding until deterministic membership checks and source-completeness requirements pass. Engine/peer constraints can block a candidate; even a passing metadata check is not a successful build/test.

Reviewer overrides create a new revision with attributed rationale and evidence. They do not delete source assertions or machine-detected gaps. A fresh advisory update can invalidate a prior candidate assessment without mutating its historical report.

## 6. Acceptance evidence for all five concepts

Registry add/disable/schema-change tests; two-provider eligible routing and denied fallback; cross-project/revocation/egress tests; concurrent overlap with max-in-flight assertions and order-independent reduction; natural Axios conflict with range/branch provenance. Use actual public payloads for semantics and clearly labelled injected failures for robustness. Actual model traces, deterministic scheduler tests, HTTP/UI acceptance and human judgments are reported separately in [evaluation](data-and-evaluation.md).
