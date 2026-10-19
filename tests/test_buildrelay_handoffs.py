from buildrelay_api.api import create_app
from buildrelay_api.workflow import Workflow
from fastapi.testclient import TestClient
from test_buildrelay_api import login
from test_buildrelay_workflow import GitHub, Provider, enqueue, run


def test_operator_can_take_ownership_and_export_handoff(tmp_path):
    app = create_app(tmp_path, username="owner", password="test-password-123")
    s = app.state.store
    s.create_client("client", "Shop")
    s.create_repo(
        "repo",
        "client",
        "acme/shop",
        123,
        "BUILDRELAY_SHOP_SECRET",
        "BUILDRELAY_SHOP_TOKEN",
        "Engineering",
        False,
    )
    enqueue(s, run())
    Workflow(s, GitHub(), Provider()).once()
    c = TestClient(app)
    login(c, password="test-password-123")
    ident = s.incidents()[0]["id"]
    response = c.post(
        f"/api/incidents/{ident}/acknowledge",
        json={"reason": "Investigating the checkout assertion", "owner": "Payments team"},
    )
    assert response.status_code == 200
    assert s.incidents()[0]["owner"] == "Payments team"
    exported = c.get(f"/api/incidents/{ident}/export")
    assert exported.status_code == 200
    assert exported.json()["client_update_approved"] is False
    assert any(a["action"] == "incident_acknowledged" for a in s.audit())
