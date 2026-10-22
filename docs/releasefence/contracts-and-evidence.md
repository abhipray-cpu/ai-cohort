# Contracts and evidence model

Implementation reference: `packages/contracts/src/contracts/releasefence.py` and
`releasefence_api/api.py`. Timestamps on the wire are finite UTC Unix seconds;
OTLP span times are Unix nanoseconds. The descriptive record catalog below remains
broader than the minimal v1 wire types. Exact available endpoints and omissions are
listed in [implementation notes](implementation-notes.md).

Implement finite Pydantic models with extra fields forbidden; finite nonnegative
numeric values, bounded strings/arrays/bodies, timezone-aware UTC timestamps and
explicit nullable/unknown semantics. Wire/API versions are independent of app code.
Canonical hashes exclude secrets and bind exact immutable content.

## Core records

| Record | Required content and invariants |
| --- | --- |
| Organization / project / environment | Server-owned tenant scope, membership, explicit environment identity; no caller-selected foreign tenant |
| ConnectorEnrollment | Connector/runtime IDs, environment, public-key identity, credential revision, exact capabilities, permitted apps and expiry |
| ReleaseManifest | Immutable ID/digest, application, code image/package digest, prompt digest, declared model/config digest, tool-schema digest, policy revision, optional compatible index snapshot, predecessor and provenance |
| RolloutPolicy | Exact manifest pair/environment, allowed actions, staged weights, metric definitions/versions, floors/windows, critical rules, expiry and approved verification scope |
| SpanEnvelope | OTLP trace/span/parent IDs, service/resource version, source backend/schema, observed times, redacted attributes, ingest identity and hash |
| TaskEvent | Event ID/sequence, session/attempt/action IDs, release digest, start/terminal/outcome/heartbeat/tool event, outcome-contract revision and receipt provenance |
| UsageRecord | Model/provider label, disjoint token categories where available, reported or estimated cost, currency, price revision and unknown reasons |
| Assignment | Tenant/app/environment/session hash, rollout revision, pinned release, assignment time and expiry |
| MetricWindow | Event-time bounds/watermark, deduped denominators, coverage/exclusions, values or null, uncertainty and metric/policy revisions |
| CanaryDecision | pass/fail/inconclusive/blocked, exact window hashes, reasons, counts, statistical method/version and next permitted action |
| Incident | Dedup key, rule revision, application/release, episode times, severity, current state and linked evidence |
| Approval | Human actor or owner-preauthorized policy, exact targets/digests/action, expected routing revision, scope/expiry and reason |
| RuntimeCommand | Unique ID, monotonic environment fencing epoch, expected routing revision, target digest, signed scope/expiry, idempotency key |
| RuntimeAttestation | Enrolled identity/signature, observed routing revision/digest, command ID, observation time, probe results and unresolved session/runtime counts |
| AuditEvent | Actor/scope/action, before/after revisions, evidence hashes, delivery/command disposition, correlation and recorded timestamp |

Changing any manifest component creates a new release; aliases such as “latest”
are not reproducible version identities. Record the model identity actually
observed when available; a configured alias is not proof of an immutable model.

## Proposed API families

`/api/session`, `/api/organizations`, `/api/projects`, `/api/enrollments`,
`/api/releases`, `/api/policies`, `/api/rollouts`, `/api/incidents`, `/api/metrics`,
`/api/approvals`, `/api/evidence`; machine endpoints under `/ingest/v1` and
`/connector/v1` use separate scoped credentials, quotas and replay protections.
These were design namespaces. Implemented browser resources are under
`/api/orgs/{tenant}`; runtime machine endpoints use `/ingest/v1` and
`/connector/v1/{enrollment}`. CI registration is `/registry/v1/releases` with a
different capability. Do not build clients against the old illustrative namespaces.

Create/start/approve/rollback APIs require explicit idempotency keys and expected
revision. Reusing a key with different content conflicts. An accepted request is
not a verified deployment. One connector cannot attest for another runtime.

## Boundaries and limits to implement first

Initial proposed limits: 1 MiB decoded event request, 100 events/batch, 64 KiB per
normalized record, 128 attributes, JSON container nesting 10, 100 requested
rows/page and 10 active rollouts/organization. Apply decompression limits before
parsing; reject conflicting duplicate event IDs and quarantine unsupported schemas.
Compressed intake is rejected rather than decompressed without bounds. Normalized
events/spans have much smaller finite contract fields. Each organization currently
has a 50,000 event and 50,000 span retention cap; new evidence is rejected visibly,
while duplicate retries are still acknowledged. Automatic archival/erasure is not
implemented. Limits still require target-host resource qualification.

Identity deduplication uses source/enrollment/event identity plus body hash. Do not
dedup independent runs merely because their prompts match. Repeated exporter
delivery is not another model call or another successful task.

An evidence export contains exact manifests/policy, event/window lineage,
assignments, analysis, approvals, command delivery, attestations/probes, unknowns
and final state. It contains redacted references rather than raw private prompts,
tokens/credentials or hidden reasoning. An audit hash chain alone is not an
independent witness against a fully compromised host.

The implemented verified-command export now includes the original signed runtime
`proof_envelope` beside its decoded `proof`; server command envelopes remain signed.
Heartbeat and closed-counter window evidence also retain signed envelopes. This
permits independent signature checks after export without private keys. Earlier
decoded-only evidence is explicitly legacy, not reconstructed signed evidence.
