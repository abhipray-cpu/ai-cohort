# Jev: legitimate free-access options

**Measured follow-up:** the user-confirmed jevmodel.org key completed a default-alias
probe and an eight-case actual product smoke run, consuming 40,794 free input tokens
in total. The proxy reported Jev 1.14, but its explicit versioned request required
payment; model identity is not independently attested. Three advisory disagreements
were retained. See [actual evidence](jevmodel-validation-2026-10-24.md), not the older
research-only findings below, for current measured access.

Checked 22 October 2026. Research only: no account created, terms accepted, key
configured, model called, payment made or consumer record sent.

**24 October follow-up:** a user-supplied gateway key authenticated and listed Jev,
but actual Jev 1.14 decision access returned 403 with free-tier/model/credit markers.
Two attempts, zero validated decisions, unchanged reported spend and $0.02 retained
reservations. [Actual campaign](jev-live-validation-2026-10-24.md). The original
research-only statement above describes the earlier checkpoint, not current activity.

## Findings

| Route | Verified published offer | Assessment for RepairClaim |
| --- | --- | --- |
| TypeSafe directly | Jev 1.14 (`jev-1.14.0`) is listed at $0.042 per million input tokens; output tokens are free | Not free inference. No guaranteed free direct allowance or downloadable model weights established. [Official model reference](https://docs.typesafe.ai/models). |
| TypeSafe promotional credits | Credits may be granted at TypeSafe's discretion; not an entitlement | Check the actual account balance and conditions before promising zero-cost use. Do not create extra accounts to obtain credits. [Agreement, section 8.2](https://typesafe.ai/legal/mca). |
| Vercel AI Gateway | $5 monthly free credits cover only the eligible subset of models | Jev is available, but its free-tier eligibility was not established from the current catalogue/account. Buying credits switches the account to the paid tier. Do not assume all catalogue models are free. [Pricing](https://vercel.com/docs/ai-gateway/pricing), [Jev integration](https://vercel.com/changelog/typesafe-ais-jev-1-14-is-now-available-on-ai-gateway). |
| Jagent (`jev-agent.com`) | Advertises five free credits monthly, no card; a credit represents 1,000 input tokens with per-request rounding | Independent, unofficial proxy, not TypeSafe. Tiny public-text smoke-test candidate only; not verified by an actual call. [Service documentation](https://jev-agent.com/docs). |

Jagent explicitly disclaims TypeSafe affiliation and uptime guarantees, can withdraw
the service, and prohibits sending other people's personal data. These restrictions
rule it out for our private consumer-document path. Its monthly allowance is roughly
5,000 input tokens at best, not five arbitrary-length calls or a rigorous evaluation
budget. [Jagent terms](https://jev-agent.com/terms).

An earlier Vercel launch promotion found during research ended on 25 September
2026. It is not evidence of free access on this report's date. Availability of an
open SDK is not availability of model weights or free local inference.

## Recommendation and proposed verification

Prefer a first-party account with confirmed promotional credit if TypeSafe grants
it. Otherwise keep the existing optional-provider boundary; do not add an untrusted
proxy as a silent production dependency. The core workflow remains deterministic
and the current validation campaign made zero provider calls.

If a free public-text probe is requested later:

1. Obtain a legitimate scoped account/key and confirm balance, model availability,
   current terms and zero-spend controls locally. Never paste keys in docs/chat.
2. Explicitly approve the external vendor and a frozen, non-personal test payload.
   No VIN, invoice, address, customer narrative or private case identifier.
3. Pin `jev-1.14.0` if supported and record the returned model/version. Do not assume
   the `latest` alias resolves to it; published alias/release information differed.
4. Bound input tokens and attempts to the confirmed allowance, stop on exhaustion,
   and do not purchase credits, enable refill or retry billable failures silently.
5. Validate actual response schema and provenance. Report advertised versus observed
   access separately. A successful smoke test is not a quality or privacy evaluation.

No Jev-specific implementation or actual Jev acceptance is claimed by this research.
