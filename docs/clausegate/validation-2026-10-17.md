# Source feasibility — 17 October 2026

Scope: **historical pre-implementation research**, not current runtime status. This note preserves what was checked during the docs stage. Later runtime/data/tests are recorded in [implementation validation](implementation-validation-2026-10-17.md); do not rewrite earlier observation as a retrospective pass.

| Observation | What was checked | What remains unknown |
| --- | --- | --- |
| ContractNLI source | [Official project page](https://stanfordnlp.github.io/contract-nli/), license/use notices, schema description and [archive listing](https://github.com/stanfordnlp/contract-nli/tree/gh-pages/resources) | Download integrity, archive contents/counts, current usability and split overlap |
| Dataset task | [Publisher paper page](https://aclanthology.org/2021.findings-emnlp.164/) and documented three-way labels/evidence | Actual inference quality and suitability for a customer's playbook |
| CUAD source | [Official publisher page](https://www.atticusprojectai.org/cuad/) and linked repository | Actual acquired artifacts, NDA subset, cross-dataset overlap and parser compatibility |
| Existing competitors | [Juro approval documentation](https://juro.com/learn/contract-approval-workflow), [Ironclad playbook index](https://support.ironcladapp.com/hc/en-us/sections/31307199486103-AI-Playbooks) | Independent buyer interviews, competitor evaluation and demand for our wedge |
| Repo fit | Existing five-product docs, Python package configuration and shared provider file layout inspected | New-product code, schema, permissions, tests, startup tasks and port readiness |

Publisher-declared sizes are 607 NDAs/17 hypotheses for ContractNLI and 510 mixed commercial contracts/41 clause types/13,000+ labels for CUAD. Those are source descriptions, not observed local acquisitions. The research did not download datasets, execute their contents, accept a contact-sharing gate, access private accounts or contact customers.

No product tests, UI screenshots, live Codex calls, actual human approvals, pause/restart drills, legal-quality review or Windows deployment checks were performed for ClauseGate. No smoke check is presented as acceptance. During research a guessed direct competitor article URL did not yield usable content; the cited official index supports only the listed feature categories, not the inaccessible article's details.

Next after implementation is authorized: acquire a versioned licensed corpus into isolated data storage, verify hashes/schema/spans/splits and coverage, then create failing test reproductions before writing workflow logic. Required counts/gates are in [data and evaluation](data-and-evaluation.md). Missing or inaccessible data remains blocked rather than replaced with generated contracts labelled real.
