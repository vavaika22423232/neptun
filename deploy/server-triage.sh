#!/usr/bin/env bash
# Запускать НА СЕРВЕРЕ (VPS), не на Mac.
# Сборка: bash deploy/server-triage.sh   или   sudo bash /home/neptun/app/deploy/server-triage.sh
set -euo pipefail

echo "═══════════════════════════════════════════════════════════════"
echo " Neptun server triage — $(date -Is)"
echo "═══════════════════════════════════════════════════════════════"

echo ""
echo "── Load / CPU ──"
uptime || true
(command -v nproc >/dev/null && echo "vCPU: $(nproc)") || true

echo ""
echo "── Memory ──"
free -h 2>/dev/null || true

echo ""
echo "── PM2 (neptun) ──"
if command -v pm2 >/dev/null; then
  sudo -u neptun env PM2_HOME=/home/neptun/.pm2 pm2 list 2>/dev/null || pm2 list 2>/dev/null || true
else
  echo "pm2 not in PATH (try: sudo -u neptun bash -lc 'pm2 list')"
fi

echo ""
echo "── Listeners 127.0.0.1:3000–3007 ──"
if command -v ss >/dev/null; then
  ss -tlnp 2>/dev/null | grep -E '127\.0\.0\.1:300[0-7]\s' || echo "(none matched)"
else
  netstat -tlnp 2>/dev/null | grep -E ':300[0-7]' || true
fi

echo ""
echo "── Nginx: upstream nextjs (snippet) ──"
if [ -d /etc/nginx ]; then
  sudo grep -R "upstream nextjs" -A 15 /etc/nginx 2>/dev/null | head -40 || echo "(not found)"
else
  echo "(no /etc/nginx)"
fi

echo ""
echo "── Last nginx error log (30 lines) ──"
if [ -r /var/log/nginx/error.log ]; then
  tail -30 /var/log/nginx/error.log
elif command -v sudo >/dev/null; then
  sudo tail -30 /var/log/nginx/error.log 2>/dev/null || true
else
  echo "(cannot read error.log)"
fi

echo ""
echo "── systemd neptun-web (last 15 journal lines) ──"
journalctl -u neptun-web -n 15 --no-pager 2>/dev/null || true

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " Дальше (после деплоя с новым ecosystem + nginx upstream):"
echo "   sudo nginx -t && sudo systemctl reload nginx"
echo "   sudo systemctl restart neptun-web   # или: sudo -u neptun pm2 reload neptun"
echo " Проверка: curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/api/health"
echo " Расширенная диагностика 502: bash /home/neptun/app/deploy/diagnose-502.sh"
echo "═══════════════════════════════════════════════════════════════"
