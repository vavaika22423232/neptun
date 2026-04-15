#!/usr/bin/env bash
# Печатает блок upstream nextjs для вставки в nginx (порты = PM2_INSTANCES).
# На сервере:  source /home/neptun/app/.env 2>/dev/null; bash /home/neptun/app/deploy/print-nginx-upstream.sh
set -euo pipefail

N="${PM2_INSTANCES:-4}"
if ! [[ "$N" =~ ^([1-9]|1[0-2])$ ]]; then
  echo "Invalid PM2_INSTANCES=$N (use 1–12)" >&2
  exit 1
fi

BASE="${PM2_BASE_PORT:-3000}"
echo "# PM2_INSTANCES=$N BASE_PORT=$BASE — вставить в http { } или include из snippets"
echo "upstream nextjs {"
echo "    least_conn;"
for ((i=0; i<N; i++)); do
  PORT=$((BASE + i))
  echo "    server 127.0.0.1:${PORT} max_fails=5 fail_timeout=30s;"
done
echo "}"
