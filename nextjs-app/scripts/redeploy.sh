#!/bin/bash
# Canonical deployment script for Neptun Iron Stability

set -e # Exit on error

APP_DIR="/home/neptun/app"
LOG_DIR="/home/neptun/logs"

echo "--- REDEPLOY STARTING (Iron Stability) ---"
date

# 1. Build in an isolated temporary directory
echo "Building in temporary environment..."
BUILD_DIR="/home/neptun/build-tmp"
rm -rf $BUILD_DIR
# Copy source code (excluding bloated logs and old backup directories)
rsync -a --exclude 'node_modules' --exclude 'node_modules.old' --exclude '.next' --exclude '.next.old' $APP_DIR/ $BUILD_DIR/
cd $BUILD_DIR

echo "Installing dependencies & Building Next.js..."
npm install
npm run build

echo "Performing atomic swap (Zero-Downtime)..."
# Swap node_modules
rm -rf $APP_DIR/node_modules.old
mv $APP_DIR/node_modules $APP_DIR/node_modules.old 2>/dev/null || true
mv $BUILD_DIR/node_modules $APP_DIR/node_modules

# Swap .next
rm -rf $APP_DIR/.next.old
mv $APP_DIR/.next $APP_DIR/.next.old 2>/dev/null || true
mv $BUILD_DIR/.next $APP_DIR/.next

# Clean up
cd $APP_DIR
rm -rf $BUILD_DIR

# 2. Permissions fix (Nginx now serves from .next/standalone/public/)
echo "Applying permissions (neptun:neptun)..."
chown -R neptun:neptun $APP_DIR
mkdir -p $LOG_DIR
chown -R neptun:neptun $LOG_DIR

# 3. Atomic Restart
echo "Restarting services..."
# Zero-downtime reload for web cluster, regular restart for worker
sudo -u neptun PM2_HOME=/home/neptun/.pm2 pm2 reload neptun || sudo -u neptun PM2_HOME=/home/neptun/.pm2 pm2 restart neptun
systemctl restart neptun-worker
sudo -u neptun PM2_HOME=/home/neptun/.pm2 pm2 list

echo "--- REDEPLOY COMPLETED SUCCESSFULLY ---"
