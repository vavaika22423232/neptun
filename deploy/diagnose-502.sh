#!/usr/bin/env bash
# Neptun — диагностика 502 (nginx → upstream Node/PM2). Запускать на VPS.
#   bash /home/neptun/app/deploy/diagnose-502.sh
#   bash /home/neptun/app/deploy/diagnose-502.sh --recover   # перезапуск neptun-web, если /api/health не отвечает
set -uo pipefail

APP_DIR="${APP_DIR:-/home/neptun/app}"
RECOVER=false
for a in "$@"; do
  case "$a" in
    --recover) RECOVER=true ;;
  esac
done

pm2_cmd() {
  if id neptun &>/dev/null && sudo -u neptun env PM2_HOME=/home/neptun/.pm2 pm2 list &>/dev/null; then
    sudo -u neptun env PM2_HOME=/home/neptun/.pm2 "$@"
  elif command -v pm2 >/dev/null; then
    "$@"
  else
    echo "(pm2 недоступен)"
    return 1
  fi
}

nginx_tail() {
  if [ -r /var/log/nginx/error.log ]; then
    tail -n "$1" /var/log/nginx/error.log
  elif command -v sudo >/dev/null; then
    sudo tail -n "$1" /var/log/nginx/error.log 2>/dev/null || true
  else
    echo "(нет доступа к /var/log/nginx/error.log)"
  fi
}

echo "═══════════════════════════════════════════════════════════════"
echo " Neptun 502 diagnostics — $(date -Is)"
echo "═══════════════════════════════════════════════════════════════"

echo ""
echo "── Nginx error.log (последние 200 строк; фильтр upstream/refused/502) ──"
nginx_tail 200 | tail -200
echo ""
echo "── Совпадения: connect refused / upstream / 502 / timed out ──"
if ! nginx_tail 500 | grep -E 'connect\(\) failed|upstream|502|timed out|no live upstreams' | tail -40; then
  echo "(совпадений нет в последних 500 строках или нет доступа к логу)"
fi

echo ""
echo "── PM2 (neptun) ──"
pm2_cmd pm2 list 2>/dev/null || true

echo ""
echo "── PM2 neptun — последние строки логов ──"
pm2_cmd pm2 logs neptun --lines 80 --nostream 2>/dev/null || true

echo ""
echo "── Слушатели 127.0.0.1:3000–3007 ──"
if command -v ss >/dev/null; then
  ss -tlnp 2>/dev/null | grep -E '127\.0\.0\.1:300[0-7]\s' || echo "(нет совпадений)"
else
  netstat -tlnp 2>/dev/null | grep -E ':300[0-7]' || true
fi

echo ""
echo "── Ожидаемый upstream (из .env + print-nginx-upstream.sh) ──"
if [ -f "$APP_DIR/.env" ]; then
  # shellcheck disable=SC1090
  set -a && source "$APP_DIR/.env" 2>/dev/null && set +a || true
fi
if [ -x "$APP_DIR/deploy/print-nginx-upstream.sh" ]; then
  bash "$APP_DIR/deploy/print-nginx-upstream.sh"
else
  echo "(нет $APP_DIR/deploy/print-nginx-upstream.sh)"
fi

echo ""
echo "── Фактический upstream nextjs в /etc/nginx ──"
if [ -d /etc/nginx ]; then
  sudo grep -R "upstream nextjs" -A 20 /etc/nginx 2>/dev/null | head -50 || echo "(блок upstream nextjs не найден — возможен proxy_pass только на :3000)"
else
  echo "(нет /etc/nginx)"
fi

echo ""
echo "── curl /api/health на портах 3000–3007 (локально) ──"
for p in 3000 3001 3002 3003 3004 3005 3006 3007; do
  code="000"
  if hc=$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 "http://127.0.0.1:${p}/api/health" 2>/dev/null); then
    code="$hc"
  fi
  echo "  :${p} → HTTP ${code}"
done

echo ""
echo "── systemd neptun-web (последние 25 строк журнала) ──"
journalctl -u neptun-web -n 25 --no-pager 2>/dev/null || true

echo ""
echo "── Память / диск ──"
free -h 2>/dev/null || true
df -h / /data 2>/dev/null | head -5 || df -h / | head -3

echo ""
echo "═══════════════════════════════════════════════════════════════"
if $RECOVER; then
  echo " Режим --recover: проверка http://127.0.0.1:3000/api/health"
  if curl -sf --connect-timeout 5 --max-time 10 "http://127.0.0.1:3000/api/health" >/dev/null; then
    echo " Health OK — перезапуск не требуется."
  else
    echo " Health FAIL — systemctl restart neptun-web"
    systemctl restart neptun-web
    sleep 3
    curl -sS -o /dev/null -w " После рестарта: HTTP %{http_code}\n" --connect-timeout 5 "http://127.0.0.1:3000/api/health" || true
  fi
else
  echo " Если upstream недоступен: sudo systemctl restart neptun-web"
  echo " Или: sudo -u neptun env PM2_HOME=/home/neptun/.pm2 pm2 reload neptun --update-env"
  echo " После смены upstream: sudo nginx -t && sudo systemctl reload nginx"
  echo " Повторная диагностика с авто-рестартом: bash $APP_DIR/deploy/diagnose-502.sh --recover"
fi
echo "═══════════════════════════════════════════════════════════════"
