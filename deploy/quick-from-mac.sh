#!/bin/bash
set -euo pipefail

# Швидке оновлення сайту з Mac: тільки Next.js + коротка збірка на сервері.
# Швидше за deploy-from-mac.sh, бо немає: worker/SSE/Photon-скриптів, повного deploy.sh.
#
# bash deploy/quick-from-mac.sh
#
# Опції:
#   SKIP_VALIDATE=1      — пропустити локальні Python-тести worker (швидше)
#   SYNC_WORKER=1        — також rsync worker/ і RESTART_WORKER на сервері
#   SKIP_DEPLOY_SYNC=0   — за замовчуванням синкає deploy/ на сервер (щоб був актуальний quick-deploy-server.sh)
#
# Якщо змінювали Python worker, залежності з нативом, nginx, systemd — використовуйте deploy-from-mac.sh.

SERVER="root@173.242.55.166"
REMOTE_APP="/home/neptun/app"
LOCAL_NEXTJS="$(cd "$(dirname "$0")/../nextjs-app" && pwd)"
LOCAL_DEPLOY="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
log() { echo -e "${GREEN}[quick-mac]${NC} $*"; }
err() { echo -e "${RED}[quick-mac]${NC} $*" >&2; }

if [ ! -d "$LOCAL_NEXTJS/src" ]; then
  err "Немає nextjs-app: $LOCAL_NEXTJS"
  exit 1
fi
if ! ssh -o ConnectTimeout=8 "$SERVER" "test -f $REMOTE_APP/.env"; then
  err "Немає .env на сервері або SSH недоступний"
  exit 1
fi

if [ "${SKIP_VALIDATE:-0}" != "1" ] && [ -f "$LOCAL_DEPLOY/validate-before-deploy.sh" ]; then
  log "локальна валідація worker (SKIP_VALIDATE=1 щоб пропустити)…"
  bash "$LOCAL_DEPLOY/validate-before-deploy.sh"
fi

log "rsync Next.js → сервер…"
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
  | tail -8

if [ "${SYNC_WORKER:-0}" = "1" ]; then
  log "rsync worker…"
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
fi

if [ "${SKIP_DEPLOY_SYNC:-0}" != "1" ]; then
  log "rsync deploy/*.sh…"
  rsync -avz \
    --exclude='.env' \
    --exclude='.env.*' \
    --exclude='.DS_Store' \
    "$LOCAL_DEPLOY/" \
    "$SERVER:$REMOTE_APP/deploy/" \
    | tail -3
  ssh "$SERVER" "chmod +x $REMOTE_APP/deploy/*.sh"
fi

RW="${SYNC_WORKER:-0}"
log "SSH: quick-deploy-server.sh (RESTART_WORKER=$RW)…"
ssh "$SERVER" "RESTART_WORKER=$RW bash $REMOTE_APP/deploy/quick-deploy-server.sh"

log "готово."
