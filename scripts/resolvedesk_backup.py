"""Create a consistent, integrity-checked ResolveDesk SQLite backup."""

import argparse
from pathlib import Path

from resolvedesk_api.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", help="New backup directory")
    parser.add_argument("--data-dir", default="var/resolvedesk")
    args = parser.parse_args()
    if not (Path(args.data_dir) / "resolvedesk.sqlite3").is_file():
        raise SystemExit("Source database does not exist; no backup was created")
    Store(args.data_dir).backup(args.destination)
    print("Backup completed and SQLite integrity check passed.")


if __name__ == "__main__":
    main()
