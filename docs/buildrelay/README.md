# BuildRelay — Day 8

An event-triggered CI failure response desk for agencies maintaining client repositories.
Converts completed GitHub Actions events into owned, evidence-backed incidents,
with optional GitHub issue synchronization. It is not an autonomous code fixer.

Current status: **corrective-tested pilot; full acceptance incomplete**. All five
Day 8 concepts have code. The lease-handler crash is fixed; failure-anchor
retention improved from 58.82% to 90.20% on the known development corpus, using a
larger bounded evidence allowance. Fixed-sample lexical citation overlap reached
73/80 (91.25%), not independently verified causal accuracy. Final regression:
533 passed, no skips. See the
corrective report for model-quality outcomes and remaining independent review,
live external-write, browser and Windows/Cloudflare gates. A green suite is not
full product acceptance.

- [Scope and product decisions](product-and-scope.md)
- [Architecture: C4 levels 1–4](architecture.md)
- [TDD implementation plan and coverage](implementation-plan.md)
- [Runbook, security and recovery](implementation-and-operations.md)
- [Actual data and evaluation design](data-and-evaluation.md)
- [Measured implementation evidence](implementation-validation-2026-10-18.md)
- [Historical failed real-data baseline](real-data-validation-2026-10-18.md)
- [Corrective fixes and latest validation](fixes-and-validation-2026-10-19.md)
- [Study guide: concepts mapped to this product and tests](study-guide.md)
- [Blog: building an event-triggered response desk](blog.md)

Start/stop: `make buildrelay-up` / `make buildrelay-down`; port 8007. No other
product's credentials, data, ports or processes are reused. The study guide and
blog explain measured limits; neither implies full release acceptance.
