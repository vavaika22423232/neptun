#!/bin/bash
set -euo pipefail

# ╔══════════════════════════════════════════════════════════════╗
# ║  Neptun VPS Setup Script — Ukraine.com.ua VPS 2G           ║
# ║  Ubuntu 24.04 LTS, IP: 173.242.55.120                      ║
# ║  Run as root: bash setup-vps.sh                             ║
# ╚══════════════════════════════════════════════════════════════╝

echo "═══════════════════════════════════════"
echo "  Neptun VPS Setup — Starting..."
echo "═══════════════════════════════════════"

# ── 1. System Update ──────────────────────────────────────────
echo "[1/8] Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
apt update -qq && apt upgrade -y -qq

# ── 2. Install System Dependencies ───────────────────────────
echo "[2/8] Installing system dependencies..."
apt install -y -qq \
  curl wget git build-essential \
  nginx certbot python3-certbot-nginx \
  python3 python3-pip python3-venv \
  ufw fail2ban htop

# ── 3. Install Node.js 20 LTS ────────────────────────────────
echo "[3/8] Installing Node.js 20 LTS..."
if ! command -v node &>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt install -y -qq nodejs
fi
echo "  Node.js $(node -v), npm $(npm -v)"

# ── 4. Create deploy user ────────────────────────────────────
echo "[4/8] Creating deploy user..."
if ! id -u neptun &>/dev/null; then
  useradd -m -s /bin/bash neptun
  mkdir -p /home/neptun/.ssh
  cp /root/.ssh/authorized_keys /home/neptun/.ssh/ 2>/dev/null || true
  chown -R neptun:neptun /home/neptun/.ssh
  chmod 700 /home/neptun/.ssh
  echo "  User 'neptun' created"
else
  echo "  User 'neptun' already exists"
fi

# ── 5. Create data directory ─────────────────────────────────
echo "[5/8] Creating data directory..."
mkdir -p /data
chown neptun:neptun /data
echo "  /data directory ready"

# ── 6. Clone repository ──────────────────────────────────────
echo "[6/8] Cloning repository..."
APP_DIR="/home/neptun/app"
if [ ! -d "$APP_DIR" ]; then
  sudo -u neptun git clone https://github.com/vavaika22423232/neptun.git "$APP_DIR"
else
  echo "  Repository already cloned, pulling latest..."
  cd "$APP_DIR" && sudo -u neptun git pull origin main
fi

# ── 7. Build Next.js app ─────────────────────────────────────
echo "[7/8] Building Next.js application..."
cd "$APP_DIR/nextjs-app"
sudo -u neptun npm install
sudo -u neptun npm run build
sudo -u neptun cp -r public .next/standalone/public
sudo -u neptun cp -r .next/static .next/standalone/.next/static
echo "  Next.js build complete"

# ── 8. Setup Python worker ───────────────────────────────────
echo "[8/8] Setting up Python worker..."
WORKER_DIR="$APP_DIR/nextjs-app/worker"
cd "$WORKER_DIR"
sudo -u neptun python3 -m venv venv
sudo -u neptun bash -c "source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"
echo "  Python worker ready"

# ── 9. Configure Firewall ────────────────────────────────────
echo "Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
echo "  Firewall configured (SSH + HTTP + HTTPS)"

# ── 10. Install systemd services ─────────────────────────────
echo "Installing systemd services..."
DEPLOY_DIR="$APP_DIR/deploy"

cp "$DEPLOY_DIR/neptun-web.service" /etc/systemd/system/
cp "$DEPLOY_DIR/neptun-worker.service" /etc/systemd/system/
systemctl daemon-reload

# ── 11. Install nginx config ─────────────────────────────────
echo "Installing nginx config..."
cp "$DEPLOY_DIR/nginx-neptun.conf" /etc/nginx/sites-available/neptun
ln -sf /etc/nginx/sites-available/neptun /etc/nginx/sites-enabled/neptun
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
echo "  Nginx configured"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Setup complete!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Next steps:"
echo "  1. Edit environment variables:"
echo "     nano /home/neptun/app/deploy/.env"
echo ""
echo "  2. Start services:"
echo "     systemctl start neptun-web"
echo "     systemctl start neptun-worker"
echo "     systemctl enable neptun-web neptun-worker"
echo ""
echo "  3. Point DNS A-record for neptun.in.ua → 173.242.55.120"
echo ""
echo "  4. Get SSL certificate:"
echo "     certbot --nginx -d neptun.in.ua -d www.neptun.in.ua"
echo ""
echo "  5. Deploy updates:"
echo "     sudo -u neptun bash /home/neptun/app/deploy/deploy.sh"
echo ""
