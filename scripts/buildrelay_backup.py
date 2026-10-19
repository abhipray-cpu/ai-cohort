"""Back up a running local SQLite store, or restore into a new stopped directory."""

import argparse

from buildrelay_api.backup import backup, restore

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("backup", "restore"))
    p.add_argument("source")
    p.add_argument("destination")
    a = p.parse_args()
    print((backup if a.action == "backup" else restore)(a.source, a.destination))
