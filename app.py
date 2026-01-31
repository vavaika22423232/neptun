# pyright: reportUnusedVariable=false, reportRedeclaration=false, reportGeneralTypeIssues=false
# pyright: reportUndefinedVariable=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false
# type: ignore
# pylint: disable=all
# fmt: off
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

    def clear_expired(self):
        """Remove expired entries (call periodically)."""
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

# Global response cache
RESPONSE_CACHE = ResponseCache(default_ttl=30)

# Cached messages - avoid repeated file reads
_MESSAGES_CACHE = {'data': None, 'expires': 0}
_MESSAGES_CACHE_TTL = 5  # 5 second cache for messages

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

# OpenCage geocoding integration (with persistent cache)
try:
    from opencage_geocoder import geocode as opencage_geocode, get_cache_stats
    GEOCODER_AVAILABLE = True
    print("INFO: OpenCage geocoding ENABLED", flush=True)
except ImportError as e:
    GEOCODER_AVAILABLE = False
    def opencage_geocode(_city, _region=None):
        return None
    def get_cache_stats():
        return {}
    print(f"WARNING: OpenCage geocoder not available: {e}", flush=True)


# === LEGACY COMPATIBILITY: Proxy dicts that use OpenCage ===
# WARNING: These proxies DON'T have region context - should be replaced with ensure_city_coords_with_message_context
class _OpenCageProxy(dict):
    """Dict-like object that proxies all lookups to OpenCage geocoder.
    WARNING: No region context - use ensure_city_coords_with_message_context instead!"""
    def __getitem__(self, key):
        print(f"[WARNING] CITY_COORDS['{key}'] called WITHOUT region context - may return wrong city!", flush=True)
        coords = opencage_geocode(key)
        if coords:
            return coords
        raise KeyError(key)
    
    def __contains__(self, key):
        return opencage_geocode(key) is not None
    
    def get(self, key, default=None):
        # Don't spam warnings for known major cities that are unambiguous
        known_major = {'харків', 'київ', 'одеса', 'дніпро', 'львів', 'миколаїв', 'запоріжжя', 'херсон', 'суми', 'полтава', 'чернігів'}
        if key and key.lower() not in known_major:
            print(f"[WARNING] CITY_COORDS.get('{key}') called WITHOUT region context - may return wrong city!", flush=True)
        coords = opencage_geocode(key)
        return coords if coords else default
    
    def keys(self):
        return []  # Empty - we don't enumerate
    
    def items(self):
        return []
    
    def values(self):
        return []

# These now proxy to OpenCage instead of being static dicts
CITY_COORDS = _OpenCageProxy()
SETTLEMENTS_INDEX = _OpenCageProxy()

def ensure_city_coords(city_name, region=None, context=None):
    """Legacy function - now uses OpenCage.
    
    Args:
        city_name: City name to geocode
        region: Optional region name (e.g., "Харківська")
        context: Optional message text to extract region from "(Область обл.)" format
    """
    if not city_name:
        return None
    # If no region but context provided, extract region from context
    if not region and context:
        region = _extract_oblast_from_text(context) or region
    coords = opencage_geocode(city_name, region)
    if coords:
        return coords
    # AI fallback for disambiguation (if enabled)
    if context and GROQ_ENABLED:
        try:
            ai_hint = _ai_geocode_hint(city_name, context, region)
            if ai_hint:
                ai_city = ai_hint.get('city') or city_name
                ai_region = ai_hint.get('region') or region
                ai_query = ai_hint.get('query')
                if ai_query:
                    coords = opencage_geocode(ai_query, None)
                    if coords:
                        return coords
                if ai_city or ai_region:
                    coords = opencage_geocode(ai_city or city_name, ai_region)
                    if coords:
                        return coords
        except Exception:
            pass
    return None

def ensure_city_coords_with_message_context(city_name, message_text=None):
    """Legacy function - now uses OpenCage with region extraction"""
    if not city_name:
        return None
    region = None
    if message_text:
        # PRIORITY: Extract region from parentheses format "Місто (Область обл.)"
        region = _extract_oblast_from_text(message_text)
    print(f"[GEOCODE_CONTEXT] city='{city_name}', extracted_region='{region}'", flush=True)
    coords = opencage_geocode(city_name, region)
    if coords:
        return coords
    # AI fallback for geocoding disambiguation
    if message_text and GROQ_ENABLED:
        try:
            ai_hint = _ai_geocode_hint(city_name, message_text, region)
            if ai_hint:
                ai_city = ai_hint.get('city') or city_name
                ai_region = ai_hint.get('region') or region
                ai_query = ai_hint.get('query')
                if ai_query:
                    coords = opencage_geocode(ai_query, None)
                    if coords:
                        return coords
                if ai_city or ai_region:
                    coords = opencage_geocode(ai_city or city_name, ai_region)
                    if coords:
                        return coords
        except Exception:
            pass
    return None


# Groq AI integration for intelligent geocoding
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_MODEL = 'llama-3.3-70b-versatile'
GROQ_ENABLED = bool(GROQ_API_KEY)

# AI request caching and rate limiting
_groq_cache = {}  # Simple in-memory cache {hash: (result, timestamp)}
_groq_cache_ttl = 1800  # Cache TTL: 30 min (reduced from 60 min)
_groq_cache_max_size = 200  # MEMORY PROTECTION: Max cached AI responses (reduced from 500)
_groq_last_request = 0  # Timestamp of last request
_groq_min_interval = 3.0  # Minimum 3 seconds between requests (was 2)
_groq_daily_cooldown_until = 0  # If set, skip ALL AI until this timestamp
_groq_429_backoff = 0  # Exponential backoff counter
_groq_requests_this_minute = 0  # Counter for requests in current minute
_groq_minute_start = 0  # Start of current minute window
_groq_max_per_minute = 5  # Max 5 requests per minute (cost optimization)

def _groq_is_available():
    """Check if Groq AI is currently available (not in cooldown)"""
    global _groq_daily_cooldown_until
    if not GROQ_ENABLED:
        return False
    if _groq_daily_cooldown_until > 0:
        if time.time() < _groq_daily_cooldown_until:
            return False
        else:
            # Cooldown expired, reset
            _groq_daily_cooldown_until = 0
            print("INFO: Groq AI cooldown expired, resuming")
    return True

if GROQ_ENABLED:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("INFO: Groq AI initialized successfully")
    except ImportError:
        GROQ_ENABLED = False
        groq_client = None
        print("WARNING: Groq library not installed. Run: pip install groq")
    except Exception as e:
        GROQ_ENABLED = False
        groq_client = None
        print(f"WARNING: Groq initialization failed: {e}")
else:
    groq_client = None
    print("INFO: Groq AI disabled (no API key)")

# --- Groq AI helper functions (geocoding, classification, trajectory) ---
def _groq_cache_get(key: str):
    entry = _groq_cache.get(key)
    if not entry:
        return None
    value, ts = entry
    if time.time() - ts > _groq_cache_ttl:
        _groq_cache.pop(key, None)
        return None
    return value

def _groq_cache_set(key: str, value):
    if len(_groq_cache) >= _groq_cache_max_size:
        # Drop oldest 10% to avoid unbounded growth
        cutoff = max(1, int(_groq_cache_max_size * 0.1))
        for old_key in sorted(_groq_cache.keys(), key=lambda k: _groq_cache[k][1])[:cutoff]:
            _groq_cache.pop(old_key, None)
    _groq_cache[key] = (value, time.time())

def _groq_can_request() -> bool:
    global _groq_last_request, _groq_requests_this_minute, _groq_minute_start
    if not _groq_is_available() or not groq_client:
        return False
    now = time.time()
    if now - _groq_minute_start > 60:
        _groq_minute_start = now
        _groq_requests_this_minute = 0
    if _groq_requests_this_minute >= _groq_max_per_minute:
        return False
    # Minimum interval
    wait = _groq_min_interval - (now - _groq_last_request)
    if wait > 0:
        time.sleep(wait)
    _groq_last_request = time.time()
    _groq_requests_this_minute += 1
    return True

def _extract_json_from_text(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        return None
    return None

def _groq_request_json(cache_key: str, system_prompt: str, user_prompt: str, max_tokens: int = 256) -> dict | None:
    if not GROQ_ENABLED or not groq_client or not _groq_can_request():
        return None
    cached = _groq_cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content if resp and resp.choices else None
        data = _extract_json_from_text(content or '')
        if data is not None:
            _groq_cache_set(cache_key, data)
        return data
    except Exception as e:
        # Backoff on rate limits
        if '429' in str(e):
            global _groq_daily_cooldown_until, _groq_429_backoff
            _groq_429_backoff = min(_groq_429_backoff + 1, 6)
            _groq_daily_cooldown_until = time.time() + (60 * (2 ** _groq_429_backoff))
            print(f"WARNING: Groq rate limited, cooldown set for {_groq_429_backoff} step(s)")
        return None

def _ai_geocode_hint(city_name: str, message_text: str, region_hint: str | None = None) -> dict | None:
    if not GROQ_ENABLED or not message_text:
        return None
    cache_key = f"geocode_hint:{hashlib.sha256((city_name + '|' + message_text[:500] + '|' + (region_hint or '')).encode('utf-8')).hexdigest()}"
    system_prompt = (
        "You extract Ukrainian geographic locations for geocoding. "
        "Return ONLY valid JSON with keys: city, region, raion, query, confidence. "
        "Use Ukrainian names, region should be full like 'Харківська область' if known. "
        "If unknown, use null."
    )
    user_prompt = (
        f"Message: {message_text}\n"
        f"City hint: {city_name}\n"
        f"Region hint: {region_hint or ''}\n"
        "Extract best geocoding hint for Ukraine."
    )
    return _groq_request_json(cache_key, system_prompt, user_prompt, max_tokens=200)

def classify_threat_with_ai(message_text: str) -> dict | None:
    if not GROQ_ENABLED or not message_text:
        return None
    cache_key = f"threat_class:{hashlib.sha256(message_text[:500].encode('utf-8')).hexdigest()}"
    system_prompt = (
        "You classify Ukrainian air threat messages. Return ONLY JSON with keys: "
        "threat_type, emoji, priority, confidence. "
        "threat_type must be one of: shahed, ballistic, cruise, kab, drone, explosion, artillery, pusk, unknown. "
        "priority is 1-5."
    )
    user_prompt = f"Message: {message_text}"
    return _groq_request_json(cache_key, system_prompt, user_prompt, max_tokens=120)

def extract_trajectory_with_ai(text: str) -> dict | None:
    if not GROQ_ENABLED or not text:
        return None
    cache_key = f"traj_extract:{hashlib.sha256(text[:500].encode('utf-8')).hexdigest()}"
    system_prompt = (
        "Extract drone trajectory info from Ukrainian text. Return ONLY JSON with keys: "
        "source_type (city|region|direction|unknown), source_name, source_position, "
        "target_type (city|region|direction|unknown), target_name, confidence (0-1)."
    )
    user_prompt = f"Text: {text}"
    return _groq_request_json(cache_key, system_prompt, user_prompt, max_tokens=200)

def predict_route_with_ai(source_text: str) -> dict | None:
    if not GROQ_ENABLED or not source_text:
        return None
    cache_key = f"route_pred:{hashlib.sha256(source_text[:200].encode('utf-8')).hexdigest()}"
    system_prompt = (
        "Predict likely next Ukrainian regions (oblasts) for an air threat. "
        "Return ONLY JSON with keys: predicted_targets (array of oblast or city names), confidence (0-1). "
        "Prefer neighboring oblasts only."
    )
    user_prompt = f"Source: {source_text}"
    return _groq_request_json(cache_key, system_prompt, user_prompt, max_tokens=120)

# Context-aware geocoding integration
try:
    from context_aware_geocoder import get_context_aware_geocoding
    CONTEXT_GEOCODER_AVAILABLE = True
except ImportError:
    CONTEXT_GEOCODER_AVAILABLE = False
    def get_context_aware_geocoding(_text):
        return []
    nlp = None
    SPACY_AVAILABLE = False
    print("WARNING: SpaCy Ukrainian model not available. Using fallback geocoding methods.")
try:
    from telethon.errors import (
        AuthKeyDuplicatedError,
        AuthKeyUnregisteredError,
        FloodWaitError,
        SessionPasswordNeededError,
    )
except ImportError:
    # Fallback dummies if some names not present in current Telethon version
    class AuthKeyDuplicatedError(Exception):
        pass
    class AuthKeyUnregisteredError(Exception):
        pass
    class FloodWaitError(Exception):
        def __init__(self, seconds=60): self.seconds = seconds
    class SessionPasswordNeededError(Exception):  # noqa: F841
        pass
import math

from telethon.sessions import StringSession


# ══════════════════════════════════════════════════════════════════════════════
# [SECTION 5] UTILITIES & HELPERS
# ══════════════════════════════════════════════════════════════════════════════
# General-purpose utility functions used across the application.
# - Geographic calculations (bearing, distance, coordinates)
# - Text parsing and normalization
# - Caching helpers
# - File I/O utilities

# --- Firebase Topic Mapping (used for FCM push notifications) ---
# Maps Ukrainian region names to Firebase topic identifiers
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

# --- Oblast ID Mapping (UA ISO codes for ID-based filtering) ---
# Maps Ukrainian region names to ISO 3166-2:UA codes
REGION_TO_OBLAST_ID = {
    'м. Київ': 'UA-30',
    'Київ': 'UA-30',
    'Київська область': 'UA-32',
    'Дніпропетровська область': 'UA-12',
    'Харківська область': 'UA-63',
    'Одеська область': 'UA-51',
    'Львівська область': 'UA-46',
    'Донецька область': 'UA-14',
    'Запорізька область': 'UA-23',
    'Вінницька область': 'UA-05',
    'Житомирська область': 'UA-18',
    'Черкаська область': 'UA-71',
    'Чернігівська область': 'UA-74',
    'Полтавська область': 'UA-53',
    'Сумська область': 'UA-59',
    'Миколаївська область': 'UA-48',
    'Херсонська область': 'UA-65',
    'Кіровоградська область': 'UA-35',
    'Хмельницька область': 'UA-68',
    'Рівненська область': 'UA-56',
    'Волинська область': 'UA-07',
    'Тернопільська область': 'UA-61',
    'Івано-Франківська область': 'UA-26',
    'Закарпатська область': 'UA-21',
    'Чернівецька область': 'UA-77',
    'Луганська область': 'UA-44',
    'АР Крим': 'UA-43',
    'Севастополь': 'UA-40',
}

# --- Known launch sites (incl. RF) for explicit "пуск" markers ---
# NOTE: These are approximate coordinates to place markers on launch locations.
LAUNCH_SITES = {
    # РФ (основные точки запусков)
    'приморск-ахтарск': (46.0514, 38.1742),
    'приморск-ахтарская': (46.0514, 38.1742),
    'приморськ-ахтарськ': (46.0514, 38.1742),
    'приморськ-ахтарська': (46.0514, 38.1742),
    'халино': (51.7510, 36.2950),
    'курск': (51.7304, 36.1938),
    'курська': (51.7304, 36.1938),
    'орел': (52.9708, 36.0635),
    'орёл': (52.9708, 36.0635),
    'орла': (52.9708, 36.0635),
    'орле': (52.9708, 36.0635),
    'орел-південний': (52.8950, 36.0010),
    'орел-южный': (52.8950, 36.0010),
    'орел южный': (52.8950, 36.0010),
    # РФ (доп. аэродромы)
    'шайковка': (54.2281, 34.2856),
    'энгельс': (51.4800, 46.2000),
    'енгельс': (51.4800, 46.2000),
    'морозовск': (48.3520, 41.8260),
    'цимбулово': (52.9980, 36.4800),
    'цимбулова': (52.9980, 36.4800),
    'навля': (52.8249, 34.4983),
    'миллерово': (48.9238, 40.3984),
    'міллерово': (48.9238, 40.3984),
    'ейск': (46.7056, 38.2728),
    'єйськ': (46.7056, 38.2728),
    'приморсько-ахтарськ': (46.0514, 38.1742),
    'приморсько-ахтарск': (46.0514, 38.1742),
    'астраханская область': (46.3497, 48.0408),
    'астраханська область': (46.3497, 48.0408),
    'каспийское море': (42.0000, 51.0000),
    'каспійське море': (42.0000, 51.0000),
    # Крим (аэродромы/полигоны)
    'чауда': (45.0043420, 35.8307884),
    'мыс чауда': (45.0043420, 35.8307884),
    'cape chauda': (45.0043420, 35.8307884),
    'гвардейское': (45.1155000, 33.9780077),
    'гвардійське': (45.1155000, 33.9780077),
    'gvardeyskoye': (45.1155000, 33.9780077),
    'hvardiiske': (45.1155000, 33.9780077),
    'аэродром гвардейское': (45.1155000, 33.9780077),
    'кiровське': (45.1665650, 35.1866323),
    'кіровське': (45.1665650, 35.1866323),
    'кировское': (45.1665650, 35.1866323),
    'kirovske': (45.1665650, 35.1866323),
    'аэродром кировское': (45.1665650, 35.1866323),
    'саки': (45.0909250, 33.5934182),
    'saky': (45.0909250, 33.5934182),
    'аэродром саки': (45.0909250, 33.5934182),
}

# --- Hot-path regex (compiled once) ---
RE_PARENS_STRIP = re.compile(r'\s*\([^)]*\)\s*')
RE_OBLAST_IN_PARENS = re.compile(r'\(([^)]*обл[^)]*)\)', re.IGNORECASE)
RE_CITY_BEFORE_PARENS = re.compile(r'^([^(]+)\s*\(')
RE_OBLAST_SUFFIX = re.compile(r'обл\.?$', re.IGNORECASE)
RE_OBLAST_PARENS_NAME = re.compile(r'\(([А-Яа-яЇїІіЄєҐґ]+(?:ська|ський|ка)?)\s*обл', re.IGNORECASE)
RE_OBLAST_ANYWHERE = re.compile(r'([А-Яа-яЇїІіЄєҐґ]+)\s*(?:обл|область)', re.IGNORECASE)
RE_PLACE_PREFIX = re.compile(r'^(м\.|смт|с\.|місто|селище)\s+', re.IGNORECASE)
RE_MULTI_SPACE = re.compile(r'\s+')
RE_OBLAST_SUFFIX_REMOVE = re.compile(r'( область| обл\.?| обл)\b', re.IGNORECASE)
RE_RAION_SUFFIX_REMOVE = re.compile(r'( район| р-н)\b', re.IGNORECASE)
RE_REGION_IN_TEXT = re.compile(r'([\w\-]+(?:ська|ький|ка)\s*(?:область|район))', re.IGNORECASE)

# --- Region ID cache (reduces repeated parsing/lookup work) ---
_REGION_IDS_CACHE: dict[str, dict] = {}
_REGION_IDS_CACHE_TTL = int(os.getenv('REGION_IDS_CACHE_TTL', '3600'))  # seconds
_REGION_IDS_CACHE_MAX = int(os.getenv('REGION_IDS_CACHE_MAX', '3000'))

_OBLAST_ID_CACHE: dict[str, str | None] = {}
_RF_GEOCODE_CACHE: dict[str, tuple] = {}
_RF_GEOCODE_CACHE_TTL = int(os.getenv('RF_GEOCODE_CACHE_TTL', '604800'))  # 7 days

def _extract_oblast_from_text(text: str) -> str | None:
    if not text:
        return None
    paren_match = RE_OBLAST_PARENS_NAME.search(text)
    if paren_match:
        candidate = paren_match.group(1).strip()
        if re.search(r'невідом|неизвест|unknown', candidate, re.IGNORECASE):
            return None
        return candidate
    match = RE_OBLAST_ANYWHERE.search(text)
    if match:
        candidate = match.group(1).strip()
        if re.search(r'невідом|неизвест|unknown', candidate, re.IGNORECASE):
            return None
        return candidate
    return None

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

    # Київська область (UA-32)
    'біла церква': ('UA-32', 'UA-32-01'),
    'білацерква': ('UA-32', 'UA-32-01'),
    'бориспіль': ('UA-32', 'UA-32-02'),
    'переяслав': ('UA-32', 'UA-32-02'),
    'бровари': ('UA-32', 'UA-32-03'),
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
    """
    cache_key = f"{(place or '').lower().strip()}|{(region or '').lower().strip()}"
    cached = _region_ids_cache_get(cache_key)
    if cached is not None:
        return cached
    
    oblast_id = REGION_TO_OBLAST_ID.get(region)
    raion_id = None
    
    if not oblast_id:
        return (None, None)
    
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
                settlement = (
                    components.get('city') or components.get('town') or components.get('village') or
                    components.get('hamlet') or components.get('municipality')
                )
                settlement_norm = _normalize_admin_name(settlement) if settlement else ''
                if settlement_norm and settlement_norm in PLACE_TO_RAION_ID:
                    found_oblast, found_raion = PLACE_TO_RAION_ID[settlement_norm]
                    if not oblast_id or found_oblast == oblast_id:
                        raion_id = found_raion

            if not raion_id:
                county = components.get('county') or components.get('district') or components.get('state_district')
                county_norm = _normalize_admin_name(county) if county else ''
                if county_norm:
                    for keyword, (kw_oblast, kw_raion) in PLACE_TO_RAION_ID.items():
                        if (not oblast_id or kw_oblast == oblast_id) and keyword in county_norm:
                            raion_id = kw_raion
                            break
    
    result = (oblast_id, raion_id)
    _region_ids_cache_set(cache_key, result)
    return result

# --- Geographic Utilities ---
# Used for: trajectory calculation, threat direction, marker positioning

def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate bearing from point 1 to point 2 in degrees (0-360).
    
    Used for: determining threat direction (e.g., "на схід від Києва")
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    return (bearing + 360) % 360

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

def get_kyiv_directional_coordinates(threat_text, original_city="київ"):
    """
    For Kyiv threats, calculate directional coordinates based on threat patterns
    Returns modified coordinates showing approach direction instead of city center
    """
    kyiv_lat, kyiv_lng = 50.4501, 30.5234
    threat_lower = threat_text.lower()

    # Try to extract source city/direction from course patterns
    course_patterns = [
        r'бпла.*?курс.*?на.*?київ.*?з\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
        r'бпла.*?курс.*?на.*?київ.*?від\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
        r'([а-яіїєё\s\-\']+?).*?курс.*?на.*?київ',
        r'z\s+([а-яіїєё\s\-\']+?).*?курс.*?на.*?київ'
    ]

    source_city = None
    for pattern in course_patterns:
        matches = re.findall(pattern, threat_lower)
        if matches:
            potential_city = matches[0].strip()
            if potential_city and len(potential_city) > 2:
                # Clean up common noise words
                noise_words = {'бпла', 'курсом', 'курс', 'на', 'над', 'області', 'область', 'обл', 'район'}
                clean_city = ' '.join([word for word in potential_city.split() if word not in noise_words])
                if clean_city:
                    source_city = clean_city
                    break

    if source_city:
        # Try to find coordinates for source city (we'll need to implement a simple lookup)
        # For now, use some common approach directions
        approach_directions = {
            'чернігів': (51.4982, 31.2893, "↘ Київ"),
            'суми': (50.9077, 34.7981, "↙ Київ"),
            'харків': (49.9935, 36.2304, "← Київ"),
            'полтава': (49.5883, 34.5514, "↖ Київ"),
            'черкаси': (49.4444, 32.0598, "↑ Київ"),
            'житомир': (50.2547, 28.6587, "→ Київ"),
            'біла церква': (49.7939, 30.1014, "↗ Київ")
        }

        if source_city in approach_directions:
            source_lat, source_lng, direction_label = approach_directions[source_city]

            # Calculate bearing from source to Kyiv
            bearing = calculate_bearing(source_lat, source_lng, kyiv_lat, kyiv_lng)

            # Place marker on approach path (70% of the way from source to Kyiv)
            progress = 0.7  # 70% towards Kyiv
            approach_lat = source_lat + (kyiv_lat - source_lat) * progress
            approach_lng = source_lng + (kyiv_lng - source_lng) * progress

            return approach_lat, approach_lng, f"{direction_label} ({int(bearing)}°)", source_city

    # Fallback: use directional keywords to offset from center
    direction_offsets = {
        'півдн': (-0.08, 0, "↑ Київ (Пд)"),      # south
        'півден': (-0.08, 0, "↑ Київ (Пд)"),
        'пн': (0.08, 0, "↓ Київ (Пн)"),          # north
        'північ': (0.08, 0, "↓ Київ (Пн)"),
        'сх': (0, 0.08, "← Київ (Сх)"),          # east
        'схід': (0, 0.08, "← Київ (Сх)"),
        'зх': (0, -0.08, "→ Київ (Зх)"),         # west
        'захід': (0, -0.08, "→ Київ (Зх)"),
        'пд-сх': (-0.06, 0.06, "↖ Київ (ПдСх)"), # southeast
        'пн-зх': (0.06, -0.06, "↘ Київ (ПнЗх)"), # northwest
    }

    for direction, (lat_offset, lng_offset, label) in direction_offsets.items():
        if direction in threat_lower:
            return (kyiv_lat + lat_offset, kyiv_lng + lng_offset,
                   label, direction)

    # Default: return regular Kyiv coordinates
    return kyiv_lat, kyiv_lng, "Київ", None

def extract_shahed_course_info(threat_text):
    """
    Extract course information from Shahed/UAV threat messages
    Returns: (source_city, target_city, direction, bearing, course_type)
    """
    text_lower = threat_text.lower()

    # Common course patterns for Shahed/UAV
    course_patterns = [
        # "БпЛА курсом з [source] на [target]"
        r'бпла\s+.*?курс(?:ом)?\s+з\s+([а-яіїєё\s\-\']+?)\s+на\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
        # "БпЛА курсом на [target] з [source]"
        r'бпла\s+.*?курс(?:ом)?\s+на\s+([а-яіїєё\s\-\']+?)\s+з\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
        # "БпЛА з [source] курсом на [target]"
        r'бпла\s+з\s+([а-яіїєё\s\-\']+?)\s+курс(?:ом)?\s+на\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
        # "БпЛА з [source] у напрямку [target]"
        r'бпла\s+з\s+([а-яіїєё\s\-\']+?)\s+у\s+напрямк[уи]\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
        # "БпЛА курсом на [target]" (target only)
        r'бпла\s+.*?курс(?:ом)?\s+на\s+([а-яіїєё\s\-\']+?)(?=\s*(?:\n|$|[,\.\!\?;]))',
        # "[count]х БпЛА курс [source]-[target]"
        r'\d*х?\s*бпла\s+курс\s+([а-яіїєё\s\-\']+?)\s*[-–—]\s*([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
    ]

    # Try to extract course information
    for pattern_idx, pattern in enumerate(course_patterns):
        matches = re.findall(pattern, text_lower)
        if matches:
            match = matches[0]

            if pattern_idx == 0:  # з source на target
                source = match[0].strip()
                target = match[1].strip()
            elif pattern_idx == 1:  # на target з source
                target = match[0].strip()
                source = match[1].strip()
            elif pattern_idx == 2:  # з source курсом на target
                source = match[0].strip()
                target = match[1].strip()
            elif pattern_idx == 3:  # з source у напрямку target
                source = match[0].strip()
                target = match[1].strip()
            elif pattern_idx == 4:  # курсом на target (no source)
                source = None
                target = match.strip() if isinstance(match, str) else match[0].strip()
            elif pattern_idx == 5:  # курс source-target
                source = match[0].strip()
                target = match[1].strip()

            # Clean up noise words
            noise_words = {'область', 'обл', 'район', 'р-н', 'на', 'з', 'від', 'до'}
            if source:
                source = ' '.join([word for word in source.split() if word not in noise_words]).strip()
            if target:
                target = ' '.join([word for word in target.split() if word not in noise_words]).strip()

            # Determine course type
            if source and target:
                course_type = "full_course"  # Full trajectory
            elif target:
                course_type = "target_only"  # Only destination
            else:
                course_type = "unknown"

            return {
                'source_city': source,
                'target_city': target,
                'course_direction': f"на {target}" if target else None,
                'raw_direction': None,
                'course_type': course_type
            }

    # Try to extract directional information
    direction_patterns = {
        'північ': 'N', 'північний': 'N', 'пн': 'N',
        'південь': 'S', 'південний': 'S', 'пд': 'S',
        'схід': 'E', 'східний': 'E', 'сх': 'E',
        'захід': 'W', 'західний': 'W', 'зх': 'W',
        'північно-східний': 'NE', 'пн-сх': 'NE',
        'північно-західний': 'NW', 'пн-зх': 'NW',
        'південно-східний': 'SE', 'пд-сх': 'SE',
        'південно-західний': 'SW', 'пд-зх': 'SW'
    }

    for direction_ukr, direction_eng in direction_patterns.items():
        if direction_ukr in text_lower:
            return {
                'source_city': None,
                'target_city': None,
                'course_direction': direction_eng,
                'raw_direction': direction_ukr,
                'course_type': "directional"
            }

    return None

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

# --- Telegram Configuration ---
API_ID = int(os.getenv('TELEGRAM_API_ID', '0') or '0')
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
_DEFAULT_CHANNELS = 'mapstransler'
# SPEED FIX: Only use mapstransler to reduce backfill time (was 21 channels)
# To restore all channels, remove the override below
CHANNELS = ['mapstransler']  # HARDCODED for speed
# Original: CHANNELS = [c.strip() for c in os.getenv('TELEGRAM_CHANNELS', _DEFAULT_CHANNELS).split(',') if c.strip()]

# Channels which failed resolution (entity not found / access denied) to avoid repeated spam
INVALID_CHANNELS = set()
GOOGLE_MAPS_KEY = os.getenv('GOOGLE_MAPS_KEY', '')
OPENCAGE_API_KEY = os.getenv('OPENCAGE_API_KEY', '')  # optional geocoding
ALWAYS_STORE_RAW = os.getenv('ALWAYS_STORE_RAW', '1') not in ('0','false','False')

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

# Shared rate tracking for lightweight bandwidth protection rules
request_counts = defaultdict(list)
_request_counts_max_keys = 2000  # MEMORY PROTECTION: Max tracked IPs (reduced from 10000)

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

# BANDWIDTH OPTIMIZATION: Enable gzip compression globally
import gzip
import io

# MEMORY PROTECTION: Max response size to compress (10MB)
MAX_COMPRESS_SIZE = 10 * 1024 * 1024

# Add global response compression
@app.after_request
def compress_response(response):
    """Apply gzip compression to reduce bandwidth usage."""
    # MEMORY PROTECTION: Skip compression for very large responses to avoid OOM
    if (
        response.status_code == 200 and
        'gzip' in request.headers.get('Accept-Encoding', '').lower() and
        response.content_length and response.content_length > 500 and
        response.content_length < MAX_COMPRESS_SIZE and  # Don't compress huge responses
        response.content_type.startswith(('application/json', 'text/html', 'text/css', 'application/javascript'))
    ):
        try:
            # Compress the response data
            data = response.get_data()
            # Double-check size to prevent memory issues
            if len(data) > MAX_COMPRESS_SIZE:
                return response
                
            buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
                f.write(data)

            compressed = buffer.getvalue()
            # Only use compressed version if it's actually smaller
            if len(compressed) < len(data):
                response.set_data(compressed)
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Length'] = len(compressed)
                response.headers['Vary'] = 'Accept-Encoding'
        except Exception:
            pass  # If compression fails, return original response

    # Add cache headers for static content
    if request.endpoint == 'static':
        response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours

    return response

# ══════════════════════════════════════════════════════════════════════════════
# [SECTION 9] SERVICES: Alarms & Notifications
# ══════════════════════════════════════════════════════════════════════════════
# Ukraine Alarm API integration for air raid alerts.
# - Proxy to ukrainealarm.com API
# - Push notifications via Firebase
# - Alarm state tracking and history

import requests as http_requests

# --- Alarm API Configuration ---
ALARM_API_KEY = os.getenv('ALARM_API_KEY', '57fe8a39:7698ad50f0f15d502b280a83019bab25')
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
_alarm_all_cache = {'data': None, 'time': 0}  # Separate cache for /all endpoint
ALARM_CACHE_TTL = 30  # seconds
ALARM_CACHE_STALE_TTL = 300  # 5 minutes - serve stale data if API fails

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
def alarm_all():
    """Returns ALL alerts (State, District, Community) for detailed view with caching"""
    import hashlib
    import time as _time
    now = _time.time()

    # Return fresh cached data if available
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

    # Try to fetch with retries
    for attempt in range(3):
        try:
            response = http_requests.get(
                f'{ALARM_API_BASE}/alerts',
                headers={'Authorization': ALARM_API_KEY},
                timeout=8
            )
            if response.ok:
                data = response.json()
                # Return all active alerts with regionId for SVG matching
                result = []
                for region in data:
                    if region.get('activeAlerts') and len(region['activeAlerts']) > 0:
                        result.append({
                            'regionId': region.get('regionId'),
                            'regionName': region.get('regionName'),
                            'regionType': region.get('regionType'),
                            'activeAlerts': region.get('activeAlerts')
                        })

                # Generate ETag from content hash
                content_hash = hashlib.md5(json.dumps(result, sort_keys=True).encode()).hexdigest()[:16]
                etag = f'"{content_hash}"'

                # Update cache with ETag
                _alarm_all_cache['data'] = result
                _alarm_all_cache['time'] = now
                _alarm_all_cache['etag'] = etag

                # Check if client has same version
                client_etag = request.headers.get('If-None-Match')
                if client_etag == etag:
                    return Response(status=304, headers={'ETag': etag})

                resp = jsonify(result)
                resp.headers['Cache-Control'] = 'public, max-age=30'
                resp.headers['ETag'] = etag
                return resp
        except Exception as e:
            print(f"Alarm all attempt {attempt+1} failed: {e}")
            if attempt < 2:
                _time.sleep(0.5)  # Wait before retry

    # All retries failed - return stale cached data if available (within 5 min)
    if _alarm_all_cache['data'] and (now - _alarm_all_cache['time']) < ALARM_CACHE_STALE_TTL:
        print(f"Returning stale alarm data ({int(now - _alarm_all_cache['time'])}s old) after API failures")
        resp = jsonify(_alarm_all_cache['data'])
        resp.headers['Cache-Control'] = 'public, max-age=30'
        return resp

    # No cache available - return empty with error flag
    print("Alarm API failed and no cache available")
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

                # For Android: DATA-ONLY message so background handler can process TTS
                # For iOS: Include notification so system shows alert (TTS won't work in background on iOS)
                message = messaging.Message(
                    # NO notification block - Android needs data-only for background handler + TTS
                    data={
                        'type': 'alarm',
                        'title': title,
                        'body': body,
                        'location': fcm_location,  # Конкретне місто або область для TTS
                        'region': region_name,  # Область (для фільтрації)
                        'region_id': region_id,
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

                response = messaging.send(message)
                success_count += 1
                log.info(f"✅ Alarm notification sent to topic {target_topic}: {response}")
            except Exception as e:
                log.error(f"Failed to send alarm to topic {target_topic}: {e}")

        log.info(f"Sent alarm notifications to {success_count} topics for region: {region_name}")
    except Exception as e:
        log.error(f"Error in send_alarm_notification: {e}")


# Track recently sent telegram alerts to avoid duplicates (message_id -> timestamp)
_telegram_alert_sent = {}
_telegram_alert_lock = threading.Lock()

# Track regions that received Telegram notifications recently to suppress duplicate alarm notifications
# region_name (normalized) -> timestamp
_telegram_region_notified = {}

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

        # Try AI classification first for more accurate results
        try:
            ai_result = classify_threat_with_ai(message_text)
            print(f"[TELEGRAM_PUSH] 🤖 AI result: {ai_result}", flush=True)
        except Exception as ai_err:
            print(f"[TELEGRAM_PUSH] ⚠️ AI classification failed: {ai_err}", flush=True)
            ai_result = None

        if ai_result and ai_result.get('threat_type') not in ['unknown', None]:
            # Use AI classification
            threat_map = {
                'shahed': ('шахеди', '🛵'),
                'ballistic': ('балістика', '🚀'),
                'cruise': ('крилаті ракети', '🎯'),
                'kab': ('КАБи', '💣'),
                'drone': ('дрони', '🔭'),
                'explosion': ('вибухи', '💥'),
                'artillery': ('артилерія', '💨'),
            }
            threat_type, emoji = threat_map.get(ai_result['threat_type'], ('загроза', '⚠️'))
            if ai_result.get('emoji'):
                emoji = ai_result['emoji']
            is_critical = ai_result.get('priority', 3) >= 3

            print(f"AI threat classification: {threat_type} {emoji} (priority {ai_result.get('priority')})")
        else:
            # Fallback to regex-based classification
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
            print(f"[TELEGRAM_PUSH] ⚠️ No topic found for '{region_name}', falling back to all_regions", flush=True)
            log.warning(f"⚠️ No topic mapping for region: {region_name}, location was: {location}")
            # Try to send to all_regions anyway so users with all_regions get it
            topic = 'all_regions'
            log.info(f"Fallback to all_regions topic for {region_name}")

        print(f"[TELEGRAM_PUSH] Final topic: {topic}", flush=True)
        log.info(f"Sending telegram threat to topic: {topic}")

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

        # Send to topic
        success_count = 0
        try:
            # NO top-level notification - Android uses AndroidNotification, iOS uses APNSPayload
            # Having both notification AND apns.payload can cause iOS delivery issues
            message = messaging.Message(
                data={
                    'type': 'telegram_threat',
                    'title': title,
                    'body': body,
                    'location': tts_location,  # City or region for TTS
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
                    notification=messaging.AndroidNotification(
                        title=title,
                        body=body,
                        icon='ic_notification',
                        channel_id='critical_alerts',
                        priority='max',
                        default_vibrate_timings=True,
                        default_sound=True,
                    ),
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

            response = messaging.send(message)
            success_count = 1
            print(f"[TELEGRAM_PUSH] ✅ Sent to topic '{topic}': {response}", flush=True)
            log.info(f"✅ Telegram threat notification sent to topic {topic}: {response}")
        except Exception as e:
            print(f"[TELEGRAM_PUSH] ❌ Failed to send to topic '{topic}': {e}", flush=True)
            log.error(f"Failed to send telegram threat to topic {topic}: {e}")

        # Also send to 'all_regions' topic for users who want all alerts
        try:
            # NO top-level notification - same fix as above for iOS
            message_all = messaging.Message(
                data={
                    'type': 'telegram_threat',
                    'title': title,
                    'body': body,
                    'location': tts_location,
                    'region': region_name,
                    'oblast_id': oblast_id or '',
                    'raion_id': raion_id or '',
                    'settlement_id': '',
                    'alarm_state': 'active',
                    'is_critical': 'true' if is_critical else 'false',
                    'threat_type': threat_type_readable,
                    'timestamp': datetime.now(pytz.timezone('Europe/Kiev')).isoformat(),
                    'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                },
                android=messaging.AndroidConfig(
                    priority='high',
                    ttl=timedelta(seconds=300),
                    notification=messaging.AndroidNotification(
                        title=title,
                        body=body,
                        icon='ic_notification',
                        channel_id='critical_alerts',
                        priority='max',
                        default_vibrate_timings=True,
                        default_sound=True,
                    ),
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
                topic='all_regions',
            )
            messaging.send(message_all)
            log.info(f"✅ Telegram threat also sent to all_regions topic")
        except Exception as e:
            log.error(f"Failed to send telegram threat to all_regions: {e}")

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
FORCE_RELOAD_TIMESTAMP = 0  # Timestamp when force reload was triggered
FORCE_RELOAD_DURATION = 120  # Duration in seconds to keep force reload active (2 minutes)
FORCE_RELOAD_LOCK = threading.Lock()
client = None
session_str = os.getenv('TELEGRAM_SESSION')  # Telethon string session (recommended for Render)
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # optional bot token fallback
AUTH_SECRET = os.getenv('AUTH_SECRET')  # simple shared secret to protect /auth endpoints
FETCH_THREAD_STARTED = False
AUTH_STATUS = {'authorized': False, 'reason': 'init'}
SUBSCRIBERS = set()  # queues for SSE clients
MAX_STREAM_SUBSCRIBERS = 100  # MEMORY PROTECTION: Limit main SSE connections
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
MAX_DEBUG_LOGS = 20  # Reduced to save memory

# Cache for fallback reparse to avoid duplicate processing
FALLBACK_REPARSE_CACHE = set()  # message IDs that have been reparsed
MAX_REPARSE_CACHE_SIZE = 100  # Reduced to save memory (was 200)


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
MESSAGES_RETENTION_MINUTES = int(os.getenv('MESSAGES_RETENTION_MINUTES', '1440'))  # 24 hours retention by default
MESSAGES_MAX_COUNT = int(os.getenv('MESSAGES_MAX_COUNT', '500'))  # Default limit 500 to prevent memory issues

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
NOTIFICATION_CACHE_TTL = 300  # 5 minutes - don't repeat same location+threat within this time

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
        conn = sqlite3.connect(db_path, timeout=10)
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
        conn = sqlite3.connect(db_path, timeout=10)
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


def load_hidden():
    if os.path.exists(HIDDEN_FILE):
        try:
            with open(HIDDEN_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_hidden(data):
    with open(HIDDEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_blocked():
    if os.path.exists(BLOCKED_FILE):
        try:
            with open(BLOCKED_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_blocked(blocked):
    try:
        with open(BLOCKED_FILE, 'w', encoding='utf-8') as f:
            json.dump(blocked, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f'Failed saving {BLOCKED_FILE}: {e}')

def _load_visit_stats():
    global VISIT_STATS
    if VISIT_STATS is not None:
        return VISIT_STATS
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE,encoding='utf-8') as f:
                VISIT_STATS = json.load(f)
        except Exception:
            VISIT_STATS = {}
    else:
        VISIT_STATS = {}
    return VISIT_STATS

def _save_visit_stats():
    if VISIT_STATS is None:
        return
    try:
        with open(STATS_FILE,'w',encoding='utf-8') as f:
            json.dump(VISIT_STATS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f'Failed saving {STATS_FILE}: {e}')

def _prune_visit_stats(days:int=30):
    # remove entries older than N days to limit file growth - reduced from 45 to 30 days
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
    if removed:
        _save_visit_stats()

# ---- Rolling daily / weekly visit tracking (for persistence of counts across deploys) ----
def _load_recent_visits():
    try:
        if os.path.exists(RECENT_VISITS_FILE):
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
    try:
        tmp = RECENT_VISITS_FILE + '.tmp'
        # Ensure directory exists (in case path was changed to subfolder later); here file in CWD so skip
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        try:
            os.replace(tmp, RECENT_VISITS_FILE)
        except FileNotFoundError:
            # Rare race on some FS / AV scanners: fall back to simple write
            try:
                with open(RECENT_VISITS_FILE, 'w', encoding='utf-8') as f2:
                    json.dump(data, f2, ensure_ascii=False, indent=2)
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
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
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
        conn = sqlite3.connect(db_path, timeout=10)
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
        conn = sqlite3.connect(db_path, timeout=10)
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
_mapstransler_cache_max_size = 500  # MEMORY PROTECTION: Max cached geocode results (reduced from 2000)

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
        if len(_opencage_cache) > 1000:
            # Keep only the 1000 most recent entries (approximate)
            items = list(_opencage_cache.items())
            cache_to_save = dict(items[-1000:])
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

UA_CITIES = [
    'київ','харків','одеса','одесса','дніпро','дніпропетровськ','львів','запоріжжя','запорожье','вінниця','миколаїв','николаев',
    'маріуполь','полтава','чернігів','чернигов','черкаси','житомир','суми','хмельницький','чернівці','рівне','івано-франківськ',
    'луцьк','тернопіль','ужгород','кропивницький','кіровоград','кременчук','краматорськ','біла церква','мелітополь','бердянськ',
    'павлоград','ніжин','шостка','короп','кролевець'
]
UA_CITY_NORMALIZE = {
    'одесса':'одеса','запорожье':'запоріжжя','запоріжжі':'запоріжжя','дніпропетровськ':'дніпро','кировоград':'кропивницький','кіровоград':'кропивницький',
    'николаев':'миколаїв','чернигов':'чернігів',
    # Accusative / variant forms
    'липову долину':'липова долина','липову долина':'липова долина',
    'великий багачку':'велика багачка','велику багачу':'велика багачка','велику багачку':'велика багачка','велику багачка':'велика багачка',
    'улянівку':'улянівка','уляновку':'улянівка',
    # Велика Димерка падежные формы
    'велику димерку':'велика димерка','велика димерку':'велика димерка','великої димерки':'велика димерка','великій димерці':'велика димерка',
    # Велика Виска падежные формы
    'велику виску':'велика виска','великої виски':'велика виска','великій висці':'велика виска',
    # Мала дівиця
    'малу дівицю':'мала дівиця','мала дівицю':'мала дівиця',
    # Additional safety normalizations
    'олишівку':'олишівка','згурівку':'згурівка','ставищею':'ставище','кегичівку':'кегичівка','кегичевку':'кегичівка',
    # Voznesensk variants
    'вознесенська':'вознесенськ',
    # Mykolaiv variants
    'миколаєва':'миколаїв',
    'корабел':'корабельний район херсон',
    'корабельний':'корабельний район херсон',
    'корабельному':'корабельний район херсон',
    'корабельному херсоні':'корабельний район херсон',
    # Novoukrainka variants
    'новоукраїнку':'новоукраїнка',
    'старому салтову':'старий салтів','старому салтові':'старий салтів','карлівку':'карлівка','магдалинівку':'магдалинівка',
    'балаклію':'балаклія','білу церкву':'біла церква','баришівку':'баришівка','сквиру':'сквира','сосницю':'сосниця',
    'васильківку':'васильківка','понорницю':'понорниця','куликівку':'куликівка','терни':'терни',
    'шостку':'шостка','березну':'березна','зачепилівку':'зачепилівка','нову водолагу':'нова водолага',
    'нову':'нова водолага',  # Fallback for partial regex matches
    'убни':'лубни','олми':'холми','летичів':'летичів','летичев':'летичів','летичеве':'летичів','деражню':'деражня',
    'деражне':'деражня','деражні':'деражня','корюківку':'корюківка','борзну':'борзна','жмеринку':'жмеринка','лосинівку':'лосинівка',
    'ніжину':'ніжин','ніжина':'ніжин','межову':'межова','межової':'межова','святогірську':'святогірськ'
}

# Add accusative / genitive / variant forms for reported missing settlements
UA_CITY_NORMALIZE.update({
    'городню':'городня','городні':'городня','городне':'городня','городни':'городня',
    'кролевця':'кролевець','кролевцу':'кролевець','кролевце':'кролевець',
    'дубовʼязівку':'дубовʼязівка','дубовязівку':'дубовʼязівка','дубовязовку':'дубовʼязівка','дубовязовка':'дубовʼязівка',
    'батурина':'батурин','батурині':'батурин','батурином':'батурин'
    ,'бердичев':'бердичів','бердичева':'бердичів','бердичеве':'бердичів','бердичеву':'бердичів','бердичеві':'бердичів','бердичевом':'бердичів','бердичіву':'бердичів','бердичіва':'бердичів'
    ,'гостомеля':'гостомель','гостомелю':'гостомель','гостомелі':'гостомель','гостомель':'гостомель'
    ,'боярки':'боярка','боярку':'боярка','боярці':'боярка','боярка':'боярка'
    # Черниговская область - дополнительные формы
    ,'седнів':'седнів','седніву':'седнів','седніва':'седнів'
    ,'новгороду':'новгород','новгороді':'новгород','новгородом':'новгород'
    ,'мену':'мена','мені':'мена','меною':'мена'
    ,'макарова':'макарів','макарові':'макарів','макаров':'макарів','макарову':'макарів','макарів':'макарів'
    ,'бородянки':'бородянка','бородянку':'бородянка','бородянці':'бородянка','бородянка':'бородянка'
    ,'кілії':'кілія','кілію':'кілія','кілією':'кілія','кілія':'кілія'
    ,'ізмаїльського':'ізмаїльський','ізмаїльському':'ізмаїльський','ізмаїльський':'ізмаїльський'
    ,'броварського':'броварський','броварському':'броварський','броварський':'броварський'
    ,'обухівського':'обухівський','обухівському':'обухівський','обухівський':'обухівський'
    ,'херсонського':'херсонський','херсонському':'херсонський','херсонський':'херсонський'
    ,'вінницького':'вінницький','вінницькому':'вінницький','вінницький':'вінницький'
    ,'куцуруба':'куцуруб','воскресенку':'воскресенка','воскресенки':'воскресенка'
    # Цибулів (Черкаська обл.) падежные / вариантные формы
    ,'цибулева':'цибулів','цибулеві':'цибулів','цибулеву':'цибулів','цибулевом':'цибулів','цибулів':'цибулів'
    # New accusative / variants for UAV course parsing batch
    ,'борзну':'борзна','царичанку':'царичанка','андріївку':'андріївка','ямполь':'ямпіль','ямполя':'ямпіль','ямпіль':'ямпіль','димеру':'димер','чорнобилю':'чорнобиль'
    ,'дмитрівку':'дмитрівка','дмитрівку чернігівська':'дмитрівка','берестин':'берестин'
    ,'семенівку':'семенівка','глобине':'глобине','глобину':'глобине','глобиному':'глобине','глобина':'глобине'
    ,'кринички':'кринички','криничок':'кринички','солоне':'солоне','солоного':'солоне','солоному':'солоне'
    ,'краснопалівку':'краснопавлівка','краснопалівка':'краснопавлівка'
    ,'велику димерку':'велика димерка','великій димерці':'велика димерка','великої димерки':'велика димерка'
    ,'брусилів':'брусилів','брусилова':'брусилів','брусилові':'брусилів'
    # New cities from napramok messages September 2025
    ,'десну':'десна','кіпті':'кіпті','ічню':'ічня','цвіткове':'цвіткове'
    ,'чоповичі':'чоповичі','звягель':'звягель','сахновщину':'сахновщина'
    ,'камʼянське':'камʼянське','піщаний брід':'піщаний брід','бобринець':'бобринець'
    ,'тендрівську косу':'тендрівська коса'
    # Одеська область
    ,'вилково':'вилкове','вилкову':'вилкове'
    # Common accusative forms for major cities
    ,'одесу':'одеса','полтаву':'полтава','сумами':'суми','суму':'суми'
})
# Apostrophe-less fallback for Sloviansk
UA_CITY_NORMALIZE['словянськ'] = "слов'янськ"

# Donetsk front city normalization (latin/ukr vowel variants)
UA_CITY_NORMALIZE['лиман'] = 'ліман'

# ---------------- Dynamic settlement name → region map (from city_ukraine.json, no coords there) ---------------
NAME_REGION_MAP = {}

def _load_name_region_map():
    global NAME_REGION_MAP
    if NAME_REGION_MAP:
        return
    path = 'city_ukraine.json'
    if not os.path.exists(path):
        return
    try:
        with open(path,encoding='utf-8') as f:
            data = json.load(f)
        added = 0
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get('object_name') or '').strip().lower()
            region = str(item.get('region') or '').strip().title()
            if not name or len(name) < 2:
                continue
            # Skip obviously generic words
            if name in NAME_REGION_MAP:
                continue
            NAME_REGION_MAP[name] = region
            added += 1
        log.info(f"Loaded NAME_REGION_MAP entries: {added}")
    except Exception as e:
        log.warning(f"Failed load city_ukraine.json names: {e}")

_load_name_region_map()

# Fix problematic entries in NAME_REGION_MAP that cause wrong city resolution
# Remove incomplete city names that point to wrong regions
PROBLEMATIC_ENTRIES = [
    'кривий',     # Should be 'кривий ріг' not just 'кривий' -> causes wrong region lookup
    'старий',     # Too generic, causes conflicts
    'нова',       # Too generic
    'велика',     # Too generic
    'мала',       # Too generic
    'білозерка',  # Conflicts with Херсонська область when message clearly specifies region
]

for entry in PROBLEMATIC_ENTRIES:
    NAME_REGION_MAP.pop(entry, None)


# =============================================================================
# TRAJECTORY PARSER - Parse various Ukrainian message formats for drone courses
# =============================================================================
# Supports formats like:
# - "БпЛА з півночі на Суми" (direction + target city)
# - "Група БпЛА на сході Миколаївщини курсом на Кіровоградщину" (region + direction + target)
# - "БпЛА з Херсонщини на Миколаївщину" (source region → target region)
# - "БпЛА курсом на м.Запоріжжя з північно-східного напрямку" (city target + direction)
# - "Харків: БпЛА на місто з північно-східного напрямку" (city prefix + direction)
# - "БпЛА на Дніпропетровщині, напрямок Синельникове" (region + target city)
# =============================================================================

# Direction mappings (Ukrainian → offset vector)
DIRECTION_VECTORS = {
    # Cardinal directions - all forms
    'північ': (-0.5, 0), 'півночі': (-0.5, 0), 'північн': (-0.5, 0), 'північний': (-0.5, 0),
    'південь': (0.5, 0), 'півдня': (0.5, 0), 'півд': (0.5, 0), 'південн': (0.5, 0), 'півдні': (0.5, 0), 'південний': (0.5, 0),
    'схід': (0, 0.5), 'сходу': (0, 0.5), 'східн': (0, 0.5), 'сході': (0, 0.5), 'східний': (0, 0.5),
    'захід': (0, -0.5), 'заходу': (0, -0.5), 'західн': (0, -0.5), 'заході': (0, -0.5), 'західний': (0, -0.5),
    # Intercardinal directions - all forms
    'північно-східн': (-0.35, 0.35), 'північний схід': (-0.35, 0.35), 'північного сходу': (-0.35, 0.35),
    'північно-східний': (-0.35, 0.35), 'північно-схід': (-0.35, 0.35),
    'північно-західн': (-0.35, -0.35), 'північний захід': (-0.35, -0.35), 'північного заходу': (-0.35, -0.35),
    'північно-західний': (-0.35, -0.35), 'північно-захід': (-0.35, -0.35),
    'південно-східн': (0.35, 0.35), 'південний схід': (0.35, 0.35), 'південного сходу': (0.35, 0.35),
    'південно-східний': (0.35, 0.35), 'південно-схід': (0.35, 0.35),
    'південно-західн': (0.35, -0.35), 'південний захід': (0.35, -0.35), 'південного заходу': (0.35, -0.35),
    'південно-західний': (0.35, -0.35), 'південно-захід': (0.35, -0.35),
}

# Direction keywords in messages (source direction - "з" pattern)
DIRECTION_FROM_KEYWORDS = [
    'з північно-східного напрямку', 'з північно-західного напрямку',
    'з південно-східного напрямку', 'з південно-західного напрямку',
    'з північного напрямку', 'з південного напрямку',
    'з східного напрямку', 'з західного напрямку',
    'з півночі', 'з півдня', 'з сходу', 'з заходу',
    'з північного сходу', 'з північного заходу',
    'з південного сходу', 'з південного заходу',
]

# Course keywords in messages (target direction - "курс" pattern)
DIRECTION_COURSE_KEYWORDS = [
    'курс північно-східний', 'курс північно-західний',
    'курс південно-східний', 'курс південно-західний',
    'курс північний', 'курс південний', 'курс східний', 'курс західний',
    'курсом на північ', 'курсом на південь', 'курсом на схід', 'курсом на захід',
]

def _get_direction_vector(direction_text):
    """Get lat/lng offset vector for a direction text"""
    direction_lower = direction_text.lower().strip()
    for key, vector in DIRECTION_VECTORS.items():
        if key in direction_lower:
            return vector
    return None

def _get_region_center(region_name):
    """Get center coordinates for a region (oblast)"""
    region_lower = region_name.lower().strip()
    # Check in OBLAST_CENTERS directly
    if region_lower in OBLAST_CENTERS:
        return OBLAST_CENTERS[region_lower]

    # Normalize instrumental case "над вінницькою областю" → "вінницька область"
    # Pattern: Xькою областю → Xька область
    instrumental_match = re.match(r'^(.+?)(ькою|ською|цькою)\s*(областю|обл\.?)$', region_lower)
    if instrumental_match:
        base = instrumental_match.group(1)
        # Convert back to nominative: ькою→ька, ською→ська, цькою→цька
        suffix_map = {'ькою': 'ька', 'ською': 'ська', 'цькою': 'цька'}
        new_suffix = suffix_map.get(instrumental_match.group(2), 'ька')
        normalized = f"{base}{new_suffix} область"
        if normalized in OBLAST_CENTERS:
            return OBLAST_CENTERS[normalized]
        # Try without ' область'
        normalized_short = f"{base}{new_suffix}"
        if normalized_short in OBLAST_CENTERS:
            return OBLAST_CENTERS[normalized_short]

    # Try removing common endings and searching again
    # Ukrainian oblast name endings: -щина/-щини/-щині/-щину, -ччина/-ччини/-ччині
    base_region = region_lower
    for ending in ['щині', 'щину', 'щини', 'щина', 'ччині', 'ччину', 'ччини', 'ччина']:
        if region_lower.endswith(ending):
            base_region = region_lower[:-len(ending)]
            break

    # Try to find with base + common endings
    for ending in ['щина', 'щини', 'ччина', 'ччини']:
        test_key = base_region + ending
        if test_key in OBLAST_CENTERS:
            return OBLAST_CENTERS[test_key]

    # Try partial match
    for key, coords in OBLAST_CENTERS.items():
        if base_region in key or key.startswith(base_region):
            return coords

    return None

def _get_city_coords(city_name, context=None):
    """Get coordinates for a city - uses ONLY OpenCage API"""
    if not city_name:
        return None
    return ensure_city_coords_with_message_context(city_name, context)

def _ai_trajectory_to_coords(ai_result):
    """Convert AI trajectory result to coordinates.

    Takes AI result with source_type, source_name, target_type, target_name
    and returns trajectory dict with start/end coordinates.
    """
    if not ai_result:
        return None

    source_type = ai_result.get('source_type')
    source_name = ai_result.get('source_name')
    target_type = ai_result.get('target_type')
    target_name = ai_result.get('target_name')
    source_position = ai_result.get('source_position')  # e.g. "схід" for "на сході Сумщини"

    # Get target coordinates
    end_coords = None
    if target_type == 'city' and target_name:
        end_coords = _get_city_coords(target_name)
    elif target_type == 'region' and target_name:
        end_coords = _get_region_center(target_name)
    elif target_type == 'direction' and target_name:
        # Direction only - need source to calculate end
        pass

    # Get source coordinates
    start_coords = None
    if source_type == 'city' and source_name:
        start_coords = _get_city_coords(source_name)
    elif source_type == 'region' and source_name:
        start_coords = _get_region_center(source_name)
        # Apply position offset if specified (e.g. "на сході Сумщини")
        if start_coords and source_position:
            pos_vec = _get_direction_vector(source_position)
            if pos_vec:
                start_coords = (start_coords[0] + pos_vec[0] * 0.3, start_coords[1] + pos_vec[1] * 0.3)
    elif source_type == 'direction' and source_name:
        # Direction source - calculate from target
        if end_coords:
            dir_vec = _get_direction_vector(source_name)
            if dir_vec:
                # Invert direction to get source position
                start_coords = (end_coords[0] - dir_vec[0], end_coords[1] - dir_vec[1])

    # Handle target direction (when target is a direction like "курс південний")
    if target_type == 'direction' and target_name and start_coords and not end_coords:
        dir_vec = _get_direction_vector(target_name)
        if dir_vec:
            end_coords = (start_coords[0] + dir_vec[0] * 0.5, start_coords[1] + dir_vec[1] * 0.5)

    # =========================================================================
    # AI ROUTE PREDICTION: If we have source but no target, use AI to predict
    # MAX DISTANCE: 300 km (only neighboring regions) - prevents Kharkiv->Lutsk errors
    # =========================================================================
    MAX_PREDICTION_DISTANCE_KM = 300  # ~neighboring oblast

    if start_coords and not end_coords and GROQ_ENABLED:
        try:
            prediction = predict_route_with_ai(source_name or '')
            if prediction and prediction.get('confidence', 0) >= 0.6:
                predicted_targets = prediction.get('predicted_targets', [])
                if predicted_targets:
                    # Try each predicted target, use first within distance limit
                    for target in predicted_targets:
                        predicted_coords = _get_region_center(target) or _get_city_coords(target)
                        if predicted_coords:
                            # Calculate distance between start and predicted end
                            from math import atan2, cos, radians, sin, sqrt
                            lat1, lon1 = radians(start_coords[0]), radians(start_coords[1])
                            lat2, lon2 = radians(predicted_coords[0]), radians(predicted_coords[1])
                            dlat, dlon = lat2 - lat1, lon2 - lon1
                            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                            distance_km = 6371 * 2 * atan2(sqrt(a), sqrt(1-a))

                            if distance_km <= MAX_PREDICTION_DISTANCE_KM:
                                end_coords = predicted_coords
                                target_name = target + ' (прогноз)'
                                print(f"DEBUG AI Route Prediction used: {source_name} -> {target} ({distance_km:.0f}km, conf={prediction.get('confidence')})")
                                break
                            else:
                                print(f"DEBUG AI Route Prediction REJECTED (too far): {source_name} -> {target} ({distance_km:.0f}km > {MAX_PREDICTION_DISTANCE_KM}km)")
        except Exception as e:
            print(f"DEBUG: AI route prediction failed: {e}")

    # Need both start and end to create trajectory
    if not start_coords or not end_coords:
        return None

    return {
        'start': [start_coords[0], start_coords[1]],
        'end': [end_coords[0], end_coords[1]],
        'source_name': source_name or 'unknown',
        'target_name': target_name or 'unknown',
        'kind': f'ai_{source_type}_to_{target_type}',
        'predicted': end_coords and '(прогноз)' in (target_name or '')
    }

def parse_trajectory_from_message(text):
    """
    Parse trajectory info from Ukrainian drone movement messages.

    Uses AI (Groq) when available for intelligent parsing, with regex fallback.

    Returns dict with:
        - start: [lat, lng] - source coordinates
        - end: [lat, lng] - target coordinates
        - source_name: str - source location name
        - target_name: str - target location name
        - kind: str - type of trajectory match
    Or None if no trajectory pattern found.
    """
    import re
    if not text:
        return None

    # ==========================================================================
    # TRY AI FIRST (if enabled) - much smarter than regex
    # ==========================================================================
    if GROQ_ENABLED:
        try:
            ai_result = extract_trajectory_with_ai(text)
            if ai_result and ai_result.get('confidence', 0) >= 0.7:
                trajectory = _ai_trajectory_to_coords(ai_result)
                if trajectory:
                    print(f"DEBUG: AI trajectory parsed successfully: {trajectory.get('kind')}")
                    return trajectory
        except Exception as e:
            print(f"DEBUG: AI trajectory failed, falling back to regex: {e}")

    # ==========================================================================
    # FALLBACK TO REGEX PATTERNS
    # ==========================================================================
    text_lower = text.lower()
    # Remove emoji prefixes for pattern matching
    text_clean = re.sub(r'^[^\w\s]*\s*', '', text_lower)

    # =========================================================================
    # Pattern 1: "БпЛА з [напрямок] на [місто]"
    # Example: "БпЛА з півночі на Суми"
    # =========================================================================
    p1 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+(півноч[іи]|півдн[яю]|сход[уі]|заход[уі]|північн\w*[\s-]*схо\w*|північн\w*[\s-]*захо\w*|південн\w*[\s-]*схо\w*|південн\w*[\s-]*захо\w*)\s+на\s+([а-яіїєґ\'\-]+)', text_lower)
    if p1:
        direction_text = p1.group(1)
        target_city = p1.group(2)

        target_coords = _get_city_coords(target_city)
        if target_coords:
            direction_vec = _get_direction_vector(direction_text)
            if direction_vec:
                # Invert direction to get source (from direction -> opposite)
                start_lat = target_coords[0] - direction_vec[0]
                start_lng = target_coords[1] - direction_vec[1]
                return {
                    'start': [start_lat, start_lng],
                    'end': [target_coords[0], target_coords[1]],
                    'source_name': f'з {direction_text}',
                    'target_name': target_city.title(),
                    'kind': 'direction_to_city'
                }

    # =========================================================================
    # Pattern 2: "БпЛА з [регіон] на [регіон]"
    # Example: "БпЛА з Херсонщини на Миколаївщину"
    # =========================================================================
    p2 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+([а-яіїєґ]+(щин|ччин)[ауиіи])\s+на\s+([а-яіїєґ]+(щин|ччин)[ауиію])', text_lower)
    if p2:
        source_region = p2.group(1)
        target_region = p2.group(3)

        source_coords = _get_region_center(source_region)
        target_coords = _get_region_center(target_region)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': target_region.title(),
                'kind': 'region_to_region'
            }

    # =========================================================================
    # Pattern 2a: "БпЛА з [регіон] курсом на [регіон], напрямок [місто/міста]"
    # Example: "БпЛА з Київщини курсом на Житомирщину, напрямок Коростень/Овруч"
    # =========================================================================
    p2a = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+([а-яіїєґ]+(щин|ччин)[иіау])\s+курсом\s+на\s+([а-яіїєґ]+(щин|ччин)[у|ю])[,\s]+(?:напрямок|напрям)\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-/]+)', text_lower)
    if p2a:
        source_region = p2a.group(1)
        target_region = p2a.group(3)
        target_cities = p2a.group(5)  # May contain multiple cities like "Коростень/Овруч"

        source_coords = _get_region_center(source_region)
        # Try to get coords for the first city mentioned
        first_city = target_cities.split('/')[0].split(',')[0].strip()
        target_coords = _get_city_coords(first_city)

        # Fallback to region center if city not found
        if not target_coords:
            target_coords = _get_region_center(target_region)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': target_cities.title(),
                'kind': 'region_course_to_city'
            }

    # =========================================================================
    # Pattern 2b: "БпЛА з [регіон] курсом на [регіон]" (без напрямку)
    # Example: "БпЛА з Київщини курсом на Житомирщину"
    # =========================================================================
    p2b = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+([а-яіїєґ]+(щин|ччин)[иіау])\s+курсом\s+на\s+([а-яіїєґ]+(щин|ччин)[уюі])', text_lower)
    if p2b:
        source_region = p2b.group(1)
        target_region = p2b.group(3)

        source_coords = _get_region_center(source_region)
        target_coords = _get_region_center(target_region)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': target_region.title(),
                'kind': 'region_course_to_region'
            }

    # =========================================================================
    # Pattern 3: "БпЛА на [напрямок] [регіон] курсом на [регіон]"
    # Example: "Група БпЛА на сході Миколаївщини курсом на Кіровоградщину"
    # =========================================================================
    p3 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+(півноч[іи]|півдн[іи]|сход[іиі]|заход[іиі]|північн\w*[\s-]*схо\w*|північн\w*[\s-]*захо\w*|південн\w*[\s-]*схо\w*|південн\w*[\s-]*захо\w*)\s+([а-яіїєґ]+(щин|ччин)[иі])\s+курсом\s+на\s+([а-яіїєґ]+(щин|ччин)[ауиію])', text_lower)
    if p3:
        direction_in_region = p3.group(1)
        source_region = p3.group(2)
        target_region = p3.group(4)

        source_coords = _get_region_center(source_region)
        target_coords = _get_region_center(target_region)

        if source_coords and target_coords:
            # Offset source by direction within the region
            direction_vec = _get_direction_vector(direction_in_region)
            if direction_vec:
                start_lat = source_coords[0] + direction_vec[0] * 0.3
                start_lng = source_coords[1] + direction_vec[1] * 0.3
            else:
                start_lat, start_lng = source_coords

            return {
                'start': [start_lat, start_lng],
                'end': [target_coords[0], target_coords[1]],
                'source_name': f'{direction_in_region} {source_region}'.title(),
                'target_name': target_region.title(),
                'kind': 'region_direction_to_region'
            }

    # =========================================================================
    # Pattern 4: "БпЛА курсом на м.[місто] з [напрямок] напрямку"
    # Example: "БпЛА курсом на м.Запоріжжя з північно-східного напрямку"
    # =========================================================================
    p4 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+курсом\s+на\s+(?:м\.?|місто\s+)?([а-яіїєґ\'\-]+)\s+з\s+(північн\w*[\s-]*схід\w*|північн\w*[\s-]*захід\w*|південн\w*[\s-]*схід\w*|південн\w*[\s-]*захід\w*|північн\w*|південн\w*|східн\w*|західн\w*)\s*напрямку', text_lower)
    if p4:
        target_city = p4.group(1)
        direction_text = p4.group(2)

        target_coords = _get_city_coords(target_city)
        if target_coords:
            direction_vec = _get_direction_vector(direction_text)
            if direction_vec:
                start_lat = target_coords[0] - direction_vec[0]
                start_lng = target_coords[1] - direction_vec[1]
                return {
                    'start': [start_lat, start_lng],
                    'end': [target_coords[0], target_coords[1]],
                    'source_name': f'з {direction_text} напрямку',
                    'target_name': target_city.title(),
                    'kind': 'city_from_direction'
                }

    # =========================================================================
    # Pattern 5: "[Місто]: БпЛА на місто з [напрямок] напрямку"
    # Example: "🛵 Харків: БпЛА на місто з північно-східного напрямку"
    # =========================================================================
    p5 = re.search(r'([а-яіїєґ\'\-]+)\s*:\s*(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+місто\s+з\s+(північн\w*[\s-]*схід\w*|північн\w*[\s-]*захід\w*|південн\w*[\s-]*схід\w*|південн\w*[\s-]*захід\w*|північн\w*|південн\w*|східн\w*|західн\w*)\s*напрямку', text_clean)
    if p5:
        target_city = p5.group(1)
        direction_text = p5.group(2)

        target_coords = _get_city_coords(target_city)
        if target_coords:
            direction_vec = _get_direction_vector(direction_text)
            if direction_vec:
                start_lat = target_coords[0] - direction_vec[0]
                start_lng = target_coords[1] - direction_vec[1]
                return {
                    'start': [start_lat, start_lng],
                    'end': [target_coords[0], target_coords[1]],
                    'source_name': f'з {direction_text}',
                    'target_name': target_city.title(),
                    'kind': 'city_prefix_direction'
                }

    # =========================================================================
    # Pattern 6: "[Місто]: БпЛА з [напрямок]"
    # Example: "🛵 Харків: БпЛА з півночі"
    # =========================================================================
    p6 = re.search(r'([а-яіїєґ\'\-]+)\s*:\s*(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+(півноч[іи]|півдн[яю]|сход[уі]|заход[уі]|північн\w*[\s-]*схо\w*|північн\w*[\s-]*захо\w*|південн\w*[\s-]*схо\w*|південн\w*[\s-]*захо\w*)', text_clean)
    if p6:
        target_city = p6.group(1)
        direction_text = p6.group(2)

        target_coords = _get_city_coords(target_city)
        if target_coords:
            direction_vec = _get_direction_vector(direction_text)
            if direction_vec:
                start_lat = target_coords[0] - direction_vec[0]
                start_lng = target_coords[1] - direction_vec[1]
                return {
                    'start': [start_lat, start_lng],
                    'end': [target_coords[0], target_coords[1]],
                    'source_name': f'з {direction_text}',
                    'target_name': target_city.title(),
                    'kind': 'city_prefix_from'
                }

    # =========================================================================
    # Pattern 7: "БпЛА на [регіон], напрямок/курс на [місто]"
    # Example: "БпЛА на Дніпропетровщині, напрямок Синельникове"
    # Example: "Група БпЛА на Одещині, курс на н.п. Кілія"
    # =========================================================================
    p7 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+([а-яіїєґ]+(щин|ччин)[іиї])[,.\s]+(?:напрямок|напрям|у напрямку|в напрямку|курс на|курс)\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-\s]+?)(?:\.|$)', text_lower)
    if p7:
        source_region = p7.group(1)
        target_city = p7.group(3).strip()

        source_coords = _get_region_center(source_region)
        target_coords = _get_city_coords(target_city)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': target_city.title(),
                'kind': 'region_to_city'
            }

    # =========================================================================
    # Pattern 7b: "БпЛА над [регіон] курсом на [напрямок]"
    # Example: "🛵 Шахед над Вінницькою областю курсом на північ"
    # =========================================================================
    p7b = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+(?:над|на)\s+([а-яіїєґ]+(?:ою|ій)\s+област[іиюь]|[а-яіїєґ]+(щин|ччин)[іиою])\s*,?\s*курсом?\s+на\s+(північ|південь|схід|захід|північний[\s-]*схід|північний[\s-]*захід|південний[\s-]*схід|південний[\s-]*захід)', text_lower)
    if p7b:
        source_region = p7b.group(1)
        direction = p7b.group(3)

        source_coords = _get_region_center(source_region)
        if source_coords:
            direction_vec = _get_direction_vector(direction)
            if direction_vec:
                end_lat = source_coords[0] + direction_vec[0] * 0.5
                end_lng = source_coords[1] + direction_vec[1] * 0.5
                return {
                    'start': [source_coords[0], source_coords[1]],
                    'end': [end_lat, end_lng],
                    'source_name': source_region.title(),
                    'target_name': f'курс на {direction}',
                    'kind': 'region_course_direction'
                }

    # =========================================================================
    # Pattern 7c: "Група БпЛА на [регіон] в напрямку [місто]"
    # Example: "🛵 Група БпЛА на Одещині в напрямку Миколаєва"
    # =========================================================================
    p7c = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+(?:на|над)\s+([а-яіїєґ]+(щин|ччин)[іиї])\s*,?\s*(?:в|у)\s+напрямку\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)', text_lower)
    if p7c:
        source_region = p7c.group(1)
        target_city = p7c.group(3).strip()

        source_coords = _get_region_center(source_region)
        target_coords = _get_city_coords(target_city)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': target_city.title(),
                'kind': 'region_towards_city_v2'
            }

    # =========================================================================
    # Pattern 7a: "БпЛА з акваторії [море] на [регіон], курс на [місто]"
    # Example: "Група БпЛА з акваторії Чорного моря на Одещині. курс на Старі Трояни."
    # =========================================================================
    p7a = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+акваторії\s+([а-яіїєґ\'\-\s]+моря)\s+на\s+([а-яіїєґ]+(щин|ччин)[іиї])[,.\s]+курс\s+(?:на\s+)?(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-\s]+?)(?:\.|$)', text_lower)
    if p7a:
        sea_name = p7a.group(1)
        region = p7a.group(2)
        target_city = p7a.group(4).strip()

        # Coordinates for seas (approximate entry points to Ukraine)
        sea_coords = {
            'чорного моря': (45.5, 31.5),  # Black Sea south of Odesa
            'азовського моря': (46.5, 36.5),  # Azov Sea
        }

        source_coords = sea_coords.get(sea_name, (45.5, 31.5))  # Default to Black Sea
        target_coords = _get_city_coords(target_city)

        # Fallback to region center if city not found
        if not target_coords:
            target_coords = _get_region_center(region)

        if target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': sea_name.title(),
                'target_name': target_city.title(),
                'kind': 'sea_to_city'
            }

    # =========================================================================
    # Pattern 8: "БпЛА на [напрямок] [регіон]" (position only, no course)
    # Example: "БпЛА на півдні Миколаївщини"
    # Note: This is just a position, not a full trajectory
    # =========================================================================
    p8 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+(півноч[іи]|півдн[іи]|сход[іи]|заход[іи]|північн\w*[\s-]*схо\w*|північн\w*[\s-]*захо\w*|південн\w*[\s-]*схо\w*|південн\w*[\s-]*захо\w*)\s+([а-яіїєґ]+(щин|ччин)[иі])', text_lower)
    if p8:
        direction_in_region = p8.group(1)
        region = p8.group(2)

        # Check if there's a course direction mentioned later in the text
        # Put compound directions FIRST to match them before simple ones
        course_match = re.search(r'курс\s+(північн\w*-?схід\w*|північн\w*-?захід\w*|південн\w*-?схід\w*|південн\w*-?захід\w*|північн\w*|південн\w*|східн\w*|західн\w*)', text_lower)

        source_coords = _get_region_center(region)
        if source_coords:
            direction_vec = _get_direction_vector(direction_in_region)
            if direction_vec:
                start_lat = source_coords[0] + direction_vec[0] * 0.3
                start_lng = source_coords[1] + direction_vec[1] * 0.3

                if course_match:
                    course_direction = course_match.group(1)
                    course_vec = _get_direction_vector(course_direction)
                    if course_vec:
                        end_lat = start_lat + course_vec[0] * 0.5
                        end_lng = start_lng + course_vec[1] * 0.5
                        return {
                            'start': [start_lat, start_lng],
                            'end': [end_lat, end_lng],
                            'source_name': f'{direction_in_region} {region}'.title(),
                            'target_name': f'курс {course_direction}',
                            'kind': 'region_position_with_course'
                        }

    # =========================================================================
    # Pattern 9: "БпЛА на [регіон], повз м.[місто] курсом на [регіон]"
    # Example: "БпЛА на Миколаївщині, повз М.Миколаїв курсом на Одещину"
    # =========================================================================
    p9 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+([а-яіїєґ]+(щин|ччин)[іиї])[,\s]+повз\s+(?:м\.?|місто\s+)?([а-яіїєґ\'\-]+)\s+курсом\s+на\s+([а-яіїєґ]+(щин|ччин)[ауиію])', text_lower)
    if p9:
        source_region = p9.group(1)
        via_city = p9.group(3)
        target_region = p9.group(4)

        via_coords = _get_city_coords(via_city)
        target_coords = _get_region_center(target_region)

        if via_coords and target_coords:
            return {
                'start': [via_coords[0], via_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': f'{via_city} ({source_region})'.title(),
                'target_name': target_region.title(),
                'kind': 'via_city_to_region'
            }

    # =========================================================================
    # Pattern 10: "БпЛА з [регіон] на [регіон], напрямок м.[місто]"
    # Example: "БпЛА з Херсонщини на Миколаївщину, напрямок м.Миколаїв"
    # =========================================================================
    p10 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+([а-яіїєґ]+(щин|ччин)[иі])\s+на\s+([а-яіїєґ]+(щин|ччин)[ауиію])[,\s]+(?:напрямок|напрям)\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)', text_lower)
    if p10:
        source_region = p10.group(1)
        mid_region = p10.group(3)
        target_city = p10.group(5)

        source_coords = _get_region_center(source_region)
        target_coords = _get_city_coords(target_city)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': f'{target_city} ({mid_region})'.title(),
                'kind': 'region_via_region_to_city'
            }

    # =========================================================================
    # Pattern 11: "БпЛА на [напрямок] [регіон], напрямок н.п.[місто]"
    # Example: "БпЛА на сході Сумщини, напрямок н.п.Лебедин"
    # =========================================================================
    p11 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+(півноч[іи]|півдн[іи]|сход[іи]|заход[іи]|північн\w*[\s-]*схо\w*|північн\w*[\s-]*захо\w*|південн\w*[\s-]*схо\w*|південн\w*[\s-]*захо\w*)\s+([а-яіїєґ]+(щин|ччин)[иі])[,\s]+(?:напрямок|напрям)\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)', text_lower)
    if p11:
        direction_in_region = p11.group(1)
        source_region = p11.group(2)
        target_city = p11.group(4)

        source_coords = _get_region_center(source_region)
        target_coords = _get_city_coords(target_city)

        if source_coords and target_coords:
            direction_vec = _get_direction_vector(direction_in_region)
            if direction_vec:
                start_lat = source_coords[0] + direction_vec[0] * 0.3
                start_lng = source_coords[1] + direction_vec[1] * 0.3
            else:
                start_lat, start_lng = source_coords

            return {
                'start': [start_lat, start_lng],
                'end': [target_coords[0], target_coords[1]],
                'source_name': f'{direction_in_region} {source_region}'.title(),
                'target_name': target_city.title(),
                'kind': 'region_position_to_city'
            }

    # =========================================================================
    # Pattern 12: "БпЛА на межі [регіон1] та [регіон2] областей, курс [напрямок]"
    # Example: "БпЛА на межі Сумської та Чернігівської областей,курс південний"
    # =========================================================================
    p12 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+меж[іи]\s+([а-яіїєґ]+)\w*\s+(?:та|і|й)\s+([а-яіїєґ]+)\w*\s+(?:областей|обл)[,\s]*курс\s+(північн\w*|південн\w*|східн\w*|західн\w*|північн\w*[\s-]*схід\w*|північн\w*[\s-]*захід\w*|південн\w*[\s-]*схід\w*|південн\w*[\s-]*захід\w*)', text_lower)
    if p12:
        region1_base = p12.group(1)
        region2_base = p12.group(2)
        course_direction = p12.group(3)

        # Try to find both regions
        region1_coords = None
        region2_coords = None

        for key, coords in OBLAST_CENTERS.items():
            if region1_base in key:
                region1_coords = coords
            if region2_base in key:
                region2_coords = coords

        if region1_coords and region2_coords:
            # Start at midpoint between regions
            start_lat = (region1_coords[0] + region2_coords[0]) / 2
            start_lng = (region1_coords[1] + region2_coords[1]) / 2

            course_vec = _get_direction_vector(course_direction)
            if course_vec:
                end_lat = start_lat + course_vec[0] * 0.5
                end_lng = start_lng + course_vec[1] * 0.5
                return {
                    'start': [start_lat, start_lng],
                    'end': [end_lat, end_lng],
                    'source_name': f'межа {region1_base}/{region2_base}',
                    'target_name': f'курс {course_direction}',
                    'kind': 'border_with_course'
                }

    # =========================================================================
    # Pattern 13: "БпЛА в напрямку м.[місто]"
    # Example: "БпЛА на Дніпропетровщині в напрямку м.Павлоград"
    # =========================================================================
    p13 = re.search(r'(?:бпла|шахед|дрон|група\s+бпла)\s+(?:на\s+)?([а-яіїєґ]+(щин|ччин)[іи])?\s*(?:в|у)\s+напрямку\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)', text_lower)
    if p13:
        source_region = p13.group(1) if p13.group(1) else None
        target_city = p13.group(3)

        target_coords = _get_city_coords(target_city)

        if target_coords:
            if source_region:
                source_coords = _get_region_center(source_region)
                if source_coords:
                    return {
                        'start': [source_coords[0], source_coords[1]],
                        'end': [target_coords[0], target_coords[1]],
                        'source_name': source_region.title(),
                        'target_name': target_city.title(),
                        'kind': 'region_towards_city'
                    }

    # =========================================================================
    # Pattern 14: "БпЛА [місто] курсом на [місто]"
    # Example: "БпЛА Боромля курсом на Тростянець"
    # CRITICAL: Marker should be at SOURCE city (where drone IS), NOT at target!
    # =========================================================================
    p14 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)\s+курсом\s+на\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)', text_lower)
    if p14:
        source_city = p14.group(1)
        target_city = p14.group(2)

        source_coords = _get_city_coords(source_city)
        target_coords = _get_city_coords(target_city)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],  # SOURCE - current position
                'end': [target_coords[0], target_coords[1]],    # TARGET - where going
                'source_name': source_city.title(),
                'target_name': target_city.title(),
                'kind': 'city_course_to_city'
            }

    return None

def process_message(text, mid, date_str, channel, _disable_multiline=False):  # type: ignore
    import re

    # Helper function to clean text from subscription prompts
    def clean_text(text_to_clean):
        if not text_to_clean:
            return text_to_clean
        import re as re_import
        cleaned = []
        for ln in text_to_clean.splitlines():
            ln2 = ln.strip()
            if not ln2:
                continue
            # Remove invisible/unicode spaces and normalize
            ln2 = re_import.sub(r'[\u200B-\u200D\uFEFF\u3164\u2060\u00A0\u1680\u180E\u2000-\u200F\u202A-\u202E\u2028\u2029\u205F\u3000]+', ' ', ln2)
            ln2 = ln2.strip()

            # Check if line ends with subscription text after meaningful content (including bold **text**)
            subscription_match = re_import.search(r'^(.+?)\s+[➡→>⬇⬆⬅⬌↗↘↙↖]\s*(\*\*)?підписатися(\*\*)?\s*$', ln2, re_import.IGNORECASE)
            if subscription_match:
                # Extract the part before the subscription text
                main_content = subscription_match.group(1).strip()
                if main_content and len(main_content) > 5:  # Only keep if meaningful content
                    cleaned.append(main_content)
                continue

            # remove any line that is ONLY a subscribe CTA (including bold)
            if re_import.search(r'^[➡→>⬇⬆⬅⬌↗↘↙↖]?\s*(\*\*)?підписатися(\*\*)?\s*$', ln2, re_import.IGNORECASE):
                continue

            # Remove URLs and links from text
            ln2 = re_import.sub(r'https?://[^\s]+', '', ln2)  # Remove http/https links
            ln2 = re_import.sub(r'www\.[^\s]+', '', ln2)      # Remove www links
            ln2 = re_import.sub(r't\.me/[^\s]+', '', ln2)     # Remove Telegram links
            ln2 = re_import.sub(r'@[a-zA-Z0-9_]+', '', ln2)  # Remove @mentions
            ln2 = re_import.sub(r'_+', '', ln2)  # Remove leftover underscores
            ln2 = re_import.sub(r'[✙✚]+[^✙✚]*✙[^✙✚]*✙', '', ln2)  # Remove ✙...✙ patterns

            # Remove card numbers and bank details
            ln2 = re_import.sub(r'\d{4}\s*\d{4}\s*\d{4}\s*\d{4}', '', ln2)  # Card numbers
            ln2 = re_import.sub(r'[—-]\s*Картка:', '', ln2)  # Card labels
            ln2 = re_import.sub(r'[—-]\s*Банка:', '', ln2)   # Bank labels
            ln2 = re_import.sub(r'[—-]\s*Конверт:', '', ln2) # Envelope labels

            # Clean up multiple spaces and trim
            ln2 = re_import.sub(r'\s+', ' ', ln2).strip()

            # Skip empty lines after cleaning
            if not ln2:
                continue

            cleaned.append(ln2)
        return '\n'.join(cleaned)

    # PRIORITY: Check for trajectory patterns FIRST using the comprehensive parser
    trajectory_data = parse_trajectory_from_message(text)
    if trajectory_data:
        print(f"DEBUG: Trajectory parsed - kind={trajectory_data.get('kind')}, source={trajectory_data.get('source_name')}, target={trajectory_data.get('target_name')}")

        # IMPORTANT: Marker should be at SOURCE (current position), NOT at target!
        # The drone is at source and flying TOWARDS target
        source_coords = trajectory_data['start']
        target_coords = trajectory_data['end']

        # Classify threat type based on message text
        text_lower = text.lower()
        if 'шахед' in text_lower or 'shahed' in text_lower:
            threat_type, icon = 'shahed', 'shahed3.webp'
        elif 'бпла' in text_lower or 'дрон' in text_lower:
            threat_type, icon = 'shahed', 'shahed3.webp'
        elif 'ракет' in text_lower:
            threat_type, icon = 'raketa', 'icon_balistic.svg'
        else:
            threat_type, icon = 'shahed', 'shahed3.webp'

        # =====================================================================
        # ENHANCED AI PREDICTION: Add ETA, multi-targets, confidence
        # =====================================================================
        enhanced_trajectory = get_enhanced_trajectory_prediction(trajectory_data, text)
        if enhanced_trajectory:
            trajectory_data = enhanced_trajectory
            # Update icon based on refined threat type
            if enhanced_trajectory.get('threat_type') == 'ballistic':
                icon = 'icon_balistic.svg'
            elif enhanced_trajectory.get('threat_type') == 'cruise':
                icon = 'icon_rocket.svg'

        # Place name shows direction: Source → Target
        place_name = f"{trajectory_data.get('source_name', 'Джерело')} → {trajectory_data.get('target_name', 'Ціль')}"

        # ETA in place name - DISABLED
        # eta_info = trajectory_data.get('eta', {})
        # if eta_info.get('formatted'):
        #     place_name += f" (ETA: {eta_info['formatted']})"

        trajectory_marker = {
            'id': str(mid),
            'place': place_name,
            'lat': source_coords[0],  # MARKER AT SOURCE (current position)
            'lng': source_coords[1],  # NOT at target!
            'threat_type': threat_type,
            'text': text[:500],
            'date': date_str,
            'channel': channel,
            'marker_icon': icon,
            'source_match': f'trajectory_{trajectory_data.get("kind", "unknown")}',
            'trajectory': trajectory_data
        }

        # Add enhanced prediction data
        if trajectory_data.get('eta'):
            trajectory_marker['eta'] = trajectory_data['eta']
        if trajectory_data.get('alternative_targets'):
            trajectory_marker['alternative_targets'] = trajectory_data['alternative_targets']
        if trajectory_data.get('confidence'):
            trajectory_marker['prediction_confidence'] = trajectory_data['confidence']
        if trajectory_data.get('confidence_level'):
            trajectory_marker['confidence_level'] = trajectory_data['confidence_level']
        if trajectory_data.get('distance_km'):
            trajectory_marker['distance_km'] = trajectory_data['distance_km']
        if trajectory_data.get('speed_kmh'):
            trajectory_marker['speed_kmh'] = trajectory_data['speed_kmh']

        # AUTO-RECORD: Save observed route for pattern learning (non-blocking)
        try:
            if not trajectory_data.get('predicted'):  # Only record confirmed routes
                update_route_pattern_with_ai({
                    'source_region': trajectory_data.get('source_name'),
                    'target_region': trajectory_data.get('target_name'),
                    'waypoints': [],
                    'threat_type': threat_type
                })
        except Exception as e:
            print(f"DEBUG: Failed to record route pattern: {e}")

        return [trajectory_marker]

    # EARLY FILTERS: Check for messages that should be completely filtered out
    def _is_russian_strategic_aviation(t: str) -> bool:
        """Suppress messages about Russian strategic aviation (Tu-95, etc.) from Russian airbases"""
        t_lower = t.lower()

        # Check for Russian strategic bombers
        russian_bombers = ['ту-95', 'tu-95', 'ту-160', 'tu-160', 'ту-22', 'tu-22']
        has_bomber = any(bomber in t_lower for bomber in russian_bombers)

        # Check for Russian airbases and regions
        russian_airbases = ['енгельс', 'engels', 'энгельс', 'саратов', 'рязань', 'муром', 'украінка', 'українка']
        has_russian_airbase = any(airbase in t_lower for airbase in russian_airbases)

        # Check for Russian regions/areas
        russian_regions = ['саратовській області', 'саратовской области', 'тульській області', 'рязанській області']
        has_russian_region = any(region in t_lower for region in russian_regions)

        # Check for terms indicating Russian territory/airbases
        russian_territory_terms = ['аеродрома', 'аэродрома', 'з аеродрому', 'с аэродрома', 'мета вильоту невідома', 'цель вылета неизвестна']
        has_russian_territory = any(term in t_lower for term in russian_territory_terms)

        # Check for generic relocation/transfer terms without specific threats
        relocation_terms = ['передислокація', 'передислокация', 'переліт', 'перелет', 'відмічено', 'отмечено']
        has_relocation = any(term in t_lower for term in relocation_terms)

        # Suppress if it's about Russian bombers from Russian territory
        if has_bomber and (has_russian_airbase or has_russian_territory or has_russian_region):
            return True

        # Suppress relocation/transfer messages between Russian airbases
        if has_relocation and has_bomber and (has_russian_airbase or has_russian_region):
            return True

        # Also suppress general strategic aviation reports without specific Ukrainian targets
        if ('борт' in t_lower or 'борти' in t_lower) and ('мета вильоту невідома' in t_lower or 'цель вылета неизвестна' in t_lower):
            return True

        return False

    def _is_general_warning_without_location(t: str) -> bool:
        """Suppress general warnings without specific locations or threat details"""
        t_lower = t.lower()

        # Check for general warning phrases
        warning_phrases = [
            'протягом ночі уважним бути',
            'протягом дня уважним бути',
            'уважним бути',
            'загальне попередження',
            'общее предупреждение'
        ]
        has_general_warning = any(phrase in t_lower for phrase in warning_phrases)

        # Check for alert messages that should only be in events, not on map
        alert_phrases = [
            'відбій тривоги',
            'повітряна тривога',
            'відбой тревоги',
            'воздушная тревога'
        ]
        has_alert_message = any(phrase in t_lower for phrase in alert_phrases)

        # Suppress alert messages - they should only be in events
        if has_alert_message:
            return True

        # Check for tactical threat messages first - these should NEVER be filtered
        tactical_phrases = [
            'бпла',
            'крилаті ракети',
            'ракет',
            'ракета',
            'ракети',
            'загроза',
            'курсом на',
            'наближається',
            'повз',
            'поблизу',
            'напрямок',
            'напрямку',
            'у напрямку',
            'кв шахед',
            'шахед',
            'каб',
            'умп',
            'іскандер'
        ]
        has_tactical_info = any(phrase in t_lower for phrase in tactical_phrases)

        # Check for informational/historical messages that should be filtered
        # even if they contain tactical terms
        informational_phrases = [
            'пролетів',
            'відвернув',
            'здійснив посадку',
            'посадку на аеродром',
            'активність бортів',
            'буду оновлювати',
            'в разі додаткової інформації',
            'наразі це єдина',
            'фактична активність'
        ]
        has_informational_content = any(phrase in t_lower for phrase in informational_phrases)

        # Check if this is actually a current location message (not brief update)
        current_location_phrases = [
            'над',
            'в районі',
            'атакував',
            'вибухи в',
            'влучання в',
            'збито в',
            'знищено в',
            'на херсонщині',
            'на дніпропетровщині',
            'на запоріжжі',
            'на харківщині',
            'в області',
            'область',
            'щині'
        ]
        has_current_location = any(phrase in t_lower for phrase in current_location_phrases)

        # Check for count prefix (e.g., "16х БпЛА", "3х БпЛА") - these are real threats
        has_count_prefix = re.search(r'\d+\s*[xх]\s*бпла', t_lower)

        # If message has threat count or current location, do NOT filter it
        if has_count_prefix or has_current_location:
            return False

        # Check for general status messages that contain tactical terms but are informational
        status_phrases = [
            'український | ппошник',
            'український|ппошник',
            'поділ лук\'янівка'
        ]
        has_status_message = any(phrase in t_lower for phrase in status_phrases)

        # Check for route/location listing messages (format: "city — city1/city2 | region:")
        route_listing_pattern = r'київ.*—.*жуляни.*вишневе.*київ'
        has_route_listing = re.search(route_listing_pattern, t_lower, re.IGNORECASE)

        # Filter route listing messages as they are informational
        if has_route_listing:
            return True

        # If message is informational/historical, filter it out
        if has_informational_content:
            return True

        # If message is a general status update with tactical info, filter it out
        if has_status_message and has_tactical_info:
            return True

        # If message contains tactical information and is not informational, do NOT filter it
        if has_tactical_info:
            return False

        # Check for donation/fundraising messages (use more specific phrases)
        donation_phrases = [
            'підтримайте мене',
            'підтримати канал',
            'реквізити',
            'картка:',
            'банка:',
            'грн на каву',
            'на каву та енергетики',
            'по бажанню',
            'підтримка тільки',
            'monobank.ua',
            'privat24.ua',
            'send.monobank',
            'www.privat24',
            'донати',
            'донат',
            'дуже вдячний',
            'вдячний вам за підтримку',
            'за підтримку',
            'дякую за підтримку'
        ]
        has_donation_message = any(phrase in t_lower for phrase in donation_phrases)

        # Suppress donation messages
        if has_donation_message:
            return True

        # Check for channel promotion messages
        promotion_phrases = [
            'підтримати канал',
            'спасибо за подписку',
            'подписывайтесь',
            'наш канал',
            'наш телеграм'
        ]
        has_promotion_message = any(phrase in t_lower for phrase in promotion_phrases)

        # Suppress promotion messages
        if has_promotion_message:
            return True

        # Check for general informational messages without threats
        info_phrases = [
            'наразі це єдина',
            'фактична активність',
            'буду оновлювати',
            'в разі додаткової інформації',
            'здійснив посадку',
            'посадку на аеродром',
            'активність бортів'
        ]
        has_info_message = any(phrase in t_lower for phrase in info_phrases)

        # Suppress general info messages
        if has_info_message:
            return True

        # Check for very broad regions without specific cities
        broad_regions = [
            'києву, київщина і західна україна',
            'київ, київщина і західна україна',
            'центр і північ',
            'південь і схід'
        ]
        has_broad_region = any(region in t_lower for region in broad_regions)

        # Suppress if it's a general warning with broad regions
        if has_general_warning and has_broad_region:
            return True

        # Also suppress very short messages that are just general alerts
        if len(t.strip()) < 50 and has_general_warning:
            return True

        return False

    # Apply early filters
    if _is_russian_strategic_aviation(text):
        return []

    if _is_general_warning_without_location(text):
        return []

    # PRIORITY: Handle directional movement patterns (у напрямку, в направлении)
    # These should show trajectory/direction, not markers at destination
    def _is_directional_movement_message(t: str) -> bool:
        """Check if message describes movement towards a destination"""
        t_lower = t.lower()

        # Patterns indicating movement toward destination, not presence at location
        directional_patterns = [
            'у напрямку',
            'в напрямку',
            'напрямок',
            'рухається в напрямку',
            'летить у напрямку',
            'курс на',
            'прямує до'
        ]

        # Additional context that suggests this is about movement, not current location
        movement_context = [
            'з північного-сходу',
            'з півдня',
            'з заходу',
            'з сходу',
            'рухається',
            'летить',
            'прямує'
        ]

        has_directional = any(pattern in t_lower for pattern in directional_patterns)
        has_movement_context = any(context in t_lower for context in movement_context)

        return has_directional and has_movement_context

    # Handle directional movement messages - create projected path instead of filtering
    if _is_directional_movement_message(text):
        return _create_directional_trajectory_markers(text, mid, date_str, channel)

    # PRIORITY: Try SpaCy enhanced processing first
    if SPACY_AVAILABLE:
        try:
            spacy_results = spacy_enhanced_geocoding(text)
            if spacy_results:
                # Convert SpaCy results to the format expected by the rest of the system
                threat_markers = []

                # Process cities with coordinates first
                cities_with_coords = [city for city in spacy_results if city['coords']]

                for spacy_city in cities_with_coords:
                    lat, lng = spacy_city['coords']

                    # Determine threat type using our classify function
                    threat_type, icon = classify(text, spacy_city['name'])

                    # Create a proper place label
                    place_label = spacy_city['name'].title()
                    if spacy_city['region']:
                        place_label += f" [{spacy_city['region'].title()}]"

                    marker = {
                        'id': f"{mid}_spacy_{len(threat_markers)+1}",
                        'place': place_label,
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': clean_text(text)[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': f'spacy_{spacy_city["source"]}',
                        'count': 1,
                        'confidence': spacy_city['confidence']
                    }
                    threat_markers.append(marker)

                    add_debug_log(f"SPACY: Created marker for {spacy_city['name']} -> {spacy_city['normalized']} "
                                f"(case: {spacy_city.get('case', 'unknown')}, confidence: {spacy_city['confidence']})",
                                "spacy_integration")

                if threat_markers:
                    add_debug_log(f"SPACY: Successfully processed message with {len(threat_markers)} markers", "spacy_integration")
                    return threat_markers

        except Exception as e:
            add_debug_log(f"SPACY: Error processing message: {e}", "spacy_integration")
            # Continue with fallback processing

    # FALLBACK: Original regex-based processing continues below

    # PRIORITY: Handle "[city] на [region]" patterns early to avoid misprocessing
    regional_city_match = re.search(r'(\d+)\s+шахед[а-яіїєёыийї]*\s+на\s+([а-яіїєё\'\-\s]+?)\s+на\s+([а-яіїє]+щині?)', text.lower()) if text else None
    if regional_city_match:
        count_str = regional_city_match.group(1)
        city_raw = regional_city_match.group(2).strip()
        region_raw = regional_city_match.group(3).strip()

        # Use context-aware resolution
        coords = ensure_city_coords_with_message_context(city_raw, text)
        if coords:
            lat, lng, approx = coords
            add_debug_log(f"PRIORITY: Regional city pattern - {city_raw} на {region_raw} -> ({lat}, {lng})", "priority_regional_city")

            result_entry = {
                'id': f"{mid}_priority_regional",
                'place': f"{city_raw.title()} на {region_raw.title()}",
                'lat': lat, 'lng': lng,
                'type': 'shahed', 'count': int(count_str),
                'timestamp': date_str, 'channel': channel
            }
            return [result_entry]

    # EARLY CHECK: General multi-line threat detection (before specific cases)
    if not _disable_multiline:
        text_lines = (text or '').split('\n')
        threat_lines = []

        # Track current oblast context from headers like "Полтавщина:", "Харківщина:"
        current_oblast = None
        oblast_header_pattern = re.compile(r'^([а-яіїєґ]+(?:щина|ська\s+обл(?:асть)?\.?)):?\s*$', re.IGNORECASE)
        # Pattern for inline oblast: "Сумщина: 2 шахеди на Лебедин"
        inline_oblast_pattern = re.compile(r'^([а-яіїєґ]+(?:щина|ська\s+обл(?:асть)?\.?)):\s+(.+)$', re.IGNORECASE)

        # Look for lines that contain threats with quantities and targets
        for line in text_lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Check if this line has inline oblast format: "Область: threat text"
            inline_match = inline_oblast_pattern.match(line_stripped)
            if inline_match:
                oblast_name = inline_match.group(1).lower()
                threat_text = inline_match.group(2).strip()

                # Add the threat with oblast context
                enhanced_line = f"{oblast_name}: {threat_text}"
                threat_lines.append(enhanced_line)
                add_debug_log(f"MULTI-LINE: Detected inline oblast threat: {oblast_name} -> {threat_text[:50]}", "multi_line_inline_oblast")
                continue

            # Check if this line is a standalone oblast header
            oblast_match = oblast_header_pattern.match(line_stripped)
            if oblast_match:
                current_oblast = oblast_match.group(1).lower()
                add_debug_log(f"MULTI-LINE: Detected oblast header: {current_oblast}", "multi_line_oblast")
                continue

            line_lower = line_stripped.lower()

            # Check if line contains threat patterns with quantities and targets
            has_threat_pattern = (
                # Pattern: "Ціль на [target]" - target city for missiles/drones
                (re.search(r'ціль\s+на\s+([а-яіїєё\'\-\s]+)', line_lower, re.IGNORECASE)) or
                # Pattern: "N БпЛА на [region]щині" - regional threats like "16х БпЛА на Херсонщині"
                (re.search(r'\d+\s*[xх×]?\s*бпла\s+на\s+([а-яіїєё]+щині)', line_lower, re.IGNORECASE)) or
                # Pattern: "БпЛА на [direction] [region]" - regional directional threats
                (re.search(r'бпла\s+на\s+(півночі|півдні|сході|заході|північ|південь|схід|захід)\s+([а-яіїєё]+щин[іауи]?)', line_lower, re.IGNORECASE)) or
                # Pattern: "БпЛА ... з акваторії Чорного моря" - Black Sea threats
                (re.search(r'бпла.*?(з\s+акваторії|з\s+моря|з\s+чорного\s+моря)', line_lower, re.IGNORECASE)) or
                # Pattern: "N x/× БпЛА курсом на [target]"
                (re.search(r'\d+\s*[xх×]\s*бпла.*?(курс|на)\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахедів/шахеди на [target]" - all forms of Shahed
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+на\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахедів/шахеди біля [target]" - near target
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+біля\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахед маневрує в районі [target]" - maneuvering in area
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+маневру[юєї]+\s+в\s+район[іуи]\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N ударних БпЛА на [target]"
                (re.search(r'\d+\s+ударн.*?бпла.*?на\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N БпЛА на [target]" or "N бпла на [target]"
                (re.search(r'\d+\s+бпла.*?на\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "БпЛА курсом на [target]" (without count)
                (re.search(r'бпла.*?курс.*?на\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахедів через [target]" - via target
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+через\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахедів з боку [target]" - from direction of target
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+з\s+боку\s+([а-яіїєё\'\-\s]+)', line_lower))
            )

            if has_threat_pattern:
                # If we have oblast context, prepend it to the line
                if current_oblast:
                    # Add oblast context to help city resolution
                    enhanced_line = f"{current_oblast}: {line_stripped}"
                    threat_lines.append(enhanced_line)
                    add_debug_log(f"MULTI-LINE: Added threat with oblast context: {current_oblast} -> {line_stripped[:50]}", "multi_line_context")
                else:
                    threat_lines.append(line_stripped)

        # If we have multiple threat lines, process them separately
        if len(threat_lines) >= 2:
            add_debug_log(f"MULTI-LINE THREAT PROCESSING: {len(threat_lines)} threat lines detected", "multi_line_threats")

            all_tracks = []
            for i, line in enumerate(threat_lines):
                if not line.strip():
                    continue

                add_debug_log(f"Processing threat line {i+1}: {line[:100]}", "threat_line")

                # Process each line as a separate message with multiline disabled
                line_result = process_message(line.strip(), f"{mid}_threat_{i+1}", date_str, channel, _disable_multiline=True)
                if line_result and isinstance(line_result, list):
                    all_tracks.extend(line_result)
                    add_debug_log(f"Threat line {i+1} produced {len(line_result)} tracks", "threat_line_result")
                else:
                    add_debug_log(f"Threat line {i+1} produced no tracks", "threat_line_result")

            if all_tracks:
                add_debug_log(f"Multi-line threat processing complete: {len(all_tracks)} total tracks", "multi_line_threats_complete")
                return all_tracks

    # PRIORITY FIRST: All air alarm messages should be list-only (no map markers)
    # This must be checked BEFORE any other processing to prevent other logic from creating markers
    original_text = text or ''
    low_orig = original_text.lower()

    # Clear any previous priority result
    globals()['_current_priority_result'] = None

    # PRIORITY CHECK: Black Sea aquatory - must check BEFORE multi-regional processing
    # Messages like "БпЛА курсом на Миколаїв з акваторії Чорного моря" or "15 шахедів з моря на Ізмаїл" should NOT place markers on cities
    lower_text = original_text.lower()
    # Check for Black Sea references: акваторія OR "з моря" OR "з чорного моря"
    is_black_sea = (('акватор' in lower_text or 'акваторії' in lower_text) and ('чорного моря' in lower_text or 'чорне море' in lower_text or 'чорному морі' in lower_text)) or \
                   ('з моря' in lower_text and ('курс' in lower_text or 'на ' in lower_text)) or \
                   ('з чорного моря' in lower_text)

    if is_black_sea:
        # Extract target region/direction if mentioned
        m_target = re.search(r'курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower_text)
        m_direction = re.search(r'на\s+(північ|південь|схід|захід|північний\s+схід|північний\s+захід|південний\s+схід|південний\s+захід)', lower_text)
        m_region = re.search(r'(одещин|одеськ|миколаїв|херсон)', lower_text)

        target_info = None
        sea_lat, sea_lng = 45.3, 30.7  # Default: northern Black Sea central coords

        # Adjust position based on direction/region
        if m_direction:
            direction = m_direction.group(1)
            if 'південь' in direction:
                sea_lat = 45.0  # Further south
            elif 'північ' in direction:
                sea_lat = 45.6  # Further north
            if 'схід' in direction:
                sea_lng = 31.2  # Further east
            elif 'захід' in direction:
                sea_lng = 30.2  # Further west

        if m_region:
            region_name = m_region.group(1)
            if 'одещин' in region_name or 'одеськ' in region_name:
                # South of Odesa region - in the sea 50km offshore
                sea_lat, sea_lng = 45.7, 30.7
                target_info = 'Одещини'
            elif 'миколаїв' in region_name:
                sea_lat, sea_lng = 45.9, 31.4
                target_info = 'Миколаївщини'
            elif 'херсон' in region_name:
                sea_lat, sea_lng = 45.7, 32.5
                target_info = 'Херсонщини'

        if m_target:
            tc = m_target.group(1).lower()
            tc = UA_CITY_NORMALIZE.get(tc, tc)
            target_info = tc.title()

        threat_type, icon = classify(original_text)
        place_label = 'Акваторія Чорного моря'
        if target_info:
            place_label += f' (на {target_info})'

        # Try to find target city coordinates for trajectory
        target_coords = None
        if m_target:
            tc_normalized = m_target.group(1).lower()
            tc_normalized = UA_CITY_NORMALIZE.get(tc_normalized, tc_normalized)
            if tc_normalized in CITY_COORDS:
                target_coords = CITY_COORDS[tc_normalized]

        result = {
            'id': str(mid), 'place': place_label, 'lat': sea_lat, 'lng': sea_lng,
            'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': icon, 'source_match': 'black_sea_course_priority'
        }

        # Add trajectory data if we have target coordinates
        if target_coords:
            result['trajectory'] = {
                'start': [sea_lat, sea_lng],
                'end': list(target_coords),
                'target': target_info
            }

        return [result]

    # IMMEDIATE CHECK: Multi-regional UAV messages (highest priority)
    text_lines = original_text.split('\n')
    region_count = sum(1 for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:', 'край:']) or (
        'щина' in line.lower() and line.lower().strip().endswith(':')
    ) or any(region in line.lower() for region in ['щина)', 'щини', 'щину', 'одещина', 'чернігівщина', 'дніпропетровщина', 'харківщина', 'київщина']))
    # Look for lines with emoji + UAV mentions (more flexible detection)
    uav_lines = [line for line in text_lines if 'бпла' in line.lower() and ('🛵' in line or '🛸' in line)]
    uav_count = len(uav_lines)

    # NEW: Look for lines with Shahed mentions and regions (without emoji requirement)
    shahed_region_lines = [line for line in text_lines if
                          ('шахед' in line.lower() or 'shahed' in line.lower()) and
                          ('щина' in line.lower() or 'щину' in line.lower() or 'щині' in line.lower())]
    shahed_count = len(shahed_region_lines)

    # NEW: Check for multiple regional aviation/БПЛА threats in one message
    # Pattern: "🛫 Донеччина та Дніпропетровщина - загроза застосування авіаційних засобів ураження. 🛵 Харківщина - загроза застосування ударних БпЛА"
    aviation_threat_lines = []
    for line in text_lines:
        line_lower = line.lower().strip()
        if not line_lower:
            continue
        # Check if line contains region + aviation/БПЛА threat
        has_region = any(region in line_lower for region in ['щина', 'область'])
        has_aviation = any(pattern in line_lower for pattern in ['авіаційних засобів', 'авіації', 'тактична авіація'])
        has_bpla = 'бпла' in line_lower or 'безпілотн' in line_lower

        if has_region and (has_aviation or has_bpla):
            aviation_threat_lines.append(line)

    aviation_threat_count = len(aviation_threat_lines)

    add_debug_log(f"DEBUG COUNT CHECK: {region_count} regions, {uav_count} UAV lines, {shahed_count} Shahed+region lines, {aviation_threat_count} aviation threat lines", "count_check")

    # Process multiple regional aviation threats
    if aviation_threat_count >= 1:
        add_debug_log(f"MULTI-REGIONAL AVIATION THREATS: {aviation_threat_count} lines detected", "multi_aviation")

        all_tracks = []

        # Regional aviation coordinates mapping (Black Sea / oblast centers)
        region_aviation_coords = {
            'одещина': (46.373528, 31.284023),  # Black Sea near Odesa
            'одесщина': (46.373528, 31.284023),
            'донеччина': (48.5, 37.8),  # Donetsk oblast center
            'дніпропетровщина': (48.45, 35.0),  # Dnipro
            'харківщина': (49.9935, 36.2304),  # Kharkiv
            'луганщина': (48.567, 39.317),  # Luhansk oblast
            'запорожжя': (47.8388, 35.1396),  # Zaporizhzhia
            'херсонщина': (46.6354, 32.6169),  # Kherson
            'миколаївщина': (46.975, 32.0),  # Mykolaiv oblast
        }

        for line in aviation_threat_lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Split by emoji or sentence patterns to separate different threats
            # Pattern: "🛫 Region - threat. 🛵 Region - threat"
            import re

            # Split by emoji patterns or full stops followed by emoji
            segments = re.split(r'[\.\!]\s*(?=[🛫🛵🛸⚠️])|(?<=[🛫🛵🛸⚠️])\s+(?=[А-ЯІЇЄа-яіїє])', line_stripped)
            if len(segments) <= 1:
                # No clear segments, treat as one line
                segments = [line_stripped]

            for segment in segments:
                segment = segment.strip()
                if not segment or len(segment) < 10:
                    continue

                segment_lower = segment.lower()

                # Extract all regions from this segment
                regions_found = re.findall(r'(одещина|одесщина|донеччина|дніпропетровщина|харківщина|луганщина|запорожжя|херсонщина|миколаївщина)', segment_lower)

                # Determine threat type from segment content
                is_aviation = any(pattern in segment_lower for pattern in ['авіаційних засобів', 'авіації', 'тактична авіація'])
                is_bpla = 'бпла' in segment_lower or 'безпілотн' in segment_lower
                is_strike_bpla = 'ударних бпла' in segment_lower or 'ударних безпілотн' in segment_lower

                threat_type = 'avia' if is_aviation else ('shahed' if is_bpla else 'artillery')
                icon = 'avia.png' if is_aviation else ('shahed3.webp' if is_bpla else 'artillery.png')
                threat_label = 'Авіація' if is_aviation else ('Ударні БпЛА' if is_strike_bpla else 'БпЛА')

                # Create marker for each region mentioned in this segment
                for region in regions_found:
                    if region in region_aviation_coords:
                        coords = region_aviation_coords[region]
                        lat, lng = coords

                        region_display = region.title()
                        place_name = f"{threat_label} [{region_display}]"

                        track = {
                            'id': f"{mid}_aviation_{region}_{len(all_tracks)}",
                            'place': place_name,
                            'lat': lat,
                            'lng': lng,
                            'threat_type': threat_type,
                            'text': segment[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'multi_regional_aviation',
                            'count': 1
                        }

                        all_tracks.append(track)
                        add_debug_log(f"Aviation threat: {place_name} at {coords} (segment: {segment[:50]})", "multi_aviation")
                    else:
                        add_debug_log(f"No coords for region: {region}", "multi_aviation")

        if all_tracks:
            add_debug_log(f"Multi-regional aviation processing complete: {len(all_tracks)} total tracks", "multi_aviation_complete")
            return all_tracks

    add_debug_log(f"DEBUG COUNT CHECK: {region_count} regions, {uav_count} UAV lines, {shahed_count} Shahed+region lines", "count_check")

    # If we have multiple Shahed lines with regions, process them separately
    if shahed_count >= 2:
        add_debug_log(f"MULTI-LINE SHAHED PROCESSING: {shahed_count} Shahed+region lines detected", "multi_shahed")

        all_tracks = []
        for i, line in enumerate(shahed_region_lines):
            if not line.strip():
                continue

            add_debug_log(f"Processing Shahed line {i+1}: {line[:100]}", "shahed_line")

            # Process each line as a separate message
            line_result = process_message(line.strip(), f"{mid}_shahed_{i+1}", date_str, channel, _disable_multiline=True)
            if line_result and isinstance(line_result, list):
                all_tracks.extend(line_result)
                add_debug_log(f"Shahed line {i+1} produced {len(line_result)} tracks", "shahed_line_result")
            else:
                add_debug_log(f"Shahed line {i+1} produced no tracks", "shahed_line_result")

        if all_tracks:
            add_debug_log(f"Multi-line Shahed processing complete: {len(all_tracks)} total tracks", "multi_shahed_complete")
            return all_tracks

    # If we have multiple UAV lines with emojis, process them separately even if they don't have explicit regions
    if uav_count >= 2 and (region_count >= 1 or any('району' in line.lower() or 'області' in line.lower() or 'обл.' in line.lower() for line in uav_lines)):
        add_debug_log(f"MULTI-LINE UAV PROCESSING: {uav_count} UAV lines detected", "multi_uav")

        all_tracks = []
        for i, line in enumerate(uav_lines):
            if not line.strip():
                continue

            add_debug_log(f"Processing UAV line {i+1}: {line[:100]}", "uav_line")

            # Process each line as a separate message
            line_result = process_message(line.strip(), f"{mid}_line_{i+1}", date_str, channel, _disable_multiline=True)
            if line_result and isinstance(line_result, list):
                all_tracks.extend(line_result)
                add_debug_log(f"Line {i+1} produced {len(line_result)} tracks", "uav_line_result")
            else:
                add_debug_log(f"Line {i+1} produced no tracks", "uav_line_result")

        if all_tracks:
            add_debug_log(f"Multi-line UAV processing complete: {len(all_tracks)} total tracks", "multi_uav_complete")
            return all_tracks

    # Legacy multi-regional detection (keep for backward compatibility)
    if region_count >= 2 and sum(1 for line in text_lines if 'бпла' in line.lower() and ('курс' in line.lower() or 'на ' in line.lower())) >= 3:
        add_debug_log(f"IMMEDIATE MULTI-REGIONAL UAV: {region_count} regions, {uav_count} UAVs - ENTERING EARLY PROCESSING", "multi_regional")
        # Process directly without going through other logic
        import re

        # Define essential functions inline for immediate processing
        def get_city_coords_quick(city_name, region_hint=None):
            """Quick coordinate lookup with accusative case normalization and regional context"""
            city_norm = city_name.strip().lower()

            # Handle specific multi-word cities in accusative case
            if city_norm == 'велику димерку':
                city_norm = 'велика димерка'
            elif city_norm == 'велику виску':
                city_norm = 'велика виска'
            elif city_norm == 'мену':
                city_norm = 'мена'
            elif city_norm == 'пісківку':
                city_norm = 'пісківка'
            elif city_norm == 'новгород-сіверський':
                city_norm = 'новгород-сіверський'
            elif city_norm == 'києвом':
                city_norm = 'київ'

            # General accusative case endings (винительный падеж)
            elif city_norm.endswith('у') and len(city_norm) > 3:
                city_norm = city_norm[:-1] + 'а'
            elif city_norm.endswith('ю') and len(city_norm) > 3:
                city_norm = city_norm[:-1] + 'я'
            elif city_norm.endswith('ку') and len(city_norm) > 4:
                city_norm = city_norm[:-2] + 'ка'

            # Apply UA_CITY_NORMALIZE rules
            if city_norm in UA_CITY_NORMALIZE:
                city_norm = UA_CITY_NORMALIZE[city_norm]

            # ONLY OpenCage API - no local dictionaries!
            # Build context with region if available
            if region_hint:
                context_text = f"({region_hint} обл.) {city_norm}"
            else:
                context_text = text
            
            coords = ensure_city_coords_with_message_context(city_norm, context_text)
            add_debug_log(f"OpenCage lookup: '{city_name}' -> '{city_norm}' (region={region_hint}) -> {coords}", "multi_regional")
            return coords

        # Map regional header patterns to oblast names for API
        region_header_to_oblast = {
            'сумщина': 'Сумська область',
            'чернігівщина': 'Чернігівська область',
            'київщина': 'Київська область',
            'полтавщина': 'Полтавська область',
            'дніпропетровщина': 'Дніпропетровська область',
            'харківщина': 'Харківська область',
            'миколаївщина': 'Миколаївська область',
            'одещина': 'Одеська область',
            'запоріжжя': 'Запорізька область',
            'херсонщина': 'Херсонська область',
            'черкащина': 'Черкаська область',
            'вінниччина': 'Вінницька область',
            'житомирщина': 'Житомирська область',
            'рівненщина': 'Рівненська область',
            'волинь': 'Волинська область',
            'львівщина': 'Львівська область',
            'донеччина': 'Донецька область',
            'луганщина': 'Луганська область',
        }

        threats = []
        processed_cities = set()  # Избегаем дубликатов
        current_region = None  # Track current region from headers

        for line in text_lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            line_lower = line_stripped.lower()

            # CHECK FOR REGION HEADER (e.g., "Київщина:", "Харківщина:")
            # This is CRITICAL for multi-regional messages
            region_header_match = re.match(r'^([а-яіїєґ]+щина|[а-яіїєґ]+ь):?\s*$', line_lower)
            if region_header_match:
                region_name = region_header_match.group(1)
                if region_name in region_header_to_oblast:
                    current_region = region_header_to_oblast[region_name]
                    add_debug_log(f"REGION HEADER detected: '{line_stripped}' -> current_region = '{current_region}'", "multi_regional")
                continue  # Skip processing the header line itself

            # Also check for inline region header like "Сумщина: БпЛА..."
            inline_region_match = re.match(r'^([а-яіїєґ]+щина|[а-яіїєґ]+ь):\s*(.+)$', line_lower)
            if inline_region_match:
                region_name = inline_region_match.group(1)
                if region_name in region_header_to_oblast:
                    current_region = region_header_to_oblast[region_name]
                    line_stripped = inline_region_match.group(2).strip()  # Process the rest of the line
                    line_lower = line_stripped.lower()
                    add_debug_log(f"INLINE REGION HEADER: '{region_name}' -> current_region = '{current_region}', processing: '{line_stripped}'", "multi_regional")

            line_lower = line_stripped.lower()

            # PRIORITY: Handle "напрямок м.X" or "напрямок на X" pattern first
            napryamok_match = re.search(r'напрямок\s+(?:м\.|місто|на)?\s*([а-яїієґ\-]+)', line_lower)
            if napryamok_match:
                target_city = napryamok_match.group(1).strip()
                target_norm = target_city
                if target_norm.endswith('у') and len(target_norm) > 3:
                    target_norm = target_norm[:-1] + 'а'
                elif target_norm.endswith('ку') and len(target_norm) > 4:
                    target_norm = target_norm[:-2] + 'ка'
                if target_norm in UA_CITY_NORMALIZE:
                    target_norm = UA_CITY_NORMALIZE[target_norm]

                # Get coordinates using region context from headers
                target_coords = get_city_coords_quick(target_norm, current_region)

                if target_coords:
                    if len(target_coords) == 3:
                        lat, lng, approx = target_coords
                    else:
                        lat, lng = target_coords[:2]

                    # Check if not already processed
                    city_key = target_norm
                    if city_key not in processed_cities:
                        processed_cities.add(city_key)

                        uav_count = 1
                        # Try to extract UAV count from line
                        count_match = re.search(r'(\d+)\s*[xх×]?\s*бпла', line_lower)
                        if count_match:
                            uav_count = int(count_match.group(1))

                        threat_id = f"{mid}_napryamok_{len(threats)}"
                        threats.append({
                            'id': threat_id,
                            'place': target_norm.title(),
                            'lat': lat,
                            'lng': lng,
                            'threat_type': 'shahed',
                            'text': f"Напрямок → {target_norm.title()}",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': 'shahed3.webp',
                            'source_match': 'immediate_napryamok',
                            'count': uav_count
                        })

                        add_debug_log(f"Напрямок pattern: {target_norm} at {target_coords}", "napryamok")
                        continue  # Skip other processing for this line

            # Look for UAV course patterns
            if 'бпла' in line_lower and ('курс' in line_lower or ' на ' in line_lower or 'над' in line_lower or 'повз' in line_lower):
                # Extract city name from patterns - handle both plain text and markdown links
                patterns = [
                    # Pattern for markdown links: БпЛА курсом на [Бровари](link)
                    r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(?:курсом?)?\s*(?:на|над)\s+\[([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]+?)\]',
                    # Pattern for plain text: БпЛА курсом на Конотоп (improved to capture multi-word cities + districts)
                    # Fixed: Added " з " and " район" to lookahead to properly capture "Миколаїв з акваторії" and "Покровський район"
                    r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]+?(?:\s+район)?)(?=\s*(?:\n|$|[,\.\!\?;]|\s+з\s+|\s+\d+[xх×]?\s*бпла|\s+[А-ЯІЇЄЁа-яіїєё]+щина:|\s+\())',
                    # PRIORITY: Pattern for "повз ... курсом на" (e.g., "БпЛА повз Юріївку курсом на Павлоград")
                    # Must be BEFORE the simple "повз" pattern to capture both cities correctly
                    # Ignored for marker creation - handled separately below to create marker at bypass city with trajectory
                ]

                # SPECIAL HANDLING: "повз ... курсом на" pattern - create marker at bypass city with trajectory to target
                povz_course_match = re.search(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+повз\s+([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]{3,50}?)\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]{3,50}?)(?=\s*(?:\n|$|[,\.\!\?;]))', line_lower, re.IGNORECASE)
                if povz_course_match:
                    count_str, bypass_city_raw, target_city_raw = povz_course_match.groups()

                    # Normalize bypass city name
                    bypass_city = bypass_city_raw.strip()
                    bypass_norm = bypass_city.lower()
                    if bypass_norm.endswith('у') and len(bypass_norm) > 3:
                        bypass_norm = bypass_norm[:-1] + 'а'
                    elif bypass_norm.endswith('ку') and len(bypass_norm) > 4:
                        bypass_norm = bypass_norm[:-2] + 'ка'
                    if bypass_norm in UA_CITY_NORMALIZE:
                        bypass_norm = UA_CITY_NORMALIZE[bypass_norm]

                    # Normalize target city name
                    target_city = target_city_raw.strip()
                    target_norm = target_city.lower()
                    if target_norm.endswith('у') and len(target_norm) > 3:
                        target_norm = target_norm[:-1] + 'а'
                    elif target_norm.endswith('ку') and len(target_norm) > 4:
                        target_norm = target_norm[:-2] + 'ка'
                    if target_norm in UA_CITY_NORMALIZE:
                        target_norm = UA_CITY_NORMALIZE[target_norm]

                    # Get coordinates for bypass city using region context
                    bypass_coords = get_city_coords_quick(bypass_norm, current_region)

                    if bypass_coords:
                        if len(bypass_coords) == 3:
                            lat, lng, approx = bypass_coords
                        else:
                            lat, lng = bypass_coords

                        uav_count = 1
                        if count_str and count_str.isdigit():
                            uav_count = int(count_str)

                        # Create marker at bypass city with trajectory info
                        threat_id = f"{mid}_povz_course_{len(threats)}"
                        threats.append({
                            'id': threat_id,
                            'place': bypass_norm.title(),
                            'lat': lat,
                            'lng': lng,
                            'threat_type': 'shahed',
                            'text': f"Повз {bypass_norm.title()} → {target_norm.title()}",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': 'shahed3.webp',
                            'source_match': 'immediate_povz_course',
                            'count': uav_count,
                            'course_source': bypass_norm,
                            'course_target': target_norm
                        })

                        add_debug_log(f"Повз курсом на: {bypass_norm} -> {target_norm} at {bypass_coords}", "povz_course")
                        continue  # Skip normal processing for this line

                # Normal patterns (after special handling)
                patterns.append(
                    # Pattern for "повз" without "курсом на" (e.g., "БпЛА повз Славутич в бік Білорусі")
                    r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(?:.*?)?повз\s+([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]{3,50}?)(?=\s+(?:в\s+бік|до|на|через|$|[,\.\!\?;]))'
                )

                # Also check for bracket city pattern like "Вилково (Одещина)"
                bracket_matches = re.finditer(r'([А-ЯІЇЄЁа-яіїєё\'\-\s]{3,30})\s*\(([А-ЯІЇЄЁа-яіїєё\'\-\s]+щина|[А-ЯІЇЄЁа-яіїєё\'\-\s]+обл\.?)\)', line_stripped, re.IGNORECASE)
                for bmatch in bracket_matches:
                    city_clean = bmatch.group(1).strip()
                    region_info = bmatch.group(2).strip()

                    city_normalized = city_clean.lower()
                    city_key = city_normalized

                    # Skip if already processed
                    if city_key in processed_cities:
                        continue
                    processed_cities.add(city_key)

                    # Try to get coordinates using region from bracket or current_region
                    # Extract oblast from bracket (e.g., "Одещина" -> "Одеська область")
                    bracket_region = None
                    region_info_lower = region_info.lower()
                    if region_info_lower in region_header_to_oblast:
                        bracket_region = region_header_to_oblast[region_info_lower]
                    elif region_info_lower.replace('щина', 'щина') in region_header_to_oblast:
                        bracket_region = region_header_to_oblast.get(region_info_lower)

                    coords = get_city_coords_quick(city_clean, bracket_region or current_region)

                    if coords:
                        if len(coords) == 3:
                            lat, lng, approx = coords
                        else:
                            lat, lng = coords

                        threat_id = f"{mid}_imm_bracket_{len(threats)}"
                        threats.append({
                            'id': threat_id,
                            'place': city_clean.title(),
                            'lat': lat,
                            'lng': lng,
                            'threat_type': 'shahed',
                            'text': f"{line_stripped} (bracket city)",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': 'shahed3.webp',
                            'source_match': 'immediate_multi_regional_bracket',
                            'count': 1
                        })

                        add_debug_log(f"Immediate Multi-regional bracket: {city_clean} -> {coords}", "multi_regional")
                    else:
                        add_debug_log(f"Immediate Multi-regional bracket: No coords for {city_clean}", "multi_regional")

                for pattern in patterns:
                    matches = re.finditer(pattern, line_stripped, re.IGNORECASE)
                    for match in matches:
                        if len(match.groups()) == 2:
                            count_str, city_raw = match.groups()
                        else:
                            count_str = None
                            city_raw = match.group(1)

                        if not city_raw:
                            continue

                        # Clean city name (remove trailing spaces)
                        city_clean = city_raw.strip()

                        # Normalize city name for coordinate lookup
                        city_normalized = city_clean.lower()

                        # Normalize for display (convert accusative to nominative)
                        city_display = city_clean
                        if city_normalized == 'велику димерку':
                            city_display = 'Велика Димерка'
                        elif city_normalized == 'велику виску':
                            city_display = 'Велика Виска'
                        elif city_normalized == 'мену':
                            city_display = 'Мена'
                        elif city_normalized == 'пісківку':
                            city_display = 'Пісківка'
                        elif city_normalized == 'києвом':
                            city_display = 'Київ'
                            city_normalized = 'київ'  # Also normalize for lookup
                        elif city_normalized.endswith('ом') and len(city_normalized) > 4:
                            # Handle other accusative masculine endings
                            city_display = city_normalized[:-2]
                            city_display = city_display.title()
                            city_normalized = city_normalized[:-2]
                        elif city_normalized.endswith('у') and len(city_normalized) > 3:
                            city_display = city_normalized[:-1] + 'а'
                            city_display = city_display.title()
                        elif city_normalized.endswith('ю') and len(city_normalized) > 3:
                            city_display = city_normalized[:-1] + 'я'
                            city_display = city_display.title()
                        elif city_normalized.endswith('ку') and len(city_normalized) > 4:
                            city_display = city_normalized[:-2] + 'ка'
                            city_display = city_display.title()
                        else:
                            city_display = city_clean.title()

                        city_key = city_normalized

                        # Skip if already processed
                        if city_key in processed_cities:
                            continue
                        processed_cities.add(city_key)

                        # Try to get coordinates using current region context
                        coords = get_city_coords_quick(city_clean, current_region)

                        if coords:
                            if len(coords) == 3:
                                lat, lng, approx = coords
                            else:
                                lat, lng = coords

                            # Extract count if present
                            uav_count_num = 1
                            if count_str and count_str.isdigit():
                                uav_count_num = int(count_str)

                            # Create multiple tracks for multiple drones
                            tracks_to_create = max(1, uav_count_num)
                            for i in range(tracks_to_create):
                                track_display_name = city_display
                                if tracks_to_create > 1:
                                    track_display_name += f" #{i+1}"

                                # Add small coordinate offsets to prevent marker overlap
                                marker_lat = lat
                                marker_lng = lng
                                if tracks_to_create > 1:
                                    # Create a chain pattern - drones one after another
                                    offset_distance = 0.03  # ~3km offset between each drone
                                    marker_lat += offset_distance * i
                                    marker_lng += offset_distance * i * 0.5

                                threat_id = f"{mid}_imm_multi_{len(threats)}"
                                threats.append({
                                    'id': threat_id,
                                    'place': track_display_name,  # Use numbered display name for multiple drones
                                    'lat': marker_lat,
                                    'lng': marker_lng,
                                    'threat_type': 'shahed',
                                    'text': f"{line_stripped} (мультирегіональне)",
                                    'date': date_str,
                                    'channel': channel,
                                    'marker_icon': 'shahed3.webp',
                                    'source_match': f'immediate_multi_regional_uav_{uav_count_num}x',
                                    'count': 1  # Each track represents 1 drone
                                })

                            add_debug_log(f"Immediate Multi-regional: {city_clean} ({uav_count_num}x) -> {tracks_to_create} tracks at {coords}", "multi_regional")
                        else:
                            add_debug_log(f"Immediate Multi-regional: No coords for {city_clean}", "multi_regional")

        # Also check for regional UAV references without specific cities
        for line in text_lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            line_lower = line_stripped.lower()

            # Look for UAV + region patterns without specific cities
            if 'бпла' in line_lower and any(region in line_lower for region in ['щини', 'щину', 'одещина', 'чернігівщина', 'дніпропетровщини']):
                # Skip if this specific line contains a city that was already processed
                line_has_processed_city = False
                for city in processed_cities:
                    if city in line_lower:
                        line_has_processed_city = True
                        break

                if line_has_processed_city:
                    continue

                # Special case: movement messages with direction in parentheses
                # Pattern: "БпЛА на півдні Чернігівщини, рухаються на південь (Київщина)"
                # Here (Київщина) indicates direction, not location
                directional_movement = re.search(r'на\s+([\w\-\s/]+?)\s+([а-яіїєґ]+щини|[а-яіїєґ]+щину|дніпропетровщини|одещини|чернігівщини).*рухаються.*\(([^)]+)\)', line_lower)
                if directional_movement:
                    direction = directional_movement.group(1).strip()
                    region_raw = directional_movement.group(2).strip()
                    target_direction = directional_movement.group(3).strip()

                    # Map region to oblast center (current location, not target)
                    region_coords = None
                    if 'дніпропетров' in region_raw:
                        region_coords = (48.45, 35.0)
                        region_name = 'Дніпропетровщини'
                    elif 'чернігів' in region_raw:
                        region_coords = (51.4982, 31.3044)
                        region_name = 'Чернігівщини'
                    elif 'одес' in region_raw:
                        region_coords = (46.5197, 30.7495)
                        region_name = 'Одещини'

                    if region_coords:
                        # Apply directional offset for current location
                        lat, lng = region_coords
                        if 'півдн' in direction or 'южн' in direction:
                            lat -= 0.5
                        elif 'північ' in direction or 'север' in direction:
                            lat += 0.5
                        elif 'захід' in direction or 'запад' in direction:
                            lng -= 0.8
                        elif 'схід' in direction or 'восток' in direction:
                            lng += 0.8

                        direction_label = direction.replace('півдн', 'південн').replace('північ', 'північн')
                        place_name = f"{region_name} ({direction_label}а частина) → {target_direction}"

                        threat_id = f"{mid}_imm_regional_movement_{len(threats)}"
                        threats.append({
                            'id': threat_id,
                            'place': place_name,
                            'lat': lat,
                            'lng': lng,
                            'threat_type': 'shahed',
                            'text': f"{line_stripped} (рух у напрямку {target_direction})",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': 'shahed3.webp',
                            'source_match': 'immediate_multi_regional_movement',
                            'count': 1,
                            'movement_target': target_direction
                        })

                        add_debug_log(f"Immediate Multi-regional movement: {place_name} -> {lat}, {lng} (target: {target_direction})", "multi_regional")
                        continue

                # Check if this is a directional reference like "на півдні Дніпропетровщини"
                region_match = re.search(r'на\s+([\w\-\s/]+?)\s+([а-яіїєґ]+щини|[а-яіїєґ]+щину|дніпропетровщини|одещини|чернігівщини)', line_lower)
                if region_match:
                    direction = region_match.group(1).strip()
                    region_raw = region_match.group(2).strip()

                    # Map region to oblast center
                    region_coords = None
                    if 'дніпропетров' in region_raw:
                        region_coords = (48.45, 35.0)
                        region_name = 'Дніпропетровщини'
                    elif 'чернігів' in region_raw:
                        region_coords = (51.4982, 31.3044)
                        region_name = 'Чернігівщини'
                    elif 'одес' in region_raw:
                        region_coords = (46.5197, 30.7495)
                        region_name = 'Одещини'

                    if region_coords:
                        # Apply directional offset
                        lat, lng = region_coords
                        if 'півдн' in direction or 'южн' in direction:
                            lat -= 0.5
                        elif 'північ' in direction or 'север' in direction:
                            lat += 0.5
                        elif 'захід' in direction or 'запад' in direction:
                            lng -= 0.8
                        elif 'схід' in direction or 'восток' in direction:
                            lng += 0.8

                        direction_label = direction.replace('півдн', 'південн').replace('північ', 'північн')
                        place_name = f"{region_name} ({direction_label}а частина)"

                        threat_id = f"{mid}_imm_regional_{len(threats)}"
                        threats.append({
                            'id': threat_id,
                            'place': place_name,
                            'lat': lat,
                            'lng': lng,
                            'threat_type': 'shahed',
                            'text': f"{line_stripped} (регіональний)",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': 'shahed3.webp',
                            'source_match': 'immediate_multi_regional_region',
                            'count': 1
                        })

                        add_debug_log(f"Immediate Multi-regional regional: {place_name} -> {lat}, {lng}", "multi_regional")

        if threats:
            add_debug_log(f"IMMEDIATE MULTI-REGIONAL RESULT: {len(threats)} threats", "multi_regional")
            return threats

    if 'повітряна тривога' in low_orig or 'тривога' in low_orig or 'тривог' in low_orig:
        # Always event-only record (list), never create map markers for air alarms or cancellations
        place = None
        low = low_orig.lower()
        # Try to extract oblast/region info for place
        for name in ['запорізька', 'одеська', 'миколаївська', 'херсонська', 'київська', 'львівська', 'харківська', 'дніпропетровська', 'чернігівська', 'сумська', 'полтавська', 'тернопільська', 'волинська', 'рівненська', 'житомирська', 'вінницька', 'закарпатська', 'івано-франківська', 'кіровоградська', 'черкаська', 'хмельницька', 'луганська', 'донецька']:
            if name in low:
                place = name.title() + ' Обл.'
                break

        # Also try to find city names
        if not place:
            for city in ['запоріжжя', 'одеса', 'миколаїв', 'херсон', 'київ', 'львів', 'харків', 'дніпро', 'чернігів', 'суми', 'полтава']:
                if city in low:
                    place = city.title()
                    break

        # Determine if this is alarm start or cancellation
        threat_type = 'alarm_cancel' if ('відбій' in low_orig or 'отбой' in low_orig) else 'alarm'
        icon = 'vidboi.png' if threat_type == 'alarm_cancel' else 'trivoga.png'

        # Clean subscription links from air alarm messages before returning
        import re as re_import
        cleaned_text = original_text
        if original_text:
            # remove lines containing subscription prompts
            cleaned = []
            for ln in original_text.splitlines():
                ln2 = ln.strip()
                if not ln2:
                    continue
                # remove any line that is just a subscribe CTA or starts with arrow+subscribe
                if re_import.search(r'(підписатись|підписатися|підписатися|подписаться|подпишись|subscribe)', ln2, re_import.IGNORECASE):
                    continue
                # remove arrow+subscribe pattern specifically
                if re_import.search(r'[➡→>]\s*підписатися', ln2, re_import.IGNORECASE):
                    continue
                cleaned.append(ln2)
            cleaned_text = '\n'.join(cleaned)

        return [{
            'id': str(mid), 'place': place, 'lat': None, 'lng': None,
            'threat_type': threat_type, 'text': cleaned_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': icon, 'list_only': True
        }]

    # Define classify function at the start so it's available throughout process_message
    def classify(th: str, city_context: str = ""):
        import re  # Import re module locally for pattern matching
        l = th.lower()

        # Add debug logging (temporarily disabled)
        # print(f"[CLASSIFY DEBUG] Input text: {th}")
        # print(f"[CLASSIFY DEBUG] Lowercase text: {l}")
        # print(f"[CLASSIFY DEBUG] City context: {city_context}")
        # print(f"[CLASSIFY DEBUG] Contains 🚀: {'🚀' in th}")
        # print(f"[CLASSIFY DEBUG] Contains 'ціль': {'ціль' in l}")
        # print(f"[CLASSIFY DEBUG] Contains 'високошвидкісн': {'високошвидкісн' in l}")
        # print(f"[CLASSIFY DEBUG] Contains 'бпла': {'бпла' in l}")

        # PRIORITY: Artillery shelling warning (обстріл / загроза обстрілу) -> use obstril.png
        # This should have priority over FPV cities when explicit shelling threat is mentioned
        if 'обстріл' in l or 'обстрел' in l or 'загроза обстрілу' in l or 'угроза обстрела' in l:
            # print(f"[CLASSIFY DEBUG] Classified as artillery")
            return 'artillery', 'obstril.png'

        # Special override for specific cities - Kherson, Nikopol, Marhanets always get FPV icon
        city_lower = city_context.lower() if city_context else ""
        fpv_cities = ['херсон', 'никополь', 'нікополь', 'марганець', 'марганец']

        # Check both city context and message text for FPV cities
        if any(fpv_city in city_lower for fpv_city in fpv_cities) or any(fpv_city in l for fpv_city in fpv_cities):
            return 'fpv', 'fpv.png'
        # Recon / розвід дрони -> use pvo icon (rozvedka2.png) per user request - PRIORITY: check BEFORE general БПЛА
        if 'розвід' in l or 'розвідуваль' in l or 'развед' in l:
            return 'rozved', 'rozvedka2.png'
        # PRIORITY: КАБы (управляемые авиационные бомбы) -> icon_missile.svg - check BEFORE пуски to avoid misclassification
        if any(k in l for k in ['каб','kab','умпк','umpk','модуль','fab','умпб','фаб','кабу']) or \
           ('авіаційн' in l and 'бомб' in l) or ('керован' in l and 'бомб' in l):
            return 'kab', 'icon_missile.svg'
        # Launch site detections for explicit "Пуск ... (РФ)" style messages
        # Examples: "Пуск Приморськ-Ахтарська (РФ)", "Пуск Халино (РФ)", "Пуск Орел-Південний (РФ)", "Пуск Курська (РФ)"
        launch_locations = [
            'приморськ-ахтарськ', 'приморськ-ахтарська', 'приморсько-ахтарськ', 'приморсько-ахтарська',
            'приморск-ахтарск', 'приморск-ахтарская', 'приморско-ахтарск', 'приморско-ахтарская',
            'халино', 'орел-південний', 'орел-южный', 'курськ', 'курська', 'курск', 'курской', 'курскую'
        ]
        if ('пуск' in l or 'пуски' in l) and (('рф' in l) or any(loc in l for loc in launch_locations)):
            return 'pusk', 'pusk.png'
        # Launch site detections for Shahed / UAV launches ("пуски" + origin phrases). User wants pusk.png marker.
        # Exclude КАБ launches - they should be classified as КАБ, not пуски
        if ('пуск' in l or 'пуски' in l) and (any(k in l for k in ['shahed','шахед','шахеді','шахедів','бпла','uav','дрон']) or ('аеродром' in l) or ('аэродром' in l)) and not any(k in l for k in ['каб','kab','умпк','fab','фаб']):
            return 'pusk', 'pusk.png'
        # Explicit launches from occupied Berdyansk airbase (Запорізька область) should also show as pusk (not avia)
        if ('пуск' in l or 'пуски' in l) and 'бердян' in l and ('авіабаз' in l or 'аеродром' in l or 'авиабаз' in l):
            return 'pusk', 'pusk.png'
        # Air alarm start
        if ('повітряна тривога' in l or 'повітряна тривога.' in l or ('тривога' in l and 'повітр' in l)) and not ('відбій' in l or 'отбой' in l):
            return 'alarm', 'trivoga.png'
        # Air alarm cancellation
        if ('відбій тривоги' in l) or ('отбой тревоги' in l):
            return 'alarm_cancel', 'vidboi.png'
        # Explosions reporting -> vibuh icon (cover broader fixation phrases)
        if ('повідомляють про вибух' in l or 'повідомлено про вибух' in l or 'зафіксовано вибух' in l or 'зафіксовано вибухи' in l
            or 'фіксація вибух' in l or 'фіксують вибух' in l or re.search(r'\b(вибух|вибухи|вибухів)\b', l)):
            return 'vibuh', 'vibuh.png'
        # Alarm cancellation (відбій тривоги / отбой тревоги)
        if ('відбій' in l and 'тривог' in l) or ('отбой' in l and 'тревог' in l):
            print("[CLASSIFY DEBUG] Classified as alarm_cancel")
            return 'alarm_cancel', 'vidboi.png'

        # PRIORITY: High-speed targets / missile threats with rocket emoji (🚀) -> icon_balistic.svg
        # This should have priority over drones to handle missile-like threats with rocket emoji
        if '🚀' in th or any(k in l for k in ['ціль','цілей','цілі','високошвидкісн','high-speed']):
            print("[CLASSIFY DEBUG] Classified as raketa (high-speed targets/rocket emoji)")
            return 'raketa', 'icon_balistic.svg'

        # PRIORITY: drones (частая путаница). Если присутствуют слова шахед/бпла/дрон -> это shahed
        if any(k in l for k in ['shahed','шахед','шахеді','шахедів','geran','герань','дрон','дрони','бпла','uav']):
            print("[CLASSIFY DEBUG] Classified as shahed (drones/UAV)")
            return 'shahed', 'shahed3.webp'
        # PRIORITY: Aircraft activity & tactical aviation (avia) -> avia.png (jets, tactical aviation, но БЕЗ КАБов)
        if any(k in l for k in ['літак','самол','avia','tactical','тактичн','fighter','истребит','jets']) or \
           ('авіаційн' in l and ('засоб' in l or 'ураж' in l)):
            return 'avia', 'avia.png'
        # Rocket / missile attacks (ракета, ракети) -> icon_balistic.svg
        if any(k in l for k in ['ракет','rocket','міжконтинент','межконтинент','балістичн','крилат','cruise']):
            return 'raketa', 'icon_balistic.svg'
        # РСЗВ (MLRS, град, ураган, смерч) -> icon_missile.svg
        if any(k in l for k in ['рсзв','mlrs','град','ураган','смерч','рсув','tор','tорнадо','торнадо']):
            return 'rszv', 'icon_missile.svg'
        # Korabel (naval/ship-related threats) -> use icon_balistic.svg as fallback
        if any(k in l for k in ['корабел','флот','корабл','ship','fleet','морськ','naval']):
            return 'raketa', 'icon_balistic.svg'
        # Artillery
        if any(k in l for k in ['арт','artillery','гармат','гаубиц','минометн','howitzer']):
            return 'artillery', 'artillery.png'
        # PVO (air defense activity) -> use vidboi.png as fallback
        if any(k in l for k in ['ппо','pvo','defense','оборон','зенітн','с-','patriot']):
            return 'vidboi', 'vidboi.png'
        # Naval mines -> use icon_balistic.svg as fallback
        if any(k in l for k in ['міна','мін ','mine','neptun','нептун','противокорабел']):
            return 'raketa', 'icon_balistic.svg'
        # FPV drones -> fpv.png
        if any(k in l for k in ['fpv','фпв','камікадз','kamikaze']):
            print("[CLASSIFY DEBUG] Classified as fpv")
            return 'fpv', 'fpv.png'

        # General fallback for unclassified threats
        print("[CLASSIFY DEBUG] Using default fallback: shahed")
        return 'shahed', 'shahed3.webp'  # default fallback

    # PRIORITY CHECK: District-level UAV messages (e.g., "вишгородський р-н київська обл.")
    # Added after classify function to ensure it's available
    lower_text = original_text.lower()
    district_pattern = re.compile(r'([а-яіїєґ\'\-\s]+ський|[а-яіїєґ\'\-\s]+цький)\s+р[-\s]*н\s+([а-яіїєґ\'\-\s]+(?:обл\.?|область|щина))', re.IGNORECASE)
    district_match = district_pattern.search(lower_text)

    if district_match and 'бпла' in lower_text:
        district_raw = district_match.group(1).strip()
        region_raw = district_match.group(2).strip()

        add_debug_log(f"DISTRICT UAV: found '{district_raw} р-н {region_raw}'", "district_uav")

        # Try to map district to city coordinates
        district_city = district_raw.replace('ський', '').replace('цький', '').strip()

        # Check if we have coordinates for this district city
        coords = CITY_COORDS.get(district_city)
        if not coords and district_city in UA_CITY_NORMALIZE:
            coords = CITY_COORDS.get(UA_CITY_NORMALIZE[district_city])

        if coords:
            lat, lng = coords
            threat_type, icon = classify(original_text, district_city)

            # Create district-level marker
            district_track = {
                'id': f"{mid}_district",
                'place': f"{district_city.title()} ({district_raw} р-н)",
                'lat': lat,
                'lng': lng,
                'threat_type': threat_type,
                'text': original_text[:500],
                'date': date_str,
                'channel': channel,
                'marker_icon': icon,
                'source_match': 'district_priority_uav',
                'count': 1
            }

            add_debug_log(f"DISTRICT UAV SUCCESS: {district_city} -> {coords}", "district_uav")
            return [district_track]
        else:
            add_debug_log(f"DISTRICT UAV: No coords for '{district_city}'", "district_uav")

    # PRIORITY CHECK: Single-region numbered UAV lists (н.п. patterns)
    # For messages like "Київщина:\n• н.п. Бровари - постійна загроза БпЛА"
    lower_text = original_text.lower()
    text_lines = original_text.split('\n')

    # Check if this is a single-region message with numbered н.п. cities
    region_lines = [line for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:']) and line.strip().endswith(':')]
    np_lines = [line for line in text_lines if ('н.п.' in line.lower() or 'н. п.' in line.lower()) and 'бпла' in line.lower()]

    if len(region_lines) == 1 and len(np_lines) >= 1:  # Single region with н.п. cities
        region_line = region_lines[0]
        region_name = region_line.replace(':', '').strip()

        add_debug_log(f"SINGLE-REGION NUMBERED: found {len(np_lines)} н.п. cities in {region_name}", "single_region_numbered")

        numbered_tracks = []
        for i, line in enumerate(np_lines):
            # Extract city name from н.п. pattern
            np_match = re.search(r'н\.?\s*п\.?\s+([а-яіїєґ\'\-\s]+)', line.lower())
            if np_match:
                city_name_raw = np_match.group(1).strip()
                # Clean up - take only the city name before any separators
                city_name = city_name_raw.split(' - ')[0].split(' –')[0].split(' ')[0].strip()

                # Try to find coordinates for this city
                coords = CITY_COORDS.get(city_name)
                if not coords and city_name in UA_CITY_NORMALIZE:
                    coords = CITY_COORDS.get(UA_CITY_NORMALIZE[city_name])

                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(line, city_name)

                    numbered_tracks.append({
                        'id': f"{mid}_np_{i+1}",
                        'place': f"{city_name.title()} ({region_name})",
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': line[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': 'single_region_numbered_np',
                        'count': 1
                    })
                    add_debug_log(f"NUMBERED UAV SUCCESS: {city_name} -> {coords}", "single_region_numbered")
                else:
                    # Fallback to region coordinates if city not found
                    region_key = region_name.lower().replace('щина', '').replace('область', '').strip()
                    region_coords = CITY_COORDS.get(region_key)
                    if region_coords:
                        lat, lng = region_coords
                        threat_type, icon = classify(line)

                        numbered_tracks.append({
                            'id': f"{mid}_np_fallback_{i+1}",
                            'place': f"{region_name} (н.п. {city_name.title()})",
                            'lat': lat,
                            'lng': lng,
                            'threat_type': threat_type,
                            'text': line[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'single_region_numbered_np_fallback',
                            'count': 1
                        })
                        add_debug_log(f"NUMBERED UAV FALLBACK: {city_name} -> {region_name} {region_coords}", "single_region_numbered")

        if numbered_tracks:
            add_debug_log(f"SINGLE-REGION NUMBERED SUCCESS: {len(numbered_tracks)} markers created", "single_region_numbered")
            return numbered_tracks

    # HIGHEST PRIORITY: Check for region-district patterns immediately
    import re as _re_priority
    region_district_pattern = _re_priority.compile(r'([а-яіїєґ]+щин[ауи]?)\s*\(\s*([а-яіїєґ\'\-\s]+)\s+р[-\s]*н\)', _re_priority.IGNORECASE)
    region_district_match = region_district_pattern.search(original_text)

    if region_district_match:
        region_raw, district_raw = region_district_match.groups()
        target_city = district_raw.strip()

        add_debug_log(f"PRIORITY REGION-DISTRICT pattern FOUND: region='{region_raw}', district='{district_raw}'", "priority_region_district")

        # Normalize city name and try to find coordinates via API
        city_norm = target_city.lower()
        # Apply UA_CITY_NORMALIZE rules if available
        if 'UA_CITY_NORMALIZE' in globals():
            city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)

        # Use API geocoding with message context
        coords_result = ensure_city_coords_with_message_context(city_norm, original_text)
        coords = (coords_result[0], coords_result[1]) if coords_result else None

        add_debug_log(f"Priority district city API lookup: '{target_city}' -> '{city_norm}' -> {coords}", "priority_region_district")

        if coords:
            lat, lng = coords
            threat_type, icon = classify(original_text)

            priority_result = [{
                'id': f"{mid}_priority_district",
                'place': target_city.title(),
                'lat': lat,
                'lng': lng,
                'threat_type': threat_type,
                'text': original_text[:500],
                'date': date_str,
                'channel': channel,
                'marker_icon': icon,
                'source_match': 'priority_region_district',
                'count': 1
            }]
            add_debug_log(f"Created PRIORITY region-district marker: {target_city.title()}", "priority_region_district")

            # Store priority result globally for combination with other results
            globals()['_current_priority_result'] = priority_result

            # Store priority result and continue with normal processing to catch other cities
            # This allows other parsers to find additional cities in the same message
        else:
            add_debug_log(f"No coordinates found for priority district city: '{target_city}' (normalized: '{city_norm}')", "priority_region_district")
            priority_result = None
    else:
        priority_result = None

    # ВСЕГДА логируем каждое входящее сообщение для отладки
    try:
        add_debug_log(f"process_message called - mid={mid}, channel={channel}, text_length={len(text or '')}", "message_processing")
        add_debug_log(f"message text preview: {(text or '')[:200]}...", "message_processing")
        # Check if this is our test message
        if 'чернігівщина' in (text or '').lower() and 'сумщина' in (text or '').lower():
            add_debug_log("MULTI-REGION MESSAGE DETECTED!", "multi_region")
            add_debug_log(f"Full text: {text}", "multi_region")
    except Exception:
        pass

    # PRIORITY: Handle emoji + city + oblast format BEFORE any other processing
    try:
        import re  # Import re module for pattern matching
        head = text.split('\n', 1)[0][:160] if text else ""

        # Handle general emoji + city + oblast format with any UAV threat (more flexible pattern)
        general_emoji_pattern = r'^[^\w\s]*\s*([А-ЯІЇЄЁа-яіїєё\'\-\s]+)\s*\(([^)]*обл[^)]*)\)'
        general_emoji_match = re.search(general_emoji_pattern, head, re.IGNORECASE)
        add_debug_log(f"PRIORITY: Testing general emoji pattern on head: {repr(head)}", "emoji_debug")
        add_debug_log(f"PRIORITY: General emoji match result: {general_emoji_match}", "emoji_debug")

        if general_emoji_match and any(uav_word in text.lower() for uav_word in ['бпла', 'дрон', 'шахед', 'активність', 'загроза', 'тривога', 'обстріл', 'обстрел']):
            city_from_general = general_emoji_match.group(1).strip()
            oblast_from_general = general_emoji_match.group(2).strip()

            # Strip UAV-related prefixes from city name (БПЛА, дрон, шахед, etc.)
            uav_prefixes = ['бпла', 'дрон', 'дрони', 'шахед', 'шахеди', 'безпілотник', 'безпілотники', 'ворожий', 'ворожі']
            city_lower = city_from_general.lower()
            for prefix in uav_prefixes:
                if city_lower.startswith(prefix + ' '):
                    city_from_general = city_from_general[len(prefix):].strip()
                    city_lower = city_from_general.lower()
                    add_debug_log(f"PRIORITY: Stripped UAV prefix '{prefix}', city now: {repr(city_from_general)}", "emoji_debug")

            # Strip course/direction suffixes from city name
            city_from_general = re.sub(r'\s+(курсом|курс|напрям(?:ком)?|в\s+напрямку|у\s+напрямку)\s+.+$', '', city_from_general, flags=re.IGNORECASE).strip()

            add_debug_log(f"PRIORITY: Found city: {repr(city_from_general)}, oblast: {repr(oblast_from_general)}", "emoji_debug")

            if city_from_general and 2 <= len(city_from_general) <= 40:
                base = city_from_general.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                base = re.sub(r'\s+',' ', base)
                norm = UA_CITY_NORMALIZE.get(base, base)

                # Extract region name from oblast string for OpenCage
                oblast_key = oblast_from_general.lower()
                region_for_geocode = oblast_key.replace(' обл.', '').replace(' обл', '').replace('область', '').strip()
                
                # ONLY OpenCage API - no local dictionaries!
                # Build context with explicit oblast
                context_text = f"{city_from_general} ({oblast_from_general})"
                coords = ensure_city_coords_with_message_context(norm, context_text)
                add_debug_log(f"PRIORITY: OpenCage lookup: city={repr(norm)}, region={repr(region_for_geocode)}, coords={coords}", "emoji_debug")

                if coords:
                    lat, lon = coords[:2]

                    # Check for threat cancellation BEFORE creating marker
                    text_lower = text.lower()
                    if ('відбій загрози' in text_lower or
                        'відбій тривоги' in text_lower or
                        ('відбій' in text_lower and any(cancel_word in text_lower for cancel_word in ['загрози', 'тривоги']))):
                        # This is a cancellation message - create list_only entry, no map marker
                        track = {
                            'id': f"{mid}_priority_emoji_cancel_{city_from_general.replace(' ','_')}",
                            'place': city_from_general.title(),
                            'threat_type': 'alarm_cancel',
                            'text': clean_text(text)[:500],
                            'date': date_str,
                            'channel': channel,
                            'list_only': True,  # NO map marker for cancellation
                            'source_match': 'priority_emoji_cancel'
                        }
                        add_debug_log(f'PRIORITY CANCELLATION: {city_from_general} -> list_only=True (no marker)', "emoji_debug")
                        return [track]  # Early return - cancellation handled

                    # Regular threat - create map marker
                    threat_type, icon = classify(text, city_from_general)
                    track = {
                        'id': f"{mid}_priority_emoji_{city_from_general.replace(' ','_')}",
                        'place': city_from_general.title(),
                        'lat': lat, 'lng': lon,
                        'threat_type': threat_type,
                        'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'priority_emoji_threat'
                    }
                    add_debug_log(f'PRIORITY EARLY RETURN: {city_from_general} -> {coords} -> {icon}', "emoji_debug")
                    return [track]  # Early return - highest priority
                else:
                    # NO COORDS FOUND - create list_only entry for push notifications but no map marker
                    threat_type, icon = classify(text, city_from_general)
                    track = {
                        'id': f"{mid}_priority_emoji_nocoords_{city_from_general.replace(' ','_')}",
                        'place': city_from_general.title(),
                        'threat_type': threat_type,
                        'text': clean_text(text)[:500],
                        'date': date_str,
                        'channel': channel,
                        'list_only': True,  # NO map marker - coords not found
                        'source_match': 'priority_emoji_no_coords'
                    }
                    add_debug_log(f'PRIORITY NO COORDS: {city_from_general} -> list_only=True (push will be sent)', "emoji_debug")
                    return [track]
    except Exception as e:
        add_debug_log(f"PRIORITY emoji processing error: {e}", "emoji_debug")

    # PRIORITY: Handle emoji + oblast format (when only oblast is specified, place marker in regional center)
    try:
        import re  # Import re module for pattern matching
        head = text.split('\n', 1)[0][:160] if text else ""

        # Handle emoji + oblast format (e.g. "👁️ Миколаївська обл.")
        oblast_emoji_pattern = r'^[^\w\s]*\s*([А-ЯІЇЄЁа-яіїєё\'\-\s]*обл\.?)\s*\*\*'
        oblast_emoji_match = re.search(oblast_emoji_pattern, head, re.IGNORECASE)
        add_debug_log(f"PRIORITY: Testing oblast emoji pattern on head: {repr(head)}", "emoji_debug")
        add_debug_log(f"PRIORITY: Oblast emoji match result: {oblast_emoji_match}", "emoji_debug")

        if oblast_emoji_match and any(uav_word in text.lower() for uav_word in ['бпла', 'дрон', 'шахед', 'активність', 'загроза', 'тривога']):
            oblast_from_emoji = oblast_emoji_match.group(1).strip()
            add_debug_log(f"PRIORITY: Found oblast from emoji: {repr(oblast_from_emoji)}", "emoji_debug")

            # Map oblast to regional center
            regional_center = None
            coords = None

            oblast_key = oblast_from_emoji.lower()
            if 'миколаївськ' in oblast_key:
                regional_center = 'Миколаїв'
                coords = CITY_COORDS.get('миколаїв')
            elif 'дніпропетровськ' in oblast_key:
                regional_center = 'Дніпро'
                coords = CITY_COORDS.get('дніпро')
            elif 'харківськ' in oblast_key:
                regional_center = 'Харків'
                coords = CITY_COORDS.get('харків')
            elif 'сумськ' in oblast_key:
                regional_center = 'Суми'
                coords = CITY_COORDS.get('суми')
            elif 'херсонськ' in oblast_key:
                regional_center = 'Херсон'
                coords = CITY_COORDS.get('херсон')
            elif 'одеськ' in oblast_key:
                regional_center = 'Одеса'
                coords = CITY_COORDS.get('одеса')
            elif 'запорізьк' in oblast_key:
                regional_center = 'Запоріжжя'
                coords = CITY_COORDS.get('запоріжжя')
            elif 'полтавськ' in oblast_key:
                regional_center = 'Полтава'
                coords = CITY_COORDS.get('полтава')

            add_debug_log(f"PRIORITY: Oblast {oblast_from_emoji} -> regional center {regional_center} -> coords {coords}", "emoji_debug")

            if coords and regional_center:
                lat, lon = coords[:2]
                threat_type, icon = classify(text)
                track = {
                    'id': f"{mid}_priority_oblast_{regional_center.replace(' ','_')}",
                    'place': regional_center,
                    'lat': lat, 'lng': lon,
                    'threat_type': threat_type,
                    'text': text[:160], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'priority_oblast_threat'
                }
                add_debug_log(f'PRIORITY OBLAST EARLY RETURN: {oblast_from_emoji} -> {regional_center} -> {coords} -> {icon}', "emoji_debug")
                return [track]  # Early return - highest priority
    except Exception as e:
        add_debug_log(f"PRIORITY oblast processing error: {e}", "emoji_debug")

    # Continue with existing logic...

    # Strip embedded links (Markdown [text](url) or raw URLs) while keeping core message text.
    # Requested: if message contains links, remove them but keep the rest.
    try:
        import re as _re_strip  # type: ignore
        if text:
            _orig_text = text
            # Remove markdown links [ ... ](http...). Keep the visible text (group 1) only.
            text = _re_strip.sub(r"\[([^\]]*)\]\((?:https?|tg|mailto)://[^)]+\)", lambda m: (m.group(1) or '').strip(), text)
            # Remove any residual raw URLs (http/https/t.me) leaving a single space
            text = _re_strip.sub(r"https?://\S+", " ", text)
            text = _re_strip.sub(r"t\.me/\S+", " ", text)
            # Remove lone decorative symbols (✙, •, ★) that may have surrounded links
            text = _re_strip.sub(r"[✙•★]{1,}", " ", text)
            # Collapse multiple spaces and trim each line
            cleaned_lines = []
            for _ln in text.splitlines():
                _cl = ' '.join(_ln.split())
                if _cl:
                    cleaned_lines.append(_cl)
            if cleaned_lines:
                text = '\n'.join(cleaned_lines)
            else:
                # If stripping removed everything, fall back to original
                text = _orig_text
    except Exception:
        pass
    # Ensure original_text is defined early to avoid UnboundLocalError in early parsing branches
    original_text = text

    # Special handling for oblast+raion format: "чернігівська область (чернігівський район), київська область (вишгородський район)"
    import re as _re_oblast
    oblast_raion_pattern = r'([а-яіїєґ]+ська\s+область)\s*\(([^)]*?райони?[^)]*?)\)'
    oblast_raion_matches = _re_oblast.findall(oblast_raion_pattern, text.lower(), _re_oblast.IGNORECASE)

    # Also check for pattern without requiring "райони" in parentheses - some messages might have just names
    if not oblast_raion_matches:
        oblast_raion_pattern_simple = r'([а-яіїєґ]+ська\s+область)\s*\(([^)]+)\)'
        oblast_raion_matches_simple = _re_oblast.findall(oblast_raion_pattern_simple, text.lower(), _re_oblast.IGNORECASE)
        # Filter to only those that contain district-like words
        oblast_raion_matches = [(oblast, raion) for oblast, raion in oblast_raion_matches_simple
                               if any(word in raion for word in ['район', 'р-н', 'ський', 'цький'])]

    add_debug_log(f"Oblast+raion pattern check: found {len(oblast_raion_matches)} matches in text: {text[:200]}...", "oblast_raion")

    if oblast_raion_matches and any(word in text.lower() for word in ['бпла', 'загроза', 'укриття']):
        add_debug_log(f"Oblast+raion format detected: {oblast_raion_matches}", "oblast_raion")
        tracks = []

        for oblast_text, raion_text in oblast_raion_matches:
            add_debug_log(f"Processing oblast: '{oblast_text}', raion_text: '{raion_text}'", "oblast_raion")
            # Extract individual raions from the parentheses
            # Handle both single and multiple raions: "сумський, конотопський райони"
            raion_parts = _re_oblast.split(r',\s*|\s+та\s+', raion_text)
            add_debug_log(f"Split raion_parts: {raion_parts}", "oblast_raion")

            for raion_part in raion_parts:
                raion_part = raion_part.strip()
                if not raion_part:
                    continue

                add_debug_log(f"Processing raion_part: '{raion_part}'", "oblast_raion")

                # Extract raion name (remove "район"/"райони" suffix)
                raion_name = _re_oblast.sub(r'\s*(райони?|р-н\.?).*$', '', raion_part).strip()
                add_debug_log(f"After removing suffix, raion_name: '{raion_name}'", "oblast_raion")

                # Normalize raion name
                raion_normalized = _re_oblast.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_name)
                add_debug_log(f"Normalized raion: '{raion_normalized}', checking in RAION_FALLBACK", "oblast_raion")

                if raion_normalized in RAION_FALLBACK:
                    lat, lng = RAION_FALLBACK[raion_normalized]
                    add_debug_log(f"Creating oblast+raion marker: {raion_normalized} at {lat}, {lng}", "oblast_raion")

                    # Use classify function to determine correct threat type and icon
                    threat_type, icon = classify(original_text, raion_normalized)

                    tracks.append({
                        'id': f"{mid}_raion_{raion_normalized}",
                        'place': f"{raion_normalized.title()} район",
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': original_text[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': 'oblast_raion_format'
                    })
                else:
                    add_debug_log(f"Raion not found in RAION_FALLBACK: '{raion_normalized}'. Available keys: {list(RAION_FALLBACK.keys())[:10]}...", "oblast_raion")

        if tracks:
            add_debug_log(f"Returning {len(tracks)} oblast+raion markers", "oblast_raion")
            return tracks

    large_message_mode = False
    LARGE_THRESHOLD = 15000
    HARD_CUTOFF = 40000  # safety to avoid pathological regex backtracking
    parse_started_ts = time.perf_counter()
    if text and len(text) > LARGE_THRESHOLD:
        large_message_mode = True
        orig_len = len(text)
        if orig_len > HARD_CUTOFF:
            # Keep head + tail slices to retain some closing context
            head = text[:HARD_CUTOFF//2]
            tail = text[-2000:]
            text = head + "\n...TRUNCATED...\n" + tail
            log.debug(f"mid={mid} large_message_mode truncation {orig_len}->{len(text)} chars")
        else:
            log.debug(f"mid={mid} large_message_mode len={orig_len}")
        # Quick complexity metrics
        try:
            lc = text.lower()
            metrics = {
                'len': orig_len,
                'lines': text.count('\n') + 1,
                'bpla': lc.count('бпла'),
                'shahed': lc.count('шахед'),
                'course': lc.count('курс'),
                'napr': lc.count('напрям') + lc.count('напрямку')
            }
            log.debug(f"mid={mid} large_msg_metrics {metrics}")
        except Exception:
            pass
        # Pre-scan chunk optimization: if many repeated 'бпла курсом на', extract tokens fast before heavy regex blocks
        try:
            if text.lower().count('курс') > 8 and text.lower().count('бпла') > 8:
                fast_tokens = []
                for ln in text.split('\n'):
                    lnl = ln.lower()
                    if 'бпла' in lnl and 'курс' in lnl and ' на ' in lnl:
                        # light-weight extraction (avoid complex backtracking)
                        # Regex: capture token after 'курс(ом) на' up to 40 chars (letters, spaces, dashes)
                        m = re.search(r"курс(?:ом)?\s+на\s+([a-zа-яіїєґ\-\s]{3,40})", lnl, re.IGNORECASE)
                        if m:
                            tok = m.group(1).strip()
                            if tok and tok not in fast_tokens:
                                fast_tokens.append(tok)
                if fast_tokens:
                    log.debug(f"mid={mid} pre-scan collected {len(fast_tokens)} fast_tokens (will still run main parser)")
        except Exception as _e_fast:
            log.debug(f"mid={mid} pre-scan error: {_e_fast}")
    # Early benign filter: city name + emojis / hearts without any threat keywords -> ignore
    try:
        lt = (text or '').lower().strip()
        if lt:
            # threat indicator tokens (broad stems)
            threat_tokens = (
                'шахед','shahed','бпла','дрон','ракет','каб','вибух','прил','удар','загроз','тривог',
                'пуск','зліт','злет','avia','авіа','пво','обстр','mlrs','rszv','fpv','артил','зеніт','зенит'
            )
            if not any(t in lt for t in threat_tokens):
                # strip emojis & symbols leaving letters, spaces and apostrophes
                import re as _re_benign
                core = _re_benign.sub(r"[^a-zа-яіїєґ'’ʼ`\s-]","", lt)
                core = ' '.join(core.split())
                # If core matches exactly a known city (or its normalized form) and original text length small -> benign
                if 2 <= len(core) <= 30:
                    base = UA_CITY_NORMALIZE.get(core, core)
                    if base in CITY_COORDS or ('SETTLEMENTS_INDEX' in globals() and (globals().get('SETTLEMENTS_INDEX') or {}).get(base)):
                        # Ignore this message (no tracks)
                        add_debug_log(f"BENIGN FILTER blocked message mid={mid} - detected city name without threats: '{core}'", "filter")
                        return []
            # NEW suppression: reconnaissance-only notes ("дорозвідка по БпЛА") should not produce a marker
            # Pattern triggers if word 'дорозвідк' present together with UAV terms but no other threat verbs
            if 'дорозвідк' in lt and any(k in lt for k in ['бпла','shahed','шахед','дрон']):
                # Avoid suppressing if explosions or launches also present
                if not any(k in lt for k in ['вибух','удар','пуск','прил','обстріл','обстрел','зліт','злет']):
                    add_debug_log(f"RECONNAISSANCE FILTER blocked message mid={mid} - reconnaissance only", "filter")
                    return []
    except Exception:
        pass

    # SPECIAL: Handle multiple threats in one message BEFORE other parsing
    def handle_multiple_threats():
        """Check for messages with multiple different threats and process each separately"""
        all_threats = []
        text_lower = text.lower()

        # 1. Check for northeast tactical aviation threat
        if ('тактичн' in text_lower or 'авіаці' in text_lower or 'авиац' in text_lower) and (
            'північно-східн' in text_lower or 'північно східн' in text_lower or 'северо-восточ' in text_lower or 'північного-сходу' in text_lower
        ):
            lat, lng = 51.0, 36.5  # On Russian territory near Belgorod (before Ukraine border)
            all_threats.append({
                'id': f"{mid}_ne_multi", 'place': 'Північно-східний напрямок', 'lat': lat, 'lng': lng,
                'threat_type': 'avia', 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'avia.png', 'source_match': 'multiple_threats_northeast_aviation'
            })

        # 2. Check for reconnaissance UAV in Mykolaiv oblast (миколаївщини/миколаївщині)
        if ('розвід' in text_lower or 'розведуваль' in text_lower) and ('миколаївщини' in text_lower or 'миколаївщині' in text_lower or 'миколаївщина' in text_lower):
            # Use Mykolaiv city coordinates
            lat, lng = 46.9750, 31.9946
            all_threats.append({
                'id': f"{mid}_mykolaiv_recon", 'place': 'Миколаївщина', 'lat': lat, 'lng': lng,
                'threat_type': 'rozved', 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'rozvedka2.png', 'source_match': 'multiple_threats_mykolaiv_recon'
            })

        # 3. Check for general БПЛА threats in oblast format (миколаївщини/миколаївщині) without "розвід"
        elif ('бпла' in text_lower or 'дрон' in text_lower) and ('миколаївщини' in text_lower or 'миколаївщині' in text_lower or 'миколаївщина' in text_lower):
            lat, lng = 46.9750, 31.9946
            all_threats.append({
                'id': f"{mid}_mykolaiv_uav", 'place': 'Миколаївщина', 'lat': lat, 'lng': lng,
                'threat_type': 'shahed', 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'shahed3.webp', 'source_match': 'multiple_threats_mykolaiv_uav'
            })

        return all_threats

    # Check if this is a multi-threat message
    if '🛬' in text and '🛸' in text:
        multi_threats = handle_multiple_threats()
        if multi_threats:
            add_debug_log(f"MULTIPLE THREATS DETECTED: Found {len(multi_threats)} threats", "multi_threats")
            return multi_threats

    # EARLY CHECK: Multi-regional UAV messages (before other logic can interfere)
    text_lines = text.split('\n')
    region_count = sum(1 for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:', 'край:']) or (
        'щина' in line.lower() and line.lower().strip().endswith(':')
    ))
    uav_count = sum(1 for line in text_lines if 'бпла' in line.lower() and ('курс' in line.lower() or 'на ' in line.lower()))

    if region_count >= 2 and uav_count >= 3:
        add_debug_log(f"EARLY MULTI-REGIONAL UAV DETECTION: {region_count} regions, {uav_count} UAVs", "multi_regional")
        # We'll process this later when all functions are defined
        # Set a flag for now
        multi_regional_flag = True
    else:
        multi_regional_flag = False

    # ... existing parsing logic continues ...
    # At the very end of function (before return default) we'll log duration.
    # Air alarm region/raion tracking (start / cancel) before other parsing
    try:
        low_full = (text or '').lower()
        now_ep = time.time()
        lines = [l.strip() for l in (text or '').split('\n') if l.strip()][:3]
        if lines:
            header = lines[0].lower()
            header_norm = header.replace('область', 'обл.').replace('обл..','обл.')
            # Oblast alarm start: contains '<adj> обл.' and body has 'повітряна тривога'
            if ('повітр' in low_full or 'тривог' in low_full) and ' обл' in header_norm:
                m_obl = re.search(r"([а-яіїєґ\-']+?)\s+обл\.?", header_norm)
                if m_obl:
                    stem = m_obl.group(1)
                    # Match against OBLAST_CENTERS keys
                    for k in OBLAST_CENTERS.keys():
                        if k.startswith(stem):
                            is_new = k not in ACTIVE_OBLAST_ALARMS
                            rec = ACTIVE_OBLAST_ALARMS.setdefault(k, {'since': now_ep, 'last': now_ep})
                            if rec['since'] > now_ep: rec['since'] = now_ep
                            rec['last'] = now_ep
                            persist_alarm('oblast', k, rec['since'], rec['last'])
                            if is_new:
                                log_alarm_event('oblast', k, 'start', now_ep)
                            break
            # Raion alarm start: '<name> район'
            if ('повітр' in low_full or 'тривог' in low_full) and ' район' in header:
                m_r = re.search(r"([а-яіїєґ\-']+?)\s+район", header)
                if m_r:
                    rb = m_r.group(1).replace('’',"'").replace('ʼ',"'")
                    if rb in RAION_FALLBACK:
                        is_new_r = rb not in ACTIVE_RAION_ALARMS
                        rec = ACTIVE_RAION_ALARMS.setdefault(rb, {'since': now_ep, 'last': now_ep})
                        if rec['since'] > now_ep: rec['since'] = now_ep
                        rec['last'] = now_ep
                        persist_alarm('raion', rb, rec['since'], rec['last'])
                        if is_new_r:
                            log_alarm_event('raion', rb, 'start', now_ep)
        # Cancellation lines contain 'відбій тривоги' or 'отбой тревоги'
        if ('відбій' in low_full or 'отбой' in low_full) and ('тривог' in low_full or 'тревог' in low_full):
            # Precise: look for explicit oblast adjectives endings '-ська', '-цька', '-ницька', etc.
            # Pattern: відбій тривоги у / в <word...> області OR '<adj> обл.'
            m_cancel_obl = re.findall(r"(\b[а-яіїєґ\-']+?)(?:ська|цька|ницька|зька|жська)\s+обл(?:асть|\.|)", low_full)
            removed_any = False
            if m_cancel_obl:
                for stem in m_cancel_obl:
                    for k in list(ACTIVE_OBLAST_ALARMS.keys()):
                        if k.startswith(stem):
                            ACTIVE_OBLAST_ALARMS.pop(k, None); remove_alarm('oblast', k); log_alarm_event('oblast', k, 'cancel', now_ep); removed_any=True
            # Raion precise cancel: "відбій тривоги у <name> районі" (locative: -ському / -івському)
            m_cancel_r = re.findall(r"відбій[^\n]*?\b([а-яіїєґ\-']+?)(?:ському|івському|ському)\s+районі", low_full)
            if m_cancel_r:
                for stem in m_cancel_r:
                    for r in list(ACTIVE_RAION_ALARMS.keys()):
                        if r.startswith(stem):
                            ACTIVE_RAION_ALARMS.pop(r, None); remove_alarm('raion', r); log_alarm_event('raion', r, 'cancel', now_ep); removed_any=True
            # Fallback broad cancel if phrase generic and no explicit names matched
            if not removed_any and re.search(r"відбій\s+тривог|отбой\s+тревог", low_full):
                # remove all (global відбій)
                for k in list(ACTIVE_OBLAST_ALARMS.keys()):
                    ACTIVE_OBLAST_ALARMS.pop(k, None); remove_alarm('oblast', k); log_alarm_event('oblast', k, 'cancel', now_ep)
                for r in list(ACTIVE_RAION_ALARMS.keys()):
                    ACTIVE_RAION_ALARMS.pop(r, None); remove_alarm('raion', r); log_alarm_event('raion', r, 'cancel', now_ep)
        # Expire stale
        ttl_cut = now_ep - APP_ALARM_TTL_MINUTES*60
        for dct in (ACTIVE_OBLAST_ALARMS, ACTIVE_RAION_ALARMS):
            for k in list(dct.keys()):
                if dct[k]['last'] < ttl_cut:
                    level = 'oblast' if dct is ACTIVE_OBLAST_ALARMS else 'raion'
                    dct.pop(k, None)
                    remove_alarm(level, k)
                    log_alarm_event(level, k, 'expire', now_ep)
    except Exception as _e_alarm:
        log.debug(f'alarm tracking block error: {_e_alarm}')
    # Early single-city (bold/emoji tolerant) parser
    try:
        orig = text
        head = orig.split('\n',1)[0][:160]
        
        # DEBUG: Log incoming message for mapstransler parsing
        print(f"[PARSER_DEBUG] Processing message: {repr(head[:80])}...")

        # PRIORITY: Handle mapstransler_bot format: "[count]х БПЛА/КАБ/Ракета Місто (Область обл.)"
        # Examples:
        #   "2х БПЛА Барвінкове (Харківська обл.) Загроза застосування БПЛА."
        #   "БПЛА Єланець (Миколаївська обл.) Загроза застосування БПЛА."
        #   "КАБ Вовчанськ (Харківська обл.)"
        #   "Ракета Запоріжжя (Запорізька обл.)"
        #   "Димер (Київська обл.) Загроза застосування БПЛА."
        #   "БПЛА Федорівку/Піщане (Харківська обл.)" - multiple cities with /
        #   "БПЛА Вільхівку⚠ (Харківська обл.)" - emoji after city name
        # Note: [^(]* allows any chars (including emoji) between city name and (
        # THREAT_TYPES: БПЛА, КАБ, Ракета, Шахед, Дрон
        threat_type_pattern = r'(?:БПЛА|КАБ|Ракета|Ракети|Шахед|Дрон|Дрони)'
        mapstransler_pattern = rf'^[^\w]*(\d+)[xх×]?\s*{threat_type_pattern}\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)'
        mapstransler_match = re.search(mapstransler_pattern, head, re.IGNORECASE)

        # Also try without count prefix
        if not mapstransler_match:
            mapstransler_pattern2 = rf'^[^\w]*{threat_type_pattern}\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)'
            mapstransler_match2 = re.search(mapstransler_pattern2, head, re.IGNORECASE)
            if mapstransler_match2:
                city_raw = mapstransler_match2.group(1).strip()
                oblast_raw = mapstransler_match2.group(2).strip()
                uav_count = 1
            else:
                city_raw = None
                oblast_raw = None
                uav_count = 1
        else:
            uav_count = int(mapstransler_match.group(1))
            city_raw = mapstransler_match.group(2).strip()
            oblast_raw = mapstransler_match.group(3).strip()

        # Handle multiple cities separated by / (take first one)
        if city_raw and '/' in city_raw:
            cities_list = city_raw.split('/')
            city_raw = cities_list[0].strip()  # Take first city
            add_debug_log(f"Multiple cities in message, using first: '{city_raw}' from {cities_list}", "mapstransler")

        # Also try format without БПЛА prefix: "Димер (Київська обл.) Загроза..."
        if not city_raw:
            no_bpla_pattern = r'^[^\w]*([А-ЯІЇЄЁа-яіїєё][А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)\s*загроза'
            no_bpla_match = re.search(no_bpla_pattern, head, re.IGNORECASE)
            if no_bpla_match:
                city_raw = no_bpla_match.group(1).strip()
                # Handle multiple cities
                if '/' in city_raw:
                    city_raw = city_raw.split('/')[0].strip()
                oblast_raw = no_bpla_match.group(2).strip()
                uav_count = 1
                print(f"[PARSER_DEBUG] no_bpla_pattern matched: city='{city_raw}', oblast='{oblast_raw}'")

        if city_raw and oblast_raw:
            print(f"[PARSER_DEBUG] mapstransler MATCHED: city='{city_raw}', oblast='{oblast_raw}', count={uav_count}")
            # Strip course/direction suffixes from city name before normalization
            city_raw = re.sub(r'\s+(курсом|курс|напрям(?:ком)?|в\s+напрямку|у\s+напрямку)\s+.+$', '', city_raw, flags=re.IGNORECASE).strip()
            # Strip "район" suffix - e.g., "Богодухів район" -> "Богодухів"
            city_raw = re.sub(r'\s+район\s*$', '', city_raw, flags=re.IGNORECASE).strip()
            print(f"[PARSER_DEBUG] After cleanup: city='{city_raw}'")
            # Normalize city name (accusative -> nominative) - COMPREHENSIVE
            city_norm = city_raw.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
            city_norm = re.sub(r'\s+',' ', city_norm).strip()

            # Store original for API search
            city_original = city_norm

            # COMPOUND NAMES: Handle "Adjective + Noun" patterns (e.g., "Малу Дівицю" -> "Мала Дівиця")
            # Split into words and normalize each
            words = city_norm.split()
            if len(words) == 2:
                adj, noun = words[0], words[1]

                # Normalize adjective (feminine accusative -> nominative)
                # -у → -а (Малу → Мала, Велику → Велика, Нову → Нова)
                if adj.endswith('у') and len(adj) > 3:
                    adj = adj[:-1] + 'а'
                # -ю → -я (Синю → Синя)
                elif adj.endswith('ю') and len(adj) > 3:
                    adj = adj[:-1] + 'я'

                # Normalize noun
                # -ку → -ка (Дівицку → Дівицка? No, Дівицю → Дівиця)
                if noun.endswith('ку') and len(noun) > 4:
                    noun = noun[:-2] + 'ка'
                elif noun.endswith('цю') and len(noun) > 3:
                    noun = noun[:-1] + 'я'  # Дівицю → Дівиця
                elif noun.endswith('ну') and len(noun) > 4:
                    noun = noun[:-2] + 'на'
                elif noun.endswith('у') and len(noun) > 3:
                    noun = noun[:-1] + 'а'
                elif noun.endswith('ю') and len(noun) > 3:
                    noun = noun[:-1] + 'я'

                city_norm = f"{adj} {noun}"
            else:
                # Single word - apply standard normalization
                # -ку → -ка (Юріївку → Юріївка, Сахновщину → Сахновщина)
                if city_norm.endswith('ку') and len(city_norm) > 4:
                    city_norm = city_norm[:-2] + 'ка'
                # -ну → -на (Сахновщину → Сахновщина)
                elif city_norm.endswith('ну') and len(city_norm) > 4:
                    city_norm = city_norm[:-2] + 'на'
                # -у → -а (Одесу → Одеса)
                elif city_norm.endswith('у') and len(city_norm) > 3:
                    city_norm = city_norm[:-1] + 'а'
                # -ю → -я (Балаклію → Балаклія)
                elif city_norm.endswith('ю') and len(city_norm) > 3:
                    city_norm = city_norm[:-1] + 'я'

            city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)

            # Extract oblast name for Photon API filtering
            oblast_lower = oblast_raw.lower()
            oblast_to_state = {
                'дніпропетровська': 'Дніпропетровська область',
                'харківська': 'Харківська область',
                'київська': 'Київська область',
                'чернігівська': 'Чернігівська область',
                'сумська': 'Сумська область',
                'полтавська': 'Полтавська область',
                'миколаївська': 'Миколаївська область',
                'одеська': 'Одеська область',
                'херсонська': 'Херсонська область',
                'запорізька': 'Запорізька область',
                'донецька': 'Донецька область',
                'луганська': 'Луганська область',
                'черкаська': 'Черкаська область',
                'вінницька': 'Вінницька область',
                'житомирська': 'Житомирська область',
                'рівненська': 'Рівненська область',
                'волинська': 'Волинська область',
                'львівська': 'Львівська область',
                'тернопільська': 'Тернопільська область',
                'хмельницька': 'Хмельницька область',
                'івано-франківська': 'Івано-Франківська область',
                'закарпатська': 'Закарпатська область',
                'чернівецька': 'Чернівецька область',
                'кіровоградська': 'Кіровоградська область',
            }

            target_state = None
            for key, state in oblast_to_state.items():
                if key in oblast_lower:
                    target_state = state
                    break

            add_debug_log(f"Mapstransler pattern: city='{city_raw}' -> norm='{city_norm}', oblast='{oblast_raw}' -> state='{target_state}', count={uav_count}", "mapstransler")

            coords = None

            # Check in-memory cache first
            cache_key = f"{city_norm}|{target_state}"
            
            # MEMORY PROTECTION: Limit cache size
            if len(_mapstransler_geocode_cache) >= _mapstransler_cache_max_size:
                # Remove ~half of the cache (oldest entries - FIFO approximation)
                keys_to_remove = list(_mapstransler_geocode_cache.keys())[:_mapstransler_cache_max_size // 2]
                for k in keys_to_remove:
                    del _mapstransler_geocode_cache[k]
            
            if cache_key in _mapstransler_geocode_cache:
                cached = _mapstransler_geocode_cache[cache_key]
                if cached:
                    coords = cached
                    add_debug_log(f"Cache HIT: {city_norm} -> ({coords[0]}, {coords[1]})", "mapstransler")
                else:
                    add_debug_log(f"Cache HIT (negative): {city_norm} not found previously", "mapstransler")

            # ONLY OpenCage API - no local dictionaries!
            if not coords and cache_key not in _mapstransler_geocode_cache and GEOCODER_AVAILABLE:
                try:
                    region_for_geocode = None
                    if target_state:
                        region_for_geocode = target_state.replace(' область', '').replace('область', '').strip()
                    
                    opencage_coords = opencage_geocode(city_norm, region=region_for_geocode)
                    if opencage_coords:
                        coords = opencage_coords
                        _mapstransler_geocode_cache[cache_key] = coords
                        add_debug_log(f"OpenCage: '{city_norm}' -> {coords}", "mapstransler")
                except Exception as e:
                    add_debug_log(f"OpenCage error: {e}", "mapstransler")

            # Save to cache (both positive and negative results)
            if coords:
                _mapstransler_geocode_cache[cache_key] = coords
                add_debug_log(f"Cache SAVED: {city_norm} -> ({coords[0]}, {coords[1]})", "mapstransler")
            elif cache_key not in _mapstransler_geocode_cache:
                _mapstransler_geocode_cache[cache_key] = None  # Negative cache
                add_debug_log(f"Cache SAVED (negative): {city_norm} not found", "mapstransler")

            # NO FALLBACK TO OBLAST CENTER - if not found, skip this city
            if not coords:
                add_debug_log(f"City NOT FOUND after all APIs, skipping: {city_raw} ({oblast_raw})", "mapstransler")

            if coords:
                if len(coords) == 3:
                    lat, lon = coords[0], coords[1]
                else:
                    lat, lon = coords[:2]

                threat_type, icon = classify(text)
                track = {
                    'id': f"{mid}_mapstransler_{city_norm.replace(' ','_')}",
                    'place': city_raw.title(),
                    'lat': lat, 'lng': lon,
                    'threat_type': threat_type,
                    'text': clean_text(orig)[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'mapstransler_format',
                    'count': uav_count
                }
                add_debug_log(f'Mapstransler parser SUCCESS: {city_raw} ({oblast_raw}) -> {coords}, count={uav_count}', "mapstransler")
                return [track]  # Early return
            else:
                add_debug_log(f'Mapstransler parser: No coords for {city_norm} ({oblast_raw})', "mapstransler")

        # NEW: Handle emoji-prefixed threat messages like "🛸 Звягель (Житомирська обл.) Загроза застосування БПЛА"
        emoji_threat_pattern = r'^[^\w\s]*\s*([А-ЯІЇЄЁа-яіїєё\'\-\s]+)\s*\([^)]*обл[^)]*\)\s*загроза\s+застосування\s+бпла'
        emoji_match = re.search(emoji_threat_pattern, head, re.IGNORECASE)
        if emoji_match:
            city_from_emoji = emoji_match.group(1).strip()
            if city_from_emoji and 2 <= len(city_from_emoji) <= 40:
                base = city_from_emoji.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                base = re.sub(r'\s+',' ', base)
                norm = UA_CITY_NORMALIZE.get(base, base)
                
                # ONLY OpenCage API
                coords = None
                if GEOCODER_AVAILABLE:
                    oblast_match = re.search(r'\(([А-Яа-яЇїІіЄєҐґ\-]+)\s*обл', head, re.IGNORECASE)
                    region_for_geocode = oblast_match.group(1) if oblast_match else None
                    try:
                        coords = opencage_geocode(norm, region=region_for_geocode)
                    except Exception as e:
                        pass
                if coords:
                    lat, lon = coords[:2]
                    threat_type, icon = classify(text)
                    track = {
                        'id': f"{mid}_emoji_threat_{city_from_emoji.replace(' ','_')}",
                        'place': city_from_emoji,
                        'lat': lat, 'lng': lon,
                        'threat_type': threat_type,
                        'text': clean_text(orig)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'emoji_threat'
                    }
                    log.debug(f'Emoji threat parser: {city_from_emoji} -> {coords} -> {icon}')
                    return [track]  # Early return

        # NEW: Handle general emoji + city + oblast format with any UAV threat (more flexible pattern)
        general_emoji_pattern = r'^[^\w\s]*\s*([А-ЯІЇЄЁа-яіїєё\'\-\s]+)\s*\([^)]*обл[^)]*\)'
        general_emoji_match = re.search(general_emoji_pattern, head, re.IGNORECASE)
        add_debug_log(f"Testing general emoji pattern on head: {repr(head)}", "emoji_debug")
        add_debug_log(f"General emoji match result: {general_emoji_match}", "emoji_debug")

        if general_emoji_match and any(uav_word in text.lower() for uav_word in ['бпла', 'дрон', 'шахед', 'активність', 'загроза']):
            city_from_general = general_emoji_match.group(1).strip()

            # Strip UAV-related prefixes from city name (БПЛА, дрон, шахед, etc.)
            uav_prefixes = ['бпла', 'дрон', 'дрони', 'шахед', 'шахеди', 'безпілотник', 'безпілотники', 'ворожий', 'ворожі']
            city_lower = city_from_general.lower()
            for prefix in uav_prefixes:
                if city_lower.startswith(prefix + ' '):
                    city_from_general = city_from_general[len(prefix):].strip()
                    city_lower = city_from_general.lower()
                    add_debug_log(f"Stripped UAV prefix '{prefix}', city now: {repr(city_from_general)}", "emoji_debug")

            add_debug_log(f"Found city from general emoji: {repr(city_from_general)}", "emoji_debug")

            if city_from_general and 2 <= len(city_from_general) <= 40:
                base = city_from_general.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                base = re.sub(r'\s+',' ', base)
                norm = UA_CITY_NORMALIZE.get(base, base)
                coords = CITY_COORDS.get(norm)
                add_debug_log(f"Looking up coordinates: base={repr(base)}, norm={repr(norm)}, coords={coords}", "emoji_debug")

                if not coords and 'SETTLEMENTS_INDEX' in globals():
                    idx_map = globals().get('SETTLEMENTS_INDEX') or {}
                    coords = idx_map.get(norm)
                
                # Try OpenCage API if still no coords
                if not coords and GEOCODER_AVAILABLE:
                    oblast_match = re.search(r'\(([А-Яа-яЇїІіЄєҐґ\-]+)\s*обл', head, re.IGNORECASE)
                    region_for_geocode = oblast_match.group(1) if oblast_match else None
                    try:
                        coords = opencage_geocode(norm, region=region_for_geocode)
                    except Exception as e:
                        pass
                
                if coords:
                    lat, lon = coords[:2]
                    threat_type, icon = classify(text)
                    track = {
                        'id': f"{mid}_general_emoji_{city_from_general.replace(' ','_')}",
                        'place': city_from_general.title(),
                        'lat': lat, 'lng': lon,
                        'threat_type': threat_type,
                        'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'general_emoji_threat'
                    }
                    add_debug_log(f'EARLY RETURN: General emoji threat parser: {city_from_general} -> {coords} -> {icon}', "emoji_debug")
                    return [track]  # Early return

        if '(' in head and ('обл' in head.lower() or 'область' in head.lower()):
            import re as _re_early
            cleaned = head.replace('**','')
            for _zw in ('\u200b','\u200c','\u200d','\ufeff','\u2060','\u00a0'):
                cleaned = cleaned.replace(_zw,' ')
            cleaned = ' '.join(cleaned.split())
            cleaned = _re_early.sub(r'^[^A-Za-zА-Яа-яЇїІіЄєҐґ]+','', cleaned)
            # NEW: if pipe '|' separates multiple city headers in one line, attempt multi-city extraction here
            if '|' in cleaned:
                parts = [p.strip() for p in cleaned.split('|') if p.strip()]
                multi_tracks = []
                for idx, part in enumerate(parts, start=1):
                    if '(' not in part:
                        continue
                    par_pos = part.find('(')
                    if par_pos <= 1:
                        continue
                    city_candidate = part[:par_pos].strip()
                    if not (2 <= len(city_candidate) <= 40):
                        continue
                    try:
                        base = city_candidate.lower().replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
                        base = _re_early.sub(r'\s+',' ', base)
                        norm = UA_CITY_NORMALIZE.get(base, base)
                        coords = CITY_COORDS.get(norm)
                        if not coords and 'SETTLEMENTS_INDEX' in globals():
                            idx_map = globals().get('SETTLEMENTS_INDEX') or {}
                            coords = idx_map.get(norm)
                        approx_flag = False
                        if not coords:
                            enriched = ensure_city_coords(norm, context=part)
                            if enriched:
                                if isinstance(enriched, tuple) and len(enriched) == 3:
                                    coords = (enriched[0], enriched[1])
                                    approx_flag = enriched[2]
                                else:
                                    coords = enriched
                        if not coords:
                            continue
                        # classification per segment
                        lseg = part.lower()
                        if any(ph in lseg for ph in ['повідомляють про вибух','повідомлено про вибух','зафіксовано вибух','зафіксовано вибухи','фіксація вибух','фіксують вибух',' вибух.',' вибухи.']):
                            threat, icon = 'vibuh','vibuh.png'
                        elif 'відбій загрози обстр' in lseg or 'відбій загрози застосування' in lseg or 'відбій загрози бпла' in lseg:
                            # treat as list-only cancellation fragment -> skip map marker for this part
                            multi_tracks.append({
                                'id': f"{mid}_p{idx}", 'text': part[:500], 'date': date_str, 'channel': channel,
                                'list_only': True, 'threat_type': 'alarm_cancel', 'place': city_candidate.title()
                            })
                            continue
                        elif 'загроза застосування бпла' in lseg or 'загроза застосування безпілот' in lseg:
                            threat, icon = 'shahed','shahed3.webp'
                        elif 'загроза обстрілу' in lseg or 'загроза обстрела' in lseg:
                            threat, icon = 'artillery','obstril.png'
                        else:
                            threat, icon = classify(part)
                        lat, lng = coords
                        track = {
                            'id': f"{mid}_p{idx}", 'place': city_candidate.title(), 'lat': lat, 'lng': lng,
                            'threat_type': threat, 'text': part[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'multi_city_pipe'
                        }
                        if approx_flag:
                            track['approx'] = True
                        multi_tracks.append(track)
                    except Exception:
                        continue
                # Return only if 2+ actual geo tracks (ignore if we only produced one, fall back to single-city logic)
                geo_count = sum(1 for t in multi_tracks if not t.get('list_only'))
                if geo_count >= 2:
                    return multi_tracks
            par = cleaned.find('(')
            if par > 1:
                city_candidate = cleaned[:par].strip()

                # CRITICAL FIX: Remove BPLA/count prefixes that should NOT be part of city name
                # Examples: "БПЛА Васильків" -> "Васильків", "2х БПЛА Ніжин" -> "Ніжин"
                city_candidate = _re_early.sub(r'^[^а-яіїєґА-ЯІЇЄҐ]*(\d+[xхX×]?\s*)?БПЛА\s+', '', city_candidate, flags=_re_early.IGNORECASE)
                city_candidate = _re_early.sub(r'^[^а-яіїєґА-ЯІЇЄҐ]*(\d+[xхX×]?\s*)?бпла\s+', '', city_candidate, flags=_re_early.IGNORECASE)
                # Also remove "біля" prefix (e.g., "біля Нового Буга" -> "Нового Буга")
                city_candidate = _re_early.sub(r'^біля\s+', '', city_candidate, flags=_re_early.IGNORECASE)
                # Remove "/груп транзитом" and similar routing noise
                city_candidate = _re_early.sub(r'^/\s*груп\s+транзитом\s+', '', city_candidate, flags=_re_early.IGNORECASE)
                city_candidate = city_candidate.strip()

                if 2 <= len(city_candidate) <= 40:
                    base = city_candidate.lower().replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
                    base = _re_early.sub(r'\s+',' ', base)
                    norm = UA_CITY_NORMALIZE.get(base, base)

                    # CRITICAL: Extract oblast from parentheses for oblast-aware lookup
                    # Format: "City (Oblast обл.)" - extract oblast to disambiguate same-name cities
                    coords = None
                    oblast_key_early = None
                    par_end = cleaned.find(')', par)
                    if par_end > par:
                        oblast_raw_early = cleaned[par+1:par_end].strip()
                        # Extract oblast key: "Миколаївська обл." -> "миколаївська"
                        oblast_lower_early = oblast_raw_early.lower()
                        if ' обл' in oblast_lower_early:
                            oblast_key_early = oblast_lower_early.split(' обл')[0].strip()
                        elif 'область' in oblast_lower_early:
                            oblast_key_early = oblast_lower_early.replace('область', '').strip()

                        # PRIORITY 0: Oblast-aware lookup in UKRAINE_SETTLEMENTS_BY_OBLAST
                        if oblast_key_early and 'UKRAINE_SETTLEMENTS_BY_OBLAST' in globals():
                            settlements_by_oblast = globals().get('UKRAINE_SETTLEMENTS_BY_OBLAST') or {}
                            lookup_key_early = (norm, oblast_key_early)
                            if lookup_key_early in settlements_by_oblast:
                                coords = settlements_by_oblast[lookup_key_early]
                                _log(f"[single_city_simple_early] OBLAST-AWARE HIT: {lookup_key_early} -> {coords}")

                    # Fallback to simple lookup if oblast-aware failed
                    if not coords:
                        coords = CITY_COORDS.get(norm)
                    if not coords and 'SETTLEMENTS_INDEX' in globals():
                        idx = globals().get('SETTLEMENTS_INDEX') or {}
                        coords = idx.get(norm)
                    approx_flag = False
                    if not coords:
                        enriched = ensure_city_coords_with_message_context(norm, orig)
                        if enriched:
                            if isinstance(enriched, tuple) and len(enriched) == 3:
                                coords = (enriched[0], enriched[1])
                                approx_flag = enriched[2]
                            else:
                                coords = enriched
                    if coords:
                        l = orig.lower()
                        if any(ph in l for ph in ['повідомляють про вибух','повідомлено про вибух','зафіксовано вибух','зафіксовано вибухи','фіксація вибух','фіксують вибух',' вибух.',' вибухи.']):
                            threat, icon = 'vibuh','vibuh.png'
                        elif 'відбій загрози обстр' in l or 'відбій загрози застосування' in l or 'відбій загрози бпла' in l:
                            # Treat city-level cancellation as list event, not a geo marker
                            return [{
                                'id': str(mid), 'text': orig[:500], 'date': date_str, 'channel': channel,
                                'list_only': True, 'threat_type': 'alarm_cancel', 'place': city_candidate.title()
                            }]
                        elif 'загроза застосування бпла' in l or 'загроза застосування безпілот' in l:
                            threat, icon = 'shahed','shahed3.webp'
                        elif 'загроза обстрілу' in l or 'загроза обстрела' in l:
                            threat, icon = 'artillery','obstril.png'
                        else:
                            threat, icon = classify(orig)
                        lat,lng = coords
                        track = {
                            'id': str(mid), 'place': city_candidate.title(), 'lat': lat, 'lng': lng,
                            'threat_type': threat, 'text': orig[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'single_city_simple_early'
                        }
                        if approx_flag:
                            track['approx'] = True
                        return [track]
    except Exception:
        pass


    # Directional multi-region (e.g. "група БпЛА на Донеччині курсом на Дніпропетровщину") -> list-only, no fixed marker
    try:
        lorig = text.lower()
        # Skip if this message has route patterns (handled by route parser above)
        if 'через' in lorig or 'повз' in lorig:
            pass
        elif (('курс' in lorig or '➡' in lorig or '→' in lorig or 'напрям' in lorig) and ('бпла' in lorig or 'дрон' in lorig or 'груп' in lorig)) or ('бпла' in lorig and 'частин' in lorig) or ('дрон' in lorig and 'частин' in lorig):
            # Special case: BPLA current location with directional info
            # e.g., "БпЛА в північно-західній частині Полтавщини, курсом на Київщину"
            # or "БпЛА в південно-східній частині Харківщини"
            import re as _re_loc

            # Look for current location patterns
            location_match = _re_loc.search(r'(?:бпла|дрон[иа]?)\s+(?:в|на|над)\s+([а-яіїєґ\-\s]+(?:частин[іа]|район[іе]|округ[уі])\s+[а-яіїєґ]+щин[иаю])', lorig)
            if location_match:
                current_location = location_match.group(1).strip()
                print(f"DEBUG: Found current BPLA location: {current_location}")

                # Extract region from current location
                region_in_location = None
                for reg_key in OBLAST_CENTERS.keys():
                    if reg_key in current_location:
                        region_in_location = reg_key
                        break

                if region_in_location:
                    # Get region center and apply directional offset
                    region_coords = OBLAST_CENTERS.get(region_in_location, (50.0, 30.0))

                    # Apply directional offset based on specified part of region
                    offset_lat, offset_lon = 0, 0
                    if 'північно-західн' in current_location:
                        offset_lat, offset_lon = 0.8, -0.8  # Northwest
                    elif 'північно-східн' in current_location:
                        offset_lat, offset_lon = 0.8, 0.8   # Northeast
                    elif 'південно-західн' in current_location:
                        offset_lat, offset_lon = -0.8, -0.8 # Southwest
                    elif 'південно-східн' in current_location:
                        offset_lat, offset_lon = -0.8, 0.8  # Southeast
                    elif 'північн' in current_location:
                        offset_lat, offset_lon = 0.8, 0     # North
                    elif 'південн' in current_location:
                        offset_lat, offset_lon = -0.8, 0    # South
                    elif 'західн' in current_location:
                        offset_lat, offset_lon = 0, -0.8    # West
                    elif 'східн' in current_location:
                        offset_lat, offset_lon = 0, 0.8     # East
                    elif 'центральн' in current_location:
                        offset_lat, offset_lon = 0, 0       # Center

                    final_lat = region_coords[0] + offset_lat
                    final_lon = region_coords[1] + offset_lon

                    # Clean up city name for display
                    region_name = region_in_location.replace('щини', 'щина').replace('щину', 'щина')
                    direction_part = ""
                    if 'північно-західн' in current_location:
                        direction_part = "Пн-Зх "
                    elif 'північно-східн' in current_location:
                        direction_part = "Пн-Сх "
                    elif 'південно-західн' in current_location:
                        direction_part = "Пд-Зх "
                    elif 'південно-східн' in current_location:
                        direction_part = "Пд-Сх "
                    elif 'північн' in current_location:
                        direction_part = "Пн "
                    elif 'південн' in current_location:
                        direction_part = "Пд "
                    elif 'західн' in current_location:
                        direction_part = "Зх "
                    elif 'східн' in current_location:
                        direction_part = "Сх "
                    elif 'центральн' in current_location:
                        direction_part = "Центр "

                    display_name = f"{direction_part}{region_name.title()}"

                    print(f"DEBUG: Location '{current_location}' in {region_in_location} -> ({final_lat}, {final_lon})")

                    return [{
                        'id': str(mid), 'text': clean_text(text)[:600], 'date': date_str, 'channel': channel,
                        'lat': final_lat, 'lon': final_lon, 'city': display_name,
                        'source_match': 'trajectory_current_location'
                    }]

            # Quick reject if explicit single settlement in parentheses (handled elsewhere)
            if '(' not in lorig:
                present_regions = []
                for reg_key in OBLAST_CENTERS.keys():
                    if reg_key in lorig:
                        present_regions.append(reg_key)
                        if len(present_regions) >= 4:
                            break
                distinct = {r.split()[0] for r in present_regions}
                # Accept patterns like "нова група ударних БпЛА на Донеччині курсом на Дніпропетровщину"
                # even if only 2 region stems present
                if len(distinct) >= 2:
                    # Check if message contains specific cities that should create markers instead
                    city_keywords = ['на кролевец', 'на конотоп', 'на чернігів', 'на вишгород', 'на петрівці', 'на велика димерка', 'на білу церкву', 'на бровари', 'на суми', 'на харків', 'на дніпро', 'на кропивницький', 'на житомир', 'на миколаївку', 'на липовець', 'на ріпки', 'на терни', 'на павлоград']
                    has_specific_cities = any(city_kw in lorig for city_kw in city_keywords)

                    # Also check for pattern "БпЛА на [city]" which should create markers
                    import re as _re_cities
                    bpla_na_pattern = _re_cities.findall(r'бпла\s+на\s+([a-zа-яіїєґʼ`\-\s]{3,20})', lorig)
                    if bpla_na_pattern:
                        has_specific_cities = True

                    if has_specific_cities:
                        # Let multi-city parser handle this instead
                        pass
                    else:
                        # Extra guard: if a well-known large city (e.g. дніпро, харків, київ) appears ONLY because it's substring of region
                        # we still treat as region directional, not city marker
                        # But if message contains multiple explicit directional part-of-region clauses ("на сході <області>" ... "на сході <області>")
                        # then we want to produce separate segment markers instead of a single list-only event.
                        import re as _re_dd
                        dir_clause_count = len(_re_dd.findall(r'на\s+(?:північ|півден|схід|заход|північно|південно)[^\.]{0,40}?(?:щина|щини|щину)', lorig))
                        if dir_clause_count < 2:
                            return [{
                                'id': str(mid), 'text': clean_text(text)[:600], 'date': date_str, 'channel': channel,
                                'list_only': True, 'source_match': 'region_direction_multi'
                            }]
    except Exception:
        pass
    # Comparative directional relative to a city ("північніше Городні", "східніше Кролевця") -> use base city location
    try:
        import re as _re_rel
        low_txt = text.lower()
        # NEW: pattern "<city> - до вас БпЛА" -> marker at city
        m_dash = _re_rel.search(r"([a-zа-яіїєґ'ʼ’`\-]{3,40})\s*[-–—]\s*до вас\s+бпла", low_txt)
        if m_dash:
            raw_city = m_dash.group(1)
            raw_city = raw_city.replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
            base = UA_CITY_NORMALIZE.get(raw_city, raw_city)
            coords = CITY_COORDS.get(base)
            if not coords and 'SETTLEMENTS_INDEX' in globals():
                coords = (globals().get('SETTLEMENTS_INDEX') or {}).get(base)
            if coords:
                lat,lng = coords
                threat, icon = 'shahed','shahed3.webp'
                return [{
                    'id': str(mid), 'place': base.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat, 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'city_dash_uav'
                }]
        # NEW: pattern "БпЛА на <city>" or "бпла на <city>" -> marker at city
        uav_city_pattern = _re_rel.compile(r"бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ\`\s/]+?)(?=\s+(?:з|на|до|від|через|повз|курсом|напрям)\s|[,\.\!\?;:\n]|$)")
        uav_cities = list(uav_city_pattern.finditer(low_txt))
        if uav_cities:
            threats = []
            for idx, match in enumerate(uav_cities):
                rc = match.group(1)
                # If the message continues with course wording immediately after this fragment,
                # treat it as a transit description (let region-course logic handle it)
                tail = low_txt[match.end():match.end()+80]
                if 'курс' in tail:
                    continue
                rc = rc.replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")

                # Handle cities separated by slash (e.g., "вишгород/петрівці")
                cities_to_process = []
                if '/' in rc:
                    cities_to_process.extend(rc.split('/'))
                else:
                    cities_to_process.append(rc)

                for city_idx, city in enumerate(cities_to_process):
                    city = city.strip()
                    if not city:
                        continue

                    base = UA_CITY_NORMALIZE.get(city, city)

                    # Special handling for Kyiv - show directional approach instead of center point
                    if base.lower() == 'київ':
                        kyiv_lat, kyiv_lng, kyiv_label, direction_info = get_kyiv_directional_coordinates(text, base)
                        threat_type, icon = classify(text)

                        # Use specialized icon for directional Kyiv threats
                        if direction_info:
                            icon = 'shahed3.webp'  # Could create special directional icon later

                        threats.append({
                            'id': f"{mid}_uav_{idx}_{city_idx}_kyiv_dir", 'place': kyiv_label, 'lat': kyiv_lat, 'lng': kyiv_lng,
                            'threat_type': threat_type, 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'uav_on_city_kyiv_directional',
                            'direction_info': direction_info
                        })
                        continue

                    coords = CITY_COORDS.get(base)
                    if not coords and 'SETTLEMENTS_INDEX' in globals():
                        coords = (globals().get('SETTLEMENTS_INDEX') or {}).get(base)
                    if coords:
                        lat,lng = coords
                        threats.append({
                            'id': f"{mid}_uav_{idx}_{city_idx}", 'place': base.title(), 'lat': lat, 'lng': lng,
                            'threat_type': 'shahed', 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'shahed3.webp', 'source_match': 'uav_on_city'
                        })
            if threats:
                return threats
        # pattern captures direction word + city morph form
        m_rel = _re_rel.search(r'(північніше|південніше|східніше|західніше)\s+([a-zа-яіїєґ\'ʼ’`\-]{3,40})', low_txt)
        if m_rel:
            raw_city = m_rel.group(2)
            # normalize apostrophes
            raw_city = raw_city.replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
            base = UA_CITY_NORMALIZE.get(raw_city, raw_city)
            coords = CITY_COORDS.get(base)
            if not coords and 'SETTLEMENTS_INDEX' in globals():
                idx = globals().get('SETTLEMENTS_INDEX') or {}
                coords = idx.get(base)
            if not coords:
                enriched = ensure_city_coords(base, context=text)
                if enriched:
                    if isinstance(enriched, tuple) and len(enriched)==3:
                        coords = (enriched[0], enriched[1])
                    else:
                        coords = enriched
            if coords:
                lat,lng = coords
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': base.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'relative_direction_city'
                }]
    except Exception:
        pass
    # Multi-segment UAV messages with pipe separator (e.g., "БпЛА курсом на Кагарлик | 2х БпЛА Білоцерківський район | 3х БпЛА Вишеньки / Українка")
    try:
        if '|' in text and 'бпла' in text.lower():
            segments = [seg.strip() for seg in text.split('|') if seg.strip()]
            if len(segments) >= 2:  # At least 2 segments
                threats = []
                import re as _re_multi

                for seg_idx, segment in enumerate(segments):
                    seg_lower = segment.lower()
                    if 'бпла' not in seg_lower:
                        continue

                    # Pattern 1: "БпЛА курсом на [city]" (with optional н.п. prefix)
                    course_match = _re_multi.search(r'бпла\s+курсом?\s+на\s+(?:н\.п\.?\s*)?([а-яіїєґ\'\-\s]+?)(?:\s*$|\s*\|)', seg_lower)
                    if course_match:
                        city_name = course_match.group(1).strip()
                        city_norm = clean_text(city_name).lower()

                        # Accusative case normalization (винительный падеж)
                        if city_norm == 'велику димерку':
                            city_norm = 'велика димерка'
                        elif city_norm == 'мену':
                            city_norm = 'мена'
                        elif city_norm == 'пісківку':
                            city_norm = 'пісківка'
                        elif city_norm == 'києвом':
                            city_norm = 'київ'
                        # General accusative case endings
                        elif city_norm.endswith('у') and len(city_norm) > 3:
                            city_norm = city_norm[:-1] + 'а'
                        elif city_norm.endswith('ю') and len(city_norm) > 3:
                            city_norm = city_norm[:-1] + 'я'
                        elif city_norm.endswith('ку') and len(city_norm) > 4:
                            city_norm = city_norm[:-2] + 'ка'

                        if city_norm in UA_CITY_NORMALIZE:
                            city_norm = UA_CITY_NORMALIZE[city_norm]

                        coords = ensure_city_coords_with_message_context(city_norm, text)

                        if coords and isinstance(coords, tuple) and len(coords) >= 2:
                            lat, lng = coords[0], coords[1]
                            threat_type, icon = classify(text)
                            # Use normalized city name for display, not the original accusative form
                            display_name = city_norm.title()
                            threats.append({
                                'id': f"{mid}_multi_{seg_idx}",
                                'place': display_name,
                                'lat': lat,
                                'lng': lng,
                                'threat_type': threat_type,
                                'text': f"Курсом на {display_name}",
                                'date': date_str,
                                'channel': channel,
                                'marker_icon': icon,
                                'source_match': 'multi_segment_course',
                                'count': 1
                            })

                    # Pattern 1.5: "БпЛА повз [city1] курсом на [city2]" - extract both cities
                    povz_match = _re_multi.search(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+повз\s+([а-яіїєґ\'\-\s]+?)\s+курсом?\s+на\s+([а-яіїєґ\'\-\s]+?)(?:\s*$|\s*\|)', seg_lower)
                    if povz_match and not course_match:  # Don't double-process if already handled by Pattern 1
                        count_str, city1_name, city2_name = povz_match.groups()
                        count = int(count_str) if count_str and count_str.isdigit() else 1

                        for city_idx, city_raw in enumerate([city1_name, city2_name]):
                            if not city_raw:
                                continue

                            city_name = city_raw.strip()
                            city_norm = clean_text(city_name).lower()

                            # Accusative case normalization for both cities
                            if city_norm == 'велику димерку':
                                city_norm = 'велика димерка'
                            elif city_norm == 'мену':
                                city_norm = 'мена'
                            elif city_norm == 'пісківку':
                                city_norm = 'пісківка'
                            elif city_norm == 'києвом':
                                city_norm = 'київ'
                            # General accusative case endings
                            elif city_norm.endswith('у') and len(city_norm) > 3:
                                city_norm = city_norm[:-1] + 'а'
                            elif city_norm.endswith('ю') and len(city_norm) > 3:
                                city_norm = city_norm[:-1] + 'я'
                            elif city_norm.endswith('ку') and len(city_norm) > 4:
                                city_norm = city_norm[:-2] + 'ка'

                            if city_norm in UA_CITY_NORMALIZE:
                                city_norm = UA_CITY_NORMALIZE[city_norm]

                            coords = ensure_city_coords(city_norm, context=text)

                            if coords and isinstance(coords, tuple) and len(coords) >= 2:
                                lat, lng = coords[0], coords[1]
                                threat_type, icon = classify(text)
                                action = "Повз" if city_idx == 0 else "Курсом на"
                                # Use normalized city name for display
                                display_name = city_norm.title()
                                threats.append({
                                    'id': f"{mid}_multi_{seg_idx}_povz_{city_idx}",
                                    'place': display_name,
                                    'lat': lat,
                                    'lng': lng,
                                    'threat_type': threat_type,
                                    'text': f"{action} {display_name} ({count}x)",
                                    'date': date_str,
                                    'channel': channel,
                                    'marker_icon': icon,
                                    'source_match': 'multi_segment_povz',
                                    'count': count
                                })

                    # Pattern 2: "[N]х БпЛА [location]" - extract cities
                    location_match = _re_multi.search(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(.+?)(?:\.|$)', seg_lower)
                    if location_match and not course_match:  # Don't double-process course segments
                        count_str = location_match.group(1) or "1"
                        location_text = location_match.group(2).strip()
                        count = int(count_str) if count_str.isdigit() else 1

                        # Split by common separators to get individual cities
                        cities = []
                        for sep in [' / ', ' та ', ' і ', ', ']:
                            if sep in location_text:
                                cities = [c.strip() for c in location_text.split(sep) if c.strip()]
                                break
                        if not cities:
                            cities = [location_text]

                        for city_idx, city in enumerate(cities):
                            city = city.strip()
                            if not city:
                                continue

                            # Handle district references (e.g., "Білоцерківський район")
                            if 'район' in city:
                                # Extract district name and try to find main city
                                district_name = city.replace('район', '').replace('ський', '').replace('цький', '').strip()

                                # Special case mappings
                                if 'білоцерків' in district_name:
                                    district_name = 'біла церква'

                                if district_name:
                                    city = district_name
                                else:
                                    continue

                            city_norm = clean_text(city).lower()
                            if city_norm in UA_CITY_NORMALIZE:
                                city_norm = UA_CITY_NORMALIZE[city_norm]

                            coords = ensure_city_coords(city_norm, context=text)

                            if coords and isinstance(coords, tuple) and len(coords) >= 2:
                                lat, lng = coords[0], coords[1]
                                threat_type, icon = classify(text)
                                threats.append({
                                    'id': f"{mid}_multi_{seg_idx}_{city_idx}",
                                    'place': city.title(),
                                    'lat': lat,
                                    'lng': lng,
                                    'threat_type': threat_type,
                                    'text': f"{count}х БпЛА на {city.title()}",
                                    'date': date_str,
                                    'channel': channel,
                                    'marker_icon': icon,
                                    'source_match': f'multi_segment_location_{count}x',
                                    'count': count
                                })

                if threats:
                    # ALSO: Extract cities from emoji structure in the same text
                    # Pattern for "| 🛸 Город (Область)"
                    emoji_pattern = r'\|\s*🛸\s*([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)\s*\([^)]*обл[^)]*\)'
                    emoji_matches = re.finditer(emoji_pattern, text, re.IGNORECASE)

                    for match in emoji_matches:
                        city_raw = match.group(1).strip()
                        if not city_raw or len(city_raw) < 2:
                            continue

                        city_norm = clean_text(city_raw).lower()
                        if city_norm in UA_CITY_NORMALIZE:
                            city_norm = UA_CITY_NORMALIZE[city_norm]

                        coords = ensure_city_coords(city_norm, context=text)

                        if coords:
                            lat, lng = coords[:2]
                            threat_type, icon = classify(text)

                            threat_id = f"{mid}_emoji_struct_{len(threats)}"
                            threats.append({
                                'id': threat_id,
                                'place': city_raw.title(),
                                'lat': lat,
                                'lng': lng,
                                'threat_type': threat_type,
                                'text': f"Загроза в {city_raw}",
                                'date': date_str,
                                'channel': channel,
                                'marker_icon': icon,
                                'source_match': 'emoji_structure_multi',
                                'count': 1
                            })

                            add_debug_log(f"Multi emoji structure: {city_raw} -> {coords}", "emoji_struct_multi")
                        else:
                            add_debug_log(f"Multi emoji structure: No coords for {city_raw}", "emoji_struct_multi")

                    # Check for priority result to combine
                    if '_current_priority_result' in globals() and globals()['_current_priority_result']:
                        combined_result = globals()['_current_priority_result'] + threats
                        add_debug_log(f"MULTI-SEGMENT: Combined priority result ({len(globals()['_current_priority_result'])}) with threats ({len(threats)}) = {len(combined_result)} total", "priority_combine")
                        # Clear the global priority result after use
                        globals()['_current_priority_result'] = None
                        return combined_result
                    return threats

    except Exception:
        pass

    # Course towards single city ("курс(ом) на Батурин") -> place marker at that city
    try:
        import re as _re_course
        low_txt2 = text.lower()
        m_course = _re_course.search(r"курс(?:ом)?\s+на\s+([a-zа-яіїєґ\'ʼ'`\-\s]{3,60})(?=\s*(?:$|[,\.\!\?;]|\n))", low_txt2)
        if m_course:
            raw_city = m_course.group(1).strip()
            raw_city = raw_city.replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
            base = UA_CITY_NORMALIZE.get(raw_city, raw_city)

            # Use enhanced coordinate lookup with Nominatim fallback
            coords = get_coordinates_enhanced(base, context="БпЛА курсом на")

            if not coords:
                # Legacy fallback for backwards compatibility
                enriched = ensure_city_coords(base, context=text)
                if enriched:
                    if isinstance(enriched, tuple) and len(enriched)==3:
                        coords = (enriched[0], enriched[1])
                    else:
                        coords = enriched
                    if isinstance(enriched, tuple) and len(enriched)==3:
                        coords = (enriched[0], enriched[1])
                    else:
                        coords = enriched
            if coords:
                lat,lng = coords
                threat_type, icon = classify(text)

                # Extract course information for Shahed threats
                course_info = None
                if threat_type == 'shahed':
                    course_info = extract_shahed_course_info(text)

                # Extract count from text (look for pattern like "10х БпЛА")
                uav_count = 1
                import re as _re_count
                count_match = _re_count.search(r'(\d+)\s*[xх×]\s*бпла', low_txt2)
                if count_match:
                    uav_count = int(count_match.group(1))

                # Create multiple tracks for multiple drones
                tracks_to_create = max(1, uav_count)
                threat_tracks = []

                for i in range(tracks_to_create):
                    track_name = base.title()
                    if tracks_to_create > 1:
                        track_name += f" #{i+1}"

                    # Add small coordinate offsets to prevent marker overlap
                    marker_lat = lat
                    marker_lng = lng
                    if tracks_to_create > 1:
                        # Create a chain pattern - drones one after another
                        offset_distance = 0.03  # ~3km offset between each drone
                        marker_lat += offset_distance * i
                        marker_lng += offset_distance * i * 0.5

                    threat_data = {
                        'id': f"{mid}_{i+1}", 'place': track_name, 'lat': marker_lat, 'lng': marker_lng,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'course_to_city', 'count': 1
                    }

                    # Add course information if available
                    if course_info:
                        threat_data.update({
                            'course_source': course_info.get('source_city'),
                            'course_target': course_info.get('target_city'),
                            'course_direction': course_info.get('course_direction'),
                            'course_type': course_info.get('course_type')
                        })

                    threat_tracks.append(threat_data)

                return threat_tracks
    except Exception:
        pass

    # --- PRIORITY: Early explicit pattern for districts - MOVED UP TO AVOID CONFLICTS ---
    # Check before region direction processing to prevent fallback to oblast centers
    try:
        import re as _re_raion
        # Pattern 1: "<RaionName> район (<Oblast ...>)"
        m_raion_oblast = _re_raion.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\'\-]{4,})\s+район\s*\(([^)]*обл[^)]*)\)', text)
        if m_raion_oblast:
            raion_token = m_raion_oblast.group(1).strip().lower()
            # Normalize morphological endings
            raion_base = _re_raion.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_token)
            if raion_base in RAION_FALLBACK:
                lat, lng = RAION_FALLBACK[raion_base]
                threat_type, icon = classify(text)
                add_debug_log(f"PRIORITY: Early district processing - {raion_base} район -> {lat}, {lng}", "district_early")
                return [{
                    'id': str(mid), 'place': f"{raion_base.title()} район", 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500],
                    'date': date_str, 'channel': channel, 'marker_icon': icon, 'source_match': 'raion_oblast_combo_early'
                }]
            else:
                add_debug_log(f"Early district processing - {raion_base} not found in RAION_FALLBACK", "district_early")

        # Pattern 2: "<RaionName> район <OblastName>" (без дужок)
        m_raion_oblast2 = _re_raion.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\'\-]{4,})\s+район\s+([\w\']+(?:щини|щину|области|області))', text)
        if m_raion_oblast2:
            raion_token = m_raion_oblast2.group(1).strip().lower()
            # Normalize morphological endings
            raion_base = _re_raion.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_token)
            if raion_base in RAION_FALLBACK:
                lat, lng = RAION_FALLBACK[raion_base]
                threat_type, icon = classify(text)
                add_debug_log(f"PRIORITY: Early district processing (format 2) - {raion_base} район -> {lat}, {lng}", "district_early")
                return [{
                    'id': str(mid), 'place': f"{raion_base.title()} район", 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500],
                    'date': date_str, 'channel': channel, 'marker_icon': icon, 'source_match': 'raion_oblast_combo_early_v2'
                }]
            else:
                add_debug_log(f"Early district processing (format 2) - {raion_base} not found in RAION_FALLBACK", "district_early")
    except Exception as e:
        add_debug_log(f"Early district processing error: {e}", "district_early")

    # Region directional segments specifying part of oblast ("на сході Дніпропетровщини") possibly multiple in one line
    try:
        import re as _re_seg
        lower_full = text.lower()
        pattern = _re_seg.compile(r'на\s+([\w\-\s/]+?)\s+(?:частині\s+)?([a-zа-яіїєґ]+щина|[a-zа-яіїєґ]+щини|[a-zа-яіїєґ]+щину)')
        seg_matches = list(pattern.finditer(lower_full))
        seg_tracks = []
        used_spans = []
        if seg_matches:
            # Map Ukrainian directional forms to codes
            dir_map_words = {
                'північ':'n','південь':'s','схід':'e','захід':'w','сході':'e','заході':'w','півночі':'n','півдні':'s',
                'північно-схід':'ne','північно-сход':'ne','північно схід':'ne','південно-схід':'se','південно схід':'se',
                'північно-захід':'nw','північно захід':'nw','південно-захід':'sw','південно захід':'sw'
            }
            def direction_codes(raw:str):
                parts = [p.strip() for p in raw.replace('–','-').split('/') if p.strip()]
                out = []
                for p in parts:
                    # compress multiple spaces
                    p2 = ' '.join(p.split())
                    # find best match in dir_map_words by prefix
                    code=None
                    for k,v in dir_map_words.items():
                        if k in p2:
                            code=v; break
                    if not code:
                        # try simple endings
                        if p2.startswith('схід'): code='e'
                        elif p2.startswith('захід'): code='w'
                    if code and code not in out:
                        out.append(code)
                return out or ['center']
            for m in seg_matches:
                dir_raw = m.group(1).strip()
                region_raw = m.group(2).strip()
                # Normalize region key to match OBLAST_CENTERS keys
                region_key = None
                for k in OBLAST_CENTERS.keys():
                    if region_raw in k:
                        region_key = k
                        break
                if not region_key:
                    continue
                base_lat, base_lng = OBLAST_CENTERS[region_key]
                codes = direction_codes(dir_raw)
                for idx, code in enumerate(codes,1):
                    # offset placement (reuse logic similar to later region_direction block)
                    def offset(lat,lng,code):
                        lat_step = 0.55
                        lng_step = 0.85 / max(0.2, abs(math.cos(math.radians(lat))))
                        if code=='n': return lat+lat_step, lng
                        if code=='s': return lat-lat_step, lng
                        if code=='e': return lat, lng+lng_step
                        if code=='w': return lat, lng-lng_step
                        lat_diag=lat_step*0.8; lng_diag=lng_step*0.8
                        if code=='ne': return lat+lat_diag, lng+lng_diag
                        if code=='nw': return lat+lat_diag, lng-lng_diag
                        if code=='se': return lat-lat_diag, lng+lng_diag
                        if code=='sw': return lat-lat_diag, lng-lng_diag
                        return lat, lng
                    lat_o, lng_o = offset(base_lat, base_lng, code)
                    label_region = region_key.split()[0].title()
                    dir_label_map = {
                        'n':'північна частина','s':'південна частина','e':'східна частина','w':'західна частина',
                        'ne':'північно-східна частина','nw':'північно-західна частина','se':'південно-східна частина','sw':'південно-західна частина','center':'частина'
                    }
                    label = f"{label_region} ({dir_label_map.get(code,'частина')})"
                    threat_type, icon = classify(text)

                    # Skip if this segment contains "курсом на [city]" after the region match
                    # to give priority to specific city course tracking
                    segment_after = text[m.end():]
                    if _re_seg.search(r'курсом?\s+на\s+(?:н\.п\.?\s*)?[А-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,}', segment_after, _re_seg.IGNORECASE):
                        continue

                    seg_tracks.append({
                        'id': f"{mid}_rd{len(seg_tracks)+1}", 'place': label, 'lat': lat_o, 'lng': lng_o,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_direction_segment'
                    })
            if seg_tracks:
                return seg_tracks
    except Exception as e:
        try: log.debug(f'region_dir_segments error: {e}')
        except: pass
    # --- Pre-split case: several bold oblast headers inside a single line (e.g. **Полтавщина:** ... **Дніпропетровщина:** ... ) ---
    try:
        # Detect two or more bold oblast headers
        hdr_pat = re.compile(r'(\*\*[A-Za-zА-Яа-яЇїІіЄєҐґ]+щина\*\*:)')
        if text.count('**') >= 4:  # quick filter
            matches = list(hdr_pat.finditer(text))
            if len(matches) >= 2:
                # Insert newline before each header (except first) if not already line-start
                # Build new text chunk-wise
                new_parts = []
                last = 0
                for i, m in enumerate(matches):
                    start = m.start()
                    if i == 0 and start > 0 and text[start-1] != '\n':
                        # ensure header is at line start
                        new_parts.append(text[last:start])
                    elif i > 0:
                        # append text before header ensuring newline separation
                        segment = text[last:start]
                        if not segment.endswith('\n'):
                            segment += '\n'
                        new_parts.append(segment)
                    last = start
                # append remaining
                new_parts.append(text[last:])
                new_text_joined = ''.join(new_parts)
                if new_text_joined != text:
                    text = new_text_joined
    except Exception:
        pass
    # --- Спец. обработка многострочных сообщений с заголовками-областями и списком городов ---
    import unicodedata
    def normalize_city_name(name):
        # Привести к нижнему регистру, заменить все апострофы на стандартный, убрать лишние пробелы
        n = name.lower().strip()
        n = n.replace('ʼ', "'").replace('’', "'").replace('`', "'")
        n = unicodedata.normalize('NFC', n)

        # Convert mixed Latin/Cyrillic to full Cyrillic (e.g. "Kov'яги" -> "ков'яги")
        # Common Latin-Cyrillic lookalikes in Ukrainian city names
        latin_to_cyrillic = {
            'a': 'а', 'e': 'е', 'i': 'і', 'o': 'о', 'p': 'р', 'c': 'с',
            'y': 'у', 'x': 'х', 'k': 'к', 'h': 'н', 't': 'т', 'm': 'м',
            'b': 'в', 'v': 'в', 'n': 'н', 's': 'с', 'r': 'р'
        }

        # Only convert if string contains mixed Latin + Cyrillic (heuristic: has both ranges)
        has_cyrillic = any(ord(c) >= 0x0400 and ord(c) <= 0x04FF for c in n)
        has_latin = any('a' <= c <= 'z' for c in n)

        if has_cyrillic and has_latin:
            # Convert Latin lookalikes to Cyrillic
            n_converted = ''
            for c in n:
                if 'a' <= c <= 'z':
                    n_converted += latin_to_cyrillic.get(c, c)
                else:
                    n_converted += c
            n = n_converted

        return n

    def sanitize_course_destination(name: str) -> str:
        if not name:
            return ''
        cleaned = name.strip()
        cleaned = re.sub(r'[\\/|]+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'(район|району|районі|районів|района|р-н|область|області|обл\.|громада|громаді|громади|community|district|sector|сектор|місто|місті)$', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'\b(район|району|районі|района|р-н|область|області|обл\.|громада|громади|community|district|sector|сектор|місто|місті)\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(" .,'-\"")
        low = cleaned.lower()
        tokens = {t for t in re.split(r'\s+', low) if t}
        garbage_tokens = {
            'передмісті', 'передмістя', 'передмістях',
            'містом', 'місті', 'місто', 'містами',
            'чисто', 'чистий', 'чиста', 'чисті'
        }
        if not tokens or tokens.issubset(garbage_tokens):
            return ''
        if 'передміст' in low and 'чист' in low:
            return ''
        return cleaned

    def extract_course_targets(raw: str):
        if not raw:
            return []
        parts = re.split(r'\s*(?:[\\/|,;]|\s+та\s+|\s+і\s+|\s+и\s+|\s+або\s+|\s+or\s+)\s*', raw, flags=re.IGNORECASE)
        targets = []
        for part in parts:
            candidate = sanitize_course_destination(part)
            if candidate:
                targets.append(candidate)
        if targets:
            return targets
        cleaned = sanitize_course_destination(raw)
        return [cleaned] if cleaned else []
    # Если сообщение содержит несколько строк с заголовками-областями и городами
    # Предварительно уберём чисто донатные/подписи строки из многострочного блока, чтобы они не мешали
    raw_lines = text.splitlines()

    # NEW: Handle single-line messages with multiple regions like "Чернігівщина: 1 БпЛА на Козелець ... Сумщина: 3 БпЛА..."
    # First try to split by region headers in single line
    single_line_regions = ['чернігівщин', 'сумщин', 'харківщин', 'полтавщин', 'херсонщин', 'донецьк', 'луганщин']
    if len(raw_lines) == 1 and any(region in text.lower() for region in single_line_regions):
        add_debug_log(f"Single-line multi-region message detected, raw_lines count: {len(raw_lines)}", "multi_region")
        # Split by oblast headers that have colon after them
        import re as _re_split
        region_split = _re_split.split(r'([А-ЯІЇЄЁа-яіїєё]+щина):\s*', text)
        add_debug_log(f"Region split result: {region_split}", "multi_region")
        if len(region_split) > 2:  # We have actual splits
            new_lines = []
            for i in range(1, len(region_split), 2):  # Take every odd element (region name) and next even (content)
                if i+1 < len(region_split):
                    region_name = region_split[i]
                    content = region_split[i+1].strip()
                    new_lines.append(f"{region_name}:")
                    new_lines.append(content)
                    add_debug_log(f"Added region header: '{region_name}:' and content: '{content}'", "multi_region")
            if new_lines:
                raw_lines = new_lines
                add_debug_log(f"Split single line into {len(raw_lines)} lines for multi-region processing", "multi_region")
        else:
            add_debug_log("Region split failed, keeping original format", "multi_region")

    cleaned_for_multiline = []
    import re as _re_clean
    donation_keys = ['монобанк','send.monobank','patreon','donat','донат','підтримати канал','підтримати']
    for l in raw_lines:
        ls = l.strip()
        if not ls:
            continue
        # If line combines header and content ("Хмельниччина: Група КР ..." possibly with formatting ** **)
        m_comb = _re_clean.match(r'^\**([A-Za-zА-Яа-яЇїІіЄєҐґ]+щина)\**:\s*(.+)$', ls)
        if m_comb:
            header_part = m_comb.group(1) + ':'
            rest_part = m_comb.group(2).strip()
            cleaned_for_multiline.append(header_part)
            ls = rest_part  # continue processing rest_part below (could still contain links)
        low_ls = ls.lower()
        # Strip markdown links / segments that are purely donation or service references, keep threat fragment
        def _strip_bad_links(s: str):
            # Remove any [text](url) where text or url contains donation_keys
            def _repl(m):
                inner_text = m.group(1).lower()
                url = m.group(2).lower()
                if any(k in inner_text or k in url for k in donation_keys):
                    return ''
                return m.group(0)
            s2 = _re_clean.sub(r'\[([^\]]{0,60})\]\(([^) ]+?)\)', _repl, s)
            return s2
        ls_no_links = _strip_bad_links(ls)
        low_no_links = ls_no_links.lower()
        if any(k in low_no_links for k in donation_keys):
            # If after stripping links still only donation noise and no threat keywords, skip.
            if not any(t in low_no_links for t in ['бпла','курс','ракета','ракети','рупа','група','кр']):
                continue
            # Else remove the donation substrings explicitly.
            for k in donation_keys:
                low_no_links = low_no_links.replace(k,' ')
            ls_no_links = ' '.join(low_no_links.split())
        cleaned_for_multiline.append(ls_no_links.strip())
    lines = cleaned_for_multiline

    oblast_hdr = None
    multi_city_tracks = []
    processed_lines_count = 0
    add_debug_log(f"Processing {len(lines)} cleaned lines for multi-city tracks", "multi_region")

    for ln in lines:
        processed_lines_count += 1
        add_debug_log(f"Processing line {processed_lines_count}/{len(lines)}: '{ln[:80]}...'", "multi_region")

        # PRIORITY: Check for specific region-city patterns FIRST
        import re as _re_region_city
        ln_lower = ln.lower()

        # Pattern 1: "на [region] [count] шахедів на [city]"
        region_city_pattern1 = _re_region_city.compile(r'на\s+([а-яіїєґ]+щин[іау]?)\s+(\d+)\s+шахед[іїв]*\s+на\s+([а-яіїєґ\'\-\s]+)', _re_region_city.IGNORECASE)
        region_city_match1 = region_city_pattern1.search(ln_lower)

        # Pattern 2: "[region] - шахеди на [city]"
        region_city_pattern2 = _re_region_city.compile(r'([а-яіїєґ]+щин[ауи]?)\s*-\s*шахед[іїив]*\s+на\s+([а-яіїєґ\'\-\s]+)', _re_region_city.IGNORECASE)
        region_city_match2 = region_city_pattern2.search(ln_lower)

        # Pattern 3: "[region] ([city] р-н)" - for district headquarters
        region_district_pattern = _re_region_city.compile(r'([а-яіїєґ]+щин[ауи]?)\s*\(\s*([а-яіїєґ\'\-\s]+)\s+р[-\s]*н\)', _re_region_city.IGNORECASE)
        region_district_match = region_district_pattern.search(ln_lower)

        add_debug_log(f"CHECKING region-city patterns for line: '{ln_lower}'", "region_city_debug")

        region_city_match = region_city_match1 or region_city_match2

        if region_district_match:
            # Handle "чернігівщина (новгород-сіверський р-н)" format
            region_raw, district_raw = region_district_match.groups()
            target_city = district_raw.strip()

            add_debug_log(f"REGION-DISTRICT pattern FOUND: region='{region_raw}', district='{district_raw}'", "region_district")

            # Normalize city name and try to find coordinates
            city_norm = target_city.lower()
            # Apply UA_CITY_NORMALIZE rules if available
            if 'UA_CITY_NORMALIZE' in globals():
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
            coords = CITY_COORDS.get(city_norm)

            add_debug_log(f"District city lookup: '{target_city}' -> '{city_norm}' -> {coords}", "region_district")

            if coords:
                lat, lng = coords
                threat_type, icon = classify(ln)

                multi_city_tracks.append({
                    'id': f"{mid}_region_district_{len(multi_city_tracks)+1}",
                    'place': target_city.title(),
                    'lat': lat,
                    'lng': lng,
                    'threat_type': threat_type,
                    'text': ln[:500],
                    'date': date_str,
                    'channel': channel,
                    'marker_icon': icon,
                    'source_match': 'region_district',
                    'count': 1
                })
                add_debug_log(f"Created region-district marker: {target_city.title()}", "region_district")
                continue  # Skip further processing of this line
            else:
                add_debug_log(f"No coordinates found for district city: '{target_city}' (normalized: '{city_norm}')", "region_district")

        elif region_city_match:
            if region_city_match1:
                region_raw, count_str, city_raw = region_city_match1.groups()
                count = int(count_str) if count_str.isdigit() else 1
            else:  # region_city_match2
                region_raw, city_raw = region_city_match2.groups()
                count = 1  # default count for pattern 2

            target_city = city_raw.strip()

            add_debug_log(f"REGION-CITY pattern FOUND: region='{region_raw}', count={count}, city='{target_city}'", "region_city")

            # Normalize city name and try to find coordinates
            city_norm = target_city.lower()
            # Apply UA_CITY_NORMALIZE rules if available
            if 'UA_CITY_NORMALIZE' in globals():
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
            coords = CITY_COORDS.get(city_norm)

            add_debug_log(f"City lookup: '{target_city}' -> '{city_norm}' -> {coords}", "region_city")

            if coords:
                lat, lng = coords
                threat_type, icon = classify(ln)

                multi_city_tracks.append({
                    'id': f"{mid}_region_city_{len(multi_city_tracks)+1}",
                    'place': target_city.title(),
                    'lat': lat,
                    'lng': lng,
                    'threat_type': threat_type,
                    'text': ln[:500],
                    'date': date_str,
                    'channel': channel,
                    'marker_icon': icon,
                    'source_match': 'region_city_shahed',
                    'count': count
                })
                add_debug_log(f"Created region-city marker: {target_city.title()} ({count} шахедів)", "region_city")
                continue  # Skip further processing of this line
            else:
                add_debug_log(f"No coordinates found for city: '{target_city}' (normalized: '{city_norm}')", "region_city")
        else:
            add_debug_log(f"REGION-CITY pattern NOT FOUND for line: '{ln_lower}'", "region_city_debug")

        # NEW: Pattern "БпЛА на [direction] [region_genitive] курсом на [target]"
        # Example: "БпЛА на півночі Херсонщини курсом на Миколаївщину"
        regional_course_pattern = re.search(r'(бпла|безпілотник|шахед|дрон).*(на\s+(півночі|півдні|сході|заході|центрі))?\s*([а-яіїєґ]+щин[іуиа])\s*.*курсом\s+на\s+([а-яіїєґ\'\-\s]+)', ln_lower, re.IGNORECASE)
        if regional_course_pattern:
            direction_part = regional_course_pattern.group(3) if regional_course_pattern.group(2) else None
            region_genitive = regional_course_pattern.group(4)
            target_raw = regional_course_pattern.group(5).strip()

            # Normalize target (could be city or region)
            target_norm = target_raw.replace('щину', 'щина').replace('щини', 'щина').strip()

            add_debug_log(f"REGIONAL COURSE pattern: direction={direction_part}, region={region_genitive}, target={target_raw} -> {target_norm}", "regional_course")

            # Try to find coordinates for target
            target_city = normalize_city_name(target_norm)
            target_city = UA_CITY_NORMALIZE.get(target_city, target_city)
            coords = CITY_COORDS.get(target_city)
            if not coords and SETTLEMENTS_INDEX:
                coords = SETTLEMENTS_INDEX.get(target_city)

            # If target is a region (щина), use region center
            if not coords and ('щина' in target_city or 'щини' in target_city):
                # Try to get region center coordinates
                region_centers = {
                    'миколаївщина': (46.975, 31.995),
                    'херсонщина': (46.635, 32.617),
                    'чернігівщина': (51.4982, 31.2893),
                    'сумщина': (50.9077, 34.7981),
                    'полтавщина': (49.5883, 34.5514),
                    'харківщина': (49.9935, 36.2304),
                    'дніпропетровщина': (48.4647, 35.0462),
                    'запоріжжя': (47.8388, 35.1396),
                    'донеччина': (48.0159, 37.8028),
                }
                coords = region_centers.get(target_city)
                if coords:
                    add_debug_log(f"Using region center for '{target_city}': {coords}", "regional_course")

            if coords:
                lat, lng = coords
                threat_type, icon = classify(ln)

                # Extract count if present
                count_match = re.search(r'(\d+)\s*[xх×]?\s*(бпла|шахед)', ln_lower)
                count = int(count_match.group(1)) if count_match else 1

                place_label = target_norm.title()
                if direction_part:
                    place_label += f" ({direction_part})"

                multi_city_tracks.append({
                    'id': f"{mid}_regional_course_{len(multi_city_tracks)+1}",
                    'place': place_label,
                    'lat': lat,
                    'lng': lng,
                    'threat_type': threat_type,
                    'text': clean_text(ln)[:500],
                    'date': date_str,
                    'channel': channel,
                    'marker_icon': icon,
                    'source_match': 'regional_course',
                    'count': count
                })
                add_debug_log(f"Created regional course marker: {place_label} at {lat}, {lng}", "regional_course")
                continue
            else:
                add_debug_log(f"No coordinates for regional course target: '{target_raw}' (norm: '{target_city}')", "regional_course")

        # NEW: Check for regional direction patterns WITHOUT specific city (e.g. "БпЛА на сході Сумщини ➡️ курсом на південь")
        # These should create regional markers, not skip
        region_direction_pattern = re.search(r'(бпла|безпілотник|шахед|дрон).*(на\s+(півночі|півдні|сході|заході)).*([а-яіїєґ]+щин[іуиа])', ln_lower, re.IGNORECASE)
        if region_direction_pattern and not region_city_match and not regional_course_pattern:
            add_debug_log(f"REGIONAL DIRECTION pattern detected (no specific city): {ln[:100]}", "regional_direction")
            # This line should be processed by regional parser - don't add to multi_city_tracks yet
            # Instead, extract the region and direction to create a regional marker later
            # For now, just mark it for special processing

        # Check if line contains БпЛА information without specific course
        ln_lower = ln.lower()
        # Support both Cyrillic БпЛА and Latin-mixed БпЛA variants, and also Shahed
        has_uav = 'бпла' in ln_lower or 'бпла' in ln_lower or 'безпілотник' in ln_lower or 'дрон' in ln_lower or 'bpla' in ln_lower or 'шахед' in ln_lower or 'shahed' in ln_lower
        if has_uav:
            add_debug_log("Line contains UAV keywords", "multi_region")
            if not any(keyword in ln_lower for keyword in ['курс', 'на ', 'районі']):
                add_debug_log("UAV line lacks direction keywords (курс/на/районі) - general activity message", "multi_region")
        else:
            add_debug_log("Line does not contain UAV keywords", "multi_region")
        # Если строка — это заголовок области (например, "Сумщина:")
        # Заголовок области: строка, заканчивающаяся на ':' (возможен пробел перед / после) или формой '<область>:' с лишними пробелами
        # NEW: Also handle format like "**🚨 Конотопський район (Сумська обл.)**"
        import re
        oblast_hdr_match = None

        # Standard format: "Сумщина:" or "Чернігівщина:"
        if re.match(r'^[A-Za-zА-Яа-яЇїІіЄєҐґ\-ʼ`\s]+:\s*$', ln):
            oblast_hdr = ln.split(':')[0].strip().lower()
            oblast_hdr_match = True
            add_debug_log(f"Standard region header format detected: '{oblast_hdr}'", "multi_region")

        # NEW format: "**🚨 Конотопський район (Сумська обл.)**" or similar with oblast in parentheses
        elif re.search(r'\(([А-ЯІЇЄЁа-яіїєё]+ська\s+обл\.?)\)', ln):
            oblast_match = re.search(r'\(([А-ЯІЇЄЁа-яіїєё]+ська\s+обл\.?)\)', ln)
            if oblast_match:
                oblast_full = oblast_match.group(1).lower().strip()
                # Convert "сумська обл." to "сумщина"
                oblast_hdr = oblast_full.replace('ська обл.', 'щина').replace('ська обл', 'щина')
                oblast_hdr_match = True
                add_debug_log(f"Parentheses region header format detected: '{oblast_full}' -> '{oblast_hdr}'", "multi_region")

        # NEW format: "Харківщина — БпЛА на Гути" - region with dash followed by content
        elif re.search(r'^([А-ЯІЇЄЁа-яіїєё]+щина)\s*[-–—]\s*(.+)', ln):
            dash_match = re.search(r'^([А-ЯІЇЄЁа-яіїєё]+щина)\s*[-–—]\s*(.+)', ln)
            if dash_match:
                oblast_hdr = dash_match.group(1).lower().strip()
                remaining_content = dash_match.group(2).strip()
                oblast_hdr_match = True
                add_debug_log(f"Dash region header format detected: '{oblast_hdr}' with content: '{remaining_content}'", "multi_region")
                # Set the line content to just the remaining part after dash for further processing
                ln = remaining_content

        # NEW: Detect regional genitive forms like "Сумщини", "Харківщини", etc.
        elif re.search(r'\b([а-яіїєґ]+щин[иі])\b', ln_lower):
            genitive_match = re.search(r'\b([а-яіїєґ]+щин[иі])\b', ln_lower)
            if genitive_match:
                genitive_form = genitive_match.group(1)
                # Convert genitive to nominative: "сумщини" -> "сумщина"
                potential_oblast = genitive_form.replace('щини', 'щина').replace('щині', 'щина')

                # Validate that this is actually a known region, not just any word ending with щин[иі]
                known_regions = ['сумщина', 'чернігівщина', 'харківщина', 'полтавщина', 'херсонщина',
                               'донеччина', 'луганщина', 'запорожжя', 'дніпропетровщина', 'київщина',
                               'львівщина', 'івано-франківщина', 'тернопільщина', 'хмельниччина',
                               'рівненщина', 'волинщина', 'житомирщина', 'вінниччина', 'черкащина',
                               'кіровоградщина', 'миколаївщина', 'одещина']

                if potential_oblast in known_regions:
                    oblast_hdr = potential_oblast
                    oblast_hdr_match = True
                    add_debug_log(f"Genitive region format detected: '{genitive_form}' -> '{oblast_hdr}' in line: '{ln}'", "multi_region")
                    add_debug_log(f"POTENTIAL ISSUE: Oblast set to '{oblast_hdr}' from genitive pattern in: '{ln}'", "oblast_detection")
                else:
                    add_debug_log(f"Ignored potential genitive form '{genitive_form}' -> '{potential_oblast}' (not in known regions) in line: '{ln}'", "multi_region")

        if oblast_hdr_match:
            add_debug_log(f"Region header detected: '{oblast_hdr}'", "multi_region")
            if oblast_hdr.startswith('на '):  # handle 'на харківщина:' header variant
                oblast_hdr = oblast_hdr[3:].strip()
            if oblast_hdr and oblast_hdr[0] in ('е','є') and oblast_hdr.endswith('гівщина'):
                # восстановить черниговщина -> чернігівщина (fix dropped leading Ч)
                oblast_hdr = 'чернігівщина'
            # Доп. почин восстановлений первых букв для областей (потеря первой буквы)
            if oblast_hdr and oblast_hdr.endswith('ївщина') and oblast_hdr != 'київщина':
                oblast_hdr = 'київщина'
            if oblast_hdr and oblast_hdr.endswith('нниччина') and oblast_hdr != 'вінниччина':
                oblast_hdr = 'вінниччина'
            # header detected
            add_debug_log(f"Final region header: '{oblast_hdr}'", "multi_region")
            continue
        try:
            add_debug_log(f"MLINE_LINE oblast={oblast_hdr} raw='{ln}'", "multi_region")
        except Exception:
            pass

        # NEW: Check for specific direction patterns before falling back to general UAV activity
        import re
        ln_lower = ln.lower()

        # NEW: Pattern "кружляє над/над [city]"
        if 'кружляє' in ln_lower or 'кружля' in ln_lower:
            kruzhlia_match = re.search(r'кружля[єюя]\s+(?:над\s+)?([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)', ln, re.IGNORECASE)
            if kruzhlia_match:
                city_raw = kruzhlia_match.group(1).strip()
                city_norm = normalize_city_name(city_raw)
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
                coords = CITY_COORDS.get(city_norm) or (SETTLEMENTS_INDEX.get(city_norm) if SETTLEMENTS_INDEX else None)

                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(ln)
                    count_match = re.search(r'(\d+)[xх×]?\s*бпла', ln_lower)
                    count = int(count_match.group(1)) if count_match else 1

                    # Create multiple tracks if count > 1
                    for i in range(count):
                        place_label = city_norm.title()
                        if count > 1:
                            place_label += f" #{i+1} (кружляє)"
                        else:
                            place_label += " (кружляє)"

                        # Add offset for multiple drones
                        marker_lat, marker_lng = lat, lng
                        if count > 1:
                            offset_distance = 0.03
                            marker_lat += offset_distance * i
                            marker_lng += offset_distance * i * 0.5

                        multi_city_tracks.append({
                            'id': f"{mid}_kruzhlia_{len(multi_city_tracks)+1}",
                            'place': place_label,
                            'lat': marker_lat,
                            'lng': marker_lng,
                            'threat_type': threat_type,
                            'text': clean_text(ln)[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'kruzhlia_nad',
                            'count': 1
                        })
                    add_debug_log(f"Created {count} marker(s) for 'кружляє': {city_norm.title()}", "kruzhlia")
                    continue

        # NEW: Pattern "північніше/південніше/східніше/західніше [city]"
        if any(direction in ln_lower for direction in ['північніше', 'південніше', 'східніше', 'західніше']):
            direction_match = re.search(r'(північніше|південніше|східніше|західніше)\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)', ln, re.IGNORECASE)
            if direction_match:
                direction_type = direction_match.group(1).lower()
                city_raw = direction_match.group(2).strip()
                city_norm = normalize_city_name(city_raw)
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
                coords = CITY_COORDS.get(city_norm) or (SETTLEMENTS_INDEX.get(city_norm) if SETTLEMENTS_INDEX else None)

                if coords:
                    lat, lng = coords
                    # Apply directional offset based on direction type
                    offset = 0.15  # ~15km
                    if direction_type == 'північніше':
                        lat += offset
                    elif direction_type == 'південніше':
                        lat -= offset
                    elif direction_type == 'східніше':
                        lng += offset
                    elif direction_type == 'західніше':
                        lng -= offset

                    threat_type, icon = classify(ln)
                    count_match = re.search(r'(\d+)[xх×]?\s*бпла', ln_lower)
                    count = int(count_match.group(1)) if count_match else 1

                    # Create multiple tracks if count > 1
                    for i in range(count):
                        place_label = f"{direction_type.title()} {city_norm.title()}"
                        if count > 1:
                            place_label += f" #{i+1}"

                        # Add offset for multiple drones
                        marker_lat, marker_lng = lat, lng
                        if count > 1:
                            offset_distance = 0.03
                            marker_lat += offset_distance * i
                            marker_lng += offset_distance * i * 0.5

                        multi_city_tracks.append({
                            'id': f"{mid}_direction_{len(multi_city_tracks)+1}",
                            'place': place_label,
                            'lat': marker_lat,
                            'lng': marker_lng,
                            'threat_type': threat_type,
                            'text': clean_text(ln)[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': f'directional_{direction_type}',
                            'count': 1
                        })
                    add_debug_log(f"Created {count} marker(s) for '{direction_type}': {city_norm.title()}", "directional")
                    continue

        # NEW: Pattern "на/через [city]" - combined "на" and "через"
        if re.search(r'на/через\s+[А-ЯІЇЄЁа-яіїєё]', ln, re.IGNORECASE):
            na_cherez_match = re.search(r'(\d+)[xх×]?\s*бпла\s+на/через\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)', ln, re.IGNORECASE)
            if na_cherez_match:
                count = int(na_cherez_match.group(1)) if na_cherez_match.group(1) else 1
                city_raw = na_cherez_match.group(2).strip()
                city_norm = normalize_city_name(city_raw)
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
                coords = CITY_COORDS.get(city_norm) or (SETTLEMENTS_INDEX.get(city_norm) if SETTLEMENTS_INDEX else None)

                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(ln)

                    # Create multiple tracks if count > 1
                    for i in range(count):
                        place_label = city_norm.title()
                        if count > 1:
                            place_label += f" #{i+1} (на/через)"
                        else:
                            place_label += " (на/через)"

                        # Add offset for multiple drones
                        marker_lat, marker_lng = lat, lng
                        if count > 1:
                            offset_distance = 0.03
                            marker_lat += offset_distance * i
                            marker_lng += offset_distance * i * 0.5

                        multi_city_tracks.append({
                            'id': f"{mid}_na_cherez_{len(multi_city_tracks)+1}",
                            'place': place_label,
                            'lat': marker_lat,
                            'lng': marker_lng,
                            'threat_type': threat_type,
                            'text': clean_text(ln)[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'na_cherez',
                            'count': 1
                        })
                    add_debug_log(f"Created {count} marker(s) for 'на/через': {city_norm.title()}", "na_cherez")
                    continue

        # NEW: Pattern "з ТОТ в напрямку [city]" - drones from occupied territory
        if 'з тот' in ln_lower or 'з tot' in ln_lower:
            tot_match = re.search(r'(\d+)[xх×]?\s*бпла\s+з\s+тот\s+(?:в\s+напрямку|на)\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)', ln, re.IGNORECASE)
            if tot_match:
                count = int(tot_match.group(1)) if tot_match.group(1) else 1
                city_raw = tot_match.group(2).strip()
                city_norm = normalize_city_name(city_raw)
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
                coords = CITY_COORDS.get(city_norm) or (SETTLEMENTS_INDEX.get(city_norm) if SETTLEMENTS_INDEX else None)

                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(ln)

                    # Create multiple tracks if count > 1
                    for i in range(count):
                        place_label = city_norm.title()
                        if count > 1:
                            place_label += f" #{i+1} (з ТОТ)"
                        else:
                            place_label += " (з ТОТ)"

                        # Add offset for multiple drones
                        marker_lat, marker_lng = lat, lng
                        if count > 1:
                            offset_distance = 0.03
                            marker_lat += offset_distance * i
                            marker_lng += offset_distance * i * 0.5

                        multi_city_tracks.append({
                            'id': f"{mid}_tot_{len(multi_city_tracks)+1}",
                            'place': place_label,
                            'lat': marker_lat,
                            'lng': marker_lng,
                            'threat_type': threat_type,
                            'text': clean_text(ln)[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'z_tot',
                            'count': 1
                        })
                    add_debug_log(f"Created {count} marker(s) for 'з ТОТ': {city_norm.title()}", "z_tot")
                    continue

        # Check if line has БпЛА or starts with a number (implying drones)
        has_bpla = 'бпла' in ln_lower
        starts_with_number = re.match(r'^\d+', ln.strip())
        has_direction_pattern = any(pattern in ln_lower for pattern in ['у напрямку', 'через', 'повз'])

        if (has_bpla or starts_with_number) and has_direction_pattern:
            target_cities = []

            # Pattern 1: "у напрямку [city]"
            naprym_pattern = r'у\s+напрямку\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)'
            naprym_matches = re.findall(naprym_pattern, ln, re.IGNORECASE)
            for city_raw in naprym_matches:
                target_cities.append(('у напрямку', city_raw.strip()))

            # Pattern 2: "через [city]"
            cherez_pattern = r'через\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)'
            cherez_matches = re.findall(cherez_pattern, ln, re.IGNORECASE)
            for city_raw in cherez_matches:
                target_cities.append(('через', city_raw.strip()))

            # Pattern 3: "повз [city]"
            povz_pattern = r'повз\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)'
            povz_matches = re.findall(povz_pattern, ln, re.IGNORECASE)
            for city_raw in povz_matches:
                target_cities.append(('повз', city_raw.strip()))

            # Process extracted target cities
            for direction_type, city_raw in target_cities:
                city_clean = city_raw.strip()
                city_norm = city_clean.lower()

                # Apply UA_CITY_NORMALIZE rules
                if city_norm in UA_CITY_NORMALIZE:
                    city_norm = UA_CITY_NORMALIZE[city_norm]

                # Try to get coordinates
                coords = CITY_COORDS.get(city_norm)
                if not coords and SETTLEMENTS_INDEX:
                    coords = SETTLEMENTS_INDEX.get(city_norm)
                if not coords:
                    coords = SETTLEMENT_FALLBACK.get(city_norm) if 'SETTLEMENT_FALLBACK' in globals() else None

                add_debug_log(f"Direction pattern '{direction_type}' found city: '{city_raw}' -> '{city_norm}' -> coords: {coords}", "direction_processing")

                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(ln)

                    # Create label showing direction
                    place_label = city_clean.title()
                    if direction_type == 'у напрямку':
                        place_label += " (напрямок)"
                    elif direction_type == 'через':
                        place_label += " (через)"
                    elif direction_type == 'повз':
                        place_label += " (повз)"

                    multi_city_tracks.append({
                        'id': f"{mid}_direction_{len(multi_city_tracks)+1}",
                        'place': place_label,
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': clean_text(ln)[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': f'direction_{direction_type.replace(" ", "_")}',
                        'count': 1
                    })
                    add_debug_log(f"Created direction marker: {place_label} ({direction_type})", "direction_processing")
                else:
                    add_debug_log(f"No coordinates found for direction target: '{city_raw}' (normalized: '{city_norm}')", "direction_processing")

            # If we found any target cities with valid coordinates, skip general UAV processing
            if any(coords for _, coords in [(city_norm, CITY_COORDS.get(UA_CITY_NORMALIZE.get(city_raw.strip().lower(), city_raw.strip().lower()))) for _, city_raw in target_cities]):
                add_debug_log(f"Direction processing complete, skipping general UAV activity for line: '{ln}'", "direction_processing")
                continue

        # NEW: Create markers for general UAV activity messages (without specific direction)
        if 'бпла' in ln_lower or 'безпілотник' in ln_lower or 'дрон' in ln_lower:
            add_debug_log(f"UAV activity detected in line: '{ln}', oblast_hdr: '{oblast_hdr}'", "uav_processing")

            # CRITICAL: Check if message has specific directional patterns - if yes, skip general marker
            # Let the main parser handle "курсом на", "напрямок на", "у напрямку", "на [місто]" etc.
            has_directional_pattern = any(pattern in ln_lower for pattern in [
                'курсом на', 'курс на', 'напрямок на', 'напрямку на',
                'ціль на', 'у напрямку', 'у бік', 'в бік', 'через', 'повз',
                'маневрує в районі', 'в районі', 'бпла на ', 'дрон на '
            ])

            # Check for emoji arrows BUT only if there's actual text (city name) after the arrow
            if '➡' in ln and not has_directional_pattern:
                # Extract text after arrow to see if there's a city name
                arrow_match = re.search(r'➡[️\s]*(.{3,})', ln)
                if arrow_match:
                    text_after_arrow = arrow_match.group(1).strip().strip('ㅤ️ ').strip()
                    # If there's meaningful text after arrow (not just punctuation/links), treat as directional
                    if text_after_arrow and len(text_after_arrow) > 1 and not text_after_arrow.startswith(('http', '[', '**', '➡')):
                        has_directional_pattern = True

            if has_directional_pattern:
                add_debug_log(f"SKIP general UAV marker - has directional pattern: '{ln}'", "uav_processing")
                # Don't create general marker - let main parser extract specific city
                continue

            # Check if we have a region and this is a UAV message
            if oblast_hdr:
                add_debug_log(f"Processing UAV with region context: '{oblast_hdr}'", "uav_processing")
                # Find the main city of the region to place the marker
                region_cities = {
                    'сумщина': 'суми',
                    'чернігівщина': 'чернігів',
                    'херсонщина': 'херсон',
                    'харківщина': 'харків',
                    'донеччина': 'краматорськ',  # safer than донецьк
                    'луганщина': 'сєвєродонецьк',
                    'запорожжя': 'запоріжжя',
                    'дніпропетровщина': 'дніпро',
                    'полтавщина': 'полтава',
                    'київщина': 'київ',
                    'львівщина': 'львів',
                    'івано-франківщина': 'івано-франківськ',
                    'тернопільщина': 'тернопіль',
                    'хмельниччина': 'хмельницький',
                    'рівненщина': 'рівне',
                    'волинщина': 'луцьк',
                    'житомирщина': 'житомир',
                    'вінниччина': 'вінниця',
                    'черкащина': 'черкаси',
                    'кіровоградщина': 'кропивницький',
                    'миколаївщина': 'миколаїв',
                    'одещина': 'одеса'
                }

                # Special coordinates for aviation threats over regions (e.g., aircraft over Black Sea for Odesa)
                region_aviation_coords = {
                    'одещина': (46.373528, 31.284023),  # Black Sea near Odesa for aviation threats
                    'одесщина': (46.373528, 31.284023),
                }

                region_city = region_cities.get(oblast_hdr)
                if region_city:
                    # Check if message refers to entire region rather than specific city
                    # Skip marker creation for some regional threats, but create for KAB/aviation bombs
                    genitive_form = oblast_hdr.replace('щина', 'щини')  # сумщина -> сумщини
                    dative_form = oblast_hdr.replace('щина', 'щині')    # сумщина -> сумщині
                    accusative_form = oblast_hdr + 'у'                  # сумщина -> сумщину

                    is_regional_threat = any(regional_ref in ln_lower for regional_ref in [
                        f'на {oblast_hdr}', f'{accusative_form}', f'{genitive_form}', f'{dative_form}',
                        f'для {genitive_form}', f'по {dative_form}'
                    ])

                    # For KAB/aviation bombs and aviation threats, always create marker even for regional threats
                    has_kab = any(kab_word in ln_lower for kab_word in ['каб', 'авіабомб', 'авиабомб'])
                    has_aviation_threat = any(avia_word in ln_lower for avia_word in [
                        'авіаційних засобів ураження', 'авіаційних засобів', 'застосування авіації',
                        'тактична авіація', 'тактичної авіації'
                    ])

                    if is_regional_threat and not has_kab and not has_aviation_threat:
                        add_debug_log(f"Skipping regional threat marker - affects entire region: {oblast_hdr} (found: {[ref for ref in [f'на {oblast_hdr}', accusative_form, genitive_form, dative_form] if ref in ln_lower]})", "multi_region")
                        continue

                    # Check if this is an aviation threat and use special coordinates if available
                    coords = None
                    if has_aviation_threat and oblast_hdr in region_aviation_coords:
                        coords = region_aviation_coords[oblast_hdr]
                        label = f"Авіація [{oblast_hdr.title()}]"
                        add_debug_log(f"Using aviation coordinates for {oblast_hdr}: {coords}", "aviation_region")

                    # Otherwise, try to find coordinates for the region's main city
                    if not coords:
                        base_city = normalize_city_name(region_city)
                        base_city = UA_CITY_NORMALIZE.get(base_city, base_city)
                        coords = CITY_COORDS.get(base_city) or (SETTLEMENTS_INDEX.get(base_city) if SETTLEMENTS_INDEX else None)
                        label = base_city.title()
                        label += f" [{oblast_hdr.title()}]"

                    if coords:
                        lat, lng = coords

                        # Determine threat type based on message content using classify function
                        threat_type, icon = classify(ln)
                        # Keep shahed as default for UAV if classify doesn't return anything specific
                        if not threat_type:
                            threat_type = 'shahed'

                        multi_city_tracks.append({
                            'id': f"{mid}_general_uav_{len(multi_city_tracks)+1}",
                            'place': label,
                            'lat': lat,
                            'lng': lng,
                            'threat_type': threat_type,
                            'text': clean_text(ln)[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'general_uav_activity',
                            'count': 1
                        })
                        add_debug_log(f"Created general UAV marker: {label} ({threat_type})", "multi_region")
                        add_debug_log(f"MARKER CREATION: oblast_hdr='{oblast_hdr}', region_city='{region_city}', coords=({lat}, {lng})", "marker_creation")
                        continue  # move to next line

        # NEW: Handle UAV messages without region but with city name
        ln_lower = ln.lower()
        if (not oblast_hdr) and ('бпла' in ln_lower or 'безпілотник' in ln_lower or 'дрон' in ln_lower or 'обстріл' in ln_lower or 'вибух' in ln_lower):
            # Try to extract city name from the message
            import re
            # Pattern for messages like "❗️ Синельникове — 1х БпЛА довкола" or "💥 Херсон — обстріл"
            city_match = re.search(r'[❗️⚠️🛸💥]*\s*([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ]{2,30}(?:ське|цьке|ський|ський район|ове|еве|ине|ино|івка|івськ|ськ|град|город)?)', ln)
            if city_match:
                city_name = city_match.group(1).strip()

                # Normalize city name
                base_city = normalize_city_name(city_name)
                base_city = UA_CITY_NORMALIZE.get(base_city, base_city)
                coords = CITY_COORDS.get(base_city) or (SETTLEMENTS_INDEX.get(base_city) if SETTLEMENTS_INDEX else None)

                if coords:
                    lat, lng = coords
                    label = base_city.title()

                    # Determine threat type based on message content using classify function
                    threat_type, icon = classify(ln)
                    # Keep shahed as default for UAV if classify doesn't return anything specific
                    if not threat_type:
                        threat_type = 'shahed'
                        icon = 'shahed3.webp'

                    multi_city_tracks.append({
                        'id': f"{mid}_city_threat_{len(multi_city_tracks)+1}",
                        'place': label,
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': clean_text(ln)[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': 'city_threat_activity',
                        'count': 1
                    })
                    add_debug_log(f"Created city threat marker: {label} ({threat_type})", "multi_region")
                    continue  # move to next line

        # --- NEW: БпЛА курсом на [city] pattern (e.g., "4х БпЛА курсом на Конотоп") ---
        # ВАЖЛИВО: Підтримка багатослівних назв міст (наприклад "Жовті Води")
        uav_course_city = None
        uav_course_count = 1
        # Pattern: "Nх БпЛА курсом на [city]" or "БпЛА курсом на [city]"
        # Захоплює назву міста до кінця рядка або до розділових знаків
        m_uav_course = re.search(r'(?:^|\b)(?:([0-9]+)[xх×]?\s*)?(?:бпла|шахед(?:и|ів)?|дрон(?:и)?)\s+курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]+?)(?:\s*$|[,\.\!\?;])', ln, re.IGNORECASE)
        if m_uav_course:
            if m_uav_course.group(1):
                try:
                    uav_course_count = int(m_uav_course.group(1))
                except:
                    uav_course_count = 1
            uav_course_city = m_uav_course.group(2).strip()

            add_debug_log(f"UAV course pattern found: {uav_course_count}x БпЛА курсом на '{uav_course_city}'", "multi_region")

        if uav_course_city:
            candidate_cities = extract_course_targets(uav_course_city)
            add_debug_log(f"extract_course_targets('{uav_course_city}') returned: {candidate_cities}", "multi_region")
            per_marker_count = uav_course_count if len(candidate_cities) <= 1 else 1
            created_course_markers = False
            for dest_city in candidate_cities or [uav_course_city]:
                if not dest_city:
                    continue
                base_uav = normalize_city_name(dest_city)
                base_uav = UA_CITY_NORMALIZE.get(base_uav, base_uav)
                coords_uav = CITY_COORDS.get(base_uav) or (SETTLEMENTS_INDEX.get(base_uav) if SETTLEMENTS_INDEX else None)
                add_debug_log(f"Geocoding '{dest_city}' -> normalized: '{base_uav}' -> coords: {coords_uav}", "multi_region")

                # Try region-specific lookup if oblast_hdr is set
                if not coords_uav and oblast_hdr:
                    combo_uav = f"{base_uav} {oblast_hdr}"
                    coords_uav = CITY_COORDS.get(combo_uav) or (SETTLEMENTS_INDEX.get(combo_uav) if SETTLEMENTS_INDEX else None)
                    add_debug_log(f"Trying region combo: '{combo_uav}' -> {coords_uav}", "multi_region")

                if not coords_uav:
                    add_debug_log(f"No coords found for '{dest_city}' (normalized: '{base_uav}', oblast: '{oblast_hdr}')", "multi_region")
                    continue
                created_course_markers = True
                lat, lng = coords_uav
                label = UA_CITY_NORMALIZE.get(base_uav, base_uav).title()
                if per_marker_count > 1:
                    label += f" ({per_marker_count}x)"
                if oblast_hdr and oblast_hdr not in label.lower():
                    label += f" [{oblast_hdr.title()}]"

                multi_city_tracks.append({
                    'id': f"{mid}_mc{len(multi_city_tracks)+1}",
                    'place': label,
                    'lat': lat,
                    'lng': lng,
                    'threat_type': 'shahed',
                    'text': clean_text(ln)[:500],
                    'date': date_str,
                    'channel': channel,
                    'marker_icon': 'shahed3.webp',
                    'source_match': 'multiline_uav_course',
                    'count': per_marker_count
                })
                add_debug_log(f"Created UAV course marker: {label}", "multi_region")
            if created_course_markers:
                continue  # move to next line
            else:
                base_uav = normalize_city_name(sanitize_course_destination(uav_course_city))
                add_debug_log(f"No coordinates found for UAV course city: '{uav_course_city}' (normalized: '{base_uav}')", "multi_region")

        # Continue processing other patterns even if UAV course didn't match
        # Don't skip the line completely

        # Пытаемся найти город и количество (например, "2х БпЛА курсом на Десну")
        import re
        # --- NEW: распознавание ракетных строк внутри многострочного блока ---
        # Примеры: "1 ракета на Холми", "2 ракети на Лубни", "3 ракеты на Лубни", "ракета на <місто>"
        rocket_city = None; rocket_count = 1
        mr = re.search(r'(?:^|\b)(?:([0-9]+)\s*)?(ракета|ракети|ракет)\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{2,40})', ln, re.IGNORECASE)
        if mr:
            if mr.group(1):
                try: rocket_count = int(mr.group(1))
                except: rocket_count = 1
            rocket_city = mr.group(3)
        if rocket_city:
            base_r = normalize_city_name(rocket_city)
            base_r = UA_CITY_NORMALIZE.get(base_r, base_r)
            coords_r = CITY_COORDS.get(base_r) or (SETTLEMENTS_INDEX.get(base_r) if SETTLEMENTS_INDEX else None)
            if not coords_r and oblast_hdr:
                combo_r = f"{base_r} {oblast_hdr}"
                coords_r = CITY_COORDS.get(combo_r) or (SETTLEMENTS_INDEX.get(combo_r) if SETTLEMENTS_INDEX else None)
            if coords_r:
                lat, lng = coords_r
                label = UA_CITY_NORMALIZE.get(base_r, base_r).title()
                if rocket_count > 1:
                    label += f" ({rocket_count})"
                if oblast_hdr and oblast_hdr not in label.lower():
                    label += f" [{oblast_hdr.title()}]"
                multi_city_tracks.append({
                    'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                    'threat_type': 'rszv', 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': 'icon_missile.svg', 'source_match': 'multiline_oblast_city_rocket', 'count': rocket_count
                })
                continue  # переходим к следующей строке (не пытаемся распознать как БпЛА)
        # --- NEW: группы крылатых ракет ("Група/Групи КР курсом на <город>") ---
        kr_city = None; kr_count = 1
        # Primary straightforward pattern for "Група/Групи КР курсом на <місто>"
        mkr = re.search(r'(?:^|\b)(?:([0-9]+)[xх×]?\s*)?груп[аи]\s+кр\b.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
        if not mkr:
            # Tolerant pattern allowing missing leading "г" or space glitches / lost letters
            mkr = re.search(r'(?:^|\b)(?:([0-9]+)[xх×]?\s*)?(?:г)?руп[аи]\s*(?:к)?р\b.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
        if not mkr and 'груп' in ln.lower() and 'курс' in ln.lower() and ' на ' in ln.lower():
            # Very loose fallback if 'КР' fragment dropped; capture after last 'на'
            after = ln.rsplit('на',1)[-1].strip()
            after = re.split(r'[,.!?:;]', after)[0].strip()
            if len(after) >= 3:
                class Dummy: pass
                mkr = Dummy(); mkr.group = lambda i: None if i==1 else after
        if mkr:
            try:
                log.info(f"KR_MATCH line='{ln}' groups={mkr.groups()}")
            except Exception:
                pass
            if mkr.group(1):
                try: kr_count = int(mkr.group(1))
                except: kr_count = 1
            kr_city = mkr.group(2)
        if kr_city:
            base_k = normalize_city_name(kr_city)
            base_k = UA_CITY_NORMALIZE.get(base_k, base_k)
            coords_k = CITY_COORDS.get(base_k) or (SETTLEMENTS_INDEX.get(base_k) if SETTLEMENTS_INDEX else None)
            if not coords_k and oblast_hdr:
                combo_k = f"{base_k} {oblast_hdr}"
                coords_k = CITY_COORDS.get(combo_k) or (SETTLEMENTS_INDEX.get(combo_k) if SETTLEMENTS_INDEX else None)
            if coords_k:
                lat, lng = coords_k
                label = UA_CITY_NORMALIZE.get(base_k, base_k).title()
                if kr_count > 1:
                    label += f" ({kr_count})"
                if oblast_hdr and oblast_hdr not in label.lower():
                    label += f" [{oblast_hdr.title()}]"
                multi_city_tracks.append({
                    'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                    'threat_type': 'raketa', 'text': ln[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': 'icon_balistic.svg', 'source_match': 'multiline_oblast_city_kr_group', 'count': kr_count
                })
                continue
        # Universal KR fallback (handles degraded OCR lines like '3х рупи  курсом на рилуки')
        low_ln = ln.lower()
        if ('курс' in low_ln and ' на ' in low_ln and ('груп' in low_ln or ' кр' in low_ln)):
            # Extract count if present at start or before 'груп'
            mcnt = re.search(r'^(\d+(?:-\d+)?)[xх×]?\s*', low_ln)
            count_guess = 1
            if mcnt:
                try: count_guess = int(mcnt.group(1))
                except: pass
            # Try after last 'на '
            parts = low_ln.rsplit(' на ', 1)
            if len(parts) == 2:
                cand = parts[1]
                cand = re.split(r'[\n,.!?:;]', cand)[0].strip()
                # strip residual non-letter chars
                cand_clean = re.sub(r"[^A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]", '', cand).strip()
                if len(cand_clean) >= 3:
                    base_f = normalize_city_name(cand_clean)
                    base_f = UA_CITY_NORMALIZE.get(base_f, base_f)
                    coords_f = CITY_COORDS.get(base_f) or (SETTLEMENTS_INDEX.get(base_f) if SETTLEMENTS_INDEX else None)
                    if not coords_f and oblast_hdr:
                        combo_f = f"{base_f} {oblast_hdr}"
                        coords_f = CITY_COORDS.get(combo_f) or (SETTLEMENTS_INDEX.get(combo_f) if SETTLEMENTS_INDEX else None)
                    # Fuzzy repair: if still not found, try restoring a potentially lost first letter
                    if not coords_f:
                        for pref in ['н','к','ч','п','г','с','в','б','д','м','т','л']:
                            test_base = pref + base_f
                            coords_try = CITY_COORDS.get(test_base) or (SETTLEMENTS_INDEX.get(test_base) if SETTLEMENTS_INDEX else None)
                            if not coords_try and oblast_hdr:
                                combo_try = f"{test_base} {oblast_hdr}"
                                coords_try = CITY_COORDS.get(combo_try) or (SETTLEMENTS_INDEX.get(combo_try) if SETTLEMENTS_INDEX else None)
                            if coords_try:
                                base_f = test_base
                                coords_f = coords_try
                                try: log.info(f"KR_FUZZ_REPAIR first_letter pref='{pref}' -> {base_f}")
                                except Exception: pass
                                break
                    if coords_f:
                        lat, lng = coords_f
                        label = UA_CITY_NORMALIZE.get(base_f, base_f).title()
                        if count_guess > 1:
                            label += f" ({count_guess})"
                        if oblast_hdr and oblast_hdr not in label.lower():
                            label += f" [{oblast_hdr.title()}]"
                        multi_city_tracks.append({
                            'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                            'threat_type': 'raketa', 'text': ln[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'icon_balistic.svg', 'source_match': 'multiline_oblast_city_kr_group_fallback2', 'count': count_guess
                        })
                        continue
        # Generic course fallback (any remaining 'курс' + ' на ' line not yet matched)
        if 'курс' in low_ln and ' на ' in low_ln and not any(tag in low_ln for tag in ['бпла','shahed']) and not any(mt['id'] == f"{mid}_mc{len(multi_city_tracks)+1}" for mt in multi_city_tracks):
            parts = low_ln.rsplit(' на ',1)
            if len(parts)==2:
                cand = re.split(r'[\n,.!?:;]', parts[1])[0].strip()
                cand = re.sub(r"[^A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]", '', cand)
                if len(cand) >= 3:
                    base_g = normalize_city_name(cand)
                    base_g = UA_CITY_NORMALIZE.get(base_g, base_g)
                    coords_g = CITY_COORDS.get(base_g) or (SETTLEMENTS_INDEX.get(base_g) if SETTLEMENTS_INDEX else None)
                    if not coords_g and oblast_hdr:
                        combo_g = f"{base_g} {oblast_hdr}"
                        coords_g = CITY_COORDS.get(combo_g) or (SETTLEMENTS_INDEX.get(combo_g) if SETTLEMENTS_INDEX else None)
                    # NEW: allow oblast center lookup if destination is a region (e.g. полтавщина / полтавщину)
                    if not coords_g and base_g in OBLAST_CENTERS:
                        coords_g = OBLAST_CENTERS[base_g]
                        try: log.info(f"GENERIC_COURSE_REGION dest='{base_g}' -> oblast center")
                        except Exception: pass
                    if not coords_g:
                        for pref in ['к','с','о','л','б','в','ж','т','я','у','р','н','п','г','ч']:
                            test = pref + base_g
                            coords_try = CITY_COORDS.get(test) or (SETTLEMENTS_INDEX.get(test) if SETTLEMENTS_INDEX else None)
                            if not coords_try and oblast_hdr:
                                combo_try = f"{test} {oblast_hdr}"
                                coords_try = CITY_COORDS.get(combo_try) or (SETTLEMENTS_INDEX.get(combo_try) if SETTLEMENTS_INDEX else None)
                            if coords_try:
                                base_g = test
                                coords_g = coords_try
                                try: log.info(f"GENERIC_FUZZ_CITY pref='{pref}' -> {base_g}")
                                except Exception: pass
                                break
                    if not coords_g:
                        for pref in ['н','к','ч','п','г','с','в','б','д','м','т','л']:
                            test_base = pref + base_g
                            coords_try = CITY_COORDS.get(test_base) or (SETTLEMENTS_INDEX.get(test_base) if SETTLEMENTS_INDEX else None)
                            if not coords_try and oblast_hdr:
                                combo_try = f"{test_base} {oblast_hdr}"
                                coords_try = CITY_COORDS.get(combo_try) or (SETTLEMENTS_INDEX.get(combo_try) if SETTLEMENTS_INDEX else None)
                            if coords_try:
                                base_g = test_base
                                coords_g = coords_try
                                try: log.info(f"GENERIC_COURSE_FUZZ pref='{pref}' -> {base_g}")
                                except Exception: pass
                                break
                    if coords_g:
                        lat, lng = coords_g
                        label = UA_CITY_NORMALIZE.get(base_g, base_g).title()
                        if oblast_hdr and oblast_hdr not in label.lower():
                            label += f" [{oblast_hdr.title()}]"
                        multi_city_tracks.append({
                            'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                            'threat_type': 'raketa', 'text': ln[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'icon_balistic.svg', 'source_match': 'multiline_oblast_city_course_generic', 'count': 1
                        })
                        continue
        # Fallback KR pattern if above failed but line mentions 'КР' and 'курс'
        if 'кр' in ln.lower() and 'курс' in ln.lower() and ' на ' in f" {ln.lower()} ":
            mkr2 = re.search(r'курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
            if mkr2:
                base_k2 = normalize_city_name(mkr2.group(1))
                base_k2 = UA_CITY_NORMALIZE.get(base_k2, base_k2)
                coords_k2 = CITY_COORDS.get(base_k2) or (SETTLEMENTS_INDEX.get(base_k2) if SETTLEMENTS_INDEX else None)
                if not coords_k2 and oblast_hdr:
                    combo_k2 = f"{base_k2} {oblast_hdr}"
                    coords_k2 = CITY_COORDS.get(combo_k2) or (SETTLEMENTS_INDEX.get(combo_k2) if SETTLEMENTS_INDEX else None)
                if not coords_k2:
                    for pref in ['н','к','ч','п','г','с','в','б','д','м','т','л']:
                        test_base = pref + base_k2
                        coords_try = CITY_COORDS.get(test_base) or (SETTLEMENTS_INDEX.get(test_base) if SETTLEMENTS_INDEX else None)
                        if not coords_try and oblast_hdr:
                            combo_try = f"{test_base} {oblast_hdr}"
                            coords_try = CITY_COORDS.get(combo_try) or (SETTLEMENTS_INDEX.get(combo_try) if SETTLEMENTS_INDEX else None)
                        if coords_try:
                            base_k2 = test_base
                            coords_k2 = coords_try
                            try: log.info(f"KR_FALLBACK_FUZZ pref='{pref}' -> {base_k2}")
                            except Exception: pass
                            break
                if coords_k2:
                    lat, lng = coords_k2
                    label = UA_CITY_NORMALIZE.get(base_k2, base_k2).title()
                    if oblast_hdr and oblast_hdr not in label.lower():
                        label += f" [{oblast_hdr.title()}]"
                    multi_city_tracks.append({
                        'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                        'threat_type': 'raketa', 'text': ln[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': 'icon_balistic.svg', 'source_match': 'multiline_oblast_city_kr_group_fallback', 'count': 1
                    })
                    continue
        # Разрешаем многословные названия (до 3 слов) до конца строки / знака препинания
        m = re.search(r'(\d+)[xх×]?\s*бпла.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
        if m:
            count = int(m.group(1))
            city = m.group(2)
        else:
            # Дополнительно поддерживаем строки вида "7х БпЛА повз <місто> ..." или "БпЛА повз <місто>"
            m2 = re.search(r'бпла.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
            if m2:
                count = 1
                city = m2.group(1)
            else:
                m3 = re.search(r'(\d+)[xх×]?\s*бпла.*?повз\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
                if m3:
                    count = int(m3.group(1))
                    city = m3.group(2)
                else:
                    m4 = re.search(r'бпла.*?повз\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
                    count = 1
                    city = m4.group(1) if m4 else None
        # --- NEW: Shahed lines inside multi-line block (e.g. '2 шахеди на Старий Салтів', '1 шахед на Мерефа / Борки') ---
        if not city:
            m_sha = re.search(r'^(?:([0-9]+)\s*[xх×]?\s*)?шахед(?:и|ів)?\s+на\s+(.+)$', ln.strip(), re.IGNORECASE)
            if m_sha:
                try:
                    scount = int(m_sha.group(1) or '1')
                except Exception:
                    scount = 1
                cities_part = m_sha.group(2)
                # Apply extract_course_targets to properly sanitize destinations (removes /район, etc.)
                raw_parts = extract_course_targets(cities_part)
                add_debug_log(f"Shahed pattern: '{cities_part}' -> sanitized targets: {raw_parts}", "multi_region")
                for ci in raw_parts:
                    c_raw = ci.strip().strip('.').strip()
                    if not c_raw or len(c_raw) < 2:
                        continue
                    cbase = normalize_city_name(c_raw)
                    cbase = UA_CITY_NORMALIZE.get(cbase, cbase)
                    coords_s = CITY_COORDS.get(cbase) or (SETTLEMENTS_INDEX.get(cbase) if SETTLEMENTS_INDEX else None)
                    add_debug_log(f"Shahed geocoding: '{ci}' -> normalized '{cbase}' -> coords {coords_s}", "multi_region")
                    if not coords_s and oblast_hdr:
                        combo_s = f"{cbase} {oblast_hdr}"
                        coords_s = CITY_COORDS.get(combo_s) or (SETTLEMENTS_INDEX.get(combo_s) if SETTLEMENTS_INDEX else None)
                    if not coords_s:
                        for pref in ['с','м','к','б','г','ч','н','п','т','в','л']:
                            test = pref + cbase
                            coords_try = CITY_COORDS.get(test) or (SETTLEMENTS_INDEX.get(test) if SETTLEMENTS_INDEX else None)
                            if not coords_try and oblast_hdr:
                                combo_try = f"{test} {oblast_hdr}"
                                coords_try = CITY_COORDS.get(combo_try) or (SETTLEMENTS_INDEX.get(combo_try) if SETTLEMENTS_INDEX else None)
                            if coords_try:
                                cbase = test; coords_s = coords_try; break
                    if not coords_s:
                        add_debug_log(f"No coords found for shahed dest '{ci}' (norm: '{cbase}')", "multi_region")
                        continue
                    lat, lng = coords_s
                    label = UA_CITY_NORMALIZE.get(cbase, cbase).title()
                    per_count = scount if len(raw_parts) == 1 else 1
                    if oblast_hdr and oblast_hdr not in label.lower():
                        label += f" [{oblast_hdr.title()}]"

                    # Create multiple tracks for multiple shaheds
                    tracks_to_create = max(1, per_count)
                    for i in range(tracks_to_create):
                        track_label = label
                        if tracks_to_create > 1:
                            track_label += f" #{i+1}"

                        # Add small coordinate offsets to prevent marker overlap
                        marker_lat = lat
                        marker_lng = lng
                        if tracks_to_create > 1:
                            # Create a chain pattern - drones one after another
                            offset_distance = 0.03  # ~3km offset between each drone
                            marker_lat += offset_distance * i
                            marker_lng += offset_distance * i * 0.5

                        multi_city_tracks.append({
                            'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': track_label, 'lat': marker_lat, 'lng': marker_lng,
                            'threat_type': 'shahed', 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'shahed3.webp', 'source_match': 'multiline_oblast_city_shahed', 'count': 1
                        })
                continue

        # --- NEW: Pattern "N на City1 N на City2..." (e.g. "Харківщина 1 на Вільшани 1 на Kov'яги 1 на Бірки") ---
        # Handles multiple "number + на + city" sequences in a single line WITHOUT repeating "БпЛА"
        # IMPORTANT: Pattern supports mixed Cyrillic/Latin city names (e.g. "Kov'яги")
        if re.search(r'(\d+)\s+на\s+[A-ZА-ЯІЇЄa-zа-яіїєґ\'\-]+', ln, re.IGNORECASE):
            # Find all "N на City" patterns in the line (supports mixed Cyrillic/Latin)
            multi_na_pattern = re.findall(r'(\d+)\s+на\s+([A-ZА-ЯІЇЄa-zа-яіїєґ\'\-]+(?:/[A-ZА-ЯІЇЄa-zа-яіїєґ\'\-]+)?)', ln, re.IGNORECASE)

            if len(multi_na_pattern) > 1:  # Multiple "N на City" patterns found - this is our case!
                add_debug_log(f"MULTI-NA pattern found {len(multi_na_pattern)} cities in line: '{ln}'", "multi_na")
                add_debug_log(f"MULTI-NA current region header (oblast_hdr): '{oblast_hdr}'", "multi_na")

                # Regional overrides for cities with duplicate names in different oblasts
                REGIONAL_CITY_COORDS = {
                    'харківщина': {
                        'вільшани': (50.177, 35.398),  # Вільшани, Харківська обл., Богодухівський район
                        'ковяги': (49.75, 36.12),       # Ков'яги, Харківська обл.
                        'березівка': (49.583, 36.450),  # Березівка, Харківська обл.
                    },
                    # Add more regional overrides as needed
                }

                for count_str, city_raw in multi_na_pattern:
                    count = int(count_str) if count_str.isdigit() else 1
                    city_name = city_raw.strip()

                    # Normalize city name (handle Latin/Cyrillic mix)
                    city_norm = normalize_city_name(city_name)
                    city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)

                    # TRY 1: Regional override if oblast_hdr is set (e.g. "Харківщина:")
                    coords = None
                    if oblast_hdr and oblast_hdr in REGIONAL_CITY_COORDS:
                        region_coords = REGIONAL_CITY_COORDS[oblast_hdr]
                        coords = region_coords.get(city_norm)
                        if coords:
                            add_debug_log(f"  Multi-NA city: '{city_name}' ({count}x) -> norm: '{city_norm}' -> REGIONAL OVERRIDE coords: {coords} (oblast: {oblast_hdr})", "multi_na")

                    # TRY 2: Default database lookup if no regional override
                    if not coords:
                        coords = CITY_COORDS.get(city_norm)
                        if coords:
                            add_debug_log(f"  Multi-NA city: '{city_name}' ({count}x) -> norm: '{city_norm}' -> DATABASE coords: {coords}", "multi_na")

                    # TRY 3: Settlements index fallback
                    if not coords and SETTLEMENTS_INDEX:
                        coords = SETTLEMENTS_INDEX.get(city_norm)
                        if coords:
                            add_debug_log(f"  Multi-NA city: '{city_name}' ({count}x) -> norm: '{city_norm}' -> SETTLEMENTS coords: {coords}", "multi_na")

                    if not coords:
                        add_debug_log(f"  WARNING: No coordinates for '{city_name}' (normalized: '{city_norm}', oblast: {oblast_hdr})", "multi_na")
                        continue

                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(ln)

                        # Create separate markers for each count
                        for i in range(count):
                            place_label = city_norm.title()
                            if count > 1:
                                place_label += f" #{i+1}"

                            # Add offset for multiple drones at same location
                            marker_lat, marker_lng = lat, lng
                            if count > 1:
                                offset_distance = 0.03  # ~3km offset
                                marker_lat += offset_distance * i
                                marker_lng += offset_distance * i * 0.5

                            multi_city_tracks.append({
                                'id': f"{mid}_multi_na_{len(multi_city_tracks)+1}",
                                'place': place_label,
                                'lat': marker_lat,
                                'lng': marker_lng,
                                'threat_type': threat_type,
                                'text': clean_text(ln)[:500],
                                'date': date_str,
                                'channel': channel,
                                'marker_icon': icon,
                                'source_match': 'multi_na_pattern',
                                'count': 1
                            })
                        add_debug_log(f"  Created {count} marker(s) for '{city_norm.title()}'", "multi_na")
                    else:
                        add_debug_log(f"  WARNING: No coordinates for '{city_name}' (normalized: '{city_norm}')", "multi_na")

                add_debug_log(f"Multi-NA pattern processed: {len(multi_city_tracks)} total markers created", "multi_na")
                continue  # Skip further processing of this line

        # --- NEW: Simple "X БпЛА на <city>" pattern (e.g. '1 БпЛА на Козелець', '2 БпЛА на Куликівку') ---
        # Also handle "Ціль на <city>" pattern for missile/rocket targets
        if not city:
            print(f"DEBUG: Checking simple БпЛА/Ціль pattern for line: '{ln}'")

            # Pattern 1: "Ціль на <city>" - rocket/missile target
            m_target = re.search(r'ціль\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=\s|$|[,\.\!\?;\[])', ln, re.IGNORECASE)
            if m_target:
                city = m_target.group(1).strip()
                count = 1  # Default count for target
                print(f"DEBUG: Found 'Ціль на' pattern - city: '{city}'")
            # Pattern 2: "X БпЛА на <city>"
            elif re.search(r'(\d+)\s+бпла\s+на\s+', ln, re.IGNORECASE):
                m_simple = re.search(r'(\d+)\s+бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
                if m_simple:
                    try:
                        count = int(m_simple.group(1))
                    except Exception:
                        count = 1
                    city = m_simple.group(2).strip()
                    print(f"DEBUG: Found simple БпЛА pattern - count: {count}, city: '{city}'")
            # Pattern 3: "БпЛА на <city>" without count
            elif re.search(r'бпла\s+на\s+[A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,}', ln, re.IGNORECASE):
                # Fallback for "БпЛА на <city>" without count - handle cities with parentheses like "Кривий ріг (Дніпропетровщина)"
                m_simple_no_count = re.search(r'бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,}?)(?:\s*\([^)]*\))?(?=\s*$|[,\.\!\?;])', ln, re.IGNORECASE)
                if m_simple_no_count:
                    count = 1
                    city = m_simple_no_count.group(1).strip()
                    print(f"DEBUG: Found simple БпЛА pattern (no count) - city: '{city}'")

        # --- NEW: Handle "X у напрямку City1, City2" pattern (e.g. "4 у напрямку Карлівки, Полтави") ---
        if not city:
            print(f"DEBUG: Checking 'X у напрямку' pattern for line: '{ln}'")
            m_naprymku = re.search(r'(\d+)\s+у\s+напрямку\s+([А-ЯІЇЄЁа-яіїєё\'\-\s,]{5,})(?=\s*$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_naprymku:
                try:
                    count = int(m_naprymku.group(1))
                except Exception:
                    count = 1
                cities_raw = m_naprymku.group(2).strip()
                print(f"DEBUG: Found 'у напрямку' pattern - count: {count}, cities: '{cities_raw}'")

                # Split cities by comma
                cities_list = [c.strip() for c in cities_raw.split(',') if c.strip()]
                for city_name in cities_list:
                    base = normalize_city_name(city_name)
                    base = UA_CITY_NORMALIZE.get(base, base)
                    coords = CITY_COORDS.get(base)

                    # If not found, try to handle declensions (ending with -и, -ми, -у, etc)
                    if not coords and base:
                        if base.endswith('і') or base.endswith('и'):
                            base_nom = base[:-1] + 'а'  # карлівки -> карлівка
                            coords = CITY_COORDS.get(base_nom)
                        elif base.endswith('у'):
                            base_nom = base[:-1] + 'а'  # полтаву -> полтава
                            coords = CITY_COORDS.get(base_nom)
                        elif base.endswith('ми'):
                            base_nom = base[:-2] + 'а'  # київми -> києва -> doesn't work, try other variants
                            coords = CITY_COORDS.get(base_nom)

                    if coords:
                        lat, lng = coords
                        multi_city_tracks.append({
                            'id': f"{mid}_naprymku{len(multi_city_tracks)+1}", 'place': city_name.title(), 'lat': lat, 'lng': lng,
                            'threat_type': 'shahed', 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'shahed3.webp', 'source_match': 'naprymku_pattern', 'count': count
                        })
                        print(f"DEBUG: Added marker for '{city_name}' at {lat}, {lng}")
                if multi_city_tracks:
                    continue

        # --- NEW: Handle "X БпЛА City1 / City2" pattern (e.g. "2х БпЛА Гнідин / Бориспіль") ---
        if not city:
            print(f"DEBUG: Checking БпЛА city/city pattern for line: '{ln}'")
            m_cities = re.search(r'(\d+)х?\s+бпла\s+(?:на\s+)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)\s*/\s*([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_cities:
                try:
                    count = int(m_cities.group(1))
                except Exception:
                    count = 1
                city1 = m_cities.group(2).strip()
                city2 = m_cities.group(3).strip()
                print(f"DEBUG: Found БпЛА city/city pattern - count: {count}, cities: '{city1}' / '{city2}'")

                # Process both cities separately
                for city_name in [city1, city2]:
                    base = normalize_city_name(city_name)
                    base = UA_CITY_NORMALIZE.get(base, base)
                    coords = CITY_COORDS.get(base)
                    if coords:
                        print(f"DEBUG: Creating БпЛА track for {city_name} at {coords}")
                        multi_city_tracks.append({
                            'lat': coords[0],
                            'lon': coords[1],
                            'name': city_name,
                            'type': 'БпЛА',
                            'time': date_str,
                            'id': mid,
                            'message': text[:100] + ('...' if len(text) > 100 else ''),
                            'channel': channel
                        })
                    else:
                        print(f"DEBUG: No coordinates found for {city_name} (base: {base})")

                # Set city to processed to prevent further processing
                city = f"{city1} / {city2}"
        # --- NEW: Handle "між X та Y" pattern (e.g. "між Корюківкою та Меною") ---
        if not city:
            m_between = re.search(r'між\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)\s+та\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_between:
                city1 = m_between.group(1).strip()
                city2 = m_between.group(2).strip()
                # Try to geocode both cities and place marker at midpoint
                base1 = normalize_city_name(city1)
                base2 = normalize_city_name(city2)
                base1 = UA_CITY_NORMALIZE.get(base1, base1)
                base2 = UA_CITY_NORMALIZE.get(base2, base2)

                coords1 = CITY_COORDS.get(base1) or (SETTLEMENTS_INDEX.get(base1) if SETTLEMENTS_INDEX else None)
                coords2 = CITY_COORDS.get(base2) or (SETTLEMENTS_INDEX.get(base2) if SETTLEMENTS_INDEX else None)

                if not coords1 and oblast_hdr:
                    combo1 = f"{base1} {oblast_hdr}"
                    coords1 = CITY_COORDS.get(combo1) or (SETTLEMENTS_INDEX.get(combo1) if SETTLEMENTS_INDEX else None)
                if not coords2 and oblast_hdr:
                    combo2 = f"{base2} {oblast_hdr}"
                    coords2 = CITY_COORDS.get(combo2) or (SETTLEMENTS_INDEX.get(combo2) if SETTLEMENTS_INDEX else None)

                if coords1 and coords2:
                    # Place marker at midpoint
                    lat = (coords1[0] + coords2[0]) / 2
                    lng = (coords1[1] + coords2[1]) / 2
                    label = f"Між {base1.title()} та {base2.title()}"
                    if oblast_hdr and oblast_hdr not in label.lower():
                        label += f" [{oblast_hdr.title()}]"

                    # Extract count from beginning of line if present
                    count_match = re.search(r'^(\d+(?:-\d+)?)\s*бпла', ln, re.IGNORECASE)
                    count = int(count_match.group(1)) if count_match else 1

                    multi_city_tracks.append({
                        'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                        'threat_type': 'shahed', 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': 'shahed3.webp', 'source_match': 'multiline_oblast_city_between', 'count': count
                    })
                    continue

        # --- NEW: Handle "неподалік X" pattern (e.g. "неподалік Ічні") ---
        if not city:
            m_near = re.search(r'неподалік\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_near:
                city = m_near.group(1).strip()
                # Extract count from beginning of line if present
                count_match = re.search(r'^(\d+(?:-\d+)?)\s*бпла', ln, re.IGNORECASE)
                count = int(count_match.group(1)) if count_match else 1

        # --- NEW: Handle "в районі X" pattern (e.g. "в районі Конотопу") ---
        if not city:
            m_area = re.search(r'в\s+районі\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_area:
                city = m_area.group(1).strip()
                # Extract count from beginning of line if present
                count_match = re.search(r'^(\d+(?:-\d+)?)\s*бпла', ln, re.IGNORECASE)
                count = int(count_match.group(1)) if count_match else 1

        if city:
            print(f"DEBUG: Processing city '{city}' with oblast_hdr '{oblast_hdr}' and count {count}")
            base = normalize_city_name(city)
            print(f"DEBUG: Normalized city name: '{base}'")
            # Простейшая нормализация винительного падежа -> именительный ("велику димерку" -> "велика димерка")
            if base.endswith('у димерку') and 'велик' in base:
                base = 'велика димерка'
            # Общая морфология: заменяем окончания "ку"->"ка", "ю"->"я" для последнего слова
            if base.endswith('ку '):
                base = base[:-3] + 'ка '
            elif base.endswith('ку'):
                base = base[:-2] + 'ка'
            if base.endswith('ю '):
                base = base[:-3] + 'я '
            elif base.endswith('ю'):
                base = base[:-1] + 'я'
            # Приводим многословные формы через UA_CITY_NORMALIZE если есть
            base = UA_CITY_NORMALIZE.get(base, base)
            if base == 'троєщину':
                base = 'троєщина'

            # Use enhanced coordinate lookup with Nominatim fallback and region context
            coords = get_coordinates_enhanced(base, region=oblast_hdr, context="БпЛА курсом на")

            print(f"DEBUG: Enhanced lookup for '{base}'" + (f" in {oblast_hdr}" if oblast_hdr else "") + f": {coords}")

            if not coords and oblast_hdr:
                # Legacy combo lookup as fallback
                combo = f"{base} {oblast_hdr}"
                print(f"DEBUG: Trying legacy combo lookup for '{combo}'")
                coords = CITY_COORDS.get(combo)
                if not coords and SETTLEMENTS_INDEX:
                    coords = SETTLEMENTS_INDEX.get(combo)
                print(f"DEBUG: Combo lookup result: {coords}")
            if not coords:
                print(f"DEBUG: Calling ensure_city_coords_with_message_context for '{base}' with oblast context '{oblast_hdr}'")
                # Try with full message context first to get oblast-specific coordinates
                context_message = f"{oblast_hdr} {original_text if 'original_text' in locals() else text}"
                coords = ensure_city_coords_with_message_context(base, context_message)
                if not coords:
                    print(f"DEBUG: Context-based lookup failed, trying standard ensure_city_coords for '{base}'")
                    coords = ensure_city_coords(base, context=text)
                print(f"DEBUG: ensure_city_coords result: {coords}")
            if coords:
                print(f"DEBUG: Found coords {coords} for city '{base}', creating track")
                # Handle both 2-tuple (lat, lng) and 3-tuple (lat, lng, approx_flag) returns
                if len(coords) == 3:
                    lat, lng, approx_flag = coords
                else:
                    lat, lng = coords
                    approx_flag = False
                threat_type, icon = 'shahed', 'shahed3.webp'
                label = UA_CITY_NORMALIZE.get(base, base).title()
                if oblast_hdr and oblast_hdr not in label.lower():
                    label += f" [{oblast_hdr.title()}]"

                # Create multiple tracks for multiple drones instead of one track with count
                tracks_to_create = max(1, count)
                for i in range(tracks_to_create):
                    track_label = label
                    if tracks_to_create > 1:
                        track_label += f" #{i+1}"

                    # Add small coordinate offsets to prevent marker overlap
                    marker_lat = lat
                    marker_lng = lng
                    if tracks_to_create > 1:
                        # Create a chain pattern - drones one after another
                        offset_distance = 0.03  # ~3km offset between each drone
                        marker_lat += offset_distance * i
                        marker_lng += offset_distance * i * 0.5

                    print(f"DEBUG: Creating track {i+1}/{tracks_to_create} with label '{track_label}' at {marker_lat}, {marker_lng}")
                    multi_city_tracks.append({
                        'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': track_label, 'lat': marker_lat, 'lng': marker_lng,
                        'threat_type': threat_type, 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'multiline_oblast_city', 'count': 1
                    })
            else:
                print(f"DEBUG: No coordinates found for city '{base}'")
    print(f"DEBUG: Multi-city tracks processing complete. Found {len(multi_city_tracks)} tracks")
    add_debug_log(f"Multi-region processing complete: {len(multi_city_tracks)} markers from {processed_lines_count} lines", "multi_region")

    if multi_city_tracks:
        print(f"DEBUG: Returning {len(multi_city_tracks)} multi-city tracks")
        add_debug_log(f"Returning {len(multi_city_tracks)} multi-city tracks: {[t['place'] for t in multi_city_tracks]}", "multi_region")
        # Combine with priority result if available
        if 'priority_result' in locals() and priority_result:
            combined_result = priority_result + multi_city_tracks
            add_debug_log(f"Combined priority result ({len(priority_result)}) with multi-city tracks ({len(multi_city_tracks)}) = {len(combined_result)} total", "priority_combine")
            return combined_result
        return multi_city_tracks
    else:
        # If no multi-city tracks were created, continue with main parsing logic
        # This allows regional direction messages like "БпЛА на сході Сумщини" to be processed by regional parser
        add_debug_log("No multi-city tracks created, continuing to main parser", "multi_region_fallback")
    # --- Detect and split multiple city targets in one message ---
    import re
    multi_city_tracks = []
    # 1. Patterns: 'на <город>', 'повз <город>'
    # Захватываем одно- или многословные названия после "на" / "повз" до знака препинания / конца строки
    city_patterns = re.findall(r'(?:на|повз)\s+([A-Za-zА-Яа-яЇїІіЄєҐґʼ`’\-\s]{3,40}?)(?=[,\.\n;:!\?]|$)', text.lower())
    # 2. Patterns: перечисление через запятую или слэш (например: "шишаки, глобине, ромодан" или "малин/гранітне")
    # Только если в сообщении нет явного одного города в начале
    city_enumerations = []
    for part in re.split(r'[\n\|]', text.lower()):
        # ищем перечисления через запятую
        if ',' in part:
            city_enumerations += [c.strip() for c in part.split(',') if len(c.strip()) > 2]
        # ищем перечисления через слэш
        if '/' in part:
            city_enumerations += [c.strip() for c in part.split('/') if len(c.strip()) > 2]
    # Объединяем все найденные города
    all_cities = set(city_patterns + city_enumerations)
    # Фильтруем по наличию в CITY_COORDS (или SETTLEMENTS_INDEX)
    found_cities = []
    def _resolve_city_candidate(raw: str):
        cand = raw.strip().lower()
        cand = re.sub(r'["“”«»\(\)\[\]]','', cand)

        # CRITICAL: Remove trailing geographic qualifiers (e.g., "Канів по межі з Київщиною" → "Канів")
        trailing_patterns = [
            r'\s+по\s+межі\s+з\s+.*$',
            r'\s+на\s+межі\s+з\s+.*$',
            r'\s+в\s+районі\s+.*$',
            r'\s+біля\s+кордону\s+.*$',
            r'\s+на\s+околицях\s+.*$',
            r'\s+поблизу\s+.*$',
        ]
        for pattern in trailing_patterns:
            cand = re.sub(pattern, '', cand).strip()

        cand = re.sub(r'\s+',' ', cand)
        # Пробуем от длинного к короткому (до 3 слов достаточно для наших случаев)
        words = cand.split()
        if not words:
            return None
        for ln in range(min(3, len(words)), 0, -1):
            sub = ' '.join(words[:ln])
            base = UA_CITY_NORMALIZE.get(sub, sub)
            if base in CITY_COORDS or (SETTLEMENTS_INDEX and base in SETTLEMENTS_INDEX):
                return base
            # Морфология окончания винительного/родительного последнего слова
            sub_mod = re.sub(r'у\b','а', sub)
            sub_mod = re.sub(r'ю\b','я', sub_mod)
            sub_mod = re.sub(r'ої\b','а', sub_mod)
            base2 = UA_CITY_NORMALIZE.get(sub_mod, sub_mod)
            if base2 in CITY_COORDS or (SETTLEMENTS_INDEX and base2 in SETTLEMENTS_INDEX):
                return base2
        return UA_CITY_NORMALIZE.get(cand, cand)
    for city in all_cities:
        norm = _resolve_city_candidate(city)
        if not norm:
            continue
        coords = CITY_COORDS.get(norm)
        if not coords and SETTLEMENTS_INDEX:
            coords = SETTLEMENTS_INDEX.get(norm)
        if coords:
            found_cities.append((norm, coords))
    # Если найдено 2 и более города — создаём отдельный маркер для каждого
    if len(found_cities) >= 2:
        threat_type, icon = 'shahed', 'shahed3.webp'  # можно доработать auto-classify

        # Extract course information for Shahed threats
        course_info = None
        if threat_type == 'shahed':
            course_info = extract_shahed_course_info(original_text)

        for idx, (city, (lat, lng)) in enumerate(found_cities, 1):
            track = {
                'id': f"{mid}_mc{idx}", 'place': city.title(), 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': clean_text(original_text)[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'multi_city_auto'
            }

            # Add course information if available
            if course_info:
                track.update({
                    'course_source': course_info.get('source_city'),
                    'course_target': course_info.get('target_city'),
                    'course_direction': course_info.get('course_direction'),
                    'course_type': course_info.get('course_type')
                })

            multi_city_tracks.append(track)
        if multi_city_tracks:
            return multi_city_tracks
    """Extract coordinates or try simple city geocoding (lightweight)."""
    original_text = text
    # ---------------- Global region (oblast) hint detection for universal settlement binding ----------------
    region_hint_global = None
    try:
        low_rt = original_text.lower()
        for obl_name in OBLAST_CENTERS.keys():
            if obl_name in low_rt:
                region_hint_global = obl_name  # first hit
                break
    except Exception:
        region_hint_global = None
    # Additional: detect section headers like "Сумщина:" "Полтавщина:" at line starts to set region hint
    if not region_hint_global:
        for line in original_text.split('\n'):
            l = line.strip().lower()
            if l.endswith(':'):
                base = l[:-1]
                if base in OBLAST_CENTERS:
                    region_hint_global = base
                    break

    def region_enhanced_coords(base_name: str, region_hint_override: str = None):
        """Resolve coordinates for a settlement name by weighted order:
        0) FIRST: Local oblast-aware lookup (UKRAINE_SETTLEMENTS_BY_OBLAST) - MOST RELIABLE
        1) External geocode (region-qualified, then plain)
        2) Exact local datasets (CITY_COORDS, SETTLEMENTS_INDEX)
        3) Fuzzy approximate local match (Levenshtein-like via difflib)
        """
        if not base_name:
            return None
        name_norm = UA_CITY_NORMALIZE.get(base_name, base_name).strip().lower()
        
        # --- 0. PRIORITY: Local oblast-aware lookup (handles duplicate city names!) ---
        region_for_query = region_hint_override or region_hint_global
        if region_for_query and UKRAINE_SETTLEMENTS_BY_OBLAST:
            # Normalize region name to match database format
            region_norm = region_for_query.lower().strip()
            # Map regional names to adjective forms
            region_to_adj = {
                'харківщина': 'харківська', 'сумщина': 'сумська', 'полтавщина': 'полтавська',
                'чернігівщина': 'чернігівська', 'київщина': 'київська', 'одещина': 'одеська',
                'миколаївщина': 'миколаївська', 'херсонщина': 'херсонська', 'запорізька': 'запорізька',
                'дніпропетровщина': 'дніпропетровська', 'донецька': 'донецька', 'луганська': 'луганська',
                'черкащина': 'черкаська', 'вінниччина': 'вінницька', 'житомирщина': 'житомирська',
                'рівненщина': 'рівненська', 'волинь': 'волинська', 'львівщина': 'львівська',
                'тернопільщина': 'тернопільська', 'хмельниччина': 'хмельницька',
                'івано-франківщина': 'івано-франківська', 'закарпаття': 'закарпатська',
                'чернівецька': 'чернівецька', 'кіровоградщина': 'кіровоградська',
            }
            if region_norm in region_to_adj:
                region_norm = region_to_adj[region_norm]
            
            # Try looking up (city, oblast) tuple
            lookup_key = (name_norm, region_norm)
            if lookup_key in UKRAINE_SETTLEMENTS_BY_OBLAST:
                coords = UKRAINE_SETTLEMENTS_BY_OBLAST[lookup_key]
                log.info(f"region_enhanced_coords: Found '{name_norm}' in '{region_norm}' oblast: {coords}")
                return coords
        
        # --- 1. Remote geocode ---
        if region_for_query:
            canon = REGION_GEOCODE_CANON.get(region_for_query)
            if canon:
                region_for_query = canon
        # Region-qualified
        if OPENCAGE_API_KEY and region_for_query:
            try:
                combo = f"{name_norm} {region_for_query}".replace('  ', ' ').strip()
                c = geocode_opencage(combo)
                if c and 43.0 <= c[0] <= 53.8 and 20.0 <= c[1] <= 42.0:
                    return c
            except Exception:
                pass
        # Plain name remote
        if OPENCAGE_API_KEY:
            try:
                c = geocode_opencage(name_norm)
                if c and 43.0 <= c[0] <= 53.8 and 20.0 <= c[1] <= 42.0:
                    return c
            except Exception:
                pass
        # --- 2. Exact local datasets ---
        coord = CITY_COORDS.get(name_norm)
        if not coord and SETTLEMENTS_INDEX:
            coord = SETTLEMENTS_INDEX.get(name_norm)
        # Explicit settlement fallback (manual corrections for mis-geocoded small places)
        if not coord:
            coord = SETTLEMENT_FALLBACK.get(name_norm)
        if coord:
            return coord
        # --- 3. Fuzzy approximate search (only if not found) ---
        try:
            if SETTLEMENTS_INDEX:
                import difflib
                # Choose candidate list limited for performance
                names = list(SETTLEMENTS_INDEX.keys())
                # High cutoff to avoid bad matches
                best = difflib.get_close_matches(name_norm, names, n=1, cutoff=0.86)
                if best:
                    b = best[0]
                    return SETTLEMENTS_INDEX.get(b)
        except Exception:
            pass
        return None
    # ---- Fundraising / donation solicitation handling ----
    # Previous behavior: fully suppressed entire message if donation links found (blocked napramok multi-line threat posts with footer links)
    # New behavior: If donation lines present BUT the message also contains threat indicators, strip only the donation lines and continue parsing.
    low_full = original_text.lower()
    DONATION_KEYS = [
        'монобанк','monobank','mono.bank','privat24','приват24','реквізит','реквизит','донат','donat','iban','paypal','patreon','send.monobank.ua','jar/','банка: http','карта(','карта(monobank)','карта(privat24)','підтримати канал'
    ]
    donation_present = any(k in low_full for k in DONATION_KEYS) or re.search(r'\b\d{16}\b', low_full)
    # Pure subscription / invite promo suppression (no threats, mostly t.me invite links + short call to action)
    if not any(w in low_full for w in ['бпла','дрон','шахед','shahed','ракета','каб','артил','града','смерч','ураган','mlrs','iskander','s-300','s300','border','trivoga','тривога','повітряна тривога']) and \
       low_full.count('t.me/') >= 1 and len(re.sub(r'\s+',' ', low_full)) < 260 and \
       len([ln for ln in low_full.splitlines() if ln.strip()]) <= 6:
        if all(tok not in low_full for tok in ['загроза','укритт','alert','launch','start','вильот','вихід','пуски','air','strike']):
            return None
    if donation_present:
        # Threat keyword heuristic (lightweight; don't rely on later THREAT_KEYS definition yet)
        threat_tokens = ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile','iskander','s-300','s300','каб','артил','града','смерч','ураган','mlrs']
        has_threat_word = any(tok in low_full for tok in threat_tokens)
        if has_threat_word:
            # НЕ удаляем строки с донатами если есть угрозы - просто продолжаем парсинг
            log.debug(f"mid={mid} donation_present but has_threats - continuing without stripping")
            # text остается без изменений
        else:
            return [{
                'id': str(mid), 'place': None, 'lat': None, 'lng': None,
                'threat_type': None, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'list_only': True, 'suppress': True, 'suppress_reason': 'donation_only'
            }]
    # --- Universal link stripping (any clickable invite / http) ---
    def _strip_links(s: str) -> str:
        if not s:
            return s
        # markdown links [text](url)
        # handle bold inside brackets [**Text**](url) by stripping ** first
        s = re.sub(r'\*\*','', s)
        s = re.sub(r'\[([^\]]{0,80})\]\((https?://|t\.me/)[^\)]+\)', lambda m: (m.group(1) or '').strip(), s, flags=re.IGNORECASE)
        # bare urls
        s = re.sub(r'(https?://\S+|t\.me/\S+)', '', s, flags=re.IGNORECASE)
        # collapse whitespace and drop empty lines
        cleaned = []
        for ln in s.splitlines():
            ln2 = ln.strip()
            if not ln2:
                continue
            # pure decoration (arrows, bullets) or subscribe call to action lines
            if re.fullmatch(r'[>➡→\-\s·•]*', ln2):
                continue
            # remove any line that is just a subscribe CTA or starts with arrow+subscribe
            if re.search(r'(підписатись|підписатися|підписатися|подписаться|подпишись|subscribe)', ln2, re.IGNORECASE):
                continue
            # remove arrow+subscribe pattern specifically
            if re.search(r'[➡→>]\s*підписатися', ln2, re.IGNORECASE):
                continue
            cleaned.append(ln2)
        return '\n'.join(cleaned)
    new_text = _strip_links(text)
    if new_text != text:
        text = new_text
    new_orig = _strip_links(original_text)
    if new_orig != original_text:
        original_text = new_orig
    # --- Explicit launch site detection (multi-line). Create one marker per detected launch location.
    low_work = text.lower()
    # --- Single-line explicit RF launch: "пуск <place> (рф)" ---
    if 'пуск' in low_work and 'рф' in low_work:
        try:
            m = re.search(r'пуск(?:и)?\s+([A-Za-zА-Яа-яЇїІіЄєҐґ0-9\-–—\s]{2,60})', low_work)
            if m:
                raw_place = m.group(1)
                raw_place = raw_place.split('(')[0].split(',')[0].strip()
                raw_place = raw_place.replace('–', '-').replace('—', '-')
                raw_place = raw_place.replace('ё', 'е')
                raw_place = re.sub(r'\bрф\b', '', raw_place).strip()
                raw_place = re.sub(r'\bрайон(у|а)?\b', '', raw_place).strip()
                raw_place = re.sub(r'\bр-н\b', '', raw_place).strip()
                raw_place = re.sub(r'\s+', ' ', raw_place)
                variants = {
                    raw_place,
                    raw_place.replace(' ', '-'),
                    raw_place.replace('-', ' '),
                }
                if raw_place.endswith('ова'):
                    variants.add(raw_place[:-3] + 'ово')
                if raw_place.endswith('ева'):
                    variants.add(raw_place[:-3] + 'ево')
                coord = None
                chosen = None
                for v in variants:
                    key = v.strip()
                    if key in LAUNCH_SITES:
                        coord = LAUNCH_SITES[key]
                        chosen = key
                        break
                if not coord:
                    coord = _geocode_rf_place(raw_place)
                if coord:
                    lat, lng = coord
                    return [{
                        'id': f"{mid}_pusk_rf",
                        'place': (chosen or raw_place).title(),
                        'lat': lat,
                        'lng': lng,
                        'threat_type': 'pusk',
                        'text': original_text[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': 'pusk.png',
                        'source_match': 'launch_site_rf'
                    }]
        except Exception:
            pass
    if ('пуск' in low_work or 'пуски' in low_work or '+ пуски' in low_work):
        # find quoted or dash-separated site tokens: «Name», "Name", or after 'з ' preposition
        sites_found = set()
        # Quoted tokens
        for m in re.findall(r'«([^»]{2,40})»', text):
            sites_found.add(m.strip().lower())
        for m in re.findall(r'"([^"\n]{2,40})"', text):
            sites_found.add(m.strip().lower())
        # Phrases after 'з ' (from) up to comma
        for m in re.findall(r'з\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{2,40})', low_work):
            sites_found.add(m.strip().lower())
        # tokens after 'аеродрому' or 'аэродрома' inside quotes
        for m in re.findall(r'аеродром[ау]\s+«([^»]{2,40})»', low_work):
            sites_found.add(m.strip().lower())
        for m in re.findall(r'аэродром[ау]\s+«([^»]{2,40})»', low_work):
            sites_found.add(m.strip().lower())
        tracks = []
        threat_type = 'pusk'
        icon = 'pusk.png'
        idx = 0
        for raw_site in sites_found:
            norm_key = raw_site.replace(' — ','-').replace(' – ','-').replace('—','-').replace('–','-')
            norm_key = norm_key.replace('  ',' ').strip()
            base_variants = [norm_key, norm_key.replace('полігон ','').replace('полигон ','')]
            coord = None
            chosen_name = raw_site
            for bv in base_variants:
                if bv in LAUNCH_SITES:
                    coord = LAUNCH_SITES[bv]
                    chosen_name = bv
                    break
            if not coord:
                continue
            idx += 1
            lat,lng = coord
            tracks.append({
                'id': f"{mid}_l{idx}", 'place': chosen_name.title(), 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'launch_site'
            })
        if tracks:
            return tracks
    # ---- Daily / periodic situation summary ("ситуація станом на HH:MM" + sectional bullets) ----
    # User request: do NOT create map markers for such aggregated status reports.
    # Heuristics: phrase "ситуація станом" (uk) or "ситуация на" (ru), OR presence of 2+ bullet headers like "• авіація", "• бпла", "• флот" in same message.
    bullet_headers = 0
    for hdr in ['• авіація', '• авиа', '• бпла', '• дро', '• флот', '• кораб', '• ракети', '• ракеты']:
        if hdr in low_full:
            bullet_headers += 1
    if re.search(r'ситуац[ія][яi]\s+станом', low_full) or re.search(r'ситуац[ия]\s+на\s+\d{1,2}:\d{2}', low_full) or bullet_headers >= 2:
        # User clarified: completely skip (no site display at all)
        return [{
            'id': str(mid), 'place': None, 'lat': None, 'lng': None,
            'threat_type': None, 'text': original_text[:800], 'date': date_str, 'channel': channel,
            'list_only': True, 'summary': True, 'suppress': True
        }]
    # ---- Imprecise directional-only messages (no exact city location) suppression ----
    # User request: messages that only state relative / directional movement without a clear city position
    # Examples: "групи ... рухаються північніше X у напрямку Y"; "... курс західний (місто)"; region-only with direction
    # Allow cases with explicit target form "курс на <city>" (precise intent) or patterns we already map like 'повз <city>' or multi-city slash/comma lists.
    def _has_threat_local(txt: str):
        l = txt.lower()
        return any(k in l for k in ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile'])
    lower_all = original_text.lower()
    if _has_threat_local(lower_all):
        directional_course = 'курс' in lower_all and any(w in lower_all for w in ['північ','півден','схід','захід']) and not re.search(r'курс(?:ом)?\s+на\s+[A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,}', lower_all)
        relative_dir_tokens = any(tok in lower_all for tok in ['північніше','південніше','східніше','західніше'])
        # Multi-city list heuristic (comma or slash separated multiple city tokens at start)
        multi_city_pattern = r"^[^\n]{0,120}?([A-Za-zА-Яа-яЇїІіЄєҐґ'`’ʼ\-]{3,}\s*,\s*){1,}[A-Za-zА-Яа-яЇїІіЄєҐґ'`’ʼ\-]{3,}"
        multi_city_enumeration = bool(re.match(multi_city_pattern, lower_all)) or ('/' in lower_all)
        has_pass_near = 'повз ' in lower_all
        if (directional_course or relative_dir_tokens) and not has_pass_near and not multi_city_enumeration:
            return [{
                'id': str(mid), 'place': None, 'lat': None, 'lng': None,
                'threat_type': None, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'list_only': True, 'suppress': True, 'suppress_reason': 'imprecise_direction_only'
            }]
    # Не удаляем полностью "Повітряна тривога" теперь: нужно показывать в списке событий.
    # Сохраняем текст как есть для event list.
    # Убираем markdown * _ ` и базовые эмодзи-иконки в начале строк
    text = re.sub(r'[\*`_]+', '', text)
    # Удаляем ведущие эмодзи/иконки перед словами
    text = re.sub(r'^[\W_]+', '', text)
    # Общий набор ключевых слов угроз
    THREAT_KEYS = ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile','iskander','s-300','s300','каб','артил','града','смерч','ураган','mlrs','avia','авіа','авиа','бомба','високошвидкісн']
    def has_threat(txt: str):
        l = txt.lower()
        return any(k in l for k in THREAT_KEYS)

    # PRIORITY: Structured messages with regional headers (e.g., "Область:\n city details")
    if not _disable_multiline and has_threat(original_text):
        import re as _struct_re
        # Look for pattern: "RegionName:\n threats with cities"
        region_header_pattern = r'^([А-Яа-яЇїІіЄєҐґ]+щина):\s*$'
        text_lines = original_text.split('\n')

        structured_sections = []
        current_region = None
        current_threats = []

        for line in text_lines:
            line = line.strip()
            if not line or 'підписатися' in line.lower():
                continue

            # Check if line is a region header
            region_match = _struct_re.match(region_header_pattern, line)
            if region_match:
                # Save previous section
                if current_region and current_threats:
                    structured_sections.append((current_region, current_threats))
                # Start new section
                current_region = region_match.group(1)
                current_threats = []
            elif current_region and ('шахед' in line.lower() or 'бпла' in line.lower()):
                # This is a threat line under current region
                current_threats.append(line)

        # Don't forget last section
        if current_region and current_threats:
            structured_sections.append((current_region, current_threats))

        # Process structured sections if we found any
        if len(structured_sections) >= 2:
            add_debug_log(f"STRUCTURED REGIONS: Found {len(structured_sections)} regions with threats", "structured_regions")

            all_structured_tracks = []
            for region_name, threat_lines in structured_sections:
                add_debug_log(f"Processing region {region_name} with {len(threat_lines)} threats", "structured_region_detail")

                for threat_line in threat_lines:
                    # Process each threat line with region context
                    region_context_text = f"{region_name}:\n{threat_line}"
                    line_tracks = process_message(region_context_text, f"{mid}_{region_name}_{len(all_structured_tracks)}",
                                                date_str, channel, _disable_multiline=True)
                    if line_tracks:
                        all_structured_tracks.extend(line_tracks)
                        add_debug_log(f"Region {region_name} threat '{threat_line[:50]}...' produced {len(line_tracks)} tracks", "structured_threat_result")

            if all_structured_tracks:
                add_debug_log(f"Structured processing complete: {len(all_structured_tracks)} total tracks", "structured_complete")
                return all_structured_tracks

    # NEW: Handle UAV messages with "через [city]" and "повз [city]" patterns - BEFORE trajectory_phrase
    try:
        lorig = text.lower()
        if 'бпла' in lorig and ('через' in lorig or 'повз' in lorig):
            threats = []

            # Extract cities from "через [city1], [city2]" pattern
            import re as _re_route
            route_pattern = r'через\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*\.\s+|$)'
            route_matches = _re_route.findall(route_pattern, text, re.IGNORECASE)

            for route_match in route_matches:
                # Split by comma to get individual cities
                cities_raw = [c.strip() for c in route_match.split(',') if c.strip()]

                for city_raw in cities_raw:
                    city_clean = city_raw.strip().strip('.,')
                    city_norm = clean_text(city_clean).lower()

                    # Apply normalization rules
                    if city_norm in UA_CITY_NORMALIZE:
                        city_norm = UA_CITY_NORMALIZE[city_norm]

                    # Try to get coordinates
                    coords = region_enhanced_coords(city_norm)
                    if not coords:
                        coords = ensure_city_coords(city_norm, context=text)

                    if coords:
                        # Handle different coordinate formats
                        if isinstance(coords, tuple) and len(coords) >= 2:
                            lat, lng = coords[0], coords[1]
                        else:
                            continue

                        threat_type, icon = classify(text)

                        # Extract count from text context (look for patterns like "15х БпЛА через")
                        count = 1
                        count_match = _re_route.search(rf'(\d+)[xх×]?\s*бпла.*?через.*?{re.escape(city_clean)}', text, re.IGNORECASE)
                        if count_match:
                            count = int(count_match.group(1))

                        threats.append({
                            'id': f"{mid}_route_{len(threats)}",
                            'place': city_clean.title(),
                            'lat': lat,
                            'lng': lng,
                            'threat_type': threat_type,
                            'text': f"Через {city_clean.title()} (з повідомлення про маршрут)",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': f'route_via_{count}x',
                            'count': count
                        })

                        add_debug_log(f"Route via: {city_clean} ({count}x) -> {coords}", "route_via")

            # Extract cities from "повз [city]" pattern
            past_pattern = r'повз\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*\.\s*|$)'
            past_matches = _re_route.findall(past_pattern, text, re.IGNORECASE)

            for past_match in past_matches:
                city_clean = past_match.strip().strip('.,')
                city_norm = clean_text(city_clean).lower()

                # Apply normalization rules
                if city_norm in UA_CITY_NORMALIZE:
                    city_norm = UA_CITY_NORMALIZE[city_norm]

                # Try to get coordinates
                coords = region_enhanced_coords(city_norm)
                if not coords:
                    coords = ensure_city_coords_with_message_context(city_norm, text)

                # Fallback: try accusative case normalization (e.g., "олександрію" -> "олександрія")
                if not coords and city_norm.endswith('ію'):
                    accusative_fallback = city_norm[:-2] + 'ія'
                    coords = region_enhanced_coords(accusative_fallback)
                    if not coords:
                        coords = ensure_city_coords_with_message_context(accusative_fallback, text)
                    if coords:
                        city_norm = accusative_fallback
                        city_clean = accusative_fallback.title()  # Use normalized name for display

                if coords:
                    # Handle different coordinate formats
                        if isinstance(coords, tuple) and len(coords) >= 2:
                            lat, lng = coords[0], coords[1]
                        else:
                            continue

                        threat_type, icon = classify(text)

                        # Extract count from text context (look for patterns like "4х БпЛА повз")
                        count = 1
                        count_match = _re_route.search(rf'(\d+)[xх×]?\s*бпла.*?повз.*?{re.escape(city_clean)}', text, re.IGNORECASE)
                        if count_match:
                            count = int(count_match.group(1))

                        threats.append({
                            'id': f"{mid}_past_{len(threats)}",
                            'place': city_clean.title(),
                            'lat': lat,
                            'lng': lng,
                            'threat_type': threat_type,
                            'text': f"Повз {city_clean.title()} (з повідомлення про маршрут)",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': f'route_past_{count}x',
                            'count': count
                        })

                        add_debug_log(f"Route past: {city_clean} ({count}x) -> {coords}", "route_past")

            if threats:
                return threats
            else:
                pass

    except Exception:
        pass

    # --- Trajectory phrase pattern: "з дніпропетровщини через харківщину у напрямку полтавщини" ---
    # We map region stems to canonical OBLAST_CENTERS keys (simplistic stem matching).
    lower_full = text.lower()
    if has_threat(lower_full) and ' через ' in lower_full and (' у напрямку ' in lower_full or ' напрямку ' in lower_full or ' в напрямку ' in lower_full):
        # Extract sequence tokens after prepositions з/із/від -> start, через -> middle(s), напрямку -> target
        # Very heuristic; splits by key words.
        try:
            norm = re.sub(r'\s+', ' ', lower_full)
            norm = norm.replace('із ', 'з ').replace('від ', 'з ')
            if ' через ' in norm:
                front, after = norm.split(' через ', 1)
                start_token = front.split(' з ')[-1].strip()
                target_part = None; mid_part = ''
                for marker in [' у напрямку ', ' в напрямку ', ' напрямку ']:
                    if marker in after:
                        mid_part, target_part = after.split(marker, 1)
                        break
                if target_part:
                    mid_token = mid_part.strip().split('.')[0]
                    target_token = target_part.strip().split('.')[0]
                    def region_center(token: str):
                        token = token.strip()
                        for k,(lat,lng) in OBLAST_CENTERS.items():
                            if token.startswith(k.split()[0][:6]) or token in k:
                                return (k,(lat,lng))
                        return None
                    seq = []
                    for tk in [start_token, mid_token, target_token]:
                        rc = region_center(tk)
                        if rc and (not seq or seq[-1][0] != rc[0]):
                            seq.append(rc)
                    if len(seq) >= 2:
                        threat_type, icon = classify(text)
                        tracks = []
                        for idx,(name,(lat,lng)) in enumerate(seq,1):
                            base = name.split()[0].title()
                            tracks.append({
                                'id': f"{mid}_t{idx}", 'place': base, 'lat': lat, 'lng': lng,
                                'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                                'marker_icon': icon, 'source_match': 'trajectory_phrase'
                            })
                        return tracks
        except Exception:
            pass
    # direct coordinates pattern
    # --- Direction with parenthetical specific settlement e.g. "у напрямку білгород-дністровського району одещини (затока)" ---
    if has_threat(lower_full) and 'у напрямку' in lower_full and '(' in lower_full and ')' in lower_full:
        # capture last parenthetical token (short) that is a known settlement
        try:
            paren_tokens = re.findall(r'\(([a-zа-яіїєґ\-\s]{3,})\)', lower_full)
            if paren_tokens:
                candidate = paren_tokens[-1].strip().lower()
                # trim descriptors like 'смт ' , 'с.' etc
                candidate = re.sub(r'^(смт|с\.|м\.|місто|селище)\s+','', candidate)
                norm = UA_CITY_NORMALIZE.get(candidate, candidate)
                coords = CITY_COORDS.get(norm)
                if not coords and SETTLEMENTS_INDEX:
                    coords = SETTLEMENTS_INDEX.get(norm)
                if not coords:
                    coords = SETTLEMENT_FALLBACK.get(norm)
                log.debug(f"parenthetical_dir detect mid={mid} candidate={candidate} norm={norm} found={bool(coords)}")
                if coords:
                    lat,lng = coords
                    threat_type, icon = classify(text)
                    return [{
                        'id': f"{mid}_dirp", 'place': norm.title(), 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'direction_parenthetical'
                    }]
        except Exception:
            pass
    # --- Region-level shelling threat (e.g. "Харківська обл. Загроза обстрілу прикордонних територій") ---
    try:
        if re.search(r'(загроза обстрілу|угроза обстрела)', lower_full):
            # attempt to match any oblast token present
            region_hit = None
            for reg_key in OBLAST_CENTERS.keys():
                if reg_key in lower_full:
                    region_hit = reg_key
                    log.debug(f"region_shelling candidate mid={mid} match={reg_key}")
                    break
            if region_hit:
                # Only emit if we haven't already returned a more specific structure earlier (heuristic: continue)
                lat, lng = OBLAST_CENTERS[region_hit]
                threat_type, icon = classify(text)
                # Enforce obstril icon for shelling phrasing even if classify changed in future
                if re.search(r'(загроза обстрілу|угроза обстрела|обстріл|обстрел)', lower_full):
                    threat_type = 'artillery'; icon = 'obstril.png'
                border_shell = bool(re.search(r'прикордон|пригранич', lower_full))
                place_label = region_hit
                if border_shell:
                    place_label += ' (прикордоння)'
                log.debug(f"region_shelling emit mid={mid} region={region_hit} border={border_shell}")
                return [{
                    'id': f"{mid}_region_shell", 'place': place_label, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'region_shelling', 'border_shelling': border_shell
                }]
    except Exception:
        pass
    # Special handling for KAB threats with regional mentions (e.g., "Загроза КАБ для прифронтових громад Сумщини")
    kab_region_match = re.search(r'(каб|авіабомб|авиабомб|авіаційних.*бомб|керован.*бомб)[^\.]*?(сумщин[иіа]|харківщин[иіа]|чернігівщин[иіа]|полтавщин[иіа])', text.lower())
    if kab_region_match:
        region_mention = kab_region_match.group(2)
        # Convert genitive/dative to nominative
        if 'сумщин' in region_mention:
            region_key = 'сумщина'
        elif 'харківщин' in region_mention:
            region_key = 'харківщина'
        elif 'чернігівщин' in region_mention:
            region_key = 'чернігівщина'
        elif 'полтавщин' in region_mention:
            region_key = 'полтавщина'
        else:
            region_key = None

        if region_key and region_key in OBLAST_CENTERS:
            lat, lng = OBLAST_CENTERS[region_key]
            # For KAB threats, offset coordinates slightly from city center to avoid implying direct city impact
            if region_key == 'сумщина':
                lat += 0.1  # Move north of Sumy city
                lng -= 0.1  # Move west of Sumy city
            elif region_key == 'харківщина':
                lat += 0.1  # Move north of Kharkiv city
                lng -= 0.1  # Move west of Kharkiv city
            add_debug_log(f"Creating KAB regional threat marker for {region_key}: lat={lat}, lng={lng}", "kab_regional")
            return [{
                'id': f"{mid}_kab_regional", 'place': region_key.title(), 'lat': lat, 'lng': lng,
                'threat_type': 'raketa', 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'icon_balistic.svg', 'source_match': 'kab_regional_threat'
            }]

    # SPECIAL: Handle multi-regional UAV messages (like the user's example)
    def handle_multi_regional_uav():
        """Handle messages with multiple regional UAV threats listed separately"""
        threats = []
        text_lines = text.split('\n')

        # Check if this looks like a multi-regional UAV message
        region_count = 0
        uav_count = 0
        for line in text_lines:
            line_lower = line.lower().strip()
            if not line_lower:
                continue

            # Count regions mentioned
            if any(region in line_lower for region in ['щина:', 'область:', 'край:']):
                region_count += 1

            # Count UAV mentions
            if 'бпла' in line_lower and ('курс' in line_lower or 'на ' in line_lower):
                uav_count += 1

        # If we have multiple regions and multiple UAV mentions, process each line
        if region_count >= 2 and uav_count >= 3:
            add_debug_log(f"MULTI-REGIONAL UAV MESSAGE: {region_count} regions, {uav_count} UAVs", "multi_regional")

            for line in text_lines:
                line_stripped = line.strip()
                if not line_stripped or ':' in line_stripped[:20]:  # Skip region headers
                    continue

                line_lower = line_stripped.lower()

                # Look for UAV course patterns
                if 'бпла' in line_lower and ('курс' in line_lower or ' на ' in line_lower):
                    # Extract city name from patterns like "БпЛА курсом на Конотоп" or "2х БпЛА курсом на Велику Димерку"
                    patterns = [
                        r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|])',
                        r'бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|])',
                        r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|])'
                    ]

                    for pattern in patterns:
                        matches = re.finditer(pattern, line_stripped, re.IGNORECASE)
                        for match in matches:
                            if len(match.groups()) == 2:
                                count_str, city_raw = match.groups()
                            else:
                                count_str = None
                                city_raw = match.group(1)

                            if not city_raw:
                                continue

                            # Clean and normalize city name
                            city_clean = city_raw.strip()
                            city_norm = clean_text(city_clean).lower()

                            # Apply normalization rules
                            if city_norm in UA_CITY_NORMALIZE:
                                city_norm = UA_CITY_NORMALIZE[city_norm]

                            # Try to get coordinates
                            coords = region_enhanced_coords(city_norm)
                            if not coords:
                                coords = ensure_city_coords(city_norm, context=text)

                            if coords:
                                lat, lng = coords
                                threat_type, icon = classify(text)

                                # Extract count if present
                                uav_count_num = 1
                                if count_str and count_str.isdigit():
                                    uav_count_num = int(count_str)

                                threat_id = f"{mid}_multi_{len(threats)}"
                                threats.append({
                                    'id': threat_id,
                                    'place': city_clean.title(),
                                    'lat': lat,
                                    'lng': lng,
                                    'threat_type': threat_type,
                                    'text': f"{line_stripped} (з багаторегіонального повідомлення)",
                                    'date': date_str,
                                    'channel': channel,
                                    'marker_icon': icon,
                                    'source_match': f'multi_regional_uav_{uav_count_num}x',
                                    'count': uav_count_num
                                })

                                add_debug_log(f"Multi-regional UAV: {city_clean} ({uav_count_num}x) -> {coords}", "multi_regional")
                            else:
                                add_debug_log(f"Multi-regional UAV: No coords for {city_clean}", "multi_regional")

        return threats

    # SPECIAL: Handle single UAV course mentions in regular messages
    def handle_single_uav_courses():
        """Handle UAV course mentions like '4х БпЛА курсом на Добротвір' in regular alert messages"""
        threats = []

        # Look for UAV course patterns in the entire message
        patterns = [
            r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|\(])',
            r'бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|\(])',
            r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|\(])'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:
                    count_str, city_raw = match.groups()
                else:
                    count_str = None
                    city_raw = match.group(1)

                if not city_raw:
                    continue

                # Clean and normalize city name
                city_clean = city_raw.strip()
                city_norm = clean_text(city_clean).lower()

                # Apply normalization rules
                if city_norm in UA_CITY_NORMALIZE:
                    city_norm = UA_CITY_NORMALIZE[city_norm]

                # Try to get coordinates
                coords = region_enhanced_coords(city_norm)
                if not coords:
                    coords = ensure_city_coords(city_norm, context=text)

                if coords:
                    lat, lng = coords[:2]
                    threat_type, icon = classify(text)

                    # Extract count if present
                    uav_count_num = 1
                    if count_str and count_str.isdigit():
                        uav_count_num = int(count_str)

                    threat_id = f"{mid}_uav_course_{len(threats)}"
                    threats.append({
                        'id': threat_id,
                        'place': city_clean.title(),
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': f"БпЛА курсом на {city_clean} ({uav_count_num}x)",
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': f'single_uav_course_{uav_count_num}x',
                        'count': uav_count_num
                    })

                    add_debug_log(f"Single UAV course: {city_clean} ({uav_count_num}x) -> {coords}", "single_uav")
                else:
                    add_debug_log(f"Single UAV course: No coords for {city_clean}", "single_uav")

        # ALSO: Extract cities from emoji structure in the same text
        # Pattern for "| 🛸 Город (Область)"
        emoji_pattern = r'\|\s*🛸\s*([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)\s*\([^)]*обл[^)]*\)'
        emoji_matches = re.finditer(emoji_pattern, text, re.IGNORECASE)

        for match in emoji_matches:
            city_raw = match.group(1).strip()
            if not city_raw or len(city_raw) < 2:
                continue

            city_norm = clean_text(city_raw).lower()
            if city_norm in UA_CITY_NORMALIZE:
                city_norm = UA_CITY_NORMALIZE[city_norm]

            coords = region_enhanced_coords(city_norm)
            if not coords:
                coords = ensure_city_coords(city_norm, context=text)

            if coords:
                lat, lng = coords[:2]
                threat_type, icon = classify(text)

                threat_id = f"{mid}_emoji_struct_{len(threats)}"
                threats.append({
                    'id': threat_id,
                    'place': city_raw.title(),
                    'lat': lat,
                    'lng': lng,
                    'threat_type': threat_type,
                    'text': f"Загроза в {city_raw}",
                    'date': date_str,
                    'channel': channel,
                    'marker_icon': icon,
                    'source_match': 'emoji_structure',
                    'count': 1
                })

                add_debug_log(f"Emoji structure: {city_raw} -> {coords}", "emoji_struct")
            else:
                add_debug_log(f"Emoji structure: No coords for {city_raw}", "emoji_struct")

        return threats

    # Check for single UAV course mentions first (before multi-regional check)
    single_uav_threats = handle_single_uav_courses()
    if single_uav_threats:
        add_debug_log(f"SINGLE UAV COURSES: Found {len(single_uav_threats)} threats", "single_uav")
        # Continue processing to also get regular location markers
        # Don't return early - we want both UAV course markers AND location markers

    # Check for multi-regional UAV messages
    if multi_regional_flag:
        multi_regional_threats = handle_multi_regional_uav()
        if multi_regional_threats:
            add_debug_log(f"MULTI-REGIONAL UAV: Found {len(multi_regional_threats)} threats", "multi_regional")
            return multi_regional_threats

    # Southeast-wide tactical aviation activity (no specific settlement): place a synthetic marker off SE border.
    se_phrase = lower if 'lower' in locals() else original_text.lower()
    if ('тактичн' in se_phrase or 'авіаці' in se_phrase or 'авиац' in se_phrase) and ('південно-східн' in se_phrase or 'південно східн' in se_phrase or 'юго-восточ' in se_phrase or 'південного-сходу' in se_phrase):
        # Approx point in Azov Sea off SE (between Mariupol & Berdyansk) to avoid implying exact impact
        lat, lng = 46.5, 37.5
        return [{
            'id': f"{mid}_se", 'place': 'Південно-східний напрямок', 'lat': lat, 'lng': lng,
            'threat_type': 'avia', 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': 'avia.png', 'source_match': 'southeast_aviation'
        }]
    # North-east tactical aviation activity - coordinates on Russian territory before Ukraine border
    # Aviation threats come FROM Russia, so marker should be in Russia
    # SKIP if this is a multi-threat message (handled separately above)
    if ('тактичн' in se_phrase or 'авіаці' in se_phrase or 'авиац' in se_phrase) and (
        'північно-східн' in se_phrase or 'північно східн' in se_phrase or 'северо-восточ' in se_phrase or 'північного-сходу' in se_phrase
    ) and not ('🛬' in original_text and '🛸' in original_text):
        # Coordinates on Russian territory (Belgorod area) - aviation source location
        lat, lng = 51.0, 36.5  # Near Belgorod, Russia (before Ukraine border)
        return [{
            'id': f"{mid}_ne", 'place': 'Північно-східний напрямок', 'lat': lat, 'lng': lng,
            'threat_type': 'avia', 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': 'avia.png', 'source_match': 'northeast_aviation'
        }]
    m = re.search(r'(\d{1,2}\.\d+),(\d{1,3}\.\d+)', text)
    if m:
        lat_val = safe_float(m.group(1))
        lng_val = safe_float(m.group(2))
        if lat_val is not None and lng_val is not None and validate_ukraine_coords(lat_val, lng_val):
            threat_type, icon = classify(text)
            return [{
                'id': str(mid), 'place': 'Unknown', 'lat': lat_val, 'lng': lng_val,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon
            }]
    # Alarm cancellation always list-only
    if re.search(r'відбій\s+тривог|отбой\s+тревог', original_text.lower()):
        return [{
            'id': str(mid), 'place': None, 'lat': None, 'lng': None,
            'threat_type': 'alarm_cancel', 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': 'vidboi.png', 'list_only': True
        }]
    lower = text.lower()
    # Specialized single-line pattern: direction from one oblast toward another (e.g. 'бпла ... курсом на полтавщину')
    import re as _re_one
    m_dir_oblast = _re_one.search(r'бпла[^\n]*курс(?:ом)?\s+на\s+([a-zа-яїієґ\-]+щин[ауі])', lower)
    if m_dir_oblast:
        dest = m_dir_oblast.group(1)
        # normalize accusative -> nominative
        dest_norm = dest.replace('щину','щина').replace('щини','щина')
        if dest_norm in OBLAST_CENTERS:
            dest_lat, dest_lng = OBLAST_CENTERS[dest_norm]

            def _region_key_from_stem(stem: str):
                for key in OBLAST_CENTERS.keys():
                    if stem and stem in key:
                        return key
                return None

            def _resolve_location_token(token: str):
                if not token:
                    return None
                cleaned = token.strip(" .,:;!?\n\t'`\"-»«")
                if not cleaned:
                    return None
                cleaned = ' '.join(cleaned.split())
                variants = [cleaned]
                def _add_variant(val: str):
                    v = val.strip()
                    if v and v not in variants:
                        variants.append(v)
                suffix_map = {
                    'щину': 'щина', 'щини': 'щина', 'щині': 'щина',
                    ' область': ' область', ' обл.': ' область', ' обл': ' область'
                }
                for suffix, repl in suffix_map.items():
                    if cleaned.endswith(suffix):
                        _add_variant(cleaned[:-len(suffix)] + repl)
                loc_endings = [('і','ь'),('і','а'),('і','я'),('ї','я'),('ю','я'),('у','а')]
                for ending, replacement in loc_endings:
                    if cleaned.endswith(ending):
                        _add_variant(cleaned[:-len(ending)] + replacement)
                for variant in list(variants):
                    normalized = UA_CITY_NORMALIZE.get(variant, variant)
                    if normalized in OBLAST_CENTERS:
                        plat, plng = OBLAST_CENTERS[normalized]
                        return {'label': normalized.split()[0].title(), 'lat': plat, 'lng': plng}
                    if normalized in CITY_TO_OBLAST:
                        stem = CITY_TO_OBLAST[normalized]
                        reg_key = _region_key_from_stem(stem)
                        if reg_key:
                            plat, plng = OBLAST_CENTERS[reg_key]
                            return {'label': reg_key.split()[0].title(), 'lat': plat, 'lng': plng}
                    if normalized in CITY_COORDS:
                        plat, plng = CITY_COORDS[normalized]
                        return {'label': normalized.title(), 'lat': plat, 'lng': plng}
                return None

            prefix = lower[:m_dir_oblast.start()]
            source_candidate = None
            src_pattern = _re_one.compile(r'(?:на|у|в|із|зі|з)\s+([a-zа-яїієґ\-\'ʼ`\s]{3,40})')
            for sm in src_pattern.finditer(prefix):
                resolved = _resolve_location_token(sm.group(1))
                if resolved:
                    source_candidate = resolved
            if not source_candidate:
                header_match = _re_one.match(r'^\s*([a-zа-яїієґ\-\'ʼ`\s]{3,})[:—-]', lower)
                if header_match:
                    resolved = _resolve_location_token(header_match.group(1))
                    if resolved:
                        # Skip if header is just an oblast/region marker (not a specific city)
                        # When destination is also an oblast, this indicates region-level info without specific location
                        header_text = header_match.group(1).strip()
                        header_normalized = LOCATIVE_NORMALIZE.get(header_text, header_text)
                        is_region_header = (
                            header_normalized in OBLAST_CENTERS or
                            header_normalized in CITY_TO_OBLAST or
                            'область' in header_normalized or 'обл' in header_normalized or
                            header_text.endswith(('щина', 'щині', 'щину', 'щиною'))
                        )
                        dest_is_oblast = dest_norm in OBLAST_CENTERS
                        # Only use header as source if it's a specific city OR if destination is a city (not oblast)
                        if not (is_region_header and dest_is_oblast):
                            source_candidate = resolved
            if source_candidate:
                src_lat, src_lng = source_candidate['lat'], source_candidate['lng']
                dest_label = dest_norm.split()[0].title()

                def _direction_token(dlat: float, dlng: float):
                    if abs(dlat) < 1e-6 and abs(dlng) < 1e-6:
                        return None
                    if abs(dlat) > abs(dlng) * 1.4:
                        return 'n' if dlat > 0 else 's'
                    if abs(dlng) > abs(dlat) * 1.4:
                        return 'e' if dlng > 0 else 'w'
                    if dlat >= 0 and dlng >= 0:
                        return 'ne'
                    if dlat >= 0 and dlng < 0:
                        return 'nw'
                    if dlat < 0 and dlng >= 0:
                        return 'se'
                    return 'sw'

                dir_token = _direction_token(dest_lat - src_lat, dest_lng - src_lng)
                arrow_label_map = {
                    'n': 'півночі', 's': 'півдня', 'e': 'сходу', 'w': 'заходу',
                    'ne': 'північного сходу', 'nw': 'північного заходу',
                    'se': 'південного сходу', 'sw': 'південного заходу'
                }
                course_direction_map = {
                    'n': 'північ', 's': 'південь', 'e': 'схід', 'w': 'захід',
                    'ne': 'північний схід', 'nw': 'північний захід',
                    'se': 'південний схід', 'sw': 'південний захід'
                }
                arrow_label = arrow_label_map.get(dir_token, '')
                course_direction_text = course_direction_map.get(dir_token, dest_label)

                place_name = f"{source_candidate['label']} → {dest_label}"
                if arrow_label:
                    place_name += f" ←{arrow_label}"

                trajectory = {
                    'start': [src_lat, src_lng],
                    'end': [dest_lat, dest_lng],
                    'source': source_candidate['label'],
                    'target': dest_label,
                    'kind': 'singleline_region_course'
                }

                threat_type, icon = classify(original_text)
                return [{
                    'id': f"{mid}_dir_oblast", 'place': place_name, 'lat': src_lat, 'lng': src_lng,
                    'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'singleline_region_course', 'trajectory': trajectory,
                    'course_source': source_candidate['label'], 'course_target': dest_label,
                    'course_direction': f"курс на {course_direction_text}", 'course_type': 'region_to_region'
                }]

            return [{
                'id': f"{mid}_dir_oblast", 'place': dest_norm.title(), 'lat': dest_lat, 'lng': dest_lng,
                'threat_type': 'uav', 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'shahed3.webp', 'source_match': 'singleline_oblast_course'
            }]
    # Extract drone / shahed count pattern (e.g. "7х бпла", "6x дронів", "10 х бпла") early so later branches can reuse
    drone_count = None
    m_count = re.search(r'(\b\d{1,3})\s*[xх]\s*(?:бпла|дрон|дрони|шахед|шахеди|шахедів)', lower)
    if m_count:
        try:
            drone_count = int(m_count.group(1))
        except ValueError:
            drone_count = None
    # Normalize some genitive forms ("дніпропетровської" -> base) to capture multiple oblasts in one message
    GENITIVE_NORMALIZE = {
        'дніпропетровської': 'дніпропетровська область',
        'днепропетровской': 'дніпропетровська область',
        'чернігівської': 'чернігівська обл.',
        'черниговской': 'чернігівська обл.',
        'сумської': 'сумська область',
        'сумской': 'сумська область',
        'харківської': 'харківська обл.',
        'харьковской': 'харківська обл.'
    }
    for gform, base_form in GENITIVE_NORMALIZE.items():
        if gform in lower:
            lower = lower.replace(gform, base_form)
    # Locative / prepositional oblast & region endings -> base ("дніпропетровщині" -> "дніпропетровщина")
    LOCATIVE_NORMALIZE = {
        'дніпропетровщині': 'дніпропетровщина',
        'донеччині': 'донеччина',
        'сумщині': 'сумщина',
        'харківщині': 'харківщина',
        'чернігівщині': 'чернігівщина',
        'миколаївщині': 'миколаївщина',
        'херсонщині': 'херсонщина',
        'запоріжжі': 'запоріжжя'
    }
    for lform, base_form in LOCATIVE_NORMALIZE.items():
        if lform in lower:
            lower = lower.replace(lform, base_form)
    # City genitive -> nominative (subset) for settlement detection
    CITY_GENITIVE = [
        ('харкова','харків'), ('києва','київ'), ('львова','львів'), ('одеси','одеса'), ('дніпра','дніпро')
    ]
    for gform, base in CITY_GENITIVE:
        if gform in lower:
            lower = lower.replace(gform, base)
    # Normalize some accusative oblast forms to nominative for matching
    lower = lower.replace('донеччину','донеччина').replace('сумщину','сумщина')
    text = lower  # downstream logic mostly uses lower-case comparisons
    # Санітизація дублювань типу "область області" -> залишаємо один раз
    text = re.sub(r'(область|обл\.)\s+област[іи]', r'\1', text)

    # --- Simple sanitization of formatting noise (bold asterisks, stray stars) ---
    # Keeps Ukrainian characters while removing leading/trailing markup like ** or * around segments
    if '**' in text or '*' in text:
        # remove isolated asterisks not part of words
        text = re.sub(r'\*+', '', text)

    # --- Early explicit pattern: "<RaionName> район (<Oblast ...>)" (e.g. "Запорізький район (Запорізька обл.)") ---
    # Sometimes such messages were slipping through as raw because the pre-parenthesis token ended with 'район'.
    m_raion_oblast = re.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{4,})\s+район\s*\(([^)]*обл[^)]*)\)', text)
    if m_raion_oblast:
        raion_token = m_raion_oblast.group(1).strip().lower()
        # Normalize morphological endings similar to later norm_raion logic
        raion_base = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_token)
        if raion_base in RAION_FALLBACK:
            lat, lng = RAION_FALLBACK[raion_base]
            threat_type, icon = classify(original_text if 'original_text' in locals() else text)
            # Maintain active raion alarm state
            if threat_type == 'alarm':
                RAION_ALARMS[raion_base] = {'place': f"{raion_base.title()} район", 'lat': lat, 'lng': lng, 'since': time.time()}
            elif threat_type == 'alarm_cancel':
                RAION_ALARMS.pop(raion_base, None)
            return [{
                'id': str(mid), 'place': f"{raion_base.title()} район", 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': (original_text if 'original_text' in locals() else text)[:500],
                'date': date_str, 'channel': channel, 'marker_icon': icon, 'source_match': 'raion_oblast_combo'
            }]
        else:
            log.debug(f"raion_oblast primary matched token={raion_token} base={raion_base} no coords")
    else:
        # Secondary heuristic fallback if formatting (emoji / markup) broke regex
        if 'район (' in text and ' обл' in text and has_threat(text):
            try:
                prefix = text.split('район (',1)[0]
                cand = prefix.strip().split()[-1].lower()
                cand_base = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', cand)
                if cand_base in RAION_FALLBACK:
                    lat,lng = RAION_FALLBACK[cand_base]
                    threat_type, icon = classify(original_text if 'original_text' in locals() else text)
                    log.debug(f"raion_oblast secondary emit cand={cand} base={cand_base}")
                    return [{
                        'id': str(mid), 'place': f"{cand_base.title()} район", 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': (original_text if 'original_text' in locals() else text)[:500],
                        'date': date_str, 'channel': channel, 'marker_icon': icon, 'source_match': 'raion_oblast_secondary'
                    }]
                else:
                    log.debug(f"raion_oblast secondary no coords cand={cand} base={cand_base}")
            except Exception as _e:
                log.debug(f"raion_oblast secondary error={_e}")

    # --- Russian strategic aviation suppression (uses _is_russian_strategic_aviation defined earlier) ---
    if _is_russian_strategic_aviation(text):
        return None

    if _is_general_warning_without_location(text):
        return None

    # --- Western border drone reconnaissance suppression ---
    def _is_western_border_reconnaissance(t: str) -> bool:
        """Suppress messages about drones crossing western borders (Hungary, etc.) - not related to Russian threats"""
        t_lower = t.lower()

        # Check for western border crossing indicators
        border_crossing_terms = [
            'перетнув державний кордон', 'пересек государственную границу',
            'перетнув кордон', 'пересек границу',
            'з боку угорщини', 'со стороны венгрии',
            'з території угорщини', 'с территории венгрии'
        ]
        has_border_crossing = any(term in t_lower for term in border_crossing_terms)

        # Check for western regions (primarily Zakarpattya)
        western_regions = ['закарпатт', 'закарпать', 'ужгород', 'мукачев']
        has_western_region = any(region in t_lower for region in western_regions)

        # Check for reconnaissance/monitoring context (not combat threats)
        recon_terms = ['радари зсу', 'радары всу', 'зафіксували проліт', 'зафиксировали пролет', 'стежити за обстановкою', 'следить за обстановкой']
        has_recon_context = any(term in t_lower for term in recon_terms)

        # Suppress if it's about western border reconnaissance
        if has_border_crossing and has_western_region:
            return True

        # Also suppress general monitoring messages about western regions
        if has_western_region and has_recon_context and ('дрон' in t_lower or 'бпла' in t_lower):
            return True

        return False

    if _is_western_border_reconnaissance(text):
        return None

    # --- Aggregate / statistical summary suppression ---
    def _is_aggregate_summary(t: str) -> bool:
        # Situation report override: if starts with 'обстановка' we evaluate full logic first (word 'загроза' inside shouldn't unblock)
        starts_obst = t.startswith('обстановка')
        # Do not suppress if explicit real-time warning words present (unless it's a structured situation report)
        if not starts_obst and any(w in t for w in ['загроза','перейдіть в укриття','укриття!']):
            return False
        verbs = ['збито/подавлено','збито / подавлено','збито-подавлено','збито','подавлено','знищено']
        context = ['станом на','за попередніми даними','у ніч на','повітряний напад','протиповітряною обороною','протиповітряна оборона','підрозділи реб','мобільні вогневі групи','обстановка']
        objects_re = re.compile(r'\b\d{1,3}[\-–]?(ма|)?\s*(ворожих|)\s*(бпла|shahed|дрон(?:ів|и)?|ракет|ракети)')
        verb_hit = any(v in t for v in verbs)
        ctx_hits = sum(1 for c in context if c in t)
        obj_hit = bool(objects_re.search(t))
        # Strong aggregate if all three categories present OR multiple context + objects
        if (verb_hit and obj_hit and ctx_hits >= 1) or (ctx_hits >= 2 and obj_hit):
            return True
        # Long multiline with origins list and many commas plus 'типу shahed'
        if 'типу shahed' in t and t.count('\n') >= 2 and obj_hit:
            return True
        # Situation report structure: starts with 'обстановка станом на' or begins with 'обстановка' and multiple category lines (— стратегічна авіація, — бпла, — флот)
        if starts_obst:
            dash_lines = sum(1 for line in t.split('\n') if line.strip().startswith('—'))
            if dash_lines >= 2:
                return True
        return False
    if _is_aggregate_summary(text):
        return None

    # --- Pattern: City (Oblast ...) e.g. "Павлоград (Дніпропетровська обл.)" ---
    bracket_city = re.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})\s*\(([^)]+)\)', text)
    if bracket_city:
        raw_city = bracket_city.group(1).strip().lower()
        raw_inside = bracket_city.group(2).lower()
        # Особый случай: "дніпропетровська область (павлоградський р-н)" -> ставим Павлоград
        if ('область' in raw_city or 'обл' in raw_city) and ('павлоград' in raw_inside):
            pav_key = 'павлоградський'
            if pav_key in RAION_FALLBACK:
                lat,lng = RAION_FALLBACK[pav_key]
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': 'Павлоградський район', 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'oblast_raion_combo'
                }]
        # Пропускаем случаи вида "<область> (<район ...>)" чтобы не трактовать слово 'область' как город
        if raw_city in {'область','обл','обл.'} or raw_city.endswith('область'):
            bracket_city = None
    if bracket_city and raw_city != 'район':
            norm_city = UA_CITY_NORMALIZE.get(raw_city, raw_city)
            # Initial local attempt (static minimal list)
            coords = CITY_COORDS.get(norm_city)
            # Region hint extraction
            region_hint = None
            if any(tok in raw_inside for tok in ['обл', 'область']):
                region_hint = raw_inside.strip()
            # 1) Explicit override for (city, region) if provided
            if region_hint:
                override_key = (norm_city, region_hint)
                if override_key in OBLAST_CITY_OVERRIDES:
                    coords = OBLAST_CITY_OVERRIDES[override_key]
            # 2) If we have region hint and NO coords yet, attempt region-qualified geocode first (priority to enforce oblast binding)
            region_combo_tried = False
            if not coords and region_hint and OPENCAGE_API_KEY:
                combo_query = f"{norm_city} {region_hint}".replace('  ',' ').strip()
                try:
                    refined = geocode_opencage(combo_query)
                    if refined:
                        coords = refined
                    region_combo_tried = True
                except Exception:
                    pass
            # 3) Attempt city alone geocode only if still no coords
            if not coords and OPENCAGE_API_KEY:
                try:
                    coords = geocode_opencage(norm_city)
                except Exception:
                    pass
            # 4) If region hint exists and we got coords from plain city geocode but city is potentially duplicated across oblasts,
            # try region-qualified geocode as refinement (unless already tried).
            if region_hint and OPENCAGE_API_KEY and not region_combo_tried and coords and norm_city in ['борова','миколаївка','николаевка']:
                try:
                    combo_query = f"{norm_city} {region_hint}".replace('  ',' ').strip()
                    refined2 = geocode_opencage(combo_query)
                    if refined2:
                        coords = refined2
                except Exception:
                    pass
            # Ambiguous manual mapping fallback (if still no coords or mismatch with region)
            if region_hint:
                # derive stem like 'харківськ', 'львівськ'
                rh_low = region_hint.lower()
                # choose first word containing 'харків' etc
                region_key = None
                for stem in ['харків','львів','київ','дніпропетров','полтав','сум','черніг','волин','запор','одес','микола','черка','житом','хмельниць','рівн','івано','терноп','ужгород','кропив','луган','донець','чернівц']:
                    if stem in rh_low:
                        region_key = stem
                        break
                AMBIGUOUS_CITY_REGION = {
                    ('золочів','харків'): (50.2788, 36.3644),  # Zolochiv Kharkiv oblast
                    ('золочів','львів'): (49.8078, 24.9002),   # Zolochiv Lviv oblast
                }
                if region_key:
                    key = (norm_city, region_key)
                    mapped = AMBIGUOUS_CITY_REGION.get(key)
                    if mapped:
                        coords = mapped
            if coords:
                lat,lng = coords
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': norm_city.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'bracket_city'
                }]

    # --- Multi-segment / enumerated lines (1. 2. 3.) region extraction ---
    # Разбиваем по переносам, собираем упоминания нескольких областей; создаём отдельные маркеры

    # PRIORITY: Detect trajectory patterns BEFORE multi-region processing
    # Pattern: "з [source_region] на [target_region(s)]" - trajectory, not multi-target
    trajectory_pattern = r'(\d+(?:-\d+)?)?\s*шахед[іївыиє]*\s+з\s+([а-яіїєґ]+(щин|ччин)[ауиі])\s+на\s+([а-яіїєґ/]+(щин|ччин)[ауиіу])'
    trajectory_match = re.search(trajectory_pattern, text.lower(), re.IGNORECASE)

    if trajectory_match:
        count_str = trajectory_match.group(1)
        source_region = trajectory_match.group(2)
        target_regions = trajectory_match.group(4)

        print(f"DEBUG: Trajectory detected - {count_str or ''}шахедів з {source_region} на {target_regions}")

        # For trajectory messages, we should NOT create markers in region centers
        # This represents movement through airspace, not attacks on specific locations
        # Options:
        # 1. Don't create any markers (trajectory only)
        # 2. Create trajectory line visualization
        # 3. Create border crossing markers

        # For now, suppress markers for pure trajectory messages
        print("DEBUG: Suppressing region markers for trajectory message")
        return None

    region_hits = []  # list of (display_name, (lat,lng), snippet)
    # Treat semicolons as separators like newlines for multi-segment parsing
    seg_text = text.replace(';', '\n')
    lines = [ln.strip() for ln in seg_text.split('\n') if ln.strip()]
    # Pre-flag launch site style multi-line posts to avoid RAW fallback – treat each line with a launch phrase as separate pseudo-track (no coords yet)
    launch_mode = any(ln.lower().startswith('відмічені пуски') or ln.lower().startswith('+ пуски') for ln in lines)
    for ln in lines:
        ln_low = ln.lower()
        local_regions = []
        for name, coords in OBLAST_CENTERS.items():
            if name in ln_low:
                local_regions.append((name, coords))
        # если в строке более 1— сохраняем все, иначе одну
        for (rn, rc) in local_regions:
            region_hits.append((rn.title(), rc, ln[:180]))
    # Якщо знайшли >=2 регіональних маркери в різних пунктах списку — формуємо множинні треки
    if len(region_hits) >= 2 and not launch_mode:
        # ВИДАЛЕНО перевірку course_line_present - тепер завжди дозволяємо region markers + course parsing
        if True:  # завжди виконуємо блок регіональних маркерів
            # Пропускаем если нет ни одного упоминания угрозы вообще
            if not has_threat(text):
                return None
            threat_type, icon = classify(text)
            tracks = []
            # deduplicate by name
            seen_names = set()
            # Directional offset helper
            def directional_offset(rlabel: str, lat: float, lng: float):
                base = rlabel.lower().split()[0]
                full = text  # already lower
                # detect "на схід <base>", "схід <base>", etc., but ignore origins "з південного сходу" for that base
                # We only tag if phrase contains base key AFTER direction (targeting side), not originating "з <dir> ..." alone.
                directions = [
                    ('схід', 'east', (0.0, 0.9)),
                    ('захід', 'west', (0.0, -0.9)),
                    ('північ', 'north', (0.7, 0.0)),
                    ('південь', 'south', (-0.7, 0.0))
                ]
                applied = None
                for word, code, (dlat, dlng) in directions:
                    patterns = [f"на {word} {base}", f" {word} {base}"]
                    if any(pat in full for pat in patterns) and f"з {word}" not in full:
                        applied = (code, dlat, dlng)
                        break
                if not applied:
                    return lat, lng, rlabel
                _, dlat, dlng = applied
                nlat = max(43.0, min(53.5, lat + dlat))
                nlng = max(21.0, min(41.0, lng + dlng))
                human = {'east':'схід','west':'захід','north':'північ','south':'південь'}[applied[0]]
                return nlat, nlng, f"{rlabel} ({human})"
            for idx, (rname, (lat,lng), snippet) in enumerate(region_hits, 1):
                if rname in seen_names: continue
                seen_names.add(rname)
                adj_lat, adj_lng, adj_label = directional_offset(rname, lat, lng)
                tracks.append({
                    'id': f"{mid}_{idx}", 'place': adj_label, 'lat': adj_lat, 'lng': adj_lng,
                    'threat_type': threat_type, 'text': snippet[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'region_multi'
                })
            if tracks:
                return tracks

    # --- Single border oblast KAB launch: place marker at predefined border point ---
    if len(region_hits) == 1 and 'каб' in lower and ('пуск' in lower or 'пуски' in lower):
        rname, (olat, olng), snippet = region_hits[0]
        # базовые ключи для соответствия
        key = rname.lower()
        BORDER_POINTS = {
            'донеччина': (48.20, 37.90),
            'донецька область': (48.20, 37.90),
            'сумщина': (51.30, 34.40),
            'сумська область': (51.30, 34.40),
            'чернігівщина': (51.75, 31.60),
            'чернігівська обл.': (51.75, 31.60),
            'харківщина': (50.25, 36.85),
            'харківська обл.': (50.25, 36.85),
            'луганщина': (48.90, 39.40),
            'луганська область': (48.90, 39.40),
            'запорізька обл.': (47.55, 35.60),
            'херсонська обл.': (46.65, 32.60)
        }
        # нормализация ключа (удаляем регистр / лишние пробелы)
        k_simple = key.replace('’','').replace("'",'').strip()
        # попытка прямого поиска
        coord = None
        for bk, bcoord in BORDER_POINTS.items():
            if bk in k_simple:
                coord = bcoord
                break
        if coord:
            threat_type, icon = classify(text)
            return [{
                'id': str(mid), 'place': rname + ' (кордон)', 'lat': coord[0], 'lng': coord[1],
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'border_kab'
            }]

    # --- Pattern: multiple shaheds with counts / directions / near-pass ("повз") ---
    # Handles composite direction phrases (південного сходу -> південний схід, північно-захід тощо)
    # Examples: "14 шахедів ... 3 на Покровське з півдня, 9 на Петропавлівку з південного сходу, 2 на Шахтарське з півдня"
    #           "16 шахедів ... 2 повз Терентівку на північ, 6 на Юріївку з півдня, 7 повз Межову північно-захід" etc.
    if 'шахед' in lower and ((' на ' in lower) or (' повз ' in lower)):
        segs = re.split(r'[\n,⚠;]+', lower)
        found = []
        # Direction phrases may appear after 'з', 'зі', 'із', 'на'. Capture full tail then normalize.
        pat_on = re.compile(r'(\d{1,2})\s+на\s+([a-zа-яіїєґ\-ʼ\']{3,})(?:у|а|е)?(?:\s+((?:з|зі|із|на)\s+[a-zа-яіїєґ\-\s]+))?')
        pat_povz = re.compile(r'(\d{1,2})\s+повз\s+([a-zа-яіїєґ\-ʼ\']{3,})(?:у|а|е)?(?:\s+(?:на\s+)?([a-zа-яіїєґ\-\s]+))?')
        def normalize_direction(raw_dir: str) -> str:
            if not raw_dir:
                return ''
            d = raw_dir.lower().strip()
            # remove leading prepositions
            d = re.sub(r'^(з|зі|із|на|від)\s+', '', d)
            d = d.replace('–','-')
            # unify hyphen variants to space-separated tokens
            d = d.replace('-', ' ')
            d = re.sub(r'\s+', ' ', d).strip()
            # morphological endings -> base cardinal forms
            repl = [
                (r'південного сходу', 'південний схід'),
                (r'північного сходу', 'північний схід'),
                (r'південного заходу', 'південний захід'),
                (r'північного заходу', 'північний захід'),
                (r'півдня', 'південь'),
                (r'півночі', 'північ'),
                (r'сходу', 'схід'),
                (r'заходу', 'захід')
            ]
            for pat, rep in repl:
                d = re.sub(pat, rep, d)
            # collapse duplicate words
            parts = []
            seen = set()
            for tok in d.split():
                if tok in seen:
                    continue
                seen.add(tok)
                parts.append(tok)
            return ' '.join(parts)
        for seg in segs:
            # Strip common trailing separators (colon, semicolon, space, slash, backslash)
            s = seg.strip(':; /\\')
            if not s or s.isdigit():
                continue
            matches = []
            matches.extend(list(pat_on.finditer(s)))
            matches.extend(list(pat_povz.finditer(s)))
            for m in matches:
                cnt = int(m.group(1))
                place_token = (m.group(2) or '').strip("-'ʼ")
                raw_dir = ''
                # pat_on group(3); pat_povz group(3)
                if len(m.groups()) >= 3:
                    raw_dir = (m.group(3) or '').strip()
                direction = normalize_direction(raw_dir)
                place_token = place_token.replace('ʼ',"'")
                variants = {place_token}
                # heuristic nominative recovery
                if place_token.endswith('ку'): variants.add(place_token[:-2]+'ка')
                if place_token.endswith('ву'): variants.add(place_token[:-2]+'ва')
                if place_token.endswith('ову'): variants.add(place_token[:-3]+'ова')
                if place_token.endswith('ю'):
                    variants.add(place_token[:-1]+'я'); variants.add(place_token[:-1]+'а')
                if place_token.endswith('у'): variants.add(place_token[:-1]+'а')
                if place_token.endswith('ому'):
                    variants.add(place_token[:-3]+'е'); variants.add(place_token[:-3])
                matched_coord = None; matched_name = None
                for var in variants:
                    if var in CITY_COORDS:
                        matched_coord = CITY_COORDS[var]; matched_name = var; break
                if matched_coord:
                    plat, plng = matched_coord
                    found.append((matched_name, plat, plng, cnt, direction, s[:160]))
        if found:
            threat_type, icon = classify(text)
            tracks = []
            for idx,(p, plat, plng, cnt, direction, snippet) in enumerate(found,1):
                base_label = f"{p.title()} ({cnt})"
                if direction:
                    base_label += f" ←{direction}"
                tracks.append({
                    'id': f"{mid}_s{idx}", 'place': base_label, 'lat': plat, 'lng': plng,
                    'threat_type': threat_type, 'text': snippet[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'multi_shah_ed', 'count': cnt
                })
            if found and not tracks:
                log.debug(f"multi_shah_ed matched segments but no tracks mid={mid} raw={found}")
            if tracks:
                log.debug(f"multi_shah_ed tracks mid={mid} -> {[t['place'] for t in tracks]}")
                return tracks

    # --- Per-line UAV course / area city targeting ("БпЛА курсом на <місто>", "8х БпЛА в районі <міста>", "БпЛА на <місто>") ---
    # Triggered when region multi list suppressed earlier due to presence of course lines or simple "на" pattern.
    if 'бпла' in lower and ('курс' in lower or 'в районі' in lower or 'в напрямку' in lower or 'в бік' in lower or 'від' in lower or 'околиц' in lower or 'сектор' in lower or 'бпла на ' in lower or (re.search(r'\d+\s*[xх×]?\s*бпла\s+на\s+', lower))):
        add_debug_log(f"UAV course parser triggered for message length: {len(text)} chars", "uav_course")

        # --- EARLY CHECK: Black Sea aquatory (e.g. "курсом на Миколаїв з акваторії Чорного моря" or "15 шахедів з моря на Ізмаїл") ---
        # Must check BEFORE "курсом на" parser to prevent placing marker on target city
        is_black_sea = (('акватор' in lower or 'акваторії' in lower) and ('чорного моря' in lower or 'чорне море' in lower or 'чорному морі' in lower)) or \
                       ('з моря' in lower and ('курс' in lower or 'на ' in lower)) or \
                       ('з чорного моря' in lower)

        if is_black_sea:
            # Extract target region/direction if mentioned
            m_target = re.search(r'курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower)
            m_direction = re.search(r'на\s+(північ|південь|схід|захід|північний\s+схід|північний\s+захід|південний\s+схід|південний\s+захід)', lower)
            m_region = re.search(r'(одещин|одеськ|миколаїв|херсон)', lower)

            target_info = None
            sea_lat, sea_lng = 45.3, 30.7  # Default: northern Black Sea central coords

            # Adjust position based on direction/region
            if m_direction:
                direction = m_direction.group(1)
                if 'південь' in direction:
                    sea_lat = 45.0  # Further south
                elif 'північ' in direction:
                    sea_lat = 45.6  # Further north
                if 'схід' in direction:
                    sea_lng = 31.2  # Further east
                elif 'захід' in direction:
                    sea_lng = 30.2  # Further west

            if m_region:
                region_name = m_region.group(1)
                if 'одещин' in region_name or 'одеськ' in region_name:
                    # South of Odesa region - in the sea 50km offshore
                    sea_lat, sea_lng = 45.7, 30.7
                    target_info = 'Одещини'
                elif 'миколаїв' in region_name:
                    sea_lat, sea_lng = 45.9, 31.4
                    target_info = 'Миколаївщини'
                elif 'херсон' in region_name:
                    sea_lat, sea_lng = 45.7, 32.5
                    target_info = 'Херсонщини'

            if m_target:
                tc = m_target.group(1).lower()
                tc = UA_CITY_NORMALIZE.get(tc, tc)
                target_info = tc.title()

            threat_type, icon = classify(text)
            place_label = 'Акваторія Чорного моря'
            if target_info:
                place_label += f' (на {target_info})'

            # Try to find target city coordinates for trajectory
            target_coords = None
            if m_target:
                tc_normalized = m_target.group(1).lower()
                tc_normalized = UA_CITY_NORMALIZE.get(tc_normalized, tc_normalized)
                if tc_normalized in CITY_COORDS:
                    target_coords = CITY_COORDS[tc_normalized]

            result = {
                'id': str(mid), 'place': place_label, 'lat': sea_lat, 'lng': sea_lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'black_sea_course'
            }

            # Add trajectory data if we have target coordinates
            if target_coords:
                result['trajectory'] = {
                    'start': [sea_lat, sea_lng],
                    'end': list(target_coords),
                    'target': target_info
                }

            return [result]

        original_text_norm = re.sub(r'(?i)(\b[А-Яа-яЇїІіЄєҐґ\-]{3,}(?:щина|область|обл\.)):(?!\s*\n)', r'\1:\n', original_text)
        lines_with_region = []
        current_region_hdr = None
        for raw_ln in original_text_norm.splitlines():
            ln_stripped = raw_ln.strip()
            if not ln_stripped:
                continue
            low_ln = ln_stripped.lower()
            # Allow region header if line ends with ':' even if preceded by emoji or bullets
            if low_ln.endswith(':'):
                # remove leading emojis/symbols
                cleaned_hdr = re.sub(r'^[^a-zа-яіїєґ]+','', low_ln[:-1])
                base_hdr = cleaned_hdr.strip()
                log.debug(f"mid={mid} region_header_check: '{low_ln}' -> cleaned: '{base_hdr}' -> found: {base_hdr in OBLAST_CENTERS}")
                if base_hdr in OBLAST_CENTERS:
                    current_region_hdr = base_hdr
                    log.debug(f"mid={mid} region_header_set: '{base_hdr}'")
                continue
            # split by semicolons; also break on pattern like " 2х БпЛА курсом" inside the same segment later
            subparts = [p.strip() for p in re.split(r'[;]+', ln_stripped) if p.strip()]
            for part in subparts:
                lines_with_region.append((part, current_region_hdr))
        # Further split segments that contain multiple "БпЛА курс" phrases glued together
        multi_start_re = re.compile(r'(?:\d+\s*[xх×]?\s*)?бпла\s*курс', re.IGNORECASE)
        expanded = []
        for part, region_hdr in lines_with_region:
            low_part = part.lower()
            starts = [m.start() for m in multi_start_re.finditer(low_part)]
            if len(starts) <= 1:
                expanded.append((part, region_hdr))
                continue
            for idx, s in enumerate(starts):
                seg_start = s
                seg_end = starts[idx+1] if idx+1 < len(starts) else len(low_part)
                segment = part[seg_start:seg_end].strip()
                if segment:
                    expanded.append((segment, region_hdr))
        if expanded:
            lines_with_region = expanded
        course_tracks = []
        pat_count_course = re.compile(r'^(\d+(?:-\d+)?)\s*[xх×]?\s*бпла(?:\s+пролетіли)?.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-’ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_course = re.compile(r'бпла(?:\s+пролетіли)?.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-’ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_area = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(?:.*?\s+)?в\s+районі\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,60}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)  # Fixed: added н.п. support
        pat_napramku = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+[➡️⬆️⬇️⬅️↗️↘️↙️↖️]*\s*(?:в|у)\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_sektor = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+в\s+секторі\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_simple_na = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_complex_napramku = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на/через\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)\s+в\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_napramku_ta = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(?:в|у)\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)\s+та\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_okolytsi = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на\s+околицях\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_vid_do = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+від\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)\s+до\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_vik = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+[➡️⬆️⬇️⬅️↗️↘️↙️↖️]*\s*(?:в|у)\s+бік\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        if re.search(r'бпла.*?курс(?:ом)?\s+на\s+кіпт[ії]', lower):
            coords = SETTLEMENT_FALLBACK.get('кіпті')
            if coords:
                lat, lng = coords
                threat_type, icon = classify(original_text)
                return [{
                    'id': f"{mid}_kipti_course", 'place': 'Кіпті', 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'course_kipti'
                }]
        def norm_city_token(tok: str) -> str:
            t = tok.lower().strip(" .,'’ʼ`-:")
            t = t.replace("'", "'")  # Normalize curly quotes
            if t.endswith('ку'): t = t[:-2] + 'ка'
            elif t.endswith('ву'): t = t[:-2] + 'ва'
            elif t.endswith('ову'): t = t[:-3] + 'ова'
            elif t.endswith('ю'): t = t[:-1] + 'я'
            elif t.endswith('у'): t = t[:-1] + 'а'
            if t.startswith('нову '):
                t = 'нова ' + t[5:]
            t = t.replace('водолагу','водолога')
            return t

        # Pattern to extract oblast from parentheses like "(Полтавська обл.)" or "(Харківська область)"
        pat_oblast_in_parens = re.compile(r'\(([А-Яа-яЇїІіЄєҐґ\-]+)\s*обл\.?\)?', re.IGNORECASE)

        for ln, region_hdr in lines_with_region:
            ln_low = ln.lower()
            if 'бпла' not in ln_low:
                continue

            # PRIORITY: Extract oblast from parentheses in the line itself (e.g., "Семенівку (Полтавська обл.)")
            # This overrides the region header from channel
            line_oblast_match = pat_oblast_in_parens.search(ln)
            if line_oblast_match:
                oblast_name = line_oblast_match.group(1).lower()
                # Map to standard oblast name
                oblast_map = {
                    'полтавськ': 'полтавщина', 'полтавська': 'полтавщина',
                    'харківськ': 'харківщина', 'харківська': 'харківщина',
                    'чернігівськ': 'чернігівщина', 'чернігівська': 'чернігівщина',
                    'сумськ': 'сумщина', 'сумська': 'сумщина',
                    'київськ': 'київщина', 'київська': 'київщина',
                    'одеськ': 'одещина', 'одеська': 'одещина',
                    'миколаївськ': 'миколаївщина', 'миколаївська': 'миколаївщина',
                    'херсонськ': 'херсонщина', 'херсонська': 'херсонщина',
                    'запорізьк': 'запорізька', 'запорізька': 'запорізька',
                    'дніпропетровськ': 'дніпропетровщина', 'дніпропетровська': 'дніпропетровщина',
                    'донецьк': 'донецька', 'донецька': 'донецька',
                    'луганськ': 'луганська', 'луганська': 'луганська',
                    'черкаськ': 'черкащина', 'черкаська': 'черкащина',
                    'житомирськ': 'житомирщина', 'житомирська': 'житомирщина',
                    'вінницьк': 'вінниччина', 'вінницька': 'вінниччина',
                    'рівненськ': 'рівненщина', 'рівненська': 'рівненщина',
                    'волинськ': 'волинь', 'волинська': 'волинь',
                    'львівськ': 'львівщина', 'львівська': 'львівщина',
                    'тернопільськ': 'тернопільщина', 'тернопільська': 'тернопільщина',
                    'хмельницьк': 'хмельниччина', 'хмельницька': 'хмельниччина',
                    'івано-франківськ': 'івано-франківщина', 'івано-франківська': 'івано-франківщина',
                    'закарпатськ': 'закарпаття', 'закарпатська': 'закарпаття',
                    'чернівецьк': 'чернівецька', 'чернівецька': 'чернівецька',
                    'кіровоградськ': 'кіровоградщина', 'кіровоградська': 'кіровоградщина',
                }
                for key, val in oblast_map.items():
                    if oblast_name.startswith(key):
                        region_hdr = val
                        log.info(f"mid={mid} OVERRIDE region_hdr from line: '{oblast_name}' -> '{region_hdr}'")
                        break

            add_debug_log(f"Processing UAV line: '{ln[:100]}...' (region: {region_hdr})", "uav_course")

            # PRIORITY: Handle "БпЛА із/з [source] ➡️ у напрямку [target]" - marker at SOURCE, not target
            # Example: "🛵 БпЛА із Чернігівщини ➡️ у напрямку Києва" -> marker at Чернігівщина
            m_iz_napramku = re.search(r'бпла\s+(?:із|з)\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)\s*[➡️⬆️⬇️⬅️↗️↘️↙️↖️]*\s*(?:в|у)\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', ln_low, re.IGNORECASE)
            if m_iz_napramku:
                source_region = m_iz_napramku.group(1).strip()
                target_name = m_iz_napramku.group(2).strip()
                add_debug_log(f"Found 'із X у напрямку Y' pattern: source={source_region}, target={target_name}", "uav_course")
                
                # Get source coordinates (this is where UAV currently is!)
                source_norm = norm_city_token(source_region)
                coords = CITY_COORDS.get(source_norm) or OBLAST_CENTERS.get(source_norm) or (SETTLEMENTS_INDEX.get(source_norm) if SETTLEMENTS_INDEX else None)
                if not coords:
                    # Try as oblast
                    for obl_key, obl_coords in OBLAST_CENTERS.items():
                        if source_norm in obl_key or obl_key in source_norm:
                            coords = obl_coords
                            break
                
                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(text)
                    label = f"{source_norm.title()} → {target_name.title()}"
                    
                    # Get target coordinates for trajectory
                    target_norm = norm_city_token(target_name)
                    target_coords = CITY_COORDS.get(target_norm) or OBLAST_CENTERS.get(target_norm) or (SETTLEMENTS_INDEX.get(target_norm) if SETTLEMENTS_INDEX else None)
                    if not target_coords:
                        target_coords = UKRAINE_ALL_SETTLEMENTS.get(target_norm)
                    
                    trajectory_data = None
                    if target_coords:
                        target_lat, target_lng = target_coords if len(target_coords) == 2 else (target_coords[0], target_coords[1])
                        trajectory_data = {
                            'start': [lat, lng],
                            'end': [target_lat, target_lng],
                            'target': target_name.title()
                        }
                    
                    course_tracks.append({
                        'id': f"{mid}_iz_napramku_{source_norm}", 'place': label, 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'uav_iz_napramku', 'count': 1,
                        'trajectory': trajectory_data
                    })
                    add_debug_log(f"Created marker at SOURCE: {source_norm} ({lat}, {lng}) with trajectory to {target_name}", "uav_course")
                    continue
                else:
                    add_debug_log(f"Could not find coords for source '{source_norm}'", "uav_course")

            # PRIORITY: Handle "БПЛА [city] курсом на [target]" - marker at CITY (current location), not target
            # Example: "БПЛА Славутич курсом на Київщина" -> marker at Славутич
            m_city_kursom = re.search(r'бпла\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`]{3,30})\s+курсом\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', ln_low, re.IGNORECASE)
            if m_city_kursom:
                current_city = m_city_kursom.group(1).strip()
                target_name = m_city_kursom.group(2).strip()
                add_debug_log(f"Found 'БПЛА [city] курсом на [target]' pattern: city={current_city}, target={target_name}", "uav_course")
                
                # Get current city coordinates (this is where UAV is NOW!)
                city_norm = norm_city_token(current_city)
                coords = CITY_COORDS.get(city_norm) or (SETTLEMENTS_INDEX.get(city_norm) if SETTLEMENTS_INDEX else None)
                if not coords:
                    coords = UKRAINE_ALL_SETTLEMENTS.get(city_norm)
                if not coords:
                    # Try region-aware lookup
                    if region_hdr:
                        oblast_key = region_hdr.replace('щина', 'ська').replace('ь', 'ська')
                        for obl in ['ська', 'ка', 'а', '']:
                            test_key = (city_norm, oblast_key.rstrip('а') + obl if obl else oblast_key)
                            if test_key in UKRAINE_SETTLEMENTS_BY_OBLAST:
                                coords = UKRAINE_SETTLEMENTS_BY_OBLAST[test_key]
                                break
                
                if coords:
                    lat, lng = coords if len(coords) == 2 else (coords[0], coords[1])
                    threat_type, icon = classify(text)
                    label = f"{city_norm.title()} → {target_name.title()}"
                    
                    # Get target coordinates for trajectory
                    target_norm = norm_city_token(target_name)
                    target_coords = CITY_COORDS.get(target_norm) or OBLAST_CENTERS.get(target_norm) or (SETTLEMENTS_INDEX.get(target_norm) if SETTLEMENTS_INDEX else None)
                    if not target_coords:
                        target_coords = UKRAINE_ALL_SETTLEMENTS.get(target_norm)
                    
                    trajectory_data = None
                    if target_coords:
                        target_lat, target_lng = target_coords if len(target_coords) == 2 else (target_coords[0], target_coords[1])
                        trajectory_data = {
                            'start': [lat, lng],
                            'end': [target_lat, target_lng],
                            'target': target_name.title()
                        }
                    
                    course_tracks.append({
                        'id': f"{mid}_city_kursom_{city_norm}", 'place': label, 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'uav_city_kursom', 'count': 1,
                        'trajectory': trajectory_data
                    })
                    add_debug_log(f"Created marker at CITY: {city_norm} ({lat}, {lng}) with trajectory to {target_name}", "uav_course")
                    continue
                else:
                    add_debug_log(f"Could not find coords for city '{city_norm}'", "uav_course")

            # Check for complex pattern "на/через X в напрямку Y" first
            m_complex = pat_complex_napramku.search(ln_low)
            if m_complex:
                count = int(m_complex.group(1)) if m_complex.group(1) else 1
                city1 = m_complex.group(2)  # через це місто
                city2 = m_complex.group(3)  # в напрямку цього міста

                # Process both cities
                for city_raw in [city1, city2]:
                    multi_norm = _resolve_city_candidate(city_raw)
                    base = norm_city_token(multi_norm)
                    
                    # PRIORITY: Try region-specific lookup first if region is known
                    coords = None
                    if region_hdr:
                        region_key = f"{base}_{region_hdr}"
                        coords = CITY_COORDS.get(region_key)
                    
                    # Fallback to base lookup
                    if not coords:
                        coords = CITY_COORDS.get(base) or (SETTLEMENTS_INDEX.get(base) if SETTLEMENTS_INDEX else None)
                    if not coords:
                        try:
                            coords = region_enhanced_coords(base, region_hint_override=region_hdr)
                        except Exception:
                            coords = None
                    # Try OpenCage API if still no coordinates
                    if not coords and GEOCODER_AVAILABLE:
                        try:
                            coords = opencage_geocode(base, region=region_hdr)
                        except Exception:
                            pass
                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(text)
                        for i in range(1, count+1):
                            label = base.title()
                            if count > 1:
                                label += f" ({i}/{count})"
                            if region_hdr and region_hdr not in label.lower():
                                label += f" [{region_hdr.title()}]"
                            course_tracks.append({
                                'id': f"{mid}_complex_{base}_{i}", 'place': label, 'lat': lat, 'lng': lng,
                                'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                                'marker_icon': icon, 'source_match': 'uav_complex', 'count': 1
                            })
                continue  # Skip to next line

            # Check for "від X до Y" pattern (trajectory)
            m_vid_do = pat_vid_do.search(ln_low)
            if m_vid_do:
                count = int(m_vid_do.group(1)) if m_vid_do.group(1) else 1
                city1 = m_vid_do.group(2)  # від цього міста
                city2 = m_vid_do.group(3)  # до цього міста

                # Process both cities
                for city_raw in [city1, city2]:
                    multi_norm = _resolve_city_candidate(city_raw)
                    base = norm_city_token(multi_norm)
                    
                    # PRIORITY: Try region-specific lookup first if region is known
                    coords = None
                    if region_hdr:
                        region_key = f"{base}_{region_hdr}"
                        coords = CITY_COORDS.get(region_key)
                    
                    # Fallback to base lookup
                    if not coords:
                        coords = CITY_COORDS.get(base) or (SETTLEMENTS_INDEX.get(base) if SETTLEMENTS_INDEX else None)
                    if not coords:
                        try:
                            coords = region_enhanced_coords(base, region_hint_override=region_hdr)
                        except Exception:
                            coords = None
                    if not coords and GEOCODER_AVAILABLE:
                        try:
                            coords = opencage_geocode(base, region=region_hdr)
                        except Exception:
                            pass
                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(text)
                        for i in range(1, count+1):
                            label = base.title()
                            if count > 1:
                                label += f" ({i}/{count})"
                            if region_hdr and region_hdr not in label.lower():
                                label += f" [{region_hdr.title()}]"
                            course_tracks.append({
                                'id': f"{mid}_viddo_{base}_{i}", 'place': label, 'lat': lat, 'lng': lng,
                                'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                                'marker_icon': icon, 'source_match': 'uav_vid_do', 'count': 1
                            })
                continue

            # Check for "в напрямку X та Y" pattern (multiple cities)
            m_ta = pat_napramku_ta.search(ln_low)
            if m_ta:
                count = int(m_ta.group(1)) if m_ta.group(1) else 1
                city1 = m_ta.group(2)
                city2 = m_ta.group(3)

                # Process both cities
                for city_raw in [city1, city2]:
                    multi_norm = _resolve_city_candidate(city_raw)
                    base = norm_city_token(multi_norm)
                    
                    # PRIORITY: Try region-specific lookup first if region is known
                    coords = None
                    if region_hdr:
                        region_key = f"{base}_{region_hdr}"
                        coords = CITY_COORDS.get(region_key)
                    
                    # Fallback to base lookup
                    if not coords:
                        coords = CITY_COORDS.get(base) or (SETTLEMENTS_INDEX.get(base) if SETTLEMENTS_INDEX else None)
                    if not coords:
                        try:
                            coords = region_enhanced_coords(base, region_hint_override=region_hdr)
                        except Exception:
                            coords = None
                    if not coords and GEOCODER_AVAILABLE:
                        try:
                            coords = opencage_geocode(base, region=region_hdr)
                        except Exception:
                            pass
                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(text)
                        for i in range(1, count+1):
                            label = base.title()
                            if count > 1:
                                label += f" ({i}/{count})"
                            if region_hdr and region_hdr not in label.lower():
                                label += f" [{region_hdr.title()}]"
                            course_tracks.append({
                                'id': f"{mid}_ta_{base}_{i}", 'place': label, 'lat': lat, 'lng': lng,
                                'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                                'marker_icon': icon, 'source_match': 'uav_ta', 'count': 1
                            })
                continue

            count = None; city = None; approx_flag = False
            m1 = pat_count_course.search(ln_low)
            if m1:
                count = int(m1.group(1)); city = m1.group(2)
            else:
                m2 = pat_area.search(ln_low)
                if m2:
                    if m2.group(1):
                        count = int(m2.group(1))
                    city = m2.group(2)
                else:
                    m3 = pat_napramku.search(ln_low)
                    if m3:
                        if m3.group(1):
                            count = int(m3.group(1))
                        city = m3.group(2)
                    else:
                        m3_sektor = pat_sektor.search(ln_low)
                        if m3_sektor:
                            if m3_sektor.group(1):
                                count = int(m3_sektor.group(1))
                            city = m3_sektor.group(2)
                        else:
                            m4 = pat_course.search(ln_low)
                            if m4:
                                city = m4.group(1)
                            else:
                                m5 = pat_okolytsi.search(ln_low)
                                if m5:
                                    if m5.group(1):
                                        count = int(m5.group(1))
                                    city = m5.group(2)
                                else:
                                    m6 = pat_simple_na.search(ln_low)
                                    if m6:
                                        if m6.group(1):
                                            count = int(m6.group(1))
                                        city = m6.group(2)
                                    else:
                                        m7 = pat_vik.search(ln_low)
                                        if m7:
                                            if m7.group(1):
                                                count = int(m7.group(1))
                                            city = m7.group(2)
            if not city:
                add_debug_log("No city found in UAV line", "uav_course")
                continue
            add_debug_log(f"Found city '{city}' in UAV line", "uav_course")
            multi_norm = _resolve_city_candidate(city)
            base = norm_city_token(multi_norm)
            add_debug_log(f"City normalized to '{base}'", "uav_course")

            # FILTER: Skip oblast/region names (e.g., "БпЛА на Дніпропетровщині" should be regional threat, not city marker)
            oblast_suffixes = ['щина', 'щині', 'область', 'обл']
            if any(base.endswith(suffix) for suffix in oblast_suffixes):
                add_debug_log(f"Skipping oblast name '{base}' - this is a regional threat, not a city target", "uav_course")
                continue

            # PRIORITY: Try region-specific variant first
            coords = None
            if region_hdr:
                # Try variant with region suffix (underscore format used by Nominatim cache)
                region_key = f"{base}_{region_hdr}"
                coords = CITY_COORDS.get(region_key)
                if coords:
                    add_debug_log(f"Found region-specific coordinates for '{region_key}': {coords}", "uav_course")
                else:
                    # Also try old format for backwards compatibility
                    region_variant = f"{base}({region_hdr})"
                    coords = CITY_COORDS.get(region_variant)
                    if coords:
                        add_debug_log(f"Found region-specific coordinates (old format) for '{region_variant}': {coords}", "uav_course")

            # Fallback to base name without region
            if not coords:
                coords = CITY_COORDS.get(base) or (SETTLEMENTS_INDEX.get(base) if SETTLEMENTS_INDEX else None)
                add_debug_log(f"Coordinates lookup for '{base}': {coords}", "uav_course")
            if not coords:
                try:
                    coords = region_enhanced_coords(base, region_hint_override=region_hdr)
                except Exception:
                    coords = None
            # Try OpenCage API if still no coordinates
            if not coords and GEOCODER_AVAILABLE:
                try:
                    coords = opencage_geocode(base, region=region_hdr)
                except Exception:
                    pass
            if not coords:
                # Fallback: if we have a region header, place placeholder near its oblast center with slight jitter
                if region_hdr and region_hdr in OBLAST_CENTERS:
                    rlat, rlng = OBLAST_CENTERS[region_hdr]
                    # deterministic jitter based on hash of city token
                    h = abs(hash(base)) % 1000 / 1000.0
                    lat = max(43.0, min(53.5, rlat + (h - 0.5) * 0.4))
                    lng = max(21.0, min(41.0, rlng + (h - 0.5) * 0.6))
                    coords = (lat, lng)
                    approx_flag = True
                else:
                    # skip THIS city but continue processing other cities
                    add_debug_log(f"Skipping unrecognized city '{base}' - no coordinates and no region context", "uav_course")
                    continue
            # Cache with region key if region is known
            cache_key = f"{base}_{region_hdr}" if region_hdr else base
            if cache_key not in CITY_COORDS:
                CITY_COORDS[cache_key] = coords
            lat, lng = coords
            threat_type, icon = classify(text)
            # Generate individual markers per drone for progressive map loading
            total = count or 1
            for i in range(1, total+1):
                label = base.title()
                if total > 1:
                    label += f" ({i}/{total})"
                if region_hdr and region_hdr not in label.lower():
                    label += f" [{region_hdr.title()}]"
                if approx_flag:
                    label += ' ~'
                course_tracks.append({
                    'id': f"{mid}_c{len(course_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'course_city_unit', 'count': 1
                })
                add_debug_log(f"Created course track for '{label}' at {lat}, {lng}", "uav_course")
        add_debug_log(f"Total course tracks generated: {len(course_tracks)}", "uav_course")
        log.debug(f"mid={mid} course_tracks_generated: {len(course_tracks)} tracks")
        if course_tracks:
            return course_tracks
        # Salvage fallback: large multi-line message with many 'бпла курсом' but parser produced nothing
        try:
            ll_full = text.lower()
            if course_tracks == [] and ll_full.count('бпла') >= 5 and ll_full.count('курс') >= 5:
                pat_salv = re.compile(r'(?:\d+\s*[xх×]?\s*)?бпла[^\n]{0,60}?курс(?:ом)?\s+на\s+([a-zа-яіїєґ\-ʼ"“”\'`\s]{3,40})', re.IGNORECASE)
                raw_hits = [m.group(1).strip() for m in pat_salv.finditer(ll_full)]
                uniq = []
                for h in raw_hits:
                    if h and h not in uniq:
                        uniq.append(h)
                salvage_tracks = []
                for idx, token in enumerate(uniq, 1):
                    base_tok = _resolve_city_candidate(token)
                    base_tok = norm_city_token(base_tok)
                    coords = CITY_COORDS.get(base_tok) or (SETTLEMENTS_INDEX.get(base_tok) if SETTLEMENTS_INDEX else None)
                    if not coords:
                        continue
                    lat, lng = coords
                    threat_type, icon = classify(text)
                    salvage_tracks.append({
                        'id': f"{mid}_sf{idx}", 'place': base_tok.title(), 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': token[:120], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'salvage_course_multi'
                    })
                if salvage_tracks:
                    log.debug(f"salvage_course_multi generated {len(salvage_tracks)} tracks mid={mid}")
                    return salvage_tracks
        except Exception as _e_salv:
            log.debug(f'salvage fallback error mid={mid}: {_e_salv}')

    # --- Generic multi-line UAV near-pass counts (e.g. "5х бпла повз Барвінкове") ---
    if 'бпла' in lower and 'повз' in lower and re.search(r'\d+[xх]\s*бпла', lower):
        lines_near = [ln.strip() for ln in lower.split('\n') if ln.strip()]
        near_tracks = []
        pat_near = re.compile(r'(\d+)[xх]\s*бпла[^\n]*?повз\s+([a-zа-яіїєґ\-ʼ\']{3,})')
        for ln in lines_near:
            m = pat_near.search(ln)
            if not m:
                continue
            cnt = int(m.group(1))
            place = (m.group(2) or '').strip("-'ʼ")
            variants = {place}
            if place.endswith('е'): variants.add(place[:-1])
            if place.endswith('ю'):
                variants.add(place[:-1]+'я'); variants.add(place[:-1]+'а')
            if place.endswith('у'):
                variants.add(place[:-1]+'а')
            if place.endswith('ому'):
                variants.add(place[:-3])
            if place.endswith('ове'):
                variants.add(place[:-2]+'’я')  # crude alt
            matched=None; mname=None
            for v in variants:
                if v in CITY_COORDS:
                    matched=CITY_COORDS[v]; mname=v; break
            if not matched and SETTLEMENTS_INDEX:
                for v in variants:
                    if v in SETTLEMENTS_INDEX:
                        matched=SETTLEMENTS_INDEX[v]; mname=v; break
            if not matched:
                # OpenCage fallback
                try:
                    for v in variants:
                        oc = region_enhanced_coords(v)
                        if oc:
                            matched=oc; mname=v; break
                except Exception:
                    matched=None
            if matched:
                if mname not in CITY_COORDS:
                    CITY_COORDS[mname]=matched
                lat,lng = matched
                threat_type, icon = classify(text)
                near_tracks.append({
                    'id': f"{mid}_n{len(near_tracks)+1}", 'place': f"{mname.title()} ({cnt})", 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'uav_near_pass', 'count': cnt
                })
        if near_tracks:
            return near_tracks

    # --- Late parenthetical specific settlement fallback (e.g. direction to oblast but (затока)) ---
    if has_threat(original_text.lower()) and '(' in original_text and ')' in original_text:
        p_tokens = re.findall(r'\(([A-Za-zА-Яа-яЇїІіЄєҐґ\-\s]{3,})\)', original_text.lower())
        if p_tokens:
            cand = p_tokens[-1].strip()
            cand = re.sub(r'^(смт|с\.|м\.|місто|селище)\s+','', cand)
            base_cand = UA_CITY_NORMALIZE.get(cand, cand)
            coords = CITY_COORDS.get(base_cand) or SETTLEMENTS_INDEX.get(base_cand)
            log.debug(f"late_parenthetical mid={mid} cand={cand} base={base_cand} found={bool(coords)}")
            if coords:
                lat,lng = coords
                threat_type, icon = classify(original_text)
                return [{
                    'id': str(mid), 'place': base_cand.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'late_parenthetical'
                }]

    # --- Settlement matching using external dataset (if provided) (single first match) ---
    if not region_hits:
        # 1) Multi-list form: "Новгород-сіверський, Шостка, Короп, Кролевець - уважно по БПЛА"
        # support both hyphen - and en dash – between list and tail
        dash_idx = None
        for dch in [' - ', ' – ', '- ', '– ']:
            if dch in lower:
                dash_idx = lower.index(dch)
                break
        if ('уважно' in lower or 'по бпла' in lower or 'бпла' in lower) and (',' in lower) and dash_idx is not None:
            left = lower[:dash_idx]
            right = lower[dash_idx+1:]
            if any(k in right for k in ['бпла','дрон','шахед','uav']):
                raw_places = [p.strip() for p in left.split(',') if p.strip()]
                tracks = []
                threat_type, icon = classify(text)
                seen = set()
                for idx, rp in enumerate(raw_places,1):
                    key = rp.replace('й,','й').strip()
                    coords = region_enhanced_coords(key)
                    if coords and key not in seen:
                        seen.add(key)
                        lat,lng = coords
                        tracks.append({
                            'id': f"{mid}_m{idx}", 'place': key.title(), 'lat': lat, 'lng': lng,
                            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'multi_settlement'
                        })
                if tracks:
                    return tracks
        # 2) Single settlement search (fallback) with word-boundary and specificity prioritization
        if SETTLEMENTS_INDEX:
            cand_hits = []
            text_len = len(lower)
            for name in SETTLEMENTS_ORDERED:
                start = 0
                while True:
                    idx = lower.find(name, start)
                    if idx == -1:
                        break
                    before_ok = (idx == 0) or not lower[idx-1].isalnum()
                    after_idx = idx + len(name)
                    after_ok = (after_idx == text_len) or not lower[after_idx].isalnum()
                    if before_ok and after_ok:
                        cand_hits.append(name)
                        break  # only need first occurrence
                    start = idx + 1
            if cand_hits:
                # Prefer longer names; deprioritize generic oblast centers when more specific present
                def score(n: str):
                    base_penalty = -5 if n in ['суми'] and len(cand_hits) > 1 else 0
                    return (len(n) + base_penalty)
                cand_hits.sort(key=score, reverse=True)
                chosen = cand_hits[0]
                lat, lng = SETTLEMENTS_INDEX[chosen]
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': chosen.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon,
                    'source_match': 'settlement'
                }]

    # --- Raion (district) detection ---
    # Ищем конструкции вида "Покровський район", а также множественные "Конотопський та Сумський районы".
    def norm_raion(token: str):
        t = token.lower().strip('- ')
        # унификация дефисов
        t = t.replace('–','-')
        # морфологические окончания -> базовая форма -ський
        t = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$','ський', t)
        return t
    raion_matches = []
    # множественное 'райони'
    plural_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё,\-\s]{4,}?)райони', re.IGNORECASE)
    for pm in plural_pattern.finditer(text):
        segment = pm.group(1)
        # разделяем по 'та' или запятым
        parts = re.split(r'\s+та\s+|,', segment)
        for p in parts:
            cand = p.strip()
            if not cand:
                continue
            # берём последнее слово (Конотопський)
            last = cand.split()[-1]
            base = norm_raion(last)
            if base in RAION_FALLBACK:
                raion_matches.append((base, RAION_FALLBACK[base]))
    # одиночное 'район' (любой падеж: район, району, районом, района)
    raion_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё\-]{4,})\s+район(?:у|ом|а)?', re.IGNORECASE)
    for m_r in raion_pattern.finditer(text):
        base = norm_raion(m_r.group(1))
        if base in RAION_FALLBACK:
            raion_matches.append((base, RAION_FALLBACK[base]))
    # Аббревиатура "р-н" (у т.ч. варианты "р-н.", "рн", "р-н," )
    raion_abbrev_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё\-]{4,})\s+р\s*[-–]?\s*н\.?', re.IGNORECASE)
    for m_ra in raion_abbrev_pattern.finditer(text):
        base = norm_raion(m_ra.group(1))
        if base in RAION_FALLBACK:
            raion_matches.append((base, RAION_FALLBACK[base]))
    if raion_matches:
        threat_type, icon = classify(text)
        tracks = []
        seen = set()
        for idx,(name,(lat,lng)) in enumerate(raion_matches,1):
            # For some districts, show the main city name instead of district name
            district_to_city_mapping = {
                'павлоградський': 'Павлоград',
                'білоцерківський': 'Біла Церква',
                'кременчуцький': 'Кременчук',
                'миколаївський': 'Миколаїв',
                'дніпровський': 'Дніпро'
            }

            if name.lower() in district_to_city_mapping:
                title = district_to_city_mapping[name.lower()]
            else:
                title = f"{name.title()} район"
            if title in seen: continue
            seen.add(title)
            # Maintain alarm overlay state
            if threat_type == 'alarm':
                RAION_ALARMS[name] = {'place': title, 'lat': lat, 'lng': lng, 'since': time.time()}
            elif threat_type == 'alarm_cancel':
                RAION_ALARMS.pop(name, None)
            tracks.append({
                'id': f"{mid}_d{idx}", 'place': title, 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'raion'
            })
        if tracks:
            log.debug(f"RAION_MATCH mid={mid} -> {[t['place'] for t in tracks]}")
            return tracks

    # --- Hromada detection (e.g., "Хотінська територіальна громада") ---
    hromada_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё\-]{4,})\s+територіал(?:ьна|ьної)?\s+громада', re.IGNORECASE)
    hromada_matches = []
    for m_h in hromada_pattern.finditer(text):
        token = m_h.group(1).lower()
        # normalize adjective endings to 'ська'
        base = re.sub(r'(ської|ской|ська|ской)$', 'ська', token)
        if base in HROMADA_FALLBACK:
            hromada_matches.append((base, HROMADA_FALLBACK[base]))
    if hromada_matches:
        threat_type, icon = classify(text)
        tracks = []
        seen = set()
        for idx,(name,(lat,lng)) in enumerate(hromada_matches,1):
            title = f"{name.title()} територіальна громада"
            if title in seen: continue
            seen.add(title)
            tracks.append({
                'id': f"{mid}_h{idx}", 'place': title, 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'hromada'
            })
        if tracks:
            return tracks

    # --- Slash separated settlements PRIORITY (moved earlier so it can't be overridden by region logic) ---
    lower_full_for_slash = text.lower()
    if '/' in lower_full_for_slash and ('бпла' in lower_full_for_slash or 'дрон' in lower_full_for_slash) and any(x in lower_full_for_slash for x in ['х бпла','x бпла',' бпла']):
        # take portion before first dash (— or -) which usually separates counts/other text
        left_part = re.split(r'[—-]', lower_full_for_slash, 1)[0]
        # Remove trailing count token like "5х бпла" from left part to isolate pure settlements
        left_part = re.sub(r'\b\d+[xх]\s*бпла.*$', '', left_part).strip()
        parts = [p.strip() for p in re.split(r'/|\\', left_part) if p.strip()]
        found = []
        # Derive a region stem from any well-known city token to bias geocoding of other parts
        inferred_region = None
        for p in parts:
            base_inf = UA_CITY_NORMALIZE.get(p, p)
            if base_inf in CITY_TO_OBLAST:
                inferred_region = CITY_TO_OBLAST[base_inf]
                break
        for p in parts:
            base = UA_CITY_NORMALIZE.get(p, p)
            coords = CITY_COORDS.get(base)
            if not coords and SETTLEMENTS_INDEX:
                coords = SETTLEMENTS_INDEX.get(base)
            if not coords:
                # If we have inferred region stem, attempt region-qualified geocode first
                if inferred_region and OPENCAGE_API_KEY:
                    oblast_variants = [
                        f"{base} {inferred_region}щина",
                        f"{base} {inferred_region}ська область",
                        f"{base} {inferred_region}ская область"
                    ]
                    for q in oblast_variants:
                        try:
                            coords = geocode_opencage(q)
                            if coords:
                                break
                        except Exception:
                            pass
                if not coords:
                    try:
                        coords = region_enhanced_coords(base)
                    except Exception:
                        coords = None
            if coords:
                found.append((base.title(), coords))
        if found:
            threat_type, icon = classify(text)
            tracks = []
            for idx,(nm,(lat,lng)) in enumerate(found,1):
                if 'курс захід' in lower_full_for_slash:
                    lng -= 0.4
                tracks.append({
                    'id': f"{mid}_s{idx}", 'place': nm, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'slash_combo', 'count': drone_count
                })
            if tracks:
                try:
                    log.debug(f"SLASH_COMBO mid={mid} parts={parts} tracks={[(t['place'], t['lat'], t['lng']) for t in tracks]}")
                except Exception:
                    pass
            if tracks:
                return tracks

    # --- Black Sea aquatory: place marker in sea, not on target city (e.g. "в акваторії чорного моря, курсом на одесу" or "з моря на Ізмаїл") ---
    lower_sea = text.lower()
    is_black_sea = (('акватор' in lower_sea or 'акваторії' in lower_sea) and ('чорного моря' in lower_sea or 'чорне море' in lower_sea or 'чорному морі' in lower_sea)) or \
                   ('з моря' in lower_sea and ('курс' in lower_sea or 'на ' in lower_sea)) or \
                   ('з чорного моря' in lower_sea)

    if is_black_sea:
        # Extract target region/direction if mentioned
        m_target = re.search(r'курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower_sea)
        m_direction = re.search(r'на\s+(північ|південь|схід|захід|північний\s+схід|північний\s+захід|південний\s+схід|південний\s+захід)', lower_sea)
        m_region = re.search(r'(одещин|одеськ|миколаїв|херсон)', lower_sea)

        target_info = None
        sea_lat, sea_lng = 45.3, 30.7  # Default: northern Black Sea central coords

        # Adjust position based on direction/region
        if m_direction:
            direction = m_direction.group(1)
            if 'південь' in direction:
                sea_lat = 45.0  # Further south
            elif 'північ' in direction:
                sea_lat = 45.6  # Further north
            if 'схід' in direction:
                sea_lng = 31.2  # Further east
            elif 'захід' in direction:
                sea_lng = 30.2  # Further west

        if m_region:
            region_name = m_region.group(1)
            if 'одещин' in region_name or 'одеськ' in region_name:
                # South of Odesa region - in the sea 50km offshore
                sea_lat, sea_lng = 45.7, 30.7
                target_info = 'Одещини'
            elif 'миколаїв' in region_name:
                sea_lat, sea_lng = 45.9, 31.4
                target_info = 'Миколаївщини'
            elif 'херсон' in region_name:
                sea_lat, sea_lng = 45.7, 32.5
                target_info = 'Херсонщини'

        if m_target:
            tc = m_target.group(1).lower()
            tc = UA_CITY_NORMALIZE.get(tc, tc)
            target_info = tc.title()

        threat_type, icon = classify(text)
        place_label = 'Акваторія Чорного моря'
        if target_info:
            place_label += f' (на {target_info})'

        # Try to find target city coordinates for trajectory
        target_coords = None
        if m_target:
            tc_normalized = m_target.group(1).lower()
            tc_normalized = UA_CITY_NORMALIZE.get(tc_normalized, tc_normalized)
            if tc_normalized in CITY_COORDS:
                target_coords = CITY_COORDS[tc_normalized]

        result = {
            'id': str(mid), 'place': place_label, 'lat': sea_lat, 'lng': sea_lng,
            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': icon, 'source_match': 'black_sea_course'
        }

        # Add trajectory data if we have target coordinates
        if target_coords:
            result['trajectory'] = {
                'start': [sea_lat, sea_lng],
                'end': list(target_coords),
                'target': target_info
            }

        return [result]

    # --- Bilhorod-Dnistrovskyi coastal UAV patrol ("вздовж узбережжя Білгород-Дністровського району") ---
    if (('узбереж' in lower_sea or 'вздовж узбереж' in lower_sea) and
        ('білгород-дністровського' in lower_sea or 'белгород-днестровского' in lower_sea) and
        ('бпла' in lower_sea or 'дрон' in lower_sea)):
        # Base approximate city coordinate; push 0.22° south into sea
        city_lat, city_lng = 46.186, 30.345
        lat = city_lat - 0.22
        lng = city_lng
        threat_type, icon = classify(text)
        return [{
            'id': str(mid), 'place': 'Узбережжя Білгород-Дністровського р-ну', 'lat': lat, 'lng': lng,
            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': icon, 'source_match': 'bilhorod_dnistrovskyi_coast'
        }]

    # --- "повз <city>" (passing near) with optional direction target "у напрямку <city>" ---
    lower_pass = text.lower()
    pass_near_detected = False
    if 'повз ' in lower_pass and ('бпла' in lower_pass or 'дрон' in lower_pass):
        pass_match = re.search(r"повз\s+([A-Za-zА-Яа-яЇїІіЄєҐґ'’ʼ`\-]{3,})", lower_pass)
        dir_match = re.search(r"напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ'’ʼ`\-]{3,})(?:\s+([A-Za-zА-Яа-яЇїІіЄєҐґ'’ʼ`\-]{3,}))?", lower_pass)
        places = []
        def norm_c(s: str):
            if not s: return None
            s = s.strip().lower().strip(".,:;()!?")
            s = UA_CITY_NORMALIZE.get(s, s)
            # Morphological heuristics: convert common Ukrainian/Russian case endings to nominative
            candidates = [s]
            if s.endswith('у') and len(s) > 4:
                candidates.append(s[:-1] + 'а')
            if s.endswith('ю') and len(s) > 4:
                candidates.append(s[:-1] + 'я')
            if s.endswith('и') and len(s) > 4:
                candidates.append(s[:-1] + 'а')
            if s.endswith('ої') and len(s) > 5:
                candidates.append(s[:-2] + 'а')
            if s.endswith('оїї') and len(s) > 6:
                candidates.append(s[:-3] + 'а')
            for cand in candidates:
                if region_enhanced_coords(cand):
                    return cand
            return s
        if pass_match:
            c1 = norm_c(pass_match.group(1))
            if c1:
                coords1 = region_enhanced_coords(c1)
                if coords1:
                    places.append((c1.title(), coords1, 'pass_near'))
        if dir_match:
            c2_first = norm_c(dir_match.group(1))
            c2_second_raw = dir_match.group(2)
            full_phrase = None
            if c2_first and c2_second_raw:
                c2_second = norm_c(c2_second_raw)
                cand_phrase = f"{c2_first} {c2_second}".strip()
                if cand_phrase in CITY_COORDS or (SETTLEMENTS_INDEX and cand_phrase in SETTLEMENTS_INDEX):
                    full_phrase = cand_phrase
            c2_key = full_phrase or c2_first
            if c2_key and c2_key != (places[0][0].lower() if places else None):
                coords2 = region_enhanced_coords(c2_key)
                if coords2:
                    places.append((c2_key.title(), coords2, 'direction_target'))
        if places:
            threat_type, icon = classify(text)
            out_tracks = []
            for idx,(nm,(lat,lng),tag) in enumerate(places,1):
                out_tracks.append({
                    'id': f"{mid}_pv{idx}", 'place': nm, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str,
                    'channel': channel, 'marker_icon': icon, 'source_match': tag, 'count': drone_count
                })
            if out_tracks:
                pass_near_detected = True
                return out_tracks

    # --- Pattern: "рухалися на <city1>, змінили курс на <city2>" ---
    lower_course_change = text.lower()
    if 'змінили курс на' in lower_course_change and ('рухал' in lower_course_change or 'рухались' in lower_course_change or 'рухалися' in lower_course_change):
        m_to = re.search(r'змінили\s+курс\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower_course_change)
        m_from = re.search(r'рухал(?:ися|ись|и|ась)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower_course_change)
        places = []
        def norm_simple(s):
            if not s: return None
            s = s.strip().lower().strip(".,:;()!")
            return UA_CITY_NORMALIZE.get(s, s)
        if m_from:
            c_from = norm_simple(m_from.group(1))
            coords_from = region_enhanced_coords(c_from)
            if coords_from:
                places.append((c_from.title(), coords_from, 'course_from'))
        if m_to:
            c_to = norm_simple(m_to.group(1))
            coords_to = region_enhanced_coords(c_to)
            if coords_to:
                # avoid duplicate if same
                if not any(p[0].lower()==c_to for p in places):
                    places.append((c_to.title(), coords_to, 'course_changed_to'))
        if places:
            threat_type, icon = classify(text)
            out = []
            for idx,(name,(lat,lng),tag) in enumerate(places,1):
                out.append({
                    'id': f"{mid}_cc{idx}", 'place': name, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': tag
                })
            if out:
                return out

    # --- Relative direction near a city: "північніше кам'янського у напрямку кременчука" ---
    rel_dir_lower = text.lower()
    if any(k in rel_dir_lower for k in ['північніше','південніше','східніше','західніше']) and ('бпла' in rel_dir_lower or 'дрон' in rel_dir_lower):
        # Allow letters plus apostrophes/hyphen
        m_rel = re.search(r"(північніше|південніше|східніше|західніше)\s+([A-Za-zА-Яа-яЇїІіЄєҐґ'`’ʼ\-]{4,})", rel_dir_lower)
        target_dir = re.search(r'напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', rel_dir_lower)
        if m_rel:
            dir_word = m_rel.group(1)
            raw_city = m_rel.group(2).strip(".,:;()!?")
            def norm_rel_city(s):
                s = s.lower()
                # нормализация окончаний родительного падежа '-ського' -> 'ське'
                if s.endswith('ського'):
                    s = s[:-6] + 'ське'
                if s.endswith('ого') and len(s) > 5:
                    s = s[:-3] + 'о'
                return UA_CITY_NORMALIZE.get(s, s)
            base_city = norm_rel_city(raw_city)
            coords_base = region_enhanced_coords(base_city)
            coords_target = None
            target_name = None
            if target_dir:
                tn = target_dir.group(1).lower().strip('.:,;()!?')
                tn = UA_CITY_NORMALIZE.get(tn, tn)
                coords_target = region_enhanced_coords(tn)
                target_name = tn
            if coords_base:
                lat_b, lng_b = coords_base
                # offset ~0.35 deg lat/long depending on direction
                lat_off, lng_off = 0,0
                if 'північ' in dir_word: lat_off = 0.35
                elif 'півден' in dir_word: lat_off = -0.35
                elif 'східн' in dir_word: lng_off = 0.55
                elif 'західн' in dir_word: lng_off = -0.55
                rel_lat, rel_lng = lat_b + lat_off, lng_b + lng_off
                threat_type, icon = classify(text)
                tracks = [{
                    'id': f"{mid}_rel1", 'place': base_city.title(), 'lat': rel_lat, 'lng': rel_lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'relative_dir'
                }]
                if coords_target:
                    tracks.append({
                        'id': f"{mid}_rel2", 'place': target_name.title(), 'lat': coords_target[0], 'lng': coords_target[1],
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'direction_target'
                    })
                return tracks

    # --- Parenthetical course city e.g. "курс західний (кременчук)" ---
    if 'курс' in lower and '(' in lower and ')' in lower and ('бпла' in lower or 'дрон' in lower):
        m_par = re.search(r'курс[^()]{0,30}\(([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})\)', lower)
        if m_par:
            pc = m_par.group(1).lower()
            pc = UA_CITY_NORMALIZE.get(pc, pc)
            coords = region_enhanced_coords(pc)
            if coords:
                threat_type, icon = classify(text)
                return [{
                    'id': f"{mid}_pc", 'place': pc.title(), 'lat': coords[0], 'lng': coords[1],
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'course_parenthetical'
                }]

    # --- Comma separated settlements followed by threat keyword (e.g. "Обухівка, Курилівка, Петриківка увага БПЛА") ---
    lower_commas = text.lower()
    if 'бпла' in lower_commas and ',' in lower_commas:
        # Identify first threat keyword position
        threat_kw_idx = None
        for kw in ['увага','проліт','пролёт','уважно','уважно.','уважно,']:
            pos = lower_commas.find(kw)
            if pos != -1:
                threat_kw_idx = pos
                break
        if threat_kw_idx is not None:
            left_seg = lower_commas[:threat_kw_idx]
            # quick guard to ensure segment not too long
            if 3 <= len(left_seg) <= 180:
                cand_parts = [p.strip() for p in left_seg.split(',') if p.strip()]
                found = []
                for cand in cand_parts:
                    # normalize basic endings (remove trailing punctuation)
                    base = cand.strip(" .!?:;()[]'`’ʼ")
                    if len(base) < 3:
                        continue
                    norm = UA_CITY_NORMALIZE.get(base, base)
                    coords = region_enhanced_coords(norm)
                    if coords:
                        found.append((norm.title(), coords))
                if found:
                    threat_type, icon = classify(text)
                    tracks = []
                    seenp = set()
                    for idx,(nm,(lat,lng)) in enumerate(found,1):
                        if nm in seenp: continue
                        seenp.add(nm)
                        tracks.append({
                            'id': f"{mid}_m{idx}", 'place': nm, 'lat': lat, 'lng': lng,
                            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'multi_settlement_comma', 'count': drone_count
                        })
                    if tracks:
                        return tracks

    # --- PRIORITY: Direction patterns (у напрямку, через, повз) - BEFORE region boundary logic ---
    try:
        import re as _re_direction

        if has_threat(text) and any(pattern in text.lower() for pattern in ['у напрямку', 'через', 'повз']):
            direction_targets = []

            # Pattern 1: "у напрямку [city], [oblast]"
            naprym_pattern = r'у\s+напрямку\s+([А-Яа-яЇїІіЄєҐґ\'\-\s]+?)(?:\s*,\s*([А-Яа-яЇїІіЄєҐґ\'\-\s]*області?))?(?:[\.\,\!\?;]|$)'
            naprym_matches = _re_direction.findall(naprym_pattern, text, _re_direction.IGNORECASE)
            for city_raw, oblast_raw in naprym_matches:
                direction_targets.append(('у напрямку', city_raw.strip(), oblast_raw.strip() if oblast_raw else ''))

            # Process direction targets
            for direction_type, city_raw, oblast_raw in direction_targets:
                if direction_type == 'у напрямку':
                    city_norm = city_raw.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                    city_norm = re.sub(r'\s+',' ', city_norm).strip()

                    # Try exact lookup
                    coords = CITY_COORDS.get(city_norm)
                    if not coords:
                        # Try normalized lookup
                        city_base = UA_CITY_NORMALIZE.get(city_norm, city_norm)
                        coords = CITY_COORDS.get(city_base)

                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(text)

                        # Extract drone count
                        import re as _re_count
                        count_match = _re_count.search(r'(\d+)\s*[хx]?\s*(?:бпла|дрон|шахед)', text.lower())
                        drone_count = int(count_match.group(1)) if count_match else 1

                        add_debug_log(f"PRIORITY: Direction target found - {city_norm} -> {coords}", "direction_priority")
                        return [{
                            'id': str(mid), 'place': city_raw.title(), 'lat': lat, 'lng': lng,
                            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'direction_target_priority', 'count': drone_count
                        }]
                    else:
                        add_debug_log(f"PRIORITY: Direction target not found - {city_norm}", "direction_priority")
    except Exception as e:
        add_debug_log(f"Direction priority processing error: {e}", "direction_priority")

    # PRIORITY: Various Shahed patterns - Process before region boundary logic
    try:
        import re as _re_shahed
        all_shahed_tracks = []

        # Pattern 1: "N шахедів біля [city]" or "N шахедів біля [city1]/[city2]"
        bilya_pattern = r'(\d+)\s+шахед[а-яіїєёыийї]*\s+біля\s+([А-Яа-яЏїІіЄєҐґ\'\-\s\/]+?)(?:\s+та\s+район)?(?:\s+на\s+[А-Яа-яЇїІіЄєҐґ\'\-\s]+)?(?:[\.\,\!\?;]|$)'
        bilya_matches = _re_shahed.findall(bilya_pattern, text, _re_shahed.IGNORECASE)

        # Pattern 2: "N шахед на [city]"
        na_pattern = r'(\d+)\s+шахед[а-яіїєёыийї]*\s+на\s+([А-Яа-яЇїІіЄєҐґ\'\-\s]+?)(?:[\.\,\!\?;]|$)'
        na_matches = _re_shahed.findall(na_pattern, text, _re_shahed.IGNORECASE)

        # Pattern 3: "N шахедів з боку [city]"
        z_boku_pattern = r'(\d+)\s+шахед[а-яіїєёыийї]*\s+з\s+боку\s+([А-Яа-яЇїІіЄєҐґ\'\-\s]+?)(?:[\.\,\!\?;]|$)'
        z_boku_matches = _re_shahed.findall(z_boku_pattern, text, _re_shahed.IGNORECASE)

        # Pattern 4: "N шахедів через [city1]/[city2]" - multiple cities
        cherez_multi_pattern = r'(\d+)\s+шахед[а-яіїєёыийї]*\s+через\s+([А-Яа-яЇїІіЄєҐґ\'\-\s\/]+?)(?:\s+район)?(?:\s+на\s+[А-Яа-яЇїІіЄєҐґ\'\-\s]+)?(?:[\.\,\!\?;]|$)'
        cherez_matches = _re_shahed.findall(cherez_multi_pattern, text, _re_shahed.IGNORECASE)

        all_patterns = [
            (bilya_matches, 'bilya'),
            (na_matches, 'na'),
            (z_boku_matches, 'z_boku'),
            (cherez_matches, 'cherez')
        ]

        for matches, pattern_type in all_patterns:
            for count_str, city_raw in matches:
                # Handle multiple cities separated by /
                cities = [c.strip() for c in city_raw.split('/')]

                for city_part in cities:
                    city_norm = city_part.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                    city_norm = re.sub(r'\s+',' ', city_norm).strip()

                    # Special handling for "[city] на [region]" patterns
                    region_match = re.match(r'^(.+?)\s+на\s+([а-яіїє]+щині?|[а-яіїє]+ській?\s+обл?\.?|[а-яіїє]+ській?\s+області?)$', city_norm)
                    if region_match:
                        city_norm = region_match.group(1).strip()
                        region_hint = region_match.group(2).strip()
                        # Use full message context for resolution
                        coords = ensure_city_coords_with_message_context(city_norm, text)
                        if coords:
                            lat, lng, approx = coords
                            add_debug_log(f"SHAHED: Regional pattern found - {city_norm} на {region_hint} -> ({lat}, {lng})", "shahed_regional")

                            result_entry = {
                                'id': f"{mid}_sha_{len(threats)+1}",
                                'place': f"{city_part.title()}",
                                'lat': lat, 'lng': lng,
                                'type': 'shahed', 'count': int(count_str),
                                'timestamp': date_str, 'channel': channel
                            }
                            threats.append(result_entry)
                            continue  # Skip regular processing for this city

                    # Apply normalization rules for accusative/genitive cases
                    original_norm = city_norm
                    if city_norm in UA_CITY_NORMALIZE:
                        city_norm = UA_CITY_NORMALIZE[city_norm]

                    # Try accusative endings for cities like "миколаєва" -> "миколаїв", "полтави" -> "полтава"
                    if not (city_norm in CITY_COORDS or region_enhanced_coords(city_norm)):
                        # Try various ending transformations
                        variants = [city_norm]
                        if city_norm.endswith('а'):
                            variants.extend([city_norm[:-1] + 'ів', city_norm[:-1] + 'і'])
                        elif city_norm.endswith('и'):
                            variants.extend([city_norm[:-1] + 'а', city_norm[:-1] + 'я'])
                        elif city_norm.endswith('у'):
                            variants.extend([city_norm[:-1] + 'п', city_norm[:-1] + 'к'])

                        for variant in variants:
                            if variant in CITY_COORDS or region_enhanced_coords(variant):
                                city_norm = variant
                                break

                    # Try to get coordinates
                    coords = region_enhanced_coords(city_norm)
                    if not coords:
                        context_result = ensure_city_coords_with_message_context(city_norm, text)
                        if context_result:
                            coords = context_result[:2]  # Take only lat, lng

                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(text)
                        count = int(count_str) if count_str.isdigit() else 1

                        # Create multiple tracks for multiple drones
                        tracks_to_create = max(1, count)
                        for i in range(tracks_to_create):
                            track_label = city_part.title()
                            if tracks_to_create > 1:
                                track_label += f" #{i+1}"

                            # Add small coordinate offsets to prevent marker overlap
                            marker_lat = lat
                            marker_lng = lng
                            if tracks_to_create > 1:
                                # Create a chain pattern - drones one after another
                                offset_distance = 0.03  # ~3km offset between each drone
                                marker_lat += offset_distance * i
                                marker_lng += offset_distance * i * 0.5

                            all_shahed_tracks.append({
                                'id': f"{mid}_{pattern_type}_{len(all_shahed_tracks)}",
                                'place': track_label,
                                'lat': marker_lat,
                                'lng': marker_lng,
                                'threat_type': threat_type,
                                'text': text[:500],
                                'date': date_str,
                                'channel': channel,
                                'marker_icon': icon,
                                'source_match': f'{pattern_type}_shahed_priority',
                                'count': 1
                            })
                        add_debug_log(f"SHAHED {pattern_type.upper()}: {city_norm} ({count}x) -> {coords}", f"shahed_{pattern_type}")

        if all_shahed_tracks:
            return all_shahed_tracks
    except Exception as e:
        add_debug_log(f"Shahed patterns processing error: {e}", "shahed_priority")

    # Region boundary logic (fallback single or midpoint for exactly two)
    matched_regions = []
    for name, coords in OBLAST_CENTERS.items():
        if name in lower:
            matched_regions.append((name, coords))
    if matched_regions:
        # НОВОЕ: Проверка контекстного геокодинга перед региональными маркерами
        if CONTEXT_GEOCODER_AVAILABLE:
            context_result = get_coordinates_context_aware(text)
            if context_result:
                lat, lng, target_city = context_result
                threat_type, icon = classify(text)

                print(f"DEBUG Context-aware geocoding: Found primary target '{target_city}' at ({lat}, {lng})")

                return [{
                    'id': str(mid), 'place': target_city.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'context_aware_geocoding', 'count': 1
                }]

        # Если только области упомянуты и нет ключей угроз, пропускаем.
        # Дополнительная защита: иногда в messages.json могли сохраниться старые записи без угроз.
        if not has_threat(text):
            # чистый список областей? (только названия + двоеточия/пробелы/переводы строк)
            stripped = re.sub(r'[\s:]+', ' ', text.lower()).strip()
            only_regions = all(rn in OBLAST_CENTERS for rn in stripped.split() if rn)
            if only_regions or len(text) < 120:
                return None
        # --- Направления внутри области (північно-західний / південно-західний и т.п.) ---
        def detect_direction(lower_txt: str):
            # Support full adjectives with endings (-ний / -ня / -ньому) by searching stems
            if 'північно-захід' in lower_txt or 'північно-західн' in lower_txt: return 'nw'
            if 'південно-захід' in lower_txt or 'південно-західн' in lower_txt: return 'sw'
            if 'північно-схід' in lower_txt or 'північно-східн' in lower_txt: return 'ne'
            if 'південно-схід' in lower_txt or 'південно-східн' in lower_txt: return 'se'
            # Single directions (allow stems 'північн', 'південн')
            if re.search(r'\bпівніч(?!о-с)(?:н\w*)?\b', lower_txt): return 'n'
            if re.search(r'\bпівденн?\w*\b', lower_txt): return 's'
            if re.search(r'\bсхідн?\w*\b', lower_txt): return 'e'
            if re.search(r'\bзахідн?\w*\b', lower_txt): return 'w'
            return None
        direction_code = None
    if len(matched_regions) == 1 and not raion_matches and not pass_near_detected:
            direction_code = detect_direction(lower)
            # If message also contains course info referencing cities/slash – skip region-level marker to allow city parsing later
            course_words = (' курс ' in lower or lower.startswith('курс '))
            # Treat city present only if it appears as a standalone word (to avoid 'дніпро' inside 'дніпропетровщини')
            has_city_token = False
            try:
                import re as _re_ct
                for c_name in CITY_COORDS.keys():
                    if _re_ct.search(r'\b'+_re_ct.escape(c_name)+r'\b', lower):
                        has_city_token = True; break
            except Exception:
                has_city_token = any(c in lower for c in CITY_COORDS.keys())
            has_slash_combo = '/' in lower
            if direction_code and not (course_words and (has_city_token or has_slash_combo)):
                # ---- Special: sector course pattern inside region directional message ----
                # e.g. "курс(ом) в бік сектору перещепине - губиниха"
                sector_match = re.search(r'курс(?:ом)?\s+в\s+бік\s+сектору\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})(?:\s*[-–]\s*([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,}))?', lower)
                if sector_match:
                    c1 = sector_match.group(1)
                    c2 = sector_match.group(2)
                    def norm_city(n):
                        if not n: return None
                        n = n.strip().lower()
                        n = re.sub(r'["`ʼ’\'.,:;()]+', '', n)
                        return UA_CITY_NORMALIZE.get(n, n)
                    c1n = norm_city(c1)
                    c2n = norm_city(c2) if c2 else None
                    coords1 = CITY_COORDS.get(c1n) or (SETTLEMENTS_INDEX.get(c1n) if SETTLEMENTS_INDEX else None)
                    coords2 = CITY_COORDS.get(c2n) or (SETTLEMENTS_INDEX.get(c2n) if (c2n and SETTLEMENTS_INDEX) else None)
                    if coords1 or coords2:
                        if coords1 and coords2:
                            lat_o = (coords1[0]+coords2[0])/2
                            lng_o = (coords1[1]+coords2[1])/2
                            place_label = f"{c1n.title()} - {c2n.title()} (сектор)"
                        else:
                            (lat_o,lng_o) = coords1 or coords2
                            place_label = (c1n or c2n).title()
                        threat_type, icon = classify(text)
                        return [{
                            'id': str(mid), 'place': place_label, 'lat': lat_o, 'lng': lng_o,
                            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'course_sector', 'count': drone_count
                        }]
                (reg_name, (base_lat, base_lng)) = matched_regions[0]

                # Define offset function for coordinate calculations
                def offset(lat, lng, code):
                    # Уменьшенные дельты для более точного позиционирования в пределах области
                    # (широта ~111 км, долгота * cos(lat))
                    import math
                    lat_step = 0.35  # Примерно 35-40 км вместо 60 км
                    lng_step = 0.55 / max(0.2, abs(math.cos(math.radians(lat))))  # Примерно 35-40 км
                    if code == 'n': return lat+lat_step, lng
                    if code == 's': return lat-lat_step, lng
                    if code == 'e': return lat, lng+lng_step
                    if code == 'w': return lat, lng-lng_step
                    # диагонали немного меньше по каждой оси
                    lat_diag = lat_step * 0.8
                    lng_diag = lng_step * 0.8
                    if code == 'ne': return lat+lat_diag, lng+lng_diag
                    if code == 'nw': return lat+lat_diag, lng-lng_diag
                    if code == 'se': return lat-lat_diag, lng+lng_diag
                    if code == 'sw': return lat-lat_diag, lng-lng_diag
                    return lat, lng

                # SPECIAL: Handle messages with start position + course direction
                # e.g. "на півночі тернопільщини ➡️ курсом на південно-західний напрямок"
                start_direction = None
                course_direction = None

                # Detect start position (на півночі/півдні/сході/заході)
                if re.search(r'\bна\s+півночі\b', lower) or re.search(r'\bпівнічн\w+\s+частин\w*\b', lower):
                    start_direction = 'n'
                elif re.search(r'\bна\s+півдні\b', lower) or re.search(r'\bпівденн\w+\s+частин\w*\b', lower):
                    start_direction = 's'
                elif re.search(r'\bна\s+сході\b', lower) or re.search(r'\bсхідн\w+\s+частин\w*\b', lower):
                    start_direction = 'e'
                elif re.search(r'\bна\s+заході\b', lower) or re.search(r'\bзахідн\w+\s+частин\w*\b', lower):
                    start_direction = 'w'

                # Detect course direction (курсом на направление)
                # Support patterns: "курсом на", "рух на", "продовжує рух на", "прямують на", "в напрямку"
                has_direction_keyword = ('курс' in lower and 'напрямок' in lower) or ('➡' in lower or '→' in lower) or \
                                       ('рух' in lower and 'на' in lower) or ('прямують' in lower and 'на' in lower) or \
                                       ('продовжує' in lower and ('рух' in lower or 'на' in lower)) or \
                                       ('в' in lower and ('напрямку' in lower or 'напрямок' in lower or 'напрям' in lower))

                if has_direction_keyword:
                    if 'північно-західн' in lower or 'північно-захід' in lower:
                        course_direction = 'nw'
                    elif 'південно-західн' in lower or 'південно-захід' in lower:
                        course_direction = 'sw'
                    elif 'північно-східн' in lower or 'північно-схід' in lower:
                        course_direction = 'ne'
                    elif 'південно-східн' in lower or 'південно-схід' in lower:
                        course_direction = 'se'
                    # Single directions in course - support "курсом на", "рух на", "в [напрямок] напрямку"
                    elif re.search(r'(курс\w*|рух|прямують|продовжує)\s+(на\s+)?північ', lower) or re.search(r'в\s+північн\w*\s+напрям', lower):
                        course_direction = 'n'
                    elif re.search(r'(курс\w*|рух|прямують|продовжує)\s+(на\s+)?південь|півд', lower) or re.search(r'в\s+півден\w*\s+напрям', lower):
                        course_direction = 's'
                    elif re.search(r'(курс\w*|рух|прямують|продовжує)\s+(на\s+)?схід', lower) or re.search(r'в\s+східн\w*\s+напрям', lower):
                        course_direction = 'e'
                    elif re.search(r'(курс\w*|рух|прямують|продовжує)\s+(на\s+)?захід', lower) or re.search(r'в\s+захід\w*\s+напрям', lower):
                        course_direction = 'w'

                # If we have both start position and course direction, apply them sequentially
                if start_direction and course_direction:
                    # First offset: move to start position within region
                    lat_start, lng_start = offset(base_lat, base_lng, start_direction)
                    # Second offset: apply course direction from start position
                    lat_final, lng_final = offset(lat_start, lng_start, course_direction)

                    # Create descriptive label with arrow for trajectory visualization
                    start_labels = {'n':'півночі', 's':'півдні', 'e':'сході', 'w':'заході'}
                    course_labels = {
                        'n':'північ', 's':'південь', 'e':'схід', 'w':'захід',
                        'ne':'північний схід', 'nw':'північний захід',
                        'se':'південний схід', 'sw':'південний захід'
                    }
                    # Direction labels for arrow (Ukrainian names compatible with frontend)
                    arrow_labels = {
                        'n':'північ', 's':'півдня', 'e':'сходу', 'w':'заходу',
                        'ne':'північного сходу', 'nw':'північного заходу',
                        'se':'південного сходу', 'sw':'південного заходу'
                    }
                    start_label = start_labels.get(start_direction, 'області')
                    course_label = course_labels.get(course_direction, 'напрямок')
                    arrow_label = arrow_labels.get(course_direction, '')
                    base_disp = reg_name.split()[0].title()

                    # Add arrow to place name for trajectory visualization in frontend
                    place_name = f"{base_disp} (з {start_label})"
                    if arrow_label:
                        place_name += f" ←{arrow_label}"

                    trajectory = {
                        'start': [lat_start, lng_start],
                        'end': [lat_final, lng_final],
                        'source': base_disp,
                        'target': course_label,
                        'kind': 'region_start_course'
                    }

                    threat_type, icon = classify(text)
                    return [{
                        'id': str(mid), 'place': place_name,
                        'lat': lat_final, 'lng': lng_final,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_start_course', 'count': drone_count,
                        'trajectory': trajectory,
                        'course_direction': f"курс на {course_label}",
                        'course_source': base_disp,
                        'course_target': course_label,
                        'course_type': 'region_start_course'
                    }]

                # If only course_direction (no start position), use it as the direction
                if course_direction and not start_direction:
                    direction_code = course_direction

                # смещение ~50-70 км в сторону указанного направления (fallback for single direction)
                lat_o, lng_o = offset(base_lat, base_lng, direction_code)
                threat_type, icon = classify(text)
                dir_label_map = {
                    'n':'північна частина', 's':'південна частина', 'e':'східна частина', 'w':'західна частина',
                    'ne':'північно-східна частина', 'nw':'північно-західна частина',
                    'se':'південно-східна частина', 'sw':'південно-західна частина'
                }
                # Direction labels for arrow (Ukrainian names compatible with frontend)
                arrow_labels = {
                    'n':'північ', 's':'півдня', 'e':'сходу', 'w':'заходу',
                    'ne':'північного сходу', 'nw':'північного заходу',
                    'se':'південного сходу', 'sw':'південного заходу'
                }
                dir_phrase = dir_label_map.get(direction_code, 'частина')
                arrow_label = arrow_labels.get(direction_code, '')
                base_disp = reg_name.split()[0].title()

                # Add arrow to place name for trajectory visualization
                place_name = f"{base_disp} ({dir_phrase})"
                if arrow_label:
                    place_name += f" ←{arrow_label}"

                return [{
                    'id': str(mid), 'place': place_name, 'lat': lat_o, 'lng': lng_o,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'region_direction', 'count': drone_count
                }]
            # если нет направления — продолжаем анализ (ищем конкретные цели типа "курс на <місто>")
    # Midpoint for explicit course between two regions (e.g. "... на запоріжжі курсом на дніпропетровщину")
    if len(matched_regions) == 2 and ('курс' in lower or '➡' in lower or '→' in lower) and (' на ' in lower):
            # ensure we really reference both regions in a course sense: one mentioned before 'курс' and the other after 'курс' / arrow
            parts_course = re.split(r'курс|➡|→', lower, 1)
            if len(parts_course) == 2:
                before, after_part = parts_course
                r1, r2 = matched_regions[0], matched_regions[1]
                bnames = [r1[0].split()[0].lower(), r2[0].split()[0].lower()]
                # If both region stems appear across the split segments, build midpoint
                cond_split = (any(n[:5] in before for n in bnames) and any(n[:5] in after_part for n in bnames))
                # Fallback heuristic: pattern 'на <region1>' earlier then arrow/"курс" then 'на <region2>'
                if not cond_split:
                    # Extract simple region stems from OBLAST_CENTERS keys
                    stems = ['запоріж','запор', 'дніпропетров','дніпропет']
                    if any(st in lower for st in stems):
                        if re.search(r'на\s+запоріж', lower) and re.search(r'на\s+дніпропетров', lower):
                            cond_split = True
                if cond_split:
                    (n1,(a1,b1)), (n2,(a2,b2)) = matched_regions

                    def region_variants(name: str):
                        base = name.split()[0].lower()
                        variants = {base}
                        cleaned = base.replace('область', '').replace('області', '').strip()
                        if cleaned:
                            variants.add(cleaned)
                        if cleaned.endswith('ська'):
                            stem = cleaned[:-4]
                            variants.update({stem + 'щина', stem + 'щини', stem + 'щин', stem})
                        elif cleaned.endswith('ської'):
                            stem = cleaned[:-5]
                            variants.update({stem + 'щина', stem + 'щини', stem + 'щин', stem})
                        return [v for v in variants if v]

                    def segment_has(segment: str, name: str) -> bool:
                        for variant in region_variants(name):
                            if variant in segment:
                                return True
                        return False

                    def region_position(full_text: str, name: str) -> int:
                        positions = []
                        for variant in region_variants(name):
                            idx = full_text.find(variant)
                            if idx != -1:
                                positions.append(idx)
                        return min(positions) if positions else 10**6

                    # Determine source and target based on message structure
                    source_entry = matched_regions[0]
                    target_entry = matched_regions[1]
                    before_region = next((entry for entry in matched_regions if segment_has(before, entry[0])), None)
                    after_region = next((entry for entry in matched_regions if segment_has(after_part, entry[0])), None)

                    if before_region and after_region and before_region != after_region:
                        source_entry = before_region
                        target_entry = after_region
                    elif before_region and not after_region:
                        source_entry = before_region
                        target_entry = next(entry for entry in matched_regions if entry != source_entry)
                    elif after_region and not before_region:
                        target_entry = after_region
                        source_entry = next(entry for entry in matched_regions if entry != target_entry)
                    else:
                        # fallback to textual order
                        ordered = sorted(matched_regions, key=lambda entry: region_position(lower, entry[0]))
                        if len(ordered) == 2 and ordered[0] != ordered[1]:
                            source_entry, target_entry = ordered[0], ordered[1]

                    (source_name, (src_lat, src_lng)) = source_entry
                    (target_name, (tgt_lat, tgt_lng)) = target_entry

                    source_region = source_name.split()[0].title()
                    target_region = target_name.split()[0].title()

                    def offset(lat, lng, code):
                        import math
                        lat_step = 0.35
                        lng_step = 0.55 / max(0.2, abs(math.cos(math.radians(lat))))
                        if code == 'n': return lat+lat_step, lng
                        if code == 's': return lat-lat_step, lng
                        if code == 'e': return lat, lng+lng_step
                        if code == 'w': return lat, lng-lng_step
                        lat_diag = lat_step * 0.8
                        lng_diag = lng_step * 0.8
                        if code == 'ne': return lat+lat_diag, lng+lng_diag
                        if code == 'nw': return lat+lat_diag, lng-lng_diag
                        if code == 'se': return lat-lat_diag, lng+lng_diag
                        if code == 'sw': return lat-lat_diag, lng-lng_diag
                        return lat, lng

                    def detect_region_direction(text_block: str, region_label: str):
                        base = region_label.split()[0].lower()
                        region_variants = [base]
                        if base.endswith('ська'):
                            region_variants.append(base[:-4] + 'щині')
                            region_variants.append(base[:-4] + 'щини')
                            region_variants.append(base[:-4] + 'щина')
                        tokens = {
                            'північ': 'n',
                            'півден': 's',
                            'схід': 'e',
                            'захід': 'w'
                        }
                        for variant in region_variants:
                            for needle, code in tokens.items():
                                pattern = rf'(?:на|у|в)\s+{needle}\w*\s+(?:частин\w*\s+)?{variant}'
                                if re.search(pattern, text_block):
                                    return code
                        return None

                    source_lat_adj, source_lng_adj = src_lat, src_lng
                    source_direction_hint = detect_region_direction(lower, source_name)
                    if source_direction_hint:
                        source_lat_adj, source_lng_adj = offset(source_lat_adj, source_lng_adj, source_direction_hint)

                    # Calculate direction from source to target for arrow labels
                    dlat = tgt_lat - src_lat
                    dlng = tgt_lng - src_lng

                    def direction_token(dy: float, dx: float):
                        if abs(dy) < 1e-6 and abs(dx) < 1e-6:
                            return None
                        if abs(dy) > abs(dx) * 1.4:
                            return 'n' if dy > 0 else 's'
                        if abs(dx) > abs(dy) * 1.4:
                            return 'e' if dx > 0 else 'w'
                        if dy >= 0 and dx >= 0:
                            return 'ne'
                        if dy >= 0 and dx < 0:
                            return 'nw'
                        if dy < 0 and dx >= 0:
                            return 'se'
                        return 'sw'

                    dir_token = direction_token(dlat, dlng)
                    arrow_label_map = {
                        'n': 'півночі', 's': 'півдня', 'e': 'сходу', 'w': 'заходу',
                        'ne': 'північного сходу', 'nw': 'північного заходу',
                        'se': 'південного сходу', 'sw': 'південного заходу'
                    }
                    course_label_map = {
                        'n': 'північ', 's': 'південь', 'e': 'схід', 'w': 'захід',
                        'ne': "північний схід", 'nw': "північний захід",
                        'se': "південний схід", 'sw': "південний захід"
                    }
                    arrow_direction = arrow_label_map.get(dir_token, '')
                    course_direction_text = course_label_map.get(dir_token)

                    # Position marker at the (optionally offset) source to avoid teleporting to the target city
                    lat = source_lat_adj
                    lng = source_lng_adj

                    # Create place name with arrow for trajectory visualization
                    place_name = f"{source_region} → {target_region}"
                    if arrow_direction:
                        place_name += f" ←{arrow_direction}"

                    trajectory = {
                        'start': [lat, lng],
                        'end': [tgt_lat, tgt_lng],
                        'target': target_region,
                        'source': source_region,
                        'kind': 'region_course'
                    }

                    threat_type, icon = classify(text)
                    result = {
                        'id': str(mid), 'place': place_name, 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_course_trajectory', 'count': drone_count,
                        'trajectory': trajectory,
                        'course_source': source_region,
                        'course_target': target_region,
                        'course_type': 'region_to_region'
                    }
                    if course_direction_text:
                        result['course_direction'] = f"курс на {course_direction_text}"
                    else:
                        result['course_direction'] = f"курс на {target_region}"
                    return [result]

    if len(matched_regions) == 2 and any(w in lower for w in ['межі','межу','межа','между','границі','граница']):
            (n1,(a1,b1)), (n2,(a2,b2)) = matched_regions
            lat = (a1+a2)/2; lng = (b1+b2)/2
            threat_type, icon = classify(text)
            return [{
                'id': str(mid), 'place': f"Межа {n1.split()[0].title()}/{n2.split()[0].title()}" , 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'count': drone_count
            }]
    else:
            # If message contains explicit course targets (parsed later), don't emit plain region markers
            course_target_hint = False
            for ln in text.split('\n'):
                ll = ln.lower()
                if 'бпла' in ll and 'курс' in ll and re.search(r'курс(?:ом)?\s+(?:на|в|у)\s+[A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,}', ll):
                    course_target_hint = True
                    break
            if not course_target_hint:
                threat_type, icon = classify(text)

                # Extract course information for Shahed threats
                course_info = None
                if threat_type == 'shahed':
                    course_info = extract_shahed_course_info(original_text or text)

                tracks = []
                seen = set()
                for idx,(n1,(lat,lng)) in enumerate(matched_regions,1):
                    base = n1.split()[0].title()
                    if base in seen: continue
                    seen.add(base)

                    track = {
                        'id': f"{mid}_r{idx}", 'place': base, 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_multi_simple', 'count': drone_count
                    }

                    # Add course information if available
                    if course_info:
                        track.update({
                            'course_source': course_info.get('source_city'),
                            'course_target': course_info.get('target_city'),
                            'course_direction': course_info.get('course_direction'),
                            'course_type': course_info.get('course_type')
                        })

                    tracks.append(track)
                if tracks:
                    return tracks
    # City fallback scan (ensure whole-word style match to avoid false hits inside oblast words, e.g. 'дніпро' in 'дніпропетровщина')
    for city in UA_CITIES:
        if re.search(r'(?<![a-zа-яїієґ])' + re.escape(city) + r'(?![a-zа-яїієґ])', lower):
            norm = UA_CITY_NORMALIZE.get(city, city)
            # City fallback: attempt region-qualified first
            coords = None
            if region_hint_global and OPENCAGE_API_KEY:
                coords = geocode_opencage(f"{norm} {region_hint_global}")
            if not coords:
                coords = region_enhanced_coords(norm)
            # If областной контекст уже определён (matched_regions) ограничим города той же области
            if matched_regions:
                # берем первый stem области
                stem = None
                for (rn, _c) in matched_regions:
                    for s in ['харків','львів','київ','дніпропетров','полтав','сум','черніг','волин','запор','одес','микола','черка','житом','хмельниць','рівн','івано','терноп','ужгород','кропив','луган','донець','чернівц']:
                        if s in rn:
                            stem = s; break
                    if stem: break
                if stem and norm in CITY_TO_OBLAST and CITY_TO_OBLAST[norm] != stem:
                    continue
            if coords:
                lat, lng = coords
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': norm.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'count': drone_count
                }]
            # if city found but no coords even in fallback, continue scanning others (no break)
    # --- Slash separated settlements with drone count (e.g. "дніпро / самар — 6х бпла ... курс західний") ---
    if '/' in lower and ('бпла' in lower or 'дрон' in lower) and any(x in lower for x in ['х бпла','x бпла',' бпла']):
        left_part = lower.split('—')[0].split('-',1)[0]
        parts = [p.strip() for p in re.split(r'/|\\', left_part) if p.strip()]
        found = []
        for p in parts:
            if p in CITY_COORDS:
                found.append((p.title(), CITY_COORDS[p]))
        if found:
            threat_type, icon = classify(text)
            tracks = []
            for idx,(nm,(lat,lng)) in enumerate(found,1):
                # If course west mentioned, offset west a bit
                if 'курс захід' in lower or 'курс запад' in lower:
                    lng -= 0.4
                tracks.append({
                    'id': f"{mid}_s{idx}", 'place': nm, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'slash_combo'
                })
            if tracks:
                return tracks
    # --- Single city with westward course ("курс західний") adjust marker to west to avoid mistaken northern region offsets ---
    if 'курс захід' in lower and 'бпла' in lower:
        for c in CITY_COORDS.keys():
            if c in lower:
                lat,lng = CITY_COORDS[c]
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': c.title(), 'lat': lat, 'lng': lng - 0.4,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'course_west'
                }]
    # --- Drone course target parsing (e.g. "БпЛА курсом на Ніжин") ---
    def _normalize_course_city(w: str):
        # Preserve internal single space for multi-word (e.g. "липова долина") before stripping punctuation
        w = re.sub(r'\s+', ' ', w.strip().lower())
        # Remove punctuation but keep spaces and hyphen
        w = re.sub(r'["`ʼ’\'.,:;()]+', '', w)
        # Allow letters, spaces, hyphen
        w = re.sub(r'[^a-zа-яїієґё\- ]', '', w)
        # Accusative to nominative heuristic for each word (handles phrases like 'велику багачку', 'липову долину')
        parts = [p for p in w.split(' ') if p]
        norm_parts = []
        for p in parts:
            base = p
            # Common feminine accusative endings -> nominative
            if len(base) > 4 and base.endswith(('у','ю')):
                base = base[:-1] + 'а'
            # Handle '-у/ю' endings for multi-word second element 'долину' -> 'долина'
            if len(base) > 5 and base.endswith('ину'):
                base = base[:-2] + 'на'
            # Special handling for oblast names ending in 'щину' -> 'щина'
            if len(base) > 6 and base.endswith('щину'):
                base = base[:-1] + 'а'
            norm_parts.append(base)
        w = ' '.join(norm_parts)
        # Apply explicit manual normalization map last (covers irregular)
        if w in UA_CITY_NORMALIZE:
            w = UA_CITY_NORMALIZE[w]
        return w
    course_matches = []
    # Ищем каждую строку с шаблоном
    for line in text.split('\n'):
        line_low = line.lower()
        if 'бпла' in line_low and 'курс' in line_low and (' на ' in line_low or ' в ' in line_low or ' у ' in line_low):
            # Capture one or two words as target, allowing hyphens and apostrophes
            m = re.search(r'курс(?:ом)?\s+(?:на|в|у)\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,}(?:\s+[A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})?)', line, flags=re.IGNORECASE)
            if m:
                raw_city = m.group(1)
                norm_city = _normalize_course_city(raw_city)
                if norm_city:
                    # If the captured target looks like an oblast (region) name (e.g. 'дніпропетровщина', 'черкаська область'),
                    # we intentionally SKIP adding a precise course target marker to avoid falsely placing it at the oblast's capital city.
                    # User requirement: phrases like 'курс(ом) на Дніпропетровщину' must NOT create a marker right in 'Дніпро'.
                    # Check both nominative and accusative forms (щина/щину)
                    if re.search(r'(щина|щину|область)$', norm_city) or re.search(r'(щина|щину|область)$', raw_city.lower()):
                        log.debug(f'skip course_target oblast_only={norm_city} raw={raw_city} mid={mid}')
                        continue
                    coords = region_enhanced_coords(norm_city)
                    if not coords:
                        log.debug(f'course_target_lookup miss city={norm_city} mid={mid} line={line.strip()[:120]!r} region_hint={region_hint_global}')
                        coords = ensure_city_coords(norm_city, context=text)
                        # Try context-based lookup if standard lookup fails
                        if not coords:
                            context_result = ensure_city_coords_with_message_context(norm_city, text)
                            if context_result:
                                coords = context_result[:2]  # Take only lat, lng
                    # Oblast stem disambiguation: if global hint exists and known expected stem differs, re-query with region-qualified geocode
                    if coords and region_hint_global and norm_city in CITY_TO_OBLAST:
                        expected_stem = CITY_TO_OBLAST[norm_city]
                        if expected_stem != region_hint_global[:len(expected_stem)]:
                            # attempt region-qualified geocode with expected stem to refine
                            if OPENCAGE_API_KEY:
                                try:
                                    region_phrase = None
                                    # derive full oblast phrase from stem heuristically (simple mapping subset)
                                    stem_map = {
                                        'сум': 'сумська область', 'полтав': 'полтавська область', 'дніпропетров': 'дніпропетровська область',
                                        'харків': 'харківська область'
                                    }
                                    region_phrase = stem_map.get(expected_stem)
                                    if region_phrase:
                                        refined = geocode_opencage(f"{norm_city} {region_phrase}")
                                        if refined:
                                            coords = refined
                                except Exception:
                                    pass
                    if coords:
                        log.debug(f'course_target_match city={norm_city} coords={coords} region_hint={region_hint_global} mid={mid}')
                    # If still no coords AND we have a region hint + OpenCage, try region-qualified query directly for multi-word ambiguous city
                    if not coords and region_hint_global and OPENCAGE_API_KEY:
                        try:
                            refined2 = geocode_opencage(f"{norm_city} {region_hint_global}")
                            if refined2:
                                coords = refined2
                        except Exception:
                            pass
                    if coords:
                        # Extract line-specific drone count if present (e.g. "4х БпЛА")
                        line_count = None
                        m_lc = re.search(r'(\b\d{1,3})\s*[xх]\s*бпла', line_low)
                        if m_lc:
                            try:
                                line_count = int(m_lc.group(1))
                            except Exception:
                                line_count = None
                        # Ensure coords is a tuple of exactly 2 elements (lat, lng)
                        if len(coords) >= 2:
                            coords = coords[:2]
                        course_matches.append((norm_city.title(), coords, line[:200], line_count))
    if course_matches:
        threat_type, icon = classify(text)
        tracks = []
        seen_places = set()
        for idx,(name,(lat,lng),snippet,line_count) in enumerate(course_matches,1):
            if name in seen_places: continue
            seen_places.add(name)

            # Extract Shahed course information if this is a Shahed threat
            course_info = None
            if threat_type == 'shahed':
                course_info = extract_shahed_course_info(original_text or text)

            # Determine how many tracks to create
            count = line_count if line_count else drone_count
            tracks_to_create = max(1, count if count else 1)

            # Create multiple tracks for multiple drones
            for i in range(tracks_to_create):
                track_name = name
                if tracks_to_create > 1:
                    track_name += f" #{i+1}"

                # Add small coordinate offsets to prevent marker overlap
                marker_lat = lat
                marker_lng = lng
                if tracks_to_create > 1:
                    # Create a chain pattern - drones one after another
                    offset_distance = 0.03  # ~3km offset between each drone
                    marker_lat += offset_distance * i
                    marker_lng += offset_distance * i * 0.5

                track = {
                    'id': f"{mid}_c{idx}_{i+1}", 'place': track_name, 'lat': marker_lat, 'lng': marker_lng,
                    'threat_type': threat_type, 'text': snippet[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'course_target', 'count': 1
                }

                # Add course information if available
                if course_info:
                    track.update({
                        'course_source': course_info.get('source_city'),
                        'course_target': course_info.get('target_city'),
                        'course_direction': course_info.get('course_direction'),
                        'course_type': course_info.get('course_type')
                    })

                tracks.append(track)
        if tracks:
            return tracks

    # Логируем длинные сообщения, которые не сгенерировали треков
    try:
        if text and len(text) > 1000:
            print(f"DEBUG: LONG MESSAGE NO TRACKS - mid={mid}, length={len(text)}, preview: {text[:200]}...")
            # Проверим наличие ключевых слов
            lower_check = text.lower()
            keywords = {'бпла': lower_check.count('бпла'), 'шахед': lower_check.count('шахед'),
                       'курс': lower_check.count('курс'), 'район': lower_check.count('район')}
            print(f"DEBUG: Long message keywords: {keywords}")
    except Exception:
        pass

    # Final check: if we found single UAV threats earlier but no other tracks, return the UAV threats
    if 'single_uav_threats' in locals() and single_uav_threats:
        add_debug_log(f"FINAL: Returning single UAV threats only: {len(single_uav_threats)}", "final_single_uav")
        return single_uav_threats

    return None

async def fetch_loop():
    log.info('fetch_loop() started')
    if not client:
        log.warning('Telegram client not configured; skipping fetch loop.')
        return
    log.info('fetch_loop: client exists, proceeding')
    async def ensure_connected():
        log.info('ensure_connected() called')
        if client.is_connected():
            log.info('Client already connected')
            auth_status = await client.is_user_authorized()
            log.info(f'Authorization status: {auth_status}')
            return auth_status
        try:
            log.info('Connecting client...')
            await client.connect()
            log.info('Client connected successfully')
            # If bot token provided and not authorized yet, try bot login
            if BOT_TOKEN and not await client.is_user_authorized():
                try:
                    log.info('Trying bot token login...')
                    await client.start(bot_token=BOT_TOKEN)
                except Exception as be:
                    log.error(f'Bot start failed: {be}')
            auth_status = await client.is_user_authorized()
            log.info(f'Final authorization status: {auth_status}')
            if not auth_status:
                log.error('Not authorized. Use /auth/start & /auth/complete to login or set TELEGRAM_SESSION.')
                return False
            return True
        except AuthKeyDuplicatedError:
            log.error('AuthKeyDuplicatedError: duplicate session. Provide new TELEGRAM_SESSION or re-auth.')
            return False
        except AuthKeyUnregisteredError:
            log.error('AuthKeyUnregisteredError: Session invalid/expired. Re-auth needed.')
            return False
        except FloodWaitError as fe:
            wait = int(getattr(fe, 'seconds', 60))
            log.warning(f'FloodWait: sleeping {wait}s before reconnect.')
            await asyncio.sleep(wait)
            return False
        except Exception as e:
            log.warning(f'ensure_connected error: {e}')
            return False

    if not await ensure_connected():
        AUTH_STATUS.update({'authorized': False, 'reason': 'not_authorized_initial'})
        await asyncio.sleep(180)
        return
    else:
        AUTH_STATUS.update({'authorized': True, 'reason': 'ok'})
    tz = pytz.timezone('Europe/Kyiv')
    # Load existing messages and create ID set (convert to strings for comparison)
    all_data = load_messages()
    processed = {str(m.get('id')) for m in all_data if m.get('id')}
    # -------- Initial backfill (last BACKFILL_MINUTES, default 50) --------
    try:
        backfill_minutes = int(os.getenv('BACKFILL_MINUTES', '50'))
    except ValueError:
        backfill_minutes = 50
    # SPEED FIX: Limit backfill messages per channel (was 400, now 100)
    try:
        backfill_limit = int(os.getenv('BACKFILL_LIMIT', '100'))
    except ValueError:
        backfill_limit = 100
    backfill_cutoff = datetime.now(tz) - timedelta(minutes=backfill_minutes)
    if backfill_minutes > 0:
        log.info(f'Starting FAST backfill for last {backfill_minutes} minutes (limit {backfill_limit} per channel, NO geocoding)...')
        # Track backfill progress
        BACKFILL_STATUS['in_progress'] = True
        BACKFILL_STATUS['started_at'] = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        BACKFILL_STATUS['channels_total'] = len([c for c in CHANNELS if c.strip()])
        BACKFILL_STATUS['channels_done'] = 0
        BACKFILL_STATUS['messages_processed'] = 0

        total_backfilled = 0
        for ch in CHANNELS:
            ch_strip = ch.strip()
            if not ch_strip:
                continue
            BACKFILL_STATUS['current_channel'] = ch_strip
            print(f"DEBUG: Processing backfill for channel: {ch_strip}")
            fetched = 0
            try:
                if not await ensure_connected():
                    log.warning('Disconnected during backfill; aborting backfill early.')
                    break
                async for msg in client.iter_messages(ch_strip, limit=backfill_limit):  # SPEED FIX: reduced from 400
                    if not msg.text:
                        continue
                    dt = msg.date.astimezone(tz)
                    if dt < backfill_cutoff:
                        break  # older than needed
                    msg_id_str = str(msg.id)
                    if msg_id_str in processed:
                        continue
                    # Check for ballistic threat messages (backfill - don't add to chat)
                    update_ballistic_state(msg.text, is_realtime=False)

                    # SPEED FIX: Skip heavy geocoding during backfill - store raw, process later
                    # This makes backfill instant instead of 30+ minutes
                    all_data.append({
                        'id': msg_id_str,
                        'place': None,
                        'lat': None,
                        'lng': None,
                        'threat_type': 'shahed',  # default, will be updated on reparse
                        'text': msg.text[:500],
                        'date': dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'channel': ch_strip,
                        'pending_geo': True  # Flag for lazy geocoding in /data
                    })
                    processed.add(msg_id_str)
                    fetched += 1
                    BACKFILL_STATUS['messages_processed'] += 1
                if fetched:
                    total_backfilled += fetched
                    log.info(f'Backfilled {fetched} raw messages from {ch_strip}')
                BACKFILL_STATUS['channels_done'] += 1
            except Exception as e:
                log.warning(f'Backfill error {ch_strip}: {e}')
                BACKFILL_STATUS['channels_done'] += 1
    if backfill_minutes > 0:
        # Mark backfill complete
        BACKFILL_STATUS['in_progress'] = False
        BACKFILL_STATUS['current_channel'] = None
        if total_backfilled:
            save_messages(all_data)
            log.info(f'Backfill saved: {total_backfilled} raw messages (geocoding deferred to /data)')
        log.info('Backfill completed.')
    while True:
        new_tracks = []
        for ch in CHANNELS:
            ch = ch.strip()
            if not ch:
                continue
            if ch in INVALID_CHANNELS:
                log.debug(f'Skip invalid channel {ch}')
                continue
            msgs_seen = 0
            msgs_recent_window = 0
            geo_added = 0
            try:
                if not await ensure_connected():
                    # If session invalid we stop loop gracefully
                    if not client.is_connected():
                        log.error('Stopping live loop due to lost/invalid session.')
                        AUTH_STATUS.update({'authorized': False, 'reason': 'lost_session'})
                        return
                log.debug(f'Polling channel {ch} (last processed count={len(processed)})')
                async for msg in client.iter_messages(ch, limit=20):
                    msgs_seen += 1
                    if not msg.text:
                        continue
                    msg_id_str = str(msg.id)
                    if msg_id_str in processed:
                        continue
                    dt = msg.date.astimezone(tz)
                    if dt < datetime.now(tz) - timedelta(minutes=30):
                        # Older than live window
                        continue
                    msgs_recent_window += 1
                    # Check for ballistic threat messages (realtime - add to chat)
                    update_ballistic_state(msg.text, is_realtime=True)
                    # Add other important messages to chat
                    add_telegram_message_to_chat(msg.text, is_realtime=True)
                    tracks = process_message(msg.text, msg.id, dt.strftime('%Y-%m-%d %H:%M:%S'), ch)
                    
                    # DEBUG: Log what process_message returned
                    print(f"[FETCH_DEBUG] msg.id={msg.id}, tracks={len(tracks) if tracks else 0}, has_coords={bool(tracks and tracks[0].get('lat'))}", flush=True)
                    if tracks:
                        print(f"[FETCH_DEBUG] First track: place={tracks[0].get('place')}, lat={tracks[0].get('lat')}, lng={tracks[0].get('lng')}", flush=True)

                    # Send push notification for threat messages (КАБи, ракети, БПЛА)
                    msg_lower = msg.text.lower()
                    if any(kw in msg_lower for kw in ['каб', 'ракет', 'балістичн', 'бпла', 'дрон', 'шахед', 'вибух']):
                        # Extract location from message (usually first part before threat description)
                        location = ''
                        if '(' in msg.text and ')' in msg.text:
                            # Format: "Харків (Харківська обл.) Загроза..."
                            location = msg.text.split(')')[0] + ')'
                        elif tracks and tracks[0].get('place'):
                            location = tracks[0]['place']
                        
                        # DEBUG: Log location extraction
                        print(f"[PUSH_DEBUG] msg_id={msg.id}, location='{location}', has_tracks={bool(tracks)}", flush=True)

                        if location:
                            # Pass FULL message text - function will extract threat part
                            send_telegram_threat_notification(msg.text, location, str(msg.id))
                        else:
                            # No location found - still try to send with raw text as fallback
                            print(f"[PUSH_DEBUG] No location found, trying with first 50 chars of msg", flush=True)
                            # Try to extract any region-like word from text
                            import re
                            oblast_match = re.search(r'([А-Яа-яІіЇїЄє]+(?:ська|ський)\s*обл)', msg.text, re.IGNORECASE)
                            if oblast_match:
                                location = oblast_match.group(1)
                                print(f"[PUSH_DEBUG] Found oblast in text: '{location}'", flush=True)
                                send_telegram_threat_notification(msg.text, location, str(msg.id))
                            else:
                                print(f"[PUSH_DEBUG] Could not extract location, skipping push for msg {msg.id}", flush=True)

                    if tracks:
                        merged_any = False
                        appended = []
                        for t in tracks:
                            merged, ref = maybe_merge_track(all_data, t)
                            print(f"[FETCH_DEBUG] Track {t.get('place')}: merged={merged}", flush=True)
                            if merged:
                                merged_any = True
                            else:
                                new_tracks.append(t)
                                appended.append(t)
                        geo_added += 1
                        processed.add(msg_id_str)
                        print(f"[FETCH_DEBUG] Result: merged_any={merged_any}, appended={len(appended)}, new_tracks_total={len(new_tracks)}", flush=True)
                        if merged_any and not appended:
                            log.info(f'Merged live track(s) {ch} #{msg.id} (no new marker).')
                        else:
                            log.info(f'Added track from {ch} #{msg.id} (+{len(appended)} new, merged={merged_any})')
                    else:
                        # Store raw if enabled to allow later reprocessing / debugging (e.g., napramok multi-line posts)
                        if ALWAYS_STORE_RAW:
                            all_data.append({
                                'id': msg_id_str, 'place': None, 'lat': None, 'lng': None,
                                'threat_type': None, 'text': msg.text[:800], 'date': dt.strftime('%Y-%m-%d %H:%M:%S'),
                                'channel': ch, 'pending_geo': True
                            })
                            processed.add(msg_id_str)
                        log.debug(f'Live skip (no geo): {ch} #{msg.id} {msg.text[:80]!r}')
            except AuthKeyDuplicatedError:
                log.error('AuthKeyDuplicatedError during live fetch. Ending loop until session replaced.')
                AUTH_STATUS.update({'authorized': False, 'reason': 'authkey_duplicated'})
                return
            except FloodWaitError as fe:
                wait = int(getattr(fe, 'seconds', 60))
                log.warning(f'FloodWait while reading {ch}: sleep {wait}s')
                await asyncio.sleep(wait)
            # Generic RPC errors will be caught by broad Exception if specific class not available
            except Exception as e:
                msg = str(e)
                log.warning(f'Error reading {ch}: {msg}')
                # Auto-mark invalid entity errors to skip future attempts this runtime
                markers = ['Cannot find any entity', 'CHANNEL_PRIVATE', 'USERNAME_NOT_OCCUPIED', 'TOPIC_DELETED']
                if any(mk in msg for mk in markers):
                    INVALID_CHANNELS.add(ch)
                    log.warning(f'Marking channel {ch} as invalid; will skip further reads this session.')
            finally:
                # Post-channel diagnostics to help debug silent channels like 'napramok'
                log.debug(
                    f'Channel diag {ch}: iter_messages_seen={msgs_seen}, recent_window={msgs_recent_window}, geo_added={geo_added}, invalid={ch in INVALID_CHANNELS}'
                )
                if msgs_seen == 0:
                    log.warning(f'Channel {ch} returned no messages this cycle (possible resolution/access issue).')
                elif msgs_recent_window == 0:
                    log.debug(f'Channel {ch} had messages but none within last 30m window.')
                elif geo_added == 0:
                    log.debug(f'Channel {ch} had {msgs_recent_window} recent messages but none produced geo tracks.')
        if new_tracks:
            # RACE CONDITION FIX: Reload all_data from disk before extending
            # This preserves updates made by /data endpoint's update_message()
            all_data = load_messages()
            processed = {m.get('id') for m in all_data}
            # Only add tracks that aren't already in the data (check by id)
            existing_ids = {m.get('id') for m in all_data}
            truly_new = [t for t in new_tracks if t.get('id') not in existing_ids]
            if truly_new:
                all_data.extend(truly_new)
                save_messages(all_data)
                try:
                    broadcast_new(truly_new)
                except Exception as e:
                    log.debug(f'SSE broadcast failed: {e}')
        # Note: removed periodic save_messages when no new tracks to avoid overwriting /data updates
        await asyncio.sleep(45)  # Check every 45 seconds (CPU optimized)

def start_fetch_thread():
    global FETCH_THREAD_STARTED
    log.info('start_fetch_thread() called')
    if not client:
        log.warning('start_fetch_thread: client is None')
        return
    if FETCH_THREAD_STARTED:
        log.info('start_fetch_thread: already started')
        return
    log.info('start_fetch_thread: starting new thread')
    FETCH_THREAD_STARTED = True
    loop = asyncio.new_event_loop()
    def runner():
        log.info('fetch_thread runner started')
        if FETCH_START_DELAY > 0:
            log.info(f'Delaying Telegram fetch start for {FETCH_START_DELAY}s (FETCH_START_DELAY).')
            time.sleep(FETCH_START_DELAY)
        asyncio.set_event_loop(loop)
        try:
            log.info('About to call fetch_loop()')
            loop.run_until_complete(fetch_loop())
        except AuthKeyDuplicatedError:
            AUTH_STATUS.update({'authorized': False, 'reason': 'authkey_duplicated_runner'})
            log.error('Fetch loop stopped: duplicated auth key.')
        except Exception as e:
            AUTH_STATUS.update({'authorized': False, 'reason': f'crash:{e.__class__.__name__}'})
            log.error(f'Fetch loop crashed: {e}')
        finally:
            log.info('fetch_thread runner finished')
    threading.Thread(target=runner, daemon=True).start()
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
def shahed_map():
    """Shahed map landing page"""
    return render_template('shahed_map.html')

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

@app.route('/')
def index():
    """Main page - Карта тривог України онлайн"""
    user_agent = request.headers.get('User-Agent', '')

    # SEO: Detect crawlers and serve optimized response
    if is_seo_bot(user_agent):
        # For bots: add extra SEO headers and potentially serve prerendered content
        response = render_template('index.html')
        resp = app.response_class(response)
        resp.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour for bots
        resp.headers['X-Robots-Tag'] = 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1'
        resp.headers['Link'] = '<https://neptun.in.ua/>; rel="canonical"'
        # Mark as bot request for debugging
        resp.headers['X-Bot-Detected'] = 'true'
        return resp

    # BANDWIDTH OPTIMIZATION: Add caching headers for main page
    response = render_template('index.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes cache
    resp.headers['ETag'] = f'index-{int(time.time() // 300)}'
    # SEO Headers for search engines
    resp.headers['X-Robots-Tag'] = 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1'
    resp.headers['Link'] = '<https://neptun.in.ua/>; rel="canonical"'
    return resp

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

    # Try API sources for exact match (используем 3 API параллельно)
    api_results = []

    # 1. Nominatim API (добавляем Ukraine в строку запроса)
    try:
        import requests
        nominatim_url = 'https://nominatim.openstreetmap.org/search'
        params = {
            'q': f'{query}, Ukraine',
            'format': 'json',
            'limit': 1,
            'accept-language': 'uk'
        }
        headers = {
            'User-Agent': 'NeptunAlarmMap/1.0 (https://neptun.in.ua)'
        }

        response = requests.get(nominatim_url, params=params, headers=headers, timeout=3)
        if response.ok:
            results = response.json()
            if isinstance(results, list) and len(results) > 0:
                result = results[0]
                if isinstance(result, dict):
                    lat_val = safe_float(result.get('lat'))
                    lng_val = safe_float(result.get('lon'))
                    if lat_val is not None and lng_val is not None and validate_ukraine_coords(lat_val, lng_val):
                        api_results.append({
                            'name': result.get('display_name', query).split(',')[0],
                            'lat': lat_val,
                            'lng': lng_val,
                            'source': 'nominatim'
                        })
    except Exception as e:
        log.warning(f'Nominatim exact match error: {e}')

    # 2. Photon API (самый быстрый и надёжный для украинских сел)
    try:
        photon_url = 'https://photon.komoot.io/api/'
        params = {
            'q': query,
            'limit': 1
        }

        response = requests.get(photon_url, params=params, timeout=3)
        if response.ok:
            data = response.json()
            features = data.get('features', [])
            if features and len(features) > 0:
                feature = features[0]
                props = feature.get('properties', {}) if isinstance(feature, dict) else {}
                coords = feature.get('geometry', {}).get('coordinates', []) if isinstance(feature, dict) else []
                if coords and len(coords) >= 2 and (props.get('country') == 'Україна' or props.get('country') == 'Ukraine'):
                    lng_val = safe_float(coords[0])
                    lat_val = safe_float(coords[1])
                    if lat_val is not None and lng_val is not None and validate_ukraine_coords(lat_val, lng_val):
                        api_results.append({
                            'name': props.get('name', query),
                            'lat': lat_val,
                            'lng': lng_val,
                            'source': 'photon'
                        })
    except Exception as e:
        log.warning(f'Photon exact match error: {e}')

    # 3. GeoNames API отключён (требует регистрацию, demo лимит исчерпан)
    # Photon + Nominatim дают полное покрытие всех украинских населённых пунктов

    # Если хотя бы один API вернул результат, используем его
    if api_results:
        # Приоритет: Photon (самый точный для украинских сел) > Nominatim
        for source_priority in ['photon', 'nominatim']:
            for result in api_results:
                if result['source'] == source_priority:
                    return jsonify({
                        'status': 'ok',
                        'name': result['name'],
                        'lat': result['lat'],
                        'lng': result['lng'],
                        'source': result['source']
                    })

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

    # ВСЕГДА используем несколько API для максимальной полноты поиска
    api_suggestions = set()

    # 1. Photon API (быстрее чем Nominatim, использует OpenStreetMap данные)
    try:
        import requests
        photon_url = 'https://photon.komoot.io/api/'
        params = {
            'q': query,
            'limit': 20
        }

        response = requests.get(photon_url, params=params, timeout=3)
        if response.ok:
            data = response.json()
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                name = props.get('name', '')
                country = props.get('country', '')
                if country == 'Україна' and name:
                    api_suggestions.add(name)
    except Exception as e:
        log.warning(f'Photon API error: {e}')

    # 2. Nominatim API (OpenStreetMap)
    try:
        import requests
        nominatim_url = 'https://nominatim.openstreetmap.org/search'
        params = {
            'q': f'{query}, Ukraine',
            'format': 'json',
            'limit': 30,
            'accept-language': 'uk',
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'NeptunAlarmMap/1.0 (https://neptun.in.ua)'
        }

        response = requests.get(nominatim_url, params=params, headers=headers, timeout=4)
        if response.ok:
            results = response.json()
            for result in results:
                # Пробуем разные поля для названия
                name = None
                address = result.get('address', {})

                # Приоритет полям
                for field in ['village', 'town', 'city', 'hamlet', 'suburb', 'municipality']:
                    if field in address:
                        name = address[field]
                        break

                if not name:
                    display_name = result.get('display_name', '')
                    if display_name:
                        name = display_name.split(',')[0]

                if name:
                    api_suggestions.add(name)
    except Exception as e:
        log.warning(f'Nominatim API error: {e}')

    # 3. GeoNames API отключён (требует регистрацию, demo лимит 20к/день исчерпан)
    # Photon + Nominatim дают полное покрытие всех украинских населённых пунктов

    # Объединяем локальные и API результаты
    suggestions.update(api_suggestions)

    # Sort and limit
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

@app.route('/data')
@protected_endpoint(is_heavy=True)  # PROTECTION: Rate limit + concurrency control
def data():
    global FALLBACK_REPARSE_CACHE, MAX_REPARSE_CACHE_SIZE

    # ===========================================================================
    # HARDENED /data ENDPOINT - Prevents 23GB+ traffic spikes
    # HIGH-LOAD OPTIMIZED: Added in-memory + persistent caching
    # DEPLOY-SAFE: Persistent cache survives server restarts (30 min TTL)
    # ===========================================================================
    
    # Allow forced reparse by clearing cache (admin use)
    if request.args.get('force_reparse') == 'true':
        print(f"[DATA] Force reparse requested, clearing FALLBACK_REPARSE_CACHE ({len(FALLBACK_REPARSE_CACHE)} items)")
        FALLBACK_REPARSE_CACHE.clear()

    # HIGH-LOAD: Check memory cache first (5 second TTL)
    cache_key = f'data_{MONITOR_PERIOD_MINUTES}'
    cached = RESPONSE_CACHE.get(cache_key)
    if cached:
        # Still check ETag for 304
        client_etag = request.headers.get('If-None-Match')
        if client_etag and cached.get('etag') == client_etag:
            return Response(status=304, headers={'Cache-Control': 'public, max-age=5'})

        response = jsonify(cached['data'])
        response.headers['Cache-Control'] = 'public, max-age=5'
        response.headers['X-Cache'] = 'HIT'
        if cached.get('etag'):
            response.headers['ETag'] = cached['etag']
        return response

    # PROTECTION: Hard limits to prevent memory/bandwidth exhaustion
    MAX_TRACKS = 200       # HARD LIMIT: max tracks per response (was unlimited)
    MAX_EVENTS = 100       # HARD LIMIT: max events per response (was unlimited)
    MAX_RESPONSE_MB = 2    # HARD LIMIT: max response size in MB

    # BANDWIDTH OPTIMIZATION: Add aggressive caching headers
    response_headers = {
        'Cache-Control': 'public, max-age=5',  # Reduced to match memory cache
        'ETag': f'data-{int(time.time() // 5)}',  # Cache for 5 seconds
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
    max_possible_ttl = 240  # 4 hours - max possible TTL for any threat type
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
        # Fallback reparse: if message lacks geo but contains course pattern, try to derive markers now
        (m.get('text') or '').lower()
        msg_id = m.get('id')

        # Skip multi-regional UAV messages - they're already handled by immediate processing
        text_full = m.get('text') or ''
        text_lines = text_full.split('\n')
        region_count = sum(1 for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:', 'край:']) or (
            'щина' in line.lower() and line.lower().strip().endswith(':')
        ))
        uav_count = sum(1 for line in text_lines if 'бпла' in line.lower() and ('курс' in line.lower() or 'на ' in line.lower()))

        # Process ALL messages without coordinates through process_message()
        if (not m.get('lat')) and (not m.get('lng')):
            debug_counts['pending_geo_processing'] = debug_counts.get('pending_geo_processing', 0) + 1
            
            # Skip if this is a multi-regional UAV message (already processed immediately)
            if region_count >= 2 and uav_count >= 3:
                add_debug_log(f"Skipping fallback reparse for multi-regional UAV message ID {msg_id}", "reparse")
                continue

            # Check if we've already reparsed this message to avoid duplicate processing
            if msg_id in FALLBACK_REPARSE_CACHE:
                debug_counts['already_cached'] = debug_counts.get('already_cached', 0) + 1
                continue

            try:
                # Add to cache to prevent future reprocessing
                FALLBACK_REPARSE_CACHE.add(msg_id)
                # Limit cache size to prevent memory growth
                if len(FALLBACK_REPARSE_CACHE) > MAX_REPARSE_CACHE_SIZE:
                    # Remove oldest half of the cache (approximate LRU)
                    cache_list = list(FALLBACK_REPARSE_CACHE)
                    FALLBACK_REPARSE_CACHE = set(cache_list[len(cache_list)//2:])

                msg_text = m.get('text') or ''
                print(f"[REPARSE] Processing pending_geo message {msg_id}: {repr(msg_text[:60])}...")
                add_debug_log(f"Fallback reparse for message ID {msg_id} - first time processing", "reparse")
                reparsed = process_message(msg_text, m.get('id'), m.get('date'), m.get('channel') or m.get('source') or '')
                print(f"[REPARSE] Result for {msg_id}: {len(reparsed) if reparsed else 0} tracks, coords: {reparsed[0].get('lat') if reparsed else 'none'}")
                if isinstance(reparsed, list) and reparsed:
                    debug_counts['reparse_success'] = debug_counts.get('reparse_success', 0) + 1
                    reparsed_any = False
                    for t in reparsed:
                        if t.get('list_only'):
                            if not t.get('suppress'):
                                events.append(t)
                                reparsed_any = True
                            continue
                        try:
                            lat_r = round(float(t.get('lat')), 3)
                            lng_r = round(float(t.get('lng')), 3)
                        except Exception:
                            debug_counts['reparse_no_coords'] = debug_counts.get('reparse_no_coords', 0) + 1
                            continue
                        text_r = (t.get('text') or '')
                        source_r = t.get('channel') or t.get('source') or ''
                        marker_key_r = f"{lat_r},{lng_r}|{text_r}|{source_r}"
                        if marker_key_r in hidden:
                            continue
                        out.append(t)
                        reparsed_any = True
                        
                        # IMPORTANT: Atomically update this message in storage
                        # This avoids race conditions with fetch thread
                        updates = {
                            'lat': lat_r,
                            'lng': lng_r,
                            'place': t.get('place'),
                            'threat_type': t.get('threat_type'),
                            'marker_icon': t.get('marker_icon'),
                            'pending_geo': False  # Mark as resolved
                        }
                        try:
                            if MESSAGE_STORE.update_message(str(msg_id), updates):
                                print(f"[REPARSE] Atomically updated message {msg_id} with coords ({lat_r}, {lng_r})")
                            else:
                                print(f"[REPARSE] Message {msg_id} not found in store")
                        except Exception as se:
                            print(f"[REPARSE] Failed to update: {se}")
                        
                    # Skip adding original as event if we produced tracks or list-only entries
                    if reparsed_any:
                        debug_counts['reparse_produced_tracks'] = debug_counts.get('reparse_produced_tracks', 0) + 1
                        continue
                else:
                    debug_counts['reparse_empty'] = debug_counts.get('reparse_empty', 0) + 1
            except Exception as e:
                debug_counts['reparse_error'] = debug_counts.get('reparse_error', 0) + 1
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

    # Replace old shahed.png with new shahed3.webp for backward compatibility
    for track in out:
        if track.get('marker_icon') == 'shahed.png':
            track['marker_icon'] = 'shahed3.webp'

    # DEBUG: Count tracks with trajectories
    traj_count = sum(1 for t in out if t.get('trajectory'))
    if traj_count > 0:
        print(f"[DEBUG] /data response has {traj_count} tracks with trajectories")

    # Build response with metadata about truncation
    response_data = {
        'tracks': out,
        'events': events,
        'all_sources': CHANNELS,
        'trajectories': [],
        # Ballistic threat state from Telegram
        'ballistic_threat': {
            'active': BALLISTIC_THREAT_ACTIVE,
            'region': BALLISTIC_THREAT_REGION,
            'timestamp': BALLISTIC_THREAT_TIMESTAMP,
        },
        # Smart threat tracking info
        'threat_tracking': threat_info,
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

    # HIGH-LOAD: Cache the response for 5 seconds (in-memory)
    RESPONSE_CACHE.set(cache_key, {
        'data': response_data,
        'etag': response_headers.get('ETag')
    }, ttl=5)

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

@app.route('/add_channel', methods=['POST'])
def add_channel():
    """Add a channel username or numeric ID at runtime.
    Body JSON: {"id": "-1001234567890", "secret": "..."}
    Requires AUTH_SECRET match if set.
    Persists into channels_dynamic.json and updates global list.
    """
    if AUTH_SECRET and request.json.get('secret') != AUTH_SECRET:
        return jsonify({'status':'error','error':'unauthorized'}), 403
    cid = str(request.json.get('id','')).strip()
    if not cid:
        return jsonify({'status':'error','error':'empty_id'}), 400
    global CHANNELS
    # Normalize removing leading @ or https link wrappers
    cid = cid.replace('https://t.me/','').replace('t.me/','')
    # Remove joinchat pattern if present (cannot directly fetch by invite hash)
    if cid.startswith('+'):
        # Cannot use invite hash directly; require numeric ID user already joined from session
        return jsonify({'status':'error','error':'invite_link_not_supported_use_numeric_id'}), 400
    if cid not in CHANNELS:
        CHANNELS.append(cid)
        # Persist dynamic list excluding originals from env for clarity
        orig_env = os.getenv('TELEGRAM_CHANNELS', '').split(',') if os.getenv('TELEGRAM_CHANNELS') else []
        dynamic_part = [c for c in CHANNELS if c.strip() and c.strip() not in orig_env]
        save_dynamic_channels(dynamic_part)
        log.info(f'Added channel {cid}. Total now {len(CHANNELS)}')
        return jsonify({'status':'ok','added':cid,'total':len(CHANNELS)})
    return jsonify({'status':'ok','added':False,'message':'exists','total':len(CHANNELS)})

# ---------------- Manual marker management -----------------

def _normalize_admin_trajectory(raw_traj):
    """Sanitize trajectory payload coming from admin UI."""
    if not isinstance(raw_traj, dict):
        return None

    def _pt(val):
        if not isinstance(val, (list, tuple)) or len(val) != 2:
            return None
        try:
            lat = float(val[0])
            lng = float(val[1])
            return [round(lat, 6), round(lng, 6)]
        except (TypeError, ValueError):
            return None

    start = _pt(raw_traj.get('start'))
    end = _pt(raw_traj.get('end'))
    if not (start and end):
        return None

    traj = {'start': start, 'end': end}
    for key in ('source', 'target', 'kind'):
        value = raw_traj.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                traj[key] = value[:160]
    return traj
@app.route('/admin/add_manual_marker', methods=['POST'])
def admin_add_manual_marker():
    """Add a manual marker via admin panel.
    JSON body: {"lat":..., "lng":..., "text":"...", "place":"...", "threat_type":"shahed", "icon":"optional.png", "rotation":0}
    Requires secret if configured.
    """
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403
    payload = request.get_json(silent=True) or {}
    try:
        lat = safe_float(payload.get('lat'))
        lng = safe_float(payload.get('lng'))
        if lat is None or lng is None:
            raise ValueError('invalid_coordinates')
        if not (43 <= lat <= 53.8 and 21 <= lng <= 41.5):
            raise ValueError('out_of_bounds')
        text = (payload.get('text') or '').strip()
        if not text:
            raise ValueError('empty_text')
        place = (payload.get('place') or '').strip()
        threat_type = (payload.get('threat_type') or '').strip().lower() or 'manual'
        allowed_types = {'shahed','raketa','avia','pvo','vibuh','alarm','alarm_cancel','mlrs','artillery','obstril','fpv','pusk','manual'}
        if threat_type not in allowed_types:
            threat_type = 'manual'
        icon = (payload.get('icon') or '').strip()
        rotation = payload.get('rotation', 0)
        try:
            rotation = float(rotation)
        except:
            rotation = 0
        trajectory = _normalize_admin_trajectory(payload.get('trajectory'))
        course_direction = (payload.get('course_direction') or '').strip() or None
        course_target = (payload.get('course_target') or '').strip() or None
        course_source = (payload.get('course_source') or '').strip() or (place or None)
        course_type = (payload.get('course_type') or '').strip() or None

        tz = pytz.timezone('Europe/Kyiv')
        now_dt = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        mid = 'manual-' + uuid.uuid4().hex[:12]
        messages = load_messages()
        # Build message dict similar to parsed messages
        msg = {
            'id': mid,
            'date': now_dt,
            'text': text,
            'place': place,
            'lat': round(lat, 6),
            'lng': round(lng, 6),
            'threat_type': threat_type,
            'marker_icon': icon or None,
            'rotation': rotation,
            'manual': True,
            'channel': 'manual',
            'source': 'manual'
        }
        if trajectory:
            msg['trajectory'] = trajectory
        if course_direction:
            msg['course_direction'] = course_direction
        if course_target:
            msg['course_target'] = course_target
        if course_source:
            msg['course_source'] = course_source
        if course_type:
            msg['course_type'] = course_type
        messages.append(msg)
        save_messages(messages)
        return jsonify({'status':'ok','id':mid})
    except Exception as e:
        return jsonify({'status':'error','error':str(e)}), 400

@app.route('/admin/update_manual_marker', methods=['POST'])
def admin_update_manual_marker():
    """Update existing manual marker coordinates/text/type."""
    if not _require_secret(request):
        return jsonify({'status': 'forbidden'}), 403

    payload = request.get_json(silent=True) or {}
    marker_id = (payload.get('id') or '').strip()
    if not marker_id:
        return jsonify({'status': 'error', 'error': 'missing_id'}), 400

    try:
        lat = safe_float(payload.get('lat'))
        lng = safe_float(payload.get('lng'))
        if lat is None or lng is None:
            raise ValueError('invalid_coordinates')
        if not (43 <= lat <= 53.8 and 21 <= lng <= 41.5):
            raise ValueError('out_of_bounds')
        place = (payload.get('place') or '').strip()
        text = (payload.get('text') or '').strip()
        if not text:
            raise ValueError('empty_text')
        threat_type = (payload.get('threat_type') or '').strip().lower() or 'manual'
        allowed_types = {'shahed','raketa','avia','pvo','vibuh','alarm','alarm_cancel','mlrs','artillery','obstril','fpv','pusk','manual'}
        if threat_type not in allowed_types:
            threat_type = 'manual'
        rotation = payload.get('rotation', 0)
        try:
            rotation = safe_float(rotation) or 0
        except Exception:
            rotation = 0

        trajectory = _normalize_admin_trajectory(payload.get('trajectory'))
        course_direction = (payload.get('course_direction') or '').strip()
        course_target = (payload.get('course_target') or '').strip()
        course_source = (payload.get('course_source') or '').strip()
        course_type = (payload.get('course_type') or '').strip()

        messages = load_messages()
        updated = False
        for msg in messages:
            if msg.get('id') != marker_id:
                continue
            msg['lat'] = round(lat, 6)
            msg['lng'] = round(lng, 6)
            msg['place'] = place
            msg['text'] = text
            msg['threat_type'] = threat_type
            msg['rotation'] = rotation
            msg['manual'] = msg.get('manual', True)

            if 'trajectory' in payload:
                if trajectory:
                    msg['trajectory'] = trajectory
                else:
                    msg.pop('trajectory', None)
            if 'course_direction' in payload:
                if course_direction:
                    msg['course_direction'] = course_direction
                else:
                    msg.pop('course_direction', None)
            if 'course_target' in payload:
                if course_target:
                    msg['course_target'] = course_target
                else:
                    msg.pop('course_target', None)
            if 'course_source' in payload:
                if course_source:
                    msg['course_source'] = course_source
                else:
                    msg.pop('course_source', None)
            if 'course_type' in payload:
                if course_type:
                    msg['course_type'] = course_type
                else:
                    msg.pop('course_type', None)
            updated = True
            break

        if not updated:
            return jsonify({'status': 'error', 'error': 'not_found'}), 404

        save_messages(messages)
        return jsonify({'status': 'ok', 'id': marker_id})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 400

@app.route('/admin/markers')
def admin_markers():
    """API endpoint to get recent markers for admin map"""
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403

    all_msgs = load_messages()
    # Get recent markers (exclude pending geo)
    recent_markers = [m for m in reversed(all_msgs) if m.get('lat') and m.get('lng') and not m.get('pending_geo')][:120]

    return jsonify({
        'status': 'ok',
        'markers': recent_markers,
        'count': len(recent_markers)
    })

@app.route('/admin/raw_msgs')
def admin_raw_msgs():
    """API endpoint to get raw messages (pending geo) for admin panel"""
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403

    all_msgs = load_messages()
    raw_msgs = [m for m in reversed(all_msgs) if m.get('pending_geo')][:100]  # latest 100
    raw_count = len([m for m in all_msgs if m.get('pending_geo')])

    return jsonify({
        'status': 'ok',
        'raw_msgs': raw_msgs,
        'raw_count': raw_count
    })

@app.route('/admin/delete_manual_marker', methods=['POST'])
def admin_delete_manual_marker():
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403
    payload = request.get_json(silent=True) or {}
    mid = (payload.get('id') or '').strip()
    if not mid:
        return jsonify({'status':'error','error':'missing id'}), 400
    try:
        messages = load_messages()
        new_list = [m for m in messages if not (m.get('manual') and m.get('id') == mid)]
        if len(new_list) == len(messages):
            return jsonify({'status':'ok','deleted':False})
        save_messages(new_list)
        return jsonify({'status':'ok','deleted':True})
    except Exception as e:
        return jsonify({'status':'error','error':str(e)}), 500

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

        # Calculate Groq cooldown status
        groq_cooldown_remaining = 0
        groq_available = _groq_is_available() if GROQ_ENABLED else False
        if GROQ_ENABLED and _groq_daily_cooldown_until > 0:
            import time as time_module
            groq_cooldown_remaining = max(0, int(_groq_daily_cooldown_until - time_module.time()))

        return jsonify({
            'status':'ok',
            'messages':len(load_messages()),
            'auth': AUTH_STATUS,
            'visitors': visitors,
            'firebase_initialized': firebase_initialized,
            'devices_count': len(device_store._load()) if device_store else 0,
            'groq_enabled': GROQ_ENABLED,
            'groq_model': GROQ_MODEL if GROQ_ENABLED else None,
            'groq_available': groq_available,
            'groq_cooldown_seconds': groq_cooldown_remaining
        })

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

    stats = _load_visit_stats()
    if vid not in stats:
        stats[vid] = now
        if int(now) % 200 == 0:
            _prune_visit_stats()
        _save_visit_stats()

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
        first_seen = prev.get('first') or db_first or stats.get(vid) or now
        ACTIVE_VISITORS[vid] = {
            'ts': now,
            'first': first_seen,
            'ip': remote_ip,
            'ua': prev.get('ua') or ua,
            'platform': platform_label,
            'nickname': nickname if nickname else prev.get('nickname', '')
        }
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
def _require_secret(req):
    if not AUTH_SECRET:
        return True
    supplied = req.args.get('secret') or req.headers.get('X-Auth-Secret') or req.form.get('secret')
    return supplied and supplied == AUTH_SECRET

@app.route('/version')
def version_check():
    return {'version': '2024-12-06-oblast-raion-fix', 'timestamp': time.time()}

@app.route('/test_oblast_raion')
def test_oblast_raion():
    if not _require_secret(request):
        return Response('Forbidden', status=403)

    test_text = "Загроза застосування БПЛА. Перейдіть в укриття! | чернігівська область (чернігівський район), київська область (вишгородський район), сумська область (сумський, конотопський райони) - загроза ударних бпла!"
    result = process_message(test_text, 'test_99999', '2024-12-06', 'test_channel')

    return {
        'test_text': test_text,
        'result': result,
        'debug_logs': [log for log in DEBUG_LOGS if log.get('category') == 'oblast_raion'][-10:]
    }

@app.route('/test-pusk')
def test_pusk_icon():
    """Test route to debug pusk.png display issues"""
    with open('/Users/vladimirmalik/Desktop/render2/test_pusk_icon.html', encoding='utf-8') as f:
        return f.read()

@app.route('/clear_geocache')
def clear_geocache():
    """Clear all geocoding caches (in-memory, file, and negative) to force re-geocoding"""
    global _mapstransler_geocode_cache
    
    # Clear in-memory cache
    old_count = len(_mapstransler_geocode_cache)
    _mapstransler_geocode_cache = {}
    
    # Clear OpenCage caches (both in-memory and file)
    try:
        import opencage_geocoder
        pos_count = len(opencage_geocoder._cache)
        neg_count = len(opencage_geocoder._negative_cache)
        
        # Clear in-memory
        opencage_geocoder._cache = {}
        opencage_geocoder._negative_cache = set()
        
        # Clear files
        opencage_geocoder._save_cache()
        opencage_geocoder._save_negative_cache()
        
        return f"Cleared {old_count} mapstransler + {pos_count} positive + {neg_count} negative cache entries. All cities will be re-geocoded."
    except Exception as e:
        return f"Cleared {old_count} mapstransler entries. OpenCage error: {e}"

@app.route('/view_geocache')
def view_geocache():
    """View current geocoding cache contents"""
    try:
        import opencage_geocoder
        cache_data = dict(opencage_geocoder._cache)
        neg_cache = list(opencage_geocoder._negative_cache)
        stats = opencage_geocoder.get_cache_stats()
        return jsonify({
            'positive_cache': {k: list(v) if isinstance(v, tuple) else v for k, v in cache_data.items()},
            'negative_cache': neg_cache,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/admin')
def admin_panel():
    if not _require_secret(request):
        return Response('Forbidden', status=403)
    # Ensure rolling recent visits file is seeded from durable SQLite (survives redeploy)
    try:
        _seed_recent_from_sql()
    except Exception:
        pass
    now = time.time()
    # Merge ACTIVE_VISITORS volatile data with persistent DB to avoid session age resets on restart
    # Strategy: build dict from DB for active window; overlay runtime (for ip/ua freshness)
    db_active = {s['id']: s for s in _active_sessions_from_db(ACTIVE_TTL)}
    with ACTIVE_LOCK:
        visitors = []
        for vid, meta in ACTIVE_VISITORS.items():
            if isinstance(meta,(int,float)):
                mem_first = meta
                mem_last = meta
                db_sess = db_active.get(vid)
                if db_sess:
                    first_ts = db_sess.get('first') or mem_first
                    last_ts = db_sess.get('last') or mem_last
                else:
                    first_ts = mem_first
                    last_ts = mem_last
            else:
                mem_first = meta.get('first') or meta.get('ts', now)
                mem_last = meta.get('ts', mem_first)
                db_sess = db_active.get(vid)
                if db_sess:
                    # Use earlier first (older session start) and later last (most recent activity)
                    first_ts = min(mem_first, db_sess.get('first') or mem_first)
                    last_ts = max(mem_last, db_sess.get('last') or mem_last)
                else:
                    first_ts, last_ts = mem_first, mem_last
            if first_ts > last_ts:
                first_ts, last_ts = last_ts, first_ts
            sess_age = int(now - first_ts)
            idle_age = int(now - last_ts)
            ua = (meta.get('ua') if isinstance(meta, dict) else '') or ''
            ip = (meta.get('ip') if isinstance(meta, dict) else '') or ''
            nickname = (meta.get('nickname') if isinstance(meta, dict) else '') or ''
            visitors.append({
                'id': vid,
                'ip': ip,
                'age': sess_age,
                'age_fmt': _fmt_age(sess_age),
                'ua': ua,
                'ua_short': _ua_label(ua) if ua else '',
                'last_seen': _fmt_age(idle_age),
                'nickname': nickname
            })
    blocked = load_blocked()
    # Load raw (pending geo) messages
    all_msgs = load_messages()
    raw_msgs = [m for m in reversed(all_msgs) if m.get('pending_geo')][:100]  # latest 100
    # Collect last N geo markers (exclude pending geo) for hide management
    recent_markers = [m for m in reversed(all_msgs) if m.get('lat') and m.get('lng') and not m.get('pending_geo')][:120]
    # --- Visit stats aggregation (prefer durable SQLite to survive redeploy) ---
    daily_unique, week_unique = sql_unique_counts()
    if daily_unique is None:
        # fallback to rolling sets file if DB unavailable
        daily_unique, week_unique = _recent_counts()
    if daily_unique is None:  # final fallback to json stats
        stats = _load_visit_stats()
        tz = pytz.timezone('Europe/Kyiv')
        now_dt = datetime.now(tz)
        today_str = now_dt.strftime('%Y-%m-%d')
        week_cut = now_dt - timedelta(days=7)
        daily_unique = 0
        week_unique = 0
        for vid, ts in stats.items():
            try:
                tsf = float(ts)
            except Exception:
                continue
            dt = datetime.fromtimestamp(tsf, tz)
            if dt.strftime('%Y-%m-%d') == today_str:
                daily_unique += 1
            if dt >= week_cut:
                week_unique += 1
    hidden_keys = load_hidden()
    parsed_hidden = []
    for hk in hidden_keys:
        try:
            coord_part, text_part, source_part = hk.split('|',2)
            lat_str, lng_str = coord_part.split(',',1)
            parsed_hidden.append({'lat':lat_str,'lng':lng_str,'text':text_part,'source':source_part,'key':hk})
        except Exception:
            continue

    # Load commercial subscriptions (from persistent storage)
    subscriptions = []
    if os.path.exists(COMMERCIAL_SUBSCRIPTIONS_FILE):
        try:
            with open(COMMERCIAL_SUBSCRIPTIONS_FILE, encoding='utf-8') as f:
                subscriptions = json.load(f)
            # Sort by timestamp (newest first)
            subscriptions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        except Exception as e:
            print(f"❌ Failed to load subscriptions: {e}")

    return render_template(
        'admin.html',
        visitors=visitors,
        blocked=blocked,
        raw_msgs=raw_msgs,
        raw_count=len([m for m in all_msgs if m.get('pending_geo')]),
        secret=(request.args.get('secret') or ''),
        monitor_period=MONITOR_PERIOD_MINUTES,
        markers=recent_markers,
        daily_unique=daily_unique,
        week_unique=week_unique,
        hidden_markers=parsed_hidden,
        neg_geocode=list(_load_neg_geocode_cache().items())[:150],
        debug_logs=DEBUG_LOGS,
        redirect_stats=get_redirect_stats(),
        subscriptions=subscriptions
    )

@app.route('/admin/clear_debug_logs', methods=['POST'])
def clear_debug_logs():
    if not _require_secret(request):
        return jsonify({'status': 'forbidden'}), 403
    global DEBUG_LOGS
    DEBUG_LOGS.clear()
    return jsonify({'status': 'ok', 'cleared': True})

@app.route('/admin/set_monitor_period', methods=['POST'])
def set_monitor_period():
    if not _require_secret(request):
        return jsonify({'status': 'forbidden'}), 403
    global MONITOR_PERIOD_MINUTES
    payload = request.get_json(silent=True) or request.form
    try:
        val = int(payload.get('value'))
        if not (1 <= val <= 360):
            raise ValueError('out of range')
        MONITOR_PERIOD_MINUTES = val
        save_config()
        print(f"[DEBUG] MONITOR_PERIOD_MINUTES updated to {MONITOR_PERIOD_MINUTES} minutes")
        return jsonify({'status':'ok','monitor_period':MONITOR_PERIOD_MINUTES})
    except Exception as e:
        return jsonify({'status':'error','error':str(e)}), 400

@app.route('/admin/threat_tracker', methods=['GET'])
def admin_threat_tracker():
    """Get current threat tracking status"""
    active_threats = THREAT_TRACKER.get_all_active_threats()

    # Serialize threats for JSON
    threats_json = []
    for t in active_threats:
        threat_copy = {}
        for k, v in t.items():
            if isinstance(v, datetime):
                threat_copy[k] = v.isoformat()
            elif k == 'history':
                # Skip history for summary
                threat_copy[k] = len(v)
            else:
                threat_copy[k] = v
        threats_json.append(threat_copy)

    # Summary by type
    by_type = {}
    for t in active_threats:
        tt = t.get('threat_type', 'unknown')
        if tt not in by_type:
            by_type[tt] = {'count': 0, 'total_quantity': 0, 'destroyed': 0}
        by_type[tt]['count'] += 1
        by_type[tt]['total_quantity'] += t.get('quantity', 1)
        by_type[tt]['destroyed'] += t.get('quantity_destroyed', 0)

    return jsonify({
        'active_threats': threats_json,
        'by_type': by_type,
        'total_active': len(active_threats),
        'total_tracked': len(THREAT_TRACKER.threats),
        'regions_with_threats': list(THREAT_TRACKER.region_to_threats.keys())
    })

@app.route('/api/threats', methods=['GET'])
def api_threats():
    """
    Public API for active threats - counts from recent messages.
    Used by mobile widget for real-time threat display.
    """
    try:
        from datetime import datetime, timedelta
        import pytz
        kyiv_tz = pytz.timezone('Europe/Kyiv')
        now_kyiv = datetime.now(kyiv_tz)
        cutoff_time = now_kyiv - timedelta(minutes=30)  # Only last 30 minutes
        
        messages = load_messages()
        
        # Count threats by type from recent messages
        drones = 0
        missiles = 0  
        kab = 0
        ballistic = 0
        
        seen_texts = set()  # Avoid counting duplicates
        
        for msg in messages[-200:]:  # Check last 200 messages
            if not isinstance(msg, dict):
                continue
            
            text = (msg.get('text') or '').lower()
            
            # Check timestamp if available
            msg_date = msg.get('date') or msg.get('timestamp', '')
            if msg_date:
                try:
                    if isinstance(msg_date, str):
                        # Parse various date formats
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                            try:
                                dt = datetime.strptime(msg_date[:19], fmt)
                                dt = kyiv_tz.localize(dt)
                                break
                            except:
                                continue
                        else:
                            continue
                    else:
                        continue
                    
                    if dt < cutoff_time:
                        continue
                except:
                    pass
            
            # Normalize text for dedup
            text_key = text[:50]
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)
            
            # Parse quantity if present (e.g. "2х БПЛА", "3 шахеди")
            qty = 1
            qty_match = re.search(r'(\d+)\s*[xхХ]?\s*(?:бпла|шахед|дрон|ракет|каб)', text)
            if qty_match:
                qty = int(qty_match.group(1))
            
            # Count by type
            if any(w in text for w in ['шахед', 'shahed', 'герань']):
                drones += qty
            elif any(w in text for w in ['бпла', 'дрон', 'uav', 'безпілот']):
                drones += qty
            elif any(w in text for w in ['каб', 'керована бомба', 'авіабомб']):
                kab += qty
            elif any(w in text for w in ['балістик', 'іскандер', 'ballistic']):
                ballistic += qty
            elif any(w in text for w in ['крилат', 'калібр', 'х-101', 'cruise', 'ракет']):
                missiles += qty
        
        # Build response with threat data
        threats = []
        if drones > 0:
            threats.append({
                'threat_type': 'drone',
                'quantity': drones,
                'quantity_remaining': drones,
                'status': 'active',
                'created_at': now_kyiv.isoformat()
            })
        if missiles > 0:
            threats.append({
                'threat_type': 'cruise',
                'quantity': missiles,
                'quantity_remaining': missiles,
                'status': 'active',
                'created_at': now_kyiv.isoformat()
            })
        if kab > 0:
            threats.append({
                'threat_type': 'kab',
                'quantity': kab,
                'quantity_remaining': kab,
                'status': 'active',
                'created_at': now_kyiv.isoformat()
            })
        if ballistic > 0:
            threats.append({
                'threat_type': 'ballistic',
                'quantity': ballistic,
                'quantity_remaining': ballistic,
                'status': 'active',
                'created_at': now_kyiv.isoformat()
            })
        
        return jsonify({
            'threats': threats,
            'summary': {
                'total': drones + missiles + kab + ballistic,
                'drones': drones,
                'missiles': missiles,
                'kab': kab,
                'ballistic': ballistic
            },
            'updated_at': now_kyiv.isoformat()
        })
        
    except Exception as e:
        print(f"[API /api/threats] Error: {e}")
        return jsonify({
            'threats': [],
            'summary': {'total': 0, 'drones': 0, 'missiles': 0, 'kab': 0, 'ballistic': 0},
            'error': str(e)
        })

@app.route('/api/fusion/events', methods=['GET'])
def api_fusion_events():
    """
    API для отримання об'єднаних подій з системи злиття каналів.

    Повертає активні події з комбінованою інформацією з різних джерел.
    """
    try:
        events = CHANNEL_FUSION.get_active_events()

        # Group by status
        by_status = {
            'active': [],
            'partially_destroyed': [],
            'destroyed': [],
            'passed': [],
        }

        for event in events:
            status = event.get('status', 'active')
            if status in by_status:
                by_status[status].append(event)
            else:
                by_status['active'].append(event)

        # Serialize events
        serialized = []
        for event in events:
            ser_event = {
                'id': event['id'],
                'threat_type': event['threat_type'],
                'quantity': event['quantity'],
                'quantity_destroyed': event['quantity_destroyed'],
                'regions': event['regions'],
                'direction': event['direction'],
                'status': event['status'],
                'confidence': event['confidence'],
                'coordinates': event['best_coordinates'],
                'trajectory_points': len(event['trajectory']),
                'source_count': len({m['channel'] for m in event['messages']}),
                'sources': list({m['channel'] for m in event['messages']}),
                'created_at': event['created_at'].isoformat(),
                'last_update': event['last_update'].isoformat(),
            }
            serialized.append(ser_event)

        return jsonify({
            'status': 'ok',
            'events': serialized,
            'summary': {
                'total': len(events),
                'active': len(by_status['active']),
                'destroyed': len(by_status['destroyed']),
                'passed': len(by_status['passed']),
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/fusion/markers', methods=['GET'])
def api_fusion_markers():
    """
    API для отримання маркерів з системи злиття.

    Ці маркери можна використовувати на карті замість звичайних.
    """
    try:
        markers = get_fused_markers()

        return jsonify({
            'status': 'ok',
            'markers': markers,
            'count': len(markers)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/fusion/trajectories', methods=['GET'])
def api_fusion_trajectories():
    """
    API для отримання траєкторій руху загроз.

    Повертає траєкторії побудовані з послідовних повідомлень.
    """
    try:
        trajectories = get_fused_trajectories()

        return jsonify({
            'status': 'ok',
            'trajectories': trajectories,
            'count': len(trajectories)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/fusion/status', methods=['GET'])
def api_fusion_status():
    """
    Статус системи злиття каналів.
    """
    try:
        with CHANNEL_FUSION.lock:
            total_events = len(CHANNEL_FUSION.fused_events)
            total_messages = len(CHANNEL_FUSION.message_to_event)

            # Count by channel
            channel_counts = {}
            ai_analyzed_count = 0
            for event in CHANNEL_FUSION.fused_events.values():
                for msg in event['messages']:
                    ch = msg['channel']
                    channel_counts[ch] = channel_counts.get(ch, 0) + 1
                # Check if AI analyzed
                sig = event.get('signature', {})
                if sig.get('ai_analyzed'):
                    ai_analyzed_count += 1

        return jsonify({
            'status': 'ok',
            'fusion_enabled': True,
            'ai_enabled': GROQ_ENABLED,
            'ai_model': GROQ_MODEL if GROQ_ENABLED else None,
            'ai_analyzed_events': ai_analyzed_count,
            'total_events': total_events,
            'total_messages_processed': total_messages,
            'by_channel': channel_counts,
            'channel_priorities': CHANNEL_FUSION.CHANNEL_PRIORITY,
            'mode': 'AI-FIRST' if GROQ_ENABLED else 'REGEX-FALLBACK',
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/admin/fusion/cleanup', methods=['POST'])
def admin_fusion_cleanup():
    """
    Примусове очищення старих подій fusion.
    """
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403

    try:
        removed = CHANNEL_FUSION.cleanup_old_events(max_age_hours=1)
        return jsonify({
            'status': 'ok',
            'removed_events': removed
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/admin/neg_geocode_clear', methods=['POST'])
def admin_neg_geocode_clear():
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403
    global _neg_geocode_cache
    _neg_geocode_cache = {}
    _save_neg_geocode_cache()
    return jsonify({'status':'ok','cleared':True})

@app.route('/admin/neg_geocode_delete', methods=['POST'])
def admin_neg_geocode_delete():
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403
    payload = request.get_json(silent=True) or {}
    name = (payload.get('name') or '').strip().lower()
    if not name:
        return jsonify({'status':'error','error':'name required'}),400
    cache = _load_neg_geocode_cache()
    if name in cache:
        del cache[name]
        _save_neg_geocode_cache()
        return jsonify({'status':'ok','deleted':True})
    return jsonify({'status':'error','error':'not found'}),404

@app.route('/admin/stats', methods=['GET'])
def admin_stats():
    """Get comprehensive system statistics for admin dashboard"""
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403

    try:
        all_msgs = load_messages()
        now = time.time()
        pytz.timezone('Europe/Kyiv')

        # Message statistics
        total_messages = len(all_msgs)
        pending_geo = len([m for m in all_msgs if m.get('pending_geo')])
        with_coordinates = len([m for m in all_msgs if m.get('lat') and m.get('lng')])

        # Recent activity (last 24h)
        cutoff_24h = now - 86400
        recent_msgs = [m for m in all_msgs if _msg_timestamp(m) > cutoff_24h]

        # Threat type breakdown
        threat_counts = {}
        for msg in all_msgs:
            if not msg.get('pending_geo') and msg.get('lat') and msg.get('lng'):
                threat_type = msg.get('threat_type', 'unknown')
                threat_counts[threat_type] = threat_counts.get(threat_type, 0) + 1

        # System health
        with ACTIVE_LOCK:
            active_users = len(ACTIVE_VISITORS)
        blocked_users = len(load_blocked())
        hidden_markers = len(load_hidden())
        neg_cache_size = len(_load_neg_geocode_cache())
        debug_logs_count = len(DEBUG_LOGS)

        return jsonify({
            'status': 'ok',
            'stats': {
                'messages': {
                    'total': total_messages,
                    'pending_geo': pending_geo,
                    'with_coordinates': with_coordinates,
                    'recent_24h': len(recent_msgs)
                },
                'threats': threat_counts,
                'system': {
                    'active_users': active_users,
                    'blocked_users': blocked_users,
                    'hidden_markers': hidden_markers,
                    'neg_cache_size': neg_cache_size,
                    'debug_logs': debug_logs_count,
                    'monitor_period': MONITOR_PERIOD_MINUTES
                },
                'timestamp': now
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ==================== API PROTECTION MONITORING ====================
@app.route('/admin/protection_status', methods=['GET'])
def admin_protection_status():
    """Get API protection statistics for monitoring bandwidth/abuse."""
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403

    try:
        if API_PROTECTION_ENABLED:
            stats = get_protection_stats()
            return jsonify({
                'status': 'ok',
                'protection_enabled': True,
                'max_response_size_mb': MAX_RESPONSE_SIZE_BYTES / 1024 / 1024,
                'stats': stats,
                'endpoint_limits': {
                    '/data': {'max_tracks': 200, 'max_events': 100},
                    '/api/messages': {'max_messages': 100},
                    '/api/events': {'max_process': 500, 'max_return': 100},
                    '/api/alarm-history': {'max_days': 7, 'max_results': 200},
                    '/alarms_stats': {'max_limit': 500, 'max_minutes': 360},
                }
            })
        else:
            return jsonify({
                'status': 'ok',
                'protection_enabled': False,
                'message': 'API protection module not loaded'
            })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500
# ===================================================================

@app.route('/admin/cleanup', methods=['POST'])
def admin_cleanup():
    """Clean up old data to maintain performance"""
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403

    payload = request.get_json(silent=True) or {}
    days_to_keep = int(payload.get('days', 7))  # Keep last 7 days by default

    try:
        cutoff_time = time.time() - (days_to_keep * 86400)

        # Clean old messages
        all_msgs = load_messages()
        old_count = len(all_msgs)
        new_msgs = [m for m in all_msgs if _msg_timestamp(m) > cutoff_time]

        # Always keep at least 100 most recent messages
        if len(new_msgs) < 100 and len(all_msgs) >= 100:
            new_msgs = sorted(all_msgs, key=_msg_timestamp, reverse=True)[:100]

        save_messages(new_msgs)

        # Clean old debug logs (keep last 500)
        global DEBUG_LOGS
        if len(DEBUG_LOGS) > 500:
            DEBUG_LOGS = DEBUG_LOGS[-500:]

        # Clean old visitor data from SQLite
        try:
            conn = sqlite3.connect(VISIT_DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM visits WHERE first_seen < ?", (cutoff_time,))
            deleted_visits = c.rowcount
            conn.commit()
            conn.close()
        except Exception:
            deleted_visits = 0

        return jsonify({
            'status': 'ok',
            'cleaned': {
                'messages': old_count - len(new_msgs),
                'debug_logs': max(0, len(DEBUG_LOGS) - 500),
                'visitor_records': deleted_visits
            },
            'remaining': {
                'messages': len(new_msgs),
                'debug_logs': len(DEBUG_LOGS)
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/admin/memory', methods=['GET'])
def admin_memory():
    """Get memory usage statistics for debugging memory leaks."""
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403
    
    import gc
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        mem_mb = mem_info.rss / 1024 / 1024
        mem_percent = process.memory_percent()
    except ImportError:
        mem_mb = 0
        mem_percent = 0
    
    # Count sizes of major in-memory caches
    cache_sizes = {
        'response_cache': len(RESPONSE_CACHE._cache),
        'request_counts_keys': len(request_counts),
        'request_counts_total_timestamps': sum(len(v) for v in request_counts.values()),
        'telegram_alert_sent': len(_telegram_alert_sent),
        'telegram_region_notified': len(_telegram_region_notified),
        'active_visitors': len(ACTIVE_VISITORS),
        'debug_logs': len(DEBUG_LOGS),
        'fallback_reparse_cache': len(FALLBACK_REPARSE_CACHE),
        'mapstransler_geocode_cache': len(_mapstransler_geocode_cache),
        'groq_cache': len(_groq_cache) if '_groq_cache' in dir() else 0,
        'messages_cache': len(_MESSAGES_CACHE.get('data') or []) if _MESSAGES_CACHE.get('data') else 0,
    }
    
    # Estimate sizes
    try:
        import sys
        estimated_sizes = {}
        for name, obj in [
            ('request_counts', request_counts),
            ('ACTIVE_VISITORS', ACTIVE_VISITORS),
            ('_mapstransler_geocode_cache', _mapstransler_geocode_cache),
        ]:
            estimated_sizes[name] = sys.getsizeof(obj)
    except:
        estimated_sizes = {}
    
    # Garbage collection stats
    gc_stats = {
        'objects': len(gc.get_objects()),
        'garbage': len(gc.garbage),
    }
    
    return jsonify({
        'status': 'ok',
        'memory_mb': round(mem_mb, 2),
        'memory_percent': round(mem_percent, 2),
        'cache_sizes': cache_sizes,
        'estimated_bytes': estimated_sizes,
        'gc': gc_stats,
    })

@app.route('/admin/export', methods=['GET'])
def admin_export():
    """Export data for backup/analysis"""
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403

    export_type = request.args.get('type', 'messages')

    try:
        if export_type == 'messages':
            all_msgs = load_messages()
            # Remove sensitive data
            clean_msgs = []
            for msg in all_msgs:
                clean_msg = {k: v for k, v in msg.items() if k not in ['id']}
                clean_msgs.append(clean_msg)
            return jsonify({'status': 'ok', 'data': clean_msgs, 'count': len(clean_msgs)})

        elif export_type == 'stats':
            with ACTIVE_LOCK:
                active_count = len(ACTIVE_VISITORS)

            return jsonify({
                'status': 'ok',
                'data': {
                    'active_users': active_count,
                    'blocked_users': len(load_blocked()),
                    'hidden_markers': len(load_hidden()),
                    'neg_cache_entries': len(_load_neg_geocode_cache()),
                    'debug_logs': len(DEBUG_LOGS),
                    'monitor_period': MONITOR_PERIOD_MINUTES,
                    'export_time': time.time()
                }
            })

        else:
            return jsonify({'status': 'error', 'error': 'Invalid export type'}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500
        _save_neg_geocode_cache()
        return jsonify({'status':'ok','removed':name})
    return jsonify({'status':'ok','removed':None})

@app.route('/block', methods=['POST'])
def block_id():
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403
    payload = request.get_json(silent=True) or request.form
    vid = (payload or {}).get('id')
    if not vid:
        return jsonify({'status':'error','error':'id required'}), 400
    blocked = load_blocked()
    if vid not in blocked:
        blocked.append(vid)
        save_blocked(blocked)
    # push control event so client can self-block immediately
    broadcast_control({'type':'block','id':vid})
    return jsonify({'status':'ok','blocked':blocked})

@app.route('/unblock', methods=['POST'])
def unblock_id():
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403
    payload = request.get_json(silent=True) or request.form
    vid = (payload or {}).get('id')
    if not vid:
        return jsonify({'status':'error','error':'id required'}), 400
    blocked = load_blocked()
    if vid in blocked:
        blocked.remove(vid)
        save_blocked(blocked)
    return jsonify({'status':'ok','blocked':blocked})

@app.route('/admin/hidden_markers')
def admin_hidden_markers():
    """Return list of all hidden markers with metadata."""
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403
    hidden_keys = load_hidden()
    hidden_list = []
    for key in hidden_keys:
        try:
            parts = key.split('|', 2)
            if len(parts) >= 3:
                lat_lng, text, source = parts
                lat_str, lng_str = lat_lng.split(',')
                hidden_list.append({
                    'lat': float(lat_str),
                    'lng': float(lng_str),
                    'text': text,
                    'source': source,
                    'key': key
                })
        except Exception as e:
            log.warning(f"Failed to parse hidden marker key: {key}, error: {e}")
    return jsonify({'status':'ok', 'hidden': hidden_list, 'count': len(hidden_list)})

@app.route('/admin/unhide_marker', methods=['POST'])
def admin_unhide_marker():
    """Unhide a marker (alias for /unhide_marker with auth check)."""
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403
    return unhide_marker()

def _fmt_age(age_seconds:int)->str:
    # Format seconds to H:MM:SS (or M:SS if <1h)
    if age_seconds < 3600:
        m, s = divmod(age_seconds, 60)
        return f"{m}:{s:02d}"
    h, rem = divmod(age_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"

def _ua_label(ua:str)->str:
    u = ua.lower()
    # Simple detection heuristics
    if 'android' in u:
        if 'wv' in u or 'version/' in u:
            base = 'Android WebView'
        else:
            base = 'Android'
    elif 'iphone' in u or 'ipad' in u or 'ipod' in u:
        base = 'iOS'
    elif 'mac os x' in u and 'mobile' not in u:
        base = 'macOS'
    elif 'windows nt' in u:
        base = 'Windows'
    elif 'linux' in u:
        base = 'Linux'
    else:
        base = 'Other'
    # Browser
    browser = 'Browser'
    if 'chrome/' in u and 'edg/' not in u and 'opr/' not in u:
        browser = 'Chrome'
    elif 'edg/' in u:
        browser = 'Edge'
    elif 'firefox/' in u:
        browser = 'Firefox'
    elif 'safari/' in u and 'chrome/' not in u:
        browser = 'Safari'
    elif 'opr/' in u or 'opera' in u:
        browser = 'Opera'
    return f"{base} {browser}"

# NOTE: _load_opencage_cache, _save_opencage_cache, SETTLEMENTS_* defined earlier in the file

# --------------- Optional Git auto-commit settings ---------------
GIT_AUTO_COMMIT = os.getenv('GIT_AUTO_COMMIT', '0') not in ('0','false','False','')
GIT_REPO_SLUG = os.getenv('GIT_REPO_SLUG')  # e.g. 'vavaika22423232/neptun'
GIT_SYNC_TOKEN = os.getenv('GIT_SYNC_TOKEN')  # GitHub PAT (classic or fine-grained) with repo write
GIT_COMMIT_INTERVAL = int(os.getenv('GIT_COMMIT_INTERVAL', '60'))  # seconds between commits (reduced for chat)
_last_git_commit = 0
_git_pull_done = False  # Track if initial pull was done

# Delay before first Telegram connect (helps избежать пересечения старого и нового инстанса при деплое)
FETCH_START_DELAY = int(os.getenv('FETCH_START_DELAY', '0'))  # seconds

def git_pull_on_startup():
    """Pull latest data from GitHub on startup to restore chat messages."""
    global _git_pull_done
    if _git_pull_done:
        return
    if not GIT_AUTO_COMMIT or not GIT_REPO_SLUG or not GIT_SYNC_TOKEN:
        log.info("Git sync not configured, skipping pull on startup")
        return
    if not os.path.isdir('.git'):
        log.warning("Not a git repo, skipping pull")
        return
    try:
        def run(cmd):
            return subprocess.run(cmd, shell=True, capture_output=True, text=True)

        run('git config user.email "bot@local"')
        run('git config user.name "Auto Sync Bot"')

        safe_remote = f'https://x-access-token:{GIT_SYNC_TOKEN}@github.com/{GIT_REPO_SLUG}.git'
        remotes = run('git remote -v').stdout
        if 'origin' not in remotes or GIT_REPO_SLUG not in remotes:
            run('git remote remove origin')
            run(f'git remote add origin "{safe_remote}"')

        # Stash any local changes, pull, then pop
        run('git stash')
        pull_result = run('git pull origin main --rebase')
        run('git stash pop')

        if pull_result.returncode == 0:
            log.info("Git pull on startup successful - chat messages restored")
            # Copy pulled files to persistent storage if using /data directory
            _copy_git_files_to_persistent_storage()
        else:
            log.warning(f"Git pull failed: {pull_result.stderr}")

        _git_pull_done = True
    except Exception as e:
        log.error(f"Git pull on startup error: {e}")


def _copy_git_files_to_persistent_storage():
    """Copy files from git repo to persistent storage directory after pull."""
    import shutil
    persistent_dir = os.getenv('PERSISTENT_DATA_DIR', '/data')
    if not os.path.isdir(persistent_dir):
        log.info(f"No persistent storage at {persistent_dir}, skipping copy")
        return

    # Files to copy from repo root to persistent storage
    files_to_copy = ['chat_messages.json', 'messages.json', 'devices.json']

    for filename in files_to_copy:
        src = filename  # In repo root
        dst = os.path.join(persistent_dir, filename)

        if os.path.exists(src):
            try:
                # Only copy if source is newer or destination doesn't exist
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    log.info(f"Copied {src} to {dst}")
                else:
                    # Compare file sizes - copy if source has more data
                    src_size = os.path.getsize(src)
                    dst_size = os.path.getsize(dst)
                    if src_size > dst_size:
                        shutil.copy2(src, dst)
                        log.info(f"Updated {dst} from git (src={src_size}b, dst={dst_size}b)")
                    else:
                        log.info(f"Keeping existing {dst} (src={src_size}b, dst={dst_size}b)")
            except Exception as e:
                log.error(f"Error copying {src} to {dst}: {e}")

def maybe_git_autocommit():
    """If enabled, commit & push updated messages.json back to GitHub.
    Requirements:
      - Set GIT_AUTO_COMMIT=1
      - Provide GIT_REPO_SLUG (owner/repo)
      - Provide GIT_SYNC_TOKEN (PAT with repo write)
    The container build must include git (Render base images do).
    Commits throttled by GIT_COMMIT_INTERVAL seconds.
    """
    global _last_git_commit
    if not GIT_AUTO_COMMIT or not GIT_REPO_SLUG or not GIT_SYNC_TOKEN:
        return
    now = time.time()
    if now - _last_git_commit < GIT_COMMIT_INTERVAL:
        return
    if not os.path.isdir('.git'):
        raise RuntimeError('Not a git repo')

    # Copy files from persistent storage to repo root before committing
    _copy_persistent_files_to_git_repo()

    # Configure user (once)
    def run(cmd):
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)
    run('git config user.email "bot@local"')
    run('git config user.name "Auto Sync Bot"')
    # Set remote URL embedding token (avoid logging token!)
    safe_remote = f'https://x-access-token:{GIT_SYNC_TOKEN}@github.com/{GIT_REPO_SLUG}.git'
    # Do not print safe_remote (contains secret)
    # Update origin only if needed
    remotes = run('git remote -v').stdout
    if 'origin' not in remotes or GIT_REPO_SLUG not in remotes:
        run('git remote remove origin')
        run(f'git remote add origin "{safe_remote}"')
    # Stage & commit if there is a change (use repo root filenames, not /data paths)
    run('git add messages.json')
    run('git add chat_messages.json')
    run('git add devices.json')
    status = run('git status --porcelain').stdout
    if 'messages.json' not in status and 'chat_messages.json' not in status and 'devices.json' not in status:
        return  # no actual diff
    commit_msg = 'Update messages (auto)'  # no secrets
    run(f'git commit -m "{commit_msg}"')
    push_res = run('git push origin HEAD:main')
    if push_res.returncode == 0:
        _last_git_commit = now
        log.info("Git autocommit successful")
    else:
        # If push fails (e.g., diverged), attempt pull+rebase then push
        run('git fetch origin')
        run('git rebase origin/main || git rebase --abort')
        push_res2 = run('git push origin HEAD:main')
        if push_res2.returncode == 0:
            _last_git_commit = now
        # else: give up silently to avoid spamming logs


def _copy_persistent_files_to_git_repo():
    """Copy files from persistent storage to repo root for git commit."""
    import shutil
    persistent_dir = os.getenv('PERSISTENT_DATA_DIR', '/data')
    if not os.path.isdir(persistent_dir):
        return  # Not using persistent storage

    files_to_copy = ['chat_messages.json', 'messages.json', 'devices.json']

    for filename in files_to_copy:
        src = os.path.join(persistent_dir, filename)
        dst = filename  # Repo root

        if os.path.exists(src):
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                log.error(f"Error copying {src} to {dst} for git: {e}")

# NOTE: _load_settlements() defined and called earlier in the file

"""(Removed duplicate legacy process_message; canonical version defined earlier.)"""

# ----------------------- Deferred initialization hooks -----------------------
# CPU OPTIMIZATION: Use before_first_request pattern manually
_INIT_BACKGROUND_DONE = False

def _memory_cleanup_worker():
    """Background worker to periodically clean up caches and prevent memory leaks."""
    while True:
        try:
            time.sleep(300)  # Run every 5 minutes
            
            # Clean request_counts
            _cleanup_request_counts()
            
            # Clean ResponseCache expired entries
            cleaned = RESPONSE_CACHE.clear_expired()
            if cleaned > 0:
                print(f"[MEMORY] Cleaned {cleaned} expired cache entries")
            
            # Clean _groq_cache - remove old entries and enforce size limit
            now = time.time()
            if _groq_cache:
                old_size = len(_groq_cache)
                # Remove expired entries
                expired_keys = [k for k, (_, ts) in _groq_cache.items() if now - ts > _groq_cache_ttl]
                for k in expired_keys:
                    del _groq_cache[k]
                # If still over limit, remove oldest entries
                if len(_groq_cache) > _groq_cache_max_size:
                    sorted_keys = sorted(_groq_cache.keys(), key=lambda k: _groq_cache[k][1])
                    for k in sorted_keys[:len(_groq_cache) - _groq_cache_max_size // 2]:
                        del _groq_cache[k]
                if old_size != len(_groq_cache):
                    print(f"[MEMORY] Cleaned groq cache: {old_size} -> {len(_groq_cache)}")
            
            # Clean _telegram_alert_sent (keep only last 5 min)
            now = time.time()
            with _telegram_alert_lock:
                old_size = len(_telegram_alert_sent)
                keys_to_del = [k for k, v in _telegram_alert_sent.items() if now - v > 300]
                for k in keys_to_del:
                    del _telegram_alert_sent[k]
                if keys_to_del:
                    print(f"[MEMORY] Cleaned {len(keys_to_del)} old telegram alerts")
            
            # Clean _telegram_region_notified (keep only last 10 min)
            old_size = len(_telegram_region_notified)
            keys_to_del = [k for k, v in _telegram_region_notified.items() if now - v > 600]
            for k in keys_to_del:
                del _telegram_region_notified[k]
            if keys_to_del:
                print(f"[MEMORY] Cleaned {len(keys_to_del)} old region notifications")
                
            # Clean ACTIVE_VISITORS (remove stale visitors)
            with ACTIVE_LOCK:
                old_size = len(ACTIVE_VISITORS)
                stale_keys = [k for k, v in ACTIVE_VISITORS.items() if now - v.get('ts', 0) > ACTIVE_TTL * 2]
                for k in stale_keys:
                    del ACTIVE_VISITORS[k]
                if stale_keys:
                    print(f"[MEMORY] Cleaned {len(stale_keys)} stale visitors")
            
            # Clean _mapstransler_geocode_cache if over limit
            if len(_mapstransler_geocode_cache) > _mapstransler_cache_max_size:
                old_size = len(_mapstransler_geocode_cache)
                # Remove half of the entries (oldest would require tracking timestamps)
                keys_to_remove = list(_mapstransler_geocode_cache.keys())[:old_size // 2]
                for k in keys_to_remove:
                    del _mapstransler_geocode_cache[k]
                print(f"[MEMORY] Cleaned mapstransler cache: {old_size} -> {len(_mapstransler_geocode_cache)}")
            
            # Force garbage collection periodically
            import gc
            gc.collect()
                    
        except Exception as e:
            print(f"[MEMORY] Cleanup worker error: {e}")

def _init_background():
    global _INIT_BACKGROUND_DONE, INIT_ONCE
    if _INIT_BACKGROUND_DONE:
        return
    _INIT_BACKGROUND_DONE = True
    INIT_ONCE = True
    _startup_diagnostics()
    # Start background workers
    try:
        start_fetch_thread()
    except Exception as e:
        log.error(f'Failed to start fetch thread: {e}\n{traceback.format_exc()}')
    try:
        start_session_watcher()
    except Exception as e:
        log.error(f'Failed to start session watcher: {e}\n{traceback.format_exc()}')
    # MEMORY PROTECTION: Start memory cleanup worker
    try:
        threading.Thread(target=_memory_cleanup_worker, daemon=True, name='memory_cleanup').start()
        print("INFO: Memory cleanup worker started")
    except Exception as e:
        log.error(f'Failed to start memory cleanup worker: {e}')
@app.before_request
def _maybe_init_background():
    # CPU OPTIMIZATION: Skip quickly if already initialized
    if _INIT_BACKGROUND_DONE:
        return
    _init_background()

@app.route('/startup_diag')
def startup_diag():
    """Expose current diagnostic snapshot (no secrets)."""
    try:
        info = {
            'pid': os.getpid(),
            'python': sys.version.split()[0],
            'platform': platform.platform(),
            'channels': CHANNELS,
            'authorized': AUTH_STATUS,
            'messages_file_exists': os.path.exists(MESSAGES_FILE),
            'messages_count': len(load_messages()),
            'fetch_thread_started': FETCH_THREAD_STARTED,
            'session_present': bool(session_str),
            'retention_minutes': MESSAGES_RETENTION_MINUTES,
            'retention_max_count': MESSAGES_MAX_COUNT,
            'subscribers': len(SUBSCRIBERS),
            'cache_stats': RESPONSE_CACHE.stats(),  # HIGH-LOAD: Cache statistics
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache-stats')
def cache_stats():
    """Get response cache statistics for monitoring."""
    stats = RESPONSE_CACHE.stats()
    # Also clean expired entries
    cleaned = RESPONSE_CACHE.clear_expired()
    stats['expired_cleaned'] = cleaned
    return jsonify(stats)


@app.route('/healthz')
def healthz():
    """Lightweight health endpoint for uptime monitors."""
    try:
        messages = load_messages()
        file_exists = os.path.exists(MESSAGES_FILE)
        latest_date = None
        for m in messages:
            candidate = m.get('date')
            if candidate and (latest_date is None or candidate > latest_date):
                latest_date = candidate
        payload = {
            'status': 'ok',
            'messages_count': len(messages),
            'manual_count': sum(1 for m in messages if m.get('manual')),
            'messages_file_size': os.path.getsize(MESSAGES_FILE) if file_exists else 0,
            'messages_file_present': file_exists,
            'latest_message_at': latest_date,
            'fetch_thread_started': FETCH_THREAD_STARTED,
            'backfill': BACKFILL_STATUS.copy(),
            'retention': {
                'minutes': MESSAGES_RETENTION_MINUTES,
                'max_count': MESSAGES_MAX_COUNT,
            },
        }
        return jsonify(payload)
    except Exception as exc:
        return jsonify({'status': 'error', 'error': str(exc)}), 500

@app.route('/admin/test-nominatim')
def test_nominatim():
    """Test if Nominatim is reachable from this server."""

    # Safely get settlements count
    try:
        all_settlements_count = len(UKRAINE_ALL_SETTLEMENTS) if UKRAINE_ALL_SETTLEMENTS else 0
    except:
        all_settlements_count = 0
    try:
        oblast_settlements_count = len(UKRAINE_SETTLEMENTS_BY_OBLAST) if UKRAINE_SETTLEMENTS_BY_OBLAST else 0
    except:
        oblast_settlements_count = 0

    results = {
        'nominatim': {'status': 'unknown', 'time_ms': 0, 'error': None},
        'settlements_db': {
            'all_loaded': all_settlements_count,
            'oblast_aware_loaded': oblast_settlements_count,
        },
        'memory_optimized': os.environ.get('MEMORY_OPTIMIZED', 'false'),
    }

    # Test Nominatim
    try:
        start = time_module.time()
        nominatim_url = 'https://nominatim.openstreetmap.org/search'
        params = {'q': 'Kyiv, Ukraine', 'format': 'json', 'limit': 1}
        headers = {'User-Agent': 'neptun.in.ua/1.0'}
        response = requests.get(nominatim_url, params=params, headers=headers, timeout=5)
        elapsed = (time_module.time() - start) * 1000

        results['nominatim']['time_ms'] = round(elapsed, 1)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                results['nominatim']['status'] = 'ok'
                results['nominatim']['result'] = data[0].get('display_name', '')[:50]
            else:
                results['nominatim']['status'] = 'empty_response'
        else:
            results['nominatim']['status'] = f'http_{response.status_code}'
    except requests.exceptions.Timeout:
        results['nominatim']['status'] = 'timeout'
        results['nominatim']['error'] = 'Request timed out after 5s'
    except requests.exceptions.ConnectionError as e:
        results['nominatim']['status'] = 'connection_error'
        results['nominatim']['error'] = str(e)[:200]
    except Exception as e:
        results['nominatim']['status'] = 'error'
        results['nominatim']['error'] = str(e)[:200]

    return jsonify(results)

# Manual trigger (idempotent) if needed before first page hit
@app.route('/startup_init', methods=['POST'])
def startup_init():
    _init_background()
    return jsonify({'status': 'ok'})

# BANDWIDTH PROTECTION: Custom static route will compete with Flask's built-in route
# Flask will prioritize our custom route due to specificity


# Force reload endpoints for admin
@app.route('/api/force-reload-status')
def force_reload_status():
    """Check if force reload flag is active"""
    global FORCE_RELOAD_TIMESTAMP
    with FORCE_RELOAD_LOCK:
        current_time = time.time()
        # Check if force reload is still active (within duration window)
        should_reload = (FORCE_RELOAD_TIMESTAMP > 0 and
                        (current_time - FORCE_RELOAD_TIMESTAMP) < FORCE_RELOAD_DURATION)
    return jsonify({'reload': should_reload})

@app.route('/admin/trigger-force-reload', methods=['POST'])
def trigger_force_reload():
    """Admin endpoint to trigger force reload for all users"""
    if not _require_secret(request):
        return Response('Forbidden', status=403)

    global FORCE_RELOAD_TIMESTAMP
    with FORCE_RELOAD_LOCK:
        FORCE_RELOAD_TIMESTAMP = time.time()

    log.info(f"🔄 ADMIN: Force reload triggered for all users (active for {FORCE_RELOAD_DURATION} seconds)")
    return jsonify({'success': True, 'message': f'Force reload activated for {FORCE_RELOAD_DURATION} seconds'})


# ========== Firebase Cloud Messaging Endpoints ==========

@app.route('/api/register-device', methods=['POST'])
def register_device():
    """Register a device for push notifications."""
    try:
        data = request.get_json()
        token = data.get('token')
        regions = data.get('regions', [])
        oblast_ids = data.get('oblast_ids', [])
        raion_ids = data.get('raion_ids', [])
        device_id = data.get('device_id', token)
        enabled = data.get('enabled', True)  # Support disabling notifications
        platform = data.get('platform', 'unknown')  # iOS/Android

        if not token and not device_id:
            return jsonify({'error': 'Missing token or device_id'}), 400

        # Log registration with platform info
        log.info(
            f"📱 Device registration: platform={platform}, device_id={device_id[:20]}..., regions={regions[:3]}..., oblast_ids={oblast_ids[:3]}..., raion_ids={raion_ids[:3]}..."
        )
        print(
            f"[REGISTER] platform={platform}, token_prefix={token[:30] if token else 'None'}..., regions={regions}, oblast_ids={oblast_ids}, raion_ids={raion_ids}",
            flush=True,
        )

        # If notifications disabled or no regions, remove device
        if not enabled or not regions:
            device_store.remove_device(device_id)
            log.info(f"Device {device_id[:20]}... unregistered (notifications disabled)")
            return jsonify({'success': True, 'device_id': device_id, 'status': 'unregistered'})

        # Derive IDs on server if client didn't send them
        if not oblast_ids or not raion_ids:
            derived_oblasts, derived_raions = _derive_region_ids_from_regions(regions)
            if not oblast_ids and derived_oblasts:
                oblast_ids = derived_oblasts
            if not raion_ids and derived_raions:
                raion_ids = derived_raions

        device_store.register_device(
            token,
            regions,
            device_id,
            oblast_ids=oblast_ids,
            raion_ids=raion_ids,
        )
        return jsonify({'success': True, 'device_id': device_id, 'platform': platform})
    except Exception as e:
        log.error(f"Error registering device: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/update-regions', methods=['POST'])
def update_regions():
    """Update regions for an existing device."""
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        regions = data.get('regions', [])
        oblast_ids = data.get('oblast_ids', [])
        raion_ids = data.get('raion_ids', [])

        if not device_id or not regions:
            return jsonify({'error': 'Missing device_id or regions'}), 400

        if not oblast_ids or not raion_ids:
            derived_oblasts, derived_raions = _derive_region_ids_from_regions(regions)
            if not oblast_ids and derived_oblasts:
                oblast_ids = derived_oblasts
            if not raion_ids and derived_raions:
                raion_ids = derived_raions

        device_store.update_regions(device_id, regions, oblast_ids=oblast_ids, raion_ids=raion_ids)
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error updating regions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/registered-devices', methods=['GET'])
def get_registered_devices():
    """Get all registered devices (for debugging)."""
    try:
        devices = device_store._load()
        # Mask tokens for security (show only last 10 chars) but show length
        for _device_id, data in devices.items():
            if 'token' in data:
                token = data['token']
                data['token_length'] = len(token)
                data['token'] = '...' + token[-10:] if len(token) > 10 else token
        return jsonify({
            'count': len(devices),
            'devices': devices
        })
    except Exception as e:
        log.error(f"Error getting devices: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-push/<token>', methods=['POST'])
def test_push_to_token(token):
    """Send a test push notification directly to a specific FCM token (for debugging)."""
    if not firebase_initialized:
        return jsonify({'error': 'Firebase not initialized'}), 500
    
    try:
        from firebase_admin import messaging
        
        title = request.json.get('title', '🧪 Test Push') if request.is_json else '🧪 Test Push'
        body = request.json.get('body', 'Тестове сповіщення для перевірки push') if request.is_json else 'Тестове сповіщення для перевірки push'
        
        message = messaging.Message(
            data={
                'type': 'test',
                'title': title,
                'body': body,
                'timestamp': datetime.now(pytz.timezone('Europe/Kiev')).isoformat(),
            },
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    icon='ic_notification',
                    channel_id='critical_alerts',
                ),
            ),
            apns=messaging.APNSConfig(
                headers={
                    'apns-priority': '10',
                    'apns-push-type': 'alert',
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(title=title, body=body),
                        sound='default',
                        badge=1,
                    ),
                ),
            ),
            token=token,
        )
        
        response = messaging.send(message)
        log.info(f"✅ Test push sent to token {token[:20]}...: {response}")
        return jsonify({'success': True, 'response': response})
    except Exception as e:
        log.error(f"❌ Test push failed: {e}")
        return jsonify({'error': str(e)}), 500


# ============ FEEDBACK / BUG REPORTS ============
# Ensure we use persistent storage for feedback
if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR):
    FEEDBACK_FILE = os.path.join(PERSISTENT_DATA_DIR, 'feedback.json')
    log.info(f'Feedback will be saved to persistent storage: {FEEDBACK_FILE}')
else:
    FEEDBACK_FILE = 'feedback.json'
    log.warning(f'Feedback will be saved locally (not persistent): {FEEDBACK_FILE}')

def load_feedback():
    """Load feedback messages."""
    try:
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, encoding='utf-8') as f:
                data = json.load(f)
                log.info(f"Loaded {len(data)} feedback items from {FEEDBACK_FILE}")
                return data
    except Exception as e:
        log.error(f"Error loading feedback: {e}")
    return []

def save_feedback(feedback_list):
    """Save feedback messages."""
    try:
        # Ensure directory exists
        feedback_dir = os.path.dirname(FEEDBACK_FILE)
        if feedback_dir and not os.path.exists(feedback_dir):
            os.makedirs(feedback_dir, exist_ok=True)

        with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(feedback_list, f, ensure_ascii=False, indent=2)
        log.info(f"Saved {len(feedback_list)} feedback items to {FEEDBACK_FILE}")
    except Exception as e:
        log.error(f"Error saving feedback: {e}")

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback or bug report."""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        feedback_type = data.get('type', 'bug')  # 'bug', 'suggestion', 'other'
        device_id = data.get('device_id', '')
        device = data.get('device', '')  # iOS, Android, etc
        app_version = data.get('app_version', '')
        regions = data.get('regions', [])  # User's selected regions

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        if len(message) > 5000:
            message = message[:5000]

        # Create feedback entry
        kyiv_tz = pytz.timezone('Europe/Kiev')
        now = datetime.now(kyiv_tz)

        feedback_entry = {
            'id': str(uuid.uuid4()),
            'type': feedback_type,
            'message': message,
            'device': device,
            'device_id': device_id[:50] if device_id else '',
            'app_version': app_version,
            'regions': regions[:10] if isinstance(regions, list) else [],  # Max 10 regions
            'timestamp': now.timestamp(),
            'date': now.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'new'
        }

        # Load, append, save
        feedback_list = load_feedback()
        feedback_list.append(feedback_entry)
        # Keep only last 500 entries
        if len(feedback_list) > 500:
            feedback_list = feedback_list[-500:]
        save_feedback(feedback_list)

        log.info(f"📩 New feedback received: {feedback_type} - {message[:50]}...")

        return jsonify({
            'success': True,
            'message': 'Дякуємо за ваш відгук!'
        })
    except Exception as e:
        log.error(f"Error submitting feedback: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['GET'])
def get_feedback():
    """Get all feedback (for admin) with nice HTML interface."""
    try:
        # Simple auth check
        auth_key = request.args.get('key', '')
        if auth_key != os.getenv('ADMIN_KEY', 'neptun_admin_2024'):
            return jsonify({'error': 'Unauthorized'}), 401

        feedback_list = load_feedback()

        # Check if JSON format requested
        if request.args.get('format') == 'json':
            return jsonify({
                'success': True,
                'feedback': feedback_list,
                'count': len(feedback_list)
            })

        # Sort by date (newest first)
        feedback_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Generate HTML
        html = '''<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEPTUN - Зворотній зв'язок</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e0e0e0;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            padding: 30px 0;
            margin-bottom: 30px;
        }

        h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }

        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 20px 40px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
            color: #00d4ff;
        }

        .stat-label {
            font-size: 0.9rem;
            color: #888;
            margin-top: 5px;
        }

        .feedback-list {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .feedback-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .feedback-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(0, 212, 255, 0.1);
            border-color: rgba(0, 212, 255, 0.3);
        }

        .feedback-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }

        .feedback-meta {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }

        .feedback-device {
            font-size: 0.85rem;
            color: #888;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .feedback-device .icon {
            font-size: 1.1rem;
        }

        .feedback-time {
            font-size: 0.8rem;
            color: #666;
            background: rgba(255, 255, 255, 0.05);
            padding: 5px 12px;
            border-radius: 20px;
        }

        .feedback-text {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            padding: 20px;
            font-size: 1rem;
            line-height: 1.6;
            color: #f0f0f0;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .feedback-regions {
            margin-top: 15px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .region-tag {
            background: linear-gradient(135deg, #7b2ff7 0%, #f107a3 100%);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }

        .empty-state .icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }

        .refresh-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: linear-gradient(135deg, #00d4ff 0%, #7b2ff7 100%);
            color: white;
            border: none;
            padding: 15px 25px;
            border-radius: 30px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .refresh-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 30px rgba(0, 212, 255, 0.4);
        }

        @media (max-width: 600px) {
            h1 { font-size: 1.8rem; }
            .stats { flex-direction: column; gap: 15px; }
            .stat-card { padding: 15px 30px; }
            .feedback-header { flex-direction: column; gap: 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌊 NEPTUN Feedback</h1>
            <p style="color: #888;">Адмін-панель зворотнього зв'язку</p>
            <p style="color: #555; font-size: 0.8rem; margin-top: 5px;">💾 ''' + ('Persistent: ' + FEEDBACK_FILE if '/data' in FEEDBACK_FILE else '⚠️ Local: ' + FEEDBACK_FILE) + '''</p>
        </header>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">''' + str(len(feedback_list)) + '''</div>
                <div class="stat-label">Всього повідомлень</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">''' + str(len([f for f in feedback_list if str(f.get('timestamp', ''))[:10] == datetime.now().strftime('%Y-%m-%d')])) + '''</div>
                <div class="stat-label">Сьогодні</div>
            </div>
        </div>

        <div class="feedback-list">'''

        if not feedback_list:
            html += '''
            <div class="empty-state">
                <div class="icon">📭</div>
                <h3>Поки немає повідомлень</h3>
                <p>Користувачі ще не надіслали зворотній зв'язок</p>
            </div>'''
        else:
            for fb in feedback_list:
                # Get device info
                device = fb.get('device', '') or fb.get('device_id', '') or 'Невідомий пристрій'
                app_version = fb.get('app_version', '')
                feedback_type = fb.get('type', 'bug')

                # Determine device icon
                if 'iphone' in device.lower() or 'ios' in device.lower():
                    device_icon = '📱'
                elif 'android' in device.lower():
                    device_icon = '🤖'
                else:
                    device_icon = '💻'

                # Type badge
                type_badge = {'bug': '🐛 Баг', 'suggestion': '💡 Ідея', 'other': '📝 Інше'}.get(feedback_type, '📝')

                # Format timestamp
                ts = fb.get('timestamp', '')
                try:
                    if isinstance(ts, (int, float)):
                        # Unix timestamp
                        dt = datetime.fromtimestamp(ts)
                        formatted_time = dt.strftime('%d.%m.%Y %H:%M')
                    elif isinstance(ts, str) and ts:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%d.%m.%Y %H:%M')
                    else:
                        formatted_time = fb.get('date', 'Невідомо')
                except:
                    formatted_time = fb.get('date', str(ts)[:16] if ts else 'Невідомо')

                # Escape HTML in text - use 'message' field!
                text = fb.get('message', '') or fb.get('text', '')
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                device_display = f"{device}" + (f" (v{app_version})" if app_version else "")
                device_escaped = device_display.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

                # Get regions
                regions = fb.get('regions', [])

                html += f'''
            <div class="feedback-card">
                <div class="feedback-header">
                    <div class="feedback-meta">
                        <div class="feedback-device">
                            <span class="icon">{device_icon}</span>
                            <span>{device_escaped}</span>
                            <span style="margin-left: 10px; background: rgba(255,255,255,0.1); padding: 3px 8px; border-radius: 10px; font-size: 0.75rem;">{type_badge}</span>
                        </div>
                    </div>
                    <div class="feedback-time">🕐 {formatted_time}</div>
                </div>
                <div class="feedback-text">{text if text else "<i style='color:#666'>Порожнє повідомлення</i>"}</div>'''

                if regions:
                    html += '''
                <div class="feedback-regions">'''
                    for region in regions[:5]:  # Show max 5 regions
                        region_escaped = region.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        html += f'''
                    <span class="region-tag">📍 {region_escaped}</span>'''
                    if len(regions) > 5:
                        html += f'''
                    <span class="region-tag">+{len(regions) - 5} ще</span>'''
                    html += '''
                </div>'''

                html += '''
            </div>'''

        html += '''
        </div>
    </div>

    <button class="refresh-btn" onclick="location.reload()">🔄 Оновити</button>
</body>
</html>'''

        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-notification', methods=['POST'])
def test_notification():
    """Send a test notification to a device."""
    if not firebase_initialized:
        return jsonify({'error': 'Firebase not initialized'}), 500

    try:
        from firebase_admin import messaging

        data = request.get_json()
        token = data.get('token')
        device_id = data.get('device_id')
        title = data.get('title', '🧪 Тестове сповіщення')
        body = data.get('body', 'NEPTUN працює коректно!')
        region = data.get('region', 'Тест')

        # If device_id provided, look up the token
        if not token and device_id:
            devices = device_store._load()
            device_data = devices.get(device_id)
            if device_data:
                token = device_data.get('token')

        if not token:
            return jsonify({'error': 'Missing token or device_id'}), 400

        # For Android: DATA-ONLY message (no notification) so background handler processes TTS
        message = messaging.Message(
            # NO notification block for Android - only data!
            data={
                'type': 'alarm',
                'title': title,
                'body': body,
                'region': region,
                'alarm_state': 'active',
                'is_critical': 'true',
                'timestamp': datetime.now(pytz.UTC).isoformat(),
            },
            android=messaging.AndroidConfig(
                priority='high',
            ),
            token=token,
        )

        response = messaging.send(message)
        log.info(f"Test notification sent successfully: {response}")
        return jsonify({'success': True, 'message_id': response})
        return jsonify({'success': True, 'message_id': response})
    except messaging.UnregisteredError:
        # Token is invalid - remove device from store
        log.warning("Token is invalid (UnregisteredError), removing device...")
        device_store.remove_device(token)
        return jsonify({'error': 'NotRegistered', 'message': 'Token is invalid and was removed. Please re-register the device.'}), 410
    except Exception as e:
        error_msg = str(e)
        if 'NotRegistered' in error_msg or 'not registered' in error_msg.lower():
            log.warning("Token not registered, removing device...")
            device_store.remove_device(token)
            return jsonify({'error': 'NotRegistered', 'message': 'Token is invalid and was removed. Please re-register the device.'}), 410
        log.error(f"Error sending test notification: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-ios-push', methods=['POST'])
def test_ios_push():
    """Send a test push notification to iOS device with full APNs config."""
    if not firebase_initialized:
        return jsonify({'error': 'Firebase not initialized'}), 500

    try:
        from firebase_admin import messaging

        data = request.get_json() or {}
        token = data.get('token')

        if not token:
            return jsonify({'error': 'Missing token parameter'}), 400

        log.info(f"=== TEST iOS PUSH to token: {token[:50]}... ===")

        # Full iOS push with APNs config (like telegram_threat)
        message = messaging.Message(
            data={
                'type': 'telegram_threat',
                'title': '🧪 ТЕСТ iOS Push',
                'body': 'Якщо ви бачите це - APNs працює!',
                'location': 'Тест',
                'region': 'Тест',
                'alarm_state': 'active',
                'is_critical': 'true',
                'threat_type': 'Тестове сповіщення',
                'timestamp': datetime.now(pytz.timezone('Europe/Kiev')).isoformat(),
            },
            apns=messaging.APNSConfig(
                headers={
                    'apns-priority': '10',
                    'apns-push-type': 'alert',
                    'apns-expiration': '0',
                },
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title='🧪 ТЕСТ iOS Push',
                            body='Якщо ви бачите це - APNs працює!'
                        ),
                        sound='default',
                        badge=1,
                        content_available=True,
                        mutable_content=True,
                    ),
                ),
            ),
            token=token,
        )

        response = messaging.send(message)
        log.info(f"✅ Test iOS push sent: {response}")
        return jsonify({'success': True, 'message_id': response})

    except messaging.UnregisteredError as e:
        log.error(f"Token unregistered: {e}")
        return jsonify({'error': 'Token unregistered - device needs to re-register'}), 410
    except Exception as e:
        log.error(f"Error sending iOS test push: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-telegram-threat', methods=['POST'])
def test_telegram_threat():
    """Send a test telegram_threat notification to all_regions topic AND specific token."""
    if not firebase_initialized:
        return jsonify({'error': 'Firebase not initialized'}), 500

    try:
        from firebase_admin import messaging

        data = request.get_json() or {}
        token = data.get('token')  # Optional: send to specific device
        region = data.get('region', 'Київська область')
        threat_type = data.get('threat_type', 'Тестова загроза')

        title = f"🧪 ТЕСТ: {region}"
        body = f"Тестове telegram_threat повідомлення - {threat_type}"

        timestamp = datetime.now(pytz.timezone('Europe/Kiev')).isoformat()

        # Build APNs config
        apns_config = messaging.APNSConfig(
            headers={
                'apns-priority': '10',
                'apns-push-type': 'alert',
                'apns-expiration': '0',
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
        )

        android_config = messaging.AndroidConfig(
            priority='high',
            ttl=timedelta(seconds=300),
        )

        fcm_data = {
            'type': 'telegram_threat',
            'title': title,
            'body': body,
            'location': region,
            'region': region,
            'alarm_state': 'active',
            'is_critical': 'false',
            'threat_type': threat_type,
            'timestamp': timestamp,
            'click_action': 'FLUTTER_NOTIFICATION_CLICK',
        }

        results = []

        # 1. Send to all_regions topic
        try:
            topic_message = messaging.Message(
                data=fcm_data,
                android=android_config,
                apns=apns_config,
                topic='all_regions',
            )
            response = messaging.send(topic_message)
            results.append({'target': 'topic:all_regions', 'success': True, 'response': response})
            log.info(f"✅ Test telegram_threat sent to all_regions: {response}")
        except Exception as e:
            results.append({'target': 'topic:all_regions', 'success': False, 'error': str(e)})
            log.error(f"❌ Failed to send to all_regions: {e}")

        # 2. If token provided, also send directly to device
        if token:
            try:
                token_message = messaging.Message(
                    data=fcm_data,
                    android=android_config,
                    apns=apns_config,
                    token=token,
                )
                response = messaging.send(token_message)
                results.append({'target': f'token:{token[:20]}...', 'success': True, 'response': response})
                log.info(f"✅ Test telegram_threat sent to token: {response}")
            except Exception as e:
                results.append({'target': f'token:{token[:20]}...', 'success': False, 'error': str(e)})
                log.error(f"❌ Failed to send to token: {e}")

        return jsonify({'success': True, 'results': results})

    except Exception as e:
        log.error(f"Error in test_telegram_threat: {e}")
        return jsonify({'error': str(e)}), 500


def send_fcm_notification(message_data: dict):
    """Send FCM notification for a new threat message."""
    if not firebase_initialized:
        log.warning("Firebase not initialized, skipping notifications")
        return

    try:
        import re

        from firebase_admin import messaging

        # Check if this is a real threat (not just informational message)
        threat_type = message_data.get('threat_type', '') or message_data.get('type', '') or ''
        text = message_data.get('text', '') or ''
        text_lower = text.lower()

        # Check if this is an "all clear" message (відбій)
        is_all_clear = any(kw in text_lower for kw in ['відбій', 'скасовано', 'завершено'])

        # Skip only truly informational messages (not відбій - we want to notify about all clear too)
        skip_keywords = ['немає загрози', 'безпечно', 'інформація', 'увага!', 'попередження']
        if any(kw in text_lower for kw in skip_keywords):
            log.info(f"Skipping FCM for informational message: {text[:50]}...")
            return

        # Skip if no threat type detected AND not an all clear message
        if not threat_type and not is_all_clear:
            log.info("Skipping FCM for message without threat type")
            return

        # Use 'place' field for location (it's the geocoded place name)
        location = message_data.get('place', '') or message_data.get('location', '') or ''

        # CRITICAL: Extract specific city from place or text if format is "City (Oblast обл.)"
        # Example: "Овруч (Житомирська обл.)" -> city = "Овруч"
        city_from_text = ''
        
        # First try to extract from place field (more reliable)
        if location and '(' in location:
            city_from_place = location.split('(')[0].strip()
            if city_from_place:
                city_from_text = city_from_place
                log.info(f"Extracted city from place: '{city_from_text}' (full place: {location})")
        
        # Fallback: try to extract from text
        if not city_from_text and text:
            # Pattern: "City (Oblast обл.)" - extract city before parentheses
            city_oblast_match = re.search(r'^[^а-яіїєґА-ЯІЇЄҐ]*([А-ЯІЇЄҐа-яіїєґ][а-яіїєґА-ЯІЇЄҐ\'\-\s]+?)\s*\([^)]*обл[^)]*\)', text)
            if city_oblast_match:
                city_from_text = city_oblast_match.group(1).strip()
                # Clean up emoji and special chars at the beginning
                city_from_text = re.sub(r'^[^\w\s]+\s*', '', city_from_text).strip()
                log.info(f"Extracted city from text: '{city_from_text}' (full text: {text[:80]})")

        # Use extracted city if available and long enough (>= 5 chars), otherwise fall back to place/region
        # This prevents "Кам" instead of "Каменське"
        if city_from_text and len(city_from_text) >= 5:
            specific_location = city_from_text
        elif location and len(location) >= 3:
            specific_location = location
        else:
            specific_location = ''

        if not specific_location and not location:
            log.info("Skipping FCM for message without place")
            return

        log.info("=== FCM NOTIFICATION TRIGGERED ===")
        log.info(f"Place (original): {location}")
        log.info(f"City (extracted): {city_from_text}")
        log.info(f"Location for TTS (min 5 chars): {specific_location}")
        log.info(f"Threat type: {threat_type}")

        # Find matching region - search in place field AND in text for oblast pattern
        # to handle "Овруч (Житомирська обл.)" format
        region = None
        place_lower = location.lower()
        text_for_region = text.lower() if text else ''

        # First try to extract region from text with "(Oblast обл.)" pattern
        oblast_in_text = re.search(r'\(([а-яіїєґ]+ська)\s+обл\.?\)', text_for_region)
        if oblast_in_text:
            oblast_adj = oblast_in_text.group(1)  # e.g., "житомирська"
            log.info(f"Found oblast in text: {oblast_adj}")

        # Region mapping - keywords to match ONLY in place name
        regions_map = {
            'Київ': ['київ', 'києв'],
            'Київська область': ['київська обл', 'київська', 'київщин', 'бориспіль', 'бровар', 'ірпін', 'буча', 'вишгород', 'фастів', 'біла церква'],
            'Дніпропетровська область': ['дніпропетровська', 'дніпропетровськ', 'дніпро', 'кривий ріг', 'кам\'янськ', 'нікополь', 'павлоград'],
            'Харківська область': ['харківська', 'харків', 'харьков', 'ізюм', 'куп\'янськ', 'чугуїв', 'лозова'],
            'Одеська область': ['одеська', 'одес', 'одещин', 'ізмаїл', 'білгород-дністровськ', 'чорноморськ'],
            'Львівська область': ['львівська', 'львів', 'львівщин', 'дрогобич', 'стрий', 'червоноград'],
            'Донецька область': ['донецька', 'донецьк', 'донеч', 'маріуполь', 'краматорськ', 'слов\'янськ', 'бахмут', 'покровськ'],
            'Запорізька область': ['запорізька', 'запоріж', 'мелітополь', 'бердянськ', 'енергодар'],
            'Вінницька область': ['вінницька', 'вінниц', 'жмеринка', 'козятин', 'хмільник'],
            'Житомирська область': ['житомирська', 'житомир', 'бердичів', 'коростень', 'новоград', 'овруч'],
            'Черкаська область': ['черкаська', 'черкас', 'умань', 'сміла', 'золотоноша'],
            'Чернігівська область': ['чернігівська', 'чернігів', 'чернігов', 'ніжин', 'прилуки', 'корюків'],
            'Чернівецька область': ['чернівецька', 'чернівці', 'чернівц', 'чернівеч', 'буковина', 'новодністровськ', 'вижниця', 'сторожинець'],
            'Полтавська область': ['полтавська', 'полтав', 'кременчук', 'миргород', 'лубни'],
            'Сумська область': ['сумська', 'сум', 'конотоп', 'шостка', 'ромни', 'охтирка'],
            'Миколаївська область': ['миколаївська', 'миколаїв', 'миколаєв', 'первомайськ', 'вознесенськ'],
            'Херсонська область': ['херсонська', 'херсон', 'нова каховка', 'каховка'],
            'Кіровоградська область': ['кіровоградська', 'кіровоград', 'кропивниц', 'олександрія', 'знам\'янка'],
            'Хмельницька область': ['хмельницька', 'хмельниц', 'кам\'янець-подільськ', 'шепетівка'],
            'Рівненська область': ['рівненська', 'рівн', 'рівне', 'дубно', 'костопіль', 'дубровиц'],
            'Волинська область': ['волинська', 'волин', 'луцьк', 'ковель', 'нововолинськ'],
            'Тернопільська область': ['тернопільська', 'тернопіль', 'чортків', 'кременець'],
            'Івано-Франківська область': ['івано-франківська', 'івано-франків', 'калуш', 'коломия', 'надвірна'],
            'Закарпатська область': ['закарпатська', 'закарпат', 'ужгород', 'мукачево', 'хуст', 'берегово'],
            'Луганська область': ['луганська', 'луганськ', 'луганщин', 'сєвєродонецьк', 'лисичанськ'],
        }

        # First search in text for oblast pattern (most reliable for "City (Oblast обл.)" format)
        # IMPORTANT: Search for LONGEST matching keyword first to avoid confusion
        # between similar names like "Чернівці" vs "Чернігів"
        best_match = None
        best_keyword_len = 0

        for region_name, keywords in regions_map.items():
            for keyword in keywords:
                if keyword in text_for_region:
                    # Prefer longer (more specific) matches
                    if len(keyword) > best_keyword_len:
                        best_match = region_name
                        best_keyword_len = len(keyword)
                        log.info(f"Found potential match: {region_name} (keyword: '{keyword}', len={len(keyword)})")

        if best_match:
            region = best_match
            log.info(f"Best match from text: {region} (keyword length: {best_keyword_len})")

        # Fallback: search in place field
        if not region:
            best_match = None
            best_keyword_len = 0
            for region_name, keywords in regions_map.items():
                for keyword in keywords:
                    if keyword in place_lower:
                        if len(keyword) > best_keyword_len:
                            best_match = region_name
                            best_keyword_len = len(keyword)
                            log.info(f"Found potential match from place: {region_name} (keyword: '{keyword}')")
            if best_match:
                region = best_match
                log.info(f"Best match from place: {region}")

        if not region:
            log.info(f"Could not determine region for place: {location}")
            return

        # Resolve ID-based region identifiers for strict client filtering
        place_for_ids = specific_location or location
        oblast_id, raion_id = get_region_ids_from_place(place_for_ids, region)
        if oblast_id:
            log.info(f"Resolved oblast_id={oblast_id} for region={region}")
        if raion_id:
            log.info(f"Resolved raion_id={raion_id} for place={place_for_ids}")

        # Determine if critical
        threat_lower = threat_type.lower()
        is_critical = any(kw in threat_lower for kw in ['ракет', 'балістич', 'kab', 'cruise', 'ballistic'])

        # Map internal threat codes to human-readable Ukrainian text for TTS
        threat_type_map = {
            'alarm': 'Повітряна тривога',
            'alarm_cancel': 'Відбій тривоги',
            'shahed': 'Загроза БПЛА',
            'raketa': 'Загроза ракетної атаки',
            'kab': 'Загроза КАБ',
            'fpv': 'Загроза FPV-дронів',
            'avia': 'Загроза авіаційної атаки',
            'vibuh': 'Вибухи',
            'artillery': 'Загроза обстрілу',
            'rozved': 'Розвідувальні дрони',
            'pusk': 'Пуски дронів',
            'vidboi': 'Відбій',
            'rszv': 'Загроза РСЗВ',
        }

        # Get human-readable threat type for notifications
        readable_threat_type = threat_type_map.get(threat_type, threat_type) if threat_type else ''

        # Create notification - different format for all clear vs threat
        if is_all_clear:
            title = "🟢 Відбій тривоги"
            body = f"{specific_location}"
            alarm_state = 'ended'
            readable_threat_type = 'Відбій тривоги'
        else:
            title = f"{'🚨' if is_critical else '⚠️'} {readable_threat_type}"
            body = f"{specific_location}"
            alarm_state = 'active'

        # Send to Firebase topic for this region (using global REGION_TOPIC_MAP)
        topic = REGION_TOPIC_MAP.get(region)
        if not topic:
            log.warning(f"No topic mapping for region: {region}")
            return

        log.info(f"Sending FCM to topic: {topic}")

        # Send via topic (reaches all subscribed devices at once)
        # CRITICAL: Use DATA-ONLY message (no notification block) so Flutter can filter by region!
        # If we include notification={}, Android shows it automatically bypassing Flutter filtering
        try:
            data_payload = {
                'type': 'all_clear' if is_all_clear else ('rocket' if is_critical else 'drone'),
                'title': title,  # Include title in data for Flutter to show
                'location': location,  # FULL place with city AND region for filtering
                'body': specific_location,  # City for TTS display
                'threat_type': readable_threat_type if readable_threat_type else 'Повітряна тривога',
                'region': region,
                'alarm_state': alarm_state,
                'is_critical': 'true' if is_critical else 'false',
                'timestamp': message_data.get('date', ''),
                'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            }

            if oblast_id:
                data_payload['oblast_id'] = oblast_id
            if raion_id:
                data_payload['raion_id'] = raion_id

            message = messaging.Message(
                data=data_payload,
                android=messaging.AndroidConfig(
                    priority='high' if not is_all_clear else 'normal',
                    ttl=timedelta(seconds=300),
                    # NO notification block - Flutter handles showing notification after filtering
                ),
                apns=messaging.APNSConfig(
                    headers={
                        'apns-priority': '10',
                        'apns-push-type': 'background',  # background so Flutter can filter
                        'apns-expiration': '0',
                    },
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            content_available=True,  # Wake app to process
                            mutable_content=True,
                            # NO alert - Flutter shows notification after filtering
                        ),
                    ),
                ),
                topic=topic,  # Send to topic instead of individual token
            )

            response = messaging.send(message)
            log.info(f"✅ Topic notification sent to {topic}: {response}")
        except Exception as e:
            log.error(f"Failed to send topic notification to {topic}: {e}")

        # NOTE: Removed all_regions broadcast for regular alerts
        # Users should only receive alerts for regions they subscribed to
        # all_regions is now only used for telegram_threat notifications
        # which have their own filtering logic in the app

        log.info(f"Sent notifications for region: {region} (topic: {topic})")
    except Exception as e:
        log.error(f"Error in send_fcm_notification: {e}")


# ============== ANONYMOUS CHAT API ==============
MAX_SYSTEM_MESSAGES = 200  # Limit for system/service messages
CHAT_RETENTION_DAYS = 7    # Keep user messages for 7 days
_chat_initialized = False

# SSE subscribers for real-time chat
CHAT_SUBSCRIBERS = set()  # queues for chat SSE clients
CHAT_TYPING_USERS = {}  # {deviceId: {'nickname': str, 'timestamp': float}}
CHAT_TYPING_TTL = 5  # seconds before typing indicator expires
MAX_SSE_SUBSCRIBERS = 100  # MEMORY PROTECTION: Limit SSE connections to prevent OOM

# ============== CHAT RATE LIMITING ==============
# Configurable rate limits (sliding window approach)
CHAT_RATE_LIMIT_MESSAGES = 10  # Max messages per window
CHAT_RATE_LIMIT_WINDOW = 60    # Window size in seconds (1 minute)
CHAT_RATE_LIMIT_COOLDOWN = 30  # Cooldown penalty in seconds after hitting limit

class ChatRateLimiter:
    """
    Sliding window rate limiter for chat messages.
    Tracks message timestamps per device and enforces limits.
    Thread-safe implementation.
    """
    def __init__(self, max_messages: int = 10, window_seconds: int = 60, cooldown_seconds: int = 30):
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self._timestamps: dict = {}  # device_id -> list of timestamps
        self._cooldowns: dict = {}   # device_id -> cooldown_end_time
        self._lock = threading.RLock()
    
    def _cleanup_old_timestamps(self, device_id: str, now: float) -> list:
        """Remove timestamps outside the sliding window."""
        window_start = now - self.window_seconds
        timestamps = self._timestamps.get(device_id, [])
        return [ts for ts in timestamps if ts > window_start]
    
    def is_rate_limited(self, device_id: str) -> tuple:
        """
        Check if device is rate limited.
        Returns: (is_limited: bool, wait_seconds: int, reason: str)
        """
        if not device_id:
            return (False, 0, '')
        
        now = time.time()
        
        with self._lock:
            # Check if in cooldown period
            cooldown_end = self._cooldowns.get(device_id, 0)
            if now < cooldown_end:
                wait = int(cooldown_end - now) + 1
                return (True, wait, 'cooldown')
            
            # Clean up and get recent timestamps
            timestamps = self._cleanup_old_timestamps(device_id, now)
            self._timestamps[device_id] = timestamps
            
            # Check if over limit
            if len(timestamps) >= self.max_messages:
                # Apply cooldown penalty
                self._cooldowns[device_id] = now + self.cooldown_seconds
                wait = self.cooldown_seconds
                return (True, wait, 'limit_exceeded')
            
            return (False, 0, '')
    
    def record_message(self, device_id: str):
        """Record a new message timestamp for the device."""
        if not device_id:
            return
        
        now = time.time()
        
        with self._lock:
            if device_id not in self._timestamps:
                self._timestamps[device_id] = []
            self._timestamps[device_id].append(now)
            
            # Cleanup: remove very old entries periodically
            if len(self._timestamps) > 10000:
                self._cleanup_all_old_entries(now)
    
    def _cleanup_all_old_entries(self, now: float):
        """Periodic cleanup of all old entries to prevent memory growth."""
        window_start = now - self.window_seconds - 3600  # Keep extra hour buffer
        devices_to_remove = []
        
        for device_id, timestamps in self._timestamps.items():
            fresh = [ts for ts in timestamps if ts > window_start]
            if fresh:
                self._timestamps[device_id] = fresh
            else:
                devices_to_remove.append(device_id)
        
        for device_id in devices_to_remove:
            del self._timestamps[device_id]
            self._cooldowns.pop(device_id, None)
    
    def get_remaining(self, device_id: str) -> int:
        """Get remaining messages allowed in current window."""
        if not device_id:
            return self.max_messages
        
        now = time.time()
        with self._lock:
            timestamps = self._cleanup_old_timestamps(device_id, now)
            return max(0, self.max_messages - len(timestamps))

# Global rate limiter instance
_chat_rate_limiter = ChatRateLimiter(
    max_messages=CHAT_RATE_LIMIT_MESSAGES,
    window_seconds=CHAT_RATE_LIMIT_WINDOW,
    cooldown_seconds=CHAT_RATE_LIMIT_COOLDOWN
)

def load_chat_messages():
    """Load chat messages from file. On first call, try git pull to restore from repo."""
    global _chat_initialized
    try:
        # On first load, try to pull latest from git
        if not _chat_initialized:
            _chat_initialized = True
            try:
                git_pull_on_startup()
            except Exception as e:
                log.warning(f"Git pull on chat init failed: {e}")

        if os.path.exists(CHAT_MESSAGES_FILE):
            with open(CHAT_MESSAGES_FILE, encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Error loading chat messages: {e}")
    return []

def save_chat_messages(messages):
    """Save chat messages to file with retention policy.
    
    User messages: kept for CHAT_RETENTION_DAYS (7 days)
    System messages: limited to MAX_SYSTEM_MESSAGES (200)
    """
    try:
        # Separate user messages and system messages
        user_messages = [m for m in messages if not m.get('isSystem', False)]
        system_messages = [m for m in messages if m.get('isSystem', False)]
        
        # User messages: time-based retention (7 days)
        cutoff_ts = time.time() - (CHAT_RETENTION_DAYS * 24 * 60 * 60)
        user_messages = [m for m in user_messages if m.get('timestamp', 0) > cutoff_ts]
        
        # System messages: count-based limit (200)
        system_messages = system_messages[-MAX_SYSTEM_MESSAGES:]
        
        # Merge and sort by timestamp
        all_messages = user_messages + system_messages
        all_messages.sort(key=lambda m: m.get('timestamp', 0))
        
        with open(CHAT_MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error saving chat messages: {e}")

@app.route('/api/chat/messages', methods=['GET'])
def get_chat_messages():
    """Get chat messages, optionally after a specific timestamp."""
    try:
        # HIGH-LOAD OPTIMIZATION: Cache chat messages for 3 seconds
        after = request.args.get('after', '')
        limit = min(int(request.args.get('limit', 50)), 200)  # Default 50, max 200
        cache_key = f'chat_messages_{after}_{limit}'

        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            response = jsonify(cached)
            response.headers['Cache-Control'] = 'public, max-age=3'
            response.headers['X-Cache'] = 'HIT'
            return response

        messages = load_chat_messages()

        # Optional: get only messages after timestamp
        if after:
            try:
                after_ts = float(after)
                messages = [m for m in messages if m.get('timestamp', 0) > after_ts]
            except:
                pass

        # Return last N messages by default
        messages = messages[-limit:]

        result = {
            'success': True,
            'messages': messages,
            'count': len(messages)
        }

        # Cache for 3 seconds
        RESPONSE_CACHE.set(cache_key, result, ttl=3)

        response = jsonify(result)
        response.headers['Cache-Control'] = 'public, max-age=3'
        response.headers['X-Cache'] = 'MISS'
        return response
    except Exception as e:
        log.error(f"Error getting chat messages: {e}")
        return jsonify({'error': str(e)}), 500

# ============== CHAT SSE (Server-Sent Events) ==============
def broadcast_chat_event(event_type: str, data: dict):
    """Broadcast chat event to all SSE subscribers."""
    if not CHAT_SUBSCRIBERS:
        return
    try:
        payload = json.dumps({
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        }, ensure_ascii=False)
    except Exception:
        return
    dead = []
    for q in list(CHAT_SUBSCRIBERS):
        try:
            q.put_nowait(payload)
        except Exception:
            dead.append(q)
    for d in dead:
        CHAT_SUBSCRIBERS.discard(d)

@app.route('/api/chat/stream')
def chat_stream():
    """SSE endpoint for real-time chat updates."""
    # MEMORY PROTECTION: Reject if too many subscribers
    if len(CHAT_SUBSCRIBERS) >= MAX_SSE_SUBSCRIBERS:
        log.warning(f"[CHAT_SSE] Rejected connection - limit reached ({MAX_SSE_SUBSCRIBERS})")
        return jsonify({'error': 'Server busy, please use polling'}), 503
    
    def gen():
        q = queue.Queue()
        CHAT_SUBSCRIBERS.add(q)
        last_ping = time.time()
        log.info(f"[CHAT_SSE] Client connected. Total subscribers: {len(CHAT_SUBSCRIBERS)}")
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
            CHAT_SUBSCRIBERS.discard(q)
            log.info(f"[CHAT_SSE] Client disconnected. Total subscribers: {len(CHAT_SUBSCRIBERS)}")
    
    headers = {
        'Cache-Control': 'no-store',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    }
    return Response(gen(), mimetype='text/event-stream', headers=headers)

@app.route('/api/chat/typing', methods=['POST'])
def chat_typing():
    """Notify that user is typing."""
    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')
        nickname = data.get('nickname', '')
        is_typing = data.get('isTyping', True)
        
        if not device_id or not nickname:
            return jsonify({'error': 'Missing deviceId or nickname'}), 400
        
        if is_typing:
            CHAT_TYPING_USERS[device_id] = {
                'nickname': nickname,
                'timestamp': time.time()
            }
        else:
            CHAT_TYPING_USERS.pop(device_id, None)
        
        # Clean up expired typing indicators
        now = time.time()
        expired = [k for k, v in CHAT_TYPING_USERS.items() if now - v['timestamp'] > CHAT_TYPING_TTL]
        for k in expired:
            del CHAT_TYPING_USERS[k]
        
        # Broadcast typing status
        typing_users = [v['nickname'] for v in CHAT_TYPING_USERS.values()]
        broadcast_chat_event('typing', {'users': typing_users})
        
        return jsonify({'success': True})
    except Exception as e:
        log.error(f"Error in chat_typing: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/react', methods=['POST'])
def chat_react():
    """Add or remove reaction to a message."""
    try:
        data = request.get_json() or {}
        message_id = data.get('messageId', '')
        device_id = data.get('deviceId', '')
        emoji = data.get('emoji', '')
        nickname = data.get('nickname', '')
        
        if not message_id or not device_id or not emoji:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate emoji (only allowed reactions)
        allowed_emojis = ['👍', '❤️', '😂', '😮', '😢', '🔥', '💪', '🙏']
        if emoji not in allowed_emojis:
            return jsonify({'error': 'Invalid emoji'}), 400
        
        messages = load_chat_messages()
        message = next((m for m in messages if m.get('id') == message_id), None)
        
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        # Initialize reactions if not present
        if 'reactions' not in message:
            message['reactions'] = {}
        
        # Toggle reaction
        if emoji not in message['reactions']:
            message['reactions'][emoji] = []
        
        reaction_list = message['reactions'][emoji]
        user_reacted = next((r for r in reaction_list if r.get('deviceId') == device_id), None)
        
        if user_reacted:
            # Remove reaction
            message['reactions'][emoji] = [r for r in reaction_list if r.get('deviceId') != device_id]
            if not message['reactions'][emoji]:
                del message['reactions'][emoji]
            action = 'removed'
        else:
            # Add reaction
            reaction_list.append({
                'deviceId': device_id,
                'nickname': nickname,
                'timestamp': time.time()
            })
            action = 'added'
        
        # Clean up empty reactions
        if not message['reactions']:
            del message['reactions']
        
        save_chat_messages(messages)
        
        # Broadcast reaction update
        broadcast_chat_event('reaction', {
            'messageId': message_id,
            'emoji': emoji,
            'action': action,
            'deviceId': device_id,
            'nickname': nickname,
            'reactions': message.get('reactions', {})
        })
        
        return jsonify({
            'success': True,
            'action': action,
            'reactions': message.get('reactions', {})
        })
    except Exception as e:
        log.error(f"Error in chat_react: {e}")
        return jsonify({'error': str(e)}), 500

# File to store registered nicknames with device IDs
CHAT_NICKNAMES_FILE = os.path.join(PERSISTENT_DATA_DIR, 'chat_nicknames.json') if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR) else 'chat_nicknames.json'
CHAT_BANNED_USERS_FILE = os.path.join(PERSISTENT_DATA_DIR, 'chat_banned_users.json') if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR) else 'chat_banned_users.json'

def load_chat_nicknames():
    """Load registered chat nicknames."""
    try:
        if os.path.exists(CHAT_NICKNAMES_FILE):
            with open(CHAT_NICKNAMES_FILE, encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Error loading chat nicknames: {e}")
    return {}

def save_chat_nicknames(nicknames):
    """Save registered chat nicknames."""
    try:
        with open(CHAT_NICKNAMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(nicknames, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error saving chat nicknames: {e}")

def load_banned_users():
    """Load banned users list."""
    try:
        if os.path.exists(CHAT_BANNED_USERS_FILE):
            with open(CHAT_BANNED_USERS_FILE, encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Error loading banned users: {e}")
    return {}

def save_banned_users(banned):
    """Save banned users list."""
    try:
        with open(CHAT_BANNED_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(banned, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error saving banned users: {e}")

def is_user_banned(device_id):
    """Check if device is banned."""
    if not device_id:
        return False
    banned = load_banned_users()
    return device_id in banned

def is_nickname_forbidden(nickname):
    """Check if nickname contains forbidden words."""
    forbidden = ['neptun', 'нептун', 'neptune', 'admin', 'адмін', 'moderator', 'модератор', 'support', 'підтримка']
    nickname_lower = nickname.lower()
    for word in forbidden:
        if word in nickname_lower:
            return True
    return False

@app.route('/api/chat/check-nickname', methods=['POST'])
def check_chat_nickname():
    """Check if nickname is available and valid."""
    try:
        data = request.get_json()
        nickname = data.get('nickname', '').strip()
        device_id = data.get('deviceId', '')

        if not nickname:
            return jsonify({'available': False, 'error': 'Нікнейм не може бути порожнім'}), 400

        if len(nickname) < 3:
            return jsonify({'available': False, 'error': 'Нікнейм має бути мінімум 3 символи'}), 400

        if len(nickname) > 20:
            return jsonify({'available': False, 'error': 'Нікнейм не може бути довше 20 символів'}), 400

        # Check forbidden words
        if is_nickname_forbidden(nickname):
            return jsonify({'available': False, 'error': 'Цей нікнейм заборонено'}), 400

        # Load existing nicknames
        nicknames = load_chat_nicknames()
        nickname_lower = nickname.lower()

        # Check if nickname is taken by someone else
        for existing_nickname, owner_device_id in nicknames.items():
            if existing_nickname.lower() == nickname_lower:
                # Allow if same device
                if owner_device_id == device_id:
                    return jsonify({'available': True, 'message': 'Це ваш поточний нік'})
                else:
                    return jsonify({'available': False, 'error': 'Цей нікнейм вже зайнятий'}), 400

        return jsonify({'available': True})
    except Exception as e:
        log.error(f"Error checking nickname: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/register-nickname', methods=['POST'])
def register_chat_nickname():
    """Register a nickname for a device."""
    try:
        data = request.get_json()
        nickname = data.get('nickname', '').strip()
        device_id = data.get('deviceId', '')

        if not nickname or not device_id:
            return jsonify({'success': False, 'error': 'Missing nickname or deviceId'}), 400

        if len(nickname) < 3 or len(nickname) > 20:
            return jsonify({'success': False, 'error': 'Нікнейм має бути 3-20 символів'}), 400

        # Check forbidden words
        if is_nickname_forbidden(nickname):
            return jsonify({'success': False, 'error': 'Цей нікнейм заборонено'}), 400

        # Load existing nicknames
        nicknames = load_chat_nicknames()
        nickname_lower = nickname.lower()

        # Check if nickname is taken by someone else
        for existing_nickname, owner_device_id in nicknames.items():
            if existing_nickname.lower() == nickname_lower and owner_device_id != device_id:
                return jsonify({'success': False, 'error': 'Цей нікнейм вже зайнятий'}), 400

        # Remove any previous nickname for this device
        nicknames = {k: v for k, v in nicknames.items() if v != device_id}

        # Register new nickname
        nicknames[nickname] = device_id
        save_chat_nicknames(nicknames)

        log.info(f"Registered chat nickname: {nickname} for device {device_id[:20]}...")

        return jsonify({'success': True, 'nickname': nickname})
    except Exception as e:
        log.error(f"Error registering nickname: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/send', methods=['POST'])
def send_chat_message():
    """Send a new chat message."""
    try:
        data = request.get_json()

        user_id = data.get('userId', '')
        device_id = data.get('deviceId', '')
        message = data.get('message', '').strip()
        reply_to = data.get('replyTo')  # Optional reply to message id

        if not user_id or not message:
            return jsonify({'error': 'Missing userId or message'}), 400

        # Check if user is banned
        if is_user_banned(device_id):
            return jsonify({'error': 'Ви заблоковані в чаті', 'banned': True}), 403

        # Rate limiting check (skip for moderators)
        if not is_chat_moderator(device_id):
            is_limited, wait_seconds, reason = _chat_rate_limiter.is_rate_limited(device_id)
            if is_limited:
                remaining = _chat_rate_limiter.get_remaining(device_id)
                log.warning(f"Rate limited user {user_id[:20]} ({reason}), wait {wait_seconds}s")
                return jsonify({
                    'error': f'Забагато повідомлень. Зачекайте {wait_seconds} сек.',
                    'rate_limited': True,
                    'wait_seconds': wait_seconds,
                    'remaining': remaining
                }), 429

        # Validate nickname ownership if device_id provided
        if device_id:
            nicknames = load_chat_nicknames()
            registered_device = nicknames.get(user_id)
            if registered_device and registered_device != device_id:
                return jsonify({'error': 'Цей нікнейм належить іншому користувачу'}), 403

        # Check forbidden nickname
        if is_nickname_forbidden(user_id):
            return jsonify({'error': 'Заборонений нікнейм'}), 400

        # Sanitize message (basic)
        if len(message) > 1000:
            message = message[:1000]

        # Create message object
        kyiv_tz = pytz.timezone('Europe/Kiev')
        now = datetime.now(kyiv_tz)

        # Check if sender is a moderator
        sender_is_moderator = is_chat_moderator(device_id)

        new_message = {
            'id': str(uuid.uuid4()),
            'userId': user_id,
            'deviceId': device_id,  # Store deviceId for isMe detection after nickname change
            'message': message,
            'timestamp': now.timestamp(),
            'time': now.strftime('%H:%M'),
            'date': now.strftime('%d.%m.%Y'),
            'isModerator': sender_is_moderator  # Show moderator badge to other users
        }

        # Add reply reference if provided
        if reply_to:
            messages = load_chat_messages()
            # Find the original message being replied to
            original_msg = next((m for m in messages if m.get('id') == reply_to), None)
            if original_msg:
                new_message['replyTo'] = {
                    'id': original_msg.get('id'),
                    'userId': original_msg.get('userId'),
                    'message': original_msg.get('message', '')[:100]  # Truncate preview
                }

        # Load, append, save
        messages = load_chat_messages()
        messages.append(new_message)
        save_chat_messages(messages)

        # Record message for rate limiting
        _chat_rate_limiter.record_message(device_id)

        # Broadcast new message via SSE
        broadcast_chat_event('new_message', new_message)
        
        # Clear typing indicator for this user
        CHAT_TYPING_USERS.pop(device_id, None)

        # Trigger git sync for persistence
        try:
            maybe_git_autocommit()
        except Exception as git_err:
            log.warning(f"Git autocommit failed for chat: {git_err}")

        log.info(f"Chat message from {user_id[:20]}: {message[:50]}...")

        return jsonify({
            'success': True,
            'message': new_message
        })
    except Exception as e:
        log.error(f"Error sending chat message: {e}")
        return jsonify({'error': str(e)}), 500

# Moderator secret for message deletion
MODERATOR_SECRET = '99446626'

# List of moderator device IDs
CHAT_MODERATORS_FILE = os.path.join(PERSISTENT_DATA_DIR, 'chat_moderators.json') if PERSISTENT_DATA_DIR and os.path.isdir(PERSISTENT_DATA_DIR) else 'chat_moderators.json'

def load_chat_moderators():
    """Load list of moderator device IDs."""
    try:
        if os.path.exists(CHAT_MODERATORS_FILE):
            with open(CHAT_MODERATORS_FILE, encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Error loading chat moderators: {e}")
    return []

def save_chat_moderators(moderators):
    """Save list of moderator device IDs."""
    try:
        with open(CHAT_MODERATORS_FILE, 'w', encoding='utf-8') as f:
            json.dump(moderators, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"Error saving chat moderators: {e}")

def is_chat_moderator(device_id):
    """Check if device is a chat moderator.
    
    Also checks JWT token claim if available.
    """
    if not device_id:
        return False
    
    # Check JWT token claim first (more secure)
    try:
        user = get_current_user()
        if user and user.get('is_moderator'):
            return True
    except Exception:
        pass
    
    # Fallback to device_id list
    moderators = load_chat_moderators()
    return device_id in moderators

@app.route('/api/chat/message/<message_id>', methods=['DELETE'])
def delete_chat_message(message_id):
    """Delete a chat message (moderator or owner only)."""
    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')

        messages = load_chat_messages()

        # Find the message
        message_to_delete = next((m for m in messages if m.get('id') == message_id), None)

        if not message_to_delete:
            return jsonify({'error': 'Повідомлення не знайдено'}), 404

        # SERVER-SIDE moderator check - don't trust client isModerator flag!
        is_actual_moderator = is_chat_moderator(device_id)
        
        # Check permissions - either moderator or message owner
        if is_actual_moderator:
            # Moderators can delete any message
            pass
        elif device_id:
            # Regular users can only delete their own messages
            nicknames = load_chat_nicknames()
            message_user = message_to_delete.get('userId')
            user_device = nicknames.get(message_user)
            if user_device != device_id:
                return jsonify({'error': 'Немає прав для видалення'}), 403
        else:
            return jsonify({'error': 'Немає прав для видалення'}), 403

        # Remove the message
        messages = [m for m in messages if m.get('id') != message_id]
        save_chat_messages(messages)
        
        # Broadcast message deletion via SSE
        broadcast_chat_event('delete_message', {'messageId': message_id})

        log.info(f"Chat message {message_id} deleted by {'moderator' if is_actual_moderator else device_id[:20]}")

        return jsonify({
            'success': True,
            'message': 'Повідомлення видалено'
        })
    except Exception as e:
        log.error(f"Error deleting chat message: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/ban-user', methods=['POST'])
def ban_chat_user():
    """Ban a user from chat (moderator only)."""
    try:
        data = request.get_json() or {}
        target_nickname = data.get('nickname', '')
        device_id = data.get('deviceId', '')
        reason = data.get('reason', 'Порушення правил чату')

        # SERVER-SIDE moderator check - don't trust client isModerator flag!
        if not is_chat_moderator(device_id):
            log.warning(f"Unauthorized ban attempt from device: {device_id[:20] if device_id else 'unknown'}...")
            return jsonify({'error': 'Тільки модератори можуть блокувати'}), 403

        if not target_nickname:
            return jsonify({'error': 'Вкажіть нікнейм'}), 400

        # Find device ID for this nickname
        nicknames = load_chat_nicknames()
        target_device_id = nicknames.get(target_nickname)

        if not target_device_id:
            return jsonify({'error': 'Користувача не знайдено'}), 404

        # Add to banned list
        banned = load_banned_users()
        kyiv_tz = pytz.timezone('Europe/Kiev')
        now = datetime.now(kyiv_tz)

        banned[target_device_id] = {
            'nickname': target_nickname,
            'reason': reason,
            'bannedAt': now.isoformat(),
            'bannedAtTimestamp': now.timestamp()
        }
        save_banned_users(banned)

        log.info(f"User banned: {target_nickname} (device: {target_device_id[:20]}...) - Reason: {reason}")

        return jsonify({
            'success': True,
            'message': f'Користувач {target_nickname} заблокований'
        })
    except Exception as e:
        log.error(f"Error banning user: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/unban-user', methods=['POST'])
def unban_chat_user():
    """Unban a user from chat (moderator only)."""
    try:
        data = request.get_json() or {}
        target_nickname = data.get('nickname', '')
        device_id = data.get('deviceId', '')

        # SERVER-SIDE moderator check - don't trust client isModerator flag!
        if not is_chat_moderator(device_id):
            log.warning(f"Unauthorized unban attempt from device: {device_id[:20] if device_id else 'unknown'}...")
            return jsonify({'error': 'Тільки модератори можуть розблоковувати'}), 403

        if not target_nickname:
            return jsonify({'error': 'Вкажіть нікнейм'}), 400

        # Find device ID for this nickname
        nicknames = load_chat_nicknames()
        target_device_id = nicknames.get(target_nickname)

        # Remove from banned list (check both by device and nickname)
        banned = load_banned_users()
        removed = False

        if target_device_id and target_device_id in banned:
            del banned[target_device_id]
            removed = True

        # Also check by nickname in case device ID changed
        for device_id, info in list(banned.items()):
            if info.get('nickname') == target_nickname:
                del banned[device_id]
                removed = True

        if not removed:
            return jsonify({'error': 'Користувач не заблокований'}), 404

        save_banned_users(banned)
        log.info(f"User unbanned: {target_nickname}")

        return jsonify({
            'success': True,
            'message': f'Користувач {target_nickname} розблокований'
        })
    except Exception as e:
        log.error(f"Error unbanning user: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/check-ban', methods=['POST'])
def check_user_ban():
    """Check if current user is banned."""
    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')

        if not device_id:
            return jsonify({'banned': False})

        banned = load_banned_users()
        ban_info = banned.get(device_id)

        if ban_info:
            return jsonify({
                'banned': True,
                'reason': ban_info.get('reason', 'Порушення правил'),
                'bannedAt': ban_info.get('bannedAt', '')
            })

        return jsonify({'banned': False})
    except Exception as e:
        log.error(f"Error checking ban: {e}")
        return jsonify({'banned': False})

@app.route('/api/chat/banned-users', methods=['GET'])
def get_banned_users():
    """Get list of banned users (moderator only)."""
    try:
        # SERVER-SIDE moderator check
        device_id = request.args.get('deviceId', '')
        if not is_chat_moderator(device_id):
            return jsonify({'error': 'Доступ заборонено'}), 403

        banned = load_banned_users()
        users = []
        for device_id, info in banned.items():
            users.append({
                'deviceId': device_id[:20] + '...',
                'nickname': info.get('nickname', 'Unknown'),
                'reason': info.get('reason', ''),
                'bannedAt': info.get('bannedAt', '')
            })

        return jsonify({'users': users, 'count': len(users)})
    except Exception as e:
        log.error(f"Error getting banned users: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/add-moderator', methods=['POST'])
def add_chat_moderator():
    """Add a device as chat moderator (requires admin secret)."""
    try:
        data = request.get_json() or {}
        secret = data.get('secret', '')
        device_id = data.get('deviceId', '')

        if secret != MODERATOR_SECRET:
            return jsonify({'error': 'Невірний секрет'}), 403

        if not device_id:
            return jsonify({'error': 'deviceId обовʼязковий'}), 400

        moderators = load_chat_moderators()
        if device_id not in moderators:
            moderators.append(device_id)
            save_chat_moderators(moderators)
            log.info(f"Added chat moderator: {device_id[:20]}...")

        return jsonify({'success': True, 'message': 'Модератора додано'})
    except Exception as e:
        log.error(f"Error adding moderator: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/remove-moderator', methods=['POST'])
def remove_chat_moderator():
    """Remove a device from chat moderators (requires admin secret)."""
    try:
        data = request.get_json() or {}
        secret = data.get('secret', '')
        device_id = data.get('deviceId', '')

        if secret != MODERATOR_SECRET:
            return jsonify({'error': 'Невірний секрет'}), 403

        if not device_id:
            return jsonify({'error': 'deviceId обовʼязковий'}), 400

        moderators = load_chat_moderators()
        if device_id in moderators:
            moderators.remove(device_id)
            save_chat_moderators(moderators)
            log.info(f"Removed chat moderator: {device_id[:20]}...")

        return jsonify({'success': True, 'message': 'Модератора видалено'})
    except Exception as e:
        log.error(f"Error removing moderator: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/user-profile', methods=['POST'])
def get_chat_user_profile():
    """Get user profile info - basic info for all, detailed for moderators."""
    try:
        data = request.get_json() or {}
        requester_device_id = data.get('requesterDeviceId', '')
        target_device_id = data.get('targetDeviceId', '')
        target_user_id = data.get('targetUserId', '')

        log.info(f"Profile request: requester={requester_device_id[:20] if requester_device_id else 'none'}..., target_user={target_user_id}")

        # Check if requester is moderator
        is_requester_mod = is_chat_moderator(requester_device_id)
        log.info(f"Requester is moderator: {is_requester_mod}")

        # Find device_id from userId if not provided
        if not target_device_id and target_user_id:
            nicknames = load_chat_nicknames()
            target_device_id = nicknames.get(target_user_id, '')
            log.info(f"Lookup nickname '{target_user_id}' -> device: {target_device_id[:20] if target_device_id else 'NOT_FOUND'}...")

        # Check if target is moderator
        is_target_mod = is_chat_moderator(target_device_id) if target_device_id else False

        # Check if target is banned
        is_banned = is_user_banned(target_device_id) if target_device_id else False

        # Basic response for all users
        response_data = {
            'userId': target_user_id,
            'isModerator': is_target_mod,
            'isBanned': is_banned,
        }

        # If requester is moderator - show more details
        if is_requester_mod and target_device_id:
            # Load device data from device_store
            devices = device_store._load()
            device_data = devices.get(target_device_id, {})

            # Get regions from device data
            regions = device_data.get('regions', [])
            log.info(f"Found regions for device: {regions}")

            response_data['deviceId'] = target_device_id[:20] + '...' if len(target_device_id) > 20 else target_device_id
            response_data['regions'] = regions
            response_data['lastSeen'] = device_data.get('last_seen', '')
        else:
            # For regular users - only basic info
            response_data['regions'] = []
            response_data['message'] = 'Детальна інформація доступна тільки модераторам'

        return jsonify(response_data)
    except Exception as e:
        log.error(f"Error getting user profile: {e}")
        return jsonify({'error': str(e)}), 500


# ============= PUSH NOTIFICATIONS FOR ALARMS =============

# Store previous alarm state to detect changes
_previous_alarms = {}

def check_alarm_changes():
    """Background task to check for alarm changes and send notifications."""
    global _previous_alarms

    if not firebase_initialized:
        return

    try:

        # Fetch current alarms
        response = http_requests.get(
            f'{ALARM_API_BASE}/alerts',
            headers={'Authorization': ALARM_API_KEY},
            timeout=8
        )

        if not response.ok:
            return

        data = response.json()
        current_alarms = {}

        # Build current alarm state by region name
        for region in data:
            region_name = region.get('regionName', '')
            active_alerts = region.get('activeAlerts', [])
            if active_alerts:
                current_alarms[region_name] = active_alerts

        # Compare with previous state
        if _previous_alarms:
            # Check for new alarms (started)
            for region, alerts in current_alarms.items():
                if region not in _previous_alarms:
                    # New alarm started
                    _send_alarm_notification(region, alerts, 'started')

            # Check for ended alarms
            for region, alerts in _previous_alarms.items():
                if region not in current_alarms:
                    # Alarm ended
                    _send_alarm_notification(region, alerts, 'ended')

        # Update previous state
        _previous_alarms = current_alarms

    except Exception as e:
        log.error(f"Error checking alarm changes: {e}")

def _send_alarm_notification(region, alerts, status):
    """Send push notification for alarm change."""
    try:
        from firebase_admin import messaging

        # Get alert types
        alert_types = [alert.get('type', '') for alert in alerts]

        # Determine criticality
        critical_types = ['Повітряна тривога', 'Ракетна небезпека', 'Хімічна загроза']
        is_critical = any(t in critical_types for t in alert_types)

        # Build notification message
        if status == 'started':
            emoji = '🚨' if is_critical else '⚠️'
            title = f'{emoji} Повітряна тривога!'
            body = f'{region}: {", ".join(alert_types)}'
        else:
            emoji = '✅'
            title = f'{emoji} Відбій тривоги'
            body = f'{region}: тривога закінчена'

        # Get devices subscribed to this region
        devices = device_store.get_devices_for_region(region)

        if not devices:
            return

        # Send to all subscribed devices
        messages = []
        for device in devices:
            if device.get('token'):
                messages.append(messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data={
                        'type': 'rocket' if is_critical else 'drone',
                        'region': region,
                        'status': status,
                    },
                    token=device['token'],
                    android=messaging.AndroidConfig(
                        priority='high' if is_critical else 'normal',
                        notification=messaging.AndroidNotification(
                            channel_id='critical_alerts' if is_critical else 'normal_alerts',
                            sound='default',
                        ),
                    ),
                    apns=messaging.APNSConfig(
                        headers={
                            'apns-priority': '10',
                            'apns-push-type': 'alert',
                            'apns-expiration': '0',
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
                ))

        if messages:
            # Send batch
            response = messaging.send_all(messages)
            log.info(f"Sent {response.success_count} notifications for {region} ({status})")

    except Exception as e:
        log.error(f"Error sending alarm notification: {e}")

# Background thread for monitoring alarms
def _alarm_monitor_thread():
    """Background thread that checks for alarm changes every 30 seconds."""
    gc_counter = 0
    while True:
        try:
            check_alarm_changes()

            # MEMORY OPTIMIZATION: Force garbage collection every 5 minutes
            gc_counter += 1
            if gc_counter >= 10:  # 10 * 30 sec = 5 minutes
                gc.collect()
                gc_counter = 0

        except Exception as e:
            log.error(f"Alarm monitor thread error: {e}")
        time.sleep(30)  # Check every 30 seconds

# Start alarm monitoring thread
# DISABLED: Using monitor_alarms() instead which has better deduplication logic
# _alarm_monitor = threading.Thread(target=_alarm_monitor_thread, daemon=True)
# _alarm_monitor.start()
log.info("Old alarm monitoring thread DISABLED - using monitor_alarms() instead")


@app.route('/api/stats')
def get_alarm_stats():
    """Get alarm statistics for a region from persistent database."""
    try:
        region = request.args.get('region', 'Дніпропетровська')
        
        # Get stats from persistent SQLite database
        stats = get_alarm_stats_from_db(region)
        
        # Average alarm duration (rough estimate)
        avg_duration = 25  # Default 25 min

        return jsonify({
            'region': region,
            'today_alarms': stats['today_alarms'],
            'week_alarms': stats['week_alarms'],
            'month_alarms': stats['month_alarms'],
            'avg_duration_min': avg_duration,
        })
    except Exception as e:
        log.error(f"Error getting stats: {e}")
        return jsonify({
            'today_alarms': 0,
            'week_alarms': 0,
            'month_alarms': 0,
            'avg_duration_min': 0,
        })

# =============================================================================
# DEBUG: Route Patterns Viewer
# =============================================================================
@app.route('/api/ai/route-patterns')
def api_route_patterns():
    """View AI learned route patterns"""
    try:
        patterns = _load_route_patterns()
        return jsonify({
            'status': 'ok',
            'file': ROUTE_PATTERNS_FILE,
            'patterns_count': len(patterns.get('patterns', {})),
            'historical_routes_count': len(patterns.get('historical_routes', [])),
            'ai_corrections_count': len(patterns.get('ai_corrections', [])),
            'last_updated': patterns.get('last_updated'),
            'data': patterns
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
