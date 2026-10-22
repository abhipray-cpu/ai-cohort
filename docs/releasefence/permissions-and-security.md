# Tenant isolation, deployment authority and threat model

The service ingests untrusted telemetry and may control a customer's release
routing. An attacker must not turn an event, trace attribute or AI explanation
into a credential, cross-tenant query or deployment command.

## Actors and capabilities

Organization owner manages memberships/enrollments and policy authority; release
operator proposes/starts approved rollouts; approver grants exact-target control;
observer reads permitted dashboards/evidence. Production self-approval is denied
by default; a recorded owner policy must explicitly permit bounded exceptions.
Machine actors are separate, least-privilege ingest, registration and connector
identities. Role membership is not unrestricted deployment authority.

All primary/foreign keys and queries include tenant scope. Use PostgreSQL RLS with
an application role that cannot bypass it and transaction-local tenant context;
test connection-pool context reset and all worker/admin/export paths. Never trust
an OTLP attribute or caller-supplied organization ID to select the tenant. Cross-
tenant IDs return indistinguishable denials before hydration or evidence linking.

Browser sessions need hashed/salted passwords, opaque expiring server sessions,
CSRF/same-origin mutation checks, login throttling and secure cookie/header policy.
Control approvals bind exact app/environment/manifests/action/revision and expiry.
Revocation is checked at dispatch and execution. Lost connectivity cannot renew a
promotion permission. Session, model, webhook and deployment credentials are distinct.

## Untrusted transport and outbound requests

Require authenticated HTTPS/machine identities, per-tenant rate/body/decompression
quotas, schema versions and replay defenses. Redact before collector export;
metadata itself can contain PII, so enforce an allowlist and retention boundaries.
No prompt/tool payload/hidden reasoning capture by default. Tenant-scoped deep
links must not expose vendor credentials or bypass that vendor's authorization.

Webhook/export destinations require owner approval, SSRF protection and DNS/IP
validation at connection time. Deny metadata/link-local/private ranges by default;
explicit internally enrolled endpoints need a separate bounded exception. Bound
redirects, timeouts, response sizes and outbound concurrency. Do not expose an
arbitrary URL probe or remote-shell API to internet clients.

Signed runtime commands must be replay-safe, monotonic/fenced and exact-targeted.
Connector private keys remain customer-side; server credentials are encrypted with
an operator-managed key outside the DB and support scoped rotation. No secrets in
logs/export/examples/real `.env` commits. TLS and Cloudflare Access supplement,
not replace, application tenant authorization.

## Availability and trust limits

RLS/application checks do not defend against a compromised DB administrator or
host. Hashes/signatures prove origin/integrity under their key assumptions, not
semantic task correctness. Independent security review, dependency/license review,
backup encryption/retention and denial-of-service testing remain release gates.
No compliance certification or enterprise isolation claim is pre-authorized.
