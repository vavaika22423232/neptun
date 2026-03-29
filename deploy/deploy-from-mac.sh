#!/bin/bash
set -euo pipefail

# ╔══════════════════════════════════════════════════════════════════╗
# ║  Neptun Deploy — run from Mac                                   ║
# ║                                                                  ║
# ║  Usage:  bash deploy/deploy-from-mac.sh                          ║
# ║  From:   /Users/vladimirmalik/Desktop/render2/                   ║
# ║                                                                  ║
# ║  What it does:                                                   ║
# ║  1. rsync code to server (EXCLUDES .env, venv, node_modules)     ║
# ║  2. rsync worker code separately                                 ║
# ║  3. rsync deploy scripts                                         ║
# ║  4. SSH into server and run deploy.sh                            ║
# ║                                                                  ║
# ║  What it NEVER touches on the server:                            ║
# ║  • .env (all secrets safe)                                       ║
# ║  • venv/ (Linux Python packages safe)                            ║
# ║  • node_modules/ (rebuilt on server)                              ║
# ║  • /data/ (SQLite databases, messages.json safe)                  ║
# ║  • firebase-credentials.json (FCM credentials safe)              ║
# ╚══════════════════════════════════════════════════════════════════╝

SERVER="root@173.242.55.166"
REMOTE_APP="/home/neptun/app"
LOCAL_NEXTJS="$(cd "$(dirname "$0")/../nextjs-app" && pwd)"
LOCAL_DEPLOY="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠ $*${NC}"; }
err()  { echo -e "${RED}[$(date +%H:%M:%S)] ✗ $*${NC}" >&2; }

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Neptun Deploy from Mac             ║"
echo "║   $(date +%Y-%m-%d\ %H:%M:%S)              ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Pre-flight ────────────────────────────────────────────────────
log "Pre-flight checks..."

if [ ! -d "$LOCAL_NEXTJS/src" ]; then
  err "Cannot find nextjs-app/src at $LOCAL_NEXTJS"
  exit 1
fi

# Test SSH connection
if ! ssh -o ConnectTimeout=5 "$SERVER" "echo ok" &>/dev/null; then
  err "Cannot connect to $SERVER"
  exit 1
fi

# Verify .env exists on server (refuse to deploy if missing)
if ! ssh "$SERVER" "test -f $REMOTE_APP/.env"; then
  err ".env missing on server! Create it first before deploying."
  err "  ssh $SERVER 'nano $REMOTE_APP/.env'"
  exit 1
fi

log "  ✓ Server reachable, .env present"

# ── 1. Sync Next.js source code ──────────────────────────────────
log "[1/5] Syncing Next.js source code..."

rsync -avz --delete \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='node_modules/' \
  --exclude='.next/' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.git/' \
  --exclude='.DS_Store' \
  --exclude='worker/' \
  --exclude='deploy/' \
  --exclude='build/' \
  --exclude='firebase-credentials.json' \
  "$LOCAL_NEXTJS/" \
  "$SERVER:$REMOTE_APP/" \
  | tail -5

log "  ✓ Next.js source synced"

# ── 2. Sync worker code ──────────────────────────────────────────
log "[2/5] Syncing worker code..."

rsync -avz --delete \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='*.session' \
  --exclude='firebase-credentials.json' \
  --exclude='nominatim_cache.json' \
  "$LOCAL_NEXTJS/worker/" \
  "$SERVER:$REMOTE_APP/worker/" \
  | tail -5

log "  ✓ Worker code synced"

# ── 3. Sync SSE Gateway (Go) ──────────────────────────────────────
log "[3/5] Syncing SSE Gateway..."

LOCAL_SSE="$(cd "$(dirname "$0")/../sse-gateway" && pwd)"
if [ -d "$LOCAL_SSE" ]; then
  # Build Linux binary if Go is available
  if command -v go &>/dev/null; then
    (cd "$LOCAL_SSE" && GOOS=linux GOARCH=amd64 go build -o sse-gateway-linux .) 2>/dev/null || true
  fi
  rsync -avz \
    --exclude='.DS_Store' \
    --exclude='sse-gateway' \
    "$LOCAL_SSE/" \
    "$SERVER:$REMOTE_APP/sse-gateway/" \
    | tail -3
  if [ -f "$LOCAL_SSE/sse-gateway-linux" ]; then
    rsync -avz "$LOCAL_SSE/sse-gateway-linux" "$SERVER:$REMOTE_APP/sse-gateway/"
  fi
  log "  ✓ SSE Gateway synced"
else
  warn "  sse-gateway dir not found, skipping"
fi

# ── 4. Sync deploy scripts ───────────────────────────────────────
log "[4/5] Syncing deploy scripts..."

rsync -avz \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='.DS_Store' \
  "$LOCAL_DEPLOY/" \
  "$SERVER:$REMOTE_APP/deploy/" \
  | tail -3

# Make deploy scripts executable
ssh "$SERVER" "chmod +x $REMOTE_APP/deploy/*.sh"

log "  ✓ Deploy scripts synced"

# ── 5. Run deploy on server ──────────────────────────────────────
log "[5/5] Running deploy on server..."
echo ""

ssh -t "$SERVER" "bash $REMOTE_APP/deploy/deploy.sh"

echo ""
log "═══ Deploy from Mac complete! ═══"
