import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "dev_stack", Path(__file__).resolve().parents[1] / "scripts/dev_stack.py"
)
assert SPEC and SPEC.loader
dev_stack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev_stack)


def test_environment_loads_dotenv_without_overriding_shell(tmp_path, monkeypatch):
    monkeypatch.setattr(dev_stack, "ROOT", tmp_path)
    (tmp_path / ".env").write_text(
        "# local configuration\nTENDERLENS_USERNAME=from-file\nTENDERLENS_PASSWORD='file-secret'\n"
    )
    monkeypatch.setenv("TENDERLENS_USERNAME", "from-shell")
    env = dev_stack.environment()
    assert env["TENDERLENS_USERNAME"] == "from-shell"
    assert env["TENDERLENS_PASSWORD"] == "file-secret"


def test_up_refuses_placeholder_password_before_starting(tmp_path, monkeypatch):
    monkeypatch.setattr(dev_stack, "ROOT", tmp_path)
    monkeypatch.setattr(dev_stack, "STATE_FILE", tmp_path / "processes.json")
    monkeypatch.setenv("TENDERLENS_USERNAME", "reviewer")
    monkeypatch.setenv("TENDERLENS_PASSWORD", "replace-me")
    with pytest.raises(RuntimeError, match="real TENDERLENS_PASSWORD"):
        dev_stack.up()
    assert not (tmp_path / "processes.json").exists()
