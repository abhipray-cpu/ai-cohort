import json
import sys
import time

import pytest
from casecouncil_api.runtime import provider_from_env, receipt_from_events


def event(usage):
    return json.dumps({"type": "turn.completed", "usage": usage})


def test_known_usage_is_not_guessed_or_double_counted():
    usage = {"input_tokens": 100, "output_tokens": 5, "cached_input_tokens": 40}
    r = receipt_from_events(event(usage), 10, True, "returned")
    assert r["usage"] == usage
    assert (
        receipt_from_events(event(usage) + "\n" + event(usage), 10, True, "returned")["usage"]
        is None
    )
    for usage in (
        {"input_tokens": True, "output_tokens": 0},
        {"input_tokens": -1, "output_tokens": 0},
        {"input_tokens": 1, "output_tokens": 0, "cached_input_tokens": 2},
    ):
        assert receipt_from_events(event(usage), 10, True, "returned")["usage"] is None


def test_runtime_environment_and_features_do_not_inherit_product_secrets(monkeypatch):
    monkeypatch.setenv("CASECOUNCIL_SECRET", "private")
    monkeypatch.setenv("OTHER_API_KEY", "private")
    p = provider_from_env()
    assert p.isolated and p.timeout_seconds == 90
    assert "CASECOUNCIL_SECRET" not in p.environment and "OTHER_API_KEY" not in p.environment
    assert "features.shell_tool=false" in p.config_overrides
    assert 'web_search="disabled"' in p.config_overrides


def test_model_transport_has_a_bounded_stdout_buffer():
    p = provider_from_env()
    p.timeout_seconds = 5
    with pytest.raises(RuntimeError):
        p._run(
            [sys.executable, "-c", "import sys; sys.stdout.write('x'*2000000); sys.stdout.flush()"],
            "",
        )


def test_model_transport_cancellation_kills_its_own_child_promptly():
    p = provider_from_env()
    p.timeout_seconds = 10
    p.cancel_check = lambda: True
    started = time.monotonic()
    with pytest.raises(RuntimeError):
        p._run([sys.executable, "-c", "import time; time.sleep(10)"], "")
    assert time.monotonic() - started < 4


def test_failure_diagnostic_keeps_safe_codes_but_never_payload_text(monkeypatch):
    import subprocess

    p = provider_from_env()

    def run(args, prompt):
        p._events = json.dumps(
            {
                "type": "error",
                "code": "rate_limit_exceeded",
                "message": "token=super-secret customer@example.com PRIVATE COMPLAINT",
            }
        )
        p._exit_code = 7
        p._stderr = "Authorization: Bearer secret\nPRIVATE COMPLAINT"
        return subprocess.CompletedProcess(args, 7, p._events, p._stderr)

    monkeypatch.setattr(p, "_run", run)
    p.generate(prompt="PRIVATE COMPLAINT", schema={"type": "object"})
    d = p.last_receipt["diagnostic"]
    assert d["category"] == "rate_limit" and d["exit_code"] == 7
    assert d["error_events"] == 1
    assert not any(
        s in json.dumps(p.last_receipt)
        for s in ("super-secret", "customer@example.com", "PRIVATE COMPLAINT", "Bearer secret")
    )
    assert p.last_receipt["usage"] is None


def test_nonzero_tool_event_is_flagged_even_without_a_completed_turn(monkeypatch):
    import subprocess

    p = provider_from_env()

    def run(args, prompt):
        p._events = json.dumps(
            {"type": "item.started", "item": {"type": "command_execution", "command": "private"}}
        )
        p._exit_code = 1
        return subprocess.CompletedProcess(args, 1, p._events, "")

    monkeypatch.setattr(p, "_run", run)
    p.generate(prompt="test", schema={"type": "object"})
    assert p.last_receipt["diagnostic"]["unsafe_tool_event"] is True
    assert p.last_receipt["diagnostic"]["category"] == "unsafe_tool"


def test_json_error_message_only_classifies_to_fixed_label_without_retention():
    from casecouncil_api.runtime import failure_diagnostic

    raw = json.dumps(
        {
            "type": "turn.failed",
            "error": {"message": "You've hit your usage limit. PRIVATE customer@example.com"},
        }
    )
    value = failure_diagnostic(raw, 1)
    assert value["category"] == "rate_limit"
    assert "PRIVATE" not in json.dumps(value) and "customer@" not in json.dumps(value)


def test_zero_exit_without_completed_audited_turn_is_not_an_ok_diagnostic(monkeypatch):
    import subprocess

    p = provider_from_env()

    def run(args, prompt):
        p._events = json.dumps({"type": "turn.started"})
        p._exit_code = 0
        return subprocess.CompletedProcess(args, 0, p._events, "")

    monkeypatch.setattr(p, "_run", run)
    with pytest.raises(RuntimeError):
        p.generate(prompt="Authored engineering input", schema={"type": "object"})
    assert p.last_receipt["diagnostic"]["category"] != "ok"
    assert p.last_receipt["usage"] is None
