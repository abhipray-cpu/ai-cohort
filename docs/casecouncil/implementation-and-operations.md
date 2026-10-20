# CaseCouncil implementation and operator runbook

20 October recovery update: [sanitized diagnostics and audited same-job recovery](recovery-fix-2026-10-20.md)
are implemented. The original real-case unknown receipt remains held; no fabricated
receipt, reset budget or fresh workspace was used to continue the campaign.

19 October 2026. Implemented engineering pilot, **not production or real-data
acceptance**. Start with [current evidence](implementation-validation-2026-10-19.md)
and [remaining gates](implementation-status.md). No FOS corpus was acquired.
The later [Irish FSPO source report](fspo-source-and-validation-2026-10-19.md)
records actual-corpus acquisition/local checks. External-model egress for those
real excerpts remains blocked pending explicit payload/destination approval.

## Implemented versus designed

| Boundary | Actual implementation |
| --- | --- |
| Strict wire contracts | `packages/contracts/src/contracts/casecouncil.py`: proposals, counterarguments, critique, ballots, synthesis, policy, rights and review; forbidden extras and finite bounds |
| Three independent proposers | `controller.py`: customer, insurer, fairness, without initial peer answers; one optional revision after a separate non-voting critic |
| Frozen voting and consensus | `consensus.py`: exact candidate equivalence, retained role lineage, snapshot/registry-bound blind ballots, fixed roster of three, explicit abstention/unavailability and deterministic blocked/no-consensus outcomes |
| Confidence and synthesis | Controller-owned low/medium **uncalibrated** labels, retained dissent and missing evidence; source-validated synthesis cannot author votes or approval; incomplete work remains a manual packet |
| Intake and citations | `evidence.py`, `pdf_worker.py`: TXT/PDF, bounded child parsing, redacted canonical text, source hashes, selected coverage, exact Unicode quote offsets; no OCR or invented page mapping |
| Durable authority | `store.py`: SQLite schema 2, sessions, scoped roles, revisions, idempotency, leases, checkpoints, maker/checker review, export, erasure and audit chain |
| Installed Codex port | `runtime.py`: shared `agent-core` provider, restricted features/tools/environment, bounded process streams and output, actual usage receipts, cancellation and timeout |
| Recovery and cost liability | `journal.py`, `backup.py`: fsynced external usage chain, unknown-call hold, new-root quarantined restore and explicit operator reconciliation |
| Workbench | `apps/casecouncil-web`: React/TypeScript case intake, administration, preview, stage polling, proposals/critic/votes/dissent, exact-source drawer, review, export, audit and erasure |
| Evaluation | `evaluation.py`, `scripts/validate_casecouncil.py`: authorized local manifests, paths/hashes/rights/dedup/splits/leak flags, isolated gold, bounded campaigns and baselines; no scraper |
| Process operations | `worker.py`, additive launchers, Make targets, Windows Task Scheduler packaging and protected Cloudflare example on loopback 8008 |

Conceptual auth/intake/roles/synthesis/audit components are deliberately grouped in
the modules above, not separate empty packages. Sources (including original bytes),
checkpoints and packets live in the product SQLite database, rather than external
artifact files. This makes the SQLite backup a consistent artifact set. The usage
authority is a **separate append-only file**, not rewound with an older database.

Citations use `(source_id, start, end, quote)` and validate containment in selected
evidence spans; there is no redundant model-provided `span_id`. The browser converts
Python Unicode offsets rather than treating them as JavaScript UTF-16 indices.
Policy has a fixed role/consensus/resource protocol; owners may activate versioned
instructions, required document kinds and egress—not redefine voting rules.

Normal debate uses 8 calls; one material/critical-critique revision makes 11.
One repair per stage permits at most 22 calls cumulatively, including restarts.
Each call has 90 seconds, each run 30 minutes, one active worker job globally.
Evidence is bounded to 64,000 characters; full prompt/schema to 256 KiB; model output
to 100 KiB; streamed stdout/stderr to 1 MiB/64 KiB. Missing coverage is visible.
Baselines are `single` (2 normal calls), `vote_only` (7), `single_refine` (11);
these are actual controller modes, not renamed debate runs. Equal-call/resource
comparisons and independent domain scoring remain real-evaluation obligations.

## Install and run locally

From the repository root, use the existing Python 3.12+ virtual environment:

```sh
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
npm --prefix apps/casecouncil-web ci
make casecouncil-up
make casecouncil-status
make casecouncil-down
```

The editable install assumes workspace dependencies are already installed. For a
fresh environment install the repository's Python dependencies first. Configure
these **product-specific** variables in `.env` before `up`:

```dotenv
CASECOUNCIL_USERNAME=owner
CASECOUNCIL_PASSWORD=<unique password of at least 12 characters>
CASECOUNCIL_HOST=127.0.0.1
CASECOUNCIL_PORT=8008
CASECOUNCIL_DATA_DIR=var/casecouncil
CASECOUNCIL_CODEX_COMMAND=codex
CASECOUNCIL_SECURE_COOKIES=false
```

Use the installed Codex executable available to the service account; no direct LLM
API key or remotely exposed Codex endpoint. Local CLI execution does **not** imply
offline inference. Configure authentication under that account and explicitly
authorize redacted-context egress. Set secure cookies true for the HTTPS tunnel;
keep false only for local loopback HTTP. No default password or other product's
credentials are inherited. Credential bootstrap is not a password-rotation API.

Open `http://127.0.0.1:8008`. Sign in, create a workspace, activate its review policy,
record current source rights and egress permission, create a case and upload its
authorized complaint/policy. Confirm issues, facts, draft and missing evidence.
Read the exact egress preview before starting. Create a separate reviewer account
and workspace membership for maker/checker approval. Inspect source quotes, critic,
votes and review questions; resolve blockers with attributed reasons. A download
is a local artifact, never an automatic customer send. Retained human overrides do
not change automated votes. Draft and reviewed-current exports have different labels.

## Actual HTTP surface

All `/api` requests authenticate; mutations require session CSRF and same-origin
checks. Core mutations require `Idempotency-Key` and expected revision where relevant.

| Routes | Purpose |
| --- | --- |
| `POST/DELETE /api/session`, `GET /api/me`, `POST /api/users` | Explicit accounts and hashed, revocable sessions |
| `GET/POST /api/workspaces`, `GET /api/workspaces/{id}` | Scoped workspaces |
| `GET/PUT /api/workspaces/{id}/members`, `PUT .../policy` | Owner administration and policy revision |
| `GET/POST .../rights`, `DELETE .../rights/{id}` | Rights attestation and revocation; not automatic legal verification |
| `GET /api/workspaces/{id}/cases`, `POST /api/cases`, `GET/PUT /api/cases/{id}` | Case intake/context revisions |
| `POST /api/cases/{id}/sources`, `GET /api/sources/{id}` | Bounded upload/replacement, authorized canonical source display |
| `GET /api/cases/{id}/egress-preview`, `POST/GET .../runs` | Exact snapshot authorization, scheduling and history |
| `GET /api/runs/{id}`, `POST .../cancel`, `POST .../reviews` | Checkpoints, receipts, packet, cancellation and attributed human review |
| `GET /api/runs/{id}/export` | JSON or escaped HTML, optional current-reviewed requirement |
| `GET /api/workspaces/{id}/audit` | Scoped audit pagination (200 events/page) |
| `GET /api/cases/{id}/erasure-preview`, `DELETE /api/cases/{id}` | Dependency-aware case erasure |
| `/health/live`, `/health/ready` | Safe liveness; schema/worker-heartbeat/journal readiness |

Readiness explicitly returns `model_connection_verified: false`; it is **not** an
authenticated provider smoke or semantic-health guarantee. No background health
call sends case evidence. Worker receipt/unknown-usage holds can block new dispatch
even while the HTTP process is alive. There is no UI “clear unknown usage” bypass.

## Engineering checks

```sh
make casecouncil-test
CASECOUNCIL_PROCESS_TEST=1 make casecouncil-acceptance \
  CASECOUNCIL_ACCEPTANCE_ARGS='--engineering-only --output var/validation/casecouncil-my-run'
```

Output directories must be new. Process tests start their own loopback API and
controlled-provider worker; they are not actual model accuracy tests. Without
`CASECOUNCIL_PROCESS_TEST=1`, the socket integration is skipped, and the acceptance
collector reports engineering checks incomplete. Without `--engineering-only`,
the acceptance command intentionally exits 1 because full release gates remain open.

Explicit actual-model smoke (owned fictional material, up to 22 calls):

```sh
.venv/bin/python scripts/smoke_casecouncil.py --live \
  --output var/validation/casecouncil-owned-smoke-new
```

## Authorized real-data phase — not performed

UK/FOS G0 remains blocked. An alternative Irish retrospective cohort exists;
source reuse does not itself approve model egress. Do not bulk-download FOS decisions on the assumption that public
access permits storage or commercial use. Obtain applicable permission/reviewed
legal basis or authorized partner files, with approved model egress and independent
domain reviewers. Follow [data design](data-and-evaluation.md) and
[acceptance gates](validation-and-acceptance.md). Audit locally first:

```sh
.venv/bin/python scripts/validate_casecouncil.py --corpus /path/to/authorized-corpus \
  --output var/validation/casecouncil-inventory-new
```

`manifest.json` schema 1 contains `permission` (basis/reference/expires/egress) and
1–500 `cases`: opaque `id`, independent `group`, `split` (development/calibration/test),
`cohort` (authored_fixture/retrospective_decision/prospective_case_file), typed `context`,
`documents` with `path` under `inputs/`, `kind` and `sha256`, plus `gold_path` under
`gold/`. Tests provide an engineering-only manifest example. Outcome-labelled final
decisions are not pre-decision input; flagged leakage needs independent review.

After authority and inventory are accepted, explicitly budget a development campaign:

```sh
.venv/bin/python scripts/validate_casecouncil.py --corpus /path/to/authorized-corpus \
  --output var/validation/casecouncil-development-new --live --authorize-egress \
  --rights-reviewed-reference 'Reference to reviewed source and egress authority' \
  --mode debate --split development --limit 1 --max-calls 22
```

No silent escalation of count/quota or replacement of failed cases. The runner
preserves progress and denominators, opens gold after inference, and deliberately
does not self-certify full product acceptance. Agreement with published outcomes
is not independent prospective accuracy, calibrated confidence or customer utility.

## Backup, recovery and erasure

Backups are **plaintext SQLite**, not application-encrypted. Require encrypted
storage and service-account ACLs; `--acknowledge-plaintext` is mandatory. Protect
`DATA_DIR/authority/usage.jsonl` independently and keep its latest state, including
receipts later than the snapshot. Losing/replacing it must not reset call liabilities.

```sh
.venv/bin/python scripts/casecouncil_backup.py backup --data-dir var/casecouncil \
  --output /protected/backup-new.sqlite3 --acknowledge-plaintext
.venv/bin/python scripts/casecouncil_backup.py restore \
  --snapshot /protected/backup-new.sqlite3 --target var/casecouncil-restored-new \
  --authority /protected/latest-usage.jsonl
```

Stop application processes before switching stores. Restore requires a new target,
verified standalone snapshot/manifest and matching current authority chain. It
changes the restore epoch, revokes sessions, makes past jobs stale and quarantines
dispatch. Only after independent reconciliation may an operator run
`authorize-restored-runtime --data-dir ... --expected-head ... --reason ...`.
Unknown/unsafe usage remains blocked; an acknowledgement cannot mark it free.
No old job is automatically replayed. Investigate integrity incidents without
editing receipts or hashes to manufacture a pass.

Case erasure removes runtime case evidence/context/checkpoints/reviews and fences
jobs, retaining minimal accounting/audit metadata. It does not recall exports,
backups, model-service egress or the filesystem's historic blocks. Retention and
legal erasure obligations need an approved operational policy.

## Target-host qualification still required

Windows packaging: `infra/windows/install-casecouncil.ps1 -RepoPath <repo>
-Credential <limited-account> [-Start]`, separate API/worker startup tasks refusing
replacement. It is not an SCM service or proof of restart acceptance. Protect the
8008 hostname with Cloudflare Access on **all** paths; no webhook exception.

PDF child input/page/text/time bounds apply on all hosts. Linux additionally uses
an address-space limit; macOS/Windows currently have **no qualified hard memory
sandbox**. Windows process-tree cancellation, ACLs, disk exhaustion, sleep/reboot,
recovery objectives, tunnel auth, browser/accessibility and sustained load require
actual target-host tests. Audit hashes are corruption evidence, not protection
against a privileged administrator rewriting the entire store and authority.
