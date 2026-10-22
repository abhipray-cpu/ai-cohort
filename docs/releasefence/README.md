# ReleaseFence — Day 11 production-agent release assurance

**Implemented engineering build; production/customer acceptance is not established.**
Latest: [browser and larger-cohort follow-up](followup-acceptance-2026-10-22.md).
Six actual browser E2E cases now pass after contrast fixes. The separately approved
200-product live cohort **failed** (165 successful outputs; 239/240 calls spent;
six Phoenix read-back dead letters). Its zero-inference 439-span backend replay
passes, but does not erase the failed run. Windows/Cloudflare is unavailable.

Implementation was subsequently authorized and tested on 21 October 2026. See the
[implementation map and runbook](implementation-notes.md) and
[measured status](implementation-status.md). [Actual validation](real-data-validation.md)
now includes 1,000 USDA products, a 150-case controlled fault matrix, installed Codex
and real authenticated MLflow plus local Phoenix. The user-approved
[OSS profile checkpoint](oss-validation-2026-10-22.md) passes bounded dual-backend
checks; full statistical promotion and Windows/Cloudflare acceptance remain
open. Legacy LangSmith remains unqualified, not required by the new named profile.
The name is provisional; trademark
clearance is unperformed.

Proposed promise: connect an existing agent stack, expose release-specific
failures, canary a change, and verify the runtime returned to the known-good
release when a scoped rollback is authorized. Not another general trace viewer.

Initial buyer: an engineering/platform lead at a B2B SaaS company operating
customer-facing support-answering or drafting agents. Willingness to pay is a
hypothesis to test, not established by competitor pricing.

## Requested concepts and required proof

| Concept | Implemented path | Acceptance evidence still required |
| --- | --- | --- |
| Dual-backend tracing | Original LangSmith/Arize design retained; user-approved `mlflow-phoenix-v1` alternative adds authenticated MLflow with Phoenix | Actual dual export/read-back, privacy, MLflow access isolation and independent outage checks pass; long-running pressure/host qualification open |
| Latency and cost dashboard | Release/cohort/task-level latency, outcomes, known/estimated/unknown cost and coverage | Independently recomputed metrics, deduplication, incomplete-window and zero-denominator tests |
| Alerting on loop failure | Repeated-call, iteration/deadline and missing-terminal detection, durable incident/notification delivery | Real isolated agent fault episodes, verified delivery, deduplication and outage recovery |
| Canary testing | Session-sticky baseline/candidate routing with immutable manifests, minimum evidence and explicit inconclusive decisions | Real adapter traffic assignment plus healthy/faulty/low-volume/missing-data scenarios |
| Rollback | Authorized compare-and-set routing change followed by runtime attestations and probes | Observe stable version actually serving new sessions; test partial/offline/replayed/failed commands |

“Arise” is interpreted as **Arize**. Phoenix and Arize AX are different deployment
options; LangSmith is a separate product. Connecting customer-owned instances is
not permission to redistribute them or run a commercial hosted clone.

## Read in order

1. [Product and scope](product-and-scope.md)
2. [Research and sources](research-and-sources.md)
3. [Commercial validation](commercial-validation.md)
4. [Architecture: C4 levels 1–4](architecture.md)
5. [Contracts and evidence](contracts-and-evidence.md)
6. [Telemetry and integrations](telemetry-and-integrations.md)
7. [Metrics and cost](metrics-and-cost.md)
8. [Alerting and incidents](alerting-and-incidents.md)
9. [Canary and rollback](canary-and-rollback.md)
10. [Data and evaluation](data-and-evaluation.md)
11. [Validation and acceptance](validation-and-acceptance.md)
12. [Operator UI](operator-ui.md)
13. [Permissions and security](permissions-and-security.md)
14. [Audit and recovery](audit-and-recovery.md)
15. [Operations](operations.md)
16. [TDD implementation plan](implementation-plan.md)
17. [Implementation status](implementation-status.md)
18. [Decisions and risks](decisions-and-risks.md)
19. [Implementation map and operating guide](implementation-notes.md)
20. [Observed TDD checkpoints](tdd-checkpoints.md)
21. [Real-source and live integration evidence](real-data-validation.md)
22. [ADR: self-hosted MLflow/Phoenix profile](adr-0002-self-hosted-mlflow.md)
23. [Latest OSS end-to-end evidence](oss-validation-2026-10-22.md)
24. [Browser and larger live-cohort follow-up](followup-acceptance-2026-10-22.md)
25. [Study guide: concepts, code and exercises](study-guide.md)
26. [Blog: 850 tests passed; the live campaign still failed](blog.md)

The stack is FastAPI/Pydantic, React/TypeScript, PostgreSQL, durable
workers and a customer-side Python connector/HTTP gateway. It does not require Kubernetes for
the first supported agent adapter. The old Windows laptop is a future lab/pilot
host behind protected Cloudflare entry, not evidence of commercial availability.
Any optional AI incident summary uses the installed-Codex port; models never own
release decisions or deployment credentials. Customers retain their own inference
providers. The original engineering-only checkpoint made no live calls. Subsequent
original authorized validation spent 24/24 bounded Codex invocations; a separately
approved larger campaign spent 239/240. No customer deployment
was performed.

Study guide/blog now document this measured implementation/validation checkpoint.
The learning cadence is complete; the failed live campaign and open product
acceptance gates remain explicitly recorded.
