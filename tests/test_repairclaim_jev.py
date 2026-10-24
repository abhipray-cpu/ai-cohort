"""Jev boundary tests use simulated HTTP, not evidence of live model quality."""

import json

import httpx
import pytest
from repairclaim_api.jev import MODEL, STATES, JevGateway
from repairclaim_api.worker import run_once
from test_repairclaim_workflow import FixtureParser, flow, register


def response():
    return {
        "model": MODEL,
        "answers": {
            "assessment": {
                "type": "choice",
                "choice": "missing_evidence",
                "confidence": 0.9,
                "probabilities": {s: float(s == "missing_evidence") for s in STATES},
            },
            "human_review": {"type": "noul", "noul": 0.9},
        },
        "usage": {"input_tokens": 500, "output_tokens": 30},
        "provider_metadata": {"gateway": {"cost": "0.000021", "generationId": "gen_fixture"}},
    }


def gateway(tmp_path, payload=None, *, failure=False, limit=60):
    calls = []

    def handle(request):
        calls.append(request)
        if request.method == "GET":
            return httpx.Response(
                200,
                json={"data": [{"id": MODEL, "pricing": {"input": "0.000000042", "output": "0"}}]},
            )
        if failure:
            raise httpx.ReadTimeout("simulated", request=request)
        return httpx.Response(200, json=payload or response())

    return JevGateway(
        "fixture-key",
        tmp_path / "budget.sqlite3",
        client=httpx.Client(transport=httpx.MockTransport(handle)),
        max_calls=limit,
    ), calls


def test_native_protocol_is_pinned_and_never_uses_chat_or_fallback(tmp_path):
    provider, calls = gateway(tmp_path)
    result = provider.review({"facts": [], "source_pages": []})
    request = json.loads(calls[-1].content)
    assert str(calls[-1].url) == "https://ai-gateway.vercel.sh/typesafe/v1/systemone"
    assert request["model"] == MODEL
    assert set(request) == {"model", "state", "questions"}
    assert request["questions"]["assessment"]["type"] == "choice"
    assert result["assessment"]["choice"] == "missing_evidence"
    assert result["receipt"]["cost_usd"] == "0.000021"


def test_budget_is_reserved_durably_before_call_and_cannot_reset(tmp_path):
    provider, calls = gateway(tmp_path, limit=1)
    provider.review({})
    with pytest.raises(ValueError, match="campaign_budget"):
        provider.review({})
    assert len([r for r in calls if r.method == "POST"]) == 1
    reopened, _ = gateway(tmp_path, limit=60)
    with pytest.raises(ValueError, match="campaign_budget"):
        reopened.review({})


def test_timeout_holds_budget_and_never_retries(tmp_path):
    provider, calls = gateway(tmp_path, failure=True)
    with pytest.raises(httpx.ReadTimeout):
        provider.review({})
    with pytest.raises(ValueError, match="campaign_unknown_usage"):
        provider.review({})
    assert len([r for r in calls if r.method == "POST"]) == 1


@pytest.mark.parametrize("bad", ["model", "probabilities", "noul", "cost"])
def test_invalid_or_unpriced_native_responses_fail_closed(tmp_path, bad):
    payload = response()
    if bad == "model":
        payload["model"] = "unapproved/model"
    elif bad == "probabilities":
        payload["answers"]["assessment"]["probabilities"] = {"unknown": 1.0}
    elif bad == "noul":
        payload["answers"]["human_review"]["noul"] = float("nan")
    else:
        del payload["provider_metadata"]["gateway"]["cost"]
    provider, _ = gateway(tmp_path, payload)
    with pytest.raises(ValueError):
        provider.review({})
    with pytest.raises(ValueError, match="campaign_unknown_usage"):
        provider.review({})


def test_oversized_context_is_rejected_before_any_request(tmp_path):
    provider, calls = gateway(tmp_path)
    with pytest.raises(ValueError, match="jev_context_limit"):
        provider.review({"text": "x" * 80001})
    assert calls == []


def test_jev_requires_its_own_destination_approval_and_persists_advice(flow, tmp_path):
    store, _, owner, _, _, case = flow
    register(store)
    codex = store.analysis_preview(owner.token, case["id"])
    with pytest.raises(Exception, match="egress_approval_required"):
        store.start_investigation(
            owner.token,
            case["id"],
            2,
            "wrong-destination",
            mode="jev",
            allowance=1,
            egress_fingerprint=codex["fingerprint"],
        )
    preview = store.analysis_preview(owner.token, case["id"], mode="jev")
    assert preview["context"]["destination"] == "vercel_ai_gateway_jev"
    assert preview["context"]["model"] == MODEL
    job = store.start_investigation(
        owner.token,
        case["id"],
        2,
        "live-mode",
        mode="jev",
        allowance=1,
        egress_fingerprint=preview["fingerprint"],
    )
    provider, _ = gateway(tmp_path)
    run_once(store, parser=FixtureParser(), jev_provider=provider)
    result = store.get_job(owner.token, job["id"])
    assert result["result"]["search"]["state"] == "missing_evidence"
    assert result["result"]["jev_advice"]["receipt"]["model"] == MODEL
    assert result["status"] == "manual_review"
    assert result["attempts"][0]["cost"] == "0.000021"


def test_provider_failure_keeps_checkpoint_and_blocks_unknown_usage_retry(flow, tmp_path):
    from repairclaim_api.errors import DomainError

    store, _, owner, _, _, case = flow
    register(store)
    preview = store.analysis_preview(owner.token, case["id"], mode="jev")
    job = store.start_investigation(
        owner.token,
        case["id"],
        2,
        "failure",
        mode="jev",
        allowance=1,
        egress_fingerprint=preview["fingerprint"],
    )
    provider, _ = gateway(tmp_path, failure=True)
    run_once(store, parser=FixtureParser(), jev_provider=provider)
    result = store.get_job(owner.token, job["id"])
    assert result["status"] == "partial"
    assert result["result"]["search"]["state"] == "missing_evidence"
    assert result["attempts"][0]["status"] == "provider_error"
    with pytest.raises(DomainError, match="unknown_usage_hold"):
        store.start_investigation(
            owner.token,
            case["id"],
            2,
            "retry",
            mode="jev",
            allowance=1,
            egress_fingerprint=preview["fingerprint"],
        )


def test_http_jev_is_disabled_by_default(flow):
    from test_repairclaim_http_workflows import BASE, client_for

    store, _, _owner, _, _, case = flow
    register(store)
    client = client_for(store)
    preview = client.get(BASE + f"/cases/{case['id']}/analysis-preview?mode=jev")
    assert preview.status_code == 200
    result = client.post(
        BASE + f"/cases/{case['id']}/investigations",
        json={
            "expected_revision": 2,
            "key": "blocked",
            "mode": "jev",
            "allowance": 1,
            "egress_fingerprint": preview.json()["fingerprint"],
        },
    )
    assert result.status_code == 409
    assert client.get(BASE + "/capabilities").json()["jev_enabled"] is False


def test_access_denial_halts_without_exposing_server_echoed_credentials(tmp_path):
    def handle(request):
        if request.method == "GET":
            return httpx.Response(
                200,
                json={"data": [{"id": MODEL, "pricing": {"input": "0.000000042", "output": "0"}}]},
            )
        return httpx.Response(
            403, json={"error": {"message": "fixture-key: free tier model requires credits"}}
        )

    provider = JevGateway(
        "fixture-key",
        tmp_path / "denied.sqlite3",
        client=httpx.Client(transport=httpx.MockTransport(handle)),
    )
    with pytest.raises(httpx.HTTPStatusError):
        provider.review({})
    diagnostic = (tmp_path / "denied.diagnostic.json").read_text()
    assert "fixture-key" not in diagnostic
    assert json.loads(diagnostic)["http_status"] == 403
    assert provider.summary()["unknown_or_invalid"] == 1
    with pytest.raises(ValueError, match="campaign_unknown_usage"):
        provider.review({})
