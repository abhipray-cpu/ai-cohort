# PatchDesk evaluation data

Real captures are intentionally gitignored below `var/patchdesk-corpus/`; no private/customer data or source-provider redistribution rights are assumed. Reacquire using `scripts/fetch_patchdesk_sources.py` as documented in the [runbook](../../docs/patchdesk/operations.md).

Initial feasibility corpus: ten paired commit-pinned snapshots, 11,780 package-location entries. Expanded assessment: **40 distinct inputs from 20 repositories, 33,909 entries, 7,731 installed package/version queries and 778 successful source captures**, frozen in `var/patchdesk-corpus/20261015-quality40-v2/`. Repository splits are 20 development / eight calibration / 12 held-out snapshots, but advisory-family overlap remains. Canonical parsed JSON hashes are recorded, not original wire-byte archives. Acquisition failures are retained; no synthetic input is labelled real.

Independent adjudicated gold does not exist. Repository splits and an independent semantic oracle do exist; they are not expert truth labels. Coverage is release-blocking: 69.15% capture-relative representation, with durable partial reports. [Evaluation design](../../docs/patchdesk/data-and-evaluation.md), [current observed results](../../docs/patchdesk/validation-2026-10-16.md).
