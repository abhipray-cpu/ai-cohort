# Actual data, workload provenance and validation design

Latest [follow-up](followup-acceptance-2026-10-22.md): a separately approved live
campaign attempted 200 products using 239/240 calls; 165 successful outputs and
35 provider-failed tasks, plus six Phoenix read-back dead letters. This was **not**
a passing larger campaign. Six actual browser cases now pass. The older bounded
checkpoint below keeps its original six-product inference denominator.

**Measured acceptance is partial, not complete.** The [latest OSS checkpoint](oss-validation-2026-10-22.md)
records rerun coverage of 1,000 frozen USDA products, 12,000 events and 150
source-bound controlled scenarios, plus the fourth bounded installed-Codex
campaign (24/24 cumulative invocations, six in this run). Actual MLflow/Phoenix
dual read-back passed. This does not expand the six-product inference sample.
Browser, target-host and actual-traffic statistical promotion remain open;
legacy LangSmith is unqualified. The [earlier report](real-data-validation.md)
retains its historical 18-call denominator. Counts
below are frozen targets, not a replacement for measured denominators.

## Source and evidence tiers

| Tier | Available source | Permitted conclusion and limit |
| --- | --- | --- |
| Existing measured artifacts | ShelfProof actual USDA/Codex run, ResolveDesk public PostgreSQL-source evaluation histories | Real-source/real-provider history for mapping/replay if files and rights verify; not ReleaseFence instrumentation or customer traffic |
| New isolated workload runs | Registered staging agent bundles using frozen approved public USDA or PostgreSQL documentation facts | Fresh runtime/trace/outcome evidence; new model/provider egress needs a separate bounded approval |
| Standard infrastructure lab | [OpenTelemetry demo](https://opentelemetry.io/docs/demo/feature-flags/) with pinned code/images and controlled faults | Real service/collector behaviour under deliberately injected conditions, not spontaneous production incidents |
| Controlled connector fixtures | Deterministic agent endpoints, signed commands, known usage receipts and injected loss/duplicates | Volume, policy and crash correctness; not model semantic quality |
| Authorized customer pilot | Customer-owned staging/production metadata under explicit agreement | Customer integration/business utility only within that consent and measured scope; none currently secured |

Existing source pointers: [ShelfProof validation](../shelfproof/real-data-validation.md)
and [ResolveDesk source evaluation](../resolvedesk/validation-2026-10-14.md).
Verify artifact availability, notices, hashes and permissions before reuse; do not
import another product's DB, grants, passwords, unknown-usage exceptions or pending
work. Use explicit HTTP/adapter boundaries and independent evaluation stores.

Do not invent a public production-agent incident dataset. Public source records,
real executed workloads, authored prompts and injected errors are four different
things. Public availability does not automatically authorize unrestricted payload
redistribution or third-party model egress. Preserve notices and source manifests.

## Frozen workload inventory

Each case records source URL/revision/hash, license/rights basis, input provenance,
workload and bundle versions, expected mechanical outcome, fault schedule, seed,
cohort/session identity, consent/egress grant and known limitations. Gold labels
and fault schedules are not included in model context. Cases from one source or
incident family stay in one development/calibration/locked group.

Use independent expected-outcome derivation for injected mechanical events. Semantic
task labels require independent review; do not reuse a model's judge score as gold.
No thresholds or margins may be retuned after inspecting locked results.

## Proposed volume and scenarios

Mechanical campaign: at least 10,000 unique normalized events, 1,000 sessions and
three isolated organizations; at least 30 scenario families with five independent
fault episodes each and 100 healthy episodes. Increase traffic to meet the frozen
canary analysis requirements; these minimum counts do not guarantee enough power.
Duplicate deliveries do not increase the unique denominator. Generate neither
millions of cloned “real” records nor fake model completions.

Required families include repeated calls, normal bounded polling, iteration cap,
provider timeout, schema-repair storm, absent terminal, human-wait state, clock
skew, duplicate/conflicting IDs, late events, sampled traces, collector overflow,
exporter outage, unavailable cost, cached-token overlap, price revision, cohort
imbalance, low traffic, healthy/regressed canary, stale approval, replayed command,
response-lost-after-apply, offline runtime, partial rollback, incompatible stable
bundle, restart at every critical checkpoint, cross-tenant access and redaction.

Live integration smoke proposal: up to 40 isolated real-provider sessions / 160
cumulative calls including retries, only after a new exact owner approval. Start
smaller if appropriate; do not spend this target automatically. Trace both actual
backends, trigger a labelled hard-failure episode in a read-only staging candidate,
observe alert delivery and verify rollback through actual routing/attestations.
No production accounts or irreversible tools are needed for that drill.

Small live samples can demonstrate integration/critical-failure rollback but not
ordinary statistical promotion, rare-event rates or production quality. A healthy
low-volume canary must remain inconclusive. Full actual-traffic promotion evidence
needs enough authorized traffic under the frozen plan or remains an unpassed gate.

## Measurements

Report unique events, sessions, episodes, source groups, backend-confirmed traces,
known/unknown calls, receiving-runtime counts, policy decisions, false pages,
detection/delivery/verification delays, missing evidence and resource overhead.
Publish false-positive/negative denominators per independent episode, not per span.
Distinguish simulated-clock results, controlled wall-clock drills and actual live
model runs. Retain failed attempts and version lineage alongside successful ones.
