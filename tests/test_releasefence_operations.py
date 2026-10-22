import json
import os
import subprocess
import sys

import pytest
from releasefence_api.errors import Forbidden
from releasefence_api.operations import generate_keys, quarantine
from test_releasefence_store import configured, rf, rf_admin  # noqa: F401


def test_key_generation_is_explicit_exclusive_and_private(tmp_path):
    path = tmp_path / "keys.json"
    generate_keys(path)
    values = json.loads(path.read_text())
    assert set(values) == {"encryption_key", "signing_key", "public_key"}
    assert path.stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        generate_keys(path)


def test_quarantine_disables_restored_authority_and_external_delivery(rf):
    s, t, _ = rf
    configured(rf)
    token, _csrf = s.login("owner", "owned-password-123")
    with s.db(t) as db:
        s._insert(db, "backend", "restored", {"enabled": True})
        s._insert(db, "destination", "restored", {"enabled": True})
    # Requires an admin connection, never the normal runtime role.
    quarantine(s.dsn, s.schema)  # Application role can quarantine itself, not bypass RLS.
    assert s.list("owner", t, "enrollment")[0]["revoked"]
    assert s.list("owner", t, "environment")[0]["paused"]
    assert not s.list("owner", t, "backend")[0]["enabled"]
    with pytest.raises(Forbidden):
        s.session(token)


def test_cli_refuses_install_without_explicit_admin_credentials():
    env = {k: v for k, v in os.environ.items() if not k.startswith("RELEASEFENCE_")}
    p = subprocess.run(
        [sys.executable, "-m", "releasefence_api.operations", "install"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert p.returncode != 0 and "explicit" in p.stderr.lower()


def test_real_postgres_backup_restores_to_new_quarantined_database(rf, rf_admin, tmp_path):
    import shutil
    from pathlib import Path

    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from releasefence_api.operations import backup, restore_quarantined

    s, _t, _ = rf
    configured(rf)
    dump = shutil.which("pg_dump")
    restore = shutil.which("pg_restore")
    if not dump or not restore:
        import pgserver

        binaries = Path(pgserver.__file__).parent / "pginstall/bin"
        dump = str(binaries / "pg_dump")
        restore = str(binaries / "pg_restore")
    path = tmp_path / "snapshot.dump"
    backup(rf_admin, path, schema=s.schema, executable=dump)
    name = restore_quarantined(rf_admin, path, s.schema, executable=restore)
    assert name.startswith("rf_restore_") and path.stat().st_size > 0
    with psycopg.connect(make_conninfo(rf_admin, dbname=name)) as db:
        db.execute(sql.SQL("SET LOCAL search_path TO {},public").format(sql.Identifier(s.schema)))
        assert db.execute("SELECT count(*) FROM tokens").fetchone()[0] == 0
        assert (
            db.execute("SELECT body->>'revoked' FROM records WHERE kind='enrollment'").fetchone()[0]
            == "true"
        )
        assert (
            db.execute("SELECT body->>'paused' FROM records WHERE kind='environment'").fetchone()[0]
            == "true"
        )
        assert db.execute("SELECT count(*) FROM records WHERE kind='audit'").fetchone()[0] > 0
