# Product documentation

Each delivery pack contains scope, architecture, implementation order, source data, evaluation, UI, and release evidence. Plans and target thresholds are distinct from measured results.

| Day | Product | Delivery pack | Current stage |
| --- | --- | --- | --- |
| 1 | TenderLens: tender requirements and evidence review | [TenderLens](tenderlens/README.md) | Active implementation; release gates remain open |
| 2 | ResolveDesk: PostgreSQL RAG chat with citation grounding | [ResolveDesk](resolvedesk/README.md) | Implemented pilot; live two-turn chat passed, release gates remain open |
| 3 | PropertyBrief: property investigation and diligence planning | [PropertyBrief](propertybrief/README.md) | Implemented pilot; actual-data validation, operations and learning docs |
| 4 | PatchDesk: client security-maintenance orchestration | [PatchDesk](patchdesk/README.md) | Implemented pilot; 40-snapshot validation, coverage/AI release blockers and learning docs |
| 5 | RelayDesk: memory-enabled technical escalation continuity | [RelayDesk](relaydesk/README.md) | Corrective-tested pilot; 89 threads/6,680 non-bot messages, 283 tests, 11 live-stage completions; full acceptance incomplete; study guide/two blog drafts |
| 6 | ClauseGate: human-in-the-loop NDA exception approval | [ClauseGate](clausegate/README.md) | Implemented pilot; 300 workflow fixtures, 61/61 development analyses, 346 tests; semantic/release gates blocked; final study/blog updated |
| 7 | CatalogBridge: budget-controlled supplier catalog matching | [CatalogBridge](catalogbridge/README.md) | Local review-draft router; 476 tests; quota-stopped comparison, savings/confidence gates open; [study](catalogbridge/study-guide.md), [blog](catalogbridge/blog.md) |

All products target the Windows service host with protected Cloudflare entry. AI generation uses an adapter to the installed Codex CLI; authentication and model-service network access are still required. Deployment acceptance must be demonstrated on the target laptop.
