/**
 * PM2 Ecosystem Configuration — Neptun Web Cluster
 *
 * Workers: INSTANCES штук на портах BASE_PORT, BASE_PORT+1, …
 * nginx upstream `nextjs` должен перечислять те же порты (см. deploy/nginx-upstream-nextjs.conf).
 *
 * Zero-downtime deploy: `pm2 reload neptun`
 * - PM2 restarts workers one-by-one, waiting for each to be ready
 * - nginx routes traffic to healthy workers during the reload
 * - SSE connections on restarting workers reconnect to remaining workers
 *
 * Usage:
 *   pm2 start ecosystem.config.cjs     # first time
 *   pm2 reload neptun                  # zero-downtime restart
 *   pm2 list                           # check status
 *   pm2 logs neptun                    # tail logs
 */

const BASE_PORT = 3000;
// Число воркеров: PM2_INSTANCES в .env (1–12). systemd MemoryMax для neptun-web має витримати N × heap.
// nginx upstream: deploy/print-nginx-upstream.sh
const _n = parseInt(process.env.PM2_INSTANCES ?? '', 10);
const INSTANCES =
  Number.isFinite(_n) && _n >= 1 && _n <= 12 ? _n : 4;

module.exports = {
  apps: [{
    name: 'neptun',
    script: 'server.js',
    node_args: '--max-old-space-size=1400',
    cwd: '/home/neptun/app/.next/standalone',

    instances: INSTANCES,
    exec_mode: 'cluster',

    // Each instance gets PORT = 3000 + instance_id
    increment_var: 'PORT',
    env: {
      PORT: BASE_PORT,
      NODE_ENV: 'production',
      // Hostname binding — only accept from localhost (nginx)
      HOSTNAME: '127.0.0.1',
      // AUTH_SECRET, ADMIN_PASSWORD — from .env via systemd EnvironmentFile
      DATA_DIR: '/data',
    },

    // Zero-downtime: wait 5s after fork before considering ready
    wait_ready: false,
    listen_timeout: 8000,
    kill_timeout: 5000,

    // Graceful reload
    shutdown_with_message: true,

    // Auto-restart on crash
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s',
    restart_delay: 2000,
    exp_backoff_restart_delay: 3000,

    // Memory limit per worker (например 3 × 1.3G ≈ 4G + запас в systemd MemoryMax)
    max_memory_restart: '1300M',

    // Logs
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    error_file: '/home/neptun/logs/neptun-error.log',
    out_file: '/home/neptun/logs/neptun-out.log',
    merge_logs: true,
    log_type: 'json',

    // Source map support
    source_map_support: false,

    // Don't watch files (we use manual reload)
    watch: false,
  }],
};
