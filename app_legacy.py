# pyright: reportUnusedVariable=false, reportRedeclaration=false, reportGeneralTypeIssues=false
# pyright: reportUndefinedVariable=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false
# type: ignore
# pylint: disable=all
# fmt: off

# CRITICAL: Monkey-patch stdlib BEFORE any imports when using gunicorn --preload + gevent
# Without this, threading.Lock/RLock are real OS locks that block greenlets instead of yielding
from gevent import monkey as _monkey
_monkey.patch_all()
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                              NEPTUN API v2.0                                 ║
║                    Ukraine Air Threat Tracking System                        ║
║                                                                              ║
║  Production URL: https://neptun.in.ua                                        ║
║  GitHub: https://github.com/vavaika22423232/neptun                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

СТРУКТУРА ФАЙЛА:
════════════════════════════════════════════════════════════════════════════════
[SECTION 1]  IMPORTS & DEPENDENCIES              lines ~1-200
[SECTION 2]  CONFIGURATION & CONSTANTS           lines ~200-900
[SECTION 3]  DOMAIN MODELS & DATA STRUCTURES     lines ~900-1200
[SECTION 4]  STATE REGISTRY (global state)       lines ~1200-1500
[SECTION 5]  UTILITIES & HELPERS                 lines ~1500-3500
[SECTION 6]  SERVICES: Geocoding                 lines ~3500-5000
[SECTION 7]  SERVICES: AI/ML Predictions         lines ~5000-6500
[SECTION 8]  SERVICES: Threat Tracking           lines ~6500-8000
[SECTION 9]  SERVICES: Alarms & Notifications    lines ~8000-10000
[SECTION 10] SERVICES: Telegram Integration      lines ~10000-12000
[SECTION 11] SERVICES: Payments & Email          lines ~12000-14000
[SECTION 12] API ROUTES: Public                  lines ~14000-22000
[SECTION 13] API ROUTES: Admin                   lines ~22000-28000
[SECTION 14] API ROUTES: Internal/Debug          lines ~28000-29500
[SECTION 15] BACKGROUND WORKERS & MONITORS       lines ~29500-30500
[SECTION 16] STARTUP & SHUTDOWN                  lines ~30500-30776
════════════════════════════════════════════════════════════════════════════════

ARCHITECTURE NOTES:
- Monolithic file by design (deployment simplicity on Render)
- All state centralized in STATE registry (see SECTION 4)
- Thread-safe operations via explicit locks
- Caching at multiple levels: ResponseCache, messages, geocode
- AI features: Groq LLM for geocoding disambiguation
"""

# ══════════════════════════════════════════════════════════════════════════════
# [SECTION 1] IMPORTS & DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════

import asyncio
import gc
import hashlib
import json
import logging
import os
import platform
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

import pytz
from flask import Flask, Response, jsonify, redirect, render_template, request, send_from_directory
from telethon import TelegramClient

from core.message_store import DeviceStore, FamilyStore, MessageStore
from threat_analysis import THREAT_BASE_TTL, THREAT_MAX_TTL
import admin_routes
import parser_service
from constants import (
    ALWAYS_STORE_RAW,
    API_HASH,
    API_ID,
    CHANNELS,
    GOOGLE_MAPS_KEY,
    INVALID_CHANNELS,
    LAUNCH_SITES,
    OBLAST_CENTERS,
    OPENCAGE_API_KEY,
    REGION_TOPIC_MAP,
    REGION_TO_OBLAST_ID,
)

# JWT Authentication (optional, graceful fallback if not available)
try:
    from core.jwt_auth import (
        JWT_AVAILABLE,
        create_token,
        create_token_pair,
        verify_token,
        jwt_required,
        jwt_optional,
        moderator_required,
        get_current_user,
        get_token_from_request,
        get_device_id_from_request,
        register_jwt_routes,
    )
    print("INFO: JWT Authentication module loaded")
except ImportError as e:
    JWT_AVAILABLE = False
    print(f"WARNING: JWT Auth not available: {e}")
    # Fallback stubs
    def jwt_required(f): return f
    def jwt_optional(f): return f
    def moderator_required(f): return f
    def get_current_user(): return None
    def register_jwt_routes(_app): pass

# MEMORY OPTIMIZATION: Force garbage collection on startup
gc.collect()

# ============================================================================
# HTTP Session with connection pooling for better performance
# ============================================================================
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def _create_http_session():
    """Create HTTP session with connection pooling and retry logic"""
    session = requests.Session()
    
    # Retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=0.5,
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    
    # Connection pooling (10 connections per host, keep-alive)
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20,
        pool_block=False
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default timeout
    session.timeout = (5, 10)  # (connect timeout, read timeout)
    
    return session

# Global HTTP session
http_requests = _create_http_session()

# ============================================================================
# HIGH-LOAD OPTIMIZATION: Response caching for API endpoints
# ============================================================================
class ResponseCache:
    """Thread-safe in-memory cache for API responses with TTL."""
    def __init__(self, default_ttl: int = 30, max_items: int = 50):
        self._cache: dict = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
        self.max_items = max_items
        self.hits = 0
        self.misses = 0

    def get(self, key: str):
        with self._lock:
            if key in self._cache:
                data, expires_at = self._cache[key]
                if time.time() < expires_at:
                    self.hits += 1
                    return data
                # Expired
                del self._cache[key]
            self.misses += 1
            return None

    def set(self, key: str, data, ttl: int = None):
        with self._lock:
            # MEMORY PROTECTION: Enforce max items limit
            if len(self._cache) >= self.max_items and key not in self._cache:
                # Remove oldest/expired entries first
                self.clear_expired()
                # If still over limit, remove oldest entry
                if len(self._cache) >= self.max_items:
                    oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                    del self._cache[oldest_key]
            expires_at = time.time() + (ttl or self.default_ttl)
            self._cache[key] = (data, expires_at)

    def cleanup(self):
        """Remove expired entries (call periodically)."""
        with self._lock:
            now = time.time()
            expired_keys = [k for k, (_, exp) in self._cache.items() if now >= exp]
            for k in expired_keys:
                del self._cache[k]
            return len(expired_keys)
    
    def clear_expired(self):
        """Alias for cleanup() - removes expired entries."""
        return self.cleanup()
    
    @property
    def cache(self):
        """Direct access to cache dict for size metrics"""
        return self._cache

    def stats(self) -> dict:
        with self._lock:
            total = self.hits + self.misses
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': f"{(self.hits / total * 100):.1f}%" if total > 0 else "0%",
                'cached_items': len(self._cache)
            }

# Global response cache
RESPONSE_CACHE = ResponseCache(default_ttl=30, max_items=20)  # MEMORY: Reduced to 20

# Cached messages - avoid repeated file reads
_MESSAGES_CACHE = {'data': None, 'expires': 0}
_MESSAGES_CACHE_TTL = 30  # 30 second cache for messages (was 5s - too frequent disk I/O under load)

def load_messages_cached():
    """Load messages with caching to reduce disk I/O."""
    global _MESSAGES_CACHE
    now = time.time()
    if _MESSAGES_CACHE['data'] is not None and now < _MESSAGES_CACHE['expires']:
        return _MESSAGES_CACHE['data']
    # Load fresh
    data = MESSAGE_STORE.load()
    log.info(f"[MESSAGES] Loaded {len(data)} messages from {MESSAGE_STORE.path}")
    _MESSAGES_CACHE = {'data': data, 'expires': now + _MESSAGES_CACHE_TTL}
    return data

def invalidate_messages_cache():
    """Call this after saving new messages."""
    global _MESSAGES_CACHE
    _MESSAGES_CACHE = {'data': None, 'expires': 0}

# ============================================================================
# API PROTECTION - Production-grade hardening (prevents 23GB+ traffic spikes)
# ============================================================================
try:
    from api_protection import (
        DEFAULT_PAGE_SIZE,
        MAX_PAGE_SIZE,
        MAX_RESPONSE_SIZE_BYTES,
        MAX_TOTAL_ITEMS,
        check_etag_match,
        check_rate_limit,
        check_response_size,
        compute_etag,
        filter_by_since,
        get_pagination_params,
        get_protection_stats,
        get_protection_status_endpoint,
        get_since_timestamp,
        init_protection,
        paginate_list,
        protected_endpoint,
        rate_limited,
        record_response_size,
        size_guarded,
        supports_since_param,
    )
    API_PROTECTION_ENABLED = True
    print("INFO: API Protection module loaded - production hardening active")
except ImportError as e:
    API_PROTECTION_ENABLED = False
    print(f"WARNING: API Protection module not available: {e}")
    # Fallback stubs
    def protected_endpoint(*_args, **_kwargs):
        def decorator(f): return f
        return decorator
    def rate_limited(f): return f
    def size_guarded(*_args, **_kwargs):
        def decorator(f): return f
        return decorator
    def init_protection(_app): return False
    MAX_RESPONSE_SIZE_BYTES = 5 * 1024 * 1024
    MAX_PAGE_SIZE = 100
    DEFAULT_PAGE_SIZE = 50
    MAX_TOTAL_ITEMS = 500
    # Unused imports from api_protection module when not available
    check_etag_match = None
    check_rate_limit = None
    check_response_size = None
    compute_etag = None
    filter_by_since = None
    get_pagination_params = None
    get_protection_status_endpoint = None
    get_since_timestamp = None
    paginate_list = None
    record_response_size = None
    supports_since_param = None
# ============================================================================

# Import expanded Ukraine addresses database
try:
    from ukraine_addresses_db import UKRAINE_ADDRESSES_DB, UKRAINE_CITIES
    print(f"INFO: Ukraine addresses database loaded: {len(UKRAINE_ADDRESSES_DB)} addresses")
except Exception as e:
    UKRAINE_ADDRESSES_DB = {}
    UKRAINE_CITIES = []
    print(f"WARNING: Ukraine addresses database not available: {e}")

# Import comprehensive Ukrainian settlements database (26000+ entries)
# MEMORY OPTIMIZATION: Load only if enough memory, otherwise use empty dict
# Default to loading the DB (needed for village-level geocoding)
MEMORY_OPTIMIZED = os.environ.get('MEMORY_OPTIMIZED', 'false').lower() == 'true'

if MEMORY_OPTIMIZED:
    # Don't load the huge settlements database - saves ~100MB RAM
    UKRAINE_ALL_SETTLEMENTS = {}
    UKRAINE_SETTLEMENTS_BY_OBLAST = {}
    print("INFO: MEMORY_OPTIMIZED=true - Large settlements database skipped to save RAM")
else:
    try:
        from ukraine_all_settlements import UKRAINE_ALL_SETTLEMENTS, UKRAINE_SETTLEMENTS_BY_OBLAST
        print(f"INFO: Ukraine ALL settlements loaded: {len(UKRAINE_ALL_SETTLEMENTS)} simple + {len(UKRAINE_SETTLEMENTS_BY_OBLAST)} oblast-aware entries")
    except Exception as e:
        UKRAINE_ALL_SETTLEMENTS = {}
        UKRAINE_SETTLEMENTS_BY_OBLAST = {}
        print(f"WARNING: Ukraine ALL settlements not available: {e}")

# RAION_FALLBACK - Coordinates for Ukrainian districts (raions)
# Used when messages mention "X район" format
RAION_FALLBACK = {
    # Харківська область
    'богодухівський': (50.1622, 35.5233),
    'богодухів': (50.1622, 35.5233),
    'валківський': (49.8331, 35.8117),
    'дергачівський': (50.1031, 36.1114),
    'зміївський': (49.6833, 36.3500),
    'золочівський': (50.2833, 35.9833),
    'ізюмський': (49.2092, 37.2614),
    'красноградський': (49.3853, 35.4439),
    'куп\'янський': (49.7144, 37.6186),
    'лозівський': (48.8897, 36.3181),
    'первомайський': (48.6206, 36.2372),
    'харківський': (50.0000, 36.2500),
    'чугуївський': (49.8372, 36.6811),
    # Полтавська область
    'полтавський': (49.5883, 34.5514),
    'кременчуцький': (49.0667, 33.4167),
    'миргородський': (49.9667, 33.6000),
    'лубенський': (50.0167, 32.9833),
    # Дніпропетровська область
    'дніпровський': (48.4647, 35.0462),
    'криворізький': (47.9083, 33.3433),
    'кам\'янський': (48.5083, 34.6153),
    'нікопольський': (47.5692, 34.3978),
    'павлоградський': (48.5333, 35.8667),
    'новомосковський': (48.6333, 35.2167),
    'синельниківський': (48.3167, 35.5000),
    # Київська область
    'білоцерківський': (49.7958, 30.1250),
    'бориспільський': (50.3517, 30.9556),
    'броварський': (50.5106, 30.7978),
    'бучанський': (50.5433, 30.2142),
    'вишгородський': (50.5847, 30.4897),
    'обухівський': (50.1167, 30.6167),
    'фастівський': (50.0767, 29.9186),
    # Херсонська область
    'херсонський': (46.6354, 32.6169),
    'генічеський': (46.1739, 34.8158),
    'каховський': (46.8158, 33.4831),
    'скадовський': (46.1167, 32.9000),
    # Запорізька область
    'запорізький': (47.8388, 35.1396),
    'мелітопольський': (46.8489, 35.3675),
    'бердянський': (46.7586, 36.7853),
    'василівський': (47.4333, 35.2667),
    'пологівський': (47.4833, 36.2667),
    # Донецька область
    'донецький': (48.0159, 37.8029),
    'маріупольський': (47.0958, 37.5494),
    'краматорський': (48.7233, 37.5567),
    'бахмутський': (48.5944, 37.9994),
    'волноваський': (47.6000, 37.4833),
    'покровський': (48.2833, 37.1667),
    # Сумська область
    'сумський': (50.9077, 34.7981),
    'конотопський': (51.2417, 33.2000),
    'охтирський': (50.3097, 34.8789),
    'роменський': (50.7500, 33.4667),
    'шосткинський': (51.8650, 33.4733),
    # Чернігівська область
    'чернігівський': (51.4939, 31.2947),
    'ніжинський': (51.0500, 31.8833),
    'прилуцький': (50.5903, 32.3858),
    'новгород-сіверський': (52.0000, 33.2500),
    # Миколаївська область
    'миколаївський': (46.9750, 31.9946),
    'вознесенський': (47.5667, 31.3333),
    'баштанський': (47.4000, 32.4500),
    'первомайський': (48.0500, 30.8667),
    # Одеська область
    'одеський': (46.4825, 30.7233),
    'білгород-дністровський': (46.1958, 30.3450),
    'ізмаїльський': (45.3500, 28.8333),
    'подільський': (47.7500, 29.5333),
    # Вінницька область
    'вінницький': (49.2331, 28.4682),
    'жмеринський': (49.0333, 28.1167),
    'тульчинський': (48.6833, 28.8500),
    'гайсинський': (48.8000, 29.3833),
    # Житомирська область
    'житомирський': (50.2547, 28.6587),
    'бердичівський': (49.8833, 28.6000),
    'коростенський': (50.9500, 28.6333),
    'новоград-волинський': (50.6000, 27.6167),
    # Кіровоградська область
    'кропивницький': (48.5079, 32.2623),
    'олександрійський': (48.6667, 33.1000),
    'новоукраїнський': (48.3167, 31.5167),
    # Черкаська область
    'черкаський': (49.4444, 32.0597),
    'уманський': (48.7500, 30.2167),
    'золотоніський': (49.6667, 32.0333),
    'звенигородський': (49.0833, 30.9667),
}
print(f"INFO: RAION_FALLBACK loaded: {len(RAION_FALLBACK)} district entries")

# SpaCy integration DISABLED to save memory (~150MB)
# Enable only if server has >1GB RAM
SPACY_AVAILABLE = False
nlp = None
print("INFO: SpaCy DISABLED to save memory")

# Geocoding integration: Visicom (primary) -> OpenCage (fallback)
# Visicom is Ukrainian service, much better for Ukrainian city names with all grammatical cases
_visicom_available = False
_opencage_available = False

try:
    from visicom_geocoder import visicom_geocode as _visicom_geocode
    _visicom_available = True
    print("INFO: Visicom geocoding ENABLED (primary)", flush=True)
except ImportError as e:
    print(f"WARNING: Visicom geocoder not available: {e}", flush=True)
    def _visicom_geocode(_city, _region=None):
        return None

try:
    from opencage_geocoder import geocode as _opencage_geocode, get_cache_stats, cleanup_bad_cache_entries, invalidate_cache_entry
    _opencage_available = True
    print("INFO: OpenCage geocoding ENABLED (fallback)", flush=True)
    # Run cache cleanup on startup
    cleanup_result = cleanup_bad_cache_entries()
    if cleanup_result['removed_count'] > 0:
        print(f"INFO: Cleaned up {cleanup_result['removed_count']} bad geocode cache entries", flush=True)
except ImportError as e:
    print(f"WARNING: OpenCage geocoder not available: {e}", flush=True)
    def _opencage_geocode(_city, _region=None):
        return None
    def get_cache_stats():
        return {}
    def cleanup_bad_cache_entries():
        return {'removed_count': 0, 'kept_count': 0, 'removed_entries': []}
    def invalidate_cache_entry(_city, _region=None):
        return False

GEOCODER_AVAILABLE = _visicom_available or _opencage_available

def opencage_geocode(city, region=None):
    """Unified geocoder: Visicom only (no OpenCage). Used for UAV/threat markers."""
    if not city:
        return None
    if _visicom_available:
        result = _visicom_geocode(city, region)
        if result:
            return result
    return None


# === LEGACY COMPATIBILITY ===
class _OpenCageProxy(dict):
    """Dict-like object that proxies lookups to geocoder."""
    def __getitem__(self, key):
        coords = opencage_geocode(key)
        if coords:
            return coords
        raise KeyError(key)
    
    def __contains__(self, key):
        return opencage_geocode(key) is not None
    
    def get(self, key, default=None):
        coords = opencage_geocode(key)
        return coords if coords else default
    
    def keys(self):
        return []
    def items(self):
        return []
    def values(self):
        return []

CITY_COORDS = _OpenCageProxy()
SETTLEMENTS_INDEX = _OpenCageProxy()

def ensure_city_coords(city_name, region=None, context=None):
    """Simple geocoding function."""
    if not city_name:
        return None
    if not region and context:
        region = _extract_oblast_from_text(context)
    return opencage_geocode(city_name, region)

def ensure_city_coords_with_message_context(city_name, message_text=None):
    """Simple geocoding with region extraction from message text."""
    if not city_name:
        return None
    region = None
    if message_text:
        region = _extract_oblast_from_text(message_text)
    return opencage_geocode(city_name, region)

# GROQ removed - route/trajectory via regex only
GROQ_ENABLED = False
GROQ_API_KEY = ''
groq_client = None

# Stubs for parser_service dependency injection (no longer used)
def extract_trajectory_with_ai(*args, **kwargs):
    return None
def predict_route_with_ai(*args, **kwargs):
    return None

# Context geocoder disabled
CONTEXT_GEOCODER_AVAILABLE = False
def get_context_aware_geocoding(_text):
    return []
nlp = None
SPACY_AVAILABLE = False

try:
    from telethon.errors import (
        AuthKeyDuplicatedError,
        AuthKeyUnregisteredError,
        FloodWaitError,
        SessionPasswordNeededError,
    )
except ImportError:
    class AuthKeyDuplicatedError(Exception):
        pass
    class AuthKeyUnregisteredError(Exception):
        pass
    class FloodWaitError(Exception):
        def __init__(self, seconds=60): self.seconds = seconds
    class SessionPasswordNeededError(Exception):
        pass
import math

from telethon.sessions import StringSession


# ══════════════════════════════════════════════════════════════════════════════
# [SECTION 5] UTILITIES & HELPERS
# ══════════════════════════════════════════════════════════════════════════════

# --- Region ID cache (reduces repeated parsing/lookup work) ---
_REGION_IDS_CACHE: dict[str, dict] = {}
_REGION_IDS_CACHE_TTL = int(os.getenv('REGION_IDS_CACHE_TTL', '1800'))  # 30 min (reduced from 1h)
_REGION_IDS_CACHE_MAX = int(os.getenv('REGION_IDS_CACHE_MAX', '500'))  # Reduced from 3000

_OBLAST_ID_CACHE: dict[str, str | None] = {}
_RF_GEOCODE_CACHE: dict[str, tuple] = {}
_RF_GEOCODE_CACHE_TTL = int(os.getenv('RF_GEOCODE_CACHE_TTL', '86400'))  # 1 day (reduced from 7 days)
_RF_GEOCODE_CACHE_MAX = 200  # MEMORY PROTECTION: Max RF geocode entries

def _geocode_rf_place(place: str) -> tuple | None:
    """Geocode RF place via Nominatim (lightweight, cached)."""
    if not place:
        return None
    key = place.lower().strip()
    cached = _RF_GEOCODE_CACHE.get(key)
    if cached:
        coords, ts = cached
        if time.time() - ts <= _RF_GEOCODE_CACHE_TTL:
            return coords
        else:
            _RF_GEOCODE_CACHE.pop(key, None)  # Remove expired
    
    # MEMORY PROTECTION: Enforce max size
    if len(_RF_GEOCODE_CACHE) >= _RF_GEOCODE_CACHE_MAX:
        # Remove oldest 20% of entries
        sorted_keys = sorted(_RF_GEOCODE_CACHE.keys(), key=lambda k: _RF_GEOCODE_CACHE[k][1])
        for old_key in sorted_keys[:len(_RF_GEOCODE_CACHE) // 5]:
            _RF_GEOCODE_CACHE.pop(old_key, None)

    try:
        query = f"{place}, Russia"
        url = 'https://nominatim.openstreetmap.org/search'
        params = {'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'ru'}
        headers = {'User-Agent': 'neptun-geocoder/1.0'}
        resp = http_requests.get(url, params=params, headers=headers, timeout=4)
        if resp.status_code == 200:
            data = resp.json() or []
            if data:
                lat = float(data[0].get('lat'))
                lon = float(data[0].get('lon'))
                coords = (lat, lon)
                _RF_GEOCODE_CACHE[key] = (coords, time.time())
                return coords
    except Exception:
        pass

    _RF_GEOCODE_CACHE[key] = (None, time.time())
    return None

def _region_ids_cache_get(key: str) -> tuple | None:
    entry = _REGION_IDS_CACHE.get(key)
    if not entry:
        return None
    if time.time() - entry['ts'] > _REGION_IDS_CACHE_TTL:
        _REGION_IDS_CACHE.pop(key, None)
        return None
    return entry['value']

def _region_ids_cache_set(key: str, value: tuple) -> None:
    if len(_REGION_IDS_CACHE) >= _REGION_IDS_CACHE_MAX:
        # Drop oldest 10% to avoid unbounded growth
        cutoff = int(_REGION_IDS_CACHE_MAX * 0.1) or 1
        for old_key in list(_REGION_IDS_CACHE.keys())[:cutoff]:
            _REGION_IDS_CACHE.pop(old_key, None)
    _REGION_IDS_CACHE[key] = {'value': value, 'ts': time.time()}

# --- Raion ID Mapping for precise district filtering ---
# Key cities/places to their raion IDs
# Format: 'keyword': ('oblast_id', 'raion_id')
PLACE_TO_RAION_ID = {
    # Дніпропетровська область (UA-12)
    'дніпро': ('UA-12', 'UA-12-01'),
    'дніпропетровськ': ('UA-12', 'UA-12-01'),
    'днепр': ('UA-12', 'UA-12-01'),
    'днепропетровск': ('UA-12', 'UA-12-01'),
    'підгородне': ('UA-12', 'UA-12-01'),
    'кривий ріг': ('UA-12', 'UA-12-02'),
    'криворіж': ('UA-12', 'UA-12-02'),
    'інгулець': ('UA-12', 'UA-12-02'),
    'кам\'янське': ('UA-12', 'UA-12-03'),
    'камянське': ('UA-12', 'UA-12-03'),
    'нікополь': ('UA-12', 'UA-12-04'),
    'марганець': ('UA-12', 'UA-12-04'),
    'покров': ('UA-12', 'UA-12-04'),
    'павлоград': ('UA-12', 'UA-12-05'),
    'тернівка': ('UA-12', 'UA-12-05'),
    'синельникове': ('UA-12', 'UA-12-06'),
    'васильківка': ('UA-12', 'UA-12-06'),
    'новомосковськ': ('UA-12', 'UA-12-07'),
    'перещепине': ('UA-12', 'UA-12-07'),
    
    # Харківська область (UA-63)
    'харків': ('UA-63', 'UA-63-01'),
    'харьков': ('UA-63', 'UA-63-01'),
    'дергачі': ('UA-63', 'UA-63-01'),
    'мерефа': ('UA-63', 'UA-63-01'),
    'куп\'янськ': ('UA-63', 'UA-63-02'),
    'купянськ': ('UA-63', 'UA-63-02'),
    'великий бурлук': ('UA-63', 'UA-63-02'),
    'ізюм': ('UA-63', 'UA-63-03'),
    'балаклія': ('UA-63', 'UA-63-03'),
    'барвінкове': ('UA-63', 'UA-63-03'),
    'чугуїв': ('UA-63', 'UA-63-04'),
    'вовчанськ': ('UA-63', 'UA-63-04'),
    'печеніги': ('UA-63', 'UA-63-04'),
    'богодухів': ('UA-63', 'UA-63-05'),
    'золочів': ('UA-63', 'UA-63-05'),
    'красноград': ('UA-63', 'UA-63-06'),
    'кегичівка': ('UA-63', 'UA-63-06'),
    'лозова': ('UA-63', 'UA-63-07'),
    'первомайський': ('UA-63', 'UA-63-07'),
    
    # Донецька область (UA-14)
    'краматорськ': ('UA-14', 'UA-14-01'),
    'слов\'янськ': ('UA-14', 'UA-14-01'),
    'словянськ': ('UA-14', 'UA-14-01'),
    'лиман': ('UA-14', 'UA-14-01'),
    'бахмут': ('UA-14', 'UA-14-02'),
    'соледар': ('UA-14', 'UA-14-02'),
    'костянтинівка': ('UA-14', 'UA-14-02'),
    'покровськ': ('UA-14', 'UA-14-03'),
    'мирноград': ('UA-14', 'UA-14-03'),
    'добропілля': ('UA-14', 'UA-14-03'),
    'волноваха': ('UA-14', 'UA-14-04'),
    'маріуполь': ('UA-14', 'UA-14-06'),
    'старобешеве': ('UA-14', 'UA-14-05'),
    'комсомольське': ('UA-14', 'UA-14-05'),
    'тельманове': ('UA-14', 'UA-14-05'),
    'донецьк': ('UA-14', 'UA-14-07'),
    'макіївка': ('UA-14', 'UA-14-07'),
    'ясинувата': ('UA-14', 'UA-14-07'),
    'авдіївка': ('UA-14', 'UA-14-07'),
    'горлівка': ('UA-14', 'UA-14-08'),
    'торецьк': ('UA-14', 'UA-14-08'),
    'дзержинськ': ('UA-14', 'UA-14-08'),
    
    # Запорізька область (UA-23)
    'запоріжжя': ('UA-23', 'UA-23-01'),
    'біленьке': ('UA-23', 'UA-23-01'),
    'беленке': ('UA-23', 'UA-23-01'),
    'беленьке': ('UA-23', 'UA-23-01'),
    'bilenke': ('UA-23', 'UA-23-01'),
    'мелітополь': ('UA-23', 'UA-23-02'),
    'веселе': ('UA-23', 'UA-23-02'),
    'бердянськ': ('UA-23', 'UA-23-03'),
    'приморськ': ('UA-23', 'UA-23-03'),
    'пологи': ('UA-23', 'UA-23-04'),
    'василівка': ('UA-23', 'UA-23-05'),
    'оріхів': ('UA-23', 'UA-23-04'),
    'гуляйполе': ('UA-23', 'UA-23-04'),
    'токмак': ('UA-23', 'UA-23-04'),
    'енергодар': ('UA-23', 'UA-23-05'),
    
    # Херсонська область (UA-65)
    'херсон': ('UA-65', 'UA-65-01'),
    'берислав': ('UA-65', 'UA-65-02'),
    'генічеськ': ('UA-65', 'UA-65-03'),
    'каховка': ('UA-65', 'UA-65-04'),
    'нова каховка': ('UA-65', 'UA-65-04'),
    'скадовськ': ('UA-65', 'UA-65-05'),
    'олешки': ('UA-65', 'UA-65-01'),
    'голая пристань': ('UA-65', 'UA-65-01'),
    'чаплинка': ('UA-65', 'UA-65-05'),
    
    # Одеська область (UA-51)
    'одеса': ('UA-51', 'UA-51-01'),
    'одесса': ('UA-51', 'UA-51-01'),
    'чорноморськ': ('UA-51', 'UA-51-01'),
    'ильичевск': ('UA-51', 'UA-51-01'),
    'южне': ('UA-51', 'UA-51-01'),
    'білгород-дністровський': ('UA-51', 'UA-51-02'),
    'белгород-днестровский': ('UA-51', 'UA-51-02'),
    'затока': ('UA-51', 'UA-51-02'),
    'сергіївка': ('UA-51', 'UA-51-02'),
    'болград': ('UA-51', 'UA-51-03'),
    'арциз': ('UA-51', 'UA-51-03'),
    'тарутине': ('UA-51', 'UA-51-03'),
    'ізмаїл': ('UA-51', 'UA-51-04'),
    'измаил': ('UA-51', 'UA-51-04'),
    'кілія': ('UA-51', 'UA-51-04'),
    'рені': ('UA-51', 'UA-51-04'),
    'подільськ': ('UA-51', 'UA-51-05'),
    'подольск': ('UA-51', 'UA-51-05'),
    'балта': ('UA-51', 'UA-51-05'),
    'березівка': ('UA-51', 'UA-51-06'),
    'роздільна': ('UA-51', 'UA-51-07'),
    'біляївка': ('UA-51', 'UA-51-07'),

    # м. Київ (UA-30) - місто зі спеціальним статусом
    'київ': ('UA-30', ''),  # Київ не має raion_id, тільки oblast_id
    'киев': ('UA-30', ''),

    # Київська область (UA-32)
    'біла церква': ('UA-32', 'UA-32-01'),
    'білацерква': ('UA-32', 'UA-32-01'),
    'бориспіль': ('UA-32', 'UA-32-02'),
    'переяслав': ('UA-32', 'UA-32-02'),
    'бровари': ('UA-32', 'UA-32-03'),
    'броварський': ('UA-32', 'UA-32-03'),
    'буча': ('UA-32', 'UA-32-04'),
    'ірпінь': ('UA-32', 'UA-32-04'),
    'гостомель': ('UA-32', 'UA-32-04'),
    'вишгород': ('UA-32', 'UA-32-05'),
    'славутич': ('UA-32', 'UA-32-05'),
    'обухів': ('UA-32', 'UA-32-06'),
    'українка': ('UA-32', 'UA-32-06'),
    'фастів': ('UA-32', 'UA-32-07'),
    'васильків': ('UA-32', 'UA-32-07'),


    # Львівська область (UA-46)
    'львів': ('UA-46', 'UA-46-01'),
    'львов': ('UA-46', 'UA-46-01'),
    'винники': ('UA-46', 'UA-46-01'),
    'рудно': ('UA-46', 'UA-46-01'),
    'стрий': ('UA-46', 'UA-46-02'),
    'сколе': ('UA-46', 'UA-46-02'),
    'жидачів': ('UA-46', 'UA-46-02'),
    'самбір': ('UA-46', 'UA-46-03'),
    'турка': ('UA-46', 'UA-46-03'),
    'дрогобич': ('UA-46', 'UA-46-04'),
    'трускавець': ('UA-46', 'UA-46-04'),
    'борислав': ('UA-46', 'UA-46-04'),
    'червоноград': ('UA-46', 'UA-46-05'),
    'сокаль': ('UA-46', 'UA-46-05'),
    'яворів': ('UA-46', 'UA-46-06'),
    'новояворівськ': ('UA-46', 'UA-46-06'),
    'золочів': ('UA-46', 'UA-46-07'),
    'броди': ('UA-46', 'UA-46-07'),

    # Миколаївська область (UA-48)
    'миколаїв': ('UA-48', 'UA-48-01'),
    'миколаев': ('UA-48', 'UA-48-01'),
    'очаків': ('UA-48', 'UA-48-01'),
    'очаков': ('UA-48', 'UA-48-01'),
    'баштанка': ('UA-48', 'UA-48-02'),
    'вознесенськ': ('UA-48', 'UA-48-03'),
    'южноукраїнськ': ('UA-48', 'UA-48-03'),
    'первомайськ': ('UA-48', 'UA-48-04'),

    # Полтавська область (UA-53)
    'полтава': ('UA-53', 'UA-53-01'),
    'кременчук': ('UA-53', 'UA-53-02'),
    'горішні плавні': ('UA-53', 'UA-53-02'),
    'комсомольськ': ('UA-53', 'UA-53-02'),
    'лубни': ('UA-53', 'UA-53-03'),
    'миргород': ('UA-53', 'UA-53-04'),
    'гадяч': ('UA-53', 'UA-53-04'),

    # Сумська область (UA-59)
    'суми': ('UA-59', 'UA-59-01'),
    'сумы': ('UA-59', 'UA-59-01'),
    'лебедин': ('UA-59', 'UA-59-01'),
    'конотоп': ('UA-59', 'UA-59-02'),
    'путивль': ('UA-59', 'UA-59-02'),
    'шостка': ('UA-59', 'UA-59-03'),
    'глухів': ('UA-59', 'UA-59-03'),
    'охтирка': ('UA-59', 'UA-59-04'),
    'краснопілля': ('UA-59', 'UA-59-04'),
    'ромни': ('UA-59', 'UA-59-05'),

    # Чернігівська область (UA-74)
    'чернігів': ('UA-74', 'UA-74-01'),
    'чернигов': ('UA-74', 'UA-74-01'),
    'новгород-сіверський': ('UA-74', 'UA-74-02'),
    'ніжин': ('UA-74', 'UA-74-03'),
    'прилуки': ('UA-74', 'UA-74-04'),
    'корюківка': ('UA-74', 'UA-74-05'),
    'мена': ('UA-74', 'UA-74-05'),

    # Черкаська область (UA-71)
    'черкаси': ('UA-71', 'UA-71-01'),
    'черкассы': ('UA-71', 'UA-71-01'),
    'золотоноша': ('UA-71', 'UA-71-02'),
    'умань': ('UA-71', 'UA-71-03'),
    'звенигородка': ('UA-71', 'UA-71-04'),
    'шпола': ('UA-71', 'UA-71-04'),

    # Кіровоградська область (UA-35)
    'кропивницький': ('UA-35', 'UA-35-01'),
    'кіровоград': ('UA-35', 'UA-35-01'),
    'олександрія': ('UA-35', 'UA-35-02'),
    'світловодськ': ('UA-35', 'UA-35-02'),
    'голованівськ': ('UA-35', 'UA-35-03'),
    'новоукраїнка': ('UA-35', 'UA-35-04'),

    # Вінницька область (UA-05)
    'вінниця': ('UA-05', 'UA-05-01'),
    'немирів': ('UA-05', 'UA-05-01'),
    'гайсин': ('UA-05', 'UA-05-02'),
    'бершадь': ('UA-05', 'UA-05-02'),
    'жмеринка': ('UA-05', 'UA-05-03'),
    'козятин': ('UA-05', 'UA-05-03'),
    'могилів-подільський': ('UA-05', 'UA-05-04'),
    'ямпіль': ('UA-05', 'UA-05-04'),
    'тульчин': ('UA-05', 'UA-05-05'),
    'ладижин': ('UA-05', 'UA-05-05'),
    'хмільник': ('UA-05', 'UA-05-06'),

    # Житомирська область (UA-18)
    'житомир': ('UA-18', 'UA-18-01'),
    'коростишів': ('UA-18', 'UA-18-01'),
    'бердичів': ('UA-18', 'UA-18-02'),
    'чуднів': ('UA-18', 'UA-18-02'),
    'коростень': ('UA-18', 'UA-18-03'),
    'овруч': ('UA-18', 'UA-18-03'),
    'звягель': ('UA-18', 'UA-18-04'),
    'новоград-волинський': ('UA-18', 'UA-18-04'),

    # Рівненська область (UA-56)
    'рівне': ('UA-56', 'UA-56-01'),
    'здолбунів': ('UA-56', 'UA-56-01'),
    'дубно': ('UA-56', 'UA-56-02'),
    'радивилів': ('UA-56', 'UA-56-02'),
    'вараш': ('UA-56', 'UA-56-03'),
    'кузнецовськ': ('UA-56', 'UA-56-03'),
    'сарни': ('UA-56', 'UA-56-04'),
    'костопіль': ('UA-56', 'UA-56-04'),

    # Волинська область (UA-07)
    'луцьк': ('UA-07', 'UA-07-01'),
    'ківерці': ('UA-07', 'UA-07-01'),
    'володимир': ('UA-07', 'UA-07-02'),
    'нововолинськ': ('UA-07', 'UA-07-02'),
    'ковель': ('UA-07', 'UA-07-03'),
    'любомль': ('UA-07', 'UA-07-03'),
    'камінь-каширський': ('UA-07', 'UA-07-04'),
    'маневичі': ('UA-07', 'UA-07-04'),

    # Тернопільська область (UA-61)
    'тернопіль': ('UA-61', 'UA-61-01'),
    'зборів': ('UA-61', 'UA-61-01'),
    'чортків': ('UA-61', 'UA-61-02'),
    'заліщики': ('UA-61', 'UA-61-02'),
    'кременець': ('UA-61', 'UA-61-03'),
    'почаїв': ('UA-61', 'UA-61-03'),

    # Хмельницька область (UA-68)
    'хмельницький': ('UA-68', 'UA-68-01'),
    'красилів': ('UA-68', 'UA-68-01'),
    'шепетівка': ('UA-68', 'UA-68-02'),
    'кам\'янець-подільський': ('UA-68', 'UA-68-03'),
    'дунаївці': ('UA-68', 'UA-68-03'),

    # Івано-Франківська область (UA-26)
    'івано-франківськ': ('UA-26', 'UA-26-01'),
    'франківськ': ('UA-26', 'UA-26-01'),
    'калуш': ('UA-26', 'UA-26-02'),
    'долина': ('UA-26', 'UA-26-02'),
    'коломия': ('UA-26', 'UA-26-03'),
    'снятин': ('UA-26', 'UA-26-03'),
    'косів': ('UA-26', 'UA-26-04'),
    'куті': ('UA-26', 'UA-26-04'),
    'надвірна': ('UA-26', 'UA-26-05'),
    'яремче': ('UA-26', 'UA-26-05'),
    'верховина': ('UA-26', 'UA-26-06'),

    # Закарпатська область (UA-21)
    'ужгород': ('UA-21', 'UA-21-01'),
    'перечин': ('UA-21', 'UA-21-01'),
    'мукачево': ('UA-21', 'UA-21-02'),
    'свалява': ('UA-21', 'UA-21-02'),
    'берегово': ('UA-21', 'UA-21-03'),
    'виноградів': ('UA-21', 'UA-21-03'),
    'хуст': ('UA-21', 'UA-21-04'),
    'іршава': ('UA-21', 'UA-21-04'),
    'рахів': ('UA-21', 'UA-21-05'),
    'ясіня': ('UA-21', 'UA-21-05'),
    'тячів': ('UA-21', 'UA-21-06'),
    'солотвино': ('UA-21', 'UA-21-06'),

    # Чернівецька область (UA-77)
    'чернівці': ('UA-77', 'UA-77-01'),
    'вижниця': ('UA-77', 'UA-77-02'),
    'новодністровськ': ('UA-77', 'UA-77-03'),
    'хотин': ('UA-77', 'UA-77-03'),

    # Луганська область (UA-44)
    'луганськ': ('UA-44', 'UA-44-01'),
    'сєвєродонецьк': ('UA-44', 'UA-44-02'),
    'северодонецьк': ('UA-44', 'UA-44-02'),
    'лисичанськ': ('UA-44', 'UA-44-02'),
    'рубіжне': ('UA-44', 'UA-44-02'),
    'алчевськ': ('UA-44', 'UA-44-03'),
    'довжанськ': ('UA-44', 'UA-44-04'),
    'свердловськ': ('UA-44', 'UA-44-04'),
    'ровеньки': ('UA-44', 'UA-44-05'),
    'щастя': ('UA-44', 'UA-44-06'),
    'новоайдар': ('UA-44', 'UA-44-06'),
    'станиця луганська': ('UA-44', 'UA-44-06'),
    'старобільськ': ('UA-44', 'UA-44-07'),
    'сватове': ('UA-44', 'UA-44-08'),
    'кремінна': ('UA-44', 'UA-44-08'),
    'троїцьке': ('UA-44', 'UA-44-08'),
}

def get_region_ids_from_place(place: str, region: str) -> tuple:
    """
    Extract oblast_id and raion_id from place name and region.
    Returns (oblast_id, raion_id) or (None, None) if not found.
    Uses aggressive caching for performance.
    """
    # Fast path: check cache first
    cache_key = f"{(place or '').lower().strip()}|{(region or '').lower().strip()}"
    cached = _region_ids_cache_get(cache_key)
    if cached is not None:
        return cached
    
    # Direct lookup in REGION_TO_OBLAST_ID
    oblast_id = REGION_TO_OBLAST_ID.get(region)
    raion_id = None
    
    if not oblast_id:
        result = (None, None)
        _region_ids_cache_set(cache_key, result)
        return result
    
    # Try to find raion from place
    place_clean = ''
    if place:
        place_lower = place.lower().strip()
        # Remove parenthetical suffixes like "(Дніпропетровська обл.)"
        place_clean = RE_PARENS_STRIP.sub('', place_lower).strip()
        # Remove common prefixes (м., смт, с., місто, селище)
        place_clean = RE_PLACE_PREFIX.sub('', place_clean).strip()
        
        # Check direct match first
        if place_clean in PLACE_TO_RAION_ID:
            found_oblast, found_raion = PLACE_TO_RAION_ID[place_clean]
            if found_oblast == oblast_id:
                raion_id = found_raion
        
        # If no direct match, try partial matching
        if not raion_id:
            for keyword, (kw_oblast, kw_raion) in PLACE_TO_RAION_ID.items():
                if kw_oblast == oblast_id and keyword in place_clean:
                    raion_id = kw_raion
                    break

    # Hybrid: try OpenCage components to improve oblast/raion resolution
    if OPENCAGE_API_KEY and (not oblast_id or not raion_id):
        components = opencage_lookup_components(place_clean or place or '', region)
        if components:
            if not oblast_id:
                state_code = components.get('state_code')
                if isinstance(state_code, str) and state_code.startswith('UA-'):
                    oblast_id = state_code
                else:
                    state_name = components.get('state') or components.get('region')
                    if state_name:
                        oblast_id = _resolve_oblast_id_from_name(state_name)

            if not raion_id:
                # Try to extract raion from OpenCage county/district field
                # OpenCage returns format like "Kharkivskyi district" or "Харківський район"
                county = components.get('county') or components.get('district') or components.get('state_district')
                if county:
                    county_lower = county.lower()
                    # Remove "district", "район", "raion" suffixes
                    county_clean = county_lower.replace(' district', '').replace(' район', '').replace(' raion', '').strip()
                    
                    # Try to map district name to raion ID
                    # Pattern: "kharkivskyi" -> "харківський" -> check in PLACE_TO_RAION_ID
                    for keyword, (kw_oblast, kw_raion) in PLACE_TO_RAION_ID.items():
                        keyword_root = keyword.replace('ський', '').replace('цький', '').strip()
                        if (not oblast_id or kw_oblast == oblast_id) and keyword_root in county_clean:
                            raion_id = kw_raion
                            break
                
                # If still no raion, try settlement name itself
                if not raion_id:
                    settlement = (
                        components.get('city') or components.get('town') or components.get('village') or
                        components.get('hamlet') or components.get('municipality')
                    )
                    settlement_norm = _normalize_admin_name(settlement) if settlement else ''
                    if settlement_norm and settlement_norm in PLACE_TO_RAION_ID:
                        found_oblast, found_raion = PLACE_TO_RAION_ID[settlement_norm]
                        if not oblast_id or found_oblast == oblast_id:
                            raion_id = found_raion
    
    result = (oblast_id, raion_id)
    _region_ids_cache_set(cache_key, result)
    return result


def haversine(coord1, coord2):
    """
    Calculate the great-circle distance between two points on Earth.

    Args:
        coord1: tuple (lat, lng) in degrees
        coord2: tuple (lat, lng) in degrees

    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers

    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c

# Basic minimal subset for Render deployment. Heavy ML parts stripped for now.
# Load secrets from a local hidden .env file (key=value) if present (for local dev),
# then fall back to environment variables (for Render / production).

def _load_local_env(path: str = '.env'):
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip(); v = v.strip().strip('"').strip("'")
                # don't override already exported env vars
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception as e:
        logging.warning(f"Failed to load .env file: {e}")

_load_local_env()

# ══════════════════════════════════════════════════════════════════════════════
# [SECTION 2] CONFIGURATION & CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
# All environment variables and configuration constants.
# Grouped by feature: Telegram, Geocoding, Payments, Firebase, etc.

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

# Suppress noisy HTTP request logs from werkzeug/gunicorn
logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)

# ============= CLOUDFLARE CDN SUPPORT =============
# Cloudflare cache status header
@app.after_request
def add_cloudflare_headers(response):
    # Add headers for Cloudflare caching
    if 'Cache-Control' not in response.headers:
        # Default: no cache for dynamic content
        response.headers['Cache-Control'] = 'no-store'

    # Add Vary header for proper caching
    if 'Vary' not in response.headers:
        response.headers['Vary'] = 'Accept-Encoding'

    return response

# ============= API PROTECTION INITIALIZATION =============
# Initialize production-grade protection BEFORE other middleware
if API_PROTECTION_ENABLED:
    init_protection(app)
    print("INFO: API Protection hooks registered")
# =========================================================

# ============= JWT AUTHENTICATION ROUTES =============
# Register JWT endpoints (/api/auth/token, /api/auth/refresh, etc.)
try:
    register_jwt_routes(app)
    print("INFO: JWT auth routes registered")
except Exception as e:
    print(f"WARNING: Failed to register JWT routes: {e}")
# ====================================================

# ============= PERFORMANCE OPTIMIZATION =============
# Enable gzip compression for faster response times
from flask_compress import Compress

compress = Compress()
compress.init_app(app)

# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED CACHE HEADERS MIDDLEWARE
# ══════════════════════════════════════════════════════════════════════════════
# IMPORTANT: Flask allows only ONE @app.after_request per function name.
# This unified handler combines all caching strategies:
# 1. Static assets (images, fonts, JS/CSS)
# 2. Versioned static files (?v= parameter) 
# 3. API endpoints (no-cache)
# 4. HTML pages
@app.after_request
def add_cache_headers(response):
    """
    Unified cache control for all response types.
    
    Caching strategy:
    - Versioned static (?v=): 1 month, immutable
    - Static images/fonts: 7 days
    - Static JS/CSS: 1 day  
    - API endpoints: no-cache, no-store
    - HTML pages: 5 minutes
    """
    # --- Static files (highest priority) ---
    if request.endpoint == 'static' or request.path.startswith('/static/'):
        # Versioned resources (with ?v= parameter) - cache aggressively
        query_string = request.query_string.decode() if request.query_string else ''
        if 'v=' in query_string:
            response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
            response.headers['Expires'] = (datetime.now() + timedelta(days=30)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        else:
            # Non-versioned static files
            if any(request.path.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.webp']):
                response.cache_control.max_age = 604800  # 7 days
                response.cache_control.public = True
                response.headers['Vary'] = 'Accept-Encoding'
                # Add ETag for better cache validation
                response.headers['ETag'] = f'"{hash(request.path + query_string)}"'
            elif any(request.path.endswith(ext) for ext in ['.js', '.css']):
                response.cache_control.max_age = 86400  # 1 day
                response.cache_control.public = True
            else:
                # Other static files - 1 week default
                response.headers['Cache-Control'] = 'public, max-age=604800, immutable'
                response.headers['Expires'] = (datetime.now() + timedelta(days=7)).strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # --- API endpoints (no caching) ---
    elif request.path.startswith('/api/'):
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True
    
    # --- HTML pages (short cache) ---
    elif request.endpoint == 'index' or request.path == '/' or request.path == '/index.html':
        response.cache_control.max_age = 300  # 5 minutes
        response.cache_control.public = True
    
    return response

# ══════════════════════════════════════════════════════════════════════════════
# [SECTION 11] SERVICES: Payments & Email
# ══════════════════════════════════════════════════════════════════════════════
# Payment integrations (WayForPay, Monobank) and email notifications.
# Used for commercial subscriptions and customer communications.

# --- WayForPay Configuration ---
WAYFORPAY_MERCHANT_ACCOUNT = os.getenv('WAYFORPAY_MERCHANT_ACCOUNT', 'neptun_in_ua')
WAYFORPAY_MERCHANT_SECRET = os.getenv('WAYFORPAY_MERCHANT_SECRET', '')
WAYFORPAY_DOMAIN = 'neptun.in.ua'
WAYFORPAY_ENABLED = bool(WAYFORPAY_MERCHANT_SECRET)

if WAYFORPAY_ENABLED:
    print("INFO: WayForPay payment initialized")
else:
    print("WARNING: WayForPay disabled (missing WAYFORPAY_MERCHANT_SECRET)")

# --- Monobank Acquiring Configuration ---
# For ФОП/ТОВ: 1.4% commission, instant payouts
MONOBANK_TOKEN = os.getenv('MONOBANK_TOKEN', '')
MONOBANK_ENABLED = bool(MONOBANK_TOKEN)

if MONOBANK_ENABLED:
    print("INFO: Monobank Acquiring initialized")
    print("INFO: Commission: 1.4% | Instant payouts | Direct bank integration")
else:
    print("WARNING: Monobank Acquiring disabled (missing X-Token)")
    print("HINT: Register at https://fop.monobank.ua/ with your ФОП/ТОВ")

# --- Email Configuration (Flask-Mail) ---
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@neptun.in.ua')

MAIL_ENABLED = bool(app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD'])

if MAIL_ENABLED:
    try:
        from flask_mail import Mail, Message
        mail = Mail(app)
        print("INFO: Flask-Mail initialized")
    except ImportError:
        MAIL_ENABLED = False
        mail = None
        print("WARNING: Flask-Mail not installed. Run: pip install flask-mail")
    except Exception as e:
        MAIL_ENABLED = False
        mail = None
        print(f"WARNING: Flask-Mail initialization failed: {e}")
else:
    mail = None
    print("WARNING: Email disabled (missing SMTP credentials)")

# Admin credentials
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'change_me_in_production')

# =========================================================

# Firebase Admin initialization
device_store = DeviceStore()
family_store = FamilyStore()
firebase_initialized = False

def init_firebase():
    """Initialize Firebase Admin SDK."""
    global firebase_initialized
    if firebase_initialized:
        return True

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Try to load from environment variable (Render deployment)
        cred_json = os.environ.get('FIREBASE_CREDENTIALS')
        if cred_json:
            import base64
            cred_dict = json.loads(base64.b64decode(cred_json))
            cred = credentials.Certificate(cred_dict)
        else:
            # Try to load from file (local development)
            if os.path.exists('firebase-credentials.json'):
                cred = credentials.Certificate('firebase-credentials.json')
            else:
                print("WARNING: Firebase credentials not found")
                return False

        firebase_admin.initialize_app(cred)
        firebase_initialized = True
        print("INFO: Firebase Admin SDK initialized successfully")
        return True
    except Exception as e:
        print(f"ERROR: Failed to initialize Firebase: {e}")
        return False

# Initialize Firebase on startup
init_firebase()

# ============================================================================
# CLOUDFLARE SUPPORT - Get real client IP behind Cloudflare proxy
# ============================================================================
def get_real_ip():
    """Get real client IP, supporting Cloudflare and other proxies.
    Priority: CF-Connecting-IP > X-Real-IP > X-Forwarded-For > remote_addr
    """
    # Cloudflare sends real IP in CF-Connecting-IP header
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        return cf_ip.strip()
    
    # Some proxies use X-Real-IP
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    
    # Standard proxy header (may contain chain: "client, proxy1, proxy2")
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        # First IP in the chain is the original client
        return forwarded.split(',')[0].strip()
    
    # Fallback to direct connection IP
    return request.remote_addr or 'unknown'

# Shared rate tracking for lightweight bandwidth protection rules
request_counts = defaultdict(list)
_request_counts_max_keys = 500  # MEMORY PROTECTION: Max tracked IPs (reduced from 2000)

def _cleanup_request_counts():
    """Periodically cleanup old request count entries to prevent memory leak."""
    global request_counts
    now = time.time()
    # Remove entries older than 5 minutes
    keys_to_remove = []
    for key, timestamps in list(request_counts.items()):
        # Keep only timestamps from last 5 minutes
        recent = [t for t in timestamps if now - t < 300]
        if recent:
            request_counts[key] = recent
        else:
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del request_counts[key]
    # If still too many keys, remove oldest
    if len(request_counts) > _request_counts_max_keys:
        sorted_keys = sorted(request_counts.keys(), key=lambda k: min(request_counts[k]) if request_counts[k] else 0)
        for key in sorted_keys[:len(request_counts) - _request_counts_max_keys // 2]:
            del request_counts[key]

# Presence counter configuration
VALID_PLATFORMS = {'web', 'android', 'ios'}
PRESENCE_RATE_WINDOW = 30  # seconds
PRESENCE_RATE_LIMIT = 3    # max requests per window per IP

# Scheduler removed - no longer needed for blackout schedules

# BANDWIDTH OPTIMIZATION: Rate limiting to prevent abuse
    # Rate limiting отключен: все пользователи имеют свободный доступ

# BANDWIDTH OPTIMIZATION: gzip compression handled by flask_compress (Compress() above)
# REMOVED manual compress_response — flask_compress already gzips all responses.
# Having both caused DOUBLE compression: flask_compress gzips, then this handler tried
# to gzip again, wasting ~30% CPU on every response.

# ══════════════════════════════════════════════════════════════════════════════
# [SECTION 9] SERVICES: Alarms & Notifications
# ══════════════════════════════════════════════════════════════════════════════
# Ukraine Alarm API integration for air raid alerts.
# - Proxy to ukrainealarm.com API
# - Push notifications via Firebase
# - Alarm state tracking and history

import requests as http_requests
import requests
import traceback

# --- Alarm API Configuration ---
ALARM_API_KEY = os.getenv('ALARM_API_KEY') or os.getenv('ALARMS_API_KEY') or '57fe8a39:7698ad50f0f15d502b280a83019bab25'
ALARM_API_BASE = os.getenv('ALARM_API_BASE', 'https://api.ukrainealarm.com/api/v3')

# Mapping district names to oblast names (for oblast-level coloring)
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
    "Роменський район": "Сумська область",
    # Чернігівська
    "Новгород-Сіверський район": "Чернігівська область",
    "Чернігівський район": "Чернігівська область",
    "Ніжинський район": "Чернігівська область",
    "Прилуцький район": "Чернігівська область",
    "Корюківський район": "Чернігівська область",
    # Донецька
    "Краматорський район": "Донецька область",
    "Бахмутський район": "Донецька область",
    "Покровський район": "Донецька область",
    "Волноваський район": "Донецька область",
    "Кальміуський район": "Донецька область",
    "Маріупольський район": "Донецька область",
    "Донецький район": "Донецька область",
    "Горлівський район": "Донецька область",
    # Запорізька
    "Запорізький район": "Запорізька область",
    "Мелітопольський район": "Запорізька область",
    "Бердянський район": "Запорізька область",
    "Пологівський район": "Запорізька область",
    "Василівський район": "Запорізька область",
    # Луганська
    "Сєвєродонецький район": "Луганська область",
    "Старобільський район": "Луганська область",
    "Сватівський район": "Луганська область",
    "Щастинський район": "Луганська область",
    # Херсонська
    "Херсонський район": "Херсонська область",
    "Бериславський район": "Херсонська область",
    "Генічеський район": "Херсонська область",
    "Каховський район": "Херсонська область",
    "Скадовський район": "Херсонська область",
    # Миколаївська
    "Миколаївський район": "Миколаївська область",
    "Баштанський район": "Миколаївська область",
    "Вознесенський район": "Миколаївська область",
    "Первомайський район": "Миколаївська область",
    # Одеська
    "Одеський район": "Одеська область",
    "Білгород-Дністровський район": "Одеська область",
    "Болградський район": "Одеська область",
    "Ізмаїльський район": "Одеська область",
    "Подільський район": "Одеська область",
    "Березівський район": "Одеська область",
    "Роздільнянський район": "Одеська область",
    # Полтавська
    "Полтавський район": "Полтавська область",
    "Кременчуцький район": "Полтавська область",
    "Лубенський район": "Полтавська область",
    "Миргородський район": "Полтавська область",
    # Київська
    "Білоцерківський район": "Київська область",
    "Бориспільський район": "Київська область",
    "Броварський район": "Київська область",
    "Бучанський район": "Київська область",
    "Вишгородський район": "Київська область",
    "Обухівський район": "Київська область",
    "Фастівський район": "Київська область",
    # Черкаська
    "Черкаський район": "Черкаська область",
    "Золотоніський район": "Черкаська область",
    "Уманський район": "Черкаська область",
    "Звенигородський район": "Черкаська область",
    # Кіровоградська
    "Кропивницький район": "Кіровоградська область",
    "Олександрійський район": "Кіровоградська область",
    "Голованівський район": "Кіровоградська область",
    "Новоукраїнський район": "Кіровоградська область",
    # Вінницька
    "Вінницький район": "Вінницька область",
    "Гайсинський район": "Вінницька область",
    "Жмеринський район": "Вінницька область",
    "Могилів-Подільський район": "Вінницька область",
    "Тульчинський район": "Вінницька область",
    "Хмільницький район": "Вінницька область",
    # Житомирська
    "Житомирський район": "Житомирська область",
    "Бердичівський район": "Житомирська область",
    "Коростенський район": "Житомирська область",
    "Звягельський район": "Житомирська область",
    # Рівненська
    "Рівненський район": "Рівненська область",
    "Дубенський район": "Рівненська область",
    "Вараський район": "Рівненська область",
    "Сарненський район": "Рівненська область",
    # Волинська
    "Луцький район": "Волинська область",
    "Володимирський район": "Волинська область",
    "Ковельський район": "Волинська область",
    "Камінь-Каширський район": "Волинська область",
    # Тернопільська
    "Тернопільський район": "Тернопільська область",
    "Чортківський район": "Тернопільська область",
    "Кременецький район": "Тернопільська область",
    # Хмельницька
    "Хмельницький район": "Хмельницька область",
    "Шепетівський район": "Хмельницька область",
    "Кам'янець-Подільський район": "Хмельницька область",
    # Львівська
    "Львівський район": "Львівська область",
    "Стрийський район": "Львівська область",
    "Самбірський район": "Львівська область",
    "Дрогобицький район": "Львівська область",
    "Червоноградський район": "Львівська область",
    "Яворівський район": "Львівська область",
    "Золочівський район": "Львівська область",
    # Івано-Франківська
    "Івано-Франківський район": "Івано-Франківська область",
    "Калуський район": "Івано-Франківська область",
    "Коломийський район": "Івано-Франківська область",
    "Косівський район": "Івано-Франківська область",
    "Надвірнянський район": "Івано-Франківська область",
    "Верховинський район": "Івано-Франківська область",
    # Закарпатська
    "Ужгородський район": "Закарпатська область",
    "Мукачівський район": "Закарпатська область",
    "Берегівський район": "Закарпатська область",
    "Хустський район": "Закарпатська область",
    "Рахівський район": "Закарпатська область",
    "Тячівський район": "Закарпатська область",
    # Чернівецька
    "Чернівецький район": "Чернівецька область",
    "Вижницький район": "Чернівецька область",
    "Дністровський район": "Чернівецька область",
}

# Cache for alarm API responses
_alarm_cache = {'data': None, 'time': 0}
_alarm_all_cache = {'data': None, 'time': 0, 'etag': None}  # Separate cache for /all endpoint
ALARM_CACHE_TTL = 30  # seconds - serve fresh data
ALARM_CACHE_STALE_TTL = 1800  # 30 minutes - serve stale data if API fails
_alarm_api_failing = False  # Track if API is failing to reduce retries
_alarm_api_fail_time = 0  # When API started failing
_alarm_bg_thread_started = False  # Background alarm fetcher

def _fetch_alarms_from_api():
    """Shared helper: fetch alarms from ukrainealarm API with aggressive retries.
    Returns list of active alerts or None on failure."""
    import hashlib
    for attempt in range(5):
        try:
            timeout = 5 + attempt * 2  # 5, 7, 9, 11, 13 seconds
            response = requests.get(
                f'{ALARM_API_BASE}/alerts',
                headers={'Authorization': ALARM_API_KEY},
                timeout=timeout
            )
            if response.ok:
                data = response.json()
                result = []
                for region in data:
                    if region.get('activeAlerts') and len(region['activeAlerts']) > 0:
                        result.append({
                            'regionId': region.get('regionId'),
                            'regionName': region.get('regionName'),
                            'regionType': region.get('regionType'),
                            'activeAlerts': region.get('activeAlerts')
                        })
                return result
            elif response.status_code == 401:
                print(f"[ALARM] API returned 401 - key may be expired")
                return None
        except RecursionError:
            print(f"Alarm all attempt {attempt+1} failed: maximum recursion depth exceeded")
            traceback.print_exc()
        except Exception as e:
            print(f"[ALARM] Attempt {attempt+1}/5 failed: {e}")
            if attempt < 4:
                import time as _t
                _t.sleep(0.5 * (attempt + 1))  # 0.5, 1.0, 1.5, 2.0s
    return None

def _start_alarm_background_fetcher():
    """Background thread that keeps alarm cache warm by polling API every 25s."""
    global _alarm_bg_thread_started
    if _alarm_bg_thread_started:
        return
    _alarm_bg_thread_started = True

    import hashlib

    def _bg_loop():
        global _alarm_api_failing, _alarm_api_fail_time
        while True:
            try:
                import time as _t
                _t.sleep(25)  # Poll every 25 seconds
                result = _fetch_alarms_from_api()
                now = _t.time()
                if result is not None:
                    _alarm_api_failing = False
                    content_hash = hashlib.md5(json.dumps(result, sort_keys=True).encode()).hexdigest()[:16]
                    etag = f'"{content_hash}"'
                    _alarm_all_cache['data'] = result
                    _alarm_all_cache['time'] = now
                    _alarm_all_cache['etag'] = etag
                    # Also update legacy cache
                    _alarm_cache['data'] = result
                    _alarm_cache['time'] = now
                else:
                    _alarm_api_failing = True
                    _alarm_api_fail_time = now
            except Exception as e:
                print(f"[ALARM BG] Error: {e}")
                import time as _t
                _t.sleep(10)

    import threading
    t = threading.Thread(target=_bg_loop, daemon=True, name='alarm-bg-fetcher')
    t.start()
    print("[ALARM] Background fetcher started (polls every 25s)")

# Start background fetcher at module load
_start_alarm_background_fetcher()

@app.route('/api/alarms/proxy')
def alarm_proxy():
    """Proxy for ukrainealarm.com API - returns ALL active alerts with type info"""
    import time as _time
    now = _time.time()

    # Return cached data if fresh
    if _alarm_cache['data'] and (now - _alarm_cache['time']) < ALARM_CACHE_TTL:
        return jsonify(_alarm_cache['data'])

    # Try to fetch fresh data with retries
    for attempt in range(3):
        try:
            response = http_requests.get(
                f'{ALARM_API_BASE}/alerts',
                headers={'Authorization': ALARM_API_KEY},
                timeout=8
            )
            if response.ok:
                data = response.json()
                # Separate State (oblast) and District alerts
                states = []
                districts = []

                for region in data:
                    if region.get('activeAlerts') and len(region['activeAlerts']) > 0:
                        region_type = region.get('regionType', '')
                        region_name = region.get('regionName', '')

                        alert_info = {
                            'regionName': region_name,
                            'regionType': region_type,
                            'activeAlerts': region.get('activeAlerts')
                        }

                        if region_type == 'State':
                            states.append(alert_info)
                        elif region_type == 'District':
                            # For districts, also include parent oblast
                            oblast = DISTRICT_TO_OBLAST.get(region_name, '')
                            alert_info['oblast'] = oblast
                            districts.append(alert_info)

                result = {
                    'states': states,
                    'districts': districts,
                    'totalAlerts': len(states) + len(districts)
                }

                # Update cache
                _alarm_cache['data'] = result
                _alarm_cache['time'] = now

                return jsonify(result)
        except RecursionError:
            print(f"Alarm proxy attempt {attempt+1} failed: maximum recursion depth exceeded")
            traceback.print_exc()
        except Exception as e:
            print(f"Alarm proxy attempt {attempt+1} failed: {e}")
            if attempt < 2:
                _time.sleep(1)  # Wait before retry

    # All retries failed - return cached data if available
    if _alarm_cache['data']:
        print("Returning cached alarm data after failures")
        return jsonify(_alarm_cache['data'])

    return jsonify({'states': [], 'districts': [], 'totalAlerts': 0, 'error': 'API unavailable'})

@app.route('/api/alarms/all')
@app.route('/api/alarms')  # Alias for compatibility
@app.route('/api/alarms/full')  # Legacy alias for mobile clients
def alarm_all():
    """Returns ALL alerts (State, District, Community) for detailed view with caching"""
    import hashlib
    import time as _time
    now = _time.time()
    global _alarm_api_failing, _alarm_api_fail_time

    # Return fresh cached data if available (background fetcher keeps this warm)
    if _alarm_all_cache['data'] and (now - _alarm_all_cache['time']) < ALARM_CACHE_TTL:
        # BANDWIDTH OPTIMIZATION: Support ETag for 304 responses
        cache_etag = _alarm_all_cache.get('etag')
        client_etag = request.headers.get('If-None-Match')
        if cache_etag and client_etag == cache_etag:
            return Response(status=304, headers={'ETag': cache_etag})

        resp = jsonify(_alarm_all_cache['data'])
        resp.headers['Cache-Control'] = 'public, max-age=30'
        if cache_etag:
            resp.headers['ETag'] = cache_etag
        return resp

    # If API is failing, serve stale data immediately (for 15 seconds cooldown)
    if _alarm_api_failing and (now - _alarm_api_fail_time) < 15:
        if _alarm_all_cache['data'] and (now - _alarm_all_cache['time']) < ALARM_CACHE_STALE_TTL:
            resp = jsonify(_alarm_all_cache['data'])
            resp.headers['Cache-Control'] = 'public, max-age=30'
            resp.headers['X-Stale'] = 'true'
            return resp

    # Try to fetch with aggressive retries
    result = _fetch_alarms_from_api()
    
    if result is not None:
        _alarm_api_failing = False
        content_hash = hashlib.md5(json.dumps(result, sort_keys=True).encode()).hexdigest()[:16]
        etag = f'"{content_hash}"'

        _alarm_all_cache['data'] = result
        _alarm_all_cache['time'] = now
        _alarm_all_cache['etag'] = etag

        client_etag = request.headers.get('If-None-Match')
        if client_etag == etag:
            return Response(status=304, headers={'ETag': etag})

        resp = jsonify(result)
        resp.headers['Cache-Control'] = 'public, max-age=30'
        resp.headers['ETag'] = etag
        return resp

    # All retries failed - mark API as failing
    _alarm_api_failing = True
    _alarm_api_fail_time = now
    
    # Return stale cached data if available (within 30 min)
    if _alarm_all_cache['data'] and (now - _alarm_all_cache['time']) < ALARM_CACHE_STALE_TTL:
        print(f"[ALARM] Returning stale data ({int(now - _alarm_all_cache['time'])}s old)")
        resp = jsonify(_alarm_all_cache['data'])
        resp.headers['Cache-Control'] = 'public, max-age=30'
        resp.headers['X-Stale'] = 'true'
        return resp

    # No cache available - return empty
    print("[ALARM] API failed and no cache available")
    resp = jsonify([])
    resp.headers['Cache-Control'] = 'public, max-age=10'
    return resp


# ===== UKRAINEALARM API MONITORING FOR PUSH NOTIFICATIONS =====
# This system monitors alarm state changes and triggers push notifications

# Store previous alarm states to detect changes
_alarm_states = {}  # {region_id: {'active': bool, 'types': [str], 'last_changed': timestamp, 'notified': bool}}
_monitoring_active = False
_first_run = True  # Don't send notifications on first run (existing alarms)

def get_region_display_name(region_data):
    """Get display name for region from API data."""
    region_name = region_data.get('regionName', '')
    region_type = region_data.get('regionType', '')

    # For State regions, return the oblast name
    if region_type == 'State':
        return region_name

    # For districts, return the DISTRICT name (not oblast!)
    # This is important for notification matching - users subscribe to districts
    if region_type == 'District':
        return region_name

    return region_name

def send_alarm_notification(region_data, alarm_started: bool):
    """Send FCM notification for alarm state change."""
    if not firebase_initialized:
        log.warning("Firebase not initialized, skipping alarm notifications")
        return

    try:
        from firebase_admin import messaging

        region_name = get_region_display_name(region_data)
        region_id = region_data.get('regionId', '')
        alert_types = region_data.get('activeAlerts', [])

        # Check if this region was recently notified via Telegram (suppress duplicate)
        # Only suppress if alarm is STARTING (not ending - відбій)
        if alarm_started:
            with _telegram_alert_lock:
                now = time.time()
                # Clean old entries (older than 5 minutes)
                for key in list(_telegram_region_notified.keys()):
                    if now - _telegram_region_notified[key] > 300:
                        del _telegram_region_notified[key]

                # Check if this region was recently notified
                region_lower = region_name.lower()
                # Extract root for matching (e.g., "херсонський район" -> "херсон")
                region_root = region_lower.replace('ський район', '').replace('ська область', '').replace('ський', '').replace('ська', '').replace(' район', '').replace(' область', '').strip()[:6]

                for notified_region, timestamp in _telegram_region_notified.items():
                    notified_root = notified_region.replace('ський район', '').replace('ська область', '').replace('ський', '').replace('ська', '').replace(' район', '').replace(' область', '').strip()[:6]

                    # Match by root or full name
                    if (notified_region in region_lower or
                        region_lower in notified_region or
                        (region_root and notified_root and region_root == notified_root)):
                        elapsed = now - timestamp
                        log.info(f"⏭️ Skipping alarm notification for {region_name} - already notified via Telegram {int(elapsed)}s ago (matched: {notified_region})")
                        return

        # Check recent Telegram messages for threat details (drones, rockets, KABs, etc.)
        threat_detail = None
        threat_text = None  # The actual text from Telegram message
        tts_location = None  # Specific city/location for TTS
        try:
            # Load all messages and filter recent ones (last 10 minutes)
            all_messages = MESSAGE_STORE.load()
            now = datetime.now(pytz.timezone('Europe/Kiev'))
            cutoff = now - timedelta(minutes=10)
            recent_messages = []
            for msg in all_messages:
                msg_time_str = msg.get('timestamp') or msg.get('time') or ''
                if msg_time_str:
                    try:
                        # Parse timestamp
                        if 'T' in msg_time_str:
                            msg_time = datetime.fromisoformat(msg_time_str.replace('Z', '+00:00'))
                        else:
                            msg_time = datetime.strptime(msg_time_str, '%Y-%m-%d %H:%M:%S')
                            msg_time = pytz.timezone('Europe/Kiev').localize(msg_time)
                        if msg_time > cutoff:
                            recent_messages.append(msg)
                    except:
                        # Include message if we can't parse time
                        recent_messages.append(msg)
                else:
                    recent_messages.append(msg)

            log.info(f"Checking {len(recent_messages)} recent messages for threat details for {region_name}")
            region_lower = region_name.lower()

            # Also get oblast for matching
            oblast = DISTRICT_TO_OBLAST.get(region_name, region_name)
            oblast_lower = oblast.lower().replace(' область', '').replace('ська', 'ськ')

            # Extract district name root for fuzzy matching (e.g., "Краматорський район" -> "краматор")
            district_root = region_lower.replace(' район', '').replace('ький', '').replace('ська', '').replace('ий', '')[:7]

            # Also extract city name (e.g., "Краматорський" -> "краматорськ")
            city_name = region_lower.replace(' район', '').replace('ький', 'ськ').replace('ий', '')

            # Extract oblast root for matching (e.g., "Харківська область" -> "харків")
            oblast_root = oblast_lower.replace('ська', '').replace('ський', '')[:6]

            for msg in recent_messages:
                msg_text = (msg.get('text', '') or '')
                msg_text_lower = msg_text.lower()
                # Use 'place' field - messages use 'place' not 'location'
                msg_location = (msg.get('place', '') or msg.get('location', '') or '').lower()
                msg_oblast = (msg.get('oblast', '') or '').lower()
                combined = msg_text_lower + ' ' + msg_location + ' ' + msg_oblast

                # Check if message relates to this region (fuzzy match)
                # Note: Telegram messages use "Харків (Харківська обл.)" format
                region_match = (
                    region_lower in combined or
                    oblast_lower in combined or
                    district_root in combined or
                    city_name in combined or
                    oblast_root in combined  # "харків" in "харків (харківська обл.)"
                )

                if region_match:
                    # Витягуємо конкретну локацію (місто) з повідомлення
                    # Повідомлення мають поле 'place' з назвою міста
                    msg_place = msg.get('place', '') or ''
                    msg_location_raw = msg.get('location', '') or ''
                    
                    # Спочатку пробуємо 'place' - чистий назва міста
                    if msg_place and len(msg_place) >= 3:
                        # Капіталізуємо першу букву
                        tts_location = msg_place.strip().capitalize()
                    elif msg_location_raw and '(' in msg_location_raw:
                        # Формат: "Харків (Харківська обл.)" - витягуємо місто до дужок
                        tts_location = msg_location_raw.split('(')[0].strip()
                    elif msg_location_raw and len(msg_location_raw) >= 3:
                        tts_location = msg_location_raw.strip()

                    # Use the FULL message text as threat_text for TTS
                    # This ensures "ЗМІ повідомляють про вибухи" is spoken as-is
                    threat_text = msg_text.strip()
                    # Remove location prefix if present (e.g., "Херсон (Херсонська обл.)")
                    # as we already announce the region separately
                    if '(' in threat_text and ')' in threat_text:
                        # Extract just the message part after the location
                        parts = threat_text.split(')', 1)
                        if len(parts) > 1 and parts[1].strip():
                            threat_text = parts[1].strip()

                    if 'ракет' in msg_text_lower or 'балістичн' in msg_text_lower or 'крилат' in msg_text_lower:
                        threat_detail = 'ракети'
                        log.info(f"Found rocket threat for {region_name} at {tts_location}: {threat_text}")
                        break
                    elif 'бпла' in msg_text_lower or 'дрон' in msg_text_lower or 'шахед' in msg_text_lower:
                        threat_detail = 'дрони'
                        log.info(f"Found drone threat for {region_name} at {tts_location}: {threat_text}")
                        break
                    elif 'каб' in msg_text_lower:
                        threat_detail = 'каби'
                        log.info(f"Found KAB threat for {region_name} at {tts_location}: {threat_text}")
                        break
                    elif 'вибух' in msg_text_lower:
                        threat_detail = 'вибухи'
                        log.info(f"Found explosion report for {region_name} at {tts_location}: {threat_text}")
                        break

            # If no specific match found, just use generic alert type
            # DON'T use global messages - they may be for different regions
            if not threat_detail:
                log.info(f"No specific threat details found for {region_name}, using generic alert")

        except Exception as e:
            log.warning(f"Error checking threat details: {e}")

        # Determine notification details based on state
        if alarm_started:
            # Alarm started
            threat_types = []
            for alert in alert_types:
                alert_type = alert.get('type', '')
                if alert_type == 'AIR':
                    threat_types.append('Повітряна тривога')
                elif alert_type == 'ARTILLERY':
                    threat_types.append('Артилерійська загроза')
                elif alert_type == 'URBAN_FIGHTS':
                    threat_types.append('Вуличні бої')
                elif alert_type == 'CHEMICAL':
                    threat_types.append('Хімічна загроза')
                elif alert_type == 'NUCLEAR':
                    threat_types.append('Ядерна загроза')

            if not threat_types:
                threat_types = ['Повітряна тривога']

            title = f"🚨 Тривога: {region_name}"

            # Use threat_text from Telegram if available, otherwise use generic descriptions
            if threat_text:
                body = threat_text  # e.g., "Загроза застосування БПЛА", "Загроза застосування КАБів"
                is_critical = True
            elif threat_detail == 'ракети':
                body = "Ракетна небезпека!"
                is_critical = True
            elif threat_detail == 'дрони':
                body = "Загроза застосування БПЛА"
                is_critical = True
            elif threat_detail == 'каби':
                body = "Загроза застосування КАБів"
                is_critical = True
            elif threat_detail == 'вибухи':
                body = "Повідомляють про вибухи"
                is_critical = True
            else:
                body = ", ".join(threat_types)
                is_critical = True
        else:
            # Alarm ended
            title = f"✅ Відбій: {region_name}"
            body = "Загрозу знято"
            is_critical = False

        log.info("=== ALARM FCM NOTIFICATION ===")
        log.info(f"Region: {region_name} ({region_id})")
        log.info(f"State: {'STARTED' if alarm_started else 'ENDED'}")
        log.info(f"Message: {title} - {body}")

        # Get topic for this region (using global REGION_TOPIC_MAP)
        topic = REGION_TOPIC_MAP.get(region_name)

        # If district, also get oblast topic
        region_type = region_data.get('regionType', '')
        oblast_topic = None
        if region_type == 'District':
            oblast = DISTRICT_TO_OBLAST.get(region_name, '')
            if oblast:
                oblast_topic = REGION_TOPIC_MAP.get(oblast)
                log.info(f"District {region_name} maps to oblast {oblast} (topic: {oblast_topic})")

        if not topic and not oblast_topic:
            log.info(f"No topic mapping for region: {region_name}")
            return

        # Send to topic (much more efficient than individual devices)
        success_count = 0

        # Send to region topic if available
        topics_to_send = []
        if topic:
            topics_to_send.append(topic)
        if oblast_topic and oblast_topic != topic:
            topics_to_send.append(oblast_topic)

        for target_topic in topics_to_send:
            try:
                # Визначаємо чіткий тип загрози для TTS
                if alarm_started:
                    if threat_detail == 'ракети':
                        tts_threat = 'Ракетна небезпека'
                    elif threat_detail == 'каби':
                        tts_threat = 'Загроза КАБів'
                    elif threat_detail == 'дрони':
                        tts_threat = 'Загроза БПЛА'
                    elif threat_detail == 'вибухи':
                        tts_threat = 'Повідомляють про вибухи'
                    else:
                        tts_threat = 'Повітряна тривога'
                else:
                    tts_threat = 'Відбій тривоги'

                # Визначаємо локацію для TTS: конкретне місто або область
                # Мінімальна довжина 5 символів щоб уникнути "Кам" замість "Каменське"
                if tts_location and len(tts_location) >= 5:
                    fcm_location = tts_location
                else:
                    fcm_location = region_name
                
                log.info(f"TTS location for FCM: tts_location={tts_location}, region_name={region_name}, fcm_location={fcm_location}")

                # Resolve region IDs for client-side filtering
                # CRITICAL FIX: If region is a District, resolve its Oblast first
                region_type = region_data.get('regionType', '')
                oblast_name = region_name
                if region_type == 'District':
                    oblast_name = DISTRICT_TO_OBLAST.get(region_name, region_name)
                    log.info(f"District {region_name} resolved to oblast: {oblast_name}")
                
                oblast_id, raion_id = get_region_ids_from_place(fcm_location, oblast_name)
                
                # If district, also try to resolve raion_id from district name directly
                if region_type == 'District' and not raion_id:
                    # Try to find raion_id from PLACE_TO_RAION_ID using district name
                    district_lower = region_name.lower().replace(' район', '').replace('ський', '').replace('цький', '').strip()
                    for keyword, (kw_oblast, kw_raion) in PLACE_TO_RAION_ID.items():
                        keyword_root = keyword.replace('ський', '').replace('цький', '').strip()
                        if oblast_id and kw_oblast == oblast_id and keyword_root in district_lower:
                            raion_id = kw_raion
                            log.info(f"Resolved raion_id={raion_id} from district name: {region_name}")
                            break
                
                log.info(f"📍 Resolved IDs for FCM: oblast_id={oblast_id}, raion_id={raion_id}, region_type={region_type}")
                if not oblast_id:
                    log.warning(f"⚠️ Failed to resolve oblast_id for region: {region_name} (oblast: {oblast_name})")

                # For Android: DATA-ONLY (no notification block) so background handler can process TTS
                # For iOS: Use APNSPayload (not top-level notification) for more reliable delivery
                message = messaging.Message(
                    data={
                        'type': 'alarm',
                        'title': title,
                        'body': body,
                        'location': fcm_location,  # Конкретне місто або область для TTS
                        'region': region_name,  # Область (для фільтрації)
                        'region_id': region_id,
                        'oblast_id': oblast_id or '',
                        'raion_id': raion_id or '',
                        'settlement_id': '',
                        'alarm_state': 'active' if alarm_started else 'ended',
                        'is_critical': 'true' if is_critical else 'false',
                        'threat_type': tts_threat,  # Чіткий тип загрози для TTS
                        'timestamp': datetime.now(pytz.timezone('Europe/Kiev')).isoformat(),
                        'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                    },
                    android=messaging.AndroidConfig(
                        priority='high',
                        ttl=timedelta(seconds=300),
                    ),
                    apns=messaging.APNSConfig(
                        headers={
                            'apns-priority': '10',
                            'apns-push-type': 'alert',
                            'apns-expiration': '0',  # Immediate delivery, no storing
                        },
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                alert=messaging.ApsAlert(title=title, body=body),
                                sound='default',
                                badge=1,
                                content_available=True,
                                mutable_content=True,  # Allows Notification Service Extension to modify
                            ),
                        ),
                    ),
                    topic=target_topic,  # Send to topic instead of individual token
                )

                success, response, error = _send_fcm_with_retry(message)
                
                if success:
                    success_count += 1
                    log.info(f"✅ Alarm notification sent to topic {target_topic}: {response}")
                else:
                    log.error(f"Failed to send alarm to topic {target_topic} after retries: {error}")
            except Exception as e:
                log.error(f"Exception sending alarm to topic {target_topic}: {e}")

        log.info(f"Sent alarm notifications to {success_count} topics for region: {region_name}")
    except Exception as e:
        log.error(f"Error in send_alarm_notification: {e}")


# Track recently sent telegram alerts to avoid duplicates (message_id -> timestamp)
_telegram_alert_sent = {}
_telegram_alert_lock = threading.Lock()

# Track regions that received Telegram notifications recently to suppress duplicate alarm notifications
# region_name (normalized) -> timestamp
_telegram_region_notified = {}

# Cache for region topic lookups (region_name -> topic)
_region_topic_cache = {}
_region_topic_cache_lock = threading.Lock()

# Cache for threat classifications (message_hash -> classification)
_threat_classification_cache = {}
_threat_classification_cache_lock = threading.Lock()
_THREAT_CACHE_TTL = 3600  # 1 hour

# ============================================================================
# Memory Management & Automatic Cleanup
# ============================================================================

class MemoryManager:
    """Automatic memory cleanup for caches"""
    
    def __init__(self):
        self.last_cleanup = time.time()
        self.cleanup_interval = 600  # 10 minutes
        self.metrics = {
            'cleanups': 0,
            'items_removed': 0,
            'memory_freed_mb': 0
        }
    
    def should_cleanup(self):
        return time.time() - self.last_cleanup > self.cleanup_interval
    
    def cleanup_all_caches(self):
        """Clean up all caches - call periodically"""
        if not self.should_cleanup():
            return
        
        import psutil
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        removed = 0
        
        # Cleanup ResponseCache
        removed += RESPONSE_CACHE.cleanup()
        
        # Cleanup threat classification cache
        with _threat_classification_cache_lock:
            now = time.time()
            old_keys = [k for k, (_, ts) in _threat_classification_cache.items() 
                       if now - ts > _THREAT_CACHE_TTL]
            for key in old_keys:
                del _threat_classification_cache[key]
            removed += len(old_keys)
        
        # Cleanup telegram alert cache
        with _telegram_alert_lock:
            now = time.time()
            old_keys = [k for k, ts in _telegram_alert_sent.items() 
                       if now - ts > 600]
            for key in old_keys:
                del _telegram_alert_sent[key]
            removed += len(old_keys)
        
        # Cleanup region notified cache
        old_keys = [k for k, ts in _telegram_region_notified.items() 
                   if now - ts > 300]
        for key in old_keys:
            del _telegram_region_notified[key]
        removed += len(old_keys)
        
        # Force garbage collection
        gc.collect()
        
        mem_after = process.memory_info().rss / 1024 / 1024
        mem_freed = max(0, mem_before - mem_after)
        
        self.metrics['cleanups'] += 1
        self.metrics['items_removed'] += removed
        self.metrics['memory_freed_mb'] += mem_freed
        self.last_cleanup = time.time()
        
        if removed > 0:
            log.info(f"🧹 Memory cleanup: removed {removed} cached items, freed ~{mem_freed:.1f}MB")
        
        return removed

_memory_manager = MemoryManager()

def _auto_cleanup_if_needed():
    """Call this in request handlers to trigger cleanup"""
    if _memory_manager.should_cleanup():
        threading.Thread(target=_memory_manager.cleanup_all_caches, daemon=True).start()


# ============================================================================
# Request Deduplication - Coalesce identical concurrent requests
# ============================================================================

_pending_requests = {}  # request_key -> Future-like object
_pending_requests_lock = threading.Lock()

class RequestResult:
    """Thread-safe result container"""
    def __init__(self):
        self.result = None
        self.error = None
        self.ready = threading.Event()
    
    def set_result(self, value):
        self.result = value
        self.ready.set()
    
    def set_error(self, error):
        self.error = error
        self.ready.set()
    
    def wait(self, timeout=10):
        """Wait for result, return (result, error)"""
        self.ready.wait(timeout)
        return self.result, self.error

def deduplicate_request(key: str, func, *args, **kwargs):
    """Deduplicate identical concurrent requests"""
    with _pending_requests_lock:
        if key in _pending_requests:
            # Request already in progress, wait for it
            pending = _pending_requests[key]
            is_waiting = True
        else:
            # First request with this key
            pending = RequestResult()
            _pending_requests[key] = pending
            is_waiting = False
    
    if is_waiting:
        # Wait for original request to complete
        result, error = pending.wait()
        if error:
            raise error
        return result
    
    # Execute the request
    try:
        result = func(*args, **kwargs)
        pending.set_result(result)
        return result
    except Exception as e:
        pending.set_error(e)
        raise
    finally:
        # Cleanup
        with _pending_requests_lock:
            _pending_requests.pop(key, None)


# Cache for threat classifications (message_hash -> classification)
# (declarations moved above for MemoryManager)


def _get_cached_topic(region_name: str) -> str | None:
    """Get topic from cache with thread safety"""
    with _region_topic_cache_lock:
        return _region_topic_cache.get(region_name)


def _cache_topic(region_name: str, topic: str):
    """Cache topic lookup result"""
    with _region_topic_cache_lock:
        _region_topic_cache[region_name] = topic


def _classify_threat_cached(message_text: str) -> dict | None:
    """Classify threat with caching"""
    import hashlib
    msg_hash = hashlib.md5(message_text.encode()).hexdigest()
    
    with _threat_classification_cache_lock:
        # Check cache
        if msg_hash in _threat_classification_cache:
            cached, timestamp = _threat_classification_cache[msg_hash]
            if time.time() - timestamp < _THREAT_CACHE_TTL:
                return cached
        
        # Classify - AI DISABLED, return None
        return None


def _send_fcm_with_retry(message, max_retries=2, initial_delay=0.5):
    """
    Send FCM message with exponential backoff retry.
    Returns (success: bool, response: str, error: str)
    """
    from firebase_admin import messaging
    
    for attempt in range(max_retries + 1):
        try:
            response = messaging.send(message)
            return (True, response, None)
        except Exception as e:
            error_str = str(e)
            
            # Don't retry on quota/auth errors
            if 'quota' in error_str.lower() or 'auth' in error_str.lower():
                return (False, None, error_str)
            
            # Last attempt - give up
            if attempt >= max_retries:
                return (False, None, error_str)
            
            # Exponential backoff
            delay = initial_delay * (2 ** attempt)
            log.warning(f"FCM send failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay}s: {error_str}")
            time.sleep(delay)
    
    return (False, None, "Max retries exceeded")


def send_telegram_threat_notification(message_text: str, location: str, message_id: str):
    """Send FCM notification for threat messages from Telegram (КАБи, ракети, БПЛА etc.)."""
    print(f"[TELEGRAM_PUSH] Called: location='{location}', msg_id={message_id}, firebase_init={firebase_initialized}", flush=True)
    log.info(f"📲 send_telegram_threat_notification called: location='{location}', msg_id={message_id}")
    
    if not firebase_initialized:
        print("[TELEGRAM_PUSH] ❌ Firebase NOT initialized, skipping push", flush=True)
        log.warning("⚠️ Firebase not initialized, skipping push")
        return

    # Deduplicate - don't send same message within 5 minutes
    with _telegram_alert_lock:
        now = time.time()
        # Clean old entries
        if _telegram_alert_sent:
            _telegram_alert_sent.update({k: v for k, v in _telegram_alert_sent.items() if now - v <= 300})
            if len(_telegram_alert_sent) > 1000:
                _telegram_alert_sent.clear()

        if message_id in _telegram_alert_sent:
            print(f"[TELEGRAM_PUSH] ⏭️ Skipping duplicate msg_id={message_id}", flush=True)
            return
        _telegram_alert_sent[message_id] = now
        print(f"[TELEGRAM_PUSH] ✅ New message, proceeding with msg_id={message_id}", flush=True)

    try:
        from firebase_admin import messaging

        msg_lower = message_text.lower()
        print(f"[TELEGRAM_PUSH] 📝 Processing: '{message_text[:50]}...'", flush=True)

        # Regex-based classification (GROQ removed)
        if 'каб' in msg_lower:
            threat_type = 'каби'
            emoji = '💣'
            is_critical = True
        elif 'ракет' in msg_lower or 'балістичн' in msg_lower:
            threat_type = 'ракети'
            emoji = '🚀'
            is_critical = True
        elif 'бпла' in msg_lower or 'дрон' in msg_lower or 'шахед' in msg_lower:
            threat_type = 'дрони'
            emoji = '🛩️'
            is_critical = True
        elif 'вибух' in msg_lower:
            threat_type = 'вибухи'
            emoji = '💥'
            is_critical = True
        else:
            # Not a threat message, skip
            return

        # Extract region from location (e.g., "Харків (Харківська обл.)" -> "Харківська область")
        region_name = location
        city_name = ''  # Specific city for TTS
        if '(' in location and 'обл' in location:
            # Extract city (before parentheses) and oblast (in parentheses)
            city_match = RE_CITY_BEFORE_PARENS.match(location)
            if city_match:
                city_name = city_match.group(1).strip()
                # Remove threat type prefixes from city name (БПЛА, ракети, каби, etc.)
                threat_prefixes = ['бпла', 'ракет', 'каб', 'шахед', 'дрон', 'удар', 'вибух', 'балістик']
                city_words = city_name.split()
                filtered_words = [w for w in city_words if not any(p in w.lower() for p in threat_prefixes)]
                city_name = ' '.join(filtered_words).strip()
                
                # ВАЖЛИВО: Якщо після фільтрації залишилось тільки "р-н", "район" або інші загальні позначки
                # це означає, що конкретне місто не вказане - НЕ НАДСИЛАТИ повідомлення
                generic_markers = ['р-н', 'р-н.', 'рн', 'район', 'районі', 'району', 'районом', 'р н', 'р.н.', 'н.п.', 'нп']
                if city_name.lower().strip() in generic_markers or len(city_name) < 3:
                    log.info(f"🚫 Generic location marker detected: '{city_name}' from location '{location}' - SKIPPING notification (no specific city)")
                    print(f"[TELEGRAM_PUSH] ❌ No specific city in location '{location}', skipping notification", flush=True)
                    return  # НЕ надсилаємо якщо немає конкретного міста
                    
            oblast_match = RE_OBLAST_IN_PARENS.search(location)
            if oblast_match:
                region_name = oblast_match.group(1).strip()
                print(f"[TELEGRAM_PUSH] Extracted oblast from parens: '{region_name}'", flush=True)
                # Normalize: "Харківська обл." -> "Харківська область"
                region_name = RE_OBLAST_SUFFIX.sub('область', region_name).strip()
                print(f"[TELEGRAM_PUSH] Normalized region name: '{region_name}'", flush=True)
        else:
            region_from_text = _extract_oblast_from_text(location)
            if region_from_text:
                region_name = RE_OBLAST_SUFFIX.sub('область', region_from_text).strip()

        # Try to find matching region in REGION_TOPIC_MAP if not exact match
        print(f"[TELEGRAM_PUSH] Looking for '{region_name}' in REGION_TOPIC_MAP (has {len(REGION_TOPIC_MAP)} entries)", flush=True)
        if region_name not in REGION_TOPIC_MAP:
            print(f"[TELEGRAM_PUSH] Exact match not found, trying partial match...", flush=True)
            # Try to find by partial match
            region_lower = region_name.lower()
            for topic_region in REGION_TOPIC_MAP.keys():
                if topic_region.lower().replace(' область', '') in region_lower or \
                   region_lower.replace(' область', '') in topic_region.lower():
                    print(f"[TELEGRAM_PUSH] Partial match: '{region_name}' -> '{topic_region}'", flush=True)
                    log.info(f"Matched region '{region_name}' to '{topic_region}'")
                    region_name = topic_region
                    break
        else:
            print(f"[TELEGRAM_PUSH] Exact match found for '{region_name}'", flush=True)

        title = f"{emoji} {region_name}"

        # For TTS: use city if available and long enough (>= 5 chars), otherwise region
        # This prevents "Кам" instead of "Каменське"
        if city_name and len(city_name) >= 5:
            tts_location = city_name
        else:
            tts_location = region_name
        
        log.info(f"TTS location: city_name='{city_name}', region_name='{region_name}', tts_location='{tts_location}'")

        # Extract threat description from message (remove location prefix)
        body = message_text
        if ')' in body:
            parts = body.split(')', 1)
            if len(parts) > 1 and parts[1].strip():
                body = parts[1].strip()

        # Remove emoji from start if present
        if body and body[0] in '💣🚀🛩️💥🚨⚠️':
            body = body[1:].strip()

        log.info("=== TELEGRAM THREAT NOTIFICATION ===")
        log.info(f"Location: {location} -> {region_name}")
        log.info(f"Threat: {threat_type}")
        log.info(f"Message: {title} - {body}")

        # Get topic for this region (using global REGION_TOPIC_MAP)
        topic = REGION_TOPIC_MAP.get(region_name)
        print(f"[TELEGRAM_PUSH] Topic lookup for '{region_name}': {topic}", flush=True)

        # Also try matching by city in parentheses -> extract oblast
        if not topic and '(' in location:
            city = location.split('(')[0].strip()
            # Try to find oblast from city
            for oblast_name in REGION_TOPIC_MAP.keys():
                if oblast_name.replace(' область', '').lower() in location.lower():
                    topic = REGION_TOPIC_MAP.get(oblast_name)
                    print(f"[TELEGRAM_PUSH] Matched city '{city}' to oblast '{oblast_name}', topic: {topic}", flush=True)
                    log.info(f"Matched city {city} to oblast {oblast_name}")
                    break

        if not topic:
            print(f"[TELEGRAM_PUSH] ❌ No topic found for '{region_name}', skipping notification", flush=True)
            log.warning(f"❌ No topic mapping for region: {region_name}, location was: {location} - notification NOT sent")
            return  # Don't send if we can't determine the region

        print(f"[TELEGRAM_PUSH] Final topic: {topic}", flush=True)
        log.info(f"Sending telegram threat to topic: {topic}")
        
        # Перевірка чи є офіційна тривога в регіоні (гібридний режим)
        has_official_alarm = False
        try:
            # Перевіряємо чи є активна тривога в цьому регіоні
            if oblast_id or region_name:
                # _alarm_states формат: {region_id: {'active': bool, 'types': [...]}}
                for stored_region_id, alarm_data in _alarm_states.items():
                    # Перевіряємо співпадіння по ID регіону
                    region_match = False
                    if oblast_id and oblast_id in stored_region_id:
                        region_match = True
                    elif region_name:
                        # Перевірка по назві в ID (напр. "Сумська" в "5:Сумська область")
                        region_name_lower = region_name.lower().replace(' область', '').replace(' обл.', '').strip()
                        if region_name_lower in stored_region_id.lower():
                            region_match = True
                    
                    if region_match:
                        # Перевіряємо чи є активна тривога
                        if alarm_data.get('active') and alarm_data.get('types'):
                            has_official_alarm = True
                            log.info(f"✅ Official alarm active in {region_name}: {alarm_data.get('types')}")
                            break
                
                if not has_official_alarm:
                    log.info(f"⚠️ No official alarm in {region_name} (checked {len(_alarm_states)} regions)")
        except Exception as check_err:
            log.warning(f"Error checking official alarm: {check_err}")

        # Map internal threat codes to human-readable Ukrainian for TTS
        threat_type_readable = {
            'каби': 'Загроза КАБів',
            'ракети': 'Ракетна небезпека',
            'дрони': 'Загроза БПЛА',
            'вибухи': 'Повідомляють про вибухи',
        }.get(threat_type, 'Повітряна тривога')  # Default to general alert

        # Resolve region IDs for ID-based filtering on client
        place_for_ids = city_name or location
        oblast_id, raion_id = get_region_ids_from_place(place_for_ids, region_name)
        
        log.info(f"📍 Telegram threat: place_for_ids='{place_for_ids}', region_name='{region_name}'")
        log.info(f"📍 Resolved IDs: oblast_id={oblast_id}, raion_id={raion_id}")
        
        if not oblast_id:
            log.warning(f"⚠️ Failed to resolve oblast_id for region: {region_name} (location: {location})")
        
        # Покращена резолюція raion_id з назви міста
        if not raion_id and city_name:
            # Try to resolve raion from city name
            city_lower = city_name.lower().strip()
            
            # Мапа популярних міст → raion_id для точної фільтрації
            # Формат: 'місто': 'UA-XX-YY' (код району)
            CITY_TO_RAION = {
                # Київська область
                'біла церква': 'UA-32-01',  # Білоцерківський район
                'білоцерківськ': 'UA-32-01',
                'бориспіль': 'UA-32-02',  # Бориспільський район
                'бровари': 'UA-32-03',  # Броварський район
                'буча': 'UA-32-04',  # Бучанський район
                'ірпінь': 'UA-32-04',
                'вишгород': 'UA-32-05',  # Вишгородський район
                'обухів': 'UA-32-06',  # Обухівський район
                'фастів': 'UA-32-07',  # Фастівський район
                # Додайте інші популярні міста за потреби
            }
            
            # Спробувати exact match
            if city_lower in CITY_TO_RAION:
                raion_id = CITY_TO_RAION[city_lower]
                log.info(f"📍 Exact match: city '{city_name}' -> raion_id={raion_id}")
            else:
                # Fallback to keyword matching in PLACE_TO_RAION_ID
                for keyword, (kw_oblast, kw_raion) in PLACE_TO_RAION_ID.items():
                    if keyword in city_lower or city_lower in keyword:
                        if not oblast_id or kw_oblast == oblast_id:
                            raion_id = kw_raion
                            log.info(f"📍 Keyword match: '{city_name}' -> raion_id={raion_id} (keyword: {keyword})")
                            break

        # Додаємо позначку якщо немає офіційної тривоги
        warning_prefix = ''
        if not has_official_alarm:
            warning_prefix = '⚠️ '
            # Додаємо пояснення в body
            if not body.startswith('⚠️'):
                body = f"{body} (попередження з Telegram, офіційної тривоги ще немає)"
            title = f"{warning_prefix}{title}"

        # Send to topic
        success_count = 0
        try:
            # DATA-ONLY for Android (enables background handler + TTS)
            # APNSPayload for iOS (shows notification + data for foreground TTS)
            message = messaging.Message(
                data={
                    'type': 'telegram_threat',
                    'title': title,
                    'body': body,
                    'location': tts_location,  # City or region for TTS
                    'city': city_name or '',  # Конкретне місто для фільтрації на клієнті
                    'region': region_name,
                    'oblast_id': oblast_id or '',
                    'raion_id': raion_id or '',
                    'settlement_id': '',
                    'alarm_state': 'active',
                    'is_critical': 'true' if is_critical else 'false',
                    'threat_type': threat_type_readable,  # Human-readable threat for TTS
                    'timestamp': datetime.now(pytz.timezone('Europe/Kiev')).isoformat(),
                    'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                },
                android=messaging.AndroidConfig(
                    priority='high',
                    ttl=timedelta(seconds=300),
                ),
                apns=messaging.APNSConfig(
                    headers={
                        'apns-priority': '10',
                        'apns-push-type': 'alert',
                        'apns-expiration': str(int(time.time()) + 300),
                    },
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(title=title, body=body),
                            sound='default',
                            badge=1,
                            content_available=True,
                            mutable_content=True,
                        ),
                    ),
                ),
                topic=topic,  # Send to topic instead of individual token
            )

            success, response, error = _send_fcm_with_retry(message)
            
            if success:
                success_count = 1
                print(f"[TELEGRAM_PUSH] ✅ Sent to topic '{topic}': {response}", flush=True)
                log.info(f"✅ Telegram threat notification sent to topic {topic}: {response}")
            else:
                print(f"[TELEGRAM_PUSH] ❌ Failed to send to topic '{topic}' after retries: {error}", flush=True)
                log.error(f"Failed to send telegram threat to topic {topic} after retries: {error}")
        except Exception as e:
            print(f"[TELEGRAM_PUSH] ❌ Exception during send: {e}", flush=True)
            log.error(f"Exception sending telegram threat to topic {topic}: {e}")

        log.info(f"Sent telegram threat notification to topic: {topic}")

        # Mark this region as notified to suppress duplicate alarm notifications
        if success_count > 0:
            with _telegram_alert_lock:
                # Normalize region name for matching
                region_key = region_name.lower()
                _telegram_region_notified[region_key] = time.time()
                # Also mark the city if different
                if '(' in location:
                    city = location.split('(')[0].strip().lower()
                    _telegram_region_notified[city] = time.time()
                log.info(f"Marked region '{region_key}' as telegram-notified (will suppress alarm notifications for 5 min)")

    except Exception as e:
        log.error(f"Error in send_telegram_threat_notification: {e}")

def monitor_alarms():
    """Background task to monitor ukrainealarm API and send notifications on state changes."""
    global _alarm_states, _first_run

    log.info("=== ALARM MONITORING STARTED ===")

    consecutive_failures = 0
    MAX_FAILURES_BEFORE_WARN = 5
    last_successful_fetch = 0

    while _monitoring_active:
        try:
            # Try multiple times before giving up this cycle
            data = None
            for attempt in range(3):
                try:
                    response = http_requests.get(
                        f'{ALARM_API_BASE}/alerts',
                        headers={'Authorization': ALARM_API_KEY},
                        timeout=15
                    )
                    if response.ok:
                        data = response.json()
                        consecutive_failures = 0
                        last_successful_fetch = time.time()
                        break
                    else:
                        log.warning(f"API attempt {attempt+1}/3 failed: HTTP {response.status_code}")
                except Exception as e:
                    log.warning(f"API attempt {attempt+1}/3 error: {e}")

                if attempt < 2:
                    time.sleep(2)  # Wait 2 sec between retries

            if data is None:
                consecutive_failures += 1
                if consecutive_failures >= MAX_FAILURES_BEFORE_WARN:
                    log.error(f"API unavailable for {consecutive_failures} consecutive cycles! Last success: {int(time.time() - last_successful_fetch)}s ago")
                else:
                    log.warning(f"API fetch failed (attempt {consecutive_failures}), keeping previous state")
                # DON'T clear _alarm_states - keep previous state!
                time.sleep(30)
                continue

            current_time = time.time()

            # Track which regions currently have alarms
            current_active_regions = set()

            # On first run, just store current states WITHOUT sending notifications
            # This prevents spam after server redeploy
            if _first_run:
                log.info("First run after deploy - storing initial alarm states WITHOUT notifications")
                for region in data:
                    region_id = region.get('regionId', '')
                    region_type = region.get('regionType', '')
                    active_alerts = region.get('activeAlerts', [])
                    has_alarm = len(active_alerts) > 0

                    if has_alarm:
                        current_active_regions.add(region_id)
                        # Just store the state - NO notification on first run
                        log.info(f"📝 Stored existing alarm: {region.get('regionName')} (type: {region_type})")
                        _alarm_states[region_id] = {
                            'active': True,
                            'types': [alert.get('type') for alert in active_alerts],
                            'last_changed': current_time,
                            'notified': True  # Mark as notified to prevent duplicate on next change
                        }

                _first_run = False
                log.info(f"Initial state stored - {len(current_active_regions)} active alarms (no push sent)")
            else:
                # Normal monitoring - check for changes
                for region in data:
                    region_id = region.get('regionId', '')
                    region_type = region.get('regionType', '')
                    active_alerts = region.get('activeAlerts', [])
                    has_alarm = len(active_alerts) > 0

                    if has_alarm:
                        current_active_regions.add(region_id)

                    # Check if this is a state change
                    previous_state = _alarm_states.get(region_id, {})
                    was_active = previous_state.get('active', False)
                    was_notified = previous_state.get('notified', False)

                    if has_alarm and not was_active:
                        # Alarm started - send notification ONLY for Districts
                        if not was_notified and region_type == 'District':
                            log.info(f"🚨 DISTRICT ALARM STARTED: {region.get('regionName')} (ID: {region_id})")
                            send_alarm_notification(region, alarm_started=True)
                        elif region_type == 'State':
                            log.info(f"ℹ️ Oblast alarm started (no push): {region.get('regionName')}")
                        _alarm_states[region_id] = {
                            'active': True,
                            'types': [alert.get('type') for alert in active_alerts],
                            'last_changed': current_time,
                            'notified': True
                        }
                    elif not has_alarm and was_active:
                        # Alarm ended - send відбій ONLY for Districts
                        if region_type == 'District':
                            log.info(f"✅ DISTRICT ALARM ENDED: {region.get('regionName')} (ID: {region_id})")
                            send_alarm_notification(region, alarm_started=False)
                        elif region_type == 'State':
                            log.info(f"ℹ️ Oblast alarm ended (no push): {region.get('regionName')}")
                        _alarm_states[region_id] = {
                            'active': False,
                            'types': [],
                            'last_changed': current_time,
                            'notified': False  # Reset for next alarm
                        }
                    elif has_alarm and was_active:
                        # Alarm still active - only log, don't resend notification
                        current_types = [alert.get('type') for alert in active_alerts]
                        previous_types = previous_state.get('types', [])
                        if set(current_types) != set(previous_types):
                            log.info(f"⚠️ ALARM TYPES CHANGED: {region.get('regionName')} - {current_types}")
                            _alarm_states[region_id]['types'] = current_types
                            # Keep notified=True to prevent resending

                # Check for regions that went from active to inactive (ended alarms)
                for region_id, state in list(_alarm_states.items()):
                    if state.get('active') and region_id not in current_active_regions:
                        # Find region data to send відбій notification
                        region_data = next((r for r in data if r.get('regionId') == region_id), None)
                        if region_data:
                            region_type = region_data.get('regionType', '')
                            # Send відбій ONLY for Districts
                            if region_type == 'District':
                                log.info(f"✅ DISTRICT ALARM ENDED (from tracking): {region_data.get('regionName')} (ID: {region_id})")
                                send_alarm_notification(region_data, alarm_started=False)
                            else:
                                log.info(f"ℹ️ Oblast alarm ended (from tracking, no push): {region_data.get('regionName')}")
                        _alarm_states[region_id] = {
                            'active': False,
                            'types': [],
                            'last_changed': current_time,
                            'notified': False
                        }

                log.info(f"Alarm monitoring cycle complete - {len(current_active_regions)} active alarms")

        except Exception as e:
            log.error(f"Error in alarm monitoring: {e}")
            consecutive_failures += 1

        # Wait before next check (45 seconds to reduce CPU load)
        time.sleep(45)

    log.info("=== ALARM MONITORING STOPPED ===")

def start_alarm_monitoring():
    """Start the alarm monitoring background thread."""
    global _monitoring_active

    if _monitoring_active:
        log.info("Alarm monitoring already active")
        return

    _monitoring_active = True
    monitor_thread = threading.Thread(target=monitor_alarms, daemon=True)
    monitor_thread.start()
    log.info("Alarm monitoring thread started")

# Start monitoring when app initializes
if firebase_initialized:
    start_alarm_monitoring()
else:
    log.warning("Firebase not initialized - alarm monitoring disabled")

@app.route('/api/monitoring-status')
def monitoring_status():
    """Check alarm monitoring status (for debugging)."""
    active_districts = []
    for region_id, state in _alarm_states.items():
        if state.get('active'):
            active_districts.append(region_id)

    return jsonify({
        'monitoring_active': _monitoring_active,
        'first_run': _first_run,
        'firebase_initialized': firebase_initialized,
        'alarm_states_count': len(_alarm_states),
        'active_alarms': len(active_districts),
        'active_region_ids': active_districts[:20],  # First 20 for debug
        'server_time': datetime.now(pytz.timezone('Europe/Kiev')).isoformat(),
    })

# ===== END UKRAINEALARM MONITORING =====


# Custom route for serving pre-compressed static files
@app.route('/static/<path:filename>')
def static_with_gzip(filename):
    """Serve static files with gzip compression support."""

    # SMART BANDWIDTH PROTECTION: Only rate limit large files, not icons
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)

    # Skip rate limiting for small assets (icons, SVG, small images)
    is_small_asset = filename.endswith(('.svg', '.ico', '.woff', '.woff2')) or \
                     filename.startswith('icon_') or \
                     filename in ('manifest.json', 'sitemap.xml')

    if not is_small_asset:
        static_requests = request_counts.get(f"{client_ip}_static", [])
        now_time = time.time()

        # Clean old requests (last 60 seconds)
        static_requests = [req_time for req_time in static_requests if now_time - req_time < 60]

        # Allow 30 static file requests per minute per IP (increased from 5)
        if len(static_requests) >= 30:
            print(f"[BANDWIDTH] Rate limiting static file {filename} from {client_ip}")
            return jsonify({'error': 'Static files rate limited - wait 1 minute'}), 429

        static_requests.append(now_time)
        request_counts[f"{client_ip}_static"] = static_requests

    # SMART BANDWIDTH PROTECTION: Block only genuinely large files (>1MB)
    try:
        static_folder = os.path.join(os.path.dirname(__file__), 'static')
        file_path = os.path.join(static_folder, filename)

        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)

            # Block files larger than 1MB to save bandwidth
            if file_size > 1024 * 1024:  # 1MB limit
                print(f"[BANDWIDTH PROTECTION] Blocking large file {filename} ({file_size//1024}KB) from {client_ip}")
                return jsonify({'error': f'Large file blocked - size {file_size//1024}KB exceeds 1MB limit'}), 503

            # Log access to files over 100KB for monitoring
            if file_size > 100 * 1024:
                print(f"[BANDWIDTH MONITOR] Serving large file {filename} ({file_size//1024}KB) to {client_ip}")
        else:
            print(f"[STATIC FILE] File not found: {filename}")
            return jsonify({'error': 'File not found'}), 404

    except Exception as e:
        print(f"[BANDWIDTH ERROR] Error checking file {filename}: {e}")
        return jsonify({'error': 'File access error'}), 500

    # Check if client accepts gzip and we have a gzipped version
    accepts_gzip = 'gzip' in request.headers.get('Accept-Encoding', '').lower()

    if accepts_gzip and filename.endswith('.js'):
        gzip_path = os.path.join(app.static_folder, filename + '.gz')
        if os.path.exists(gzip_path):
            response = send_from_directory(app.static_folder, filename + '.gz')
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Type'] = 'application/javascript; charset=utf-8'

            # Add strong caching for JS files
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            response.headers['Expires'] = (datetime.now() + timedelta(days=365)).strftime('%a, %d %b %Y %H:%M:%S GMT')

            return response

    # Fall back to regular static file serving
    response = send_from_directory(app.static_folder, filename)

    # CRITICAL BANDWIDTH PROTECTION: Check file size
    try:
        file_path = os.path.join(app.static_folder, filename)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            if file_size > 100 * 1024:  # 100KB limit
                print(f"[CRITICAL BANDWIDTH] Large static file {filename}: {file_size/1024:.1f}KB from {client_ip}")
    except Exception:
        pass

    return response

# Configure caching and compression for better performance on slow connections
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year for static files
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# MEMORY PROTECTION: Max response size limit
MAX_RESPONSE_SIZE_MB = 50  # 50MB absolute max - anything larger is an error

@app.after_request
def check_response_size_limit(response):
    """Emergency protection against huge responses that could crash the server."""
    try:
        if response.content_length and response.content_length > MAX_RESPONSE_SIZE_MB * 1024 * 1024:
            print(f"[CRITICAL] Response too large: {response.content_length / 1024 / 1024:.1f}MB for {request.path}")
            # Don't send the huge response - return error instead
            return Response(
                json.dumps({'error': 'Response too large', 'size_mb': response.content_length / 1024 / 1024}),
                status=500,
                mimetype='application/json'
            )
    except:
        pass
    return response

# NOTE: Cache headers handled by unified add_cache_headers() in SECTION [PERFORMANCE OPTIMIZATION]
# Duplicate @app.after_request removed to fix Flask middleware conflict

COMMENTS = []  # retained as a small in-memory cache (recent) but now persisted to SQLite
COMMENTS_MAX = 500
ACTIVE_VISITORS = {}
ACTIVE_LOCK = threading.Lock()
ACTIVE_TTL = 70  # seconds of inactivity before a visitor is dropped
BLOCKED_FILE = 'blocked_ids.json'
# STATS_FILE and RECENT_VISITS_FILE are defined below in persistent storage section
VISIT_STATS = None  # lazy-loaded dict: {id: first_seen_epoch}
_visit_stats_lock = threading.RLock()  # Prevent concurrent modification errors
_recent_visits_lock = threading.RLock()  # Prevent concurrent modification of recent visits
TTL_SYSTEM_ENABLED = True  # Global flag to enable/disable TTL filtering for markers
FORCE_RELOAD_TIMESTAMP = 0  # Timestamp when force reload was triggered
FORCE_RELOAD_DURATION = 120  # Duration in seconds to keep force reload active (2 minutes)
FORCE_RELOAD_LOCK = threading.Lock()
client = None
session_str = os.getenv('TELEGRAM_SESSION')  # Telethon string session (recommended for Render)
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # optional bot token fallback
AUTH_SECRET = os.getenv('AUTH_SECRET')  # simple shared secret to protect /auth endpoints
FETCH_THREAD_STARTED = False
FETCH_THREAD_STARTED_AT = 0
FETCH_THREAD = None
FETCH_START_DELAY = int(os.getenv('FETCH_START_DELAY', '0'))
AUTH_STATUS = {'authorized': False, 'reason': 'init'}
SUBSCRIBERS = set()  # queues for SSE clients
MAX_STREAM_SUBSCRIBERS = 100  # MEMORY PROTECTION: Limit main SSE connections (reduced from 200)
INIT_ONCE = False  # guard to ensure background startup once
# Persistent dynamic channels file
CHANNELS_FILE = 'channels_dynamic.json'

# Backfill progress tracking
BACKFILL_STATUS = {
    'in_progress': False,
    'started_at': None,
    'channels_done': 0,
    'channels_total': 0,
    'messages_processed': 0,
    'current_channel': None
}

# Global debug storage for admin panel
DEBUG_LOGS = []
MAX_DEBUG_LOGS = 10  # Reduced to save memory

# Cache for fallback reparse to avoid duplicate processing
FALLBACK_REPARSE_CACHE = set()  # message IDs that have been reparsed
MAX_REPARSE_CACHE_SIZE = 50  # Reduced to save memory (was 100)


def _normalize_platform(platform_hint: str, ua: str) -> str:
    """Map arbitrary client hints to canonical platform buckets."""
    candidate = (platform_hint or '').strip().lower()
    if candidate in VALID_PLATFORMS:
        return candidate

    ua_lower = (ua or '').lower()
    if 'android' in ua_lower:
        return 'android'
    if any(token in ua_lower for token in ('iphone', 'ipad', 'ios', 'cfnetwork')):
        return 'ios'
    return 'web'

def add_debug_log(message, category="general"):
    """Add debug message to global debug storage for admin panel."""
    global DEBUG_LOGS
    DEBUG_LOGS.append({
        'timestamp': datetime.now().isoformat(),
        'category': category,
        'message': str(message)
    })
    # Keep only recent logs
    if len(DEBUG_LOGS) > MAX_DEBUG_LOGS:
        DEBUG_LOGS = DEBUG_LOGS[-MAX_DEBUG_LOGS:]

# -------- Air alarm tracking (oblast / raion) --------
APP_ALARM_TTL_MINUTES = 65  # auto-expire if no update ~1h
ACTIVE_OBLAST_ALARMS = {}   # canonical oblast key -> {'since': epoch, 'last': epoch}
ACTIVE_RAION_ALARMS = {}    # raion base (lowercase) -> {'since': epoch, 'last': epoch}
RAION_ALARMS = {}           # Display/API raion alarm cache (separate from internal tracking)

# P-code mapping for ADM1 (області + special status cities)
OBLAST_PCODE = {
    'автономна республіка крим': 'UA01',
    'вінницька область': 'UA05',
    'волинська область': 'UA07',
    'дніпропетровська область': 'UA12',
    'донецька область': 'UA14',
    'житомирська область': 'UA18',
    'закарпатська область': 'UA21',
    'запорізька область': 'UA23',
    'івано-франківська область': 'UA26',
    'київська область': 'UA32',
    'кіровоградська область': 'UA35',
    'луганська область': 'UA44',
    'львівська область': 'UA46',
    'миколаївська область': 'UA48',
    'одеська область': 'UA51',
    'полтавська область': 'UA53',
    'рівненська область': 'UA56',
    'сумська область': 'UA59',
    'тернопільська область': 'UA61',
    'харківська область': 'UA63',
    'херсонська область': 'UA65',
    'хмельницька область': 'UA68',
    'черкаська область': 'UA71',
    'чернівецька область': 'UA73',
    'чернігівська область': 'UA74',
    'київ': 'UA80',
    'севастополь': 'UA85'
}

# ---- Alarm persistence (SQLite) ----
def log_alarm_event(level:str, name:str, event:str, ts=None):
    ts = ts or time.time()
    try:
        with _visits_db_conn() as conn:
            conn.execute("INSERT INTO alarm_events (id,level,name,event,ts) VALUES (?,?,?,?,?)",
                         (uuid.uuid4().hex[:12], level, name, event, ts))
    except Exception as e:
        log.debug(f"log_alarm_event failed: {e}")

def _alarm_key(level:str, name:str)->str:
    return f"{level}:{name}".lower()

def persist_alarm(level:str, name:str, since:float, last:float):
    try:
        with _visits_db_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO alarms (id,level,name,since,last) VALUES (?,?,?,?,?)",
                         (_alarm_key(level,name), level, name, since, last))
    except Exception as e:
        log.debug(f"persist_alarm failed: {e}")

def remove_alarm(level:str, name:str):
    try:
        with _visits_db_conn() as conn:
            conn.execute("DELETE FROM alarms WHERE id=?", (_alarm_key(level,name),))
    except Exception as e:
        log.debug(f"remove_alarm failed: {e}")

def load_dynamic_channels():
    try:
        if os.path.exists(CHANNELS_FILE):
            with open(CHANNELS_FILE,encoding='utf-8') as f:
                dyn = json.load(f)
            if isinstance(dyn, list):
                return [str(x).strip() for x in dyn if x]
    except Exception as e:
        log.warning(f'Failed loading {CHANNELS_FILE}: {e}')
    return []

def save_dynamic_channels(extra):
    try:
        with open(CHANNELS_FILE,'w',encoding='utf-8') as f:
            json.dump(extra, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f'Failed saving {CHANNELS_FILE}: {e}')

_dyn = load_dynamic_channels()
if _dyn:
    # Merge without duplicates
    base = [c.strip() for c in CHANNELS if c.strip()]
    for d in _dyn:
        if d not in base:
            base.append(d)
    CHANNELS = base
# ---------------- Monitoring period global config (admin editable) ----------------
CONFIG_FILE = 'config.json'
MONITOR_PERIOD_MINUTES = 30  # default; editable only via admin panel
MANUAL_MARKER_WINDOW_MINUTES = int(os.getenv('MANUAL_MARKER_WINDOW_MINUTES', '720'))  # manual markers stay visible at least 12h

# ---------------- Threat Tracker (simple stub) ----------------
class ThreatTracker:
    """Simple threat tracker for managing active threats"""
    def __init__(self):
        self.threats = {}
        self.region_to_threats = {}
    
    def cleanup_old_threats(self, max_age_hours=4):
        """Remove old threats"""
        pass
    
    def get_all_active_threats(self):
        """Get all active threats"""
        return []

THREAT_TRACKER = ThreatTracker()

def check_alarms_and_update_threats():
    """Update threat tracker based on alarm state"""
    pass

# ---------------- Channel Fusion (lightweight AI overlay) ----------------
class ChannelFusionStub:
    """Lightweight fusion container (AI overlays are computed from recent markers)."""
    def __init__(self):
        self.fused_events = {}
        self.message_to_event = {}
        self.lock = threading.Lock()
        self.CHANNEL_PRIORITY = {}

    def get_active_events(self):
        return []

    def cleanup_old_events(self, max_age_hours=4):
        return 0

CHANNEL_FUSION = ChannelFusionStub()

_FUSION_TRAJ_CACHE = {'time': 0, 'data': []}
_FUSION_CACHE_TTL = int(os.getenv('FUSION_CACHE_TTL', '10'))
_FUSION_MAX_TRAJ = int(os.getenv('FUSION_MAX_TRAJ', '150'))
_FUSION_WINDOW_MIN = int(os.getenv('FUSION_WINDOW_MIN', '90'))

def _project_point(lat: float, lng: float, bearing_deg: float, distance_km: float) -> tuple | None:
    try:
        from math import radians, degrees, sin, cos, asin, atan2
        r = 6371.0
        brng = radians(bearing_deg)
        d = distance_km / r
        lat1 = radians(lat)
        lon1 = radians(lng)
        lat2 = asin(sin(lat1) * cos(d) + cos(lat1) * sin(d) * cos(brng))
        lon2 = lon1 + atan2(sin(brng) * sin(d) * cos(lat1), cos(d) - sin(lat1) * sin(lat2))
        return (degrees(lat2), degrees(lon2))
    except Exception:
        return None

def _estimate_speed_kmh(threat_type: str | None) -> float:
    if not threat_type:
        return 150.0
    t = str(threat_type).lower()
    if t in ['shahed', 'drone', 'bpla']:
        return 160.0
    if t in ['cruise', 'raketa', 'missile']:
        return 700.0
    if t in ['ballistic']:
        return 2000.0
    if t in ['pusk', 'avia']:
        return 300.0
    return 180.0

def get_fused_trajectories():
    """Return AI-enhanced trajectories built from recent markers."""
    now_ts = time.time()
    cached = _FUSION_TRAJ_CACHE.get('data')
    if cached and (now_ts - _FUSION_TRAJ_CACHE.get('time', 0)) <= _FUSION_CACHE_TTL:
        return cached

    out = []
    seen = set()
    cutoff = datetime.now(pytz.timezone('Europe/Kyiv')).replace(tzinfo=None) - timedelta(minutes=_FUSION_WINDOW_MIN)

    for m in load_messages()[-800:]:
        if not isinstance(m, dict):
            continue
        try:
            dt = datetime.strptime(m.get('date', ''), '%Y-%m-%d %H:%M:%S')
        except Exception:
            continue
        if dt < cutoff:
            continue

        traj = m.get('trajectory') or m.get('enhanced_trajectory')
        start = traj.get('start') if isinstance(traj, dict) else None
        end = traj.get('end') if isinstance(traj, dict) else None

        if not (start and end):
            # AI fallback: project from course bearing if present
            bearing = m.get('course_bearing')
            if bearing is not None and m.get('lat') and m.get('lng'):
                projected = _project_point(float(m['lat']), float(m['lng']), float(bearing), 30)
                if projected:
                    start = [float(m['lat']), float(m['lng'])]
                    end = [projected[0], projected[1]]
                    traj = {'predicted': True, 'kind': 'ai_bearing_projection'}
        if not (start and end):
            continue

        # AI predicted path (time-based projection)
        predicted_path = None
        speed_kmh = None
        try:
            bearing = calculate_bearing(start[0], start[1], end[0], end[1])
            speed_kmh = (traj.get('speed_kmh') if isinstance(traj, dict) else None) or m.get('speed_kmh')
            if not speed_kmh:
                speed_kmh = _estimate_speed_kmh(m.get('threat_type') or (traj.get('threat_type') if isinstance(traj, dict) else None))
            if bearing is not None and speed_kmh:
                predicted_path = [end]
                for minutes in (10, 20, 30):
                    dist_km = speed_kmh * (minutes / 60.0)
                    pt = _project_point(end[0], end[1], bearing, dist_km)
                    if pt:
                        predicted_path.append([pt[0], pt[1]])
        except Exception:
            predicted_path = None

        event_id = str(m.get('id') or f"{start[0]}:{start[1]}->{end[0]}:{end[1]}")
        if event_id in seen:
            continue
        seen.add(event_id)

        out.append({
            'event_id': event_id,
            'threat_type': m.get('threat_type') or (traj.get('threat_type') if isinstance(traj, dict) else None),
            'actual_path': [start, end],
            'predicted_path': predicted_path,
            'confidence': (traj.get('confidence') if isinstance(traj, dict) else None) or m.get('prediction_confidence') or (0.6 if predicted_path else None),
            'distance_km': (traj.get('distance_km') if isinstance(traj, dict) else None) or m.get('distance_km'),
            'speed_kmh': (traj.get('speed_kmh') if isinstance(traj, dict) else None) or m.get('speed_kmh') or (speed_kmh if predicted_path else None),
            'eta': traj.get('eta') if isinstance(traj, dict) else None,
            'source_name': traj.get('source_name') if isinstance(traj, dict) else m.get('place'),
            'target_name': traj.get('target_name') if isinstance(traj, dict) else None,
        })

        if len(out) >= _FUSION_MAX_TRAJ:
            break

    _FUSION_TRAJ_CACHE['time'] = now_ts
    _FUSION_TRAJ_CACHE['data'] = out
    return out

def get_fused_markers():
    """Return markers with AI-related fields for optional frontend use."""
    return []

# ---------------- Ballistic threat state ----------------
BALLISTIC_THREAT_ACTIVE = False
BALLISTIC_THREAT_REGION = None
BALLISTIC_THREAT_TIMESTAMP = None

def add_system_chat_message(message_type, text, region=None, threat_type='ballistic'):
    """Add system message to chat about threats/alerts.

    message_type: 'threat_start' or 'threat_end'
    text: The alert message text
    region: Optional region name
    threat_type: 'ballistic', 'air', 'artillery', etc.
    """
    try:
        kyiv_tz = pytz.timezone('Europe/Kiev')
        now = datetime.now(kyiv_tz)

        # Load existing messages
        messages = load_chat_messages()
        
        # DEDUPE: Check if same message was added recently (last 5 minutes)
        text_short = text[:80]  # Compare first 80 chars
        five_min_ago = now.timestamp() - 300
        for m in messages[-50:]:  # Check last 50 messages
            if m.get('isSystem') and m.get('timestamp', 0) > five_min_ago:
                existing_text = (m.get('message') or '')[:80]
                if existing_text == text_short:
                    # Same message recently - skip
                    return
        
        # Create system message
        system_message = {
            'id': f'system_{uuid.uuid4()}',
            'userId': '⚠️ Система сповіщень',
            'deviceId': 'system',
            'message': text,
            'timestamp': now.timestamp(),
            'time': now.strftime('%H:%M'),
            'date': now.strftime('%d.%m.%Y'),
            'isSystem': True,  # Mark as system message
            'systemType': message_type,  # 'threat_start' or 'threat_end'
            'threatType': threat_type,
            'region': region
        }

        messages.append(system_message)
        save_chat_messages(messages)

        log.info(f'📢 Added system chat message: {message_type} - {text[:50]}...')
    except Exception as e:
        log.error(f'Error adding system chat message: {e}')

def update_ballistic_state(text, is_realtime=False):
    """Update ballistic threat state based on Telegram message text.

    Args:
        text: The message text to analyze
        is_realtime: If True, this is a live message (add to chat). If False, it's from backfill (don't add to chat)
    """
    global BALLISTIC_THREAT_ACTIVE, BALLISTIC_THREAT_REGION, BALLISTIC_THREAT_TIMESTAMP
    if not text:
        return
    text_lower = text.lower()

    # Detect ballistic threat activation
    if 'загроза балістики' in text_lower and 'відбій' not in text_lower:
        was_active = BALLISTIC_THREAT_ACTIVE
        BALLISTIC_THREAT_ACTIVE = True
        BALLISTIC_THREAT_TIMESTAMP = datetime.now().isoformat()
        # Try to extract region
        import re
        region_match = re.search(r'([\w\-]+(?:ська|ький|ка)\s*область)', text, re.IGNORECASE)
        if region_match:
            BALLISTIC_THREAT_REGION = region_match.group(1)
        else:
            BALLISTIC_THREAT_REGION = None
        log.info(f'🚀 BALLISTIC THREAT ACTIVATED: region={BALLISTIC_THREAT_REGION}, realtime={is_realtime}')

        # Add system message to chat ONLY for realtime (live) messages, not backfill
        if not was_active and is_realtime:
            region_text = f' ({BALLISTIC_THREAT_REGION})' if BALLISTIC_THREAT_REGION else ''
            add_system_chat_message(
                'threat_start',
                f'🚀 ЗАГРОЗА БАЛІСТИКИ{region_text}! Негайно в укриття!',
                BALLISTIC_THREAT_REGION,
                'ballistic'
            )
        return

    # Detect ballistic threat deactivation
    if 'відбій' in text_lower and ('балістик' in text_lower or 'загроз' in text_lower):
        was_active = BALLISTIC_THREAT_ACTIVE
        if BALLISTIC_THREAT_ACTIVE:
            log.info(f'✅ BALLISTIC THREAT DEACTIVATED, realtime={is_realtime}')
        BALLISTIC_THREAT_ACTIVE = False
        BALLISTIC_THREAT_REGION = None
        BALLISTIC_THREAT_TIMESTAMP = None

        # Add system message to chat ONLY for realtime (live) messages
        if was_active and is_realtime:
            add_system_chat_message(
                'threat_end',
                '✅ Відбій загрози балістики. Залишайтесь пильними.',
                None,
                'ballistic'
            )
        return

def add_telegram_message_to_chat(text, is_realtime=False):
    """Add important Telegram messages to chat as system notifications.

    Args:
        text: The message text from Telegram
        is_realtime: If True, add to chat. If False, skip (backfill)
    """
    if not text or not is_realtime:
        return

    text_lower = text.lower()

    # Skip if it's a ballistic message (handled separately by update_ballistic_state)
    if 'балістик' in text_lower:
        return

    # Detect threat type and format message
    message_type = None
    threat_type = None
    emoji = '⚠️'
    formatted_text = None
    region = None

    # Extract region from text
    region_match = RE_REGION_IN_TEXT.search(text)
    if region_match:
        region = region_match.group(1)
    else:
        region = _extract_oblast_from_text(text) or region

    # КАБи (Керовані авіабомби)
    if 'каб' in text_lower and 'відбій' not in text_lower:
        message_type = 'threat_start'
        threat_type = 'kab'
        emoji = '💣'
        # Extract short version
        if len(text) > 100:
            formatted_text = f'{emoji} КАБи: {text[:100]}...'
        else:
            formatted_text = f'{emoji} {text}'

    # Ракети / крилаті ракети
    elif ('ракет' in text_lower or 'крилат' in text_lower) and 'відбій' not in text_lower:
        message_type = 'threat_start'
        threat_type = 'rocket'
        emoji = '🚀'
        if len(text) > 100:
            formatted_text = f'{emoji} Ракети: {text[:100]}...'
        else:
            formatted_text = f'{emoji} {text}'

    # БПЛА / Дрони / Шахеди
    elif any(kw in text_lower for kw in ['бпла', 'дрон', 'шахед', 'безпілотн']) and 'відбій' not in text_lower:
        message_type = 'threat_start'
        threat_type = 'drone'
        emoji = '🛩️'
        if len(text) > 100:
            formatted_text = f'{emoji} БПЛА: {text[:100]}...'
        else:
            formatted_text = f'{emoji} {text}'

    # Вибухи
    elif 'вибух' in text_lower:
        message_type = 'threat_start'
        threat_type = 'explosion'
        emoji = '💥'
        if len(text) > 100:
            formatted_text = f'{emoji} Вибухи: {text[:100]}...'
        else:
            formatted_text = f'{emoji} {text}'

    # Відбій тривоги (загальний)
    elif 'відбій' in text_lower and ('тривог' in text_lower or 'загроз' in text_lower):
        message_type = 'threat_end'
        threat_type = 'all_clear'
        emoji = '✅'
        formatted_text = f'{emoji} Відбій: {text[:80]}' if len(text) > 80 else f'{emoji} {text}'

    # Тривога (загальна повітряна)
    elif 'тривог' in text_lower and 'повітрян' in text_lower and 'відбій' not in text_lower:
        message_type = 'threat_start'
        threat_type = 'air_alarm'
        emoji = '🚨'
        formatted_text = f'{emoji} {text[:100]}' if len(text) > 100 else f'{emoji} {text}'

    # If we detected something, add to chat
    if message_type and formatted_text:
        add_system_chat_message(
            message_type,
            formatted_text,
            region,
            threat_type
        )
        log.info(f'📢 Added Telegram message to chat: {threat_type} - {formatted_text[:50]}...')

def load_config():
    """Load persisted configuration (currently only monitor period)."""
    global MONITOR_PERIOD_MINUTES
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, encoding='utf-8') as f:
                cfg = json.load(f)
            # Validate range 1..360 else ignore
            mp = int(cfg.get('monitor_period', MONITOR_PERIOD_MINUTES))
            if 1 <= mp <= 360:
                MONITOR_PERIOD_MINUTES = mp
    except Exception as e:
        log.warning(f'Failed loading {CONFIG_FILE}: {e}')

def save_config():
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'monitor_period': MONITOR_PERIOD_MINUTES}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f'Failed saving {CONFIG_FILE}: {e}')

load_config()
if API_ID and API_HASH:
    if session_str:
        log.info('Initializing Telegram client with TELEGRAM_SESSION string.')
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    elif BOT_TOKEN:
        log.info('Initializing Telegram client with BOT token (limited access).')
        # Bot sessions auto-authorize on start
        client = TelegramClient(StringSession(), API_ID, API_HASH)
    else:
        log.info('Initializing Telegram client with local session file (may not persist on Render).')
        client = TelegramClient('anon', API_ID, API_HASH)
else:
    AUTH_STATUS.update({'authorized': False, 'reason': 'missing_api_credentials'})
    log.warning('Telegram API credentials missing (TELEGRAM_API_ID/TELEGRAM_API_HASH).')

# Use persistent disk on Render for data that should survive deploys
PERSISTENT_DATA_DIR = os.getenv('PERSISTENT_DATA_DIR', '/data')

# Log persistent storage status
log.info(f'PERSISTENT_DATA_DIR: {PERSISTENT_DATA_DIR}')
log.info(f'Directory exists: {os.path.isdir(PERSISTENT_DATA_DIR)}')

# Try to create the directory if it doesn't exist (Render disk should be mounted)
try:
    if PERSISTENT_DATA_DIR and not os.path.isdir(PERSISTENT_DATA_DIR):
        os.makedirs(PERSISTENT_DATA_DIR, exist_ok=True)
        log.info(f'Created directory: {PERSISTENT_DATA_DIR}')
except Exception as e:
    log.warning(f'Could not create persistent directory: {e}')

# Check again after attempting to create
if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR):
    MESSAGES_FILE = os.path.join(PERSISTENT_DATA_DIR, 'messages.json')
    CHAT_MESSAGES_FILE = os.path.join(PERSISTENT_DATA_DIR, 'chat_messages.json')
    HIDDEN_FILE = os.path.join(PERSISTENT_DATA_DIR, 'hidden_markers.json')
    COMMERCIAL_SUBSCRIPTIONS_FILE = os.path.join(PERSISTENT_DATA_DIR, 'commercial_subscriptions.json')
    STATS_FILE = os.path.join(PERSISTENT_DATA_DIR, 'visits_stats.json')
    RECENT_VISITS_FILE = os.path.join(PERSISTENT_DATA_DIR, 'visits_recent.json')
    log.info(f'Using PERSISTENT storage: {CHAT_MESSAGES_FILE}')
else:
    # Fallback to local files (for development)
    MESSAGES_FILE = 'messages.json'
    CHAT_MESSAGES_FILE = 'chat_messages.json'  # Anonymous chat messages
    HIDDEN_FILE = 'hidden_markers.json'
    COMMERCIAL_SUBSCRIPTIONS_FILE = 'commercial_subscriptions.json'
    STATS_FILE = 'visits_stats.json'
    RECENT_VISITS_FILE = 'visits_recent.json'
    log.warning(f'Using LOCAL storage (will be lost on redeploy): {CHAT_MESSAGES_FILE}')
OPENCAGE_CACHE_FILE = 'opencage_cache.json'
OPENCAGE_TTL = 60 * 60 * 24 * 30  # 30 days
NEG_GEOCODE_FILE = 'negative_geocode_cache.json'
NEG_GEOCODE_TTL = 60 * 60 * 24 * 3  # 3 days for 'not found' entries
MESSAGES_RETENTION_MINUTES = int(os.getenv('MESSAGES_RETENTION_MINUTES', '360'))  # 6 hours retention (reduced from 12h to save memory)
MESSAGES_MAX_COUNT = int(os.getenv('MESSAGES_MAX_COUNT', '100'))  # Default limit 100 to prevent memory issues (reduced from 150)

def _startup_diagnostics():
    """Log one-time startup diagnostics to help investigate early exit issues on hosting platforms."""
    try:
        log.info('--- Startup diagnostics begin ---')
        log.info(f'Python: {sys.version.split()[0]} Platform: {platform.platform()} PID: {os.getpid()}')
        log.info(f'Flask version: {getattr(sys.modules.get("flask"), "__version__", "?")} Telethon version: {getattr(sys.modules.get("telethon"), "__version__", "?")}')
        log.info(f'Configured channels ({len(CHANNELS)}): {CHANNELS}')
        log.info(f'API_ID set: {bool(API_ID)} HASH set: {bool(API_HASH)} SESSION len: {len(session_str) if session_str else 0}')
        log.info(f'GOOGLE_MAPS_KEY set: {bool(GOOGLE_MAPS_KEY)} OPENCAGE_API_KEY set: {bool(OPENCAGE_API_KEY)}')
        if os.path.exists(MESSAGES_FILE):
            try:
                sz = os.path.getsize(MESSAGES_FILE)
                log.info(f'{MESSAGES_FILE} exists size={sz} bytes')
            except Exception:
                pass
        else:
            log.info(f'{MESSAGES_FILE} not present yet.')
        log.info(f'Retention minutes: {MESSAGES_RETENTION_MINUTES} Max count: {MESSAGES_MAX_COUNT}')
        log.info(f'FETCH_START_DELAY={os.getenv("FETCH_START_DELAY", "0")}')
        log.info('--- Startup diagnostics end ---')
    except Exception as e:
        log.warning(f'Diagnostics error: {e}')

def _prune_messages(data):
    """Apply retention policies (time / count). Mutates and returns list."""
    if not data:
        return data
    # Time based pruning
    if MESSAGES_RETENTION_MINUTES > 0:
        cutoff = datetime.utcnow() - timedelta(minutes=MESSAGES_RETENTION_MINUTES)
        pruned = []
        for m in data:
            if m.get('manual'):
                pruned.append(m)
                continue
            try:
                dt = datetime.strptime(m.get('date',''), '%Y-%m-%d %H:%M:%S')
            except Exception:
                # keep malformed to avoid data loss
                pruned.append(m)
                continue
            if dt.replace(tzinfo=None) >= cutoff:
                pruned.append(m)
        data = pruned
    # Count based pruning (keep newest by date)
    if MESSAGES_MAX_COUNT > 0 and len(data) > MESSAGES_MAX_COUNT:
        try:
            manual_items = [m for m in data if m.get('manual')]
            auto_items = [m for m in data if not m.get('manual')]
            allow_auto = max(0, MESSAGES_MAX_COUNT - len(manual_items))
            if len(auto_items) > allow_auto:
                auto_items = sorted(auto_items, key=lambda x: x.get('date',''))[-allow_auto:]
            combined = manual_items + auto_items
            data = sorted(combined, key=lambda x: x.get('date',''))
        except Exception:
            data = data[-MESSAGES_MAX_COUNT:]
    return data


MESSAGE_STORE = MessageStore(
    MESSAGES_FILE,
    prune_fn=_prune_messages,
    preserve_manual=True,
    backup_count=3,
)

# Cache for sent FCM notifications to prevent duplicates
# Format: {notification_hash: timestamp}
SENT_NOTIFICATIONS_CACHE = {}
NOTIFICATION_CACHE_TTL = 120  # 2 minutes
NOTIFICATION_CACHE_MAX_SIZE = 50  # MEMORY: Reduced to 50

def _normalize_location_name(name: str) -> str:
    """Normalize location name for deduplication - remove common suffixes/prefixes."""
    if not name:
        return ''
    name = name.lower().strip()
    # Remove common suffixes
    suffixes = [' район', ' область', ' громада', ' міська', ' селищна', ' сільська',
                ' (міська)', ' (районна)', ' (обласна)', 'ська', 'ський']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.strip()

def _get_notification_hash(msg: dict) -> str:
    """Generate a unique hash for a notification based on content.
    Uses location name + threat type only (ignores coordinates) for better deduplication.
    """
    import hashlib
    # Use place + threat_type as unique key (ignore coordinates for better dedup)
    place = (msg.get('place', '') or msg.get('location', '') or '')[:100]
    place = _normalize_location_name(place)

    msg_type = (msg.get('threat_type', '') or msg.get('type', '') or '')[:50].lower()

    # Normalize threat type to category
    if 'бпла' in msg_type or 'дрон' in msg_type or 'шахед' in msg_type:
        msg_type = 'drone'
    elif 'ракет' in msg_type or 'балістичн' in msg_type or 'крилат' in msg_type:
        msg_type = 'rocket'
    elif 'каб' in msg_type or 'бомб' in msg_type:
        msg_type = 'kab'
    elif 'відбій' in msg_type or 'знято' in msg_type:
        msg_type = 'clear'
    else:
        msg_type = 'alert'

    content = f"{place}|{msg_type}"
    return hashlib.md5(content.encode()).hexdigest()

def _should_send_notification(msg: dict) -> bool:
    """Check if notification should be sent (not a duplicate)."""
    global SENT_NOTIFICATIONS_CACHE

    msg_hash = _get_notification_hash(msg)
    now = time.time()

    # Clean old entries from cache
    SENT_NOTIFICATIONS_CACHE = {
        h: t for h, t in SENT_NOTIFICATIONS_CACHE.items()
        if now - t < NOTIFICATION_CACHE_TTL
    }
    
    # MEMORY PROTECTION: Enforce max size limit
    if len(SENT_NOTIFICATIONS_CACHE) > NOTIFICATION_CACHE_MAX_SIZE:
        # Keep only the newest entries
        sorted_items = sorted(SENT_NOTIFICATIONS_CACHE.items(), key=lambda x: x[1], reverse=True)
        SENT_NOTIFICATIONS_CACHE = dict(sorted_items[:NOTIFICATION_CACHE_MAX_SIZE // 2])

    if msg_hash in SENT_NOTIFICATIONS_CACHE:
        log.info(f"Skipping duplicate notification (hash: {msg_hash[:8]}...)")
        return False

    # Mark as sent
    SENT_NOTIFICATIONS_CACHE[msg_hash] = now
    return True

def load_messages():
    # HIGH-LOAD: Use cached version to reduce disk I/O
    return load_messages_cached()


def save_messages(data, send_notifications=True):
    try:
        # Invalidate cache on save
        invalidate_messages_cache()

        # Check for new messages to send notifications
        existing = MESSAGE_STORE.load()
        existing_ids = {msg.get('id') for msg in existing}
        new_messages = [msg for msg in data if msg.get('id') and msg.get('id') not in existing_ids]

        if new_messages:
            log.info(f"Found {len(new_messages)} new messages to process for notifications")

            # === INCREMENT ALARM STATISTICS (persistent) ===
            for msg in new_messages:
                try:
                    # Get region from message
                    region = msg.get('region') or msg.get('location', '')
                    if region:
                        increment_alarm_stat(region)
                except Exception as e:
                    log.debug(f"Failed to increment alarm stat: {e}")

            # === MULTI-CHANNEL FUSION: Process new messages ===
            for msg in new_messages:
                try:
                    fusion_result = process_message_with_fusion(msg)
                    if fusion_result:
                        log.info(f"[FUSION] {fusion_result['action']} event {fusion_result['event_id']}")
                except Exception as e:
                    log.debug(f"Fusion system error: {e}")

            # === THREAT TRACKER: Process new messages ===
            for msg in new_messages:
                try:
                    result = process_message_for_threats(msg)
                    if result:
                        log.debug(f"Threat tracker: {result['action']} threat {result['threat_id']}")
                except Exception as e:
                    log.debug(f"Threat tracker error: {e}")

        saved = MESSAGE_STORE.save(data)

        # Send FCM notifications for new messages (with deduplication)
        if send_notifications:
            # Get current Kyiv time for freshness check
            kyiv_tz = pytz.timezone('Europe/Kyiv')
            now_kyiv = datetime.now(kyiv_tz)
            max_age_minutes = 5  # Only send notifications for messages less than 5 minutes old

            for msg in new_messages:
                # Skip messages that should NOT trigger notifications:
                # 1. Manual markers
                # 2. Messages without coordinates (pending_geo or no lat/lng)
                # 3. Messages without threat_type/type
                # 4. Old messages (more than 5 minutes old)
                if msg.get('manual'):
                    log.debug(f"Skipping FCM for manual marker: {msg.get('id')}")
                    continue

                # Check for coordinates - field names may vary
                lat = msg.get('lat') or msg.get('latitude')
                lng = msg.get('lng') or msg.get('longitude')
                if msg.get('pending_geo') or not lat or not lng:
                    log.debug(f"Skipping FCM for message without coordinates: {msg.get('id')}")
                    continue

                if not msg.get('threat_type') and not msg.get('type'):
                    log.debug(f"Skipping FCM for message without threat type: {msg.get('id')}")
                    continue

                # Check message age - skip old messages
                # Try multiple date formats: 'timestamp', 'date'
                msg_date = msg.get('timestamp') or msg.get('date', '')
                if msg_date:
                    try:
                        # Try different date formats
                        msg_time = None
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M', '%d.%m.%Y']:
                            try:
                                msg_time = datetime.strptime(msg_date, fmt)
                                break
                            except ValueError:
                                continue

                        if msg_time:
                            msg_time = kyiv_tz.localize(msg_time)
                            age_minutes = (now_kyiv - msg_time).total_seconds() / 60

                            if age_minutes > max_age_minutes:
                                log.info(f"Skipping FCM for old message ({age_minutes:.1f} min old): {msg.get('location', 'unknown')}")
                                continue
                            log.info(f"Message is fresh ({age_minutes:.1f} min old), sending notification")
                        else:
                            log.warning(f"Could not parse message date '{msg_date}' with any format")
                            continue
                    except Exception as e:
                        log.warning(f"Error parsing message date '{msg_date}': {e}")
                        continue
                else:
                    log.debug("Message has no timestamp, skipping FCM")
                    continue

                # Check if this notification was already sent recently
                if not _should_send_notification(msg):
                    log.info(f"Skipping duplicate FCM for: {msg.get('location', 'unknown')}")
                    continue
                try:
                    location = msg.get('place') or msg.get('location') or ''
                    threat = msg.get('threat_type') or msg.get('type') or 'загроза'
                    log.info(f"Sending FCM for message: {location} - {threat}")
                    send_fcm_notification(msg)
                except Exception as e:
                    log.error(f"Failed to send FCM notification: {e}")
    except Exception as exc:
        log.error('Failed to persist messages: %s', exc)
        saved = data
    else:
        print(f"DEBUG: Saving {len(saved)} messages to file")
    # After each save attempt optional git auto-commit
    try:
        maybe_git_autocommit()
    except Exception as e:
        log.debug(f'git auto-commit skipped: {e}')
    return saved

# ---------------- Deduplication / merge of near-duplicate geo events -----------------
# Two messages that refer to the same object coming almost back-to-back should not
# produce two separate points: instead we update the earlier one (increment count, merge text).
# Heuristics: same threat_type, within DEDUP_DIST_KM km, within DEDUP_TIME_MIN minutes.
# DISABLED: Now showing all messages as separate points with small offset
DEDUP_ENABLED = False  # Set to True to enable merging
DEDUP_TIME_MIN = int(os.getenv('DEDUP_TIME_MIN', '5'))
DEDUP_DIST_KM = float(os.getenv('DEDUP_DIST_KM', '7'))
DEDUP_SCAN_BACK = int(os.getenv('DEDUP_SCAN_BACK', '400'))  # how many recent messages to scan

def _parse_dt(s:str):
    try:
        return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None

def _haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate distance in km between two points.
    Wrapper around haversine() for (lat, lon, lat, lon) signature.
    
    NOTE: Prefer using haversine((lat1,lon1), (lat2,lon2)) directly.
    This function exists for backward compatibility.
    """
    try:
        return haversine((lat1, lon1), (lat2, lon2))
    except Exception:
        return 999999

def maybe_merge_track(all_data:list, new_track:dict):
    """Try to merge new_track into an existing recent track.
    Returns tuple (merged: bool, track_ref: dict).

    If DEDUP_ENABLED is False, adds small random offset to prevent overlapping.
    """
    import random

    # If dedup disabled, add small offset and return as new track
    if not DEDUP_ENABLED:
        lat = new_track.get('lat')
        lng = new_track.get('lng')
        if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
            # Add small random offset (about 500m-1.5km)
            offset_lat = random.uniform(-0.012, 0.012)
            offset_lng = random.uniform(-0.015, 0.015)
            new_track['lat'] = lat + offset_lat
            new_track['lng'] = lng + offset_lng
        return False, new_track

    try:
        if not all_data:
            return False, new_track
        tt = (new_track.get('threat_type') or '').lower()
        if not tt:
            return False, new_track
        lat = new_track.get('lat'); lng = new_track.get('lng')
        if not isinstance(lat, (int,float)) or not isinstance(lng, (int,float)):
            return False, new_track
        new_dt = _parse_dt(new_track.get('date','')) or datetime.utcnow()
        # Scan recent slice only for performance
        scan_slice = all_data[-DEDUP_SCAN_BACK:]
        # Iterate reversed (newest first)
        for existing in reversed(scan_slice):
            if existing is new_track:  # shouldn't happen yet
                continue
            if (existing.get('threat_type') or '').lower() != tt:
                continue
            e_lat = existing.get('lat'); e_lng = existing.get('lng')
            if not isinstance(e_lat,(int,float)) or not isinstance(e_lng,(int,float)):
                continue
            dist = _haversine_km(lat,lng,e_lat,e_lng)
            if dist > DEDUP_DIST_KM:
                continue
            e_dt = _parse_dt(existing.get('date','')) or new_dt
            dt_min = abs((new_dt - e_dt).total_seconds())/60.0
            if dt_min > DEDUP_TIME_MIN:
                continue
            # Merge
            # Increment count
            existing['count'] = int(existing.get('count') or 1) + 1
            # Merge text (avoid duplication / uncontrolled growth)
            new_text = (new_track.get('text') or '').strip()
            if new_text:
                ex_text = existing.get('text') or ''
                if new_text not in ex_text:
                    combined = (ex_text + ' | ' + new_text).strip(' |') if ex_text else new_text
                    if len(combined) > 800:
                        combined = combined[:790] + '…'
                    existing['text'] = combined
            # Maintain list of merged ids
            if 'merged_ids' not in existing:
                existing['merged_ids'] = [existing.get('id')]
            nid = new_track.get('id')
            if nid and nid not in existing['merged_ids']:
                existing['merged_ids'].append(nid)
            # Update displayed date to the most recent
            if new_dt >= e_dt:
                existing['date'] = new_track.get('date') or existing.get('date')
            # Optionally capture first occurrence time
            if 'first_date' not in existing:
                existing['first_date'] = e_dt.strftime('%Y-%m-%d %H:%M:%S')
            existing['merged'] = True
            return True, existing
    except Exception as e:
        log.debug(f'dedup merge error: {e}')
    return False, new_track


# ---------------- SQL/Stats stub functions ----------------
def _seed_recent_from_sql():
    """Seed recent visits from SQL - stub"""
    pass

def _active_sessions_from_db(ttl):
    """Get active sessions from DB - stub, returns empty dict"""
    return {}

def sql_unique_counts():
    """Get unique visitor counts from SQLite database (thread-safe, survives deploys)."""
    try:
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            cursor = conn.cursor()
            
            # Ensure table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visitor_log (
                    visitor_id TEXT NOT NULL,
                    visit_date TEXT NOT NULL,
                    created_at REAL DEFAULT (strftime('%s', 'now')),
                    PRIMARY KEY (visitor_id, visit_date)
                )
            """)
            conn.commit()
            
            tz = pytz.timezone('Europe/Kyiv')
            now_dt = datetime.now(tz)
            today = now_dt.strftime('%Y-%m-%d')
            week_ago = (now_dt - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Count unique visitors today
            cursor.execute("SELECT COUNT(DISTINCT visitor_id) FROM visitor_log WHERE visit_date = ?", (today,))
            daily = cursor.fetchone()[0] or 0
            
            # Count unique visitors in last 7 days
            cursor.execute("SELECT COUNT(DISTINCT visitor_id) FROM visitor_log WHERE visit_date >= ?", (week_ago,))
            weekly = cursor.fetchone()[0] or 0
            
            return daily, weekly
        finally:
            conn.close()
    except Exception as e:
        log.warning(f"sql_unique_counts error: {e}")
        return None, None

def sql_record_visit(visitor_id: str):
    """Record visitor in SQLite (thread-safe, prevents race conditions)."""
    if not visitor_id:
        return
    try:
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            cursor = conn.cursor()
            
            # Ensure table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visitor_log (
                    visitor_id TEXT NOT NULL,
                    visit_date TEXT NOT NULL,
                    created_at REAL DEFAULT (strftime('%s', 'now')),
                    PRIMARY KEY (visitor_id, visit_date)
                )
            """)
            
            tz = pytz.timezone('Europe/Kyiv')
            today = datetime.now(tz).strftime('%Y-%m-%d')
            
            # INSERT OR IGNORE - no duplicates, thread-safe
            cursor.execute(
                "INSERT OR IGNORE INTO visitor_log (visitor_id, visit_date) VALUES (?, ?)",
                (visitor_id, today)
            )
            conn.commit()
            
            # Cleanup old entries (older than 30 days) - run occasionally
            import random
            if random.random() < 0.01:  # 1% chance
                cutoff = (datetime.now(tz) - timedelta(days=30)).strftime('%Y-%m-%d')
                cursor.execute("DELETE FROM visitor_log WHERE visit_date < ?", (cutoff,))
                conn.commit()
        finally:
            conn.close()
    except Exception as e:
        log.warning(f"sql_record_visit error: {e}")

def get_redirect_stats():
    """Get redirect statistics - stub"""
    return {}


# ── Cached load_hidden / load_blocked (avoid disk I/O on every /data request) ──
_hidden_cache = {'data': None, 'ts': 0}
_blocked_cache = {'data': None, 'ts': 0}
_HIDDEN_BLOCKED_CACHE_TTL = 30  # seconds

def load_hidden():
    now = time.time()
    if _hidden_cache['data'] is not None and now - _hidden_cache['ts'] < _HIDDEN_BLOCKED_CACHE_TTL:
        return _hidden_cache['data']
    if os.path.exists(HIDDEN_FILE):
        try:
            with open(HIDDEN_FILE, encoding='utf-8') as f:
                result = json.load(f)
            _hidden_cache['data'] = result
            _hidden_cache['ts'] = now
            return result
        except Exception:
            return []
    return []

def save_hidden(data):
    with open(HIDDEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _hidden_cache['data'] = data
    _hidden_cache['ts'] = time.time()

def load_blocked():
    now = time.time()
    if _blocked_cache['data'] is not None and now - _blocked_cache['ts'] < _HIDDEN_BLOCKED_CACHE_TTL:
        return _blocked_cache['data']
    if os.path.exists(BLOCKED_FILE):
        try:
            with open(BLOCKED_FILE, encoding='utf-8') as f:
                result = json.load(f)
            _blocked_cache['data'] = result
            _blocked_cache['ts'] = now
            return result
        except Exception:
            return []
    return []

def save_blocked(blocked):
    try:
        with open(BLOCKED_FILE, 'w', encoding='utf-8') as f:
            json.dump(blocked, f, ensure_ascii=False, indent=2)
        _blocked_cache['data'] = blocked
        _blocked_cache['ts'] = time.time()
    except Exception as e:
        log.warning(f'Failed saving {BLOCKED_FILE}: {e}')

def _load_visit_stats():
    global VISIT_STATS
    if VISIT_STATS is not None:
        return VISIT_STATS
    if os.path.exists(STATS_FILE):
        try:
            # Check file size - if too big, reset to save memory
            file_size = os.path.getsize(STATS_FILE)
            if file_size > 500_000:  # 500KB max
                log.warning(f"visit_stats file too large ({file_size} bytes), resetting")
                VISIT_STATS = {}
                _save_visit_stats()
                return VISIT_STATS
            with open(STATS_FILE,encoding='utf-8') as f:
                VISIT_STATS = json.load(f)
            # Immediately prune if too many entries
            if len(VISIT_STATS) > 2000:
                log.warning(f"visit_stats has {len(VISIT_STATS)} entries, pruning to 2000")
                sorted_items = sorted(VISIT_STATS.items(), key=lambda x: float(x[1]) if isinstance(x[1], (int, float, str)) else 0, reverse=True)
                VISIT_STATS = dict(sorted_items[:2000])
                _save_visit_stats()
        except Exception:
            VISIT_STATS = {}
    else:
        VISIT_STATS = {}
    return VISIT_STATS

def _save_visit_stats():
    if VISIT_STATS is None:
        return
    # Use thread-safe copy to prevent 'dictionary changed size during iteration'
    with _visit_stats_lock:
        stats_copy = dict(VISIT_STATS)
    try:
        with open(STATS_FILE,'w',encoding='utf-8') as f:
            json.dump(stats_copy, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f'Failed saving {STATS_FILE}: {e}')

def _prune_visit_stats(days:int=3, max_entries:int=2000):
    # remove entries older than N days - reduced to 3 days to save memory
    # Also limit total entries to max_entries
    if VISIT_STATS is None:
        return
    cutoff = time.time() - days*86400
    removed = 0
    for vid, ts in list(VISIT_STATS.items()):
        try:
            if float(ts) < cutoff:
                del VISIT_STATS[vid]
                removed += 1
        except Exception:
            continue
    
    # If still over limit, remove oldest entries
    if len(VISIT_STATS) > max_entries:
        sorted_items = sorted(VISIT_STATS.items(), key=lambda x: float(x[1]) if isinstance(x[1], (int, float, str)) else 0)
        to_remove = len(VISIT_STATS) - max_entries
        for vid, _ in sorted_items[:to_remove]:
            del VISIT_STATS[vid]
            removed += 1
    
    if removed:
        _save_visit_stats()

# ---- Rolling daily / weekly visit tracking (for persistence of counts across deploys) ----
def _load_recent_visits():
    with _recent_visits_lock:
        try:
            if os.path.exists(RECENT_VISITS_FILE):
                # Check file size first - reset if too large
                try:
                    file_size = os.path.getsize(RECENT_VISITS_FILE)
                    if file_size > 200_000:  # 200KB max
                        log.warning(f"recent_visits file too large ({file_size} bytes), resetting")
                        return {}
                except:
                    pass
                # Guard against oversized/corrupted file (e.g. concurrent writes producing concatenated JSON objects)
                try:
                    raw = open(RECENT_VISITS_FILE, encoding='utf-8').read()
                except Exception as e_read:
                    log.warning(f"Failed reading {RECENT_VISITS_FILE}: {e_read}")
                    return {}
                # Quick heuristic: if multiple top-level JSON objects concatenated, keep first valid
                data = None
                if raw.strip():
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError as je:
                        # Try to split by newlines and stitch until first valid JSON object
                        fragments = raw.splitlines()
                        buf = ''
                        for line in fragments:
                            buf += line.strip() + '\n'
                            try:
                                data = json.loads(buf)
                                log.warning(f"Recovered first valid JSON segment from {RECENT_VISITS_FILE} after decode error: {je}")
                                break
                            except Exception:
                                continue
                        if data is None:
                            log.warning(f"Unable to repair {RECENT_VISITS_FILE}: {je}")
                            return {}
                    except Exception as e_generic:
                        log.warning(f"Generic JSON load failure {RECENT_VISITS_FILE}: {e_generic}")
                        return {}
                else:
                    return {}
                if not isinstance(data, dict):
                    log.warning(f"Unexpected structure in {RECENT_VISITS_FILE}, resetting")
                    return {}
                data.setdefault('day', '')
                data.setdefault('week_start', '')
                data.setdefault('today_ids', [])
                data.setdefault('week_ids', [])
                return data
        except Exception as e:
            log.warning(f"Failed loading {RECENT_VISITS_FILE}: {e}")
        return {}

def _save_recent_visits(data:dict):
    with _recent_visits_lock:
        try:
            # Make a safe copy to avoid modification during serialization
            data_copy = {
                'day': data.get('day', ''),
                'week_start': data.get('week_start', ''),
                'today_ids': list(data.get('today_ids', [])),
                'week_ids': list(data.get('week_ids', []))
            }
            tmp = RECENT_VISITS_FILE + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data_copy, f, ensure_ascii=False, indent=2)
            try:
                os.replace(tmp, RECENT_VISITS_FILE)
            except FileNotFoundError:
                # Rare race on some FS / AV scanners: fall back to simple write
                try:
                    with open(RECENT_VISITS_FILE, 'w', encoding='utf-8') as f2:
                        json.dump(data_copy, f2, ensure_ascii=False, indent=2)
                except Exception as e2:
                    log.warning(f"Fallback direct save failed {RECENT_VISITS_FILE}: {e2}")
        except Exception as e:
            log.warning(f"Failed saving {RECENT_VISITS_FILE}: {e}")

def _update_recent_visits(vid:str):
    """Update rolling daily/week sets with visitor id. Uses Europe/Kyiv timezone.
    This offers stable daily/week unique counts even if the broader first-seen file is lost on redeploy."""
    if not vid:
        return
    data = _load_recent_visits() or {}
    tz = pytz.timezone('Europe/Kyiv')
    now_dt = datetime.now(tz)
    today = now_dt.strftime('%Y-%m-%d')
    
    # Week window: 7-day rolling window from week_start
    stored_week_start = data.get('week_start') or today
    try:
        sw_dt = datetime.strptime(stored_week_start, '%Y-%m-%d')
        sw_dt = tz.localize(sw_dt)
    except Exception:
        sw_dt = now_dt
    
    # If week window expired (7+ days), reset week
    if (now_dt - sw_dt).days >= 7:
        stored_week_start = today
        data['week_ids'] = []
        data['week_start'] = stored_week_start
    
    # Day rollover - reset today_ids but KEEP week_ids!
    if data.get('day') != today:
        data['day'] = today
        data['today_ids'] = []
        # DON'T reset week_ids here - they accumulate for 7 days
    
    # Ensure lists exist
    if 'today_ids' not in data or not isinstance(data['today_ids'], list):
        data['today_ids'] = []
    if 'week_ids' not in data or not isinstance(data['week_ids'], list):
        data['week_ids'] = []
    
    # Add visitor to both lists if not already present
    if vid not in data['today_ids']:
        data['today_ids'].append(vid)
    if vid not in data['week_ids']:
        data['week_ids'].append(vid)
    
    data['week_start'] = stored_week_start
    _save_recent_visits(data)

def _recent_counts():
    data = _load_recent_visits()
    if not data:
        return None, None
    return len(set(data.get('today_ids', []))), len(set(data.get('week_ids', [])))

# Simplified message processor placeholder
import sqlite3
from contextlib import contextmanager

# ---- SQLite Database Connection (persistent storage in /data) ----
# Path to SQLite database - use persistent storage if available
_DB_PATH = None

def _get_db_path():
    """Get path to SQLite database, preferring persistent storage."""
    global _DB_PATH
    if _DB_PATH is not None:
        return _DB_PATH
    
    # Try persistent directory first
    if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR):
        _DB_PATH = os.path.join(PERSISTENT_DATA_DIR, 'neptun.db')
    else:
        # Fallback to local directory
        _DB_PATH = 'neptun.db'
    
    return _DB_PATH

@contextmanager
def _visits_db_conn():
    """Context manager for SQLite database connections."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ---- Alarm Statistics Table (persistent across deploys) ----
def init_alarm_stats_db():
    """Initialize alarm_stats table for persistent statistics."""
    try:
        with _visits_db_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alarm_stats (
                    date TEXT NOT NULL,
                    region TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    PRIMARY KEY (date, region)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alarm_stats_date ON alarm_stats(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alarm_stats_region ON alarm_stats(region)")
            log.info("alarm_stats table initialized")
    except Exception as e:
        log.warning(f"alarm_stats db init failed: {e}")

def increment_alarm_stat(region: str):
    """Increment alarm counter for today and given region."""
    today = datetime.now(pytz.timezone('Europe/Kyiv')).strftime('%Y-%m-%d')
    try:
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            # Use UPSERT to increment counter
            conn.execute("""
                INSERT INTO alarm_stats (date, region, count) VALUES (?, ?, 1)
                ON CONFLICT(date, region) DO UPDATE SET count = count + 1
            """, (today, region))
            conn.commit()
            log.info(f"[ALARM_STAT] Incremented: {region} on {today}, db={db_path}")
        finally:
            conn.close()
    except Exception as e:
        log.error(f"[ALARM_STAT] increment_alarm_stat FAILED: {e}")

def get_alarm_stats_from_db(region: str) -> dict:
    """Get alarm statistics from database for given region."""
    kyiv_tz = pytz.timezone('Europe/Kyiv')
    now = datetime.now(kyiv_tz)
    today = now.strftime('%Y-%m-%d')
    week_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d')
    month_ago = (now - timedelta(days=30)).strftime('%Y-%m-%d')
    
    today_count = 0
    week_count = 0
    month_count = 0
    
    try:
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path, timeout=30)
        try:
            # Today
            cur = conn.execute(
                "SELECT COALESCE(SUM(count), 0) FROM alarm_stats WHERE region LIKE ? AND date = ?",
                (f'%{region}%', today)
            )
            today_count = cur.fetchone()[0] or 0
            
            # Week
            cur = conn.execute(
                "SELECT COALESCE(SUM(count), 0) FROM alarm_stats WHERE region LIKE ? AND date >= ?",
                (f'%{region}%', week_ago)
            )
            week_count = cur.fetchone()[0] or 0
            
            # Month
            cur = conn.execute(
                "SELECT COALESCE(SUM(count), 0) FROM alarm_stats WHERE region LIKE ? AND date >= ?",
                (f'%{region}%', month_ago)
            )
            month_count = cur.fetchone()[0] or 0
            
            log.info(f"[ALARM_STAT] Read stats for {region}: today={today_count}, week={week_count}, month={month_count}, db={db_path}")
        finally:
            conn.close()
            
    except Exception as e:
        log.error(f"[ALARM_STAT] get_alarm_stats_from_db FAILED: {e}")
    
    return {
        'today_alarms': today_count,
        'week_alarms': week_count,
        'month_alarms': month_count
    }

# Initialize alarm stats DB on import
try:
    init_alarm_stats_db()
except Exception as e:
    log.warning(f"Failed to init alarm_stats on import: {e}")

_opencage_cache = None
_neg_geocode_cache = None
_mapstransler_geocode_cache = {}  # In-memory cache for mapstransler geocoding
_mapstransler_cache_max_size = 50  # MEMORY: Reduced to 50

def _load_opencage_cache():
    global _opencage_cache
    if _opencage_cache is not None:
        return _opencage_cache
    if os.path.exists(OPENCAGE_CACHE_FILE):
        try:
            with open(OPENCAGE_CACHE_FILE, encoding='utf-8') as f:
                _opencage_cache = json.load(f)
        except Exception:
            _opencage_cache = {}
    else:
        _opencage_cache = {}
    return _opencage_cache

def _save_opencage_cache():
    if _opencage_cache is None:
        return
    try:
        # Limit cache size to prevent memory issues
        cache_to_save = _opencage_cache
        if len(_opencage_cache) > 500:  # Reduced from 1000
            # Keep only the 500 most recent entries (approximate)
            items = list(_opencage_cache.items())
            cache_to_save = dict(items[-500:])
        with open(OPENCAGE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f"Failed saving OpenCage cache: {e}")

def geocode_opencage(query: str):
    """
    Geocode a place name using OpenCage API with caching.
    Returns (lat, lng) tuple or None if not found.
    """
    if not OPENCAGE_API_KEY or not query:
        return None
    
    query = query.strip()
    if not query:
        return None
    
    # Check cache first
    cache = _load_opencage_cache()
    cache_key = query.lower()
    if cache_key in cache:
        entry = cache[cache_key]
        # Check TTL
        if time.time() - entry.get('ts', 0) < OPENCAGE_TTL:
            coords = entry.get('coords')
            if coords:
                return tuple(coords)
            return None
    
    # Call OpenCage API
    try:
        url = 'https://api.opencagedata.com/geocode/v1/json'
        params = {
            'q': f"{query}, Ukraine",
            'key': OPENCAGE_API_KEY,
            'limit': 1,
            'no_annotations': 1,
            'countrycode': 'ua',
            'language': 'uk'
        }
        resp = http_requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', [])
            if results:
                geo = results[0].get('geometry', {})
                lat = geo.get('lat')
                lng = geo.get('lng')
                if lat and lng:
                    # Validate Ukraine bounds
                    if 43.0 <= lat <= 53.8 and 20.0 <= lng <= 42.0:
                        coords = (lat, lng)
                        cache[cache_key] = {'coords': list(coords), 'ts': time.time()}
                        _save_opencage_cache()
                        return coords
        # Cache negative result
        cache[cache_key] = {'coords': None, 'ts': time.time()}
        _save_opencage_cache()
        return None
    except Exception as e:
        log.debug(f"OpenCage geocode error for '{query}': {e}")
        return None

def _normalize_admin_name(value: str) -> str:
    """Normalize admin/place names for matching."""
    if not value:
        return ''
    name = value.lower().strip()
    name = name.replace('ʼ', "'").replace('’', "'")
    name = RE_MULTI_SPACE.sub(' ', name)
    name = RE_OBLAST_SUFFIX_REMOVE.sub('', name)
    name = RE_RAION_SUFFIX_REMOVE.sub('', name)
    return name.strip()

def _resolve_oblast_id_from_name(name: str) -> str | None:
    """Resolve oblast ID from a possibly unnormalized oblast name."""
    if not name:
        return None
    if name in _OBLAST_ID_CACHE:
        return _OBLAST_ID_CACHE[name]
    name_norm = _normalize_admin_name(name)
    for key, val in REGION_TO_OBLAST_ID.items():
        if _normalize_admin_name(key) == name_norm:
            _OBLAST_ID_CACHE[name] = val
            return val
    _OBLAST_ID_CACHE[name] = None
    return None

def _derive_region_ids_from_regions(regions: list) -> tuple[list, list]:
    """Derive oblast_ids/raion_ids from region strings when client doesn't send IDs."""
    if not regions:
        return [], []
    derived_oblasts: set[str] = set()
    derived_raions: set[str] = set()

    # First pass: resolve oblasts
    for r in regions:
        if not r:
            continue
        oblast_id = _resolve_oblast_id_from_name(str(r))
        if oblast_id:
            derived_oblasts.add(oblast_id)

    default_oblast = next(iter(derived_oblasts), None)

    # Second pass: resolve raions
    for r in regions:
        if not r:
            continue
        r_low = str(r).lower()
        if 'район' not in r_low and 'р-н' not in r_low:
            continue
        raion_base = _normalize_admin_name(str(r))
        raion_key = raion_base
        if raion_key.endswith('ський') or raion_key.endswith('цький') or raion_key.endswith('зький'):
            raion_key = raion_key[:-2]  # "ський" -> "ськ"

        # Direct match
        if raion_key in PLACE_TO_RAION_ID:
            ob, ra = PLACE_TO_RAION_ID[raion_key]
            if not default_oblast or ob == default_oblast:
                derived_oblasts.add(ob)
                derived_raions.add(ra)
                continue

        # Substring match
        for keyword, (kw_ob, kw_ra) in PLACE_TO_RAION_ID.items():
            if default_oblast and kw_ob != default_oblast:
                continue
            if keyword in raion_key or raion_key in keyword:
                derived_oblasts.add(kw_ob)
                derived_raions.add(kw_ra)
                break

    return list(derived_oblasts), list(derived_raions)

def opencage_lookup_components(place: str, region: str | None = None) -> dict | None:
    """
    Get OpenCage components for a place (cached).
    Returns components dict or None.
    """
    if not OPENCAGE_API_KEY or not place:
        return None

    place = place.strip()
    if not place:
        return None

    cache = _load_opencage_cache()
    region_part = (region or '').strip()
    cache_key = f"components|{place.lower()}|{region_part.lower()}"

    if cache_key in cache:
        entry = cache[cache_key]
        if time.time() - entry.get('ts', 0) < OPENCAGE_TTL:
            components = entry.get('components')
            if components:
                return components

    query = place
    if region_part:
        query = f"{place}, {region_part}"

    try:
        url = 'https://api.opencagedata.com/geocode/v1/json'
        params = {
            'q': f"{query}, Ukraine",
            'key': OPENCAGE_API_KEY,
            'limit': 1,
            'no_annotations': 1,
            'countrycode': 'ua',
            'language': 'uk'
        }
        resp = http_requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', [])
            if results:
                r0 = results[0]
                components = r0.get('components', {})
                geo = r0.get('geometry', {})
                lat = geo.get('lat')
                lng = geo.get('lng')
                if components and components.get('country_code', '').lower() == 'ua':
                    cache[cache_key] = {
                        'components': components,
                        'coords': [lat, lng] if lat and lng else None,
                        'ts': time.time()
                    }
                    _save_opencage_cache()
                    return components
        cache[cache_key] = {'components': None, 'ts': time.time()}
        _save_opencage_cache()
        return None
    except Exception as e:
        log.debug(f"OpenCage components error for '{query}': {e}")
        return None

def _load_neg_geocode_cache():
    global _neg_geocode_cache
    if _neg_geocode_cache is not None:
        return _neg_geocode_cache
    if os.path.exists(NEG_GEOCODE_FILE):
        try:
            with open(NEG_GEOCODE_FILE,encoding='utf-8') as f:
                _neg_geocode_cache = json.load(f)
        except Exception:
            _neg_geocode_cache = {}
    else:
        _neg_geocode_cache = {}
    return _neg_geocode_cache

def _save_neg_geocode_cache():
    if _neg_geocode_cache is None:
        return
    try:
        # Limit cache size to prevent memory issues
        cache_to_save = _neg_geocode_cache
        if len(_neg_geocode_cache) > 500:
            # Keep only the 500 most recent entries (approximate)
            items = list(_neg_geocode_cache.items())
            cache_to_save = dict(items[-500:])
        with open(NEG_GEOCODE_FILE,'w',encoding='utf-8') as f:
            json.dump(cache_to_save,f,ensure_ascii=False,indent=2)
    except Exception as e:
        log.warning(f"Failed saving negative geocode cache: {e}")

def _msg_timestamp(msg):
    """Extract timestamp from message for sorting and filtering"""
    if not msg:
        return 0

    # Try different timestamp fields
    date_str = msg.get('date') or msg.get('timestamp') or msg.get('time')
    if not date_str:
        return 0

    try:
        # Handle different date formats
        if isinstance(date_str, (int, float)):
            return float(date_str)

        # Parse datetime string
        if isinstance(date_str, str):
            # Try common formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.timestamp()
                except ValueError:
                    continue

            # Try parsing with dateutil as fallback
            try:
                from dateutil import parser
                dt = parser.parse(date_str)
                return dt.timestamp()
            except:
                pass
    except Exception:
        pass

    return 0

def start_fetch_thread():
    global FETCH_THREAD_STARTED, FETCH_THREAD_STARTED_AT, FETCH_THREAD
    log.info('start_fetch_thread() called')
    if not client:
        log.warning('start_fetch_thread: client is None')
        return
    if FETCH_THREAD_STARTED:
        log.info('start_fetch_thread: already started')
        return
    log.info('start_fetch_thread: starting new thread')
    FETCH_THREAD_STARTED = True
    FETCH_THREAD_STARTED_AT = time.time()
    AUTH_STATUS.update({'authorized': False, 'reason': 'starting_fetch'})
    loop = asyncio.new_event_loop()
    def runner():
        try:
            log.info('fetch_thread runner started')
            fetch_loop_fn = globals().get('fetch_loop') or getattr(parser_service, 'fetch_loop', None)
            if fetch_loop_fn is None:
                AUTH_STATUS.update({'authorized': False, 'reason': 'missing_fetch_loop'})
                log.error('fetch_thread runner: fetch_loop is not available')
                return
            if FETCH_START_DELAY > 0:
                log.info(f'Delaying Telegram fetch start for {FETCH_START_DELAY}s (FETCH_START_DELAY).')
                time.sleep(FETCH_START_DELAY)
            asyncio.set_event_loop(loop)
            while True:
                try:
                    log.info('About to call fetch_loop()')
                    loop.run_until_complete(fetch_loop_fn())
                    log.warning('fetch_loop() exited; restarting in 30s')
                    time.sleep(30)
                except AuthKeyDuplicatedError:
                    AUTH_STATUS.update({'authorized': False, 'reason': 'authkey_duplicated_runner'})
                    log.error('Fetch loop stopped: duplicated auth key.')
                    break
                except Exception as e:
                    AUTH_STATUS.update({'authorized': False, 'reason': f'crash:{e.__class__.__name__}'})
                    log.error(f'Fetch loop crashed: {e}')
                    time.sleep(30)
        except Exception as e:
            AUTH_STATUS.update({'authorized': False, 'reason': f'runner_crash:{e.__class__.__name__}'})
            log.error(f'fetch_thread runner crashed before loop: {e}')
        log.info('fetch_thread runner finished')
    FETCH_THREAD = threading.Thread(target=runner, daemon=True)
    FETCH_THREAD.start()
    log.info('start_fetch_thread: thread started successfully')

def replace_client(new_session: str):
    global client, session_str
    session_str = new_session
    try:
        if client:
            try:
                # Telethon has disconnect
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(client.disconnect())
            except Exception:
                pass
    finally:
        client = TelegramClient(StringSession(new_session), API_ID, API_HASH)
        AUTH_STATUS.update({'authorized': True, 'reason': 'replaced_session'})
        start_fetch_thread()

# ----------------- Session watcher (auto reload new_session.txt) -----------------
SESSION_WATCH_FILE = os.getenv('SESSION_WATCH_FILE', 'new_session.txt')
SESSION_WATCH_INTERVAL = int(os.getenv('SESSION_WATCH_INTERVAL', '60'))  # CPU optimized: 60s instead of 20s
_watch_thread_started = False
_last_session_file_mtime = 0

def start_session_watcher():
    global _watch_thread_started, _last_session_file_mtime
    if _watch_thread_started:
        return
    _watch_thread_started = True
    def _watch():
        global _last_session_file_mtime, session_str
        while True:
            try:
                if os.path.exists(SESSION_WATCH_FILE):
                    mt = os.path.getmtime(SESSION_WATCH_FILE)
                    if mt != _last_session_file_mtime:
                        _last_session_file_mtime = mt
                        with open(SESSION_WATCH_FILE,encoding='utf-8') as f:
                            new_s = f.read().strip()
                        if new_s and new_s != session_str:
                            log.info('Session watcher: detected updated session file, reloading...')
                            replace_client(new_s)
                # If we are unauthorized due to duplicate key, keep looking for replacement
                if AUTH_STATUS.get('reason','').startswith('authkey_duplicated') and not client.is_connected():
                    # just a hint in logs every few cycles
                    if int(time.time()) % (SESSION_WATCH_INTERVAL*3) == 0:
                        log.info('Waiting for new session (AuthKeyDuplicatedError). Generate via /auth endpoints.')
            except Exception as e:
                log.debug(f'Session watcher error: {e}')
            time.sleep(SESSION_WATCH_INTERVAL)
    threading.Thread(target=_watch, daemon=True).start()

@app.route('/google2848d36b38653ede.html')
def google_verification():
    """Google Search Console verification file"""
    return send_from_directory('static', 'google2848d36b38653ede.html')

@app.route('/new')
def index_new():
    """New UI - SVG map from ukrainealarm.com with districts"""
    response = render_template('index_map.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp

@app.route('/old')
def index_old():
    """Old TopoJSON map (has artifacts)"""
    response = render_template('index_new.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp

@app.route('/shahed-map')
@app.route('/shahed')
@app.route('/drones')
@app.route('/radar-shahed')
@app.route('/radar-shahediv')
@app.route('/karta-shahediv')
@app.route('/shahed-radar')
def shahed_map():
    """Shahed map landing page"""
    response = render_template('shahed_map.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp

# --- Consolidated static asset redirects (table-driven) ---
STATIC_REDIRECTS = {
    '/icon_missile.svg': '/static/icon_missile.svg',
    '/icon_balistic.svg': '/static/icon_balistic.svg',
    '/icon_drone.svg': '/static/shahed3.webp',
    '/static/icon_drone.svg': '/static/shahed3.webp',
    '/shahed3.webp': '/static/shahed3.webp',
    '/rozved.png': '/static/rozvedka2.png',
    '/static/rozved.png': '/static/rozvedka2.png',
    '/icon_rozved.svg': '/static/rozvedka2.png',
    '/static/icon_rozved.svg': '/static/rozvedka2.png',
    '/favicon.ico': '/static/icons/favicon-32x32.png',
}

@app.route('/icon_missile.svg')
@app.route('/icon_balistic.svg')
@app.route('/icon_drone.svg')
@app.route('/static/icon_drone.svg')
@app.route('/shahed3.webp')
@app.route('/rozved.png')
@app.route('/static/rozved.png')
@app.route('/icon_rozved.svg')
@app.route('/static/icon_rozved.svg')
@app.route('/favicon.ico')
def static_redirect():
    """Consolidated redirect handler for static assets"""
    target = STATIC_REDIRECTS.get(request.path)
    if target:
        return redirect(target, code=301)
    return '', 404

# SEO: Bot detection patterns for prerender
SEO_BOT_PATTERNS = [
    'googlebot', 'bingbot', 'yandex', 'baiduspider', 'facebookexternalhit',
    'twitterbot', 'rogerbot', 'linkedinbot', 'embedly', 'quora link preview',
    'showyoubot', 'outbrain', 'pinterest', 'slackbot', 'vkshare', 'w3c_validator',
    'whatsapp', 'telegram', 'applebot', 'duckduckbot'
]

def is_seo_bot(user_agent):
    """Check if request is from SEO bot/crawler"""
    if not user_agent:
        return False
    ua_lower = user_agent.lower()
    return any(bot in ua_lower for bot in SEO_BOT_PATTERNS)

@app.route('/dev')
def index_dev():
    """Development/experimental version of the map"""
    return render_template('index_dev.html')

# BANDWIDTH PROTECTION: Cache rendered HTML in memory
_INDEX_HTML_CACHE = {'html': None, 'ts': 0, 'etag': ''}
_INDEX_CACHE_TTL = 300  # Cache for 5 minutes (HTML rarely changes, saves CPU under load)
_index_cache_lock = threading.Lock()  # Prevent thundering herd on cache expiry

@app.route('/')
def index():
    """Main page - Карта тривог України онлайн"""
    global _INDEX_HTML_CACHE
    
    user_agent = request.headers.get('User-Agent', '')
    
    # DDOS PROTECTION: Block empty/suspicious User-Agents (except legitimate bots)
    if not user_agent or len(user_agent) < 10:
        if not is_seo_bot(user_agent):
            return Response('Bad Request', status=400)
    
    # SEO: Detect crawlers and serve optimized response
    if is_seo_bot(user_agent):
        response = _get_cached_index()
        resp = app.response_class(response)
        resp.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour for bots
        resp.headers['X-Robots-Tag'] = 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1'
        resp.headers['Link'] = '<https://neptun.in.ua/>; rel="canonical"'
        resp.headers['X-Bot-Detected'] = 'true'
        return resp
    
    now = time.time()
    cache_etag = f'index-{int(now // _INDEX_CACHE_TTL)}'
    
    # Check ETag for 304 response (saves bandwidth)
    client_etag = request.headers.get('If-None-Match')
    if client_etag and client_etag == cache_etag:
        return Response(status=304, headers={
            'Cache-Control': 'public, max-age=300',
            'ETag': cache_etag
        })
    
    # BANDWIDTH OPTIMIZATION: Serve cached HTML
    response = _get_cached_index()
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'  # 5 min cache - HTML is static
    resp.headers['ETag'] = cache_etag
    resp.headers['X-Robots-Tag'] = 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1'
    resp.headers['Link'] = '<https://neptun.in.ua/>; rel="canonical"'
    return resp

def _get_cached_index():
    """Get cached index.html content with thundering-herd protection."""
    global _INDEX_HTML_CACHE
    now = time.time()
    # Fast path: cache is valid
    if _INDEX_HTML_CACHE['html'] is not None and now - _INDEX_HTML_CACHE['ts'] <= _INDEX_CACHE_TTL:
        return _INDEX_HTML_CACHE['html']
    # Slow path: only one greenlet renders, others get stale cache
    if _index_cache_lock.acquire(blocking=False):
        try:
            # Re-check after acquiring lock (another greenlet may have refreshed)
            now = time.time()
            if _INDEX_HTML_CACHE['html'] is None or now - _INDEX_HTML_CACHE['ts'] > _INDEX_CACHE_TTL:
                _INDEX_HTML_CACHE['html'] = render_template('index.html')
                _INDEX_HTML_CACHE['ts'] = now
        finally:
            _index_cache_lock.release()
    # Return whatever is cached (possibly stale by a few ms — perfectly fine)
    return _INDEX_HTML_CACHE['html']

# SEO: Regional pages for each oblast
REGIONS_SEO = {
    'kyiv': {'name': 'Київська область', 'name_gen': 'Київської області', 'city': 'Київ'},
    'kharkiv': {'name': 'Харківська область', 'name_gen': 'Харківської області', 'city': 'Харків'},
    'odesa': {'name': 'Одеська область', 'name_gen': 'Одеської області', 'city': 'Одеса'},
    'dnipro': {'name': 'Дніпропетровська область', 'name_gen': 'Дніпропетровської області', 'city': 'Дніпро'},
    'lviv': {'name': 'Львівська область', 'name_gen': 'Львівської області', 'city': 'Львів'},
    'zaporizhzhia': {'name': 'Запорізька область', 'name_gen': 'Запорізької області', 'city': 'Запоріжжя'},
    'vinnytsia': {'name': 'Вінницька область', 'name_gen': 'Вінницької області', 'city': 'Вінниця'},
    'poltava': {'name': 'Полтавська область', 'name_gen': 'Полтавської області', 'city': 'Полтава'},
    'chernihiv': {'name': 'Чернігівська область', 'name_gen': 'Чернігівської області', 'city': 'Чернігів'},
    'sumy': {'name': 'Сумська область', 'name_gen': 'Сумської області', 'city': 'Суми'},
    'mykolaiv': {'name': 'Миколаївська область', 'name_gen': 'Миколаївської області', 'city': 'Миколаїв'},
    'kherson': {'name': 'Херсонська область', 'name_gen': 'Херсонської області', 'city': 'Херсон'},
    'zhytomyr': {'name': 'Житомирська область', 'name_gen': 'Житомирської області', 'city': 'Житомир'},
    'cherkasy': {'name': 'Черкаська область', 'name_gen': 'Черкаської області', 'city': 'Черкаси'},
    'rivne': {'name': 'Рівненська область', 'name_gen': 'Рівненської області', 'city': 'Рівне'},
    'khmelnytskyi': {'name': 'Хмельницька область', 'name_gen': 'Хмельницької області', 'city': 'Хмельницький'},
    'volyn': {'name': 'Волинська область', 'name_gen': 'Волинської області', 'city': 'Луцьк'},
    'ternopil': {'name': 'Тернопільська область', 'name_gen': 'Тернопільської області', 'city': 'Тернопіль'},
    'ivano-frankivsk': {'name': 'Івано-Франківська область', 'name_gen': 'Івано-Франківської області', 'city': 'Івано-Франківськ'},
    'chernivtsi': {'name': 'Чернівецька область', 'name_gen': 'Чернівецької області', 'city': 'Чернівці'},
    'zakarpattia': {'name': 'Закарпатська область', 'name_gen': 'Закарпатської області', 'city': 'Ужгород'},
    'kirovohrad': {'name': 'Кіровоградська область', 'name_gen': 'Кіровоградської області', 'city': 'Кропивницький'},
    'donetsk': {'name': 'Донецька область', 'name_gen': 'Донецької області', 'city': 'Донецьк'},
    'luhansk': {'name': 'Луганська область', 'name_gen': 'Луганської області', 'city': 'Луганськ'},
}

@app.route('/region/<region_slug>')
def region_page(region_slug):
    """SEO page for each region - helps with regional search queries"""
    region = REGIONS_SEO.get(region_slug)
    if not region:
        return render_template('index.html'), 404

    return render_template('region.html',
                          region_slug=region_slug,
                          region_name=region['name'],
                          region_name_gen=region['name_gen'],
                          region_city=region['city'])

@app.route('/map-only')
def map_only():
    """Map-only view - new SVG map for embedding in mobile apps (iOS/Android WebView)"""
    response = render_template('index_map.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes cache
    resp.headers['X-Frame-Options'] = 'ALLOWALL'  # Allow embedding in iframes/WebView
    resp.headers['Access-Control-Allow-Origin'] = '*'  # Allow cross-origin requests
    return resp

@app.route('/map-old')
def map_old():
    """Old Leaflet map view (map_only.html)"""
    response = render_template('map_only.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes cache
    resp.headers['X-Frame-Options'] = 'ALLOWALL'  # Allow embedding in iframes/WebView
    resp.headers['Access-Control-Allow-Origin'] = '*'  # Allow cross-origin requests
    return resp

@app.route('/map-embed')
def map_embed():
    """Map with world mask (dimming) for mobile apps embedding"""
    response = render_template('map_embed.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes cache
    resp.headers['X-Frame-Options'] = 'ALLOWALL'  # Allow embedding in iframes/WebView
    resp.headers['Access-Control-Allow-Origin'] = '*'  # Allow cross-origin requests
    return resp

@app.route('/svg')
def index_svg():
    """SVG map - redirect to main page"""
    from flask import redirect
    return redirect('/', code=301)

@app.route('/about')
def about():
    """About NEPTUN project page"""
    response = render_template('about.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour cache
    return resp

@app.route('/analytics')
def analytics():
    """Analytics and statistics page with original content analysis"""
    response = render_template('analytics.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes cache
    return resp

@app.route('/community')
@app.route('/telegram')
@app.route('/join')
def redirect_telegram():
    """Redirect to Telegram community"""
    page_name = request.path.lstrip('/')
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    track_redirect_visit(page_name, user_ip, user_agent)
    return render_template('redirect.html')

@app.route('/channel')
@app.route('/group')
@app.route('/chat')
def redirect_telegram2():
    """Redirect to Telegram channel"""
    page_name = request.path.lstrip('/')
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    track_redirect_visit(page_name, user_ip, user_agent)
    return render_template('redirect2.html')

@app.route('/news')
@app.route('/updates')
@app.route('/alerts')
def redirect_telegram3():
    """Redirect to Telegram alerts channel"""
    page_name = request.path.lstrip('/')
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    track_redirect_visit(page_name, user_ip, user_agent)
    return render_template('redirect3.html')

@app.route('/track_redirect_click', methods=['POST'])
def track_redirect_click():
    """Track button click on redirect page"""
    try:
        data = request.get_json() or {}
        page_name = data.get('page', 'unknown')
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')

        # Track as click (we'll add a suffix to differentiate)
        track_redirect_visit(f"{page_name}_click", user_ip, user_agent)

        return jsonify({'status': 'ok'})
    except Exception as e:
        log.warning(f"Failed to track redirect click: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/faq')
def faq():
    """Frequently Asked Questions page"""
    response = render_template('faq.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour cache
    return resp

@app.route('/privacy')
def privacy():
    """Privacy Policy page"""
    response = render_template('privacy.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours cache
    return resp

@app.route('/terms')
def terms():
    """Terms of Service page"""
    response = render_template('terms.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours cache
    return resp

@app.route('/contact')
def contact():
    """Contact page"""
    response = render_template('contact.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours cache
    return resp



@app.route('/locate')
def locate_place():
    """Search for a city/settlement and return coordinates or suggestions"""
    query = request.args.get('q', '').strip()

    if not query:
        return jsonify({'status': 'error', 'message': 'No query provided'})

    # Clean query from region suffixes before searching
    query_clean = query
    for suffix in [' область', ' Область', 'область', 'Область', 'ська область', 'цька область']:
        if suffix in query_clean:
            query_clean = query_clean.split(suffix)[0].strip()
            break

    query_lower = query_clean.lower()

    # First, try exact match in CITY_COORDS
    if query_lower in CITY_COORDS:
        lat, lng = CITY_COORDS[query_lower]
        return jsonify({
            'status': 'ok',
            'name': query.title(),
            'lat': lat,
            'lng': lng,
            'source': 'city_coords'
        })

    # Try exact match in SETTLEMENTS_INDEX
    if query_lower in SETTLEMENTS_INDEX:
        lat, lng = SETTLEMENTS_INDEX[query_lower]
        return jsonify({
            'status': 'ok',
            'name': query.title(),
            'lat': lat,
            'lng': lng,
            'source': 'settlements'
        })

    # Try exact match in UKRAINE_ADDRESSES_DB (extract city names)
    if UKRAINE_ADDRESSES_DB:
        for _key, value in UKRAINE_ADDRESSES_DB.items():
            city_name = value.get('city', '').lower()
            if city_name == query_lower:
                # Use CITY_COORDS or SETTLEMENTS_INDEX for this city
                if city_name in CITY_COORDS:
                    lat, lng = CITY_COORDS[city_name]
                    return jsonify({
                        'status': 'ok',
                        'name': value.get('city'),
                        'lat': lat,
                        'lng': lng,
                        'source': 'addresses_db'
                    })

    # Try normalized version with UA_CITY_NORMALIZE
    if query_lower in UA_CITY_NORMALIZE:
        normalized = UA_CITY_NORMALIZE[query_lower]
        if normalized in CITY_COORDS:
            lat, lng = CITY_COORDS[normalized]
            return jsonify({
                'status': 'ok',
                'name': normalized.title(),
                'lat': lat,
                'lng': lng,
                'source': 'normalized'
            })
        if normalized in SETTLEMENTS_INDEX:
            lat, lng = SETTLEMENTS_INDEX[normalized]
            return jsonify({
                'status': 'ok',
                'name': normalized.title(),
                'lat': lat,
                'lng': lng,
                'source': 'normalized'
            })

    # Try OpenCage geocoder as fallback
    try:
        coords = opencage_geocode(query)
        if coords:
            lat_val, lng_val = coords
            if validate_ukraine_coords(lat_val, lng_val):
                return jsonify({
                    'status': 'ok',
                    'name': query.title(),
                    'lat': lat_val,
                    'lng': lng_val,
                    'source': 'opencage'
                })
    except Exception as e:
        log.warning(f'OpenCage geocode error: {e}')

    # If no exact match, return suggestions (prefix/substring match)
    suggestions = set()

    # Search in CITY_COORDS first (priority)
    for city_name in CITY_COORDS.keys():
        if query_lower in city_name:
            suggestions.add(city_name.title())
            if len(suggestions) >= 50:
                break

    # Then search in SETTLEMENTS_INDEX
    if len(suggestions) < 50:
        for settlement_name in SETTLEMENTS_INDEX.keys():
            city_title = settlement_name.title()
            if query_lower in settlement_name:
                suggestions.add(city_title)
                if len(suggestions) >= 100:
                    break

    # Also search in UKRAINE_ADDRESSES_DB cities
    if len(suggestions) < 100 and UKRAINE_ADDRESSES_DB:
        cities_from_db = set()
        for value in UKRAINE_ADDRESSES_DB.values():
            city_name = value.get('city', '').strip()
            if city_name and query_lower in city_name.lower():
                cities_from_db.add(city_name)
        suggestions.update(cities_from_db)

    # Add UKRAINE_CITIES if available
    if len(suggestions) < 100 and UKRAINE_CITIES:
        for city in UKRAINE_CITIES:
            if query_lower in city.lower():
                suggestions.add(city)

    suggestions_list = sorted(suggestions, key=lambda x: (len(x), x))[:50]

    if suggestions_list:
        return jsonify({
            'status': 'suggest',
            'matches': suggestions_list
        })

    # No matches found
    return jsonify({
        'status': 'not_found',
        'message': f'Не знайдено: {query}'
    })


def _prune_comments():
    # keep only last COMMENTS_MAX comments
    global COMMENTS
    if len(COMMENTS) > COMMENTS_MAX:
        COMMENTS = COMMENTS[-COMMENTS_MAX:]

@app.route('/comments', methods=['GET','POST'])
def comments_endpoint():
    """GET returns recent anonymous comments. POST inserts a new one persistently.

    Persistence strategy:
      - Store each comment into SQLite (comments table) with epoch for ordering.
      - Maintain small in-memory tail cache to avoid DB hit storms on rapid polling.
      - On GET always fetch from DB (limit) for durability across redeploys.
    """
    if request.method == 'POST':
        try:
            data = request.get_json(force=True, silent=True) or {}
        except Exception:
            data = {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({'ok': False, 'error': 'empty'}), 400
        reply_to = (data.get('reply_to') or '').strip() or None
        if reply_to and not re.fullmatch(r'[0-9a-fA-F]{6,20}', reply_to):
            reply_to = None  # sanitize unexpected format
        # rudimentary spam / flooding throttles (per-IP simple memory window)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'
        now_ts = time.time()
        # simple rate tracker: store recent post times per IP in a module-level dict
        rt = getattr(app, '_comment_rate', None)
        if rt is None:
            rt = {}
            app._comment_rate = rt
        arr = rt.get(ip, [])
        # drop entries older than 60s
        arr = [t for t in arr if now_ts - t < 60]
        if len(arr) >= 8:  # max 8 comments per minute per IP
            return jsonify({'ok': False, 'error': 'rate_limited'}), 429
        arr.append(now_ts)
        rt[ip] = arr
        # basic length clamp
        if len(text) > 800:
            text = text[:800]
        item = {
            'id': uuid.uuid4().hex[:10],
            'text': text,
            'ts': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'epoch': now_ts,
            'reply_to': reply_to
        }
        cache_item = {k: item[k] for k in ('id','text','ts')}
        if reply_to:
            cache_item['reply_to'] = reply_to
        COMMENTS.append(cache_item)  # store subset in memory cache
        _prune_comments()
        # persist
        save_comment_record(item)
        resp_item = {k: item[k] for k in ('id','text','ts')}
        if reply_to:
            resp_item['reply_to'] = reply_to
        return jsonify({'ok': True, 'item': resp_item})
    # GET
    limit = 80
    rows = load_recent_comments(limit=limit)
    if not rows and COMMENTS:  # fallback to cache if DB query unexpectedly empty
        rows = COMMENTS[-limit:]
    return jsonify({'ok': True, 'items': rows})

@app.route('/comments/react', methods=['POST'])
def comment_react_endpoint():
    """Toggle emoji reactions on comments."""
    try:
        data = request.get_json(force=True, silent=True) or {}
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid_json'}), 400

    comment_id = (data.get('comment_id') or '').strip()
    emoji = (data.get('emoji') or '').strip()

    # Validation
    if not comment_id or not emoji:
        return jsonify({'ok': False, 'error': 'missing_params'}), 400

    # Validate emoji is in allowed list
    allowed_emojis = ['👍', '❤️', '🔥', '😢', '😡', '😂', '👎']
    if emoji not in allowed_emojis:
        return jsonify({'ok': False, 'error': 'invalid_emoji'}), 400

    # Get user IP for uniqueness
    ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown'

    # Rate limiting: max 20 reactions per minute per IP
    now_ts = time.time()
    rt = getattr(app, '_reaction_rate', None)
    if rt is None:
        rt = {}
        app._reaction_rate = rt

    arr = rt.get(ip, [])
    arr = [t for t in arr if now_ts - t < 60]  # Keep last 60 seconds
    if len(arr) >= 20:
        return jsonify({'ok': False, 'error': 'rate_limited'}), 429
    arr.append(now_ts)
    rt[ip] = arr

    # Toggle reaction
    result = toggle_comment_reaction(comment_id, emoji, ip)

    if result['action'] == 'error':
        return jsonify({'ok': False, 'error': 'server_error'}), 500

    return jsonify({
        'ok': True,
        'action': result['action'],
        'reactions': result['reactions']
    })

@app.route('/active_alarms')
def active_alarms_endpoint():
    """Return current active oblast & raion air alarms (for polygon styling)."""

    # Rate limit отключен: все пользователи имеют свободный доступ

    try:
        now_ep = time.time()
        cutoff = now_ep - APP_ALARM_TTL_MINUTES*60
        for dct in (ACTIVE_OBLAST_ALARMS, ACTIVE_RAION_ALARMS):
            for k in list(dct.keys()):
                if dct[k]['last'] < cutoff:
                    dct.pop(k, None)
        obl_list = []
        for k,v in ACTIVE_OBLAST_ALARMS.items():
            base = k.lower()
            pcode = OBLAST_PCODE.get(base)
            obl_list.append({'name': k, 'since': v['since'], **({'pcode':pcode} if pcode else {})})
        return jsonify({
            'oblasts': obl_list,
            'raions': [{'name': k, 'since': v['since']} for k,v in ACTIVE_RAION_ALARMS.items()],
            'ttl_minutes': APP_ALARM_TTL_MINUTES
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/alarms_stats')
@protected_endpoint(is_heavy=False)  # PROTECTION: Rate limiting
def alarms_stats():
    """Return recent alarm events history (start/cancel/expire) with optional query params:
    ?level=oblast|raion  ?name=<substring>  ?minutes=<window>  ?limit=N
    """
    # ===========================================================================
    # HARDENED /alarms_stats ENDPOINT
    # BEFORE: Could request up to 2000 items with 720 min window
    # AFTER:  Max 500 items, max 360 min (6h) window
    # ===========================================================================
    MAX_LIMIT = 500      # HARD LIMIT (was 2000)
    MAX_MINUTES = 360    # HARD LIMIT: 6 hours (was 720 = 12h)

    level_f = request.args.get('level')
    name_sub = (request.args.get('name') or '').lower().strip()
    minutes = min(MAX_MINUTES, max(1, int(request.args.get('minutes', '360'))))  # Cap at 6h
    limit = min(MAX_LIMIT, max(1, int(request.args.get('limit', '200'))))  # Cap at 500

    cutoff = time.time() - minutes*60
    rows = []
    try:
        with _visits_db_conn() as conn:
            q = "SELECT level,name,event,ts FROM alarm_events WHERE ts >= ?"
            params = [cutoff]
            if level_f in ('oblast','raion'):
                q += " AND level = ?"; params.append(level_f)
            if name_sub:
                q += " AND LOWER(name) LIKE ?"; params.append(f"%{name_sub}%")
            q += " ORDER BY ts DESC LIMIT ?"; params.append(limit)
            cur = conn.execute(q, tuple(params))
            for level,name,event,tsv in cur.fetchall():
                rows.append({'level': level, 'name': name, 'event': event, 'ts': tsv})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'items': rows, 'count': len(rows), 'window_minutes': minutes})

# ===========================================================================
# AGGRESSIVE RATE LIMIT FOR /data - 1 request per 5 seconds per IP
# ===========================================================================
_data_rate_limit = {}  # {ip: last_request_time}
_data_rate_limit_window = 5  # seconds between requests
_data_rate_limit_max_ips = 1000  # max tracked IPs

def _check_data_rate_limit():
    """Check if IP is rate limited for /data endpoint. Returns True if blocked."""
    global _data_rate_limit
    # Use Cloudflare-aware IP detection
    client_ip = get_real_ip()
    
    now = time.time()
    last_request = _data_rate_limit.get(client_ip, 0)
    
    # Cleanup old entries periodically
    if len(_data_rate_limit) > _data_rate_limit_max_ips:
        cutoff = now - 60  # Remove IPs not seen in 60 seconds
        _data_rate_limit = {ip: ts for ip, ts in _data_rate_limit.items() if ts > cutoff}
    
    if now - last_request < _data_rate_limit_window:
        return True  # Rate limited
    
    _data_rate_limit[client_ip] = now
    return False  # OK

@app.route('/data')
@protected_endpoint(is_heavy=True)  # PROTECTION: Rate limit + concurrency control
def data():
    global FALLBACK_REPARSE_CACHE, MAX_REPARSE_CACHE_SIZE

    # ===========================================================================
    # HARDENED /data ENDPOINT - Prevents 23GB+ traffic spikes
    # HIGH-LOAD OPTIMIZED: Added in-memory + persistent caching
    # DEPLOY-SAFE: Persistent cache survives server restarts (30 min TTL)
    # ===========================================================================
    
    # AGGRESSIVE RATE LIMIT: 1 request per 5 seconds per IP
    # Skip rate limit for admin requests (they pass secret)
    is_admin_request = bool(request.args.get('secret') or request.headers.get('X-Auth-Secret'))
    if not is_admin_request and _check_data_rate_limit():
        return Response(
            '{"error":"rate_limited","retry_after":5}',
            status=429,
            mimetype='application/json',
            headers={'Retry-After': '5', 'Cache-Control': 'no-store'}
        )
    
    # Allow forced reparse by clearing cache (admin use)
    if request.args.get('force_reparse') == 'true':
        print(f"[DATA] Force reparse requested, clearing FALLBACK_REPARSE_CACHE ({len(FALLBACK_REPARSE_CACHE)} items)")
        FALLBACK_REPARSE_CACHE.clear()

    # HIGH-LOAD: Check memory cache first (5 second TTL)
    # Admin requests bypass cache to always get fresh data
    cache_key = f'data_{MONITOR_PERIOD_MINUTES}'
    if not is_admin_request:
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            # Still check ETag for 304
            client_etag = request.headers.get('If-None-Match')
            if client_etag and cached.get('etag') == client_etag:
                return Response(status=304, headers={'Cache-Control': 'public, max-age=30'})

            response = jsonify(cached['data'])
            response.headers['Cache-Control'] = 'public, max-age=30'
            response.headers['X-Cache'] = 'HIT'
            if cached.get('etag'):
                response.headers['ETag'] = cached['etag']
            return response

    # PROTECTION: Hard limits to prevent memory/bandwidth exhaustion
    MAX_TRACKS = 50        # HARD LIMIT: max tracks per response (reduced from 100)
    MAX_EVENTS = 25        # HARD LIMIT: max events per response (reduced from 50)
    MAX_RESPONSE_MB = 0.5  # HARD LIMIT: max response size in MB (reduced from 1)
    
    # MEMORY CHECK: Log memory usage periodically
    import random
    if random.random() < 0.05:  # 5% of requests
        try:
            import psutil
            mem_mb = psutil.Process().memory_info().rss / 1024 / 1024
            print(f"[MEMORY] /data request: {mem_mb:.1f}MB used")
            if mem_mb > 1500:  # Warn if over 1.5GB
                print(f"[MEMORY] WARNING: High memory usage! {mem_mb:.1f}MB")
                import gc
                gc.collect()
        except:
            pass

    # BANDWIDTH OPTIMIZATION: Add aggressive caching headers
    response_headers = {
        'Cache-Control': 'public, max-age=30',  # 30 sec client cache
        'ETag': f'data-{int(time.time() // 30)}',  # ETag changes every 30 sec
        'Vary': 'Accept-Encoding'
    }

    # Check if client has cached version (saves bandwidth)
    client_etag = request.headers.get('If-None-Match')
    if client_etag == response_headers['ETag']:
        return Response(status=304, headers=response_headers)

    # Use global configured MONITOR_PERIOD_MINUTES from admin panel
    # URL parameter timeRange is ignored - only admin can control this
    time_range = MONITOR_PERIOD_MINUTES
    # Validate range (should be 1-360 as set by admin, but apply safety limits)
    time_range = max(1, min(time_range, 360))

    print(f"[DEBUG] /data endpoint called with timeRange={request.args.get('timeRange')}, MONITOR_PERIOD_MINUTES={MONITOR_PERIOD_MINUTES}, using time_range={time_range}")
    messages = load_messages()
    print(f"[DEBUG] Loaded {len(messages)} total messages")
    
    # DEDUPLICATE messages by text+date to avoid showing same message multiple times
    seen_keys = set()
    unique_messages = []
    for m in messages:
        # Create key from text + date (messages with same text at same time are duplicates)
        msg_key = f"{m.get('text', '')[:100]}|{m.get('date', '')}"
        if msg_key not in seen_keys:
            seen_keys.add(msg_key)
            unique_messages.append(m)
    if len(unique_messages) < len(messages):
        print(f"[DEDUP] Removed {len(messages) - len(unique_messages)} duplicate messages")
    messages = unique_messages
    
    tz = pytz.timezone('Europe/Kyiv')
    now = datetime.now(tz).replace(tzinfo=None)

    # Check each message individually
    # Pre-filter to avoid checking very old messages
    max_possible_ttl = 30  # 30 minutes - max possible TTL for any threat type (was 240)
    min_time_prefilter = now - timedelta(minutes=max_possible_ttl)

    # Use fixed time window
    min_time = now - timedelta(minutes=time_range)
    manual_cutoff = now - timedelta(minutes=max(time_range, MANUAL_MARKER_WINDOW_MINUTES))

    print(f"[DEBUG] Filtering messages since {min_time} (last {time_range} minutes)")
    hidden = set(load_hidden())
    out = []  # geo tracks
    events = []  # list-only (alarms, cancellations, other non-geo informational)
    
    # DEBUG: Count messages by category
    debug_counts = {'too_old': 0, 'no_date': 0, 'pending_geo': 0, 'has_coords': 0, 'recent': 0}
    
    # DEBUG: Log first message time vs current time
    if messages:
        sample_date = messages[0].get('date', '')
        print(f"[DEBUG_TIME] now={now}, min_time={min_time}, sample_msg_date='{sample_date}'")

    for m in messages:
        try:
            dt = datetime.strptime(m.get('date',''), '%Y-%m-%d %H:%M:%S')
        except Exception:
            debug_counts['no_date'] += 1
            continue
        
        # DEBUG: Track message categories
        has_coords = bool(m.get('lat') and m.get('lng'))
        is_pending = bool(m.get('pending_geo'))
        is_recent = dt >= min_time
        
        if has_coords:
            debug_counts['has_coords'] += 1
        if is_pending:
            debug_counts['pending_geo'] += 1
        if is_recent:
            debug_counts['recent'] += 1
        if not is_recent:
            debug_counts['too_old'] += 1

        manual_marker = bool(m.get('manual'))

        # === TIME FILTERING ===
        # Use fixed time window
        if not (dt >= min_time or (manual_marker and dt >= manual_cutoff)):
            continue

        # === MARKER PROCESSING ===
        msg_id = m.get('id')

        # PERF FIX: Never geocode inside /data — process_message() calls Visicom/Nominatim
        # HTTP APIs (500ms-10s per call), which blocks the greenlet and causes cascading 502s.
        # Messages without coordinates are geocoded by the background Telegram fetch thread.
        if (not m.get('lat')) and (not m.get('lng')):
            debug_counts['pending_geo_processing'] = debug_counts.get('pending_geo_processing', 0) + 1
            # Show as list-only event if it has meaningful text
            if m.get('text') and not m.get('suppress'):
                events.append(m)
            continue
        # list-only (no coordinates) -> push into events list if not suppressed
        if m.get('list_only'):
            if not m.get('suppress'):
                events.append(m)
            continue  # skip trying to interpret as marker
        # build marker key similar to frontend hide logic (rounded lat/lng + text + source/channel)
        try:
            lat = round(float(m.get('lat')), 3)
            lng = round(float(m.get('lng')), 3)
        except Exception:
            continue  # not a proper geo marker
        text = (m.get('text') or '')
        source = m.get('source') or m.get('channel') or ''
        marker_key = f"{lat},{lng}|{text}|{source}"
        if marker_key in hidden:
            continue
        # Backward compatibility: allow prefix match (text truncated when stored) for same lat,lng,source
        base_prefix = f"{lat},{lng}|"
        if not any(h.startswith(base_prefix) for h in hidden if '|' in h):
            pass
        else:
            # iterate candidates with same coords and source, compare text prefix
            skip = False
            for h in hidden:
                if not h.startswith(base_prefix):
                    continue
                try:
                    _, htext, hsource = h.split('|',2)
                except ValueError:
                    continue
                if hsource == source and text.startswith(htext):
                    skip = True
                    break
            if skip:
                continue
        # Фильтр: удаляем региональные метки без явных слов угроз (могли сохраниться старыми версиями логики)
        low_txt = text.lower()
        if m.get('source_match','').startswith('region') and not any(k in low_txt for k in ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile','iskander','s-300','s300','каб','артил','града','смерч','ураган','mlrs','avia','авіа','авиа','бомба']):
            continue
        
        # === TTL FILTERING: Apply per-threat-type TTL limits (if enabled) ===
        if TTL_SYSTEM_ENABLED:
            threat_type = m.get('threat_type', '').lower()
            marker_icon = m.get('marker_icon', '').lower()
            
            # If threat_type is empty, try to infer from marker_icon or text
            if not threat_type:
                if 'raketa' in marker_icon or 'rocket' in marker_icon or 'missile' in marker_icon:
                    threat_type = 'rocket'
                elif 'kab' in marker_icon or 'bomb' in marker_icon:
                    threat_type = 'kab'
                elif 'cruise' in marker_icon or 'kalibr' in marker_icon or 'x101' in marker_icon:
                    threat_type = 'cruise'
                elif 'ballistic' in marker_icon or 'iskander' in marker_icon:
                    threat_type = 'ballistic'
                elif 'kinzhal' in marker_icon:
                    threat_type = 'kinzhal'
                # Also check text for rocket/kab keywords
                elif any(kw in low_txt for kw in ['ракета', 'ракети', 'балістик', 'крилат', 'калібр', 'х-101', 'х-22', 'іскандер', 'кінжал', 'missile', 'rocket']):
                    threat_type = 'rocket'
                elif any(kw in low_txt for kw in ['каб', 'kab', 'керован', 'бомб']):
                    threat_type = 'kab'
            
            # Determine TTL for this marker type
            marker_ttl = THREAT_MAX_TTL.get(threat_type, 30)  # Default 30 min if unknown
            # For rockets/missiles/KAB, use strict 5 min TTL
            if threat_type in ['kab', 'rocket', 'cruise', 'ballistic', 'kinzhal', 'iskander', 'kalibr', 'x101', 'x22', 'raketa']:
                marker_ttl = 5
            # Check if marker is expired based on its TTL
            marker_age_minutes = (now - dt).total_seconds() / 60
            if marker_age_minutes > marker_ttl and not manual_marker:
                debug_counts['ttl_expired'] = debug_counts.get('ttl_expired', 0) + 1
                continue
        
        out.append(m)




    # === THREAT TRACKER: Update from alarms and get active threats ===
    try:
        # Check alarm state and update threats
        if _alarm_all_cache.get('data'):
            check_alarms_and_update_threats()

        # Cleanup old threats
        THREAT_TRACKER.cleanup_old_threats(max_age_hours=4)

        # Get active tracked threats
        active_threats = THREAT_TRACKER.get_all_active_threats()
        threat_info = {
            'count': len(active_threats),
            'by_type': {},
            'by_region': {}
        }
        for t in active_threats:
            tt = t.get('threat_type', 'unknown')
            threat_info['by_type'][tt] = threat_info['by_type'].get(tt, 0) + t.get('quantity_remaining', 1)
            for r in t.get('regions', []):
                threat_info['by_region'][r] = threat_info['by_region'].get(r, 0) + 1
    except Exception as e:
        print(f"[THREAT TRACKER] Error in /data: {e}")
        threat_info = None

    # Sort events by time desc (latest first) like markers implicitly (messages stored chronological)
    try:
        events.sort(key=lambda x: x.get('date',''), reverse=True)
    except Exception:
        pass

    # ===========================================================================
    # PROTECTION: Apply hard limits to prevent bandwidth/memory exhaustion
    # ===========================================================================
    total_tracks = len(out)
    total_events = len(events)

    # HARD LIMIT: Truncate tracks (newest first - reverse since messages are chronological)
    if len(out) > MAX_TRACKS:
        out = out[-MAX_TRACKS:]  # Keep newest tracks
        print(f"[BANDWIDTH PROTECTION] Truncated tracks: {total_tracks} -> {MAX_TRACKS}")

    # HARD LIMIT: Truncate events
    if len(events) > MAX_EVENTS:
        events = events[:MAX_EVENTS]  # Already sorted newest first
        print(f"[BANDWIDTH PROTECTION] Truncated events: {total_events} -> {MAX_EVENTS}")

    print(f"[DEBUG] Message categories: {debug_counts}")
    print(f"[DEBUG] Returning {len(out)} tracks and {len(events)} events (limits: {MAX_TRACKS}/{MAX_EVENTS})")

    # PERF FIX: Build NEW dicts for response instead of mutating cached originals.
    # Previously we did track.pop('raw_text') etc. directly on MessageStore objects,
    # which permanently destroyed data in the shared cache after the first request.
    trimmed_out = []
    for track in out:
        t = {
            'id': track.get('id'),
            'lat': track.get('lat'),
            'lng': track.get('lng'),
            'text': (track.get('text') or '')[:100] + ('...' if len(track.get('text') or '') > 100 else ''),
            'date': track.get('date'),
            'source': track.get('source') or track.get('channel') or '',
            'channel': track.get('channel') or track.get('source') or '',
            'threat_type': track.get('threat_type'),
            'marker_icon': 'shahed3.webp' if track.get('marker_icon') == 'shahed.png' else track.get('marker_icon'),
            'place': track.get('place'),
            'manual': track.get('manual'),
            'course': track.get('course'),
            'speed': track.get('speed'),
            'altitude': track.get('altitude'),
        }
        if is_admin_request and track.get('trajectory'):
            t['trajectory'] = track['trajectory']
        trimmed_out.append(t)
    out = trimmed_out

    trimmed_events = []
    for event in events:
        e = {
            'id': event.get('id'),
            'text': (event.get('text') or '')[:100] + ('...' if len(event.get('text') or '') > 100 else ''),
            'date': event.get('date'),
            'source': event.get('source') or event.get('channel') or '',
            'channel': event.get('channel') or event.get('source') or '',
            'threat_type': event.get('threat_type'),
            'list_only': event.get('list_only'),
            'suppress': event.get('suppress'),
        }
        trimmed_events.append(e)
    events = trimmed_events

    # DEBUG: Count tracks with trajectories
    traj_count = sum(1 for t in out if t.get('trajectory'))
    if traj_count > 0:
        print(f"[DEBUG] /data response has {traj_count} tracks with trajectories")

    # Build response with metadata about truncation
    response_data = {
        'tracks': out,
        'events': events,
        'all_sources': CHANNELS,
        # 'trajectories': [],  # REMOVED - too heavy, saves bandwidth
        # Ballistic threat state from Telegram
        'ballistic_threat': {
            'active': BALLISTIC_THREAT_ACTIVE,
            'region': BALLISTIC_THREAT_REGION,
            'timestamp': BALLISTIC_THREAT_TIMESTAMP,
        },
        # Smart threat tracking info removed to save bandwidth
        # 'threat_tracking': threat_info,
        # Metadata for clients to know if data was truncated
        '_meta': {
            'tracks_total': total_tracks,
            'tracks_returned': len(out),
            'tracks_truncated': total_tracks > MAX_TRACKS,
            'events_total': total_events,
            'events_returned': len(events),
            'events_truncated': total_events > MAX_EVENTS,
            'time_range_minutes': time_range,
        }
    }

    # PROTECTION: Final response size check
    response_json = json.dumps(response_data, separators=(',', ':'))
    response_size = len(response_json.encode('utf-8'))

    if response_size > MAX_RESPONSE_MB * 1024 * 1024:
        # Emergency truncation - should rarely happen with above limits
        print(f"[BANDWIDTH EMERGENCY] Response too large: {response_size / 1024 / 1024:.2f}MB > {MAX_RESPONSE_MB}MB")
        response_data['tracks'] = out[:50]
        response_data['events'] = events[:25]
        response_data['_meta']['emergency_truncated'] = True
        response_json = json.dumps(response_data, separators=(',', ':'))

    # HIGH-LOAD: Cache the response for 30 seconds (in-memory) to survive traffic spikes
    RESPONSE_CACHE.set(cache_key, {
        'data': response_data,
        'etag': response_headers.get('ETag')
    }, ttl=30)

    resp = Response(response_json, mimetype='application/json')
    # Add aggressive caching headers to reduce bandwidth
    resp.headers.update(response_headers)
    resp.headers['X-Cache'] = 'MISS'
    return resp

@app.route('/channels')
def list_channels():
    return jsonify({'channels': CHANNELS, 'invalid': list(INVALID_CHANNELS)})

@app.route('/debug_parse', methods=['POST'])
def debug_parse():
    """Ad-hoc debugging endpoint to inspect parser output for a stored message or raw text.

    POST JSON:
      {"id": <message_id>}  -> reparse stored message text
      or
      {"text": "raw message text", "channel": "optional", "date": "YYYY-MM-DD HH:MM:SS"}

    Response: { ok: bool, source: 'stored'|'raw', message: {...original message fields subset...}, tracks: [...], count: N }
    """
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        try:
            payload = request.get_json(silent=True) or {}
        except Exception:
            payload = {}
    mid = payload.get('id')
    raw_text = payload.get('text')
    # Allow base64-encoded text to avoid client console encoding corruption
    if not raw_text:
        b64_txt = payload.get('b64') or payload.get('b64_text') or None
        if b64_txt:
            try:
                import base64
                raw_text = base64.b64decode(b64_txt).decode('utf-8', errors='replace')
            except Exception:
                raw_text = ''
    channel = payload.get('channel') or ''
    date_str = payload.get('date') or datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    src = 'raw'
    if mid and not raw_text:
        # look up stored messages
        try:
            for m in load_messages():
                if str(m.get('id')) == str(mid):
                    raw_text = m.get('text') or ''
                    channel = m.get('channel') or m.get('source') or channel
                    date_str = m.get('date') or date_str
                    src = 'stored'
                    break
        except Exception:
            pass
    if not raw_text:
        return jsonify({'ok': False, 'error': 'no_text_provided'}), 400
    try:
        tracks = process_message(raw_text, str(mid) if mid else 'debug', date_str, channel)
    except Exception as e:
        return jsonify({'ok': False, 'error': f'parse_error: {e}'}), 500
    return jsonify({
        'ok': True,
        'source': src,
        'message': {
            'id': mid,
            'channel': channel,
            'date': date_str,
            'text': raw_text[:2000]
        },
        'count': len(tracks) if isinstance(tracks, list) else 0,
        'tracks': tracks if isinstance(tracks, list) else []
    })

@app.route('/api/visitor_count')
def visitor_count():
    """API endpoint to get total visitor count from database."""
    try:
        import sqlite3
        conn = sqlite3.connect('visits.db')
        cursor = conn.cursor()

        # Get total unique visitors
        cursor.execute('SELECT COUNT(DISTINCT ip) FROM visits')
        total_visitors = cursor.fetchone()[0]

        conn.close()

        return str(total_visitors), 200, {
            'Content-Type': 'text/plain',
            'Cache-Control': 'public, max-age=10',
            'Access-Control-Allow-Origin': '*'
        }
    except Exception as e:
        print(f"[ERROR] Failed to get visitor count: {e}")
        return "0", 200, {'Content-Type': 'text/plain'}

@app.route('/api/android_visitor_count')
def android_visitor_count():
    """API endpoint to get Android app visitor count."""
    try:
        import sqlite3
        conn = sqlite3.connect('visits.db')
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_visits (
                device_id TEXT PRIMARY KEY,
                platform TEXT,
                ip TEXT,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('SELECT COUNT(*) FROM app_visits WHERE platform = ?', ('android',))
        android_visitors = cursor.fetchone()[0] or 0

        conn.close()

        return str(android_visitors), 200, {
            'Content-Type': 'text/plain',
            'Cache-Control': 'public, max-age=10',
            'Access-Control-Allow-Origin': '*'
        }
    except Exception as e:
        print(f"[ERROR] Failed to get Android visitor count: {e}")
        return "0", 200, {'Content-Type': 'text/plain'}

@app.route('/api/track_android_visit', methods=['POST'])
def track_android_visit():
    """Track Android app visitor."""
    try:
        import sqlite3
        payload = request.get_json(silent=True) or {}
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        device_id = str(payload.get('device_id') or '').strip() or client_ip
        platform_hint = payload.get('platform') or 'android'
        ua = request.headers.get('User-Agent', '')
        platform_label = _normalize_platform(platform_hint, ua)

        conn = sqlite3.connect('visits.db')
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_visits (
                device_id TEXT PRIMARY KEY,
                platform TEXT,
                ip TEXT,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            INSERT INTO app_visits (device_id, platform, ip, last_seen)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(device_id) DO UPDATE SET
                platform=excluded.platform,
                ip=excluded.ip,
                last_seen=CURRENT_TIMESTAMP
        ''', (device_id, platform_label, client_ip))

        conn.commit()
        conn.close()

        return jsonify({'ok': True, 'platform': platform_label}), 200
    except Exception as e:
        print(f"[ERROR] Failed to track Android visit: {e}")
        return jsonify({'ok': False}), 500

@app.route('/api/events')
@protected_endpoint(is_heavy=False)  # PROTECTION: Rate limiting
def get_events():
    """Get recent air alarm events from Telegram."""
    # ===========================================================================
    # HARDENED /api/events ENDPOINT
    # BEFORE: Processed ALL messages without limit
    # AFTER:  Process last 500 messages max, return 100 events max
    # ===========================================================================
    MAX_PROCESS_MESSAGES = 500  # HARD LIMIT: max messages to scan
    MAX_RETURN_EVENTS = 100     # HARD LIMIT: max events to return

    try:
        messages = load_messages()
        events = []

        # PROTECTION: Only process last 500 messages (was: ALL messages)
        for msg in messages[-MAX_PROCESS_MESSAGES:]:
            if not isinstance(msg, dict):
                continue

            text = msg.get('text', '').strip()
            channel = msg.get('channel', '')
            timestamp = msg.get('time', '')

            # Detect alarm type by emoji or text
            emoji = None
            status = None

            if '🚨' in text or 'Повітряна тривога' in text:
                emoji = '🚨'
                status = 'Повітряна тривога'
            elif '🟢' in text or 'Відбій тривоги' in text or 'відбій тривоги' in text:
                emoji = '🟢'
                status = 'Відбій тривоги'
            else:
                continue

            # Extract region from multiple formats:
            # Format 1: "**🚨 Дніпропетровська область**"
            # Format 2: "**🚨 Харківський район (Харківська обл.)**"
            region = ''

            if '**' in text:
                parts = text.split('**')
                for part in parts:
                    part = part.strip()
                    # Look for parts containing emoji
                    if '🚨' in part or '🟢' in part:
                        # Remove emoji and clean up
                        region = part.replace('🚨', '').replace('🟢', '').strip()
                        break

            # Fallback: extract from first line
            if not region and text:
                first_line = text.split('\n')[0].strip()
                # Remove markdown and emojis
                region = first_line.replace('**', '').replace('🚨', '').replace('🟢', '').strip()
                # Remove common phrases
                region = region.replace('Повітряна тривога.', '').replace('Прямуйте в укриття!', '').strip()
                region = region.replace('Відбій тривоги.', '').replace('Будьте обережні!', '').strip()

            # Skip if no region found
            if not region:
                continue

            events.append({
                'timestamp': timestamp,
                'channel': channel,
                'emoji': emoji,
                'region': region,
                'status': status,
                'text': text[:200]  # First 200 chars
            })

        # Sort by timestamp (newest first) and return last 100 events
        # This ensures stable results regardless of message order in file
        events.reverse()

        # PROTECTION: Hard limit on returned events
        returned_events = events[:MAX_RETURN_EVENTS]

        response = jsonify(returned_events)
        response.headers['Cache-Control'] = 'public, max-age=30'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        print(f"[ERROR] /api/events failed: {e}")
        return jsonify([]), 500

@app.route('/api/messages')
@protected_endpoint(is_heavy=False)  # PROTECTION: Rate limiting
def get_messages():
    """Get recent alarm messages with coordinates for mobile apps."""
    _auto_cleanup_if_needed()  # Periodic memory cleanup
    
    # ===========================================================================
    # HARDENED /api/messages ENDPOINT - HIGH LOAD OPTIMIZED
    # Uses response cache to avoid reprocessing on every request
    # ===========================================================================

    # Check cache first (30 second TTL)
    cache_key = 'api_messages'
    cached = RESPONSE_CACHE.get(cache_key)
    if cached:
        response = jsonify(cached)
        response.headers['Cache-Control'] = 'public, max-age=30'
        response.headers['X-Cache'] = 'HIT'
        return response

    MAX_MESSAGES = 100  # HARD LIMIT: max messages per request (was 200)

    try:
        messages = load_messages()
        result_messages = []

        # PROTECTION: Reduced from 200 to 100 messages max
        for msg in messages[-MAX_MESSAGES:]:
            if not isinstance(msg, dict):
                continue

            text = msg.get('text', '').strip()

            # Detect alarm type
            alarm_type = 'Тривога'
            if 'БпЛА' in text or 'дрон' in text:
                alarm_type = 'БпЛА/Дрони'
            elif 'ракет' in text or 'балістич' in text:
                alarm_type = 'Ракетна загроза'
            elif 'Повітряна тривога' in text:
                alarm_type = 'Повітряна тривога'

            # Try to extract location and coordinates
            location = ''
            latitude = 48.3794  # Default: center of Ukraine
            longitude = 31.1656

            # Extract region/city from text
            if '**' in text:
                parts = text.split('**')
                for part in parts:
                    part = part.strip()
                    if '🚨' in part or '🟢' in part or 'область' in part.lower():
                        location = part.replace('🚨', '').replace('🟢', '').strip()
                        break

            # If no location found, try first line
            if not location and text:
                first_line = text.split('\n')[0].strip()
                location = first_line.replace('**', '').replace('🚨', '').replace('🟢', '').strip()[:100]

            # Try to get coordinates from UKRAINE_ADDRESSES_DB
            if location:
                location_lower = location.lower()
                for city_name, coords in UKRAINE_ADDRESSES_DB.items():
                    if city_name.lower() in location_lower or location_lower in city_name.lower():
                        latitude = coords['lat']
                        longitude = coords['lon']
                        if not location:
                            location = city_name
                        break

            # Get timestamp in Kyiv time
            import pytz
            kyiv_tz = pytz.timezone('Europe/Kiev')
            msg_time = msg.get('time', '') or msg.get('timestamp', '') or msg.get('date', '')

            # If no timestamp from message, use current time
            if not msg_time:
                msg_time = datetime.now(kyiv_tz).strftime('%d.%m.%Y %H:%M')
            else:
                # Try to parse and convert to Kyiv time if needed
                try:
                    # If it's a string, keep it as is (assuming it's already formatted)
                    if not isinstance(msg_time, str):
                        dt = datetime.fromtimestamp(msg_time, tz=pytz.UTC)
                        msg_time = dt.astimezone(kyiv_tz).strftime('%d.%m.%Y %H:%M')
                except:
                    # Fallback to original or current time
                    if isinstance(msg_time, str):
                        pass  # Keep original string
                    else:
                        msg_time = datetime.now(kyiv_tz).strftime('%d.%m.%Y %H:%M')

            result_messages.append({
                'type': alarm_type,
                'location': location or 'Україна',
                'timestamp': msg_time,
                'text': text[:300],  # First 300 chars
                'latitude': latitude,
                'longitude': longitude,
                'channel': msg.get('channel', ''),
            })

        # Sort by timestamp (newest first)
        result_messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Cache the result
        result_data = {
            'messages': result_messages,
            'count': len(result_messages),
            'timestamp': datetime.now().isoformat()
        }
        RESPONSE_CACHE.set(cache_key, result_data, ttl=30)

        response = jsonify(result_data)
        response.headers['Cache-Control'] = 'public, max-age=30'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['X-Cache'] = 'MISS'
        return response

    except Exception as e:
        print(f"[ERROR] /api/messages failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'messages': [], 'count': 0, 'error': str(e)}), 500

# ==================== ALARM STATUS API (для AlarmTimerWidget) ====================
_active_alarms_cache = {}  # region -> {active: bool, start_time: str, type: str}

@app.route('/api/alarm-status')
@protected_endpoint(is_heavy=False)  # PROTECTION: Rate limiting
def get_alarm_status():
    """Get current alarm status for regions - used by AlarmTimerWidget."""

    # HIGH-LOAD: Check cache first (15 second TTL)
    cache_key = 'api_alarm_status'
    cached = RESPONSE_CACHE.get(cache_key)
    if cached:
        response = jsonify(cached)
        response.headers['Cache-Control'] = 'public, max-age=15'
        response.headers['X-Cache'] = 'HIT'
        return response

    MAX_MESSAGES_TO_SCAN = 100  # HARD LIMIT

    try:
        messages = load_messages()
        alerts = {}

        # Process last 100 messages to find active alarms
        for msg in messages[-MAX_MESSAGES_TO_SCAN:]:
            if not isinstance(msg, dict):
                continue

            text = msg.get('text', '').lower()
            location = ''

            # Extract region from location field or text
            if '**' in msg.get('text', ''):
                parts = msg.get('text', '').split('**')
                for part in parts:
                    part = part.strip()
                    if 'область' in part.lower() or 'обл' in part.lower():
                        location = part.replace('🚨', '').replace('🟢', '').strip()
                        break

            if not location:
                location = msg.get('location', msg.get('text', '')[:50])

            # Get timestamp
            timestamp = msg.get('time', '') or msg.get('timestamp', '') or datetime.now().isoformat()

            # Determine if this is alarm start or end
            is_all_clear = 'відбій' in text
            is_alarm = 'тривога' in text or 'бпла' in text or 'дрон' in text or 'ракет' in text

            # Determine alarm type
            alarm_type = 'Повітряна тривога'
            if 'бпла' in text or 'дрон' in text:
                alarm_type = 'БпЛА/Дрони'
            elif 'ракет' in text or 'балістичн' in text:
                alarm_type = 'Ракетна загроза'

            if location:
                # Clean up location name
                region_key = location.replace('🚨', '').replace('🟢', '').strip()[:50]

                if is_all_clear:
                    alerts[region_key] = {
                        'active': False,
                        'start_time': None,
                        'type': None,
                        'end_time': timestamp
                    }
                elif is_alarm:
                    # Only set if not already active or if this is newer
                    if region_key not in alerts or not alerts[region_key].get('active'):
                        alerts[region_key] = {
                            'active': True,
                            'start_time': timestamp,
                            'type': alarm_type,
                            'end_time': None
                        }

        result_data = {
            'alerts': alerts,
            'timestamp': datetime.now().isoformat(),
            'count': sum(1 for a in alerts.values() if a.get('active'))
        }
        RESPONSE_CACHE.set(cache_key, result_data, ttl=15)

        response = jsonify(result_data)
        response.headers['Cache-Control'] = 'public, max-age=15'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['X-Cache'] = 'MISS'
        return response

    except Exception as e:
        print(f"[ERROR] /api/alarm-status failed: {e}")
        return jsonify({'alerts': {}, 'error': str(e)}), 500

# ==================== ALARM HISTORY API (для AlarmHistoryPage) ====================
@app.route('/api/alarm-history')
@protected_endpoint(is_heavy=True)  # PROTECTION: This can be heavy with large date ranges
def get_alarm_history():
    """Get alarm history for statistics - used by AlarmHistoryPage."""
    # ===========================================================================
    # HARDENED /api/alarm-history ENDPOINT
    # BEFORE: Could scan unlimited messages with days=365
    # AFTER:  Max 7 days lookback, max 200 results
    # ===========================================================================
    MAX_DAYS = 7       # HARD LIMIT: max days to look back (was unlimited)
    MAX_RESULTS = 200  # HARD LIMIT: max results to return (was 500)

    try:
        region = request.args.get('region', '')
        days = min(MAX_DAYS, max(1, int(request.args.get('days', 7))))  # PROTECTION: Cap at 7 days

        messages = load_messages()
        history = []

        # Calculate date cutoff
        cutoff_date = datetime.now() - timedelta(days=days)

        for msg in messages:
            if not isinstance(msg, dict):
                continue

            text = msg.get('text', '').lower()

            # Skip if not alarm-related
            if not any(kw in text for kw in ['тривога', 'відбій', 'бпла', 'дрон', 'ракет']):
                continue

            # Get timestamp
            timestamp_str = msg.get('time', '') or msg.get('timestamp', '')
            try:
                # Try to parse timestamp
                if timestamp_str:
                    # Handle various formats
                    for fmt in ['%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            timestamp = datetime.strptime(timestamp_str[:19], fmt)
                            break
                        except:
                            continue
                    else:
                        timestamp = datetime.now()
                else:
                    timestamp = datetime.now()

                # Skip if too old
                if timestamp < cutoff_date:
                    continue

            except:
                continue

            # Extract location
            location = msg.get('location', '')
            if not location and '**' in msg.get('text', ''):
                parts = msg.get('text', '').split('**')
                for part in parts:
                    if 'область' in part.lower():
                        location = part.strip()
                        break

            # Filter by region if specified
            if region and region.lower() not in location.lower():
                continue

            # Determine alarm type
            is_start = 'тривога' in text and 'відбій' not in text
            alarm_type = 'air_raid'
            if 'бпла' in text or 'дрон' in text:
                alarm_type = 'drone'
            elif 'ракет' in text:
                alarm_type = 'missile'

            history.append({
                'start_time': timestamp.isoformat(),
                'end_time': None,  # Would need to match with відбій
                'type': alarm_type,
                'region': location[:50],
                'is_start': is_start,
                'duration_minutes': 30  # Estimate
            })

        # Sort by time
        history.sort(key=lambda x: x['start_time'], reverse=True)

        # PROTECTION: Hard limit on results
        returned_history = history[:MAX_RESULTS]

        response = jsonify({
            'history': returned_history,
            'count': len(returned_history),
            'total_count': len(history),
            'truncated': len(history) > MAX_RESULTS,
            'region': region,
            'days': days,
            'timestamp': datetime.now().isoformat()
        })
        response.headers['Cache-Control'] = 'public, max-age=60'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        print(f"[ERROR] /api/alarm-history failed: {e}")
        return jsonify({'history': [], 'error': str(e)}), 500

# ==================== FAMILY SAFETY API (для FamilySafetyTab) ====================
# Using family_store (FamilyStore class) for persistent storage

@app.route('/api/family/status', methods=['POST'])
def get_family_status():
    """Get safety status for family members by their codes."""
    try:
        data = request.get_json() or {}
        codes = data.get('codes', [])

        statuses = family_store.get_statuses(codes)

        response = jsonify({'statuses': statuses, 'timestamp': datetime.now().isoformat()})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        print(f"[ERROR] /api/family/status failed: {e}")
        return jsonify({'statuses': {}, 'error': str(e)}), 500

@app.route('/api/family/update', methods=['POST'])
def update_family_status():
    """Update safety status for a family member."""
    try:
        data = request.get_json() or {}
        code = (data.get('code', '') or '').upper()
        is_safe = data.get('is_safe', False)
        name = data.get('name', '')
        fcm_token = data.get('fcm_token')
        device_id = data.get('device_id')

        if not code or len(code) < 4:
            return jsonify({'success': False, 'error': 'Invalid code'}), 400

        family_store.update_status(code, is_safe, name, fcm_token, device_id)

        response = jsonify({'success': True, 'code': code, 'is_safe': is_safe})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        print(f"[ERROR] /api/family/update failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/family/register-token', methods=['POST'])
def register_family_fcm_token():
    """Register FCM token for family member to receive SOS notifications."""
    try:
        data = request.get_json() or {}
        code = (data.get('code', '') or '').upper()
        fcm_token = data.get('fcm_token')
        device_id = data.get('device_id')

        if not code or len(code) < 4:
            return jsonify({'success': False, 'error': 'Invalid code'}), 400
        if not fcm_token:
            return jsonify({'success': False, 'error': 'Missing FCM token'}), 400

        family_store.register_fcm_token(code, fcm_token, device_id)

        response = jsonify({'success': True, 'code': code})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        print(f"[ERROR] /api/family/register-token failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/family/sos', methods=['POST'])
def send_family_sos():
    """Send SOS signal to family members via push notification."""
    try:
        data = request.get_json() or {}
        code = (data.get('code', '') or '').upper()
        family_codes = data.get('family_codes', [])
        sender_name = data.get('name', '')
        location = data.get('location')  # Optional: {lat, lng, address}

        print("[SOS] === SOS REQUEST RECEIVED ===")
        print(f"[SOS] Sender code: {code}")
        print(f"[SOS] Sender name: {sender_name}")
        print(f"[SOS] Family codes to notify: {family_codes}")

        if not code:
            return jsonify({'success': False, 'error': 'Invalid code'}), 400

        # Get tokens to notify and mark sender as needing help
        sos_data = family_store.send_sos(code, family_codes)
        tokens_to_notify = sos_data.get('tokens_to_notify', [])

        print(f"[SOS] Found {len(tokens_to_notify)} family members with FCM tokens")
        for t in tokens_to_notify:
            print(f"[SOS]   - {t['code']}: token={t['fcm_token'][:30]}...")

        # Send FCM push notifications to family members
        notified_count = 0
        if tokens_to_notify and init_firebase():
            from firebase_admin import messaging

            for member in tokens_to_notify:
                try:
                    # Prepare SOS notification
                    sos_message = f"🆘 {sender_name or code} потребує допомоги!"
                    if location and location.get('address'):
                        sos_message += f"\n📍 {location['address']}"

                    # Send FCM notification
                    message = messaging.Message(
                        token=member['fcm_token'],
                        data={
                            'type': 'sos',
                            'sender_code': code,
                            'sender_name': sender_name,
                            'title': '🆘 SOS Сигнал!',
                            'body': sos_message,
                            'location_lat': str(location.get('lat', '')) if location else '',
                            'location_lng': str(location.get('lng', '')) if location else '',
                            'location_address': location.get('address', '') if location else '',
                        },
                        android=messaging.AndroidConfig(
                            priority='high',
                            ttl=3600,
                        ),
                        apns=messaging.APNSConfig(
                            headers={
                                'apns-priority': '10',
                                'apns-push-type': 'alert',
                                'apns-expiration': '0',
                            },
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(
                                    alert=messaging.ApsAlert(
                                        title='🆘 SOS Сигнал!',
                                        body=sos_message,
                                    ),
                                    sound='default',
                                    badge=1,
                                    content_available=True,
                                    mutable_content=True,
                                ),
                            ),
                        ),
                    )

                    messaging.send(message)
                    notified_count += 1
                    print(f"[SOS] Notified {member['code']} via FCM")

                except Exception as fcm_error:
                    print(f"[SOS] Failed to notify {member['code']}: {fcm_error}")

        print(f"[SOS] Code {code} sent SOS to {len(family_codes)} family members, {notified_count} notified via FCM")

        response = jsonify({
            'success': True,
            'code': code,
            'notified': notified_count,
            'total_family': len(family_codes)
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        print(f"[ERROR] /api/family/sos failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/family/clear-sos', methods=['POST'])
def clear_family_sos():
    """Clear SOS status for a family member (they are OK now)."""
    try:
        data = request.get_json() or {}
        code = (data.get('code', '') or '').upper()

        if not code:
            return jsonify({'success': False, 'error': 'Invalid code'}), 400

        family_store.clear_sos(code)

        response = jsonify({'success': True, 'code': code})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        print(f"[ERROR] /api/family/clear-sos failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/family/check-tokens', methods=['POST'])
def check_family_tokens():
    """Debug endpoint to check which family codes have FCM tokens registered."""
    try:
        data = request.get_json() or {}
        codes = data.get('codes', [])

        if not codes:
            return jsonify({'success': False, 'error': 'No codes provided'}), 400

        result = {}
        for code in codes:
            code_upper = code.upper()
            status = family_store.get_status(code_upper)
            # Check if member has FCM token
            family_data = family_store._load()
            member_data = family_data.get('members', {}).get(code_upper, {})
            has_token = bool(member_data.get('fcm_token'))

            result[code_upper] = {
                'has_token': has_token,
                'last_active': member_data.get('last_active'),
                'status': status,
            }

        response = jsonify({'success': True, 'codes': result})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        print(f"[ERROR] /api/family/check-tokens failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test_parse')
def test_parse():
    """Test endpoint to manually test message parsing without auth."""
    test_message = "Чернігівщина: 1 БпЛА на Козелець 1 БпЛА на Носівку 1 БпЛА неподалік Ічні 2 БпЛА на Куликівку 2 БпЛА між Корюківкою та Меною Сумщина: 3 БпЛА в районі Конотопу ㅤ ➡Підписатися"

    try:
        print("="*50)
        print("MANUAL TEST STARTED")
        print("="*50)
        tracks = process_message(test_message, 'TEST_1', '2025-09-05 17:20:00', 'test')
        print("="*50)
        print("MANUAL TEST COMPLETED")
        print("="*50)

        return jsonify({
            'success': True,
            'message': test_message,
            'tracks_count': len(tracks) if tracks else 0,
            'tracks': tracks,
            'test_time': datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in test_parse: {error_details}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_details
        }), 500


@app.route('/locate')
def locate_settlement():
    """Locate a settlement or raion by name. Query param: q=<name>
    Returns: {status:'ok', name, lat, lng, source:'dict'|'geocode'|'fallback'} or {status:'not_found'}
    Lightweight normalization reusing UA_CITY_NORMALIZE and CITY_COORDS. Falls back to ensure_city_coords (may geocode if key allowed).
    """
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'status':'empty'}), 400
    raw = q.lower()
    # Basic cleanup similar to parser's normalization
    raw = re.sub(r'["`ʼ’\'".,:;()]+','', raw)
    raw = re.sub(r'\s+',' ', raw)
    # Try direct dict match
    key = raw
    if key in UA_CITY_NORMALIZE:
        key = UA_CITY_NORMALIZE[key]
    # Heuristic accusative -> nominative (simple feminine endings) if still not found
    if key not in CITY_COORDS and len(key) > 4 and key.endswith(('у','ю')):
        alt = key[:-1] + 'а'
        if alt in CITY_COORDS:
            key = alt
    # Direct dictionary coordinate fetch
    if key in CITY_COORDS:
        lat,lng = CITY_COORDS[key]
        return jsonify({'status':'ok','name':key.title(),'lat':lat,'lng':lng,'source':'dict'})
    # Check full settlements index (all cities/villages loaded from external file)
    if 'SETTLEMENTS_INDEX' in globals() and key in SETTLEMENTS_INDEX:
        lat,lng = SETTLEMENTS_INDEX[key]
        return jsonify({'status':'ok','name':key.title(),'lat':lat,'lng':lng,'source':'settlement'})
    # If not exact, attempt prefix suggestions for UI autocomplete
    if 'SETTLEMENTS_INDEX' in globals() and len(key) >= 3:
        pref = key
        matches = [n for n in SETTLEMENTS_INDEX.keys() if n.startswith(pref)][:15]
        if not matches and pref.endswith(('у','ю')):
            pref2 = pref[:-1] + 'а'
            matches = [n for n in SETTLEMENTS_INDEX.keys() if n.startswith(pref2)][:15]
        if matches:
            return jsonify({'status':'suggest','query':q,'matches':matches})
    # Attempt dynamic ensure (geocode) unless negative cache prohibits
    coords = None
    try:
        coords = ensure_city_coords(key)
    except Exception:
        coords = None
    if coords:
        lat,lng = coords
        return jsonify({'status':'ok','name':key.title(),'lat':lat,'lng':lng,'source':'geocode'})
    return jsonify({'status':'not_found','query':q}), 404

@app.route('/hide_marker', methods=['POST'])
def hide_marker():
    """Store a marker key so it's excluded from subsequent /data responses."""
    try:
        payload = request.get_json(force=True) or {}
        lat = round(float(payload.get('lat')), 3)
        lng = round(float(payload.get('lng')), 3)
        text = (payload.get('text') or '').strip()
        source = (payload.get('source') or '').strip()
        marker_key = f"{lat},{lng}|{text}|{source}"
        hidden = load_hidden()
        if marker_key not in hidden:
            hidden.append(marker_key)
            save_hidden(hidden)
        return jsonify({'status':'ok','hidden_count':len(hidden)})
    except Exception as e:
        log.warning(f"hide_marker error: {e}")
        return jsonify({'status':'error','error':str(e)}), 400

@app.route('/unhide_marker', methods=['POST'])
def unhide_marker():
    """Remove previously hidden marker by key or by lat,lng plus text/source prefix match."""
    try:
        payload = request.get_json(force=True) or {}
        key = (payload.get('key') or '').strip()
        hidden = load_hidden()
        changed = False
        if key:
            if key.isdigit():
                idx = int(key)
                if 0 <= idx < len(hidden):
                    del hidden[idx]
                    changed = True
            elif key in hidden:
                hidden.remove(key)
                changed = True
        else:
            lat = payload.get('lat')
            lng = payload.get('lng')
            text = (payload.get('text') or '').strip()
            source = (payload.get('source') or '').strip()
            if lat is not None and lng is not None:
                try:
                    lat_r = round(float(lat), 3)
                    lng_r = round(float(lng), 3)
                except Exception:
                    lat_r = lng_r = None
                base_prefix = f"{lat_r},{lng_r}|" if lat_r is not None else None
                if base_prefix:
                    for h in list(hidden):
                        if not h.startswith(base_prefix):
                            continue
                        try:
                            _, htext, hsource = h.split('|', 2)
                        except ValueError:
                            continue
                        if source and hsource != source:
                            continue
                        if not text or htext.startswith(text) or text.startswith(htext):
                            hidden.remove(h)
                            changed = True
        if changed:
            save_hidden(hidden)
        else:
            log.info(f"unhide_marker: no change for key='{key}' payload={payload}")
        return jsonify({'status': 'ok', 'removed': changed, 'remaining': len(hidden)})
    except Exception as e:
        log.warning(f"unhide_marker error: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 400

# Guard against duplicate registration if this file is imported twice or a previous
# health endpoint already exists (avoids Flask AssertionError: overwriting endpoint)
if 'health' not in app.view_functions:
    @app.route('/health')
    def health():  # type: ignore
        now = time.time()

        # Basic stats + prune visitors
        with ACTIVE_LOCK:
            for vid, meta in list(ACTIVE_VISITORS.items()):
                ts = meta if isinstance(meta,(int,float)) else meta.get('ts',0)
                if now - ts > ACTIVE_TTL:
                    del ACTIVE_VISITORS[vid]
            visitors = len(ACTIVE_VISITORS)

        # Add memory manager metrics
        memory_metrics = {
            'cleanups_total': _memory_manager.metrics['cleanups'],
            'items_removed': _memory_manager.metrics['items_removed'],
            'memory_freed_mb': round(_memory_manager.metrics['memory_freed_mb'], 1),
            'cache_sizes': {
                'response_cache': len(RESPONSE_CACHE.cache),
                'threat_cache': len(_threat_classification_cache),
                'telegram_alerts': len(_telegram_alert_sent),
                'region_topics': len(_region_topic_cache)
            }
        }

        resp = jsonify({
            'status':'ok',
            'server_time': int(now),
            'pid': os.getpid(),
            'messages':len(load_messages()),
            'auth': AUTH_STATUS,
            'visitors': visitors,
            'firebase_initialized': firebase_initialized,
            'devices_count': len(device_store._load()) if device_store else 0,
            'ai_route': 'regex',
            'telegram_last_fetch_ts': getattr(parser_service, 'TELEGRAM_LAST_FETCH_TS', 0),
            'telegram_fetch_phase': getattr(parser_service, 'TELEGRAM_FETCH_PHASE', 'unknown'),
            'telegram_last_error': getattr(parser_service, 'TELEGRAM_LAST_ERROR', ''),
            'fetch_thread_started': FETCH_THREAD_STARTED,
            'fetch_thread_alive': bool(FETCH_THREAD and FETCH_THREAD.is_alive()),
            'fetch_thread_started_at': int(FETCH_THREAD_STARTED_AT) if FETCH_THREAD_STARTED_AT else 0,
            'fetch_start_delay': globals().get('FETCH_START_DELAY', 0),
            'memory': memory_metrics
        })
        resp.headers['Cache-Control'] = 'no-store'
        return resp

@app.route('/ads.txt')
def ads_txt():
    """Serve ads.txt for ad networks verification"""
    from flask import send_from_directory
    return send_from_directory('static', 'ads.txt', mimetype='text/plain')

@app.route('/app-ads.txt')
def app_ads_txt():
    """Serve app-ads.txt for mobile app ad networks verification (Google AdMob)"""
    return send_from_directory('static', 'app-ads.txt', mimetype='text/plain')

@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt for search engines with proper SEO headers"""
    response = send_from_directory('static', 'robots.txt', mimetype='text/plain')
    response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
    response.headers['X-Robots-Tag'] = 'noindex'  # Don't index robots.txt itself
    return response

@app.route('/sitemap.xml')
def sitemap_xml():
    """Serve dynamic sitemap.xml for search engines with proper headers"""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')

    sitemap_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">

  <!-- ГОЛОВНА СТОРІНКА -->
  <url>
    <loc>https://neptun.in.ua/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>1.0</priority>
    <image:image>
      <image:loc>https://neptun.in.ua/static/og-image.png</image:loc>
      <image:title>Карта тривог та шахедів України онлайн - NEPTUN</image:title>
      <image:caption>Карта повітряних тривог України в реальному часі. Відстеження шахедів, дронів, ракет 24/7</image:caption>
    </image:image>
    <xhtml:link rel="alternate" hreflang="uk" href="https://neptun.in.ua/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://neptun.in.ua/"/>
  </url>

  <!-- ФУНКЦІОНАЛЬНІ СТОРІНКИ -->
  <url>
    <loc>https://neptun.in.ua/map</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.95</priority>
  </url>

  <url>
    <loc>https://neptun.in.ua/blackouts</loc>
    <lastmod>{today}</lastmod>
    <changefreq>hourly</changefreq>
    <priority>0.9</priority>
  </url>

  <!-- РЕГІОНАЛЬНІ СТОРІНКИ -->
  <url>
    <loc>https://neptun.in.ua/region/kyiv</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/kyivska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.88</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/kharkivska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.88</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/odeska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.88</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/dnipropetrovska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.88</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/lvivska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.87</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/zaporizka</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.87</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/mykolaivska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.86</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/poltavska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.85</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/vinnytska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.85</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/zhytomyrska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.84</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/cherkaska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.84</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/sumska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.84</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/chernihivska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.84</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/khmelnytska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.83</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/volynska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.83</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/rivnenska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.83</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/ternopilska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.82</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/ivano-frankivska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.82</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/zakarpatska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.82</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/chernivetska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.81</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/kirovohradska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.81</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/khersonska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.85</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/donetska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.86</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/region/luhanska</loc>
    <lastmod>{today}</lastmod>
    <changefreq>always</changefreq>
    <priority>0.85</priority>
  </url>

  <!-- ІНФОРМАЦІЙНІ СТОРІНКИ -->
  <url>
    <loc>https://neptun.in.ua/about</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/faq</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/privacy</loc>
    <lastmod>{today}</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.3</priority>
  </url>
  <url>
    <loc>https://neptun.in.ua/terms</loc>
    <lastmod>{today}</lastmod>
    <changefreq>yearly</changefreq>
    <priority>0.3</priority>
  </url>

</urlset>'''

    response = Response(sitemap_content, mimetype='application/xml')
    response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.route('/presence', methods=['POST'])
def presence():
    """Register active viewers and return synchronized counts per platform."""
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr) or 'unknown'
    rate_key = f"{client_ip}_presence"
    now_time = time.time()
    recent = [ts for ts in request_counts[rate_key] if now_time - ts < PRESENCE_RATE_WINDOW]
    if len(recent) >= PRESENCE_RATE_LIMIT:
        return jsonify({'error': 'presence rate limited', 'retry_after': PRESENCE_RATE_WINDOW}), 429
    recent.append(now_time)
    request_counts[rate_key] = recent

    data = request.get_json(silent=True) or {}
    vid = str(data.get('id') or '').strip()
    if not vid:
        return jsonify({'status': 'error', 'error': 'id required'}), 400

    now = time.time()
    blocked = set(load_blocked())
    if vid in blocked:
        return jsonify({'status': 'blocked'})

    remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    ua = request.headers.get('User-Agent', '')[:300]
    platform_label = _normalize_platform(data.get('platform') or '', ua)
    nickname = data.get('nickname', '')[:20] if data.get('nickname') else ''  # Max 20 chars

    # DISABLED: visit_stats in memory - using SQLite instead
    # stats = _load_visit_stats()
    # if vid not in stats:
    #     stats[vid] = now
    #     if int(now) % 50 == 0 or len(stats) > 2500:
    #         _prune_visit_stats()
    #     _save_visit_stats()

    try:
        _update_recent_visits(vid)
    except Exception as e:
        log.warning(f"recent visits update failed: {e}")

    # Record visit in SQLite for accurate daily/weekly counts (thread-safe)
    try:
        sql_record_visit(vid)
    except Exception as e:
        log.warning(f"sql_record_visit failed: {e}")

    try:
        record_visit_sql(vid, now, remote_ip)
    except Exception:
        pass

    db_first = None
    try:
        with _visits_db_conn() as conn:
            cur = conn.execute("SELECT first_seen FROM visits WHERE id=?", (vid,))
            row = cur.fetchone()
            if row and row[0]:
                try:
                    db_first = float(row[0])
                except Exception:
                    db_first = None
    except Exception:
        pass

    with ACTIVE_LOCK:
        prev = ACTIVE_VISITORS.get(vid) if isinstance(ACTIVE_VISITORS.get(vid), dict) else {}
        first_seen = prev.get('first') or db_first or now
        # Simplified visitor data to save memory
        ACTIVE_VISITORS[vid] = {
            'ts': now,
            'first': first_seen,
            'platform': platform_label,
        }
        # Cleanup stale visitors (by TTL only - no artificial limit)
        for key, meta in list(ACTIVE_VISITORS.items()):
            ts = meta if isinstance(meta, (int, float)) else meta.get('ts', 0)
            if now - ts > ACTIVE_TTL:
                del ACTIVE_VISITORS[key]

        platform_counts = {}
        for meta in ACTIVE_VISITORS.values():
            bucket = meta.get('platform') or 'web'
            platform_counts[bucket] = platform_counts.get(bucket, 0) + 1
        total = sum(platform_counts.values())

    apps_total = platform_counts.get('android', 0) + platform_counts.get('ios', 0)
    payload = {
        'status': 'ok',
        'visitors': total,
        'platforms': {
            'web': platform_counts.get('web', 0),
            'android': platform_counts.get('android', 0),
            'ios': platform_counts.get('ios', 0),
            'other': sum(v for k, v in platform_counts.items() if k not in VALID_PLATFORMS)
        },
        'apps': apps_total
    }
    return jsonify(payload)

@app.route('/raion_alarms')
def raion_alarms():
    # ...existing code...

    # Expose current active district air alarms
    out = []
    now = time.time()
    for key, info in list(RAION_ALARMS.items()):
        # Optional expiry cleanup (e.g., 3h stale auto-clear)
        if now - info.get('since', now) > 3*3600:
            RAION_ALARMS.pop(key, None)
            continue
        out.append({
            'raion': key,
            'place': info['place'],
            'lat': info['lat'],
            'lng': info['lng'],
            'since': info['since']
        })
    return jsonify({'alarms': out, 'count': len(out)})

# SSE stream endpoint
@app.route('/stream')
def stream():
    # MEMORY PROTECTION: Reject if too many subscribers
    if len(SUBSCRIBERS) >= MAX_STREAM_SUBSCRIBERS:
        log.warning(f"[SSE] Rejected /stream connection - limit reached ({MAX_STREAM_SUBSCRIBERS})")
        return jsonify({'error': 'Server busy, please poll /api/data'}), 503
    
    def gen():
        q = queue.Queue()
        SUBSCRIBERS.add(q)
        last_ping = time.time()
        try:
            while True:
                try:
                    item = q.get(timeout=5)
                    yield f'data: {item}\n\n'
                except Exception:
                    pass
                now_t = time.time()
                if now_t - last_ping > 25:
                    last_ping = now_t
                    yield ': ping\n\n'
        except GeneratorExit:
            pass
        finally:
            SUBSCRIBERS.discard(q)
    headers = {
        'Cache-Control': 'no-store',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    }
    return Response(gen(), mimetype='text/event-stream', headers=headers)

def broadcast_new(tracks):
    """Send new geo tracks to all connected SSE subscribers."""
    if not tracks:
        return
    payload = json.dumps({'tracks': tracks}, ensure_ascii=False)
    dead = []
    for q in list(SUBSCRIBERS):
        try:
            q.put_nowait(payload)
        except Exception:
            dead.append(q)
    for d in dead:
        SUBSCRIBERS.discard(d)
def broadcast_control(event:dict):
    try:
        payload = json.dumps({'control': event}, ensure_ascii=False)
    except Exception:
        return
    dead = []
    for q in list(SUBSCRIBERS):
        try:
            q.put_nowait(payload)
        except Exception:
            dead.append(q)

# ---------------- Admin & blocking endpoints -----------------

# ==== Externalized modules wiring ====
parser_service.bind_dependencies(globals())
process_message = parser_service.process_message
parse_trajectory_from_message = parser_service.parse_trajectory_from_message
extract_shahed_course_info = parser_service.extract_shahed_course_info
fetch_loop = parser_service.fetch_loop
_extract_oblast_from_text = parser_service._extract_oblast_from_text
calculate_bearing = parser_service.calculate_bearing
RE_PARENS_STRIP = parser_service.RE_PARENS_STRIP
RE_OBLAST_IN_PARENS = parser_service.RE_OBLAST_IN_PARENS
RE_CITY_BEFORE_PARENS = parser_service.RE_CITY_BEFORE_PARENS
RE_OBLAST_SUFFIX = parser_service.RE_OBLAST_SUFFIX
RE_OBLAST_PARENS_NAME = parser_service.RE_OBLAST_PARENS_NAME
RE_OBLAST_ANYWHERE = parser_service.RE_OBLAST_ANYWHERE
RE_PLACE_PREFIX = parser_service.RE_PLACE_PREFIX
RE_MULTI_SPACE = parser_service.RE_MULTI_SPACE
RE_OBLAST_SUFFIX_REMOVE = parser_service.RE_OBLAST_SUFFIX_REMOVE
RE_RAION_SUFFIX_REMOVE = parser_service.RE_RAION_SUFFIX_REMOVE
RE_REGION_IN_TEXT = parser_service.RE_REGION_IN_TEXT
UA_CITIES = parser_service.UA_CITIES
UA_CITY_NORMALIZE = parser_service.UA_CITY_NORMALIZE
NAME_REGION_MAP = parser_service.NAME_REGION_MAP
DIRECTION_VECTORS = parser_service.DIRECTION_VECTORS
DIRECTION_FROM_KEYWORDS = parser_service.DIRECTION_FROM_KEYWORDS
DIRECTION_COURSE_KEYWORDS = parser_service.DIRECTION_COURSE_KEYWORDS
admin_routes.bind_dependencies(globals())
admin_routes.register_admin_routes(app)

# Ensure Telegram fetch loop starts in WSGI mode
if client and not FETCH_THREAD_STARTED:
    try:
        start_fetch_thread()
    except Exception as e:
        log.error(f'Auto start_fetch_thread failed: {e}')

if __name__ == '__main__':
    # Local / container direct run (not needed if a WSGI server like gunicorn is used)
    port = int(os.getenv('PORT', '5000'))
    host = os.getenv('HOST', '0.0.0.0')
    log.info(f'Launching Flask app on {host}:{port}')
    # Eager start (still guarded) so that fetch begins even without first HTTP request locally
    try:
        _init_background()
    except Exception:
        pass
    app.run(host=host, port=port, debug=False)
