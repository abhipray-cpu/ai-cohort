# Telemetry and integration contract

## Required first-class integrations

**Current selected self-hosted profile:** `mlflow-phoenix-v1`, authorized by the
user on 22 October. See [ADR 0002](adr-0002-self-hosted-mlflow.md) and
[OSS qualification](oss-validation-2026-10-22.md). Both actual backends are required;
the existing `langsmith-phoenix-v1` profile remains unchanged for legacy policies.
The [later 200-product campaign](followup-acceptance-2026-10-22.md) failed complete
export verification with six Phoenix dead letters. A separate 439-span retained
metadata replay passes both actual backends; it does not clear the original state.
The following original LangSmith requirement is retained for that legacy profile,
not a blocker falsely marked passed by MLflow evidence.

Support an actual authorized LangSmith destination and an internally/customer-owned
Arize Phoenix instance. Do not label AX qualified because Phoenix passed. Pin
collector/SDK/server versions and record backend response/query evidence.
LangSmith SaaS is acceptable; self-hosted LangSmith needs its own entitlement.
An isolated local Phoenix 20.23.0 endpoint has now been installed and qualified
for the bounded [live campaign](real-data-validation.md). No LangSmith account,
license, endpoint or key is available; dual-backend acceptance remains open.
If self-hosted LangSmith deployment is specifically required for acceptance, that
remains a separate licensed deployment gate: a SaaS connection must never be
reported as successful self-hosting. Record which mode was actually exercised.

Implemented v1 path: dedicated `TraceBridge` instrumentation or an owner-managed
collector -> authenticated ReleaseFence OTLP intake -> privacy normalization ->
PostgreSQL trace export work -> permitted LangSmith/Phoenix endpoints -> identity
read-back. The original direct customer-collector fan-out is an alternative design,
not a supplied/deployed/qualified collector distribution. No untested collector
YAML is advertised as working infrastructure.
Do not nest two auto-instrumentors and count the resulting duplicates as traffic.
Preserve trace/span IDs and parent links; map backend IDs explicitly when needed.
Round-trip test GenAI/OpenInference attribute mappings, not just HTTP 200 acceptance.

The MLflow adapter uses authenticated protobuf ingest, numeric experiment IDs and
experiment-scoped protobuf-JSON trace read-back. Original IDs/parent/release must
match. Its authenticated service account is distinct from ReleaseFence's machine
ingest credentials and from the MLflow bootstrap admin. The selected profile is
part of the approval-bound policy, not an operator-side bypass toggle.

Implemented mappings retain trace/span/parent IDs, release, safe span kind, timing
and status. Raw names, events, arguments, exception messages and arbitrary attributes
are not retained or forwarded. LangSmith UUID5 IDs and original-ID metadata make its
read-back explicit; Phoenix is queried by project and trace ID. Rich GenAI payload,
task-to-trace links and vendor UI deep links are not implemented. Cost accounting
comes from typed lifecycle/usage events, not guessed from trace payloads.

The actual Phoenix endpoint rejected JSON with HTTP 415. Its exporter now sends
OTLP protobuf and `x-project-name`, with trace/span IDs converted to protobuf byte
fields correctly. A project omitted on export is not allowed to be qualified by
querying a different project. LangSmith's JSON/UUID mapping remains implemented
but unqualified against a live authorized account. Keep these evidence levels separate.

## ReleaseFence-specific lifecycle evidence

Generic model spans cannot establish task success or detect an unclosed run alone.
The Python adapter must emit release digest, session/task/attempt IDs, declared
outcome contract, iteration/stop reason, tool action identity, relevant heartbeats,
terminal outcome and usage provenance. Async jobs propagate context explicitly.
Record attempted, authorized, dispatched and completed actions separately.

Loop signals use tool name plus a keyed fingerprint of permitted normalized
arguments/outcome and a progress marker. Do not log raw secrets to compare calls.
Legitimate polling/retries need declared bounds; repeated calls are a signal, not
proof of a semantic loop. Critical max-iteration enforcement is code-owned.

## Transport and data quality

At-least-once delivery is assumed. Dedup IDs, body-hash conflicts, out-of-order
timestamps, late completions, orphan spans, missing terminals and clock skew are
visible states. Use event time for windows with an ingest watermark/lateness
policy; never silently rewrite an already-issued decision with late data.

Runtime lifecycle/coverage counters needed for safety gates must not depend on
sampled trace payloads. Sampling configuration and dropped/export-failed counts
are recorded. Compare independent runtime assignments/accepted-task counters
against received terminal events. Trace backend outage is not agent success.

Initial collector/connector queues are disk-bounded with backoff, quotas and a
visible overflow condition. No unbounded memory buffer or blocking network export
inside every tool call. Test that pressure does not stall the customer's agent;
lost safety evidence holds promotion and raises a telemetry-health incident.

## Observe-only versus controlled mode

Observe-only credentials permit event ingest/read-back but no deployment commands.
Controlled mode enrolls exact app/environment/runtime identities and an allowlisted
routing adapter. The first adapter can resolve registered stable/candidate bundle
digests and update the session-routing configuration; no arbitrary shell/code URLs.

Connectors initiate authenticated outbound polling for signed expiring commands;
customers need not expose their internal agent port to our public internet.
Recheck enrollment/capability/epoch at command execution, not only at creation.
Generic tracing, notification and deployment credentials remain separate secrets.

Actual integration acceptance must query both backends for known traces, assert
version/parent-child identity, verify redaction, then deliberately break one
exporter and prove loss is reported without double-counting the other stream.
