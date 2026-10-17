# Research, evidence and limitations

Research inspected 17 October 2026. External facts below come from primary publisher/vendor documentation; design choices and commercial conclusions are explicitly proposals. No source establishes that ClauseGate has customers or superior performance.

This preserves the initial research stage. Subsequent actual corpus acquisition, implementation and test results are recorded in [implementation validation](implementation-validation-2026-10-17.md); the earlier “not downloaded” observation below is historical, not current acquisition status.

## Buyer/workflow evidence

| Primary source | Supported observation | Limit |
| --- | --- | --- |
| [Juro: contract approval workflows](https://juro.com/learn/contract-approval-workflow) | Describes approval ownership, version confusion, sequential review and reapproval after document changes | Vendor-authored category evidence, not an independent customer study |
| [Ironclad: AI Playbooks](https://support.ironcladapp.com/hc/en-us/sections/31307199486103-AI-Playbooks) | Lists playbook-based review, misclassification management and non-standard-term exception requests | Strong existing competition; listing does not prove ClauseGate differentiation |
| [Ironclad product descriptions](https://legal.ironcladapp.com/fy2026-product-descriptions) | Describes configured workflow stages and AI playbook guidance subject to permissions/human review | Capabilities/availability depend on vendor terms; not a feature-parity audit |

Inference: exception ownership and document-version binding are credible workflow concerns. Hypothesis: a focused NDA-only self-hosted product can sell to teams that do not want a broader platform. Neither inference proves willingness to pay, an underserved market or superiority. No competitor pricing or claimed accuracy is reused as our own benchmark.

## Primary real-data source: ContractNLI

[Official project/dataset documentation](https://stanfordnlp.github.io/contract-nli/) describes **607 non-disclosure agreements**, **17 fixed hypotheses**, three labels (`Entailment`, `Contradiction`, `NotMentioned`) and evidence spans. It documents original source URLs/types and text/annotation JSON. Evidence can be multiple noncontiguous spans, which matters for exception language. Documentation says each document has a single annotation set; this is not two independent reviewers per document.

[Peer-reviewed paper](https://aclanthology.org/2021.findings-emnlp.164/) explains the task and challenges of exceptions/negation. The [official archive listing](https://github.com/stanfordnlp/contract-nli/tree/gh-pages/resources) exposes `contract-nli.zip`. Dataset documentation states CC BY 4.0 and presents additional usage notices. Record the exact acquired version, notices, attribution and license before evaluation. Do not assume links to original PDFs confer equivalent reuse rights.

Why it fits: existing human annotations can test interpretation, evidence selection and unsupported/missing assertions. `NotMentioned` is a legitimate annotated semantic result, not automatically model uncertainty or a company-policy breach. Whether it requires clarification depends on the configured rule and complete-document coverage.

What it does not supply: company playbooks, approval authorities, customer intentions, reviewer interactions, actual approval outcomes or willingness to pay. The known 17 hypotheses do not cover every risk in an NDA. Public benchmark exposure also limits claims of model novelty/unseen evaluation.

## Secondary source: CUAD

[The Atticus Project](https://www.atticusprojectai.org/cuad/) documents **510 commercial contracts**, **41 clause types** and **13,000+ labels**, manually annotated under experienced-lawyer supervision; the publisher states CC BY 4.0. [Official repository](https://github.com/The-Atticus-Project/cuad) is linked by the publisher. Verify exact files, terms and attribution at acquisition rather than relying on these headline counts.

Use CUAD only for separately labelled extraction robustness and out-of-scope contract detection/generalization. It is not an NDA-only cohort, not a source of approval policies and not an oracle that the system may approve a clause. Do not add its 510 contracts to the primary NDA denominator or assume zero overlap without hashes/similarity checks.

## Infrastructure evidence and architectural choice

[SQLite WAL documentation](https://www.sqlite.org/wal.html) describes concurrent reads with one writer and the same-host/local-filesystem requirement. Proposed deployment therefore keeps the product database on local disk, not a network share or live cloud-sync folder. Short transactions and no database lock during inference/human waiting are design requirements. Verify supported patched SQLite/runtime versions at implementation; WAL is not blanket crash/backup/audit-proof certification.

The existing repo contains `packages/agent-core/src/agent_core/codex_local.py` and provider contracts. Reuse is a proposal subject to isolation, audit, timeout and service-account tests. This is not a request to configure Codex itself, migrate models or introduce a direct model API.

## Evidence status

Documentation and public file listings were inspected. No dataset archive was acquired in this docs stage; no hashes, actual imported counts, inference results, customer decisions or product passes exist. See [dated feasibility](validation-2026-10-17.md) and [evaluation plan](data-and-evaluation.md). Do not call documentation availability an end-to-end test.
