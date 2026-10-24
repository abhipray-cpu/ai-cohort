"""The proxy's simulated responses test contracts, not its upstream identity or quality."""

import json

import httpx
import pytest
from repairclaim_api.jev import STATES
from repairclaim_api.jevmodel import JevModelProvider
from test_repairclaim_workflow import FixtureParser, flow, register


def reply():
    return {
        "model": "jev-1.14.0",
        "answers": {
            "assessment": {
                "type": "choice",
                "choice": "missing_evidence",
                "confidence": 0.9,
                "probabilities": {s: float(s == "missing_evidence") for s in STATES},
            },
            "human_review": {"type": "noul", "noul": 0.9},
        },
        "usage": {"input_tokens": 100, "output_tokens": 20},
    }


def provider(tmp_path, *, bad_model=False, header=True):
    calls = []

    def handle(request):
        calls.append(request)
        result = reply()
        if bad_model:
            result["model"] = "unknown-model"
        return httpx.Response(
            200,
            json=result,
            headers={"X-Tokens-Remaining": str(99707 - 100 * len(calls))} if header else {},
        )

    return JevModelProvider(
        "fixture-key",
        tmp_path / "budget.sqlite3",
        client=httpx.Client(transport=httpx.MockTransport(handle)),
    ), calls


def test_only_documented_confirmed_host_and_alias_and_honest_receipt(tmp_path):
    p, calls = provider(tmp_path)
    result = p.review({"facts": [], "source_pages": []})
    assert str(calls[0].url) == "https://jevmodel.org/v1/systemone"
    assert json.loads(calls[0].content)["model"] == "jev-latest"
    assert result["receipt"]["model"] == "jev-1.14.0"
    assert result["receipt"]["cost_usd"] is None
    assert result["receipt"]["tokens_remaining"] == 99607
    assert calls[0].headers.get("Idempotency-Key")
    assert p.token_summary()["used_tokens"] == 100


@pytest.mark.parametrize("bad_model,header", [(True, True), (False, False)])
def test_unknown_version_or_missing_balance_halts_without_retry(tmp_path, bad_model, header):
    p, calls = provider(tmp_path, bad_model=bad_model, header=header)
    with pytest.raises(ValueError):
        p.review({})
    with pytest.raises(ValueError, match="campaign_unknown_usage"):
        p.review({})
    assert len(calls) == 1


def test_no_request_can_reserve_beyond_token_budget(tmp_path):
    p, calls = provider(tmp_path)
    with p._db() as db:
        db.execute("UPDATE token_config SET token_limit=100")
    with pytest.raises(ValueError, match="free_token_budget"):
        p.review({})
    assert calls == []


def test_reopen_does_not_reset_spend_or_raise_quota(tmp_path):
    p, _ = provider(tmp_path)
    p.review({})
    with p._db() as db:
        db.execute("UPDATE config SET call_limit=1")
    reopened, calls = provider(tmp_path)
    assert reopened.token_summary()["used_tokens"] == 100
    with pytest.raises(ValueError, match="campaign_budget"):
        reopened.review({})
    assert calls == []


def test_proxy_approval_is_distinct_and_worker_preserves_token_receipt(flow, tmp_path, monkeypatch):
    from repairclaim_api.errors import DomainError
    from repairclaim_api.worker import run_once

    store, _, owner, _, _, case = flow
    register(store)
    old = store.analysis_preview(owner.token, case["id"], mode="jev")
    monkeypatch.setenv("REPAIRCLAIM_JEV_ROUTE", "jevmodel")
    preview = store.analysis_preview(owner.token, case["id"], mode="jev")
    assert preview["context"]["destination"] == "jevmodel.org"
    assert preview["context"]["model"] == "jev-latest"
    with pytest.raises(DomainError, match="egress_approval_required"):
        store.start_investigation(
            owner.token,
            case["id"],
            2,
            "wrong-host",
            mode="jev",
            allowance=1,
            egress_fingerprint=old["fingerprint"],
        )
    job = store.start_investigation(
        owner.token,
        case["id"],
        2,
        "proxy",
        mode="jev",
        allowance=1,
        egress_fingerprint=preview["fingerprint"],
    )
    p, _ = provider(tmp_path)
    run_once(store, parser=FixtureParser(), jev_provider=p)
    result = store.get_job(owner.token, job["id"])
    assert result["status"] == "manual_review"
    assert result["attempts"][0]["cost"] is None
    assert result["result"]["jev_advice"]["receipt"]["tokens_remaining"] == 99607
    assert p.summary()["known_cost_usd"] is None


def test_new_lower_token_campaign_limit_is_durable_and_cannot_be_raised_on_reopen(tmp_path):
    journal = tmp_path / "lower.sqlite3"
    p = JevModelProvider("fixture", journal, token_limit=50000)
    with p._db() as db:
        assert db.execute("SELECT token_limit FROM token_config").fetchone()[0] == 50000
    reopened = JevModelProvider("fixture", journal, token_limit=90000)
    with reopened._db() as db:
        assert db.execute("SELECT token_limit FROM token_config").fetchone()[0] == 50000
    with pytest.raises(ValueError):
        JevModelProvider("fixture", tmp_path / "invalid.sqlite3", token_limit=90001)
