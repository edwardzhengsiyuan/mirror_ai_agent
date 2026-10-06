#!/usr/bin/env bash
# Scheduled preview only. Never deletes conversations; preserve last good report.
set -euo pipefail
umask 077
days="${CONVERSATION_RETENTION_DAYS:-90}"
report_dir="${RETENTION_REPORT_DIR:-/var/lib/mirror-retention}"
container="${RETENTION_CONTAINER:-bazi-agent-api}"
[[ "$days" =~ ^[1-9][0-9]*$ ]] || { echo 'Invalid retention days' >&2; exit 2; }
mkdir -p "$report_dir"
temp_report=$(mktemp "$report_dir/.preview.XXXXXX")
trap 'rm -f -- "$temp_report"' EXIT
docker exec "$container" python /app/scripts/prune_conversations.py \
  --storage /app/storage --days "$days" > "$temp_report"
mv -f -- "$temp_report" "$report_dir/latest.json"
echo "Conversation retention preview complete (${days} days); no conversations deleted."
