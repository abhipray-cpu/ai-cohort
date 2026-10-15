# Product documentation

Each delivery pack contains scope, architecture, implementation order, source data, evaluation, UI, and release evidence. Plans and target thresholds are distinct from measured results.

| Day | Product | Delivery pack | Current stage |
| --- | --- | --- | --- |
| 1 | TenderLens: tender requirements and evidence review | [TenderLens](tenderlens/README.md) | Active implementation; release gates remain open |
| 2 | ResolveDesk: PostgreSQL RAG chat with citation grounding | [ResolveDesk](resolvedesk/README.md) | Implemented pilot; live two-turn chat passed, release gates remain open |
| 3 | PropertyBrief: property investigation and diligence planning | [PropertyBrief](propertybrief/README.md) | Implemented pilot; actual-data validation, operations and learning docs |

All products target the Windows service host with protected Cloudflare entry. AI generation uses an adapter to the installed Codex CLI; authentication and model-service network access are still required. Deployment acceptance must be demonstrated on the target laptop.
