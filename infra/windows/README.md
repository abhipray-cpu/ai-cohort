# Windows service host

Products run on the Windows laptop. Keep the Codex executable local and private; applications invoke it through `agent-core`.

Future scripts here will install each product as a Windows service and start its local web/API process. No script should expose Codex's own port through Cloudflare Tunnel.
