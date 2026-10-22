# Decisions, open risks and change control

## Accepted design defaults, not implemented guarantees

1. Integrate existing trace backends; do not compete as a generic trace viewer.
2. First controlled runtime is a Python HTTP session router with registered bundles.
3. Support actual customer-owned LangSmith/Phoenix proof; no licensed server resale assumed.
4. Dedicated PostgreSQL, server-owned tenant identity/RLS and transactional outboxes.
5. Metadata-first privacy with bounded buffers and independent lifecycle coverage.
6. Deterministic policy/alerts/control. Optional AI is advisory and separately authorized.
7. Session-sticky canaries, immutable manifests, low-evidence hold and no-data not healthy.
8. Signed scoped commands and runtime verification; no magical reversal of side effects.
9. Laptop deployment is a lab/pilot target, not a commercial reliability claim.
10. No study/blog success narrative until implementation and a measured checkpoint.

## Highest risks and required responses

| Risk | Response / release consequence |
| --- | --- |
| Incumbents add the same workflow; DIY is enough | Customer discovery and paid pilot; narrow adapter demand before expansion |
| Hosted-platform licensing | Customer-owned endpoints; review pinned terms before managed bundling |
| Traces incomplete/sampled/delayed | Independent lifecycle counters, coverage gates, explicit unknown/inconclusive |
| Cost cannot be reliably priced | Preserve unknowns; cost gate unavailable, never invent zero dollars |
| Statistical false promotion or noisy alerts | Frozen methods/looks/margins, independent episodes, calibration and hold states |
| Whole-agent rollback incompatibility | Preflight predecessor availability/schema/index compatibility; partial/blocked state |
| External command repeats after crash | Stable command identity, runtime persistence, fencing and read-back reconciliation |
| Cross-tenant control/data leak | Scoped enrollment, DB RLS/pool tests, separate secrets and independent security review |
| Observer outage creates operational risk | Last approved routing, no expansion under stale authority, separate observer health |
| Laptop cannot run the target stack | Measure host first; explicit alternative, not silent architectural downgrade |
| Public data mistaken for customer proof | Source provenance and labelled fault injection; consented pilot remains separate |

Open before implementation: actual host capacity, backend account/license access,
exact version pins, precise analyzer math/calibration cases, supported signing/key
lifecycle, trusted runtime-attestation assumptions and initial pilot commitments.

Change control: update docs/contracts/tests before changing rollout authority,
no-data semantics, statistical margins, manifest identity, cost accounting,
redaction, connector capabilities or target adapter. Freeze a new evaluated version
and retain old evidence. A hard task or missing key is not permission to loosen
the gate or mutate a different customer's infrastructure.
