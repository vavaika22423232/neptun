#!/usr/bin/env bash
# Quick checks after deploy (run on VPS as root or neptun).
# Usage:  bash deploy/check-post-deploy.sh
# Optional: BASE_URL=http://127.0.0.1:3000  ADMIN_HEADER_SECRET=...  (for resolve-quality)
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:3000}"
HEALTH="${BASE_URL%/}/api/health"

echo "== Health: $HEALTH"
curl -sfS "$HEALTH" | head -c 400 || { echo "FAIL: health" >&2; exit 1; }
echo ""
echo "OK health"

if [ -n "${ADMIN_HEADER_SECRET:-}" ]; then
  RQ="${BASE_URL%/}/api/admin/resolve-quality"
  echo "== Resolve quality: $RQ"
  curl -sfS -H "X-Auth-Secret: $ADMIN_HEADER_SECRET" "$RQ" | head -c 2000 || echo "WARN: resolve-quality failed (wrong secret or route)"
  echo ""
else
  echo "Skip /api/admin/resolve-quality (set ADMIN_HEADER_SECRET to enable)"
fi

echo "== systemd"
systemctl is-active neptun-web.service neptun-worker.service 2>/dev/null || true
