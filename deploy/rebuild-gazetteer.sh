#!/usr/bin/env bash
# Run ON THE VPS after syncing code, if geo/data/build_gazetteer.py or ALIAS_MAP changed.
# Rebuilds worker/geo/data/settlements.db (full rebuild — backup first if you customized DB).
#
#   sudo -u neptun bash /home/neptun/app/deploy/rebuild-gazetteer.sh
#
set -euo pipefail
APP_DIR="${APP_DIR:-/home/neptun/app}"
WORKER_DIR="$APP_DIR/worker"
VENV_PYTHON="${VENV_PYTHON:-/home/neptun/venv/bin/python}"

if [ ! -f "$WORKER_DIR/geo/data/build_gazetteer.py" ]; then
  echo "ERROR: $WORKER_DIR/geo/data/build_gazetteer.py not found" >&2
  exit 1
fi

PY=python3
if [ -x "$VENV_PYTHON" ]; then
  PY="$VENV_PYTHON"
fi

echo "[rebuild-gazetteer] using $PY"
cd "$WORKER_DIR/geo/data"
"$PY" build_gazetteer.py
chmod 666 "$WORKER_DIR/geo/data/settlements.db" 2>/dev/null || true
echo "[rebuild-gazetteer] OK: $WORKER_DIR/geo/data/settlements.db"
