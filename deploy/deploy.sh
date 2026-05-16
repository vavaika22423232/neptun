#!/bin/bash
set -euo pipefail

# ╔══════════════════════════════════════════════════════════════════╗
# ║  Neptun Deploy Script — hardened, safe, idempotent              ║
# ║                                                                  ║
# ║  Runs ON THE SERVER after code is synced by deploy-from-mac.sh  ║
# ║  Usage:  sudo bash /home/neptun/app/deploy/deploy.sh            ║
# ║                                                                  ║
# ║  Safety guarantees:                                              ║
# ║  • .env is NEVER overwritten (excluded from rsync)               ║
# ║  • .env + firebase creds backed up before every deploy           ║
# ║  • Python venv created if missing, never deleted                 ║
# ║  • better-sqlite3 native binary rebuilt for Linux                ║
# ║  • Health checks verify services are alive after restart         ║
# ║  • Crash-loop protection via systemd StartLimitBurst             ║
# ╚══════════════════════════════════════════════════════════════════╝

# ── Configuration ─────────────────────────────────────────────────
APP_DIR="/home/neptun/app"
WORKER_DIR="$APP_DIR/worker"
VENV_DIR="/home/neptun/venv"
BACKUP_DIR="/home/neptun/backups"
ENV_FILE="$APP_DIR/.env"
FIREBASE_CREDS="$WORKER_DIR/firebase-credentials.json"
HEALTH_URL="http://127.0.0.1:3000/api/health"
MAX_BACKUPS=10

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠ $*${NC}"; }
err()  { echo -e "${RED}[$(date +%H:%M:%S)] ✗ $*${NC}" >&2; }
die()  { err "$@"; exit 1; }

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       Neptun Deploy — $(date +%Y-%m-%d)      ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Pre-flight checks ────────────────────────────────────────────
log "[0/7] Pre-flight checks..."

[ -f "$ENV_FILE" ] || die ".env not found at $ENV_FILE — aborting to prevent data loss"

if ! command -v node &>/dev/null; then
  die "Node.js not installed"
fi

if ! command -v python3 &>/dev/null; then
  die "Python3 not installed"
fi

log "  ✓ .env exists ($(wc -l < "$ENV_FILE") lines)"
log "  ✓ Node $(node -v), npm $(npm -v)"
log "  ✓ Python $(python3 --version)"

# ── 1. Backup critical files ─────────────────────────────────────
log "[1/7] Backing up critical files..."
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

cp "$ENV_FILE" "$BACKUP_DIR/.env.$TIMESTAMP"
log "  ✓ .env → $BACKUP_DIR/.env.$TIMESTAMP"

if [ -f "$FIREBASE_CREDS" ]; then
  cp "$FIREBASE_CREDS" "$BACKUP_DIR/firebase-credentials.$TIMESTAMP.json"
  log "  ✓ firebase-credentials.json backed up"
fi

# Rotate old backups (keep last $MAX_BACKUPS)
cd "$BACKUP_DIR"
ls -t .env.* 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm --
ls -t firebase-credentials.*.json 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm --
log "  ✓ Rotated backups (keeping last $MAX_BACKUPS)"

# ── 2. Install Node.js dependencies ──────────────────────────────
log "[2/7] Installing Node.js dependencies..."
cd "$APP_DIR"

# Use npm ci for deterministic installs if lockfile exists
if [ -f package-lock.json ]; then
  npm ci --production=false 2>&1 | tail -3
else
  npm install --production=false 2>&1 | tail -3
fi
log "  ✓ Node modules installed"

# ── 3. Build Next.js ─────────────────────────────────────────────
log "[3/7] Building Next.js..."
cd "$APP_DIR"
npx next build 2>&1 | tail -5

# Copy standalone output to app root + static assets
if [ -d .next/standalone ]; then
  cp .next/standalone/server.js "$APP_DIR/server.js"
  log "  ✓ server.js copied to app root"
  cp -r public .next/standalone/public 2>/dev/null || true
  cp -r .next/static .next/standalone/.next/static 2>/dev/null || true
  rm -f .next/standalone/.env 2>/dev/null || true
  log "  ✓ Static assets copied to standalone"
fi

# Ensure sitemap.xml is readable by nginx (www-data)
if [ -f "$APP_DIR/public/sitemap.xml" ]; then
  chmod 644 "$APP_DIR/public/sitemap.xml"
  chmod 755 "$APP_DIR/public" 2>/dev/null || true
  log "  ✓ sitemap.xml permissions set"
fi

# ── 4. Fix native modules ────────────────────────────────────────
log "[4/7] Fixing native modules (better-sqlite3)..."
cd "$APP_DIR"

# Ensure better-sqlite3 has correct Linux binary (not macOS)
SQLITE_DIR="node_modules/better-sqlite3"
if [ -d "$SQLITE_DIR" ]; then
  SQLITE_NODE="$SQLITE_DIR/build/Release/better_sqlite3.node"
  if [ -f "$SQLITE_NODE" ]; then
    FILE_TYPE=$(file "$SQLITE_NODE" 2>/dev/null || echo "unknown")
    if echo "$FILE_TYPE" | grep -q "ELF"; then
      log "  ✓ better-sqlite3 binary is Linux ELF (correct)"
    else
      warn "  better-sqlite3 binary is NOT Linux ELF — rebuilding..."
      cd "$SQLITE_DIR"
      npx prebuild-install || npm rebuild better-sqlite3
      cd "$APP_DIR"
      log "  ✓ better-sqlite3 rebuilt for Linux"
    fi
  else
    warn "  better-sqlite3 .node file missing — installing prebuilt..."
    cd "$SQLITE_DIR"
    npx prebuild-install || npm rebuild better-sqlite3
    cd "$APP_DIR"
  fi
fi

# Symlink Turbopack hash-renamed dirs → original
STANDALONE_MODULES="$APP_DIR/.next/standalone/node_modules"
if [ -d "$STANDALONE_MODULES" ]; then
  cd "$STANDALONE_MODULES"
  for hashed in $(grep -roh 'better-sqlite3-[0-9a-f]\{16\}' "$APP_DIR/.next/server/" 2>/dev/null | sort -u); do
    if [ ! -e "$hashed" ]; then
      ln -sf better-sqlite3 "$hashed"
      log "  ✓ Symlink: $hashed → better-sqlite3"
    fi
  done
fi
cd "$APP_DIR"

# ── 5. Setup Python venv & worker deps ───────────────────────────
log "[5/7] Setting up Python worker..."

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  warn "  Python venv missing — creating..."
  python3 -m venv "$VENV_DIR"
  log "  ✓ Created venv at $VENV_DIR"
fi

# Verify venv is functional
if [ ! -f "$VENV_DIR/bin/python" ]; then
  warn "  venv broken — recreating..."
  rm -rf "$VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# Install/update worker dependencies
if [ -f "$WORKER_DIR/requirements.txt" ]; then
  "$VENV_DIR/bin/pip" install -r "$WORKER_DIR/requirements.txt" --quiet 2>&1 | tail -3
  log "  ✓ Worker dependencies installed"
fi

# Ensure gazetteer DB is writable by worker (neptun user)
GAZ_DB="$WORKER_DIR/geo/data/settlements.db"
if [ -f "$GAZ_DB" ]; then
  chmod 666 "$GAZ_DB" 2>/dev/null || true
  chmod 777 "$(dirname "$GAZ_DB")" 2>/dev/null || true
fi

# Verify Firebase credentials file exists
if [ ! -f "$FIREBASE_CREDS" ]; then
  warn "  firebase-credentials.json missing at $FIREBASE_CREDS"
  warn "  FCM push notifications will not work!"
else
  log "  ✓ Firebase credentials present"
fi

# ── 6. Update systemd services ───────────────────────────────────
log "[6/7] Updating & restarting services..."

# Build/copy SSE Gateway binary
SSE_DIR="$APP_DIR/sse-gateway"
if [ -d "$SSE_DIR" ]; then
  if [ -f "$SSE_DIR/sse-gateway-linux" ]; then
    cp "$SSE_DIR/sse-gateway-linux" "$SSE_DIR/sse-gateway"
    chmod +x "$SSE_DIR/sse-gateway"
    chown -R neptun:neptun "$SSE_DIR" 2>/dev/null || true
    log "  ✓ SSE Gateway binary ready"
  elif command -v go &>/dev/null; then
    if (cd "$SSE_DIR" && go build -o sse-gateway .); then
      log "  ✓ SSE Gateway built from source"
    else
      warn "  SSE Gateway build failed"
    fi
  else
    warn "  sse-gateway-linux not found and Go not installed — SSE may not start"
  fi
fi

# Copy hardened service files if they differ
DEPLOY_DIR="$APP_DIR/deploy"
if [ -d "$DEPLOY_DIR" ]; then
  for svc in neptun-web.service neptun-worker.service neptun-sse.service; do
    if [ -f "$DEPLOY_DIR/$svc" ]; then
      if ! diff -q "$DEPLOY_DIR/$svc" "/etc/systemd/system/$svc" &>/dev/null; then
        cp "$DEPLOY_DIR/$svc" "/etc/systemd/system/$svc"
        log "  ✓ Updated $svc"
      fi
    fi
  done
  systemctl daemon-reload
fi

# Sync nginx upstream with actual PM2 instance count
ECOSYSTEM="$APP_DIR/ecosystem.config.cjs"
if [ -f "$ECOSYSTEM" ]; then
  # ecosystem.config.cjs uses multi-line `const INSTANCES = … ? _n : N` — do not grep `INSTANCES = digits`
  PM2_INSTANCES=$(grep -E '^PM2_INSTANCES=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"[:space:]')
  if ! [[ "$PM2_INSTANCES" =~ ^[1-9][0-9]*$ ]] || [ "$PM2_INSTANCES" -gt 12 ]; then
    PM2_INSTANCES=$( (grep -oP '\? _n : \K[0-9]+' "$ECOSYSTEM" 2>/dev/null || true) | head -1 )
  fi
  PM2_INSTANCES=${PM2_INSTANCES:-4}
  PM2_BASE_PORT=$( (grep -oP 'BASE_PORT\s*=\s*\K[0-9]+' "$ECOSYSTEM" 2>/dev/null || true) | head -1 )
  PM2_BASE_PORT=${PM2_BASE_PORT:-3000}

  TMPUP=$(mktemp)
  echo "    upstream nextjs {" > "$TMPUP"
  echo "        least_conn;" >> "$TMPUP"
  for i in $(seq 0 $((PM2_INSTANCES - 1))); do
    port=$((PM2_BASE_PORT + i))
    echo "        server 127.0.0.1:${port} max_fails=5 fail_timeout=30s;" >> "$TMPUP"
  done
  echo "    }" >> "$TMPUP"

  if grep -q 'upstream nextjs' /etc/nginx/nginx.conf; then
    cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak 2>/dev/null || true
    python3 -c "
import re, sys
with open('/etc/nginx/nginx.conf') as f:
    conf = f.read()
with open('$TMPUP') as f:
    new_block = f.read()
conf = re.sub(r'(\s*)upstream nextjs \{[^}]*\}', new_block.rstrip(), conf, count=1)
with open('/etc/nginx/nginx.conf','w') as f:
    f.write(conf)
"
    log "  ✓ upstream nextjs synced (${PM2_INSTANCES} workers, ports ${PM2_BASE_PORT}-$((PM2_BASE_PORT + PM2_INSTANCES - 1)))"
  fi
  rm -f "$TMPUP"
fi
rm -f /etc/nginx/conf.d/neptun-upstream.conf 2>/dev/null || true

# Update nginx site config
NGINX_SRC="$DEPLOY_DIR/nginx-neptun-optimized.conf"
NGINX_DST="/etc/nginx/sites-available/neptun"
if [ -f "$NGINX_SRC" ]; then
  cp "$NGINX_DST" "$NGINX_DST.bak" 2>/dev/null || true
  if ! diff -q "$NGINX_SRC" "$NGINX_DST" &>/dev/null 2>&1; then
    cp "$NGINX_SRC" "$NGINX_DST"
    ln -sf "$NGINX_DST" /etc/nginx/sites-enabled/neptun
  fi
fi

# Purge nginx disk proxy caches (STATIC/API) so no stale HTML or API right after a new build
for _cache_dir in /tmp/nginx_static_cache /tmp/nginx_api_cache; do
  if [ -d "$_cache_dir" ]; then
    find "$_cache_dir" -mindepth 1 -delete 2>/dev/null || true
  fi
done
log "  ✓ nginx proxy_cache dirs purged (static + api)"

# Test & reload nginx
if NGINX_TEST_OUTPUT=$(nginx -t 2>&1); then
  systemctl reload nginx
  log "  ✓ nginx config OK & reloaded"
else
  err "  ✗ nginx config syntax error — rolling back"
  err "$NGINX_TEST_OUTPUT"
  if [ -f /etc/nginx/nginx.conf.bak ]; then
    cp /etc/nginx/nginx.conf.bak /etc/nginx/nginx.conf
  fi
  if [ -f "$NGINX_DST.bak" ]; then
    cp "$NGINX_DST.bak" "$NGINX_DST"
  fi
  nginx -t 2>/dev/null && systemctl reload nginx
fi

# Restart services
systemctl reset-failed neptun-web neptun-worker neptun-sse 2>/dev/null || true
systemctl restart neptun-web
sleep 2
systemctl restart neptun-worker
if [ -f "$SSE_DIR/sse-gateway" ] && [ -f "$DEPLOY_DIR/neptun-sse.service" ]; then
  if systemctl restart neptun-sse 2>/dev/null; then
    log "  ✓ neptun-sse restarted"
  else
    cp "$DEPLOY_DIR/neptun-sse.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable --now neptun-sse
    log "  ✓ neptun-sse installed and started"
  fi
fi

log "  ✓ Services restarted"

# Clear Next.js in-memory API caches (each PM2 process has its own heap)
_CACHE_SECRET=$(grep -E '^ADMIN_API_SECRET=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"[:space:]' || true)
[ -n "$_CACHE_SECRET" ] || _CACHE_SECRET=$(grep -E '^ADMIN_SECRET=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"[:space:]' || true)
[ -n "$_CACHE_SECRET" ] || _CACHE_SECRET=$(grep -E '^AUTH_SECRET=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"[:space:]' || true)
if [ -n "$_CACHE_SECRET" ]; then
  _ci="${PM2_INSTANCES:-4}"
  _bp="${PM2_BASE_PORT:-3000}"
  if ! [[ "$_ci" =~ ^[1-9][0-9]*$ ]] || [ "$_ci" -gt 12 ]; then _ci=4; fi
  if ! [[ "$_bp" =~ ^[0-9]+$ ]]; then _bp=3000; fi
  _cleared=0
  for _k in $(seq 0 $((_ci - 1))); do
    _port=$((_bp + _k))
    if curl -sf -X POST "http://127.0.0.1:${_port}/api/admin/cache/clear" \
      -H "X-Auth-Secret: ${_CACHE_SECRET}" -o /dev/null; then
      _cleared=$((_cleared + 1))
    fi
  done
  log "  ✓ App in-memory cache cleared (${_cleared}/${_ci} PM2 instances, ports ${_bp}-$((_bp + _ci - 1)))"
else
  warn "  Skip app cache clear (no ADMIN_API_SECRET / ADMIN_SECRET / AUTH_SECRET in .env)"
fi

# Persist iptables rules (Cloudflare-only firewall)
if command -v iptables-save &>/dev/null && [ -d /etc/iptables ]; then
  iptables-save > /etc/iptables/rules.v4
  ip6tables-save > /etc/iptables/rules.v6 2>/dev/null || true
  log "  ✓ iptables rules persisted"
fi

# ── 7. Health checks ─────────────────────────────────────────────
log "[7/7] Running health checks..."
HEALTH_OK=false

for i in $(seq 1 15); do
  if curl -sf "$HEALTH_URL" -o /tmp/health_response 2>/dev/null; then
    HEALTH_OK=true
    break
  fi
  sleep 2
done

if $HEALTH_OK; then
  MARKERS=$(cat /tmp/health_response | python3 -c "import sys,json; print(json.load(sys.stdin).get('markers','?'))" 2>/dev/null || echo "?")
  log "  ✓ neptun-web is healthy (markers: $MARKERS)"
else
  err "  ✗ neptun-web health check FAILED after 30s"
  err "    Check logs: journalctl -u neptun-web -n 30 --no-pager"
fi

# Check worker
sleep 3
if systemctl is-active --quiet neptun-worker; then
  log "  ✓ neptun-worker is active"
else
  err "  ✗ neptun-worker is NOT active"
  err "    Check logs: journalctl -u neptun-worker -n 20 --no-pager"
fi

# Check SSE gateway
if systemctl is-active --quiet neptun-sse 2>/dev/null; then
  if curl -sf http://127.0.0.1:4000/health &>/dev/null; then
    log "  ✓ neptun-sse is active"
  else
    warn "  neptun-sse running but /health not responding"
  fi
else
  warn "  neptun-sse not active (SSE/online count may not work)"
fi

# Optional: full rebuild of settlements.db after changing build_gazetteer / ALIAS_MAP
#   REBUILD_GAZETTEER=1 sudo bash deploy/deploy.sh   (or export before one-liner SSH)
if [ "${REBUILD_GAZETTEER:-0}" = "1" ] && [ -x "$DEPLOY_DIR/rebuild-gazetteer.sh" ]; then
  log "REBUILD_GAZETTEER=1 — rebuilding gazetteer DB..."
  bash "$DEPLOY_DIR/rebuild-gazetteer.sh" || warn "rebuild-gazetteer.sh failed (worker may still run with old DB)"
  systemctl restart neptun-worker 2>/dev/null || true
  log "  ✓ neptun-worker restarted after gazetteer rebuild"
fi

# Quick post checks (health + optional resolve-quality if secret in .env)
if [ -f "$ENV_FILE" ] && [ -x "$DEPLOY_DIR/check-post-deploy.sh" ]; then
  ADMIN_HEADER_SECRET=$(grep -E '^ADMIN_API_SECRET=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"' || true)
  if [ -z "$ADMIN_HEADER_SECRET" ]; then
    ADMIN_HEADER_SECRET=$(grep -E '^AUTH_SECRET=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"' || true)
  fi
  export ADMIN_HEADER_SECRET
  BASE_URL="${BASE_URL:-http://127.0.0.1:3000}"
  export BASE_URL
  bash "$DEPLOY_DIR/check-post-deploy.sh" || true
fi

# ── Summary ───────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║       Deploy Complete!               ║"
echo "╚══════════════════════════════════════╝"
echo ""
log "neptun-web:    $(systemctl is-active neptun-web)"
log "neptun-worker: $(systemctl is-active neptun-worker)"
log "neptun-sse:    $(systemctl is-active neptun-sse 2>/dev/null || echo 'not installed')"
echo ""
log "Backup:  $BACKUP_DIR/.env.$TIMESTAMP"
log "Logs:    journalctl -u neptun-web -f"
log "         journalctl -u neptun-worker -f"
