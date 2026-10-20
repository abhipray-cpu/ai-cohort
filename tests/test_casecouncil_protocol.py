# ruff: noqa: F811
import json

from agent_core.provider import StructuredGeneration
from casecouncil_api.controller import Controller
from test_casecouncil_store import seeded, start  # noqa: F401


class ControlledProvider:
    """An authored engineering stand-in, not real model or real-data evidence."""

    timeout_seconds = 90

    def __init__(self, critic=False, fail_stage=None, invalid_stage=None):
        self.prompts = []
        self.critic = critic
        self.fail_stage = fail_stage
        self.invalid_stage = invalid_stage
        self.last_receipt = {
            "status": "returned",
            "usage": {"input_tokens": 10, "output_tokens": 10, "cached_input_tokens": 0},
            "tools_audited": True,
            "elapsed_ms": 10,
        }

    def generate(self, *, prompt, schema):
        data = json.loads(prompt.split("\nCONTEXT_JSON:\n")[1])
        self.prompts.append(data)
        stage = data["stage"]
        span = data["evidence"]["spans"][0]
        cite = {
            "source_id": span["source_id"],
            "start": span["start"],
            "end": span["end"],
            "quote": span["text"],
        }
        if stage == self.fail_stage:
            raise RuntimeError("controlled provider outage")
        if stage == self.invalid_stage:
            return StructuredGeneration(
                text='{"forged":"winner"}', exit_code=0, elapsed_ms=10, tools_audited=True
            )
        if stage.startswith(("proposal:", "revision:")):
            value = {
                "issues": [
                    {
                        "issue_id": i["id"],
                        "disposition": "partial_uphold",
                        "remedy": "Review the premium and service handling separately.",
                        "conditions": [],
                        "rationale": "This is a proposed interpretation, not a binding ruling.",
                        "counterargument": "A different interpretation may be supported by the full communications record.",
                        "citations": [cite],
                        "missing": [],
                    }
                    for i in data["context"]["issues"]
                ],
                "new_issues": [],
                "critique_responses": [
                    {
                        "finding_id": f["id"],
                        "action": "accepted",
                        "reason": "Addressed in this revised proposal.",
                    }
                    for f in data.get("critique", {}).get("findings", [])
                ],
            }
        elif stage == "critic":
            value = {
                "findings": [
                    {
                        "id": "f1",
                        "issue_id": "premium",
                        "target_role": "insurer",
                        "severity": "material",
                        "assertion": "Review proposed remedy",
                        "reason": "Material interpretation needs human review.",
                        "citations": [cite],
                    }
                ]
                if self.critic
                else []
            }
        elif stage.startswith("ballot:"):
            r = data["registry"]
            value = {
                "snapshot": data["binding"],
                "registry_hash": r["hash"],
                "issues": [
                    {
                        "issue_id": i["id"],
                        "candidate_id": next(
                            c["id"] for c in r["candidates"] if c["issue_id"] == i["id"]
                        ),
                        "reason": "Chosen from the frozen alternatives.",
                        "missing": [],
                    }
                    for i in data["context"]["issues"]
                ],
            }
        else:
            value = {
                "observations": [{"text": span["text"], "citations": [cite]}],
                "proposed_response": "Proposed response for independent human review.",
                "next_actions": ["Review the cited evidence before sending any response."],
            }
        return StructuredGeneration(
            text=json.dumps(value), exit_code=0, elapsed_ms=10, tools_audited=True
        )


def test_complete_debate_uses_isolated_proposals_blind_ballots_and_human_review(seeded):
    s, _w, c = seeded
    j = start(s, c)
    p = ControlledProvider()
    assert Controller(s, p).once()
    saved = s.job("owner", j["id"])
    assert saved["state"] == "draft_ready" and len(p.prompts) == 8
    assert saved["packet"]["consensus"]["issues"][0]["status"] == "unanimous_agreement"
    for context in p.prompts[:3]:
        assert "proposals" not in context and "ballots" not in context
    for context in p.prompts:
        if context["stage"].startswith("ballot:"):
            assert "ballots" not in context and "consensus" not in context
    assert not saved["packet"]["approved"]
    review = {
        "packet_hash": saved["packet_hash"],
        "reason": "Independently checked the policy and complaint.",
        "response": "Reviewed proposed response.",
        "resolutions": {},
        "overrides": {},
    }
    s.review("reviewer", j["id"], review, "review1")
    assert s.export("reviewer", j["id"], True)["approved"]


def test_critic_material_findings_trigger_one_revision_not_automatic_clearance(seeded):
    s, _w, c = seeded
    j = start(s, c)
    p = ControlledProvider(critic=True)
    Controller(s, p).once()
    saved = s.job("owner", j["id"])
    assert len(p.prompts) == 11
    assert saved["packet"]["consensus"]["issues"][0]["status"] == "agreement_blocked"
    assert "f1" in saved["packet"]["review_requirements"]


def test_invalid_synthesis_preserves_valid_prior_draft_and_failure_history(seeded):
    s, w, c = seeded
    j = start(s, c)
    p = ControlledProvider(invalid_stage="synthesis")
    Controller(s, p).once()
    saved = s.job("owner", j["id"])
    assert saved["state"] == "manual_required" and len(p.prompts) == 9
    assert saved["packet"]["proposals"] and saved["packet"]["consensus"]
    assert saved["packet"]["synthesis"] is None
    assert sum(r["action"] == "validation_failed" for r in s.audit("owner", w)) == 2


def test_missing_required_role_does_not_shrink_quorum(seeded):
    s, _w, c = seeded
    j = start(s, c)
    Controller(s, ControlledProvider(fail_stage="proposal:fairness")).once()
    saved = s.job("owner", j["id"])
    assert saved["state"] == "manual_required"
    assert saved["packet"]["consensus"]["issues"][0]["status"] == "insufficient_participation"
    assert len(saved["packet"]["proposals"]) == 2
