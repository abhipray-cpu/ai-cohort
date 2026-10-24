# Free-proxy live checkpoint — 24 October 2026

Subsequent [actual public complaint metadata campaign](public-complaint-validation-2026-10-24.md)
used another 25,834 free input tokens; latest observed remaining allowance is 33,372.
Balances below describe this earlier frozen run, not the current remaining grant.

**Bounded API/worker integration passed; full product acceptance and model-quality
acceptance did not.** The user confirmed that the supplied key belonged to
jevmodel.org and authorized testing. No credential was saved in repository files,
printed, sent to Vercel or committed. No credit pack, subscription, automatic refill
or billing change was made. The key was entered without echo and inherited only
by the owned worker, not the API process. Rotate the chat-exposed key separately.

## Access observations, not advertised guarantees

| Probe | Observed response |
| --- | --- |
| Explicit `jev-1.14.0` | HTTP 402 `payment_required`; service says versioned access needs a paid plan |
| Documented default `jev-latest` | HTTP 200; service returned `model: jev-1.14.0`, valid Noul answer, 293 input tokens used and 99,707 remaining |

These responses are inconsistent with treating all access to 1.14 as paid-only.
We used only the service's documented default route, not a hidden endpoint, billing
override or spoofed credential. The live adapter requests that alias and accepts
only the currently observed returned version; another returned version halts the
campaign. The proxy's version field is **self-reported, not an independent upstream
model attestation**. Availability and alias resolution can change. This does not
prove direct TypeSafe access or unblock the separate Vercel account.

## Scope and execution

Using the [22 October frozen public corpus](real-data-validation-2026-10-22.md),
the campaign registered one initial exploratory Accord-condenser configuration,
ran eight authored boundaries, then added historical/revised Pilot programmes for
the source-change check. Eleven parsed PDFs were captured in the isolated state,
but only selected reviewed anchors were sent; this is not eleven distinct programme
families or eleven actual consumer documents.

Actual path: authenticated socket HTTP → household/revision checks → exact preview
approved for **jevmodel.org / jev-latest** → durable investigation → actual worker
→ native proxy POST → strict Choice/Noul/version/usage/balance validation → persisted
advisory and token receipt → manual review when indicated. Deterministic rules remain
authoritative. A Vercel-bound approval cannot authorize the proxy route.

Measured campaign:

- **8/8 engineering scenarios passed**, using real official-source bytes and clearly
  authored repair facts. They are not independently reviewed accuracy labels.
- **11/11 native decisions validated**, including the post-upload re-investigation
  and two historical/revised-source investigations. No automatic retries.
- One actual four-page official PDF upload, real restricted parsing and cross-household
  denial; the document was classified `other`, never presented as a customer invoice.
- One actual queued packet-render, sanitized attachment, preapproval denial, exact
  fingerprint approval, CSRF-protected ZIP download, manifest/PDF hash verification
  and denial after revocation.
- Source evolution: deterministic outside-condition finding changed to potentially
  applicable; one consented notification, monitoring revocation and case-erasure
  access denial all passed. Future repair dates are labelled authored boundaries.
- All owned API/worker processes stopped and test cases were erased. No submission
  was sent to a dealer, manufacturer or consumer.

The scoped campaign took 37.23 seconds. This is not a production latency/load test,
browser test or Windows/tunnel deployment qualification.

## Semantic failures retained

The native advisory disagreed with the rule result **three times out of eleven
calls**, including dependent/repeated inputs. This is not an independent accuracy
benchmark or an estimate of general performance.

| Scenario | Rule result | Proxy advisory | Confidence | Product disposition |
| --- | --- | --- | --- | --- |
| Accord one day past anniversary | Appears outside conditions | Potentially applicable | 0.49 | Manual review; rules unchanged |
| Pilot historical programme | Appears outside conditions | Potentially applicable | 0.51 | Manual review; rules unchanged |
| Pilot revised programme | Potentially applicable | Appears outside conditions | 0.45 | Manual review; rules unchanged |

Six decisions had Choice confidence below 0.7. All eleven jobs ended in manual review
because of uncertainty, disagreement and/or manufacturer-verification probability.
This demonstrates conservative routing; it does not demonstrate autonomous coverage
assessment or a useful reduction in human effort. Thresholds remain provisional.

The eight-case engineering pass means the expected rule outcomes and control flows
worked while actual advisory calls were validated—not that Jev answered every case
correctly. The earlier progress update noted two disagreements before the final
revised-source call finished; the final audited total is three.

## Free allowance and monetary accounting

| Measure | Observed |
| --- | --- |
| Successful standalone probe | 293 input tokens |
| Actual API/worker campaign | 40,501 input tokens over 11 calls |
| Combined successful usage | 40,794 input tokens |
| Remaining proxy allowance | 59,206 tokens, reported by `X-Tokens-Remaining` |
| Payments/purchases/refills made | None |
| USD billing receipt | Not returned; `cost_usd` is null, not a fabricated zero |

The adapter enforces a persistent **90,000-input-token / 16-attempt campaign limit**,
reserving conservative byte-based capacity before sending each two-question request.
Known usage settles the reservation. Missing/invalid usage, balance, version or
distribution leaves an unknown reservation and stops subsequent calls. No automatic
retry, vendor fallback or arbitrary base URL is supported. The host is fixed.

The retained first campaign's `reserved_usd: 0.11` was a legacy harness display of
eleven nominal $0.01 attempt allowances—not an actual proxy dollar charge or
provider-side reservation. The harness now uses null for proxy USD reservations
and reports token accounting separately. The original report remains unchanged.
The earlier Vercel attempts retain $0.02 conservative unknown-use allowances; no
claim that those were conclusively settled is made. Do not reset the user's
cumulative $2 monetary authorization by creating new journals.

## TDD and regression evidence

The first proxy-boundary test collection failed because its module was absent;
after implementation, six new tests pass. They cover fixed host/default alias,
honest non-USD receipts, unknown-model/missing-balance holds, token-budget refusal,
restart persistence, distinct destination approval and actual worker settlement
using simulated HTTP. These are not live model-quality evidence.

Post-change scoped run: **180 Python passed / three optional process skips**, three
frontend tests, build and lint passed. No Jev browser controls were added or tested.

Full repository regression with actual RepairClaim process checks enabled:
**1,033 passed / five existing optional skips**, six upstream warnings, 114.49
seconds. JUnit: `var/repairclaim-jevmodel-regression-20261024.xml`. Temporary
PostgreSQL and actual restricted-parser/API/worker checks ran without mocked-out
assertions.

Local ignored evidence:

- `var/repairclaim-validation/jevmodel-20261024-probe-a/`: paid-plan rejection.
- `var/repairclaim-validation/jevmodel-20261024-probe-b/`: successful default-alias probe.
- `var/repairclaim-validation/jevmodel-20261024-e2e-a/report.json`: actual decisions,
  confidence, rules comparisons, receipts, frozen interpretation/scenarios and checks.
- Same campaign directory: durable budget DB, owned-process log, actual downloaded
  packet PDF and manifest. No raw private consumer records or account secret.

## Reproduction and remaining gates

```bash
make repairclaim-test repairclaim-lint
# Explicit user-approved third-party route; prompts without echo.
.venv/bin/python scripts/repairclaim_public_e2e.py \
  --corpus var/repairclaim-validation/public-20261022-b \
  --out var/repairclaim-validation/NEW-UNUSED-DIRECTORY \
  --jev --jev-route jevmodel --families 1
```

Do not rerun while assuming the original 100,000-token grant is untouched. Confirm
remaining capacity and cumulative authorization first. No private invoice, VIN,
address or third party's customer information may be sent through this route.

Full acceptance still needs the original corpus volume and independent labels,
consented private cases/outcomes, browser interaction, specialist interpretation,
Windows/tunnel qualification and demonstrated model usefulness. This bounded pass
does not satisfy those gates and is not a 100% MVP acceptance claim.

Service protocol/limitations: [API documentation](https://jevmodel.org/docs/).
Independent-provider status and private-data restrictions:
[service terms](https://jevmodel.org/terms/).
