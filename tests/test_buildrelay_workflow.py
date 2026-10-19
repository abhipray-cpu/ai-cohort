import json
import time

import pytest
from agent_core.provider import StructuredGeneration
from buildrelay_api.store import Store
from buildrelay_api.workflow import Failure, Workflow, redact, validate_triage
from contracts.buildrelay import RunEvent


def run(attempt=1, conclusion="failure"):
    return RunEvent(
        repository_id=123,
        repository="acme/shop",
        run_id=77,
        attempt=attempt,
        conclusion=conclusion,
        workflow="CI",
        branch="main",
        sha="a" * 40,
        source_url="https://github.com/acme/shop/actions/runs/77",
    )


def triage():
    return {
        "category": "test",
        "summary": "The checkout assertion failed.",
        "hypothesis": "A checkout expectation may be wrong.",
        "confidence": 0.8,
        "next_steps": ["Inspect the failing assertion."],
        "citations": [{"line": 2, "quote": "AssertionError: expected 2, got 3"}],
        "client_update": "A checkout test failed; engineering is investigating.",
    }


class Provider:
    def __init__(self, values=None):
        self.values = iter(values or [json.dumps(triage())])
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        return StructuredGeneration(text=next(self.values), exit_code=0, elapsed_ms=10)


class GitHub:
    def __init__(self):
        self.issues = []
        self.fail_after_create = False
        self.updates = []

    def evidence(self, repo, event):
        return {
            "text": "Test checkout\nAssertionError: expected 2, got 3",
            "truncated": False,
            "source": "test-fixture",
        }

    def find_issue(self, repo, marker):
        return next((i for i in self.issues if marker in i["body"]), None)

    def create_issue(self, repo, title, body):
        issue = {"number": 1, "body": body}
        self.issues.append(issue)
        if self.fail_after_create:
            self.fail_after_create = False
            raise Failure("network_timeout", transient=True)
        return issue

    def update_issue(self, repo, number, title, body, state):
        self.updates.append((number, body, state))


@pytest.fixture
def setup(tmp_path):
    s = Store(tmp_path)
    s.create_client("client", "Shop")
    s.create_repo(
        "repo", "client", "acme/shop", 123, "BUILDRELAY_SECRET", "BUILDRELAY_TOKEN", "QA", True
    )
    return s, GitHub(), Provider()


def enqueue(s, event):
    s.accept("repo", event, "queue", str(time.time_ns()))


def test_schema_repair_is_logged_and_citations_are_validated(setup):
    s, gh, _ = setup
    p = Provider(["not json", json.dumps(triage())])
    enqueue(s, run())
    Workflow(s, gh, p).once()
    assert p.calls == 2
    assert s.events()[0]["state"] == "done"
    assert s.incidents()[0]["owner"] == "QA"
    assert any(a["action"] == "validation_failed" for a in s.audit())


@pytest.mark.parametrize("failure", [False, True])
def test_superseded_worker_cannot_change_replacement_lease(setup, failure):
    s, gh, p = setup
    enqueue(s, run())

    def replacement(*_):
        with s.write() as db:
            db.execute(
                "UPDATE events SET lease_token='replacement',lease_until=?", (time.time() + 600,)
            )
        if failure:
            raise Failure("late_network_failure", transient=True)
        return {"text": "Test checkout\nAssertionError: expected 2, got 3", "truncated": False}

    gh.evidence = replacement
    assert Workflow(s, gh, p).once()
    row = s.events()[0]
    assert row["lease_token"] == "replacement"
    assert row["state"] == "processing" and row["checkpoint"] == "{}"
    assert p.calls == 0 and not gh.issues
    assert any(a["action"] == "lease_lost" for a in s.audit())


def test_value_error_containing_lease_is_not_silently_ignored(setup):
    s, gh, p = setup
    enqueue(s, run())
    gh.evidence = lambda *_: (_ for _ in ()).throw(ValueError("release contract invalid"))
    assert Workflow(s, gh, p).once()
    assert s.events()[0]["state"] == "dead"
    assert s.events()[0]["error"] == "contract_failure"


def test_lease_loss_during_analysis_audit_is_not_schema_retry():
    from buildrelay_api.store import LeaseLost
    from buildrelay_api.workflow import triage_evidence

    provider, notes = Provider(), []

    def emit(action, detail):
        notes.append(action)
        raise LeaseLost("expired")

    with pytest.raises(LeaseLost):
        triage_evidence(provider, {}, {"text": "failure"}, emit)
    assert notes == ["generation_started"] and provider.calls == 0


def test_lost_create_response_reconciles_without_duplicate_or_repeat_ai(setup):
    s, gh, p = setup
    enqueue(s, run())
    gh.fail_after_create = True
    w = Workflow(s, gh, p)
    w.once()
    assert s.events()[0]["state"] == "retry"
    assert len(s.incidents()) == 1  # internal handoff survives failed external delivery
    with s.write() as db:
        db.execute("UPDATE events SET due=0")
    w.once()
    assert len(gh.issues) == 1
    assert p.calls == 1
    assert s.events()[0]["state"] == "done"


def test_out_of_order_old_failure_cannot_reopen_recovery(setup):
    s, gh, p = setup
    w = Workflow(s, gh, p)
    enqueue(s, run())
    w.once()
    enqueue(s, run(3, "success"))
    w.once()
    enqueue(s, run(2))
    w.once()
    assert p.calls == 1
    assert s.incidents()[0]["state"] == "recovered"
    assert gh.updates[-1][2] == "closed"


def test_permanent_failure_deadletters_and_timeout_has_history(setup):
    s, gh, p = setup
    enqueue(s, run())
    gh.evidence = lambda *_: (_ for _ in ()).throw(Failure("source_expired", transient=False))
    Workflow(s, gh, p).once()
    assert s.events()[0]["state"] == "dead"
    assert s.events()[0]["error"] == "source_expired"


def test_invalid_generation_gracefully_creates_manual_triage(setup):
    s, gh, _ = setup
    enqueue(s, run())
    Workflow(s, gh, Provider(["invalid", "invalid"])).once()
    assert s.incidents()[0]["state"] == "needs_triage"
    assert s.events()[0]["state"] == "done"
    assert "manual" in gh.issues[0]["body"].lower()


def test_grounding_rejects_fabricated_lines_and_redacts_secrets():
    with pytest.raises(ValueError):
        validate_triage(triage(), "a different log")
    text = redact(
        "token=ghp_abcdefghijklmnopqrstuvwxyz1234567890 password=hunter22\nsecret-123456",
        ["secret-123456"],
    )
    assert "ghp_" not in text and "hunter22" not in text and "secret-123456" not in text


def test_success_observed_before_delayed_failure_does_not_create_incident(setup):
    s, gh, p = setup
    w = Workflow(s, gh, p)
    enqueue(s, run(2, "success"))
    w.once()
    enqueue(s, run(1))
    w.once()
    assert not s.incidents() and not gh.issues and p.calls == 0


def test_recovery_issue_update_is_retried_after_internal_projection(setup):
    s, gh, p = setup
    w = Workflow(s, gh, p)
    enqueue(s, run())
    w.once()
    enqueue(s, run(2, "success"))
    original = gh.update_issue
    gh.update_issue = lambda *_: (_ for _ in ()).throw(Failure("network_timeout", transient=True))
    w.once()
    assert s.incidents()[0]["state"] == "recovered"
    with s.write() as db:
        db.execute("UPDATE events SET due=0 WHERE state='retry'")
    gh.update_issue = original
    w.once()
    assert gh.updates and gh.updates[-1][2] == "closed"
    assert all(e["state"] == "done" for e in s.events())


def test_provider_timeout_is_audited_and_preserves_manual_handoff(setup):
    from agent_core.provider import ProviderTimeoutError

    s, gh, p = setup
    enqueue(s, run())
    p.generate = lambda **_: (_ for _ in ()).throw(ProviderTimeoutError("timeout"))
    Workflow(s, gh, p).once()
    assert s.events()[0]["state"] == "done"
    assert s.incidents()[0]["state"] == "needs_triage"
    assert any(
        "provider_timeout" in a["detail"] for a in s.audit() if a["action"] == "validation_failed"
    )
