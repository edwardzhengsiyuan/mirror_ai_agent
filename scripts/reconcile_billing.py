"""Inspect pending charges; explicitly resolve one after stopping serving processes.

No automatic age-based refunds: a pending request may already have served its answer.
Back up the database first and use logs to determine the requested resolution.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.billing import BillingService, BillingStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--action", choices=("list", "settle", "refund"), default="list")
    parser.add_argument("--request-id")
    parser.add_argument("--reason")
    parser.add_argument("--service-stopped", action="store_true",
                        help="Confirm all processes serving this billing database are stopped")
    args = parser.parse_args(argv)
    if not args.db.is_file():
        parser.error("Existing billing database required")
    if args.action == "list":
        # Inspection does not initialize/migrate the database.
        conn = sqlite3.connect(args.db.resolve().as_uri() + "?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT * FROM ledger WHERE kind = 'charge' AND status = 'pending' ORDER BY ts").fetchall()
            print(json.dumps([dict(row) for row in rows], ensure_ascii=False, indent=2))
        finally:
            conn.close()
        return 0
    if not args.service_stopped or not args.request_id or not args.reason or not args.reason.strip():
        parser.error("Resolution requires --service-stopped, --request-id and --reason")
    service = BillingService(BillingStore(str(args.db)))
    try:
        operation = service.refund if args.action == "refund" else service.settle
        receipt = operation(args.request_id, resolution_reason=args.reason)
    except ValueError as exc:
        parser.error(str(exc))
    if receipt is None:
        parser.error("Charge not found")
    print(json.dumps(receipt.to_dict(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
