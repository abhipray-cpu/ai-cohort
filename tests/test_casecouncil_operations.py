import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_launcher_is_isolated_and_has_real_entrypoints():
    spec = importlib.util.spec_from_file_location(
        "casecouncil_dev_launcher", ROOT / "scripts/dev_stack.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.configure("casecouncil")
    assert module.PREFIX == "CASECOUNCIL" and module.DEFAULT_PORT == "8008"
    assert "casecouncil_api.worker" in module.COMMANDS["worker"]
    assert module.STATE_FILE == ROOT / "var/casecouncil-dev/processes.json"


def test_operational_wiring_is_additive_and_does_not_create_public_hook_exception():
    make = (ROOT / "Makefile").read_text()
    for target in ("up", "down", "status", "test", "acceptance"):
        assert f"casecouncil-{target}:" in make
    windows = (ROOT / "infra/windows/install-casecouncil.ps1").read_text()
    assert "-RunLevel Limited" in windows and "Existing task" in windows
    assert "casecouncil.example.com" in (ROOT / "infra/cloudflare/config.example.yml").read_text()
    assert "CASECOUNCIL_PASSWORD=replace-me" in (ROOT / ".env.example").read_text()
