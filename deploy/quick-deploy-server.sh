#!/bin/bash
set -euo pipefail

# Швидке оновлення лише Next.js на сервері (запускати на сервері або через SSH).
# Не чіпає: Photon, Python worker, nginx, SSE, gazetteer.
# Повний deploy/deploy.sh потрібен після змін у worker/, залежностях з нативними модулями, systemd, nginx.
#
# Використання на сервері:
#   sudo bash /home/neptun/app/deploy/quick-deploy-server.sh
#
# Змінні:
#   RESTART_WORKER=1 — після збірки також systemctl restart neptun-worker
#   NPM_CI_FLAGS="--prefer-offline --no-audit --no-fund" — за замовчуванням

APP_DIR="${APP_DIR:-/home/neptun/app}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:3000/api/health}"
NPM_CI_FLAGS="${NPM_CI_FLAGS:---prefer-offline --no-audit --no-fund}"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
log() { echo -e "${GREEN}[quick]${NC} $*"; }
err() { echo -e "${RED}[quick]${NC} $*" >&2; }

cd "$APP_DIR"

log "npm ci $NPM_CI_FLAGS"
if [ -f package-lock.json ]; then
  npm ci --production=false $NPM_CI_FLAGS
else
  npm install --production=false $NPM_CI_FLAGS
fi

log "next build"
npx next build

if [ -d .next/standalone ]; then
  cp .next/standalone/server.js "$APP_DIR/server.js"
  cp -r public .next/standalone/public 2>/dev/null || true
  cp -r .next/static .next/standalone/.next/static 2>/dev/null || true
  log "standalone assets оновлено"
fi

chown -R neptun:neptun "$APP_DIR/.next" 2>/dev/null || true

# Мінімальна перевірка better-sqlite3 (як у повному deploy)
SQLITE_DIR="node_modules/better-sqlite3"
if [ -d "$SQLITE_DIR" ]; then
  SQLITE_NODE="$SQLITE_DIR/build/Release/better_sqlite3.node"
  if [ -f "$SQLITE_NODE" ]; then
    if ! file "$SQLITE_NODE" 2>/dev/null | grep -q "ELF"; then
      log "перезбірка better-sqlite3 для Linux…"
      (cd "$SQLITE_DIR" && npx prebuild-install || npm rebuild better-sqlite3)
    fi
  fi
fi
STANDALONE_MODULES="$APP_DIR/.next/standalone/node_modules"
if [ -d "$STANDALONE_MODULES" ]; then
  cd "$STANDALONE_MODULES"
  for hashed in $(grep -roh 'better-sqlite3-[0-9a-f]\{16\}' "$APP_DIR/.next/server/" 2>/dev/null | sort -u); do
    [ -e "$hashed" ] || ln -sf better-sqlite3 "$hashed"
  done
  cd "$APP_DIR"
fi

if [ -f "$APP_DIR/public/sitemap.xml" ]; then
  chmod 644 "$APP_DIR/public/sitemap.xml" 2>/dev/null || true
fi

log "systemctl restart neptun-web"
systemctl restart neptun-web

for i in $(seq 1 20); do
  if curl -sf "$HEALTH_URL" -o /dev/null; then
    log "health OK"
    break
  fi
  if [ "$i" -eq 20 ]; then
    err "health check не пройшов — див. journalctl -u neptun-web -n 40"
    exit 1
  fi
  sleep 1
done

if [ "${RESTART_WORKER:-0}" = "1" ]; then
  log "systemctl restart neptun-worker"
  systemctl restart neptun-worker || true
fi

log "готово (швидке оновлення Next.js)"
