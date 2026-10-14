# ResolveDesk data

`manifests/smoke-cases.json` contains explicitly labelled public/adapted smoke inputs with provisional expectations, not a gold benchmark. The acquisition script creates `manifests/sources.json` with official document URLs, versions, capture dates, and hashes. Raw acquired HTML is ignored by Git.

Acquisition: `.venv/bin/python scripts/fetch_resolvedesk_sources.py --data-dir var/resolvedesk`. Existing frozen files are verified and reused; changed content requires an explicit new corpus revision. Preserve PostgreSQL copyright/license notices in original HTML; see [the PostgreSQL license](https://www.postgresql.org/about/licence/).

Use separate raw/extracted/gold/adversarial/manifests collections as the evaluation grows. Public reports and links are question sources, not automatically authoritative answers. No customer tickets, independent gold labels, or reproduced database errors have been acquired in this starter manifest.
