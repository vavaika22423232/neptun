"""
Neptun Alarm - Configuration Management
All environment variables and settings in one place
"""
import os
from datetime import timedelta

# === Application Settings ===
APP_NAME = "Neptun Alarm"
APP_VERSION = "2.0.0"
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# === Server Settings ===
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

# === Timezone ===
TIMEZONE = 'Europe/Kyiv'

# === Telegram Settings ===
TELEGRAM_API_ID = int(os.getenv('API_ID', 0))
TELEGRAM_API_HASH = os.getenv('API_HASH', '')
TELEGRAM_SESSION = os.getenv('SESSION_STRING', '')
TELEGRAM_PHONE = os.getenv('PHONE_NUMBER', '')

# Default channels to monitor
DEFAULT_CHANNELS = [
    'nikolaev_bpla',
    'dsns_telegram',
    'operativnoZSU',
    'ukrainealarmcommunity',
    'air_alert_ua',
    'povaborona',
    'klobelyuk',
    'kyivoda1808'
]

# === Firebase Settings ===
FIREBASE_CREDENTIALS = os.getenv('FIREBASE_CREDENTIALS', '')
FCM_ENABLED = bool(FIREBASE_CREDENTIALS)

# === Geocoding API Keys ===
OPENCAGE_API_KEY = os.getenv('OPENCAGE_API_KEY', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# === Cache Settings ===
OPENCAGE_TTL = 86400 * 7  # 7 days
MESSAGE_TTL = 3600 * 6     # 6 hours
ALARM_TTL = 3600 * 2       # 2 hours
NOTIFICATION_CACHE_TTL = 300  # 5 minutes

# === Rate Limits ===
MAX_MESSAGES = 500
MAX_MARKERS = 1000
FETCH_INTERVAL = 30  # seconds

# === Git Auto-Sync Settings ===
GIT_AUTO_COMMIT = os.getenv('GIT_AUTO_COMMIT', 'false').lower() == 'true'
GIT_REPO_SLUG = os.getenv('GIT_REPO_SLUG', '')
GIT_SYNC_TOKEN = os.getenv('GIT_SYNC_TOKEN', '')

# === Database Files ===
MESSAGES_FILE = 'messages.json'
CHAT_MESSAGES_FILE = 'chat_messages.json'
DEVICES_FILE = 'devices.json'
VISITS_DB = 'visits.db'
ALARMS_DB = 'alarms.db'

# === Static Paths ===
STATIC_DIR = 'static'
TEMPLATES_DIR = 'templates'

# === Feature Flags ===
SPACY_ENABLED = True
NOMINATIM_ENABLED = True
GROQ_ENABLED = bool(GROQ_API_KEY)
GEMINI_ENABLED = bool(GEMINI_API_KEY)
