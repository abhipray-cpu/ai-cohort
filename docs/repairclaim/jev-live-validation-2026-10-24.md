# Live Jev acceptance attempt — 24 October 2026

Follow-up: a separately authorized [free-proxy checkpoint](jevmodel-validation-2026-10-24.md)
completed bounded API/worker integration through jevmodel.org. This does not change
the historical Vercel access failure below or establish full model/product acceptance.

**Blocked, not passed.** The gateway credential authenticates and the catalogue
lists Jev 1.14, but actual native decision access returned HTTP 403. Sanitized
error markers refer to model, free tier and credits. A working key and positive
balance do not establish model entitlement. The earlier conversational claim that
we could use Jev was premature.

## Authorization, boundaries and cost

The user authorized actual E2E testing with a strict $2 ceiling. No credit purchase,
auto-top-up, provider fallback, billing-setting change, private-document egress or
claim submission occurred. The credential was supplied interactively, never saved
in a repository file or printed. Only the owned worker inherited it; the API process
did not. Rotate the chat-exposed credential separately.

Each owned campaign journal allows at most 60 single attempts, reserving $0.01
before each POST, durable across restarts. Current model pricing is checked before
each attempt. Only the pinned `typesafe-ai/jev-1.14.0` is allowed; no long-context
headers, fallback models or automatic retries. Requests are bounded to 100,000 JSON
bytes, with at most 80,000 bytes of approved context. The default model input bound
and observed catalogue price leave ample headroom inside each reservation. Receipt
validation rejects missing/nonfinite/excess cost and unexpected model/probabilities.
This application reservation is not a provider-side account spending-limit change.

| Retained campaign | Actual native POST attempts | Validated decisions | Reserved usage | Observed account spend delta |
| --- | --- | --- | --- | --- |
| `jev-20261024-a` | 1 | 0 | $0.01 | $0 |
| `jev-20261024-b` | 1 | 0 | $0.01 | $0 |
| Combined | 2 | 0 | $0.02 | $0 |

Neither attempt returned a usable billing receipt, so the reservations remain
unknown rather than being released as proven free calls. Before/after account
balance and total usage were identical in both runs. This is an observed snapshot,
not proof against delayed billing. No further live attempts were made. A subsequent
campaign must include these held reservations in the user's cumulative $2 ceiling;
creating another journal does not renew that authorization.

The first run lacked sufficient safe error diagnostics and was retained unchanged.
The second added only field names, status, fixed vocabulary error markers and answer
field names—no raw server messages, request text or credential. It recorded:
`403 /typesafe/v1/systemone`, with model/credit/free/tier markers. First-run cause
is not retroactively asserted as identical. Both stopped at the first case; zero
of the planned 48 live case evaluations completed. Historical reports' zero failed
case counter reflects early interruption before a result was appended, not success;
the harness now explicitly records halted status and the interrupted failing case.

## Actual product path exercised

The previous implementation had only rules and optional installed-Codex advice.
A native Jev adapter was necessary before an honest Jev product test could start.
It was added behind `REPAIRCLAIM_ENABLE_JEV=0` by default, following an observed
missing-module red followed by passing boundary tests.

Actual path: frozen official PDFs and explicitly authored facts → isolated
authenticated HTTP API → owner-approved exact Jev-destination context fingerprint
→ durable queued job → real worker → pinned native gateway POST → access denial
→ persisted partial job with its deterministic rule checkpoint and attempt audit
→ no automatic retry → case erasure and owned-process shutdown.

The correct endpoint is `/typesafe/v1/systemone`, not `/v1/chat/completions`.
Jev returns Choice distributions and Noul probabilities, not arbitrary structured
generation. This adapter separately stores `jev_advice` and validated usage receipts;
it does not manufacture LLM citations or overwrite rule decisions. Disagreement,
Choice confidence below 0.7 or human-review probability at least 0.3 routes to human
review. These are provisional application thresholds, not calibrated accuracy.

Jev's approval preview explicitly names Vercel and the pinned model. A Codex-bound
approval cannot authorize Jev egress. The minimized context excludes VIN, invoice,
address, credentials, case/household identifiers and raw private documents. It adds
the user-attributed in-service date needed for date-window checks and reviewed
programme conditions. Unit tests use fixture data; live inputs used only the frozen
public-source corpus and authored boundary facts, not genuine consumer invoices.

This path is API/worker-enabled. No Jev control or rendering has been added to the
browser interface, and browser E2E is not claimed. The broader consumer/inventory,
independent-label and Windows acceptance shortfalls are unchanged.

## Evidence and reproduction

Post-change scoped verification: 174 Python tests passed, three optional process
tests skipped in the normal invocation, three frontend tests passed, production
build and lint passed. Twelve Jev boundary tests use simulated HTTP and establish
protocol/scope/budget/fault behaviour, not live model accuracy. They include durable
budget exhaustion, timeout/403 holds, invalid model/distribution/cost rejection,
exact-destination approval, persisted receipts and disabled-by-default HTTP gating.

Full repository regression with RepairClaim process tests enabled: **1,027 passed /
five existing optional skips**, six upstream warnings, 114.41 seconds. Artifact:
`var/repairclaim-jev-regression-20261024.xml`. Owned short-runtime PostgreSQL and
actual native parser/API/worker process checks ran; no assertions were mocked out.

Local ignored artifacts:

- `var/repairclaim-validation/jev-20261024-a/report.json`
- `var/repairclaim-validation/jev-20261024-b/report.json`
- Each run's `jev-budget.sqlite3` and process log; second run additionally has
  `jev-budget.diagnostic.json`. No credential is contained in these artifacts.
- `interpretations.json` and `scenarios.json` were frozen before each run. The public
  source corpus is the [22 October freeze](real-data-validation-2026-10-22.md).

```bash
make repairclaim-test repairclaim-lint
# Only after verifying Jev access and remaining cumulative authorization:
.venv/bin/python scripts/repairclaim_public_e2e.py \
  --corpus var/repairclaim-validation/public-20261022-b \
  --out var/repairclaim-validation/NEW-UNUSED-DIRECTORY --jev
```

The CLI prompts without echo, never enables Codex or source-refresh network calls,
and starts only isolated owned API/worker processes. Do not rerun blindly while
model entitlement is denied. The example environment documents the opt-in and
durable budget path; no live account configuration was changed.

## External blocker and next authorized step

Vercel's current documentation distinguishes a restricted free-model subset from
the paid catalogue; listing a model does not establish eligibility. Purchasing
credits changes tier and monthly-free-credit eligibility. This campaign did not
make that account change. The user/account owner must establish Jev entitlement
or supply an authorized direct TypeSafe route before another live acceptance run.
Do not use a different model and label it Jev, or call this blocked campaign a pass.
[Vercel pricing](https://vercel.com/docs/ai-gateway/pricing).

Native protocol and response reference:
[Vercel TypeSafe API](https://vercel.com/docs/ai-gateway/sdks-and-apis/typesafe),
[Choice](https://docs.typesafe.ai/primitives/choice),
[Noul](https://docs.typesafe.ai/primitives/noul).
