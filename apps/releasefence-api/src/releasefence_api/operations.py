"""Explicit operator commands. Never migrate, generate keys or restore on startup."""

import argparse
import base64
import json
import os
import secrets
import subprocess
from pathlib import Path

import psycopg
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from .crypto import public_key
from .store import Store


def generate_keys(path):
    key = Ed25519PrivateKey.generate()
    payload = {
        "encryption_key": Fernet.generate_key().decode(),
        "signing_key": base64.b64encode(key.private_bytes_raw()).decode(),
        "public_key": public_key(key),
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(payload, stream)


def quarantine(dsn, schema):
    """Irreversible authority invalidation after an isolated restore, not resume."""
    with psycopg.connect(dsn) as db:
        db.execute(sql.SQL("SET LOCAL search_path TO {},public").format(sql.Identifier(schema)))
        tenants = [r[0] for r in db.execute("SELECT id::text FROM organizations")]
        for tenant in tenants:
            db.execute("SELECT set_config('rf.tenant',%s,true)", (tenant,))
            for kind, field in (
                ("enrollment", "revoked"),
                ("approval", "revoked"),
                ("environment", "paused"),
            ):
                db.execute(
                    "UPDATE records SET body=jsonb_set(body,ARRAY[%s],%s::jsonb),revision=revision+1 WHERE kind=%s",
                    (field, "true", kind),
                )
            for kind in ("backend", "destination"):
                db.execute(
                    "UPDATE records SET body=jsonb_set(body,'{enabled}','false'::jsonb),revision=revision+1 WHERE kind=%s",
                    (kind,),
                )
        db.execute("DELETE FROM tokens")
        db.execute("DELETE FROM sessions")
        db.execute("DELETE FROM worker_status")


def pg_environment(dsn):
    values = conninfo_to_dict(dsn)
    env = os.environ.copy()
    password = values.pop("password", None)
    if password:
        env["PGPASSWORD"] = password
    return make_conninfo(**values), env


def backup(dsn, path, *, schema="releasefence", executable="pg_dump"):
    connection, env = pg_environment(dsn)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        completed = subprocess.run(
            [
                executable,
                "--format=custom",
                "--no-owner",
                "--no-acl",
                "--schema",
                schema,
                "--dbname",
                connection,
            ],
            stdout=stream,
            stderr=subprocess.PIPE,
            env=env,
            timeout=300,
            check=False,
        )
    if completed.returncode:
        raise RuntimeError("backup failed; partial artifact retained, do not restore")


def restore_quarantined(admin_dsn, path, schema, *, executable="pg_restore"):
    # Always a NEW database. Existing/live database names are never accepted.
    name = "rf_restore_" + secrets.token_hex(10)
    with psycopg.connect(admin_dsn, autocommit=True) as db:
        db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    dsn = make_conninfo(admin_dsn, dbname=name)
    connection, env = pg_environment(dsn)
    result = subprocess.run(
        [
            executable,
            "--exit-on-error",
            "--no-owner",
            "--no-acl",
            "--dbname",
            connection,
            str(path),
        ],
        capture_output=True,
        env=env,
        timeout=300,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "isolated restore failed; database retained for investigation, no services started"
        )
    quarantine(dsn, schema)
    return name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    keys = sub.add_parser("keys")
    keys.add_argument("path", type=Path)
    install = sub.add_parser("install")
    install.add_argument("--schema", default="releasefence")
    install.add_argument("--role", default="releasefence_app")
    dump = sub.add_parser("backup")
    dump.add_argument("path", type=Path)
    dump.add_argument("--schema", default="releasefence")
    restore = sub.add_parser("restore-quarantined")
    restore.add_argument("path", type=Path)
    restore.add_argument("--schema", default="releasefence")
    args = parser.parse_args()
    if args.action == "keys":
        generate_keys(args.path)
        print("Private key file created; protect and back up separately.")
        return
    dsn = os.environ.get("RELEASEFENCE_ADMIN_DATABASE_URL")
    if not dsn:
        parser.error("explicit RELEASEFENCE_ADMIN_DATABASE_URL required")
    if args.action == "install":
        password = os.environ.get("RELEASEFENCE_DATABASE_PASSWORD", "")
        if len(password) < 24:
            parser.error("explicit strong RELEASEFENCE_DATABASE_PASSWORD required")
        Store.install(dsn, args.schema, args.role, password)
        print("Schema and non-bypass runtime role created.")
    elif args.action == "backup":
        backup(dsn, args.path, schema=args.schema)
        print("Database snapshot created. Back up encryption/signing keys separately.")
    else:
        print("Quarantined database:", restore_quarantined(dsn, args.path, args.schema))


if __name__ == "__main__":
    main()
