# Neptun — Ukrainian Air Alert Tracking

Real-time tracking of air threats over Ukraine based on Telegram channel data.

## Project Structure

```text
render2/
├── nextjs-app/          # Next.js web app, API routes, chat, admin UI
│   └── worker/          # Python Telegram worker, parser, geo, LLM analysis
├── neptun_alarm_app/    # Flutter mobile app
├── deploy/              # VPS deploy, nginx, systemd, diagnostics
├── docs/                # Data-flow and runbook docs
├── infra/photon/        # Photon geocoder Docker/import setup
├── tools/geo/           # One-off OSM/Overpass utilities
├── ops/snapshots/       # Local operational snapshots, not app code
├── sse-gateway/         # Optional Go SSE gateway
└── designpack/          # TailAdmin source used for style sync
```

Map/API data flow is documented in [`docs/NEPTUN_DATA_FLOW.md`](docs/NEPTUN_DATA_FLOW.md). Public marker publication rules live in [`nextjs-app/src/lib/marker-publication.ts`](nextjs-app/src/lib/marker-publication.ts).

## Common Commands

```bash
cd nextjs-app
npm ci
npm run dev
npm run lint
npm run test:domain
```

Worker tests:

```bash
cd nextjs-app/worker
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Deploy validation:

```bash
make deploy-validate
bash deploy/deploy-from-mac.sh
```

## Environment Variables

```bash
NODE_ENV=production
PORT=3000
HOSTNAME=0.0.0.0
DATA_DIR=/data

AUTH_SECRET=...       # Base fallback secret
INGEST_SECRET=...     # Worker -> /api/ingest; falls back to AUTH_SECRET
ADMIN_API_SECRET=...  # X-Auth-Secret for admin JSON/moderator tools
ADMIN_SECRET=...      # Deprecated alias for ADMIN_API_SECRET
JWT_SECRET=...        # Chat/device JWT signing; falls back to AUTH_SECRET
ADMIN_PASSWORD=...    # Admin login password or bcrypt hash

TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_SESSION=...
INGEST_URL=http://127.0.0.1:3000/api/ingest

ALARM_API_KEY=...
ALARMS_API_KEY=...
OPENCAGE_API_KEY=...
VISICOM_API_KEY=...
GROQ_API_KEY=...
GROQ_TRAJECTORY_MODEL=llama-3.3-70b-versatile

GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_PLAY_PACKAGE_NAME=com.neptunalarm.neptun_alarm_app
APPLE_SHARED_SECRET=...
```

## Operational Notes

- VPS deployment and nginx guidance: [`deploy/README.md`](deploy/README.md).
- Photon setup: run commands from [`infra/photon`](infra/photon).
- Legacy parser/push smoke scripts live in [`nextjs-app/worker/manual_checks`](nextjs-app/worker/manual_checks); CI only runs maintained unit tests in [`nextjs-app/worker/tests`](nextjs-app/worker/tests).
- `/api/ingest`, `/api/ingest/batch`, and ingest `PATCH` reject bodies over **768 KiB**.
