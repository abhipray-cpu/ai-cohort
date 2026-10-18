import json
import subprocess
from pathlib import Path

import pytest
from catalogbridge_api.model_boundary import MeteredCodex
from catalogbridge_api.runtime import ProviderFailure


def test_current_cli_usage_includes_zero_cache_write_and_reasoning_breakdown(monkeypatch):
    adapter = MeteredCodex("economy")

    def run(args, prompt):
        Path(args[args.index("--output-last-message") + 1]).write_text("{}")
        event = {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 7967,
                "cached_input_tokens": 0,
                "cache_write_input_tokens": 0,
                "output_tokens": 11,
                "reasoning_output_tokens": 0,
            },
        }
        return subprocess.CompletedProcess(args, 0, json.dumps(event), "")

    monkeypatch.setattr(adapter, "_execute", run)
    result = adapter.generate_metered("task", {"type": "object"})
    assert result.usage is not None and result.usage.total == 7978
    assert result.effective_model is None


def test_unknown_nonzero_token_categories_are_not_silently_ignored(monkeypatch):
    adapter = MeteredCodex("economy")

    def run(args, prompt):
        Path(args[args.index("--output-last-message") + 1]).write_text("{}")
        event = {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 10,
                "cached_input_tokens": 0,
                "output_tokens": 5,
                "unrecognized_billable_tokens": 100,
            },
        }
        return subprocess.CompletedProcess(args, 0, json.dumps(event), "")

    monkeypatch.setattr(adapter, "_execute", run)
    assert adapter.generate_metered("task", {"type": "object"}).usage is None


def test_reasoning_is_an_output_subset_not_additional_charge(monkeypatch):
    adapter = MeteredCodex("economy")

    def run(args, prompt):
        Path(args[args.index("--output-last-message") + 1]).write_text("{}")
        event = {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 10,
                "cached_input_tokens": 0,
                "cache_write_input_tokens": 0,
                "output_tokens": 20,
                "reasoning_output_tokens": 15,
            },
        }
        return subprocess.CompletedProcess(args, 0, json.dumps(event), "")

    monkeypatch.setattr(adapter, "_execute", run)
    result = adapter.generate_metered("task", {"type": "object"})
    assert result.usage.total == 30
    assert result.usage.reasoning_output_tokens == 15


@pytest.mark.parametrize("as_bytes", [False, True])
def test_timeout_retains_completed_usage_and_safe_partial_stream(monkeypatch, as_bytes):
    adapter = MeteredCodex("economy")
    output = json.dumps(
        {"type": "turn.completed", "usage": {"input_tokens": 20, "output_tokens": 5}}
    )
    stderr = "private-token customer@example.com"

    def run(*_):
        raise subprocess.TimeoutExpired(
            "codex",
            1,
            output=output.encode() if as_bytes else output,
            stderr=stderr.encode() if as_bytes else stderr,
        )

    monkeypatch.setattr(adapter, "_execute", run)
    with pytest.raises(ProviderFailure) as raised:
        adapter.generate_metered("task", {"type": "object"})
    assert raised.value.usage.total == 25
    evidence = raised.value.diagnostics
    assert evidence["category"] == "timeout"
    assert evidence["stdout_bytes"] == len(output.encode())
    assert not any(s in json.dumps(evidence) for s in ("private-token", "customer@"))


def test_timeout_without_completion_keeps_unknown_usage_and_thread_correlation(monkeypatch):
    adapter = MeteredCodex("economy")
    thread = "0199a7bc-1234-7123-8123-123456789abc"
    output = json.dumps({"type": "thread.started", "thread_id": thread}) + '\n{"type":'

    def run(*_):
        raise subprocess.TimeoutExpired("codex", 1, output=output.encode())

    monkeypatch.setattr(adapter, "_execute", run)
    with pytest.raises(ProviderFailure) as raised:
        adapter.generate_metered("task", {"type": "object"})
    assert raised.value.usage is None
    assert raised.value.diagnostics["runtime_thread_ids"] == [thread]


@pytest.mark.parametrize(
    "tail",
    [
        {"type": "turn.started"},
        {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}},
    ],
)
def test_later_turn_cannot_be_settled_from_only_first_completion(monkeypatch, tail):
    adapter = MeteredCodex("economy")
    events = [
        {"type": "turn.started"},
        {"type": "turn.completed", "usage": {"input_tokens": 20, "output_tokens": 5}},
        tail,
    ]

    def run(args, _):
        Path(args[args.index("--output-last-message") + 1]).write_text("{}")
        return subprocess.CompletedProcess(args, 0, "\n".join(map(json.dumps, events)), "")

    monkeypatch.setattr(adapter, "_execute", run)
    assert adapter.generate_metered("task", {"type": "object"}).usage is None


def test_only_runtime_thread_events_supply_safe_correlation_ids(monkeypatch):
    from catalogbridge_api.runtime import diagnostics

    good = "0199a7bc-1234-7123-8123-123456789abc"
    events = [
        {"type": "thread.started", "thread_id": good},
        {"type": "thread.started", "thread_id": "Bearer private-token"},
        {"type": "item.completed", "item": {"type": "agent_message", "thread_id": good}},
    ]
    evidence = diagnostics("\n".join(map(json.dumps, events)), exit_code=1)
    assert evidence["runtime_thread_ids"] == [good]
    assert "private-token" not in json.dumps(evidence)


@pytest.mark.parametrize(
    "tail",
    [
        '{"type":',
        json.dumps({"type": "turn.completed", "usage": None}),
        json.dumps({"type": "turn.failed"}),
    ],
)
def test_incomplete_or_ambiguous_stream_is_not_a_complete_receipt(monkeypatch, tail):
    adapter = MeteredCodex("economy")
    completed = json.dumps(
        {"type": "turn.completed", "usage": {"input_tokens": 20, "output_tokens": 5}}
    )

    def run(*_):
        raise subprocess.TimeoutExpired("codex", 1, output=completed + "\n" + tail)

    monkeypatch.setattr(adapter, "_execute", run)
    with pytest.raises(ProviderFailure) as raised:
        adapter.generate_metered("task", {"type": "object"})
    assert raised.value.usage is None


def test_diagnostics_hashes_actual_bytes_even_with_invalid_utf8():
    import hashlib

    from catalogbridge_api.runtime import diagnostics

    raw = b"\xff\xfe\x00"
    evidence = diagnostics(raw, exception=TimeoutError())
    assert evidence["stdout_bytes"] == 3
    assert evidence["stdout_sha256"] == hashlib.sha256(raw).hexdigest()
