# Shared configuration and utilities for routes
# This module contains shared state that needs to be imported by multiple route modules

import os
import json
import threading
import time
import pytz
from datetime import datetime
from functools import lru_cache
from collections import defaultdict

# =============================================================================
# PERSISTENT DATA DIRECTORY
# =============================================================================
# Render persistent storage: /opt/render/project/src/.data
PERSISTENT_DATA_DIR = os.environ.get('PERSISTENT_DATA_DIR', '/opt/render/project/src/.data')

# Ensure directory exists
if PERSISTENT_DATA_DIR and not os.path.exists(PERSISTENT_DATA_DIR):
    try:
        os.makedirs(PERSISTENT_DATA_DIR, exist_ok=True)
    except:
        PERSISTENT_DATA_DIR = None

# =============================================================================
# FILE PATHS
# =============================================================================
def get_data_path(filename):
    """Get path to data file, using persistent storage if available."""
    if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR):
        return os.path.join(PERSISTENT_DATA_DIR, filename)
    return filename

MESSAGES_FILE = get_data_path('messages.json')
COMMERCIAL_SUBSCRIPTIONS_FILE = get_data_path('commercial_subscriptions.json')
CHAT_MESSAGES_FILE = get_data_path('chat_messages.json')
CHAT_NICKNAMES_FILE = get_data_path('chat_nicknames.json')
CHAT_BANNED_USERS_FILE = get_data_path('chat_banned_users.json')
CHAT_MODERATORS_FILE = get_data_path('chat_moderators.json')
DEVICES_FILE = get_data_path('devices.json')
BLOCKED_IDS_FILE = get_data_path('blocked_ids.json')

# =============================================================================
# API CONFIGURATION
# =============================================================================
ALARM_API_KEY = '57fe8a39:7698ad50f0f15d502b280a83019bab25'
ALARM_API_BASE = 'https://api.ukrainealarm.com/api/v3'

# WayForPay configuration  
WAYFORPAY_MERCHANT_ACCOUNT = os.getenv('WAYFORPAY_MERCHANT_ACCOUNT', 'neptun_in_ua')
WAYFORPAY_MERCHANT_SECRET = os.getenv('WAYFORPAY_MERCHANT_SECRET', '')
WAYFORPAY_DOMAIN = 'neptun.in.ua'
WAYFORPAY_ENABLED = bool(WAYFORPAY_MERCHANT_SECRET)

# Monobank Acquiring
MONOBANK_TOKEN = os.getenv('MONOBANK_TOKEN', '')
MONOBANK_ENABLED = bool(MONOBANK_TOKEN)

# Admin credentials
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'change_me_in_production')

# Chat moderator secret
MODERATOR_SECRET = '99446626'

# =============================================================================
# SHARED STATE - Caching
# =============================================================================
class ResponseCache:
    """Thread-safe in-memory cache for API responses with TTL."""
    def __init__(self, default_ttl: int = 30):
        self._cache: dict = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str):
        with self._lock:
            if key in self._cache:
                data, expires_at = self._cache[key]
                if time.time() < expires_at:
                    self.hits += 1
                    return data
                del self._cache[key]
            self.misses += 1
            return None
    
    def set(self, key: str, data, ttl: int = None):
        with self._lock:
            expires_at = time.time() + (ttl or self.default_ttl)
            self._cache[key] = (data, expires_at)
    
    def clear_expired(self):
        with self._lock:
            now = time.time()
            expired_keys = [k for k, (_, exp) in self._cache.items() if now >= exp]
            for k in expired_keys:
                del self._cache[k]
            return len(expired_keys)
    
    def stats(self) -> dict:
        with self._lock:
            total = self.hits + self.misses
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': f"{(self.hits / total * 100):.1f}%" if total > 0 else "0%",
                'cached_items': len(self._cache)
            }

RESPONSE_CACHE = ResponseCache(default_ttl=30)

# =============================================================================
# RATE LIMITING
# =============================================================================
request_counts = defaultdict(list)
VALID_PLATFORMS = {'web', 'android', 'ios'}
PRESENCE_RATE_WINDOW = 30
PRESENCE_RATE_LIMIT = 3

# =============================================================================
# DISTRICT TO OBLAST MAPPING
# =============================================================================
DISTRICT_TO_OBLAST = {
    # Дніпропетровська
    "Синельниківський район": "Дніпропетровська область",
    "Новомосковський район": "Дніпропетровська область",
    "Дніпровський район": "Дніпропетровська область",
    "Криворізький район": "Дніпропетровська область",
    "Кам'янський район": "Дніпропетровська область",
    "Нікопольський район": "Дніпропетровська область",
    "Павлоградський район": "Дніпропетровська область",
    # Харківська
    "Куп'янський район": "Харківська область",
    "Ізюмський район": "Харківська область",
    "Чугуївський район": "Харківська область",
    "Харківський район": "Харківська область",
    "Богодухівський район": "Харківська область",
    "Красноградський район": "Харківська область",
    "Лозівський район": "Харківська область",
    # Сумська
    "Сумський район": "Сумська область",
    "Конотопський район": "Сумська область",
    "Шосткинський район": "Сумська область",
    "Охтирський район": "Сумська область",
    # Запорізька
    "Запорізький район": "Запорізька область",
    "Мелітопольський район": "Запорізька область",
    "Бердянський район": "Запорізька область",
    "Пологівський район": "Запорізька область",
    "Василівський район": "Запорізька область",
    # Add more as needed...
}

# =============================================================================
# REGION TOPIC MAPPING FOR FCM
# =============================================================================
REGION_TOPIC_MAP = {
    'Київ': 'region_kyiv_city',
    'Київська область': 'region_kyivska',
    'Дніпропетровська область': 'region_dnipropetrovska',
    'Харківська область': 'region_kharkivska',
    'Одеська область': 'region_odeska',
    'Львівська область': 'region_lvivska',
    'Донецька область': 'region_donetska',
    'Запорізька область': 'region_zaporizka',
    'Вінницька область': 'region_vinnytska',
    'Житомирська область': 'region_zhytomyrska',
    'Черкаська область': 'region_cherkaska',
    'Чернігівська область': 'region_chernihivska',
    'Полтавська область': 'region_poltavska',
    'Сумська область': 'region_sumska',
    'Миколаївська область': 'region_mykolaivska',
    'Херсонська область': 'region_khersonska',
    'Кіровоградська область': 'region_kirovohradska',
    'Хмельницька область': 'region_khmelnytska',
    'Рівненська область': 'region_rivnenska',
    'Волинська область': 'region_volynska',
    'Тернопільська область': 'region_ternopilska',
    'Івано-Франківська область': 'region_ivano_frankivska',
    'Закарпатська область': 'region_zakarpatska',
    'Чернівецька область': 'region_chernivetska',
    'Луганська область': 'region_luhanska',
}

# =============================================================================
# KYIV TIMEZONE
# =============================================================================
KYIV_TZ = pytz.timezone('Europe/Kiev')

def get_kyiv_now():
    """Get current time in Kyiv timezone."""
    return datetime.now(KYIV_TZ)

# =============================================================================
# UKRAINE ADDRESSES DATABASE (for coordinates lookup)
# =============================================================================
UKRAINE_ADDRESSES_DB = {
    'Київ': {'lat': 50.4501, 'lon': 30.5234},
    'Дніпро': {'lat': 48.4647, 'lon': 35.0462},
    'Харків': {'lat': 49.9935, 'lon': 36.2304},
    'Одеса': {'lat': 46.4825, 'lon': 30.7233},
    'Львів': {'lat': 49.8397, 'lon': 24.0297},
    'Запоріжжя': {'lat': 47.8388, 'lon': 35.1396},
    'Вінниця': {'lat': 49.2331, 'lon': 28.4682},
    'Полтава': {'lat': 49.5883, 'lon': 34.5514},
    'Чернігів': {'lat': 51.4982, 'lon': 31.2893},
    'Суми': {'lat': 50.9077, 'lon': 34.7981},
    'Миколаїв': {'lat': 46.9750, 'lon': 31.9946},
    'Херсон': {'lat': 46.6354, 'lon': 32.6169},
    'Кропивницький': {'lat': 48.5079, 'lon': 32.2623},
    'Хмельницький': {'lat': 49.4228, 'lon': 26.9871},
    'Рівне': {'lat': 50.6199, 'lon': 26.2516},
    'Луцьк': {'lat': 50.7593, 'lon': 25.3424},
    'Тернопіль': {'lat': 49.5535, 'lon': 25.5948},
    'Івано-Франківськ': {'lat': 48.9226, 'lon': 24.7111},
    'Ужгород': {'lat': 48.6208, 'lon': 22.2879},
    'Чернівці': {'lat': 48.2921, 'lon': 25.9358},
    'Черкаси': {'lat': 49.4444, 'lon': 32.0598},
    'Житомир': {'lat': 50.2547, 'lon': 28.6587},
}

# =============================================================================
# CLOUDFLARE IP DETECTION
# =============================================================================
def get_real_ip():
    """Get real client IP, supporting Cloudflare proxy."""
    from flask import request
    # Cloudflare specific headers
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        return cf_ip
    # Standard proxy headers
    x_forwarded = request.headers.get('X-Forwarded-For')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    x_real_ip = request.headers.get('X-Real-IP')
    if x_real_ip:
        return x_real_ip
    return request.remote_addr or 'unknown'
