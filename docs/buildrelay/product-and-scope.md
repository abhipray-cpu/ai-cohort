# Product and scope

## Buyer and outcome

Hypothesis: agency engineering/delivery leads overseeing multiple client repositories
will pay to reduce the time from failed build to an owned, actionable response.
A proposed $99/month pilot is a willingness-to-pay experiment, not validated demand.

GitHub already explains failed checks through Copilot; BuildPulse and Trunk already
sell CI/test intelligence. The proposed wedge is per-client operations and reliable
handoffs, not novel log explanation or unique self-hosting.

Sources: [GitHub](https://docs.github.com/en/actions/how-tos/troubleshoot-workflows),
[BuildPulse](https://buildpulse.io/), [Trunk](https://trunk.io/flaky-tests).

## Implemented pilot scope

- Owner-managed clients, repository identity binding, configured response owner/team.
- Signed GitHub `workflow_run` completed events and independent JetStream envelopes.
- Durable inbox, bounded leased execution, duplicate suppression across transports.
- Bounded attempt-specific log retrieval, redaction, exact excerpt citations,
  schema repair, and explicit manual triage on AI outage/invalid output.
- One incident per configured repository/run across attempts, newer attempt protection,
  operator acknowledgment/reassignment, and unapproved-draft JSON handoff export.
- Optional GitHub issue creation/update/recovery close, explicit action ledger,
  ambiguous-create reconciliation, and owner-controlled verified rearming.
- Retry schedule, durable workflow dead letters, checkpoint-preserving replay,
  audit, recent-run repair, readiness and worker signals.
- Client-scoped operator/viewer access, sessions/CSRF, revocation and live grant changes.

Configured owner labels are routing rules, not automatic GitHub assignee permissions.
Acknowledgment records responsibility; it does not confirm the AI diagnosis.
GitHub owner text updates on the next run event, not immediately after reassignment.

## Not implemented / not claimed

No autonomous patches, merges, deployment, test execution, blind reruns, automatic
client messages, SLA escalations, billing, SSO, arbitrary workflow builder, or other
CI providers. LogChunks' Travis logs are evaluation inputs, not a supported native
Travis webhook integration. No guarantee of processing all historical reruns.
Public data is not proof of commercial value, diagnosis accuracy or security.

An incident correlates attempts of **one run ID**. Separate runs/commits remain
separate incidents; the service does not infer that a passing later commit fixed
an older failed run.
