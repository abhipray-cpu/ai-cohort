import pytest
from contracts.patchdesk import Approval, ProjectPolicy, Review
from fastapi.testclient import TestClient
from patchdesk_api.api import create_app
from patchdesk_api.publisher import Publisher
from patchdesk_api.worker import run_once
from test_patchdesk_worker import EmptySources, Provider, job


def reviewed(tmp_path):
    store, project, run = job(tmp_path, model=False)
    store.update_policy(
        "alice",
        project["id"],
        ProjectPolicy(
            expected_revision=2,
            public_packages=["axios", "lodash", "follow-redirects"],
            repository="owned/test",
            repository_id=123,
        ),
    )
    run_once(store, sources=EmptySources(), provider=Provider([]))
    report = store.run("alice", run["id"])["report"]
    store.review("alice", report["id"], Review(expected_revision=1, acknowledge_limits=True))
    return store, project, report["id"]


def test_publication_exact_approval_timeout_and_no_blind_retry(tmp_path):
    store, _, report_id = reviewed(tmp_path)
    calls = []

    def remote(url, data=None, **_):
        calls.append((url, data))
        if data is None:
            return {"id": 123}
        raise TimeoutError("accepted but reply lost")

    publisher = Publisher(store, request=remote, enabled=True)
    draft = publisher.draft("alice", report_id, "Maintenance plan")
    with pytest.raises(ValueError):
        publisher.dispatch("alice", draft["id"])
    publisher.approve(
        "alice", draft["id"], Approval(expected_revision=1, payload_hash=draft["payload_hash"])
    )
    value = publisher.dispatch("alice", draft["id"])
    assert value["status"] == "outcome_unknown"
    with pytest.raises(ValueError):
        publisher.dispatch("alice", draft["id"])
    assert sum(data is not None for _, data in calls) == 1


def test_policy_change_and_cross_project_deny_publication(tmp_path):
    store, project, report_id = reviewed(tmp_path)
    publisher = Publisher(
        store,
        enabled=True,
        request=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not send")),
    )
    draft = publisher.draft("alice", report_id, "Maintenance plan")
    publisher.approve(
        "alice", draft["id"], Approval(expected_revision=1, payload_hash=draft["payload_hash"])
    )
    with pytest.raises(PermissionError):
        publisher.get("bob", draft["id"])
    store.update_policy("alice", project["id"], ProjectPolicy(expected_revision=3))
    with pytest.raises(ValueError):
        publisher.dispatch("alice", draft["id"])


def test_session_csrf_and_artifact_idor(tmp_path):
    store, project, _ = job(tmp_path, model=False)
    app = create_app(store=store)
    client = TestClient(app)
    assert client.get("/v1/projects").status_code == 401
    signed = client.post(
        "/v1/session", json={"username": "alice", "password": "long-password-alice"}
    )
    assert signed.status_code == 200
    csrf = signed.json()["csrf"]
    assert (
        client.post("/v1/projects", json={"name": "Denied", "client": "Example"}).status_code == 403
    )
    assert (
        client.post(
            "/v1/projects",
            headers={"X-CSRF-Token": csrf, "Origin": "https://evil.example"},
            json={"name": "Denied", "client": "Example"},
        ).status_code
        == 403
    )
    assert client.get(f"/v1/projects/{project['id']}").status_code == 200
    bob = TestClient(app)
    bob.post("/v1/session", json={"username": "bob", "password": "long-password-bob"})
    assert bob.get(f"/v1/projects/{project['id']}").status_code == 403
    assert bob.get("/v1/projects").json() == []


def test_disabled_repository_connector_cannot_bypass_registry(tmp_path):
    store, project, _ = job(tmp_path, model=False)
    store.update_policy(
        "alice",
        project["id"],
        ProjectPolicy(expected_revision=2, repository="owned/test", repository_id=123),
    )
    store.set_setting("disabled_adapters", ["github_repository"])

    class NoSources:
        def repository(self, *_):
            raise AssertionError("Disabled adapter must never dispatch")

    client = TestClient(create_app(store=store, sources=NoSources()))
    signed = client.post(
        "/v1/session", json={"username": "alice", "password": "long-password-alice"}
    )
    result = client.post(
        f"/v1/projects/{project['id']}/repository-snapshots",
        headers={"X-CSRF-Token": signed.json()["csrf"]},
        json={"ref": "main"},
    )
    assert result.status_code == 403


def test_approved_success_is_idempotent_and_unknown_write_reconciles(tmp_path):
    store, _, report_id = reviewed(tmp_path)
    posted = []

    def remote(url, data=None, **_):
        if data is not None:
            posted.append(data)
            return {"number": 7, "title": data["title"], "body": data["body"]}
        return {"id": 123}

    publisher = Publisher(store, request=remote, enabled=True)
    draft = publisher.draft("alice", report_id, "Reviewed maintenance")
    publisher.approve(
        "alice", draft["id"], Approval(expected_revision=1, payload_hash=draft["payload_hash"])
    )
    assert publisher.dispatch("alice", draft["id"])["status"] == "published"
    assert publisher.dispatch("alice", draft["id"])["status"] == "published"
    assert len(posted) == 1


def test_expired_approval_does_not_dispatch(tmp_path):
    store, _, report_id = reviewed(tmp_path)
    publisher = Publisher(
        store,
        request=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not send")),
        enabled=True,
    )
    draft = publisher.draft("alice", report_id, "Reviewed maintenance")
    publisher.approve(
        "alice", draft["id"], Approval(expected_revision=1, payload_hash=draft["payload_hash"])
    )
    with store.connect() as db:
        db.execute("UPDATE publications SET expires='2000-01-01' WHERE id=?", (draft["id"],))
    with pytest.raises(ValueError):
        publisher.dispatch("alice", draft["id"])


def test_reconciliation_checks_remote_repository_identity_first(tmp_path):
    store, _, report_id = reviewed(tmp_path)
    changed = False

    def remote(url, data=None, **_):
        if data is not None:
            raise TimeoutError("response lost")
        if "?" in url:
            raise AssertionError("Must not inspect issues in a changed repository")
        return {"id": 999 if changed else 123}

    publisher = Publisher(store, request=remote, enabled=True)
    draft = publisher.draft("alice", report_id, "Reviewed maintenance")
    publisher.approve(
        "alice", draft["id"], Approval(expected_revision=1, payload_hash=draft["payload_hash"])
    )
    publisher.dispatch("alice", draft["id"])
    changed = True
    with pytest.raises(ValueError):
        publisher.reconcile("alice", draft["id"])


def test_unexpected_remote_content_is_not_a_verified_receipt(tmp_path):
    store, _, report_id = reviewed(tmp_path)
    publisher = Publisher(
        store,
        request=lambda _url, data=None, **_: (
            {"id": 123} if data is None else {"number": 7, "title": "Unexpected", "body": "Changed"}
        ),
        enabled=True,
    )
    draft = publisher.draft("alice", report_id, "Reviewed maintenance")
    publisher.approve(
        "alice", draft["id"], Approval(expected_revision=1, payload_hash=draft["payload_hash"])
    )
    assert publisher.dispatch("alice", draft["id"])["status"] == "outcome_unknown"
