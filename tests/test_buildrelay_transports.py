# ruff: noqa: F811
# Imported pytest fixture intentionally matches function parameter names.
import asyncio
import io
import json
import zipfile

import httpx
import pytest
from buildrelay_api.github import GitHub, parse_webhook
from buildrelay_api.queue import consume_message
from buildrelay_api.workflow import Failure
from test_buildrelay_core import store  # noqa: F401
from test_buildrelay_workflow import run


def payload():
    e = run()
    return {
        "action": "completed",
        "repository": {"id": e.repository_id, "full_name": e.repository},
        "workflow_run": {
            "id": e.run_id,
            "run_attempt": e.attempt,
            "status": "completed",
            "conclusion": e.conclusion,
            "name": e.workflow,
            "head_branch": e.branch,
            "head_sha": e.sha,
            "html_url": e.source_url,
        },
    }


def test_parse_webhook_ignores_irrelevant_actions_and_rejects_bad_identity():
    assert parse_webhook("workflow_run", payload()) == run()
    assert parse_webhook("push", {}) is None
    p = payload()
    p["action"] = "requested"
    assert parse_webhook("workflow_run", p) is None
    p = payload()
    p["workflow_run"]["html_url"] = "http://localhost/secrets"
    with pytest.raises(ValueError):
        parse_webhook("workflow_run", p)


class Message:
    def __init__(self, data):
        self.data, self.result = data, None

    async def ack_sync(self):
        self.result = "ack"

    async def nak(self, delay):
        self.result = "nak"

    async def term(self):
        self.result = "term"


def test_queue_ack_only_after_persist_and_poison_is_recorded(store):
    m = Message(
        json.dumps(
            {
                "schema_version": 1,
                "repo_id": "repo",
                "delivery_id": "abc",
                "event": run().model_dump(),
            }
        ).encode()
    )
    asyncio.run(consume_message(store, m))
    assert m.result == "ack" and len(store.events()) == 1
    bad = Message(b'{"token":"do not persist me"}')
    asyncio.run(consume_message(store, bad))
    assert bad.result == "term"
    assert any(a["action"] == "queue_rejected" for a in store.audit())
    assert "do not persist me" not in str(store.audit())


def test_queue_storage_failure_naks_not_acks(store, monkeypatch):
    m = Message(
        json.dumps(
            {
                "schema_version": 1,
                "repo_id": "repo",
                "delivery_id": "abc",
                "event": run().model_dump(),
            }
        ).encode()
    )
    monkeypatch.setattr(store, "accept", lambda *_: (_ for _ in ()).throw(OSError("disk full")))
    asyncio.run(consume_message(store, m))
    assert m.result == "nak"


def test_github_rate_limit_and_no_arbitrary_redirect(monkeypatch):
    monkeypatch.setenv("BUILDRELAY_TOKEN", "private-token")
    repo = {
        "name": "acme/shop",
        "github_id": 123,
        "token_ref": "BUILDRELAY_TOKEN",
        "secret_ref": "BUILDRELAY_SECRET",
    }
    requests = []

    def handler(req):
        requests.append(str(req.url))
        return httpx.Response(429, headers={"Retry-After": "12"})

    gh = GitHub(httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(Failure) as caught:
        gh.evidence(repo, run())
    assert caught.value.transient and caught.value.retry_after >= 12
    assert all(u.startswith("https://api.github.com/") for u in requests)


def test_log_archive_bounds_path_safety_and_secret_redaction(monkeypatch):
    monkeypatch.setenv("BUILDRELAY_TOKEN", "private-token")
    repo = {
        "name": "acme/shop",
        "github_id": 123,
        "token_ref": "BUILDRELAY_TOKEN",
        "secret_ref": "BUILDRELAY_SECRET",
    }
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("job/step.txt", "AssertionError private-token")
        z.writestr("../../escape.txt", "untrusted content")

    def handler(req):
        if str(req.url).endswith("/logs"):
            return httpx.Response(
                302,
                headers={"Location": "https://productionresultssa1.blob.core.windows.net/logs/a"},
            )
        if req.url.host.endswith("blob.core.windows.net"):
            assert "authorization" not in req.headers
            return httpx.Response(200, content=b.getvalue())
        return httpx.Response(200, json={"id": 77, "run_attempt": 1, "repository": {"id": 123}})

    result = GitHub(httpx.Client(transport=httpx.MockTransport(handler))).evidence(repo, run())
    assert "private-token" not in result["text"]
    assert "escape.txt" not in result["text"]
    assert "AssertionError" in result["text"]
