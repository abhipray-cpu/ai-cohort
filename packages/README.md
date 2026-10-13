# Shared packages

Packages are deliberately framework-light. They make product behavior consistent without coupling products together.

- `agent-core`: local Codex invocation and structured-output retry orchestration.
- `contracts`: Pydantic contracts shared by products and tools.
- `observability`: structured events for runs, validation failures, and retries.
