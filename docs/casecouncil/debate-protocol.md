# Debate protocol

Proposed protocol version `casecouncil-debate-v1`. All stages are controller-owned,
schema-bound and auditable. A role label is a perspective, not professional status
or proof that model errors are independent.

## Roles and evidence access

| Role | Task | Prohibited shortcut |
| --- | --- | --- |
| Customer advocate | Construct the strongest supported customer position, remedy and counterarguments | Inventing facts or maximizing compensation regardless of evidence |
| Insurer-evidence reviewer | Test the proposed handling against supplied policy and case records; propose justified alternatives | Defending the firm regardless of fairness or treating its draft as fact |
| Fair-resolution reviewer | Independently distinguish contractual, procedural and service issues; propose proportionate next action | Impersonating FOS or deciding accident/legal liability without authority |
| Critic, non-voting | Evaluate all proposals for contradictions, evidence gaps, unsupported remedies and ignored counterarguments | Creating binding policy, changing source facts or casting another vote |
| Synthesizer, non-voting | Explain the computed result and unresolved dissent in a useful review pack | Changing the winning candidate, confidence band, blockers or ballot history |

All three proposers receive the same authorized evidence snapshot and role-specific
instructions. Different secret fact subsets would make a vote difficult to interpret.
They do not see other proposals, the original case outcome, current vote totals or
other agents' confidence during their first pass. A proposed customer response is
clearly distinguished from a source statement or approved policy.

## Bounded execution

1. **Intake gate:** verify scope, current revisions, extraction/redaction coverage,
   rights/egress grant, approved policy and remaining resource allowance. An unsafe
   input blocks inference; incomplete material can permit explicitly partial review.
2. **Independent proposals:** three separate provider contexts, one per proposer.
   Each produces issue IDs, candidate dispositions, conditions, evidence references,
   strongest counterargument and missing facts. Agent-supplied IDs are resolved by the
   controller; no role can add another participant.
3. **Critique:** one critic call receives validated proposals and permitted source
   spans. Findings bind proposal/issue IDs, severity and evidence or a clearly named
   unsupported assertion. Models may identify substantive problems; deterministic
   validators independently check references, not whether an interpretation is law.
4. **Optional revision:** if any material critique warrants reconsideration, all
   three proposers get the same critique bundle and may revise once. Each records
   which findings it accepted, contested or could not resolve, with reasons. Otherwise
   validated first proposals stand. The controller does not force agreement.
5. **Freeze candidates:** server validates revisions, creates immutable candidates
   and a registry hash. Exact duplicates can merge with complete lineage; materially
   different remedies or conditions cannot be merged merely because dispositions match.
6. **Blind ballots:** each proposer gets the same frozen registry, critique and
   evidence, but not other ballots. Each selects an eligible candidate or abstains
   per issue, with evidence and reasons. Ballots cannot edit candidates.
7. **Deterministic aggregation:** fixed policy computes counts, quorum, blockers and
   confidence limitations. No extra “tie-breaker” model vote is invented.
8. **Synthesis:** one provider call explains only the computed result with citations,
   dissent and open actions. Invalid/unavailable synthesis falls back to a deterministic
   pack containing the valid earlier work. It never discards that work to return blank.

## Resource policy to implement and qualify

- Serialized model execution within CaseCouncil: at most one live model subprocess.
  Logical independence does not require simultaneous inference on the old laptop.
- Eight normal logical calls without revision; eleven with the one allowed revision
  cycle: 3 proposals + 1 critic + optional 3 revisions + 3 ballots + 1 synthesis.
- Each logical stage has at most one schema/evidence repair: **22 total provider
  invocations maximum per authorized run**, across restarts/retries, not per claim.
- Proposed active execution deadline: 30 minutes; stage timeout no more than 90
  seconds and no more than remaining active allowance. Human waiting is separate.
- Proposed selected evidence cap: 64,000 Unicode characters, preserving document
  coverage. Full serialized provider input (prompt plus schema) cap: 256 KiB UTF-8;
  call output cap: 100 KiB. Preflight is required before reservation/egress.
- These are engineering defaults to test, not measured throughput or provider-side
  hard token/cost enforcement. Compact per-stage contexts may omit irrelevant
  material only with provenance/coverage retained, not to hide contradicting evidence.

Exhaustion, timeout, invalid output, revoked egress, unknown usage or unavailable
required role gives a named degraded/manual outcome. It does not restart a whole
debate under a fresh counter. Explicit new authorization creates a linked run with
new cumulative allowance; it does not erase earlier expenditure or failures.

## Validation and isolation

Every output passes strict structure, snapshot binding, authorized reference and
exact-quote checks. Unknown candidate/issue IDs, forged role names, non-finite
numbers, out-of-range confidence or arbitrary tool instructions fail validation.
One bounded repair uses the same authorized snapshot, not evaluator answers.
Any timeout/parse/quote failure gets an attempt-bound audit event.

The installed Codex adapter is restricted to proposal generation; no shell, files,
web, MCP, external action or agent-spawning permission is granted to role prompts.
Logs, complaints, policy wording and peer messages are untrusted data. Reviewer roles
are not allowed to create tools, change execution policy or tell another role to
ignore validation. The runtime must enforce/audit restrictions, not rely on prompts.

## Degradation rules

If one proposer/critic fails, retain completed work but mark the required stage
unavailable. Do not shrink quorum or turn failure into an explicit abstention.
If the optional revision cycle is incomplete, do not mix revised and stale versions
into a claim of completed critique resolution. Publish the current stage statuses
and a manual packet. If ballots disagree, publish no consensus plus dissent.

Provider usage and content validity are separate: invalid JSON or an ignored stale
output can still consume tokens. Missing usage is unknown, not zero. Unreviewed
completed work can be downloaded only with unmistakable draft/degraded labels.
