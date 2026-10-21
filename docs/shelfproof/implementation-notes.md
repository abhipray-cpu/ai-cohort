# ShelfProof implementation map and engineering evidence

21 October 2026. Read [implementation status](implementation-status.md) for the
latest gate result. Code existence, engineering tests, actual inference, independent
quality and physical-host acceptance are different claims.

## Actual modules

| Module | Responsibility |
| --- | --- |
| `packages/contracts/src/contracts/shelfproof.py` | Bounded facts, drafts/claims, findings, fixed five-dimension ratings, correction plans and selection contracts |
| `apps/shelfproof-api/src/shelfproof_api/core.py` | Explicit CSV/JSON mapping/freeze, hashes, Unicode/quantity/literal-reference checks, weighted score and nonregression |
| `store.py` | Isolated WAL/FULL SQLite, users/sessions/roles, snapshots, leases, immutable artifacts, usage journal, review and typed patch export |
| `lifecycle.py` | Finite prepared batches and exact egress/start, policy activation, attributed successor edits, review CSV, dependency-aware logical erasure |
| `operations.py` | New-only backup/restore, quarantine, orphan isolation, bounded same-job resume, append-only verified receipts, constrained owner incident and grant amendment |
| `runtime.py` | Restricted installed-Codex adapter and cooperative Windows/POSIX lock; bounded pipes, process cancellation and nullable audited usage |
| `workflow.py`, `worker.py` | Execute/judge/critique/regenerate loop, two revisions, two attempts/stage, 16 cumulative calls, heartbeats and partial retention |
| `api.py` | Same-origin sessions/CSRF, scoped intake/run/review/export API and production static assets |
| `corpus.py`, `validation.py` | Explicit offline archive/dictionary acquisition, conservative source mapping, engineering workload and approved actual-smoke runner; not automatic startup work |
| `apps/shelfproof-web/src/` | Workspace desk, saved sources/batches, mapping and egress, version/diff/Unicode evidence, independent review, attributed edit, receipts, policy/team and exports |

These modules do not import another product application. Shared installed-Codex
transport is reused additively; existing product code/data/credentials are not copied.

## TDD evidence and important regressions

Focused tests were written/run red before the corresponding contracts, core,
workflow/store, runtime, API, lifecycle, recovery and corpus/validation slices.
Initial collection failures identified missing modules; subsequent behavioural
failures drove fixes. Additional regression coverage was added after implementation;
this is not a claim that every formatting or integration edit was written test-first.

Examples of observed red -> green defects:

- Duplicate headers/JSON keys, nonfinite quantities, missing literal facts and
  restricted claims cannot silently become approved facts/output.
- A higher judge score cannot adopt a new blocking defect or reduced coverage.
- Journal settlement persisted before a DB rollback must open a global hold.
- A later timeout retains an already adopted incumbent, not just version zero.
- Identical text in different iterations retains distinct revision/evaluation
  identities; approval/export uses the selected revision and exact artifact hash.
- Unassessable evaluation stops instead of spending another generation call.
- The actual USDA recovery run exposed an omitted channel profile in independent
  judge context. A failing regression reproduced it; producer and judge now share
  one immutable channel-profile constant without sharing scores or reasoning.
  The prior frozen run had five unassessable channel ratings and one exhausted
  parse retry. The exact old parse cause was not retained; the new bounded retry
  now adds safe actionable guidance without echoing rejected text. Latest actual
  fixed-code measurements are recorded separately in real-data-validation.md.
- Accepted-unknown history follows successor ancestry into UI/review. A red/green
  regression caught a child edit dropping its parent's warning; the recursive
  lineage lookup now preserves the warning and mandatory reviewer acknowledgement.
- A fully terminal run with any manual-review rows cannot pass the live-workflow
  gate merely because another row produced improvement metrics.
- A `missing_source` finding remains blocking even if the model labels it minor.
- Erasure racing a provider result fences that result without crashing the worker;
  newer erasure authority is replayed when restoring an older backup.
- An expired/crashed lease cannot write success or failure state; completed known
  stages survive real child-process termination without repeated inference.
- Fsync failure, stale journal head, unsafe tool receipt, depleted stage/grant/row
  allowance, low disk and duplicate approved product IDs fail closed.

Use `make shelfproof-test` for build/focused Python/frontend tests. The loopback
process test is opt-in (`SHELFPROOF_PROCESS_TEST=1`); skipped is not passed.
JUnit/build totals and paths belong in implementation status, not an invented
real-data pass count. `make shelfproof-up`, status and down were exercised with an
isolated owned fixture and a nonexistent provider command: no startup inference.

## Explicit implementation decisions

- The first fact profile is deliberately narrow: literal brand/name/GTIN,
  net package quantity/unit, ordered ingredients and source reference. It does not
  pretend serving/nutrition data is a package-size source or infer absent facts.
- Separate conceptual DTOs in the design are stored as canonical hashed envelopes;
  all untrusted request/model contracts use Pydantic. Fixed profile/rubric constants
  plus a versioned owner-activated brief replace three mutable policy editors.
- Missing literal required ingredients block and enter constrained repair; they
  are never silently paraphrased/truncated or claimed as an LLM improvement after
  an unrecorded controller insertion. This is stricter than automatic insertion.
- Plans allow up to 40 bounded items to cover up to 20 judge findings plus code
  findings. Excessive/unrepresentable repair contexts degrade to manual review;
  neither item volume nor parse repair adds iterations or call allowance.
- A human edit is an attributed successor task, with parent/source linkage and
  inherited row call/claim consumption. The old task becomes stale; it does not
  retain an export approval. Task totals are not independent product totals.
- Flat uploads are bounded to 25 MiB/1,000 rows/64 KiB per row and parsed off the
  API event loop. There is no claim of an OS-isolated parser or measured Windows
  RAM bound. Archive inventory is separate and streamed, not uploaded to the API.
- Erasure is logical application-content erasure, with secure-delete requested and
  external erasure authority retained. SQLite WAL/storage remnants, independent
  backups and downloaded exports require operator retention/storage handling.
  Expiry prevents further authorized use; retention cleanup is not advertised as
  an automatic secure physical wipe.
- Export is an on-demand current-state typed partial JSON patch and a separate
  UNAPPROVED spreadsheet-safe review CSV. There is no auto-publishing, cached
  feed upload, invented price/stock/URL or reviewer bypass of hard gates.
- Cooperative process locks and CLI feature restrictions are not a hostile-host
  security boundary. Real Windows process-tree/resource/tunnel qualification is
  an acceptance task, not established by POSIX code branches or packaging.

## Validation order and limits

Finish the implementation gate first. Then acquire the official archive into a
new directory, inspect its field dictionary, and explicitly supply that
dictionary hash before curation. Keep raw/normalized hashes and measured exclusions.
The acquired April 2026 archive omitted a dictionary; the tested fallback pins the
official external October 2020 PDF. Its age and mapping limits are recorded in the
validation log; it is not presented as a complete 2026 JSON specification.
Do not substitute brand owner for brand name, serving quantity for package size,
or injected faults for authentic customer mistakes.

The approved initial actual campaign is at most six distinct development products
and 96 cumulative calls, including parse failures and retries. The runner records
that approval in a persistent registry; reusing it cannot create a clean new grant.
It uses actual API/worker/CLI processes, never a fixture provider in actual mode.
It stops on unknown usage and retains pending rows. No automatic incident closure,
model/auth change, independent-human approval or larger baseline campaign occurs.

Browser availability, independent quality labels, paid customer utility, broad
held-out comparisons and actual Windows/Cloudflare acceptance are separate gates.
The acceptance utility reports them pending and exits nonzero; a judge score or
large controlled-provider workload cannot turn them into production acceptance.
