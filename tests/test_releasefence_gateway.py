import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from releasefence_api.connector import Router
from releasefence_api.core import digest
from releasefence_api.crypto import public_key
from releasefence_api.gateway import HTTPBundles, create_gateway
from releasefence_api.sdk import Spool
from test_releasefence_core import release


@pytest.mark.parametrize("attempt,declared", [("actual", 1), ("unknown:0", 2)])
def test_gateway_serves_only_registered_bundles_and_records_real_dispatch(
    tmp_path, attempt, declared
):
    manifest = release()
    identity = digest(manifest)
    calls = []

    def transport(url, **kw):
        calls.append((url, kw))
        body = json.loads(kw["body"])
        if url.endswith("/probe"):
            return 200, json.dumps(
                {"nonce": body["nonce"], "release": identity, "healthy": True}
            ).encode()
        return 200, json.dumps(
            {
                "release": identity,
                "output": "Answer from owned adapter",
                "outcome": "success",
                "model_calls": declared,
                "usage": [{"attempt": attempt, "reported_cost": "0.01"}],
            }
        ).encode()

    bundles = HTTPBundles(
        {
            identity: {
                "manifest": manifest.model_dump(),
                "url": "http://127.0.0.1:9999",
                "token": "private",
            }
        },
        transport=transport,
        lab_loopback=True,
    )
    key = Ed25519PrivateKey.generate()
    router = Router(
        tmp_path / "r.db",
        "runtime",
        "support",
        "staging",
        public_key(key),
        key,
        {identity},
        identity,
        probe=bundles.probe,
    )
    spool = Spool(tmp_path / "s.db")
    app = create_gateway(router, spool, bundles, "customer-owned-key")
    with TestClient(app) as client:
        assert (
            client.post(
                "/agent/v1/tasks", json={"id": "task", "session": "s", "input": "PRIVATE INPUT"}
            ).status_code
            == 403
        )
        result = client.post(
            "/agent/v1/tasks",
            headers={"Authorization": "Bearer customer-owned-key"},
            json={"id": "task", "session": "s", "input": "PRIVATE INPUT"},
        )
        assert result.status_code == 200 and result.json()["release"] == identity
    proof = router.attest("heartbeat")["body"]
    assert proof["probe_kind"] == "http_bundle" and proof["probe_receipt"]
    events = []
    spool.flush(lambda p, b: events.extend(b["events"]) or {"accepted": len(b["events"])})
    assert len(events) == 3 and "PRIVATE INPUT" not in str(events)
    assert next(e for e in events if e["kind"] == "terminal")["model_calls"] == declared
    assert calls[-1][0].endswith("/probe")
    assert next(kw for url, kw in calls if url.endswith("/tasks"))["deadline_seconds"] == 300


def test_bundle_wrong_loaded_release_cannot_attest(tmp_path):
    import pytest

    manifest = release()
    identity = digest(manifest)
    bundles = HTTPBundles(
        {
            identity: {
                "manifest": manifest.model_dump(),
                "url": "http://127.0.0.1:9999",
                "token": "private",
            }
        },
        transport=lambda *a, **k: (200, b'{"release":"wrong","healthy":true}'),
        lab_loopback=True,
    )
    with pytest.raises(ValueError):
        bundles.probe(identity, "probe")
