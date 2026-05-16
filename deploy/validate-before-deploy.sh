#!/usr/bin/env bash
# Run locally (Mac/Linux) before rsync — catches broken worker tests early.
# Usage:  bash deploy/validate-before-deploy.sh
# From repo root or from deploy/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKER="$ROOT/nextjs-app/worker"
cd "$WORKER"
export PYTHONPATH=.
echo "[validate] $WORKER"
python3 -m unittest discover -s tests -p 'test_*.py' -q
echo "[validate] OK"
