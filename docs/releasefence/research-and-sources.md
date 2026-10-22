# Research, competitors and source register

Checked 21 October 2026 against primary vendor/project material. Vendor claims
describe advertised/documented functionality, not independent comparative tests.
Prices/features may change; recheck before procurement or a published comparison.

| Source | Observed capability or constraint | Design implication |
| --- | --- | --- |
| [LangSmith alerts](https://docs.langchain.com/langsmith/alerts) | Alerts already cover operational/cost/feedback signals | Do not market basic alerting as absent from LangSmith |
| [LangSmith OTLP](https://docs.langchain.com/langsmith/trace-with-opentelemetry) | Collector fan-out and attribute mapping are documented | Instrument once, qualify mappings and destinations; export is not runtime authority |
| [LangSmith self-hosting](https://docs.langchain.com/langsmith/self-hosted) | Enterprise add-on with licensed deployment | No assumption of a free bundled LangSmith server |
| [Arize pricing/capabilities](https://arize.com/pricing/) | AX offers traces, evaluation and production monitoring; Phoenix is a separate self-hosting option | Integrate with existing platforms, not claim they lack agent observability |
| [Phoenix self-hosting](https://arize.com/docs/phoenix/self-hosting/deploying-phoenix) | SQL-backed instance; SQLite and PostgreSQL options documented | Pin an internally owned test instance; qualify resource/auth setup |
| [Phoenix license](https://raw.githubusercontent.com/Arize-ai/phoenix/main/LICENSE) | Current ELv2 restricts commercial hosted/managed provision of substantial functionality | Customer-owned connection by default; any managed bundling needs separate licensing review |
| [Langfuse prompt CI/CD](https://langfuse.com/resources/engineering/prompt-cicd) | Versioning, eval gates and label rollback; traffic splits/approvals composed with application/CI | Integration glue is a possible opportunity, not a uniquely invented release capability |
| [Langfuse alerts](https://langfuse.com/docs/observability/features/alerts) | Cost/quality alerts with Slack, webhook and GitHub Actions delivery | A chart and a webhook are insufficient differentiation |
| [Braintrust observability](https://www.braintrust.dev/learn/ai-observability/v0) | Production traces, scoring and regression alerts | Evaluation of production traffic is already an offered service |
| [Datadog prompt experimentation](https://docs.datadoghq.com/llm_observability/configure/prompt_experimentation/) | Documented preview of prompt experiments/guarded rollout integration | Direct incumbent threat; verify current availability by site/plan |
| [LaunchDarkly guarded-rollout FAQ](https://support.launchdarkly.com/hc/en-us/articles/55384223785115-FAQ-Guarded-rollouts) | Metric-backed guarded releases and regression rollback | Automatic rollback is not a novel category |
| [Argo analysis](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/) | Progressive-delivery analysis and inconclusive pauses | DIY integration is a serious alternative; do not turn no data into success |
| [OpenTelemetry demo flags](https://opentelemetry.io/docs/demo/feature-flags/) | Configurable demo scenarios for telemetry/infrastructure testing | Reproducible lab faults, not real customer incidents |

Published entry prices observed during research: LangSmith Plus $39/seat/month
plus usage; Arize AX Pro $50/month; Langfuse Core $29/month; Braintrust Pro
$249/month plus applicable usage. Billing units and included features differ;
these are not equal-workload total-cost comparisons. Primary sources:
[LangSmith](https://www.langchain.com/pricing),
[Arize](https://arize.com/pricing/), [Langfuse](https://langfuse.com/pricing),
[Braintrust](https://www.braintrust.dev/pricing).

## Opportunity versus evidence

### Self-hosted alternative follow-up — 22 October 2026

The user authorized the recommended upstream MLflow/Phoenix alternative after no
LangSmith account was available. [ADR 0002](adr-0002-self-hosted-mlflow.md) records
the profile change and licensing boundary; [actual tests](oss-validation-2026-10-22.md)
record qualification, rather than relying on vendor claims alone.

- [MLflow OTLP ingestion](https://mlflow.org/docs/latest/genai/tracing/opentelemetry/ingest/):
  HTTP protobuf and experiment routing support the existing OTel boundary.
- [MLflow basic HTTP authentication](https://mlflow.org/docs/latest/self-hosting/security/basic-http-auth/):
  authenticated scoped access; lab explicitly denies default permissions instead
  of relying on permissive defaults. Tested installed version: 3.17.2.
- [MLflow license](https://github.com/mlflow/mlflow/blob/master/LICENSE.txt):
  Apache-2.0 upstream; retain applicable notices. This does not change Phoenix ELv2.

The lighter MLflow SQL topology was selected over Langfuse's additional stateful
services for this first host target, not as a general product-quality ranking or
proof of old-Windows resource suitability.

### Original product opportunity

Proposed wedge: verify whole-agent releases across a customer's existing trace,
runtime and release systems, including actual runtime adoption, in-flight exposure,
no-data holds and a durable decision packet. This is an inference from integration
boundaries and the proposed buyer workflow, not proof that competitors lack all
of these features. No customer interviews, paid pilots or head-to-head tests exist.

Research sources are not authorization to create vendor accounts, accept terms,
run paid plans, use someone else's traces or connect deployment credentials.
Record exact image/SDK/license revisions at implementation time. Do not describe
ELv2 software as unrestricted open-source hosting infrastructure.
