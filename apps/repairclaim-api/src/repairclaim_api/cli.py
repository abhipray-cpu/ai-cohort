"""Explicit operator actions. No bundled coverage, default credentials or live calls."""

import argparse
import getpass
import json
import os
from pathlib import Path

from repairclaim_api.operations import restore_backup
from repairclaim_api.parser import RestrictedParser
from repairclaim_api.store import Store


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.environ.get("REPAIRCLAIM_DATA_DIR"))
    commands = parser.add_subparsers(dest="command", required=True)
    provision = commands.add_parser("provision")
    provision.add_argument("username")
    capture = commands.add_parser("capture")
    capture.add_argument("source_id")
    capture.add_argument("url")
    capture.add_argument("pdf", type=Path)
    activate = commands.add_parser("activate-programme")
    activate.add_argument("definition", type=Path)
    commands.add_parser("registry")
    commands.add_parser("backup")
    restore = commands.add_parser("restore")
    restore.add_argument("backup", type=Path)
    restore.add_argument("--erasure-ledger", required=True, type=Path)
    commands.add_parser("activate-restored")
    commands.add_parser("maintain")
    args = parser.parse_args(argv)
    if not args.data_dir:
        parser.error("Set REPAIRCLAIM_DATA_DIR or --data-dir; use a dedicated product directory.")
    root = Path(args.data_dir).resolve()
    if args.command == "restore":
        restore_backup(
            args.backup.read_bytes(),
            getpass.getpass("Backup passphrase: "),
            root,
            args.erasure_ledger,
        )
        print("Restored quarantined. Review erasure ledger before activate-restored.")
        return
    store = Store(root / "repairclaim.sqlite3")
    if args.command == "provision":
        password = getpass.getpass("New account password (12+ characters): ")
        if password != getpass.getpass("Repeat password: "):
            parser.error("Passwords do not match")
        store.provision_owner(args.username, password)
        print("Account provisioned; no default password stored in config.")
    elif args.command == "capture":
        raw = args.pdf.read_bytes()
        parsed = RestrictedParser(mode=os.environ.get("REPAIRCLAIM_PARSER", "auto")).run(
            "parse", raw, args.pdf.name
        )
        print(json.dumps(store.capture_source(args.source_id, args.url, raw, parsed)))
    elif args.command == "activate-programme":
        store.activate_programme(json.loads(args.definition.read_text()))
        print("Reviewed programme activated; affected outputs invalidated.")
    elif args.command == "registry":
        print(json.dumps(store.registry_status(), indent=2))
    elif args.command == "backup":
        password = getpass.getpass("New backup passphrase (12+ characters): ")
        if password != getpass.getpass("Repeat passphrase: "):
            parser.error("Passphrases do not match")
        data = store.create_backup(password)
        directory = root / "backups"
        directory.mkdir(mode=0o700, exist_ok=True)
        if directory.is_symlink():
            parser.error("Backup directory must not be a symlink")
        path = directory / f"repairclaim-{int(store._now())}.rcbk"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        print(path)
        print(
            "Keep the current erasure.jsonl separately and protect it. Managed backups expire after 30 days during maintenance."
        )
    elif args.command == "activate-restored":
        store.activate_restored()
        print("Quarantine removed. Sessions and packet approvals remain revoked.")
    elif args.command == "maintain":
        print(json.dumps(store.maintenance()))


if __name__ == "__main__":
    main()
