# Deployment and operational boundaries

Executable setup, commands, customer protocol and recovery procedures now live in
[implementation notes](implementation-notes.md). This file retains the deployment
qualification boundaries. Implementation did not edit the real `.env`, start old
products, provision vendors, deploy a tunnel or run a live model.

## Implemented packaging

Independent roots: `apps/releasefence-api`, `apps/releasefence-web`, a connector
package, namespaced contracts and owned `var/releasefence` evidence/config paths.
Use dedicated PostgreSQL roles/database, migration ownership, secret storage and
backup locations. Proposed loopback API port 8010 must be checked before allocation.
Do not copy credentials, data stores or authority from another cohort product.

Available Make interface: `releasefence-build/up/down/status/test`.
There is no automatic acceptance target claiming the remaining gates passed.
`up` must validate configuration, build static assets, start only owned services
and expose honest dependency/readiness checks. Startup/health must not call a
model, register customer credentials, fetch live data, start a rollout or dispatch
a newly authorized command. Restart may continue already authorized unexpired
outbox work, with current checks and documented pause/quarantine behaviour.

`down` must stop only identified owned processes and disclose unresolved external
command state; it must not revoke an unrelated runtime or silently report rollback.
There is no default real deployment destination or weak public demo password.

## Windows laptop and commercial SaaS are separate gates

Inspect actual CPU/RAM/disk/Windows version, virtualization, container/WSL2 support,
service identity and port conflicts before choosing lab deployment. PostgreSQL and
collector/Phoenix resource pressure require measurement. A lightweight external
customer-owned backend or managed DB can be an explicitly approved alternative;
do not silently replace the multi-tenant design with an unqualified local store.

Cloudflare protects application routes with end-user access and scoped machine
service authentication. Do not expose PostgreSQL, raw collector, Phoenix admin,
credential files or Codex directly. Verify each authenticated ingest/connector
route under the real proxy; Access login alone is not machine API authorization.

The laptop is a lab/limited pilot host. Commercial SaaS needs separate availability,
capacity, security, tenant restore, key rotation, alert delivery and incident support
qualification. No paid uptime commitment is inferred from a successful tunnel.

## Observer health

Track ingest acceptance/drop/quarantine, lifecycle coverage, exporter backlog,
worker lease/lag, DB availability, query duration, command reconciliation age,
connector freshness, notification retries/dead letters and disk/CPU/RAM. Use a
separate operational notification route for failures of ReleaseFence itself.
An unhealthy collector or expired control authority must not green a release.

## Before any actual integration campaign

Verify backend credentials/license terms and endpoint allowlists; source rights;
redaction; exact payload destinations; target app/environment/runtime set;
notification receiver; maximum sessions/model calls/cost and expiry; rollback
capability/approval; compatible stable bundle; isolated tool side effects; evidence
directory and cleanup ownership. Existing ShelfProof/ResolveDesk approvals do not
apply. No model/key changes, external messages, production mutations or account
creation were performed by the engineering implementation turn. Such operations
need their own exact scope; implementation approval is not a vendor subscription.
