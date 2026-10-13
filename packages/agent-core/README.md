# agent-core

Shared AI execution layer. Its first provider is `LocalCodexProvider`, which invokes the Codex runtime installed on the Windows host. It must expose a provider-neutral interface, return raw execution data for auditability, and never assume an external LLM API.
