# Neptun — Ukrainian Air Alert Tracking

Real-time tracking of air threats over Ukraine based on Telegram channel data.

## Project Structure

```
neptun/
├── nextjs-app/          # Next.js web application (frontend + API)
│   ├── src/             # React pages, components, API routes
│   ├── public/          # Static assets (icons, map data, SVGs)
│   └── worker/          # Python Telegram worker
│       ├── worker.py    # Telethon client → /api/ingest
│       ├── core/        # Parser v2 (entity extraction)
│       └── geo/         # Geocoding (Nominatim, OpenCage, Visicom)
├── neptun_alarm_app/    # Flutter mobile app (iOS + Android)
│   └── lib/             # Dart source
└── deploy/              # VPS deployment scripts & configs
    ├── setup-vps.sh     # Initial server setup
    ├── deploy.sh        # Code deploy script
    ├── nginx-neptun.conf
    ├── neptun-web.service
    └── neptun-worker.service
```

## Deployment (VPS)

The app runs on a Ukrainian VPS (Ubuntu 24.04):

- **Web**: Next.js standalone → nginx reverse proxy → https://neptun.in.ua
- **Worker**: Python Telethon client monitoring 14 Ukrainian Telegram channels (kpszsu, povitryanatrivogaaa, UkraineAlarmSignal, etc.)
- **Services**: systemd (`neptun-web`, `neptun-worker`)

```bash
# Deploy latest code (from local machine)
scp -r nextjs-app/src nextjs-app/public nextjs-app/package.json root@173.242.55.166:/home/neptun/app/nextjs-app/
ssh root@173.242.55.166 "cd /home/neptun/app/nextjs-app && npm run build && cp -r public .next/standalone/public && cp -r .next/static .next/standalone/.next/static && systemctl restart neptun-web neptun-worker"
```

## Environment Variables

```
NODE_ENV=production
PORT=3000
HOSTNAME=0.0.0.0
DATA_DIR=/data
AUTH_SECRET=...     # Base secret (ingest + admin header + JWT if dedicated vars unset)
INGEST_SECRET=...   # Optional — worker → /api/ingest only; leak ≠ admin API (falls back to AUTH_SECRET)
ADMIN_API_SECRET=... # Optional — X-Auth-Secret for admin JSON + moderators (falls back to AUTH_SECRET)
JWT_SECRET=...      # Optional — chat/device JWT signing (falls back to AUTH_SECRET)
DISABLE_INGEST_BRUTE_GUARD=1  # Optional dev only — disables Redis lockout after bad ingest secrets
ADMIN_PASSWORD=... # Required — no fallback (admin login)
ALARM_API_KEY=...
ALARMS_API_KEY=...
ADMIN_PASSWORD=...
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_SESSION=...
INGEST_URL=http://127.0.0.1:3000/api/ingest
FIREBASE_CREDENTIALS=...
OPENCAGE_API_KEY=...
VISICOM_API_KEY=...
GROQ_API_KEY=...       # optional: trajectory AI uses Groq (llama-3.3-70b) when set; else OpenAI
GROQ_TRAJECTORY_MODEL=llama-3.3-70b-versatile  # optional override

# In-app purchase verification (optional, secure by default = deny if not set)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_PLAY_PACKAGE_NAME=com.neptunalarm.neptun_alarm_app
APPLE_SHARED_SECRET=... # iOS: from App Store Connect → In-App Purchases
```

### Flutter: API base URL

For staging or custom API:

```bash
flutter build apk --dart-define=API_BASE_URL=https://staging.neptun.in.ua
```

### Worker: geo unit tests

From `nextjs-app/worker`:

```bash
python3 -m unittest tests.test_geo_rules -v
```

### API: ingest body size

`/api/ingest`, `/api/ingest/batch`, and ingest `PATCH` reject requests whose `Content-Length` exceeds **768 KiB** (`413`) to limit accidental or abusive huge JSON payloads.
