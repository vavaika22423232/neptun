#!/usr/bin/env bash
set -euo pipefail

# GMhost deploy helper: sync files to your hosting and set basic permissions.
# Usage:
#   ./deploy_gmhost.sh <REMOTE_USER> <REMOTE_HOST> [REMOTE_PORT] [REMOTE_DIR]
# Example:
#   ./deploy_gmhost.sh mylogin mydomain.gmhost.com.ua 22 ~/public_html

REMOTE_USER="${1:-}"
REMOTE_HOST="${2:-}"
REMOTE_PORT="${3:-22}"
REMOTE_DIR="${4:-~/public_html}"

if [[ -z "$REMOTE_USER" || -z "$REMOTE_HOST" ]]; then
  echo "Usage: $0 <REMOTE_USER> <REMOTE_HOST> [REMOTE_PORT] [REMOTE_DIR]"
  exit 1
fi

command -v rsync >/dev/null || { echo "rsync is required"; exit 1; }
command -v ssh >/dev/null   || { echo "ssh is required"; exit 1; }

echo "➡️  Deploying to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR} (port ${REMOTE_PORT})"

# Create remote dir if missing
ssh -p "${REMOTE_PORT}" "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_DIR}"

# Sync workspace (exclude caches and VCS)
rsync -avz --delete \
  --exclude '.git' \
  --exclude '.DS_Store' \
  --exclude 'venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'logs/*' \
  ./ "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"

# Set permissions and make sure basics exist
ssh -p "${REMOTE_PORT}" "${REMOTE_USER}@${REMOTE_HOST}" bash -lc "\
  cd ${REMOTE_DIR} && \
  mkdir -p logs tmp data && \
  chmod 755 index.py app.py 2>/dev/null || true && \
  chmod 644 .htaccess 2>/dev/null || true && \
  [[ -f .env ]] && chmod 600 .env || true && \
  python3 --version && pip3 --version && echo 'Remote Python detected.'
"

echo "✅ Sync complete."
echo ""
echo "Next steps on GMhost (run over SSH):"
cat <<'EONEXT'
  # 1) Install dependencies (once)
  chmod +x install_gmhost.sh && ./install_gmhost.sh

  # 2) Ensure .env is present and filled (TELEGRAM_* keys, TELEGRAM_SESSION)
  cp env_example.txt .env   # if not created yet
  nano .env

  # 3) Test fetcher once
  python3 telegram_fetcher_v2.py

  # 4) Add cron to refresh data every 2 minutes
  crontab -e
  # Insert line (adjust path to your public_html):
  */2 * * * * cd ~/public_html && /usr/bin/python3 telegram_fetcher_v2.py >> logs/fetch.log 2>&1

  # 5) Open your site and check /data
  #    https://your-domain/data?timeRange=40
EONEXT

echo "ℹ️  If you use a non-standard SSH port, it is already respected (port ${REMOTE_PORT})."
