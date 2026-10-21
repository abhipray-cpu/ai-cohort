# Research and source register

Primary sources checked 20 October 2026. This records published evidence and
our product hypotheses, not market validation, legal advice or retailer certification.
No corpus was downloaded, private account accessed or external message sent.

## Market evidence

| Primary source | What it supports | What it does not support |
| --- | --- | --- |
| [Salsify Grocery Accelerator](https://www.salsify.com/pxm/grocery-accelerator) | An existing vendor markets grocery-specific content validation and AI change suggestions | Our workflow being unique, superior or cheaper |
| [Akeneo AI configuration guidance](https://help.akeneo.com/en_US/serenity-boost-your-productivity/manage-your-ai-configurations) | AI enrichment exists; the vendor explicitly distinguishes it from fact checking and complete source data | That all competing tools lack controls, or a measured market gap |

Inference: agencies may value a focused review/repair tool without a platform
migration. Confirm through workflow observation and a paid bounded pilot. Do not
repeat vendor performance claims as our own expected ROI.

## Real-data feasibility

| Source | Verified published fact | Intended use / limitation |
| --- | --- | --- |
| [USDA API guide, licensing section](https://fdc.nal.usda.gov/api-guide/) | FDC data is published under CC0; normal API access uses a key | Record attribution/provenance; separate customer egress authority still applies |
| [USDA downloadable datasets](https://fdc.nal.usda.gov/download-datasets/) | Branded data is available in CSV/JSON; April 2026 is listed | Freeze a release and stream a bounded subset; availability/eligible counts not tested |
| [Branded Foods documentation](https://fdc.nal.usda.gov/GBFPD_Documentation/) | Data providers supply product facts; nutrient values can use a per-100-g basis | Do not treat a record as an independently verified or current physical label |
| [FDC field dictionary](https://fdc.nal.usda.gov/portal-data/external/dataDictionary) | Documents product identifiers, ingredients, serving metadata and dates | Acquired April 2026 ZIP omitted the guide; the pinned official external PDF was inspected instead. See real-data-validation.md for its hash, age and conservative mapping limits |

The listing currently gives the branded JSON archive as about 195 MB compressed
and 3.1 GB expanded, and CSV as about 428 MB/2.9 GB. Do not assume the whole corpus
fits in RAM. No promise of 1,000 eligible records follows from a download listing.
API demo access is not a bulk-acquisition plan; no private API key is needed for
the proposed public archive path. Do not acquire third-party package imagery.

## Channel requirements

[Google title specification](https://support.google.com/merchants/answer/6324415?hl=en-GB)
documents structured titles and a 150-character content limit.
[Google description specification](https://support.google.com/merchants/answer/6324468?hl=en)
documents structured descriptions and a 5,000-character content limit. Both specify
AI source labelling using `trained_algorithmic_media`. These are frozen profile
inputs, not a complete retailer compliance model or guaranteed approval.

Record page URL, retrieval time, content hash/retained permitted excerpt and the
implemented profile revision. Recheck before a real export release; policy change
does not silently rewrite existing judgments. The output is only a reviewed patch.

## Technical foundations

[Self-Refine](https://arxiv.org/abs/2303.17651) studies iterative feedback/refinement.
It supports investigating the loop, not assuming an improvement for food listings.
[Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) examines judge limitations
including position, verbosity and self-enhancement biases. Therefore freeze rubrics,
blind comparative order, measure judge/human disagreement and retain external checks.

No fine-tuning, autonomous model training or learning of new factual authority is
implied by “self-reflecting.” This is bounded inference-time revision of an artifact.
“Critique reasoning” means an explicit, brief, auditable correction rationale—not
requesting or storing a provider's private chain-of-thought.

## Evidence still needed

Actual download integrity and schema audit; suitable product-family counts; reviewed
field mappings; independently annotated claim support; judge calibration; channel
serializer tests; actual provider/usage checks; browser/target-host testing; buyer
review-time baseline and willingness to pay. These remain open, not research passes.
