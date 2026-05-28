#!/usr/bin/env bash
# Online backup of the billing SQLite database.
#
# Uses SQLite's .backup command, which is the official online-snapshot
# mechanism: it copies pages while the writer is live, so there is no
# downtime and the backup is always internally consistent (unlike a naive
# `cp billing.db` while a write is in flight, which can corrupt the WAL).
#
# Usage:
#   scripts/backup_billing.sh                            # uses defaults
#   BILLING_DB=/opt/bazi/storage/billing.db \
#     BACKUP_DIR=/var/backups/bazi-billing \
#     RETENTION_DAYS=30 \
#     scripts/backup_billing.sh
#
# Suggested crontab line (run daily at 03:17 server time, off the hour to
# spread load when many hosts share a backup target):
#
#   17 3 * * * /opt/bazi/scripts/backup_billing.sh >> /var/log/bazi-backup.log 2>&1
#
# After installation:
#
#   chmod +x scripts/backup_billing.sh
#   crontab -e   # paste the line above
#
# For off-server durability, append an `rclone copy` / `aws s3 cp` / `coscli`
# line below the local snapshot. The script exits non-zero on any failure
# so cron will email you (assuming an MTA + /etc/aliases is configured).

set -euo pipefail

BILLING_DB="${BILLING_DB:-/opt/bazi/storage/billing.db}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/bazi-billing}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/billing-${TIMESTAMP}.db"

if [[ ! -f "$BILLING_DB" ]]; then
  echo "[backup_billing] FATAL: source DB not found: $BILLING_DB" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

echo "[backup_billing] $(date -Iseconds) — snapshotting $BILLING_DB"
sqlite3 "$BILLING_DB" ".backup '${OUT}'"

# Compress in place; SQLite backups dedupe well with zstd, fall back to gzip.
if command -v zstd >/dev/null 2>&1; then
  zstd --quiet --rm "$OUT"
  FINAL="${OUT}.zst"
elif command -v gzip >/dev/null 2>&1; then
  gzip "$OUT"
  FINAL="${OUT}.gz"
else
  FINAL="$OUT"
fi

SIZE_BYTES=$(stat -c%s "$FINAL" 2>/dev/null || stat -f%z "$FINAL")
echo "[backup_billing] wrote $FINAL ($SIZE_BYTES bytes)"

# Prune older snapshots beyond the retention window.
find "$BACKUP_DIR" -maxdepth 1 -type f \
  \( -name 'billing-*.db' -o -name 'billing-*.db.gz' -o -name 'billing-*.db.zst' \) \
  -mtime "+${RETENTION_DAYS}" -print -delete || true

# --- Optional: ship to remote object storage. Uncomment and customize. ---
#
# # Tencent Cloud COS (Chinese hosts):
# coscli cp "$FINAL" "cos://your-bucket/bazi-billing/"
#
# # AWS S3 compatible:
# aws s3 cp "$FINAL" "s3://your-bucket/bazi-billing/"
#
# # Backblaze B2 / rclone-friendly:
# rclone copy "$FINAL" b2:your-bucket/bazi-billing/

echo "[backup_billing] done"
