"""Actual temporary SQLite/credential tests, not browser or consumer acceptance."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from contracts.repairclaim import Fact
from repairclaim_api.errors import DomainError
from repairclaim_api.store import Store

PASSWORD = "repairclaim-test-password-only"


@pytest.fixture
def setup_store(tmp_path):
    clock = [1_000_000.0]
    path = tmp_path / "repairclaim.sqlite3"
    store = Store(path, clock=lambda: clock[0])
    owner = store.provision_owner("owner", PASSWORD)
    other = store.provision_owner("other", PASSWORD)
    a = store.login("owner", PASSWORD)
    b = store.login("other", PASSWORD)
    vehicle = store.create_vehicle(
        a.token, make="Honda", model="Fixture", model_year=2018, jurisdiction="US"
    )
    case = store.create_case(a.token, vehicle["id"], "Fixture repair")
    return store, clock, path, owner, other, a, b, vehicle, case


def denied(code, callable_):
    with pytest.raises(DomainError) as error:
        callable_()
    assert error.value.code == code
    return error.value


def test_passwords_sessions_and_csrf_are_not_stored_in_plaintext(setup_store):
    store, _, path, _, _, a, _, _, _ = setup_store
    assert store.authenticate(a.token)["username"] == "owner"
    store.check_csrf(a.token, a.csrf_token)
    denied("csrf_failed", lambda: store.check_csrf(a.token, "wrong"))
    with sqlite3.connect(path) as db:
        dump = "\n".join(db.iterdump())
    assert PASSWORD not in dump
    assert a.token not in dump
    assert a.csrf_token not in dump
    assert a.token not in repr(a)


def test_unknown_user_and_wrong_password_have_same_safe_error(setup_store):
    store, *_ = setup_store
    first = denied("authentication_failed", lambda: store.login("owner", "not-it"))
    second = denied("authentication_failed", lambda: store.login("absent", "not-it"))
    assert str(first) == str(second)
    assert "not-it" not in str(first)


def test_login_throttling_persists_across_store_instances(setup_store):
    store, clock, path, *_ = setup_store
    for _ in range(5):
        denied("authentication_failed", lambda: store.login("owner", "not-it"))
    restarted = Store(path, clock=lambda: clock[0])
    denied("rate_limited", lambda: restarted.login("owner", PASSWORD))
    clock[0] += 901
    assert restarted.login("owner", PASSWORD).token


def test_session_expiry_and_logout_revoke_every_later_operation(setup_store):
    store, clock, _, _, _, a, _, _, case = setup_store
    store.logout(a.token)
    denied("authentication_required", lambda: store.get_case(a.token, case["id"]))
    fresh = store.login("owner", PASSWORD)
    clock[0] = fresh.expires_at
    denied("authentication_required", lambda: store.authenticate(fresh.token))


@pytest.mark.parametrize("password", ["short", "x" * 257, "🔒" * 100])
def test_credential_resource_bounds(setup_store, password):
    store, *_ = setup_store
    denied("invalid_credentials", lambda: store.provision_owner("new", password))


def test_other_household_cannot_list_read_edit_or_delete_private_case(setup_store):
    store, _, _, _, _, _, b, vehicle, case = setup_store
    assert store.list_cases(b.token) == []
    for action in (
        lambda: store.get_case(b.token, case["id"]),
        lambda: store.snapshot(b.token, case["id"]),
        lambda: store.replace_facts(b.token, case["id"], 1, ()),
        lambda: store.delete_case(b.token, case["id"], 1),
        lambda: store.create_case(b.token, vehicle["id"], "Not mine"),
    ):
        assert denied("not_found", action).status == 404


def test_sqlite_composite_foreign_key_blocks_cross_household_vehicle_reference(setup_store):
    _, _, path, _, other, _, _, vehicle, _ = setup_store
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO cases(id,household_id,vehicle_id,title,revision,deleted) "
                "VALUES(?,?,?,?,1,0)",
                ("forged", other["household_id"], vehicle["id"], "forged"),
            )


def test_case_snapshot_has_vehicle_attributes_and_durable_revisions(setup_store):
    store, clock, path, _, _, a, _, _, case = setup_store
    original = store.snapshot(a.token, case["id"])
    assert {fact.field for fact in original.facts} >= {"make", "model", "model_year"}
    repair = Fact(field="repair_mileage", value="90000", unit="mi", status="user_reported")
    updated = store.replace_facts(a.token, case["id"], 1, (*original.facts, repair))
    assert updated["revision"] == 2
    restarted = Store(path, clock=lambda: clock[0])
    assert restarted.snapshot(a.token, case["id"]).revision == 2
    assert restarted.snapshot(a.token, case["id"], revision=1) == original
    assert restarted.snapshot(a.token, case["id"]).facts[-1] == repair
    denied("revision_conflict", lambda: store.replace_facts(a.token, case["id"], 1, ()))


def test_concurrent_edit_has_one_winner_not_last_writer_wins(setup_store):
    store, _, _, _, _, a, _, _, case = setup_store

    def update(value):
        try:
            return store.replace_facts(
                a.token,
                case["id"],
                1,
                (Fact(field="component", value=value, status="user_reported"),),
            )["revision"]
        except DomainError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, ["compressor", "engine"]))
    assert sorted(map(str, results)) == ["2", "revision_conflict"]


def test_explicit_viewer_grant_is_case_scoped_and_cannot_escalate(setup_store):
    store, _, _, _, other, a, b, vehicle, case = setup_store
    second = store.create_case(a.token, vehicle["id"], "Other private case")
    store.grant(a.token, case["id"], other["id"], "viewer")
    assert store.get_case(b.token, case["id"])["role"] == "viewer"
    assert [row["id"] for row in store.list_cases(b.token)] == [case["id"]]
    denied("not_found", lambda: store.get_case(b.token, second["id"]))
    denied("not_found", lambda: store.replace_facts(b.token, case["id"], 1, ()))
    denied("not_found", lambda: store.grant(b.token, case["id"], other["id"], "editor"))
    denied("invalid_grant", lambda: store.grant(a.token, case["id"], other["id"], "owner"))


def test_editor_can_change_facts_but_cannot_delete_and_revocation_is_immediate(setup_store):
    store, _, _, _, other, a, b, _, case = setup_store
    store.grant(a.token, case["id"], other["id"], "editor")
    assert store.replace_facts(b.token, case["id"], 1, ())["revision"] == 2
    denied("not_found", lambda: store.delete_case(b.token, case["id"], 2))
    store.revoke_grant(a.token, case["id"], other["id"])
    denied("not_found", lambda: store.get_case(b.token, case["id"]))
    denied("not_found", lambda: store.replace_facts(b.token, case["id"], 2, ()))


def test_expired_grant_is_not_retained_by_an_authenticated_session(setup_store):
    store, clock, _, _, other, a, b, _, case = setup_store
    store.grant(a.token, case["id"], other["id"], "viewer", ttl=10)
    clock[0] += 10
    denied("not_found", lambda: store.get_case(b.token, case["id"]))


def test_deleted_case_cannot_be_read_edited_or_granted_again(setup_store):
    store, _, path, _, other, a, b, _, case = setup_store
    store.grant(a.token, case["id"], other["id"], "editor")
    store.delete_case(a.token, case["id"], 1)
    for token in (a.token, b.token):
        denied("not_found", lambda token=token: store.snapshot(token, case["id"]))
        denied("not_found", lambda token=token: store.replace_facts(token, case["id"], 1, ()))
    denied("not_found", lambda: store.grant(a.token, case["id"], other["id"], "viewer"))
    assert store.list_cases(a.token) == []
    with sqlite3.connect(path) as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM fact_revisions WHERE case_id=?", (case["id"],)
            ).fetchone()[0]
            == 0
        )
        assert db.execute("SELECT title FROM cases WHERE id=?", (case["id"],)).fetchone()[0] == ""


def test_manual_fact_input_cannot_assert_document_or_manufacturer_authentication(setup_store):
    store, _, _, _, _, a, _, _, case = setup_store
    from contracts.repairclaim import EvidenceAnchor

    anchored = Fact(
        field="component",
        value="engine",
        status="manufacturer_response",
        anchor=EvidenceAnchor(document_id="fake-doc", sha256="a" * 64, page=1, quote="engine"),
    )
    denied(
        "manual_fact_authority", lambda: store.replace_facts(a.token, case["id"], 1, (anchored,))
    )


def test_audit_records_actions_without_private_fact_values(setup_store):
    store, _, _, _, _, a, b, _, case = setup_store
    store.replace_facts(
        a.token,
        case["id"],
        1,
        (Fact(field="diagnostic_code", value="PRIVATE-CODE", status="user_reported"),),
    )
    audit = store.timeline(a.token, case["id"])
    assert {event["action"] for event in audit} >= {"case_created", "facts_replaced"}
    assert "PRIVATE-CODE" not in str(audit)
    denied("not_found", lambda: store.timeline(b.token, case["id"]))


def test_case_limit_excludes_deleted_cases(setup_store):
    store, _, _, _, _, a, _, vehicle, case = setup_store
    for index in range(9):
        store.create_case(a.token, vehicle["id"], f"Case {index}")
    denied("case_limit", lambda: store.create_case(a.token, vehicle["id"], "Too many"))
    store.delete_case(a.token, case["id"], 1)
    assert store.create_case(a.token, vehicle["id"], "Replacement")["revision"] == 1


def test_foreign_version_one_database_is_refused_without_changing_its_journal(tmp_path):
    path = tmp_path / "other-product.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE private_data(secret TEXT)")
        db.execute("INSERT INTO private_data VALUES('unrelated-data')")
        db.execute("PRAGMA user_version=1")
    denied("foreign_store", lambda: Store(path))
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        assert db.execute("SELECT secret FROM private_data").fetchone()[0] == "unrelated-data"


def test_concurrent_initialization_does_not_race_schema_creation(tmp_path):
    path = tmp_path / "shared-initialization.sqlite3"
    with ThreadPoolExecutor(max_workers=4) as pool:
        stores = list(pool.map(lambda _: Store(path), range(4)))
    assert len(stores) == 4


def test_whitespace_password_cannot_be_provisioned(setup_store):
    store, *_ = setup_store
    denied("invalid_credentials", lambda: store.provision_owner("blank", " " * 20))
