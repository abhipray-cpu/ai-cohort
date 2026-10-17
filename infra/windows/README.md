# Windows service host

Products run on the Windows laptop. Keep the Codex executable local and private; applications invoke it through `agent-core`.

RelayDesk has additive `install-relaydesk.ps1` startup-task packaging, port 8004 and an independent store/erasure ledger. See its [current runbook](../../docs/relaydesk/implementation-and-operations.md). Windows acceptance remains required; packaging alone does not pass reboot, service identity or tunnel checks.

`install-resolvedesk.ps1` packages ResolveDesk as two Task Scheduler startup tasks (API and worker), under an explicit limited account. It refuses to replace existing tasks and requires the Python workspace and web build to exist. The service runner loads explicit product credentials and rotates its role logs.

This packaging has not been accepted on the target Windows laptop. It is not an SCM service installer and does not provision Codex auth, ACLs, DNS, or Cloudflare Access. Follow the [ResolveDesk operations runbook](../../docs/resolvedesk/operations.md) and validate reboot, child-process shutdown, auth, and restore before remote use. No script exposes Codex through the tunnel.
