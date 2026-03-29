#!/bin/bash
# Upload Google Play verification key to server (run once)
# Usage: bash deploy/upload-play-key.sh [path-to-key.json]
#
# Default: ~/Downloads/dron-alerts-9090f78f6648.json

set -euo pipefail

SERVER="root@173.242.55.166"
REMOTE_KEYS="/home/neptun/keys"
REMOTE_KEY="$REMOTE_KEYS/play-purchase-verifier.json"

KEY_PATH="${1:-$HOME/Downloads/dron-alerts-9090f78f6648.json}"

if [ ! -f "$KEY_PATH" ]; then
  echo "Key file not found: $KEY_PATH"
  echo "Usage: bash deploy/upload-play-key.sh [path-to-json]"
  exit 1
fi

echo "Uploading Play verification key..."
ssh "$SERVER" "mkdir -p $REMOTE_KEYS && chmod 700 $REMOTE_KEYS"
scp "$KEY_PATH" "$SERVER:$REMOTE_KEY"
ssh "$SERVER" "chown neptun:neptun $REMOTE_KEY && chmod 600 $REMOTE_KEY"
echo "Done. Restarting neptun-web..."
ssh "$SERVER" "systemctl restart neptun-web"
echo "✓ Play purchase verification is now active."
