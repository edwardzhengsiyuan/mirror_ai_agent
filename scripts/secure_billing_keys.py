"""Offline portal-key migration/rotation. Never prints API keys or encryption keys."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.billing import BillingStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--backup", required=True, type=Path)
    parser.add_argument("--service-stopped", action="store_true")
    parser.add_argument("--rotate", action="store_true")
    args = parser.parse_args(argv)
    if not args.service_stopped or not args.db.is_file():
        parser.error("Stop all serving processes and provide an existing database")
    if args.backup.resolve() == args.db.resolve() or args.backup.exists():
        parser.error("Backup must be a new, distinct file")
    # Exclusive creation, SQLite backup API includes committed WAL contents.
    with args.backup.open("xb"):
        pass
    with closing(sqlite3.connect(args.db.resolve().as_uri() + "?mode=ro", uri=True)) as src:
        with closing(sqlite3.connect(str(args.backup))) as dst:
            src.backup(dst)
    store = BillingStore(str(args.db))
    changed = store.migrate_api_key_storage(rotate=args.rotate)
    with closing(store._connect()) as conn:
        status = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if status[0]:
            raise RuntimeError("Database still busy; keep services stopped and retry checkpoint")
        conn.execute("VACUUM")
        status = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if status[0]:
            raise RuntimeError("Database checkpoint incomplete")
        remaining = conn.execute("SELECT COUNT(*) FROM api_keys WHERE plaintext IS NOT NULL").fetchone()[0]
    print(json.dumps({"plaintext_rows": remaining, "rotated_rows": changed if args.rotate else 0,
                      "backup": str(args.backup), "backup_contains_legacy_secrets": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
