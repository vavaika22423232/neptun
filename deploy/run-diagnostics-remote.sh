#!/usr/bin/env bash
# Запуск с Mac: диагностика 502 на прод-VPS (тот же хост, что deploy-from-mac).
#   bash deploy/run-diagnostics-remote.sh
#   NEPTUN_SERVER=user@host bash deploy/run-diagnostics-remote.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER="${NEPTUN_SERVER:-root@173.242.55.166}"
SCRIPT="$ROOT/deploy/diagnose-502.sh"

if [ ! -f "$SCRIPT" ]; then
  echo "Missing $SCRIPT" >&2
  exit 1
fi

if ! ssh -o ConnectTimeout=10 "$SERVER" "echo ok" &>/dev/null; then
  echo "Cannot SSH to $SERVER (проверьте ключи и сеть)." >&2
  exit 1
fi

echo "Running diagnose-502.sh on $SERVER ${*:-}..."
ssh "$SERVER" bash -s -- "$@" < "$SCRIPT"
