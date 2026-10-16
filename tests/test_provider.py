import json
import subprocess
from pathlib import Path

import pytest
from agent_core.codex_local import LocalCodexProvider, codex_output_schema
from agent_core.provider import ProviderTimeoutError
from contracts.tenderlens import DraftBrief


def test_codex_provider_uses_schema_file_and_read_only_sandbox(tmp_path, monkeypatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        schema_path = Path(args[args.index("--output-schema") + 1])
        assert json.loads(schema_path.read_text())["type"] == "object"
        Path(args[args.index("--output-last-message") + 1]).write_text('{"ok":true}')
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = LocalCodexProvider(command="codex", timeout_seconds=30).generate(
        prompt="Extract", schema={"type": "object"}
    )
    assert result.text == '{"ok":true}'
    assert captured["args"][0:2] == ["codex", "exec"]
    assert captured["args"][captured["args"].index("--sandbox") + 1] == "read-only"
    assert captured["kwargs"]["input"] == "Extract"
    assert captured["kwargs"]["shell"] is False
    assert "env" not in captured["kwargs"]


def test_codex_provider_timeout_is_operational_error(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="codex", timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ProviderTimeoutError, match="timed out"):
        LocalCodexProvider(command="codex", timeout_seconds=1).generate(
            prompt="Extract", schema={"type": "object"}
        )


def test_pydantic_schema_is_strict_for_codex_without_changing_validation_contract():
    original = DraftBrief.model_json_schema()
    normalized = codex_output_schema(original)
    claim = normalized["$defs"]["Claim"]
    assert set(claim["required"]) == set(claim["properties"])
    assert claim["additionalProperties"] is False
    assert "default" not in claim["properties"]["status"]
    assert original["$defs"]["Claim"]["required"] == ["kind", "value"]


def test_isolated_provider_timeout_cleans_child_process_group(monkeypatch):
    import os
    import signal

    captured = {}

    class Child:
        pid = 43210
        returncode = None

        def communicate(self, **kwargs):
            captured["communicate"] = kwargs
            raise subprocess.TimeoutExpired("codex", 0.1)

        def poll(self):
            return None

        def kill(self):
            captured["killed"] = True

        def wait(self, timeout=None):
            return 0

    def popen(args, **kwargs):
        captured["options"] = kwargs
        return Child()

    monkeypatch.setattr(subprocess, "Popen", popen)
    monkeypatch.setattr(
        os, "killpg", lambda pid, sig: captured.update(group=(pid, sig)), raising=False
    )
    with pytest.raises(ProviderTimeoutError):
        LocalCodexProvider(timeout_seconds=0.1, isolated=True).generate(
            prompt="test", schema={"type": "object"}
        )
    if os.name != "nt":
        assert captured["options"]["start_new_session"] is True
        assert captured["group"] == (43210, signal.SIGKILL)


@pytest.mark.parametrize("item_type", ["command_execution", "mcp_tool_call"])
def test_isolated_provider_rejects_native_tools_even_with_valid_final_json(monkeypatch, item_type):
    provider = LocalCodexProvider(isolated=True)

    def run(args, prompt):
        Path(args[args.index("--output-last-message") + 1]).write_text('{"ok":true}')
        events = [
            {"type": "item.completed", "item": {"type": item_type}},
            {"type": "turn.completed"},
        ]
        return subprocess.CompletedProcess(args, 0, "\n".join(map(json.dumps, events)), "")

    monkeypatch.setattr(provider, "_run", run)
    with pytest.raises(RuntimeError, match="internal tool"):
        provider.generate(prompt="test", schema={"type": "object"})


def test_isolated_provider_requires_completed_turn(monkeypatch):
    provider = LocalCodexProvider(isolated=True)
    monkeypatch.setattr(
        provider, "_run", lambda args, _: subprocess.CompletedProcess(args, 0, "", "")
    )
    with pytest.raises(RuntimeError, match="audited turn"):
        provider.generate(prompt="test", schema={"type": "object"})


def test_isolated_provider_accepts_audited_tool_free_completion(monkeypatch):
    provider = LocalCodexProvider(isolated=True, config_overrides=("features.shell_tool=false",))

    def run(args, prompt):
        assert "--json" in args and "features.shell_tool=false" in args
        Path(args[args.index("--output-last-message") + 1]).write_text('{"ok":true}')
        events = [
            {"type": "item.completed", "item": {"type": "agent_message"}},
            {"type": "turn.completed"},
        ]
        return subprocess.CompletedProcess(args, 0, "\n".join(map(json.dumps, events)), "")

    monkeypatch.setattr(provider, "_run", run)
    result = provider.generate(prompt="test", schema={"type": "object"})
    assert result.tools_audited and json.loads(result.text) == {"ok": True}


def test_isolated_provider_uses_explicit_environment_without_inheritance(monkeypatch):
    captured = {}

    class Child:
        returncode = 0

        def communicate(self, **_):
            return "", ""

    def popen(_args, **kwargs):
        captured.update(kwargs)
        return Child()

    monkeypatch.setenv("PATCHDESK_GITHUB_PUBLISH_TOKEN", "must-not-inherit")
    monkeypatch.setattr(subprocess, "Popen", popen)
    LocalCodexProvider(isolated=True, environment={"PATH": "/usr/bin"})._run(["codex"], "test")
    assert captured["env"] == {"PATH": "/usr/bin"}
