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
