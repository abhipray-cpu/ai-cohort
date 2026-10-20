# Windows service host

Products run on the Windows laptop. Keep the Codex executable local and private; applications invoke it through `agent-core`.

CaseCouncil (Day 9): `install-casecouncil.ps1 -RepoPath <repo> -Credential <limited account> [-Start]`
packages separate API/worker startup tasks on loopback 8008. It refuses existing
tasks and requires the Python workspace and frontend build. All tunnel paths need
Access; there is no webhook exception. This is packaging, not Windows/reboot or
process-isolation acceptance. See the [CaseCouncil runbook](../../docs/casecouncil/implementation-and-operations.md).

BuildRelay (Day 8): `install-buildrelay.ps1 -RepoPath <repo> -Credential <limited account>` packages API/worker startup tasks on loopback 8007. A separately managed authenticated NATS JetStream broker is needed for queue ingress. Packaging does not prove Windows/reboot acceptance or configure Cloudflare's public webhook-path exception. See the [BuildRelay runbook](../../docs/buildrelay/implementation-and-operations.md).

RelayDesk has additive `install-relaydesk.ps1` startup-task packaging, port 8004 and an independent store/erasure ledger. See its [current runbook](../../docs/relaydesk/implementation-and-operations.md). Windows acceptance remains required; packaging alone does not pass reboot, service identity or tunnel checks.

`install-resolvedesk.ps1` packages ResolveDesk as two Task Scheduler startup tasks (API and worker), under an explicit limited account. It refuses to replace existing tasks and requires the Python workspace and web build to exist. The service runner loads explicit product credentials and rotates its role logs.

This packaging has not been accepted on the target Windows laptop. It is not an SCM service installer and does not provision Codex auth, ACLs, DNS, or Cloudflare Access. Follow the [ResolveDesk operations runbook](../../docs/resolvedesk/operations.md) and validate reboot, child-process shutdown, auth, and restore before remote use. No script exposes Codex through the tunnel.
# ClauseGate (Day 6)

`install-clausegate.ps1 -RepoPath <repo> -Credential <limited-account> [-Start]`
adds separate API/worker startup tasks on loopback 8005, refusing existing tasks.
Build its web app and install the Python workspace first. Configure explicit
`CLAUSEGATE_USERNAME/PASSWORD` and the installed Codex identity under that account;
no CLI authentication is copied from another user. No embedding model is required.
Protect `var/clausegate` and the independent `var/clausegate-authority` store with
the service ACLs. Restore is quarantined and requires fresh operator/reviewer grants.
These are Task Scheduler packages, not actual Windows acceptance results.
See `docs/clausegate/implementation-and-operations.md` for current commands and limits.
