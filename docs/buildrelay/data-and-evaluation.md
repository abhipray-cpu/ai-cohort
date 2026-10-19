# Real data and evaluation

Follow-up: [rigorous actual-data validation](real-data-validation-2026-10-18.md)
has now executed 80 actual real-log analyses and a 36-record fresh GitHub E2E replay
with another 22 actual analyses. Quality/recovery gates failed. The inventory audit
below remains an integrity-only record, not the latest semantic result.

The [19 October corrective report](fixes-and-validation-2026-10-19.md) preserves
those failures, compares generic selector revisions against the same known corpus,
and reports new bounded model/transport campaigns. It must not be relabeled as a
new independent held-out evaluation. See it for the current quality-gate status.

## Captured, not merely proposed

Local capture: `var/validation/buildrelay-capture-2026-10-18/`, gitignored.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| LogChunks ZIP | 24,108,826 | `fa2e3d10fc700cfe06b92b286741666a6389b46548356da9f0679c0d89be7fa8` |
| GHALogs example run JSON | 150,884 | `6385e38a8ab4f1c02ec002d38ccd1f12e7dd56f346117b94755221432f73181b` |
| GHALogs example log archive | 1,177,467 | `b809d1dba727c9cfc6231221e8d55347414d72a7edfbf669e80cded52d8ce43c` |

Capture provenance and hashes are in its `manifest.json`; publisher MD5 also verified
for LogChunks. [LogChunks](https://zenodo.org/records/3632351) is Brandt/Panichella/Beller's
research corpus; [API metadata](https://zenodo.org/api/records/3632351) declares CC BY 4.0.
Keep attribution and review underlying log content rights/privacy before redistribution.
[GHALogs examples](https://github.com/D2KLab/gha-dataset/tree/master/examples) come from
the authors' repository; do not assume every underlying project's logs have one blanket
commercial redistribution licence. Raw research artifacts are not bundled in the app.

The local integrity audit actually enumerated **797 `.log` files, 797 annotations in
80 XML files, 80 repositories and 29 languages**, with no missing log references or
empty annotated chunks. Archive metadata/resource-fork files are excluded from counts.
The structural annotation category must not be confused with our agent's failure class.

The GHALogs example is PyTables/PyTables run `6261949618`, attempt 1, conclusion
`success`. It is useful for testing successful runs and avoiding false incidents,
not a failed-run diagnosis sample. The full [GHALogs publication](https://zenodo.org/records/14796970)
reports 513k runs, but its 142.3 GB log archive was **not** acquired or evaluated here.
BugSwarm access was not confirmed from this environment and is not an acceptance dependency.

## Reproduce capture/audit

Use a new output path each time; never overwrite a failed/previous capture:

```sh
.venv/bin/python scripts/fetch_buildrelay_data.py --output var/validation/buildrelay-capture-new
.venv/bin/python scripts/audit_buildrelay_data.py --corpus var/validation/buildrelay-capture-new --output var/validation/buildrelay-capture-new/audit.json
```

Acquisition and reference integrity are **not AI accuracy**. Current audit explicitly
states `ai_semantic_validation: not_run`, `native_webhook_traffic: false`.

## Evaluation design and remaining independent acceptance

The first bounded campaigns below have now run; see the linked results for counts,
metric corrections and failures. Independent causal/next-step review, live issue
operations and target-host acceptance are still required.

1. Freeze case IDs, source hashes, selection logic and repository-level held-out split.
   Detect duplicate/near-identical failures; do not count repeated logs as independent
   diagnosis coverage. Stratify by languages, log sizes and failure patterns.
2. Use the same bounded evidence selection as the live product; do not insert gold
   chunks into prompts. Report how often the selector omitted annotated evidence.
   LogChunks is Travis data: evaluate interpretation without fabricating GitHub
   Actions URLs/events or pretending it exercises the native GitHub adapter.
3. Run a bounded installed-Codex campaign, preserve failures/timeouts/fallbacks, and
   stop on quota/runtime outages. Do not count manual fallback as a correct diagnosis.
4. Score exact citation validity separately from relevance to the annotated failure
   chunk. Have an independent reviewer judge observed-failure accuracy, hypothesis
   restraint, useful next steps, and client-draft safety. The labels do not prove
   causal root cause, ownership, resolution or calibrated confidence.
5. Obtain a bounded accessible subset of **failed GitHub Actions records** or capture
   actual owned-repository failures for modern adapter/lifecycle validation. Record
   acquisition feasibility instead of promising the 142 GB corpus fits the laptop.
6. Delivery fault tests should include repeated events and crashes around commit,
   model checkpoint, external POST and ACK. Clearly distinguish original real records,
   reconstructed replay envelopes, and synthetic delivery fault permutations.

Suggested acceptance targets must be agreed before results: zero cross-client leaks
and unintended duplicate writes in tested faults; every failed workflow has visible
terminal/retry state; precise grounded failure evidence and useful handoffs on held-out
cases, with an explicit abstention/coverage tradeoff. These are targets, not achieved
real-data results or a guarantee outside the tested workload.
