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
| 8 | BuildRelay: event-triggered CI failure response | [BuildRelay](buildrelay/README.md) | [Corrective validation](buildrelay/fixes-and-validation-2026-10-19.md): 533 tests, lease crash fixed, 90.20% development anchor retention; independent/deployment gates open; study guide/blog available |
| 9 | CaseCouncil: multi-agent motor-insurance complaint review | [CaseCouncil](casecouncil/README.md) | Six actual-data artifact sets, five audited histories/one accepted unknown; 71 citations checked, 681 tests; browser/domain/Windows gates open; [study](casecouncil/study-guide.md), [blog](casecouncil/blog.md) |
| 10 | ShelfProof: self-reflecting packaged-food content review | [ShelfProof](shelfproof/README.md) | 785 tests passed; bounded actual USDA/Codex run 6/6 review-ready, all concepts observed; broader acceptance pending; [study](shelfproof/study-guide.md), [blog](shelfproof/blog.md) |

All products target the Windows service host with protected Cloudflare entry. AI generation uses an adapter to the installed Codex CLI; authentication and model-service network access are still required. Deployment acceptance must be demonstrated on the target laptop.
