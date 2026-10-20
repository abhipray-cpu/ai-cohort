# Three agents agreeing is not enough: building CaseCouncil

*Day 9 of our 14-day, 12-product challenge.*

An insurance complaint can contain several plausible stories. The customer
describes one sequence of events. The provider explains its handling differently.
A proposed response may sound convincing while leaving a contractual question,
service failure or missing document unresolved.

That is the problem behind CaseCouncil: an advisory second-review desk that
challenges a complaint response before a separate human reviewer approves it.
Its intended value is a better-supported handoff, not an automated claims decision.
Whether it improves review quality or effort enough to justify its cost remains
a product hypothesis, not something we have proven by adding agents.

The Day 9 concepts were multiple proposals, critique, voting, consensus and synthesis
with confidence. Building them into a service made one distinction central:
**a model may propose an interpretation; the application owns the decision rules.**

## Give the roles different jobs

CaseCouncil starts with three isolated proposal contexts: customer, insurer and
fairness. Each sees the authorized evidence and confirmed issues, but not the
other initial answers. Each returns structured alternatives with citations,
conditions, counterarguments and missing evidence.

The customer role must make the strongest supported case, not demand compensation
regardless of evidence. The insurer role tests handling, not automatically defends
it. The fairness role considers supported alternatives without claiming adjudicatory
authority.

This limits initial copying between roles. It does not make them independent
experts. They can share a model, share assumptions and make correlated mistakes.
Counting their agreement as a probability of correctness would be misleading.

## Let critique challenge, not decide

A separate non-voting critic examines the proposals. Material or critical findings
trigger at most one revision cycle. The roles must respond to the findings, but
their own declaration that a concern is resolved cannot remove the need for
human review.

Keeping critique separate from voting matters. The critic should surface a
contradiction or evidence gap, not acquire an extra vote or rewrite the policy.
It is a structured challenge mechanism—not a trusted oracle.

Our real-case critics all returned no findings. That demonstrates execution of
the stage, not effective defect detection. Revision is covered by authored tests;
its real-case quality still needs independent assessment.

## Freeze the choices before asking for votes

After proposals and any revision, the controller freezes a candidate registry.
Exact-equivalent candidate payloads merge with their role lineage preserved.
The same disposition with a different remedy or conditions remains a different
alternative.

Each ballot binds the evidence snapshot and registry hash. It can select a known
candidate or explicitly abstain; it cannot introduce a new option during voting.
Invalid roles, stale snapshots and unknown candidate references are rejected.

The denominator stays three. Two matching votes and a missing participant are
not silently presented as a unanimous two-person panel. A valid abstention is
also different from a role that never returned a valid ballot.

## Consensus belongs in ordinary code

The vote counter is deterministic Python, not another model asked to announce
who won. It checks participation, counts candidates, retains dissent and applies
evidence and critique blockers.

A majority can exist while a recommendation remains unqualified. Missing decisive
evidence does not disappear because two agents chose the same answer. A winning
`undetermined` alternative does not become a supported determination either.

Confidence is deliberately limited to low or medium, both uncalibrated. Two votes
out of three are a voting fact, not a 67% correctness estimate. The synthesizer
adds an advisory narrative around the stored result; it cannot rewrite the recorded
votes or mark the packet approved. Its prose still needs substantive review.

## Citations are a boundary, not a truth machine

Pydantic contracts validate structure and bounds. Application checks validate issue
coverage, ballot identities and exact source quotations within permitted spans.
The UI maps Python Unicode offsets correctly before highlighting text in JavaScript.

Those checks answer useful questions: is the output well formed, and does the
quoted text actually exist? They do not establish that an allegation is true or
that a citation supports every inference made about it.

That distinction also affected the interface. A developer spot-check found internal
vote metadata in some generated summaries. The workbench now labels that output
an advisory review summary, not a customer letter. The human response editor starts
with the handler's own draft rather than copying AI voting metadata into a response.

## The important failure arrived halfway through a ballot

The first approved real-data run completed two cases. On the third, a later ballot
call exited without known usage or a verified tool audit. Earlier proposals and
the critic were available, but the campaign stopped with three cases unstarted.

The service correctly retained partial work and opened a hold. The operational
problem was what happened next: a lost provider receipt may not be reconstructible.
The original failure also lacked enough retained diagnostics to prove a root cause.
Calling it a quota or network problem would have been speculation.

We added bounded, sanitized failure diagnostics and an evidence-based recovery
path. Then, with explicit owner approval, we implemented a separate policy for an
irrecoverable incident.

That policy does not invent usage or declare the historical invocation safe. It
retains the unknown receipt and full reserved call/time charge, requires stopped
runtime isolation attestation and an exclusive cooperative worker lock, and permits
one incident closure per store-authority lifetime. Explicit unsafe-tool or integrity
incidents are not eligible. Resuming work is a separate, bounded authorization.

The recovered job reused its three proposers and critic. Only the three ballots
and synthesis ran again. The incident remains visible and requires reviewer
acknowledgement; even a reviewed export retains its unknown-usage warning.

Recovery should make unfinished work usable without changing what happened.

## Put accounting somewhere a database rollback cannot erase

The service stores evidence, checkpoints and packets in SQLite, with a separate
fsynced usage-authority journal. Incident closure and the cumulative research call
ceiling are recorded in that independent chain.

The continuation kept the original store and counted every original attempt.
The 132-call ceiling could not be raised by another grant or reset through another
workspace. A backup restore retained authority and quarantined old jobs instead
of automatically running them again.

This is not tamper-proof protection against a hostile host administrator. It is
a practical boundary against accidental rollback, blind retry and erased accounting.

## What the real-data work actually showed

We acquired 132 actual Irish FSPO motor-insurance decisions and prepared 122 usable
party-summary excerpts. Local checks across those 122 cases used an explicit test
provider; they were not real-model accuracy results.

Only six development excerpts were approved for the configured model service.
After recovery, all six had complete proposal, critic, ballot and synthesis artifacts.
Across the original and continued work there were 49 calls: 48 known receipts and
the one explicitly accepted historical unknown. A read-only recheck verified 71
exact citation occurrences and recomputed all six consensus results.

Five invocation histories were fully audited. The recovered case was not. The
report therefore separates complete artifacts from a fully audited campaign pass
and deliberately retains a nonzero acceptance exit status.

All six packets remained low confidence with zero qualified issues: the summaries
did not contain the full original policy and case files. Two results were agreement
blocked and four had no consensus. No real packet was human-approved and no response
was sent to a customer. Six development cases are not a held-out quality benchmark.

The final engineering regression passed 681 Python tests with zero skips, including
148 CaseCouncil tests. Six frontend tests and the production build passed. An
actual-data local backup/restore drill retained all attempts and the incident,
revoked sessions and left six jobs stale in quarantine. These are engineering
and local recovery results, not browser, Windows or independent domain acceptance.

## A delivery checkpoint, with the claims kept narrow

The user accepted this checkpoint as sufficient to complete the Day 9 learning
cadence. That does not turn unresolved release evidence into a pass.

Interactive browser acceptance, the actual Windows laptop and protected tunnel,
qualified domain review, and authorized prospective UK case files remain open.
The Irish research replay does not certify UK complaint handling. Debate has also
not yet demonstrated a quality or review-effort advantage over matched baselines.

The architecture still targets a service on an old Windows laptop, using an adapter
to locally installed Codex. Local execution is not a claim of offline inference;
approved context may reach its authenticated model service.

The lesson from CaseCouncil is that multi-agent debate needs more than contrasting
prompts. It needs frozen alternatives, explicit participation rules, durable stages,
bounded recovery and a record that distinguishes agreement from evidence.

The strongest result is not always a confident recommendation. Sometimes it is a
clear account of the disagreement, the missing material and why a person must decide.

---

Engineering references: [study guide](study-guide.md),
[architecture](architecture.md), [measured continuation](real-data-continuation-2026-10-20.md)
and [incident policy](incident-closure-2026-10-20.md).

Publication note: this is a draft engineering retrospective, not an endorsement,
legal claim or production-readiness announcement. No case narratives, source quotes
or corpus files are reproduced here. Source reuse/publication constraints remain
subject to the [recorded rights review](fspo-source-and-validation-2026-10-19.md);
this document does not authorize publishing the research corpus or using it as
promotional case material. No external publication was performed.
