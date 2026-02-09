#!/bin/bash
set -euo pipefail

# ╔══════════════════════════════════════════════════════════════╗
# ║  Neptun Deploy Script — pull, build, restart                ║
# ║  Run as: sudo -u neptun bash /home/neptun/app/deploy/deploy.sh
# ╚══════════════════════════════════════════════════════════════╝

APP_DIR="/home/neptun/app"
NEXTJS_DIR="$APP_DIR/nextjs-app"
WORKER_DIR="$NEXTJS_DIR/worker"

echo "═══ Neptun Deploy ═══"
echo "$(date '+%Y-%m-%d %H:%M:%S')"

# 1. Pull latest code
echo "[1/4] Pulling latest code..."
cd "$APP_DIR"
git pull origin main

# 2. Build Next.js
echo "[2/4] Building Next.js..."
cd "$NEXTJS_DIR"
npm install --production=false
npm run build
cp -r public .next/standalone/public
cp -r .next/static .next/standalone/.next/static

# 3. Update worker deps
echo "[3/4] Updating worker dependencies..."
cd "$WORKER_DIR"
source venv/bin/activate
pip install -r requirements.txt --quiet
deactivate

# 4. Restart services (needs sudo)
echo "[4/4] Restarting services..."
sudo systemctl restart neptun-web
sudo systemctl restart neptun-worker

echo ""
echo "═══ Deploy complete! ═══"
echo "Check status:"
echo "  sudo systemctl status neptun-web"
echo "  sudo systemctl status neptun-worker"
echo "  sudo journalctl -u neptun-web -f"
echo "  sudo journalctl -u neptun-worker -f"
