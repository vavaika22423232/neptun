# Neptun - Ukrainian Air Alert Tracking

Real-time tracking of air threats over Ukraine based on Telegram channel data.

## Architecture

```
app_new.py          # Flask application entry point
config.py           # Configuration management
├── api/            # REST API blueprints
├── services/       # Business logic
│   ├── geocoding/  # SmartGeocoder with Ukrainian location support
│   ├── processing/ # Message pipeline
│   ├── telegram/   # Telegram integration
│   └── tracks/     # Track storage
├── domain/         # Domain models
├── data/           # Static data (settlements, coordinates)
├── static/         # Frontend assets
├── templates/      # HTML templates
└── utils/          # Utilities
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app_new.py

# Production (Render)
gunicorn app_new:app --workers 1 --worker-class gevent
```

## Environment Variables

```
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_SESSION=...
OPENCAGE_API_KEY=...  # Optional
```

## API Endpoints

- `GET /data` - Get current tracks
- `GET /api/alarms/all` - Get alarm status
- `GET /health` - Health check

## Flutter App

Mobile app located in `neptun_alarm_app/` directory.

```bash
cd neptun_alarm_app
flutter pub get
flutter run
```
