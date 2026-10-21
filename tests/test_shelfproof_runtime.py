import json
import subprocess

import pytest
from shelfproof_api.runtime import CodexProvider, parse_receipt, runtime_lock


def events(item="agent_message", usage=None):
    return "\n".join(
        json.dumps(e)
        for e in [
            {"type": "item.completed", "item": {"type": item}},
            {
                "type": "turn.completed",
                "usage": usage
                or {"input_tokens": 20, "cached_input_tokens": 10, "output_tokens": 5},
            },
        ]
    )


def test_receipt_missing_or_ambiguous_usage_is_not_zero():
    assert parse_receipt("", 0)["input_tokens"] is None
    assert parse_receipt(events() + "\n" + events(), 0)["input_tokens"] is None
    assert (
        parse_receipt(events(usage={"input_tokens": True, "output_tokens": 1}), 0)["input_tokens"]
        is None
    )
    assert parse_receipt(events(), 0)["input_tokens"] == 20


def test_tool_events_and_failed_turns_cannot_be_audited_success():
    assert not parse_receipt(events("command_execution"), 0)["audited"]
    assert not parse_receipt(events(), 1)["audited"]
    assert not parse_receipt(events() + '\n{"type":"turn.failed"}', 0)["audited"]


def test_runtime_lock_excludes_second_worker(tmp_path):
    with runtime_lock(tmp_path) as first, runtime_lock(tmp_path) as second:
        assert first and not second
    with runtime_lock(tmp_path) as released:
        assert released


def test_cli_restrictions_and_receipt_are_required(monkeypatch):
    from pathlib import Path

    provider = CodexProvider()

    def run(args, prompt):
        assert "--ignore-user-config" in args
        assert "--json" in args
        assert "read-only" in args
        assert 'web_search="disabled"' in args
        Path(args[args.index("--output-last-message") + 1]).write_text('{"ok":true}')
        provider._events = events()
        provider._exit_code = 0
        return subprocess.CompletedProcess(args, 0, provider._events, "private diagnostic")

    monkeypatch.setattr(provider, "_run", run)
    assert provider.generate(prompt="test", schema={"type": "object"}).text == '{"ok":true}'
    assert provider.last_receipt["audited"]


def test_no_final_output_file_means_failure(monkeypatch):
    provider = CodexProvider()

    def run(args, prompt):
        provider._events = events()
        provider._exit_code = 0
        return subprocess.CompletedProcess(args, 0, provider._events, "secret")

    monkeypatch.setattr(provider, "_run", run)
    with pytest.raises(RuntimeError):
        provider.generate(prompt="test", schema={"type": "object"})
    assert provider.last_receipt["input_tokens"] == 20


def test_per_attempt_output_limit_matches_documented_100_kib():
    assert CodexProvider().max_output_bytes == 100 * 1024
