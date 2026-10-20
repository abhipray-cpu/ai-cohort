# Research and source register

Later alternative-source work: [Irish FSPO source, inventory and validation limits](fspo-source-and-validation-2026-10-19.md).
Original no-corpus statements below describe the earlier UK/FOS phase. UK source
restrictions remain unchanged; the new Irish cohort is separate.

Reviewed 19 October 2026. This is desk research, not customer discovery, acquired
benchmark evidence or professional legal advice. Facts, interpretations and planned
experiments are separated below. All externally sourced material is linked directly;
no raw decision corpus is bundled with these documents.

## Buyer problem and competitive reality

The [FOS 2025/26 annual data](https://www.financial-ombudsman.org.uk/businesses/resolving-complaint/our-insight/annual-complaints-data-and-insight-2025-26)
reports 13,420 new car/motorcycle insurance cases and a 35% uphold rate for resolved
complaints in that product category. These are different denominators; do not infer
that 35% of those new cases were upheld, or extrapolate a software addressable market.

The current [FOS fee page](https://www.financial-ombudsman.org.uk/businesses/resolving-complaint/case-fees)
lists a maximum respondent fee of £680 and an annual £2,000 allowance. This is
context about escalation economics, not a promise that software avoids fees or an
ROI calculation. Terms change; recheck before customer-facing pricing claims.

[ComplaintLab](https://complaintlab.com/complaint-analyst) advertises AI investigation,
drafting, redress consistency and pre-send quality checks. [Resolver](https://www.resolver.co.uk/resolver-business)
markets complaint-management software. These are vendor descriptions, not independently
verified performance. Generic summaries and letter generation are already competitive.

Inference: a narrow, measured adversarial motor-complaint QA layer could be useful
without replacing an existing case desk. There is no evidence yet that customers
will buy it or that competitors lack equivalent functionality. Validate positioning
and price through paid pilots, not a uniqueness claim about “multiple agents.”

## Real-data feasibility: readable is not licensed

The [official decisions database](https://www.financial-ombudsman.org.uk/businesses/resolving-complaint/ombudsman-decisions/search)
contains published final decisions since April 2013, searchable by product/business
and outcome. FOS says decisions are anonymized and individual, not definitive law
or a universal statement of its approach. Public access was checked during the
preceding research; no bulk case inventory was acquired or counted.

Sample references inspected during research:

| Reference | Research use | Limitation |
| --- | --- | --- |
| [DRN-6054699](https://www.financial-ombudsman.org.uk/decision/DRN-6054699.pdf) | Shows why premium obligations and misleading service communication are distinct issues | Outcome text is mixed with reasoning; not a ready-to-use blind packet |
| [DRN-6195866](https://www.financial-ombudsman.org.uk/decision/DRN-6195866.pdf) | Illustrates the distinction between reviewing an insurer's handling and deciding accident liability | Referenced video/photographs are not supplied as raw evidence |
| [DRN-6158696](https://www.financial-ombudsman.org.uk/decision/DRN-6158696.pdf) | Confirms accessible upheld-case material for potential sampling | Access is not permission for ingestion; individual eligibility remains to be annotated |

**Material correction to the initial feasibility assumption:** the
[FOS legal/copyright page](https://www.financial-ombudsman.org.uk/legal-policy)
permits personal-use extracts but restricts reproduction and storage in another
public/private electronic retrieval system without permission unless specifically
permitted. Do not infer a research/commercial licence from public PDF accessibility.
No permission has been obtained. Bulk download, transformed packet storage, indexing,
model egress and redistribution require a verified applicable permission or other
reviewed legal basis. This documentation does not conclude that one already exists.

Decision G0: obtain the required source clearance, use authorized design-partner
case files with appropriate rights/egress approval, or explicitly revisit source or
product choice with the user. No automatic switch to another similarly restricted
dataset. No outreach/licence application is authorized by this docs-only task.

Public decisions also summarize the evidence rather than expose complete original
files. Rights-cleared retrospective tests alone cannot certify prospective customer
case performance. [Data design](data-and-evaluation.md) defines separate cohorts.

## Technical evidence for the debate design

[Choi, Zhu and Li, Debate or Vote (NeurIPS 2025)](https://arxiv.org/abs/2508.17536)
finds that majority voting accounts for much of observed improvement in the tested
settings. [Voting or Consensus? (ACL Findings 2025)](https://aclanthology.org/2025.findings-acl.606/)
studies how decision protocols affect performance and resource use. Neither paper
establishes useful insurance-review accuracy for this product.

Design inference: first proposals are isolated, ballots are blind to current vote
totals, dissent is retained, and deterministic checks are not outvoted. A same-model
role ensemble is correlated; separate prompts do not establish independent experts.
Compare debate against independent voting and strong single-agent alternatives,
including a cost-matched control, before claiming incremental value.

## Governance references

- [FCA AI approach](https://www.fca.org.uk/firms/innovation/ai-approach): use as an
  accountability/governance reference, not certification of this design.
- [FCA Consumer Duty](https://handbook.fca.org.uk/handbook/prin2a): relevant context
  for fair outcomes; applicability and current rules require qualified review.
- [ICO anonymisation introduction](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/anonymisation/introduction-to-anonymisation/):
  masking identifiers must not be assumed to make a case anonymous or remove data obligations.

We do not copy a universal complaint deadline, compensation formula or retention
period from a competitor. Customer policies must be dated, scoped and approved by
an authorized domain owner. Historical decisions cannot silently become today's rules.

## Evidence status

Known: source pages and examples are accessible; existing products target this
workflow; debate needs baseline comparison. Unknown: corpus permission, eligible
volume, extraction quality, label reliability, expert availability, product accuracy,
review-time savings, willingness to pay and target-laptop performance. These are
open gates, not tasks already completed.
