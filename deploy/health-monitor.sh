#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║  Neptun Health Monitor — runs via cron every 2 minutes          ║
# ║                                                                  ║
# ║  Checks:                                                        ║
# ║    1. HTTPS endpoint responds with status=ok                    ║
# ║    2. Redis is alive                                             ║
# ║    3. Worker process is active                                   ║
# ║    4. PM2 cluster has expected number of workers                 ║
# ║    5. Memory usage is within limits                              ║
# ║                                                                  ║
# ║  Alerts via Telegram bot on failure, auto-resolves on recovery.  ║
# ║                                                                  ║
# ║  Install:                                                        ║
# ║    crontab -e                                                    ║
# ║    */2 * * * * /home/neptun/app/deploy/health-monitor.sh         ║
# ╚══════════════════════════════════════════════════════════════════╝

set -u

# ── Config ────────────────────────────────────────────────────────
HEALTH_URL="http://127.0.0.1:3000/api/health"
HEALTH_URL_HTTPS="https://neptun.in.ua/api/health"
STATE_FILE="/tmp/neptun_health_state"
ALERT_COOLDOWN=300  # don't re-alert within 5 minutes
EXPECTED_PM2_WORKERS=3

# Telegram Bot (set these in /home/neptun/app/.env or here)
source /home/neptun/app/.env 2>/dev/null || true
TELEGRAM_BOT_TOKEN="${MONITOR_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${MONITOR_CHAT_ID:-}"

# ── Functions ─────────────────────────────────────────────────────

send_telegram() {
    local message="$1"
    if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
        echo "[MONITOR] No Telegram config — logging only: $message"
        return
    fi
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${message}" \
        -d "parse_mode=HTML" \
        -d "disable_notification=false" \
        > /dev/null 2>&1
}

get_last_alert_time() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

should_alert() {
    local last_alert
    last_alert=$(get_last_alert_time)
    local now
    now=$(date +%s)
    local diff=$((now - last_alert))
    [ "$diff" -gt "$ALERT_COOLDOWN" ]
}

mark_alerted() {
    date +%s > "$STATE_FILE"
}

mark_resolved() {
    rm -f "$STATE_FILE" 2>/dev/null
}

# ── Checks ────────────────────────────────────────────────────────

errors=()

# 1. HTTP health check (local)
health_response=$(curl -sf --connect-timeout 5 --max-time 10 "$HEALTH_URL" 2>/dev/null)
if [ $? -ne 0 ] || [ -z "$health_response" ]; then
    errors+=("❌ Web service not responding on port 3000")
else
    status=$(echo "$health_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)
    if [ "$status" != "ok" ]; then
        errors+=("⚠️ Health status: $status")
    fi
    
    # Check Redis
    redis_status=$(echo "$health_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('redis',''))" 2>/dev/null)
    if [ "$redis_status" = "disconnected" ]; then
        errors+=("❌ Redis disconnected")
    fi
    
    # Check memory
    rss=$(echo "$health_response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('memory',{}).get('rss',0))" 2>/dev/null)
    if [ "$rss" -gt 2000 ] 2>/dev/null; then
        errors+=("⚠️ High memory: ${rss}MB RSS")
    fi
fi

# 2. Redis ping
redis_pong=$(redis-cli ping 2>/dev/null)
if [ "$redis_pong" != "PONG" ]; then
    errors+=("❌ Redis not responding")
fi

# 3. Worker process
if ! systemctl is-active --quiet neptun-worker; then
    errors+=("❌ Worker (neptun-worker) is DOWN")
fi

# 4. PM2 workers (if PM2 is installed)
if command -v pm2 &>/dev/null; then
    online_count=$(pm2 jlist 2>/dev/null | python3 -c "
import sys,json
try:
    apps=json.load(sys.stdin)
    print(sum(1 for a in apps if a.get('pm2_env',{}).get('status')=='online'))
except:
    print(0)
" 2>/dev/null)
    
    if [ "$online_count" -lt "$EXPECTED_PM2_WORKERS" ] 2>/dev/null; then
        errors+=("⚠️ PM2: only ${online_count}/${EXPECTED_PM2_WORKERS} workers online")
    fi
fi

# 5. Disk space
disk_usage=$(df / --output=pcent 2>/dev/null | tail -1 | tr -d ' %')
if [ "$disk_usage" -gt 90 ] 2>/dev/null; then
    errors+=("⚠️ Disk usage: ${disk_usage}%")
fi

# ── Alert Logic ───────────────────────────────────────────────────

RESTART_STATE="/tmp/neptun_restart_state"

auto_restart() {
    local now
    now=$(date +%s)
    local last_restart=0
    [ -f "$RESTART_STATE" ] && last_restart=$(cat "$RESTART_STATE" 2>/dev/null || echo 0)
    local diff=$((now - last_restart))
    # No more than one auto-restart per 3 minutes
    if [ "$diff" -lt 180 ]; then
        return
    fi
    echo "$now" > "$RESTART_STATE"

    if ! systemctl is-active --quiet neptun-web; then
        systemctl restart neptun-web 2>/dev/null
        errors+=("🔄 Auto-restarted neptun-web")
    else
        # PM2 may have lost workers — reload
        su - neptun -c "pm2 reload neptun --update-env" 2>/dev/null || true
        errors+=("🔄 PM2 reload triggered")
    fi

    if ! systemctl is-active --quiet neptun-worker; then
        systemctl restart neptun-worker 2>/dev/null
        errors+=("🔄 Auto-restarted neptun-worker")
    fi

    if ! systemctl is-active --quiet neptun-sse 2>/dev/null; then
        systemctl restart neptun-sse 2>/dev/null
        errors+=("🔄 Auto-restarted neptun-sse")
    fi
}

if [ ${#errors[@]} -gt 0 ]; then
    auto_restart

    error_list=""
    for err in "${errors[@]}"; do
        error_list="${error_list}\n${err}"
    done
    
    if should_alert; then
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        message="🚨 <b>Neptun Alert</b> — ${timestamp}${error_list}"
        send_telegram "$message"
        mark_alerted
        echo "[$(date)] ALERT: ${errors[*]}"
    fi
else
    if [ -f "$STATE_FILE" ]; then
        timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        message="✅ <b>Neptun Recovered</b> — ${timestamp}\nAll systems operational"
        send_telegram "$message"
        mark_resolved
        echo "[$(date)] RECOVERED"
    fi
fi
