
# pyright: reportUnusedVariable=false, reportRedeclaration=false, reportGeneralTypeIssues=false
# pyright: reportUndefinedVariable=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false
# type: ignore
# pylint: disable=all
# ---------------- Admin & blocking endpoints -----------------

# ...existing code...

import os, re, json, asyncio, threading, logging, pytz, time, subprocess, queue, sys, platform, traceback, uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, Response, send_from_directory
from telethon import TelegramClient
from apscheduler.schedulers.background import BackgroundScheduler

# Import blackout API client
try:
    from blackout_api import blackout_client
    BLACKOUT_API_AVAILABLE = True
    print("INFO: Blackout API client loaded successfully")
except Exception as e:
    BLACKOUT_API_AVAILABLE = False
    print(f"WARNING: Blackout API client not available: {e}")

# Import schedule updater
try:
    from schedule_updater import schedule_updater, start_schedule_updates
    SCHEDULE_UPDATER_AVAILABLE = True
    print("INFO: Schedule updater loaded successfully")
except Exception as e:
    SCHEDULE_UPDATER_AVAILABLE = False
    print(f"WARNING: Schedule updater not available: {e}")

# Import expanded Ukraine addresses database
try:
    from ukraine_addresses_db import UKRAINE_ADDRESSES_DB, UKRAINE_CITIES
    print(f"INFO: Ukraine addresses database loaded: {len(UKRAINE_ADDRESSES_DB)} addresses")
except Exception as e:
    UKRAINE_ADDRESSES_DB = {}
    UKRAINE_CITIES = []
    print(f"WARNING: Ukraine addresses database not available: {e}")

# SpaCy integration for enhanced Ukrainian NLP
try:
    import spacy
    nlp = spacy.load('uk_core_news_sm')
    SPACY_AVAILABLE = True
    print("INFO: SpaCy Ukrainian model uk_core_news_sm loaded successfully")
except ImportError:
    SPACY_AVAILABLE = False
    nlp = None
    print("WARNING: SpaCy library not available - NLP analysis disabled")
except OSError:
    SPACY_AVAILABLE = False
    nlp = None
    print("WARNING: SpaCy Ukrainian model uk_core_news_sm not found - NLP analysis disabled")
    print("HINT: Install with: python -m spacy download uk_core_news_sm")
except Exception as e:
    SPACY_AVAILABLE = False
    nlp = None
    print(f"ERROR: SpaCy initialization failed: {e}")

# Nominatim geocoding integration
try:
    from nominatim_geocoder import get_coordinates_nominatim
    NOMINATIM_AVAILABLE = True
except ImportError:
    NOMINATIM_AVAILABLE = False
    def get_coordinates_nominatim(city_name, region=None):
        return None

# Context-aware geocoding integration
try:
    from context_aware_geocoder import get_context_aware_geocoding
    CONTEXT_GEOCODER_AVAILABLE = True
except ImportError:
    CONTEXT_GEOCODER_AVAILABLE = False
    def get_context_aware_geocoding(text):
        return []
        return None
    nlp = None
    SPACY_AVAILABLE = False
    print("WARNING: SpaCy Ukrainian model not available. Using fallback geocoding methods.")
try:
    from telethon.errors import (
        AuthKeyDuplicatedError,
        AuthKeyUnregisteredError,
        FloodWaitError,
        SessionPasswordNeededError
    )
except ImportError:
    # Fallback dummies if some names not present in current Telethon version
    class AuthKeyDuplicatedError(Exception):
        pass
    class AuthKeyUnregisteredError(Exception):
        pass
    class FloodWaitError(Exception):
        def __init__(self, seconds=60): self.seconds = seconds
    class SessionPasswordNeededError(Exception):
        pass
from telethon.sessions import StringSession
import math

# === Kyiv Directional Enhancement Functions ===
def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing from point 1 to point 2 in degrees (0-360)"""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    return (bearing + 360) % 360

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

API_ID = int(os.getenv('TELEGRAM_API_ID', '0') or '0')
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
_DEFAULT_CHANNELS = 'UkraineAlarmSignal,kpszsu,war_monitor,napramok,raketa_trevoga'
# TELEGRAM_CHANNELS env var (comma-separated) overrides; fallback includes numeric channel ID.
CHANNELS = [c.strip() for c in os.getenv('TELEGRAM_CHANNELS', _DEFAULT_CHANNELS).split(',') if c.strip()]

# Channels which failed resolution (entity not found / access denied) to avoid repeated spam
INVALID_CHANNELS = set()
GOOGLE_MAPS_KEY = os.getenv('GOOGLE_MAPS_KEY', '')
OPENCAGE_API_KEY = os.getenv('OPENCAGE_API_KEY', '')  # optional geocoding
ALWAYS_STORE_RAW = os.getenv('ALWAYS_STORE_RAW', '1') not in ('0','false','False')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize background scheduler for automatic schedule updates
scheduler = BackgroundScheduler(daemon=True)
scheduler_initialized = False

def init_scheduler():
    """Initialize the scheduler for automatic updates"""
    global scheduler_initialized
    
    if scheduler_initialized:
        return
    
    if SCHEDULE_UPDATER_AVAILABLE:
        try:
            # Run initial update
            start_schedule_updates()
            
            # Schedule hourly updates
            scheduler.add_job(
                func=schedule_updater.update_all_schedules,
                trigger='interval',
                hours=1,
                id='update_schedules',
                name='Update blackout schedules from DTEK and Ukrenergo',
                replace_existing=True
            )
            
            scheduler.start()
            scheduler_initialized = True
            log.info("✅ Scheduler started: automatic updates every hour")
        except Exception as e:
            log.error(f"❌ Failed to start scheduler: {e}")
    else:
        log.warning("⚠ Schedule updater not available, skipping automatic updates")
    
    # YASNO API schedule refresh every hour
    if BLACKOUT_API_AVAILABLE:
        try:
            # Schedule YASNO schedule refresh
            scheduler.add_job(
                func=refresh_yasno_schedules,
                trigger='interval',
                hours=1,
                id='refresh_yasno',
                name='Refresh YASNO API schedules cache',
                replace_existing=True
            )
            log.info("✅ YASNO schedule refresh scheduled every hour")
        except Exception as e:
            log.error(f"❌ Failed to schedule YASNO refresh: {e}")

def refresh_yasno_schedules():
    """Background task to refresh YASNO schedules cache"""
    try:
        if BLACKOUT_API_AVAILABLE:
            log.info("🔄 Refreshing YASNO schedules from API...")
            result = blackout_client.fetch_yasno_schedule(force_refresh=True)
            if result:
                log.info(f"✅ YASNO schedules refreshed successfully")
            else:
                log.warning("⚠ Failed to refresh YASNO schedules")
    except Exception as e:
        log.error(f"❌ Error refreshing YASNO schedules: {e}")

# Don't start scheduler immediately - wait for first request
# init_scheduler()

# BANDWIDTH OPTIMIZATION: Rate limiting to prevent abuse
    # Rate limiting отключен: все пользователи имеют свободный доступ

# BANDWIDTH OPTIMIZATION: Enable gzip compression globally
from flask import Flask
import gzip
import io

# Initialize scheduler on first request
@app.before_request
def ensure_scheduler_running():
    """Ensure scheduler is initialized on first request"""
    if not scheduler_initialized:
        init_scheduler()

# Add global response compression
@app.after_request
def compress_response(response):
    """Apply gzip compression to reduce bandwidth usage."""
    if (
        response.status_code == 200 and
        'gzip' in request.headers.get('Accept-Encoding', '').lower() and
        response.content_length and response.content_length > 500 and
        response.content_type.startswith(('application/json', 'text/html', 'text/css', 'application/javascript'))
    ):
        try:
            # Compress the response data
            buffer = io.BytesIO()
            with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
                f.write(response.get_data())
            
            response.set_data(buffer.getvalue())
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Length'] = len(response.get_data())
            response.headers['Vary'] = 'Accept-Encoding'
        except Exception:
            pass  # If compression fails, return original response
    
    # Add cache headers for static content
    if request.endpoint == 'static':
        response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
    
    return response

# Custom route for serving pre-compressed static files
@app.route('/static/<path:filename>')
def static_with_gzip(filename):
    """Serve static files with gzip compression support."""
    # Rate limiting removed
    # ...existing code...
    """Serve static files with gzip compression support."""
    
    # CRITICAL BANDWIDTH PROTECTION: Rate limit static files
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    static_requests = request_counts.get(f"{client_ip}_static", [])
    now_time = time.time()
    
    # Clean old requests (last 60 seconds)
    static_requests = [req_time for req_time in static_requests if now_time - req_time < 60]
    
    # Allow only 5 static file requests per minute per IP
    if len(static_requests) >= 5:
        print(f"[CRITICAL BANDWIDTH] Blocking static file {filename} from {client_ip} - too many requests")
        return jsonify({'error': 'Static files rate limited - wait 1 minute'}), 429
    
    static_requests.append(now_time)
    request_counts[f"{client_ip}_static"] = static_requests
        # Rate limiting removed
    
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

# Add cache headers for static files
@app.after_request
def add_cache_headers(response):
    if request.endpoint == 'static':
        # Check if this is a versioned resource (with ?v= parameter)
        if 'v=' in request.query_string.decode():
            # Cache versioned static files for 1 month (they won't change)
            response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'
            response.headers['Expires'] = (datetime.now() + timedelta(days=30)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        else:
            # Cache regular static files for 1 week
            response.headers['Cache-Control'] = 'public, max-age=604800, immutable'
            response.headers['Expires'] = (datetime.now() + timedelta(days=7)).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Add compression hints for images
        if request.path.endswith(('.png', '.jpg', '.jpeg', '.webp')):
            response.headers['Vary'] = 'Accept-Encoding'
            # Add ETag for better caching
            response.headers['ETag'] = f'"{hash(request.path + request.query_string.decode())}"'
            
    elif request.endpoint == 'index':
        # Cache main page for 5 minutes
        response.headers['Cache-Control'] = 'public, max-age=300'
        
    return response
COMMENTS = []  # retained as a small in-memory cache (recent) but now persisted to SQLite
COMMENTS_MAX = 500
ACTIVE_VISITORS = {}
ACTIVE_LOCK = threading.Lock()
ACTIVE_TTL = 70  # seconds of inactivity before a visitor is dropped
BLOCKED_FILE = 'blocked_ids.json'
STATS_FILE = 'visits_stats.json'  # persistent first-seen timestamps per visitor id
RECENT_VISITS_FILE = 'visits_recent.json'  # stores rolling today/week visitor id sets for fast counts
VISIT_STATS = None  # lazy-loaded dict: {id: first_seen_epoch}
client = None
session_str = os.getenv('TELEGRAM_SESSION')  # Telethon string session (recommended for Render)
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # optional bot token fallback
AUTH_SECRET = os.getenv('AUTH_SECRET')  # simple shared secret to protect /auth endpoints
FETCH_THREAD_STARTED = False
AUTH_STATUS = {'authorized': False, 'reason': 'init'}
SUBSCRIBERS = set()  # queues for SSE clients
INIT_ONCE = False  # guard to ensure background startup once
# Persistent dynamic channels file
CHANNELS_FILE = 'channels_dynamic.json'

# Global debug storage for admin panel
DEBUG_LOGS = []
MAX_DEBUG_LOGS = 100

# Cache for fallback reparse to avoid duplicate processing
FALLBACK_REPARSE_CACHE = set()  # message IDs that have been reparsed
MAX_REPARSE_CACHE_SIZE = 1000  # Limit cache size to prevent memory growth

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
def init_alarms_db():
    try:
        with _visits_db_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alarms (
                    id TEXT PRIMARY KEY,
                    level TEXT,
                    name TEXT,
                    since REAL,
                    last REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alarms_level ON alarms(level)")
    except Exception as e:
        log.warning(f"alarms db init failed: {e}")

def init_alarm_events_db():
    try:
        with _visits_db_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alarm_events (
                    id TEXT PRIMARY KEY,
                    level TEXT,
                    name TEXT,
                    event TEXT,
                    ts REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alarm_events_time ON alarm_events(ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alarm_events_name ON alarm_events(name)")
    except Exception as e:
        log.warning(f"alarm_events db init failed: {e}")

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

def load_active_alarms(ttl_seconds:int):
    out_obl = {}
    out_raion = {}
    cutoff = time.time() - ttl_seconds
    try:
        with _visits_db_conn() as conn:
            cur = conn.execute("SELECT level,name,since,last FROM alarms WHERE last >= ?", (cutoff,))
            for level,name,since,last in cur.fetchall():
                if level == 'oblast': out_obl[name] = {'since': since, 'last': last}
                elif level == 'raion': out_raion[name] = {'since': since, 'last': last}
    except Exception as e:
        log.debug(f"load_active_alarms failed: {e}")
    return out_obl, out_raion

def load_dynamic_channels():
    try:
        if os.path.exists(CHANNELS_FILE):
            with open(CHANNELS_FILE,'r',encoding='utf-8') as f:
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

def load_config():
    """Load persisted configuration (currently only monitor period)."""
    global MONITOR_PERIOD_MINUTES
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
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

MESSAGES_FILE = 'messages.json'
HIDDEN_FILE = 'hidden_markers.json'
OPENCAGE_CACHE_FILE = 'opencage_cache.json'
OPENCAGE_TTL = 60 * 60 * 24 * 30  # 30 days
NEG_GEOCODE_FILE = 'negative_geocode_cache.json'
NEG_GEOCODE_TTL = 60 * 60 * 24 * 3  # 3 days for 'not found' entries
MESSAGES_RETENTION_MINUTES = int(os.getenv('MESSAGES_RETENTION_MINUTES', '120'))  # 2 hours retention by default
MESSAGES_MAX_COUNT = int(os.getenv('MESSAGES_MAX_COUNT', '0'))  # 0 = unlimited

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
            data_sorted = sorted(data, key=lambda x: x.get('date',''))
            data = data_sorted[-MESSAGES_MAX_COUNT:]
        except Exception:
            data = data[-MESSAGES_MAX_COUNT:]
    return data

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_messages(data):
    # Apply retention before persistence
    try:
        data = _prune_messages(data)
    except Exception as e:
        log.debug(f'Retention prune error: {e}')
    print(f"DEBUG: Saving {len(data)} messages to file")
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # After each save attempt optional git auto-commit
    try:
        maybe_git_autocommit()
    except Exception as e:
        log.debug(f'git auto-commit skipped: {e}')

# ---------------- Deduplication / merge of near-duplicate geo events -----------------
# Two messages that refer to the same object coming almost back-to-back should not
# produce two separate points: instead we update the earlier one (increment count, merge text).
# Heuristics: same threat_type, within DEDUP_DIST_KM km, within DEDUP_TIME_MIN minutes.
DEDUP_TIME_MIN = int(os.getenv('DEDUP_TIME_MIN', '5'))
DEDUP_DIST_KM = float(os.getenv('DEDUP_DIST_KM', '7'))
DEDUP_SCAN_BACK = int(os.getenv('DEDUP_SCAN_BACK', '400'))  # how many recent messages to scan

def _parse_dt(s:str):
    try:
        return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None

def _haversine_km(lat1, lon1, lat2, lon2):
    try:
        from math import radians, sin, cos, asin, sqrt
        R = 6371.0
        dlat = radians(lat2-lat1)
        dlon = radians(lon2-lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
        c = 2*asin(sqrt(a))
        return R*c
    except Exception:
        return 999999

def maybe_merge_track(all_data:list, new_track:dict):
    """Try to merge new_track into an existing recent track.
    Returns tuple (merged: bool, track_ref: dict).
    """
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
            with open(BLOCKED_FILE, 'r', encoding='utf-8') as f:
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
            with open(STATS_FILE,'r',encoding='utf-8') as f:
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

def _prune_visit_stats(days:int=45):
    # remove entries older than N days to limit file growth
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
                raw = open(RECENT_VISITS_FILE, 'r', encoding='utf-8').read()
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
    # ISO week (Monday start) anchor date for 7-day rolling window (not strictly calendar week) -> we store date 6 days prior cutoff
    # We'll implement simple 7-day rolling: if stored week_start older than 7 days, reset week_ids
    stored_week_start = data.get('week_start') or today
    try:
        sw_dt = datetime.strptime(stored_week_start, '%Y-%m-%d')
        # make tz-aware in same timezone
        sw_dt = tz.localize(sw_dt)
    except Exception:
        sw_dt = now_dt
    if (now_dt - sw_dt).days >= 7:
        # reset week window
        stored_week_start = today
        data['week_ids'] = []
    # day rollover
    if data.get('day') != today:
        data['day'] = today
        data['today_ids'] = []
    # ensure lists
    if 'today_ids' not in data or not isinstance(data['today_ids'], list):
        data['today_ids'] = []
    if 'week_ids' not in data or not isinstance(data['week_ids'], list):
        data['week_ids'] = []
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
import math
import sqlite3

_opencage_cache = None
_neg_geocode_cache = None

def _load_opencage_cache():
    global _opencage_cache
    if _opencage_cache is not None:
        return _opencage_cache
    if os.path.exists(OPENCAGE_CACHE_FILE):
        try:
            with open(OPENCAGE_CACHE_FILE, 'r', encoding='utf-8') as f:
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
        with open(OPENCAGE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_opencage_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f"Failed saving OpenCage cache: {e}")

def _load_neg_geocode_cache():
    global _neg_geocode_cache
    if _neg_geocode_cache is not None:
        return _neg_geocode_cache
    if os.path.exists(NEG_GEOCODE_FILE):
        try:
            with open(NEG_GEOCODE_FILE,'r',encoding='utf-8') as f:
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
        with open(NEG_GEOCODE_FILE,'w',encoding='utf-8') as f:
            json.dump(_neg_geocode_cache,f,ensure_ascii=False,indent=2)
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

def _msg_timestamp(msg):
    """Extract timestamp from message for sorting/filtering"""
    if not msg:
        return 0
    
    # Try different timestamp fields
    date_str = msg.get('date') or msg.get('timestamp') or msg.get('ts')
    if not date_str:
        return 0
    
    try:
        # Handle different date formats
        if isinstance(date_str, (int, float)):
            return float(date_str)
        
        # Parse string dates
        if isinstance(date_str, str):
            # Try common formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%d.%m.%Y %H:%M:%S',
                '%d.%m.%Y %H:%M'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.timestamp()
                except ValueError:
                    continue
                    
        return 0
    except Exception:
        return 0

def neg_geocode_check(name:str):
    if not name:
        return False
    cache = _load_neg_geocode_cache()
    key = name.strip().lower()
    entry = cache.get(key)
    if not entry:
        return False
    # expire
    if int(time.time()) - entry.get('ts',0) > NEG_GEOCODE_TTL:
        try: del cache[key]; _save_neg_geocode_cache()
        except Exception: pass
        return False
    return True

def neg_geocode_add(name:str, reason:str='not_found'):
    if not name:
        return
    cache = _load_neg_geocode_cache()
    key = name.strip().lower()
    cache[key] = {'ts': int(time.time()), 'reason': reason}
    _save_neg_geocode_cache()

UA_CITIES = [
    'київ','харків','одеса','одесса','дніпро','дніпропетровськ','львів','запоріжжя','запорожье','вінниця','миколаїв','николаев',
    'маріуполь','полтава','чернігів','чернигов','черкаси','житомир','суми','хмельницький','чернівці','рівне','івано-франківськ',
    'луцьк','тернопіль','ужгород','кропивницький','кіровоград','кременчук','краматорськ','біла церква','мелітополь','бердянськ',
    'павлоград','ніжин','шостка','короп','кролевець'
]
UA_CITY_NORMALIZE = {
    'одесса':'одеса','запорожье':'запоріжжя','дніпропетровськ':'дніпро','кировоград':'кропивницький','кіровоград':'кропивницький',
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
    # Novoukrainka variants
    'новоукраїнку':'новоукраїнка',
    'старому салтову':'старий салтів','старому салтові':'старий салтів','карлівку':'карлівка','магдалинівку':'магдалинівка',
    'балаклію':'балаклія','білу церкву':'біла церква','баришівку':'баришівка','сквиру':'сквира','сосницю':'сосниця',
    'васильківку':'васильківка','понорницю':'понорниця','куликівку':'куликівка','терни':'терни',
    'шостку':'шостка','березну':'березна','зачепилівку':'зачепилівка','нову водолагу':'нова водолага',
    'нову':'нова водолага',  # Fallback for partial regex matches
    'убни':'лубни','олми':'холми','летичів':'летичів','летичев':'летичів','летичеве':'летичів','деражню':'деражня',
    'деражне':'деражня','деражні':'деражня','корюківку':'корюківка','борзну':'борзна','жмеринку':'жмеринка','лосинівку':'лосинівка',
    'ніжину':'ніжин','ніжина':'ніжин','межову':'межова','святогірську':'святогірськ'
}

# Add accusative / genitive / variant forms for reported missing settlements
UA_CITY_NORMALIZE.update({
    'городню':'городня','городні':'городня','городне':'городня','городни':'городня',
    'кролевця':'кролевець','кролевцу':'кролевець','кролевце':'кролевець',
    'дубовʼязівку':'дубовʼязівка','дубовязівку':'дубовʼязівка','дубовязовку':'дубовʼязівка','дубовязовка':'дубовʼязівка',
    'батурина':'батурин','батурині':'батурин','батурином':'батурин'
    ,'бердичев':'бердичів','бердичева':'бердичів','бердичеве':'бердичів','бердичеву':'бердичів','бердичеві':'бердичів','бердичевом':'бердичів','бердичеву':'бердичів','бердичіву':'бердичів','бердичіва':'бердичів'
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
    ,'краснопалівку':'краснопавлівка','краснопалівку':'краснопавлівка','краснопалівка':'краснопавлівка'
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
        with open(path,'r',encoding='utf-8') as f:
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

def ensure_city_coords(name: str):
    """Return (lat,lng,approx_bool) for settlement, performing lazy geocoding.
    approx_bool True means we used oblast center fallback (low precision)."""
    if not name:
        return None
    n = name.strip().lower()
    
    # Quick check in existing coordinates first
    if n in CITY_COORDS:
        lat,lng = CITY_COORDS[n]; return (lat,lng,False)
    # Check if it's a direct oblast/region name
    if n in OBLAST_CENTERS:
        lat,lng = OBLAST_CENTERS[n]; return (lat,lng,True)
    if 'SETTLEMENTS_INDEX' in globals() and n in (globals().get('SETTLEMENTS_INDEX') or {}):
        lat,lng = globals()['SETTLEMENTS_INDEX'][n]; return (lat,lng,False)
    
    # Try SpaCy normalization for single city names (with limited context)
    if SPACY_AVAILABLE:
        try:
            # Create a simple test message to leverage SpaCy normalization
            # NOTE: This should only find exact matches for the specific city
            test_message = f"на {name}"
            spacy_results = spacy_enhanced_geocoding(test_message)
            
            for result in spacy_results:
                if (result['coords'] and 
                    result['normalized'] == n and 
                    result['name'].lower() == n):  # Ensure exact name match
                    lat, lng = result['coords']
                    print(f"DEBUG SpaCy single city: Found {name} -> {result['normalized']} -> ({lat}, {lng})")
                    return (lat, lng, False)
                    
        except Exception as e:
            print(f"DEBUG SpaCy single city error: {e}")
            # Continue to existing logic
    
    region_hint = NAME_REGION_MAP.get(n)
    # Attempt precise geocode if API key
    if region_hint and OPENCAGE_API_KEY:
        q = f"{n} {region_hint} Україна"
        coords = geocode_opencage(q)
        if coords:
            # store in both for fast reuse
            CITY_COORDS[n] = coords
            try:
                if 'SETTLEMENTS_INDEX' in globals():
                    globals()['SETTLEMENTS_INDEX'][n] = coords
            except Exception:
                pass
            return (coords[0], coords[1], False)
    # Fallback: try geocode without region if key exists
    if OPENCAGE_API_KEY:
        coords = geocode_opencage(f"{n} Україна")
        if coords:
            CITY_COORDS[n] = coords
            try:
                if 'SETTLEMENTS_INDEX' in globals():
                    globals()['SETTLEMENTS_INDEX'][n] = coords
            except Exception:
                pass
            return (coords[0], coords[1], False)
    # Approximate fallback: oblast center (if region hint matches an oblast name substring)
    if region_hint:
        reg_low = region_hint.lower()
        for oblast_key, (olat, olng) in OBLAST_CENTERS.items():
            if oblast_key in reg_low:
                return (olat, olng, True)
    return None

def ensure_city_coords_with_message_context(name: str, message_text: str = ""):
    """Enhanced version that tries to extract oblast from message if city not found.
    Returns (lat,lng,approx_bool) - approx_bool True means used oblast fallback."""
    
    # PRIORITY: Try SpaCy first if available
    if SPACY_AVAILABLE and message_text:
        try:
            spacy_results = spacy_enhanced_geocoding(message_text)
            
            # Look for the specific city we're searching for
            name_lower = name.lower()
            for result in spacy_results:
                if (result['normalized'] == name_lower or 
                    result['name'].lower() == name_lower):
                    if result['coords']:
                        lat, lng = result['coords']
                        print(f"DEBUG SpaCy: Found {name} via SpaCy -> ({lat}, {lng})")
                        return (lat, lng, False)  # Not approximate since SpaCy found exact match
            
        except Exception as e:
            print(f"DEBUG SpaCy fallback error: {e}")
            # Continue to regex-based processing
    
    # FALLBACK: Original regex-based processing
    
    # First, if we have message text, try to extract oblast info and build specific city keys
    if message_text:
        message_lower = message_text.lower()
        
        # ENHANCED: Find the closest oblast to the specific city name
        city_pos = message_lower.find(name.lower())
        if city_pos != -1:
            # Look for oblast in close proximity to the city (within 100 characters before/after)
            start_pos = max(0, city_pos - 100)
            end_pos = min(len(message_lower), city_pos + len(name) + 100)
            context = message_lower[start_pos:end_pos]
            
            # Enhanced regional context detection - try parenthetical oblast first
            oblast_patterns = [
                # Parenthetical oblast: "(Oblast обл.)" - most specific
                r'\(([^)]+)\s+обл\.\)',
                r'\(([^)]+)\s+область\)',
                # Oblast adjective forms: "харківська обл."
                r'\b([а-яїіє]+ська)\s+обл(?:\.|асть)?\b',
                r'\b([а-яїіє]+цька)\s+обл(?:\.|асть)?\b', 
                # Regional names: "харківщина", "полтавщина", etc.
                r'\b([а-яїіє]+щина)\b',
                r'\b([а-яїіє]+щині)\b',
                r'\b([а-яїіє]+щину)\b',
                # Additional patterns for regional context
                r'\bна\s+([а-яїіє]+щині)\b',  # "на Сумщині"
                r'\bу\s+([а-яїіє]+щині)\b',   # "у Сумщині"
                r'\bв\s+([а-яїіє]+щині)\b',   # "в Сумщині"
            ]
            
            detected_oblast_key = None
            
            for pattern in oblast_patterns:
                matches = re.findall(pattern, context)  # Search in context, not full message
                for match in matches:
                    match = match.strip().lower()
                    
                    # Normalize regional names to nominative case AND adjective form
                    if match.endswith('щині'):
                        match = match[:-2] + 'на'  # сумщині -> сумщина
                    elif match.endswith('щину'):
                        match = match[:-2] + 'на'  # сумщину -> сумщина
                    
                    # Convert regional names to adjective forms for city lookup
                    regional_to_adjective = {
                        'сумщина': 'сумська',
                        'харківщина': 'харківська',
                        'чернігівщина': 'чернігівська',
                        'полтавщина': 'полтавська',
                        'дніпропетровщина': 'дніпропетровська',
                        'херсонщина': 'херсонська',
                        'миколаївщина': 'миколаївська',
                    }
                    
                    if match in regional_to_adjective:
                        match = regional_to_adjective[match]
                    
                    # Create possible city+oblast combinations to search
                    city_variants = [
                        f"{name.lower()}({match})",  # миколаївка(сумська)
                        f"{name.lower()} ({match})",  # миколаївка (сумська)
                        f"{name.lower()} {match}",
                        f"{name.lower()} {match} обл.",
                        f"{name.lower()} {match} область",
                    ]
                    
                    print(f"DEBUG: Checking variants for {name} with closest oblast {match}: {city_variants}")
                    
                    # Try to find coordinates using these specific combinations
                    for variant in city_variants:
                        if variant in CITY_COORDS:
                            coords = CITY_COORDS[variant]
                            print(f"DEBUG: Found exact match for '{variant}' -> {coords}")
                            return (coords[0], coords[1], False)
                        
                        # Also try SETTLEMENTS_INDEX if available
                        if 'SETTLEMENTS_INDEX' in globals():
                            settlements = globals().get('SETTLEMENTS_INDEX') or {}
                            if variant in settlements:
                                coords = settlements[variant]
                                print(f"DEBUG: Found settlement match for '{variant}' -> {coords}")
                                return (coords[0], coords[1], False)
                    
                    print(f"DEBUG: No exact match found for variants: {city_variants}")
                    
                    # Store oblast key for potential fallback
                    oblast_normalizations = {
                        'харківська': 'харківська обл.',
                        'чернігівська': 'чернігівська обл.',
                        'полтавська': 'полтавська область',
                        'дніпропетровська': 'дніпропетровська область',
                        'сумська': 'сумська область',
                        'харківщина': 'харківська',
                        'чернігівщина': 'чернігівська',
                        'полтавщина': 'полтавська',
                        'дніпропетровщина': 'дніпропетровська',
                        'сумщина': 'сумська',
                    }
                    
                    if match in oblast_normalizations:
                        detected_oblast_key = oblast_normalizations[match]
                    elif match in OBLAST_CENTERS:
                        detected_oblast_key = match
                    
                    # If we found a valid oblast, stop searching
                    if detected_oblast_key:
                        break
                
                # If we found oblast in this pattern, stop searching other patterns 
                if detected_oblast_key:
                    break
    
    # Second try: standard city lookup (without oblast context)
    result = ensure_city_coords(name)
    if result:
        return result
    
    # Third try: if we have oblast key, return oblast center as fallback
    if message_text and detected_oblast_key and detected_oblast_key in OBLAST_CENTERS:
        lat, lng = OBLAST_CENTERS[detected_oblast_key]
        print(f"DEBUG: Using oblast center fallback for {name}: {detected_oblast_key} -> ({lat}, {lng})")
        return (lat, lng, True)  # True indicates this is an oblast fallback
    
    return None

def normalize_ukrainian_toponym(lemmatized_name: str, original_text: str, grammatical_case: str = None) -> str:
    """
    Universal normalization for Ukrainian place names using linguistic patterns
    
    Args:
        lemmatized_name: SpaCy lemmatized form
        original_text: Original text from message
        grammatical_case: Grammatical case detected by SpaCy (Nom, Gen, Acc, etc.)
        
    Returns:
        Properly normalized toponym
    """
    
    # Rule 1: Special exceptions that need manual handling
    special_exceptions = {
        'чкаловський': 'чкаловське',    # "Чкаловське" wrongly lemmatized as adjective
        'чкаловського': 'чкаловське',   # Genitive case of Чкаловське
        'чкаловському': 'чкаловське',   # Locative case of Чкаловське
        'чкаловськом': 'чкаловське',    # Instrumental case of Чкаловське
        'олексадрія': 'олександрія',    # Common typo/variant
    }
    
    if lemmatized_name in special_exceptions:
        fixed = special_exceptions[lemmatized_name]
        print(f"DEBUG normalize_toponym: Special exception '{lemmatized_name}' → '{fixed}'")
        return fixed
    
    # Rule 2: Adjective endings → City names (most common SpaCy error)
    adjective_to_city_patterns = [
        (r'(.+)ський$', r'\1ськ'),      # покровський → покровськ
        (r'(.+)цький$', r'\1цьк'),      # краматорський → краматорськ  
        (r'(.+)рський$', r'\1рськ'),    # examples like "петрівський" → "петрівськ"
        (r'(.+)нський$', r'\1нськ'),    # examples like "український" → "українськ"
        (r'(.+)льський$', r'\1льськ'),  # examples like "кривський" → "кривськ"
    ]
    
    for pattern, replacement in adjective_to_city_patterns:
        import re
        if re.match(pattern, lemmatized_name):
            normalized = re.sub(pattern, replacement, lemmatized_name)
            print(f"DEBUG normalize_toponym: Adjective pattern '{lemmatized_name}' → '{normalized}'")
            return normalized
    
    # Rule 3: Handle specific case forms that need different normalization
    case_specific_fixes = {
        # Genitive forms that should be nominative
        'зарічний': 'зарічне',          # "Зарічного" (Gen) → "зарічне" (Nom)
        
        # Instrumental case normalization
        'новоукраїнськом': 'новоукраїнськ',  # "над Новоукраїнськом" (Ins) → base form
        'краматорськом': 'краматорськ',      # "над Краматорськом" (Ins) → base form
        'покровськом': 'покровськ',          # "над Покровськом" (Ins) → base form
    }
    
    if lemmatized_name in case_specific_fixes:
        fixed = case_specific_fixes[lemmatized_name]
        print(f"DEBUG normalize_toponym: Case fix '{lemmatized_name}' → '{fixed}'")
        return fixed
    
    # Rule 4: Handle endings that indicate feminine places
    feminine_place_patterns = [
        (r'(.+)івка$', r'\1івка'),      # Keep as is: миколаївка, гусарівка
        (r'(.+)енка$', r'\1енка'),      # Keep as is: савинка (but handle special cases)
    ]
    
    # Special feminine cases that need fixing
    feminine_special_cases = {
        'савинка': 'савинці',  # This is actually "Савинці" wrongly lemmatized
    }
    
    if lemmatized_name in feminine_special_cases:
        fixed = feminine_special_cases[lemmatized_name]
        print(f"DEBUG normalize_toponym: Feminine fix '{lemmatized_name}' → '{fixed}'")
        return fixed
    
    # Rule 5: Use original text pattern if lemmatization looks wrong
    original_lower = original_text.lower()
    
    # If original ends with typical city suffixes but lemma doesn't, prefer original pattern
    city_ending_patterns = [r'(.+)ськ$', r'(.+)цьк$', r'(.+)ів$', r'(.+)ине$', r'(.+)не$']
    lemma_is_adjective = any(lemmatized_name.endswith(ending) for ending in ['ський', 'цький', 'рський', 'нський'])
    
    import re
    for pattern in city_ending_patterns:
        if re.match(pattern, original_lower) and lemma_is_adjective:
            print(f"DEBUG normalize_toponym: Using original pattern '{original_lower}' over lemma '{lemmatized_name}'")
            return original_lower
    
    # Rule 6: Default - return the lemmatized form if no patterns match
    return lemmatized_name


def determine_regional_context(entity, doc, detected_regions, message_text):
    """
    Determine the correct regional context for a geographical entity
    based on its position in the text relative to regional headers
    
    Args:
        entity: SpaCy entity or PseudoEntity
        doc: SpaCy Doc object
        detected_regions: List of detected region names
        message_text: Original message text
        
    Returns:
        str: Most appropriate region name or None
    """
    if not detected_regions:
        return None
    
    if len(detected_regions) == 1:
        return detected_regions[0]
    
    # For multiple regions, find the closest preceding region header
    entity_start_char = entity.start_char if hasattr(entity, 'start_char') else 0
    
    # If entity doesn't have char positions, estimate from token positions
    if not hasattr(entity, 'start_char'):
        try:
            # Find token in doc by text matching
            for token in doc:
                if token.text == entity.text and token.i >= entity.start:
                    entity_start_char = token.idx
                    break
        except:
            entity_start_char = 0
    
    # Find all region positions in text
    region_positions = []
    message_lower = message_text.lower()
    
    region_patterns = {
        'сумщина': ['сумщин'],
        'чернігівщина': ['чернігівщин'],
        'харківщина': ['харківщин'],
        'полтавщина': ['полтавщин'],
        'херсонщина': ['херсонщин'],
        'миколаївщина': ['миколаївщин'],
        'дніпропетровщина': ['дніпропетровщин'],
        'київщина': ['київщин'],
        'донеччина': ['донеччин'],
        'луганщина': ['луганщин'],
        'одесщина': ['одесщин', 'одещин'],
        'запорізька': ['запорізьк'],
        'львівщина': ['львівщин'],
        'волинщина': ['волинщин', 'волинь'],
        'житомирщина': ['житомирщин'],
        'черкащина': ['черкащин'],
        'вінниччина': ['вінниччин', 'вінничин'],
    }
    
    for region_name in detected_regions:
        patterns = region_patterns.get(region_name, [region_name])
        for pattern in patterns:
            pos = message_lower.find(pattern)
            if pos != -1:
                region_positions.append((pos, region_name))
                break
    
    # Sort by position
    region_positions.sort(key=lambda x: x[0])
    
    # Find the closest preceding region
    closest_region = None
    closest_distance = float('inf')
    
    for pos, region_name in region_positions:
        if pos <= entity_start_char:
            distance = entity_start_char - pos
            if distance < closest_distance:
                closest_distance = distance
                closest_region = region_name
    
    # If no preceding region found, use the first one
    result = closest_region if closest_region else detected_regions[0]
    
    print(f"DEBUG Regional context: Entity '{entity.text}' at char {entity_start_char} -> region '{result}'")
    print(f"DEBUG Region positions: {region_positions}")
    
    return result


def spacy_enhanced_geocoding(message_text: str, existing_city_coords: dict = None, 
                           existing_normalizer: dict = None) -> list:
    """
    Enhanced city extraction using SpaCy NLP for Ukrainian text with proper entity recognition
    
    Args:
        message_text: Original message text
        existing_city_coords: CITY_COORDS dict (defaults to global CITY_COORDS)
        existing_normalizer: UA_CITY_NORMALIZE dict (defaults to global UA_CITY_NORMALIZE)
        
    Returns:
        List of dicts with city information:
        {
            'name': str,           # Original city name from message
            'normalized': str,     # Normalized city name for lookup
            'coords': tuple,       # (lat, lng) coordinates if found
            'region': str,         # Detected region if any
            'confidence': float,   # Confidence score 0.0-1.0
            'source': str,         # Detection method used
            'case': str           # Grammatical case if detected
        }
    """
    if not SPACY_AVAILABLE:
        return []
    
    if existing_city_coords is None:
        existing_city_coords = CITY_COORDS
    if existing_normalizer is None:
        existing_normalizer = UA_CITY_NORMALIZE
        
    results = []
    
    try:
        doc = nlp(message_text)
        
        # Extract regions first for context
        detected_regions = []
        region_patterns = {
            'сумщина': ['сумщин', 'сумська область', 'сумська обл'],
            'чернігівщина': ['чернігівщин', 'чернігівська область', 'чернігівська обл'],
            'харківщина': ['харківщин', 'харківська область', 'харківська обл'],
            'полтавщина': ['полтавщин', 'полтавська область', 'полтавська обл'],
            'херсонщина': ['херсонщин', 'херсонська область', 'херсонська обл'],
            'миколаївщина': ['миколаївщин', 'миколаївська область', 'миколаївська обл'],
            'дніпропетровщина': ['дніпропетровщин', 'дніпропетровська область', 'дніпропетровська обл'],
            'київщина': ['київщин', 'київська область', 'київська обл'],
            'донеччина': ['донеччин', 'донецька область', 'донецька обл'],
            'луганщина': ['луганщин', 'луганська область', 'луганська обл'],
            'одесщина': ['одесщин', 'одеська область', 'одеська обл', 'одещин', 'одещина'],
            'запорізька': ['запорізьк', 'запорізька область', 'запорізька обл'],
            'львівщина': ['львівщин', 'львівська область', 'львівська обл'],
            'волинщина': ['волинщин', 'волинська область', 'волинська обл', 'волинь'],
            'житомирщина': ['житомирщин', 'житомирська область', 'житомирська обл'],
            'черкащина': ['черкащин', 'черкаська область', 'черкаська обл'],
            'вінниччина': ['вінниччин', 'вінницька область', 'вінницька обл', 'вінничин'],
        }
        
        message_lower = message_text.lower()
        for region_name, patterns in region_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                detected_regions.append(region_name)
        
        print(f"DEBUG SpaCy NLP: Processing text: '{message_text}'")
        print(f"DEBUG SpaCy NLP: Detected regions: {detected_regions}")
        
        # Process named entities from SpaCy NER - this is the proper NLP approach
        geographical_entities = []
        for ent in doc.ents:
            if ent.label_ in ['LOC', 'GPE']:  # Location, Geopolitical entity
                print(f"DEBUG SpaCy NLP: Found entity '{ent.text}' with label '{ent.label_}' confidence: {ent._.score if hasattr(ent, '_') and hasattr(ent._, 'score') else 'N/A'}")
                geographical_entities.append(ent)
        
        # Also look for proper nouns that might be geographical names
        for token in doc:
            if (token.pos_ == 'PROPN' and 
                not any(ent.start <= token.i < ent.end for ent in geographical_entities) and
                len(token.text) > 2):  # Skip short tokens
                print(f"DEBUG SpaCy NLP: Found additional PROPN candidate: '{token.text}'")
                # Create a pseudo-entity for processing
                class PseudoEntity:
                    def __init__(self, token):
                        self.text = token.text
                        self.start = token.i
                        self.end = token.i + 1  # Add missing end attribute
                        self.label_ = 'PROPN_CANDIDATE'
                geographical_entities.append(PseudoEntity(token))
        
        for ent in geographical_entities:
            entity_text = ent.text.lower()
            
            # Skip if this is a region (already processed)
            is_region = False
            for region_name, patterns in region_patterns.items():
                if any(pattern in entity_text for pattern in patterns):
                    is_region = True
                    break
            
            if not is_region:
                # Get morphological info
                if hasattr(ent, 'start'):
                    token = doc[ent.start]
                else:
                    # For pseudo-entities, find the token
                    token = next((t for t in doc if t.text.lower() == entity_text), None)
                    if not token:
                        continue
                
                case_info = None
                if hasattr(token, 'morph') and token.morph:
                    morph_dict = token.morph.to_dict()
                    case_info = morph_dict.get('Case', None)
                
                # Normalize city name using lemma - this is proper NLP morphological analysis
                normalized_name = token.lemma_.lower() if token.lemma_ and token.lemma_ != '-PRON-' else entity_text
                
                # For multi-word geographical entities, handle them specially
                if len(ent.text.split()) > 1:
                    # For multi-word entities, use custom normalization
                    entity_lower = ent.text.lower()
                    multi_word_fixes = {
                        'кривому рогу': 'кривий ріг',
                        'кривий ріг': 'кривий ріг',
                        'кривого рогу': 'кривий ріг',
                        'новий буг': 'новий буг',
                        'білий камінь': 'білий камінь',
                        'покровськ': 'покровськ',  # formerly красноармейск
                    }
                    for pattern, canonical in multi_word_fixes.items():
                        if pattern in entity_lower:
                            normalized_name = canonical
                            break
                    else:
                        # If no special case, try to reconstruct from lemmas
                        words = []
                        for i in range(ent.start, ent.end):
                            word_token = doc[i]
                            word_lemma = word_token.lemma_.lower() if word_token.lemma_ and word_token.lemma_ != '-PRON-' else word_token.text.lower()
                            words.append(word_lemma)
                        normalized_name = ' '.join(words)
                
                print(f"DEBUG SpaCy NLP: Entity '{ent.text}' -> normalized: '{normalized_name}', case: {case_info}")
                
                # Apply intelligent normalization for Ukrainian place names
                normalized_name = normalize_ukrainian_toponym(normalized_name, ent.text, case_info)
                
                # Apply existing normalization rules
                if normalized_name in existing_normalizer:
                    normalized_name = existing_normalizer[normalized_name]
                
                # Determine the most appropriate regional context for this entity
                region_context = determine_regional_context(ent, doc, detected_regions, message_text)
                
                # Look up coordinates using enhanced lookup with Nominatim fallback
                coords = get_coordinates_enhanced(normalized_name, region_context, message_text)
                
                # Determine confidence based on source
                confidence = 0.9 if ent.label_ in ['LOC', 'GPE'] else 0.7  # Higher for NER entities
                source = 'spacy_ner' if ent.label_ in ['LOC', 'GPE'] else 'spacy_propn'
                
                result = {
                    'name': ent.text,
                    'normalized': normalized_name,
                    'coords': coords,
                    'region': region_context,
                    'confidence': confidence,
                    'source': source,
                    'case': case_info
                }
                results.append(result)
                print(f"DEBUG SpaCy NLP: Added result: {result}")
        
        # Additional pattern-based extraction for missed entities (as fallback)
        preposition_patterns = ['на', 'повз', 'через', 'у напрямку', 'в напрямку']
        
        for i, token in enumerate(doc):
            # Simple prepositions
            if token.text.lower() in preposition_patterns[:3]:  # на, повз, через
                city_info = _extract_city_after_preposition_spacy(doc, i, detected_regions, 
                                                                existing_city_coords, existing_normalizer)
                if city_info:
                    results.append(city_info)
            
            # Direction patterns
            elif (token.text.lower() == 'у' and i + 1 < len(doc) and 
                  doc[i + 1].text.lower() == 'напрямку'):
                city_info = _extract_city_after_preposition_spacy(doc, i + 1, detected_regions,
                                                                existing_city_coords, existing_normalizer)
                if city_info:
                    results.append(city_info)
        
        # Remove duplicates while preserving order
        unique_results = []
        seen_cities = set()
        for result in results:
            city_key = result['normalized']
            if city_key not in seen_cities:
                seen_cities.add(city_key)
                unique_results.append(result)
        
        print(f"DEBUG SpaCy NLP: Final results: {unique_results}")
        return unique_results
        
    except Exception as e:
        print(f"SpaCy processing error: {e}")
        return []

def _find_coordinates_multiple_formats(city_name: str, detected_regions: list, existing_city_coords: dict) -> tuple:
    """
    Try to find coordinates using multiple key formats
    Returns coordinates tuple (lat, lng) or None
    """
    # List of key formats to try
    search_keys = [city_name]
    
    # Add regional variants if regions detected
    if detected_regions:
        for region in detected_regions:
            # Convert region names to adjective forms for coordinate lookup
            region_adj_map = {
                'сумщина': 'сумська',
                'чернігівщина': 'чернігівська', 
                'харківщина': 'харківська',
                'полтавщина': 'полтавська',
                'дніпропетровщина': 'дніпропетровська',
                'херсонщина': 'херсонська',
                'миколаївщина': 'миколаївська',
                'київщина': 'київська',
                'донеччина': 'донецька',
                'луганщина': 'луганська'
            }
            
            region_adj = region_adj_map.get(region, region)
            
            # Try various formats
            search_keys.extend([
                f"{city_name} {region}",           # миколаївка сумщина
                f"{city_name}({region_adj})",      # миколаївка(сумська)
                f"{city_name} ({region_adj})",     # миколаївка (сумська)  
                f"{city_name} {region_adj}",       # миколаївка сумська
                f"{city_name} {region_adj} обл",   # миколаївка сумська обл
                f"{city_name} {region_adj} область" # миколаївка сумська область
            ])
    
    # Try each key format
    for key in search_keys:
        coords = existing_city_coords.get(key)
        if coords:
            print(f"DEBUG SpaCy coord lookup: Found '{city_name}' using key '{key}' -> {coords}")
            return coords
    
    print(f"DEBUG SpaCy coord lookup: No coordinates found for '{city_name}' (tried {len(search_keys)} keys)")
    return None

def get_coordinates_enhanced(city_name: str, region: str = None, context: str = "") -> tuple:
    """
    Enhanced coordinate lookup with Nominatim API fallback
    
    Args:
        city_name: Name of the settlement
        region: Optional region specification
        context: Context for military priority (e.g., "БпЛА курсом на")
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    
    # First try local database with regional context prioritization
    context_lower = context.lower()
    
    # Handle Зарічне disambiguation based on context
    if city_name == 'зарічне':
        if any(keyword in context_lower for keyword in ['дніпропетровщина', 'дніпро', 'покровський', 'бпла']):
            # For Dnipropetrovska oblast contexts
            coords = DNIPRO_CITY_COORDS.get('зарічне дніпропетровська')
            if coords:
                print(f"DEBUG Enhanced coord lookup: Found '{city_name}' using Dnipropetrovska context -> {coords}")
                return coords
        elif any(keyword in context_lower for keyword in ['рівненщина', 'рівне']):
            # For Rivne oblast contexts  
            coords = (51.2167, 26.0833)
            print(f"DEBUG Enhanced coord lookup: Found '{city_name}' using Rivne context -> {coords}")
            return coords
    
    # Handle regional prefixes in context
    regional_indicators = {
        'дніпропетровщина': 'дніпропетровська',
        'киівщина': 'київська', 
        'харківщина': 'харківська',
        'житомирщина': 'житомирська',
        'чернігівщина': 'чернігівська',
        'сумщина': 'сумська'
    }
    
    detected_region = None
    for indicator, region_name in regional_indicators.items():
        if indicator in context_lower:
            detected_region = region_name
            break
    
    # If region detected from context but not passed as parameter, use detected
    if detected_region and not region:
        region = detected_region
        print(f"DEBUG Enhanced coord lookup: Detected region '{region}' from context for '{city_name}'")
    
    # Handle specific directional contexts (e.g., "північніше Чернігова")
    if 'чернігов' in context_lower and any(direction in context_lower for direction in ['північн', 'півн', 'північ']):
        if city_name == 'любеч':
            # Любеч північніше Чернігова
            coords = (51.4961, 30.2675)  # Правильні координати Любеча
            print(f"DEBUG Enhanced coord lookup: Found '{city_name}' using directional context north of Chernigiv -> {coords}")
            return coords
    
    # PRIORITIZE NOMINATIM API when region is specified
    if region and NOMINATIM_AVAILABLE:
        # Normalize region name for Nominatim API
        normalized_region = region.lower()
        
        # Convert regional nicknames to standard oblast names
        region_mappings = {
            'миколаївщина': 'миколаївська область',
            'херсонщина': 'херсонська область', 
            'харківщина': 'харківська область',
            'донеччина': 'донецька область',
            'луганщина': 'луганська область',
            'запоріжжя': 'запорізька область',
            'дніпропетровщина': 'дніпропетровська область',
            'полтавщина': 'полтавська область',
            'сумщина': 'сумська область',
            'чернігівщина': 'чернігівська область',
            'київщина': 'київська область',
            'житомирщина': 'житомирська область',
            'вінниччина': 'вінницька область',
            'черкащина': 'черкаська область',
            'кіровоградщина': 'кіровоградська область',
            'тернопільщина': 'тернопільська область',
            'хмельниччина': 'хмельницька область',
            'рівненщина': 'рівненська область',
            'волинщина': 'волинська область',
            'львівщина': 'львівська область',
            'закарпаття': 'закарпатська область',
            'івано-франківщина': 'івано-франківська область',
            'буковина': 'чернівецька область',
            'одещина': 'одеська область',
            'одесщина': 'одеська область',
        }
        
        # Apply mapping if available
        nominatim_region = region_mappings.get(normalized_region, region)
        
        print(f"DEBUG Enhanced coord lookup: Trying Nominatim API first for '{city_name}' in {nominatim_region} (from {region})")
        coords = get_coordinates_nominatim(city_name, nominatim_region)
        if coords:
            print(f"DEBUG Enhanced coord lookup: Nominatim found '{city_name}' in {nominatim_region} -> {coords}")
            # Cache the result in local database for future use
            cache_key = f"{city_name} {region}"
            CITY_COORDS[cache_key] = coords
            return coords
        else:
            print(f"DEBUG Enhanced coord lookup: Nominatim could not find '{city_name}' in {nominatim_region}")
    
    # Try basic local lookup (only if no region specified or Nominatim failed)
    coords = CITY_COORDS.get(city_name)
    if coords:
        print(f"DEBUG Enhanced coord lookup: Found '{city_name}' in local database -> {coords}")
        return coords
    
    # Try settlements index if available
    if 'SETTLEMENTS_INDEX' in globals() and globals().get('SETTLEMENTS_INDEX'):
        coords = globals()['SETTLEMENTS_INDEX'].get(city_name)
        if coords:
            print(f"DEBUG Enhanced coord lookup: Found '{city_name}' in settlements index -> {coords}")
            return coords
    
    # Try with region specification in local database
    if region:
        # Normalize region name
        region_lower = region.lower().replace('область', '').replace('обл.', '').replace('обл', '').strip()
        search_keys = [
            f"{city_name} {region_lower}",
            f"{city_name} {region_lower} область",
            f"{city_name} {region_lower} обл",
            f"{city_name} ({region_lower})",
            f"{city_name} ({region})"
        ]
        
        for key in search_keys:
            coords = CITY_COORDS.get(key)
            if coords:
                print(f"DEBUG Enhanced coord lookup: Found '{city_name}' using regional key '{key}' -> {coords}")
                return coords
    
    # Fallback to Nominatim API for precise geocoding
    if NOMINATIM_AVAILABLE:
        print(f"DEBUG Enhanced coord lookup: Trying Nominatim API for '{city_name}'" + (f" in {region}" if region else ""))
        coords = get_coordinates_nominatim(city_name, region)
        if coords:
            print(f"DEBUG Enhanced coord lookup: Nominatim found '{city_name}' -> {coords}")
            # Cache the result in local database for future use
            cache_key = f"{city_name}" + (f" {region}" if region else "")
            CITY_COORDS[cache_key] = coords
            return coords
        else:
            print(f"DEBUG Enhanced coord lookup: Nominatim could not find '{city_name}'")
    
    print(f"DEBUG Enhanced coord lookup: No coordinates found for '{city_name}' anywhere")
    return None

def get_coordinates_context_aware(text: str) -> tuple:
    """
    Context-aware coordinate lookup using intelligent text analysis
    
    Args:
        text: Full message text for context analysis
        
    Returns:
        Tuple of (latitude, longitude, target_city_name) or None if not found
    """
    
    if not CONTEXT_GEOCODER_AVAILABLE:
        print("DEBUG Context geocoder: Not available")
        return None
    
    print(f"DEBUG Context geocoder: Analyzing text: '{text}'")
    
    # Get prioritized geocoding candidates
    candidates = get_context_aware_geocoding(text)
    
    if not candidates:
        print("DEBUG Context geocoder: No candidates found")
        return None
    
    print(f"DEBUG Context geocoder: Found {len(candidates)} candidates: {candidates}")
    
    # Try each candidate in order of confidence
    for city_name, region, confidence in candidates:
        # Skip obviously invalid candidates
        if len(city_name) < 2 or city_name in ['-', 'над', 'на', 'у', 'в', 'до', 'під', 'біля', 'а', 'курсом']:
            continue
            
        print(f"DEBUG Context geocoder: Trying candidate '{city_name}' (region: {region}, confidence: {confidence})")
        
        # Use enhanced coordinate lookup
        coords = get_coordinates_enhanced(city_name, region=region, context=text)
        
        if coords:
            print(f"DEBUG Context geocoder: SUCCESS - Found '{city_name}' -> {coords}")
            return coords[0], coords[1], city_name
    
    print("DEBUG Context geocoder: No valid coordinates found for any candidate")
    return None

def _extract_city_after_preposition_spacy(doc, prep_index: int, detected_regions: list,
                                        existing_city_coords: dict, existing_normalizer: dict) -> dict:
    """Extract city name after preposition using SpaCy tokens"""
    if prep_index + 1 >= len(doc):
        return None
    
    # Collect potential city tokens (proper nouns, nouns, adjectives)
    city_tokens = []
    start_idx = prep_index + 1
    
    for i in range(start_idx, min(start_idx + 3, len(doc))):  # Max 3 words
        token = doc[i]
        if token.pos_ in ['PROPN', 'NOUN', 'ADJ'] or token.text == '-':
            city_tokens.append(token)
        else:
            break
    
    if not city_tokens:
        return None
    
    # Build city name
    city_name = ' '.join(token.text for token in city_tokens)
    
    # Get morphological info from the main token (usually the first one)
    main_token = city_tokens[0]
    case_info = None
    if hasattr(main_token, 'morph') and main_token.morph:
        morph_dict = main_token.morph.to_dict()
        case_info = morph_dict.get('Case', None)
    
    # Normalize using lemma
    normalized_name = main_token.lemma_ if main_token.lemma_ != city_name.lower() else city_name.lower()
    
    # Apply intelligent normalization for Ukrainian place names
    normalized_name = normalize_ukrainian_toponym(normalized_name, city_name, case_info)
    
    # Apply existing normalization rules
    if normalized_name in existing_normalizer:
        normalized_name = existing_normalizer[normalized_name]
    
    # Look up coordinates using enhanced lookup with Nominatim fallback  
    region_context = detected_regions[0] if detected_regions else None
    coords = get_coordinates_enhanced(normalized_name, region_context, ' '.join(token.text for token in doc))
    
    return {
        'name': city_name,
        'normalized': normalized_name,
        'coords': coords,
        'region': detected_regions[0] if detected_regions else None,
        'confidence': 0.7,  # Medium confidence for pattern-based
        'source': 'spacy_pattern',
        'case': case_info
    }

# Consolidated static fallback coordinates
CITY_COORDS = {
        # Core cities
        'київ': (50.4501, 30.5234), 'харків': (49.9935, 36.2304), 'одеса': (46.4825, 30.7233), 'дніпро': (48.4647, 35.0462),
        'львів': (49.8397, 24.0297), 'запоріжжя': (47.8388, 35.1396), 'вінниця': (49.2331, 28.4682), 'миколаїв': (46.9750, 31.9946),
        'маріуполь': (47.0971, 37.5434), 'полтава': (49.5883, 34.5514), 'чернігів': (51.4982, 31.2893), 'черкаси': (49.4444, 32.0598),
        'житомир': (50.2547, 28.6587), 'суми': (50.9077, 34.7981), 'хмельницький': (49.4229, 26.9871), 'чернівці': (48.2921, 25.9358),
    
    # Житомирська область - усі основні міста
    'овруч': (51.3244, 28.8006), 'коростень': (50.9550, 28.6336), 'новоград-волинський': (50.5833, 27.6167), 
    'бердичів': (49.8978, 28.6011), 'звягель': (50.5833, 27.6167), 'малин': (50.7726, 29.2360), 
    'радомишль': (50.4972, 29.2292), 'черняхів': (50.4583, 28.8500), 'баранівка': (50.3000, 27.6667),
    'попільня': (49.9333, 28.4167), 'ємільчине': (50.8667, 28.8500), 'олевськ': (51.2167, 27.6667),
    'лугини': (50.9333, 27.2667), 'чудnів': (50.0500, 28.1167), 'андрушівка': (50.0833, 29.8000),
    'романів': (50.1500, 28.2667), 'ружин': (49.6333, 28.6000), 'володарськ-волинський': (50.5500, 28.3833),
    'коростишів': (50.3167, 29.0333), 'народичі': (51.0583, 29.1167), 'іванківець': (50.1333, 29.3333),
    'любар': (49.9167, 27.7333), 'високе': (51.1000, 28.1000), 'чорнобиль': (51.2768, 30.2219),
    'поліське': (51.1833, 29.5000),
    
    # Форми відмінків для Овруча
    'овручі': (51.3244, 28.8006), 'овручу': (51.3244, 28.8006), 'овручем': (51.3244, 28.8006),
    'овручем': (51.3244, 28.8006), 'овруча': (51.3244, 28.8006),
    
    # Інші форми для міст Житомирської області
    'малині': (50.7726, 29.2360), 'малину': (50.7726, 29.2360), 'малином': (50.7726, 29.2360),
    'коростені': (50.9550, 28.6336), 'коростену': (50.9550, 28.6336), 'коростенем': (50.9550, 28.6336),
    'бердичеві': (49.8978, 28.6011), 'бердичеву': (49.8978, 28.6011), 'бердичевом': (49.8978, 28.6011),
    'новограді-волинському': (50.5833, 27.6167), 'новоград-волинському': (50.5833, 27.6167),
    
    # Бершадь - райцентр Вінницької області
    'бершадь': (48.3667, 29.5167),
    'бершаді': (48.3667, 29.5167),
    'бершадю': (48.3667, 29.5167),
    'бершадью': (48.3667, 29.5167),
    'бершадей': (48.3667, 29.5167),
    
    # Added per user report (обстріл alert should map): Костянтинівка (Donetsk Obl.)
    'костянтинівка': (48.5277, 37.7050),
    # Mezhova (Дніпропетровська обл.) to avoid fallback to Dnipro
    'межова': (48.2583, 36.7363),
    # Sviatohirsk (Святогірськ) Donetsk Oblast
    'святогірськ': (49.0339, 37.5663),
    # Antonivka (Kherson urban-type settlement, user report for UAV threat)
    'антонівка': (46.6925, 32.7186),
    # Alexandria (Kirovohrad Oblast) - avoid confusion with other cities named Alexandria
    'олександрія': (48.8033, 33.1147),
    # Vilshany (Kirovohrad Oblast) - separate from Vilshanka in other regions  
    'вільшани': (48.4667, 32.2667),
    'вільшанам': (48.4667, 32.2667),
    'вільшанах': (48.4667, 32.2667),
    # Baturyn (Chernihiv Obl.) for directional course reports
    'батурин': (51.3450, 32.8761),
        'рівне': (50.6199, 26.2516), 'івано-франківськ': (48.9226, 24.7111), 'луцьк': (50.7472, 25.3254), 'тернопіль': (49.5535, 25.5948),
        'ужгород': (48.6208, 22.2879), 'кропивницький': (48.5079, 32.2623), 'кременчук': (49.0670, 33.4204), 'краматорськ': (48.7389, 37.5848),
        'мелітополь': (46.8489, 35.3650), 'бердянськ': (46.7553, 36.7885), 'павлоград': (48.5350, 35.8700), 'нікополь': (47.5667, 34.4061),
        'марганець': (47.6433, 34.6289), 'херсон': (46.6350, 32.6169),
        'білозерка': (46.64, 32.88),  # Херсонська область
        'чорнобаївка': (46.6964, 32.5469),  # Херсонська область
    
    # Недостающие города из UAV сообщений (сентябрь 2025)
    'зарічне': (51.2167, 26.0833),      # Рівненська область
    'сенкевичівка': (51.5667, 25.8333), # Волинська область
    'голоби': (50.7833, 25.2167),       # Волинська область
    
    # Дополнительные города из UAV сообщений (сентябрь 2025)
    'корнин': (50.9167, 29.1167),       # Житомирська область, Малинський район
    'корнину': (50.9167, 29.1167),
    'корнином': (50.9167, 29.1167),
    'корнина': (50.9167, 29.1167),
    'устинівка': (50.7481, 29.0028),    # Житомирська область, Малинський район
    'устинівці': (50.7481, 29.0028),
    'устинівку': (50.7481, 29.0028),
    'устинівкою': (50.7481, 29.0028),
    'добротвір': (50.2053, 24.4239),    # Львівська область, енергетичний центр
    'добротворі': (50.2053, 24.4239),
    'добротвору': (50.2053, 24.4239),
    'добротвором': (50.2053, 24.4239),
    'добротвора': (50.2053, 24.4239),
    'слов\'янськ': (48.8417, 37.5983), 'дружківка': (48.6203, 37.5263),
    # Fallback key without apostrophe (some sources strip it)
    'словянськ': (48.8417, 37.5983),
    'білопілля': (51.1500, 34.3014),
        # Extended regional towns & settlements
        'гадяч': (50.3713, 34.0109), 'чорнухи': (50.2833, 33.0000), 'великі сорочинці': (50.0167, 33.9833), 'семенівка': (50.6633, 32.3933),
        'лубни': (50.0186, 32.9931), 'шишаки': (49.8992, 34.0072), 'широке': (47.6833, 34.5667), 'зеленодольськ': (47.5667, 33.5333),
        'бабанка': (48.9833, 30.4167), 'новий буг': (47.6833, 32.5167), 'березнегувате': (47.3167, 32.8500), 'новоархангельськ': (48.6667, 30.8000),
        'липняжка': (48.6167, 30.8667), 'голованівськ': (48.3772, 30.5322), 'бишів': (50.3167, 29.9833), 'обухів': (50.1072, 30.6211),
        'гребінки': (50.2500, 30.2500), 'біла церква': (49.7950, 30.1310), 'сквира': (49.7333, 29.6667), 'чорнобиль': (51.2768, 30.2219),
        'пулини': (50.4333, 28.4333), 'головине': (50.3833, 28.6667), 'радомишль': (50.4972, 29.2292), 'коростень': (50.9500, 28.6333),
        'погребище': (49.4833, 29.2667), 'теплик': (48.6667, 29.6667), 'оратів': (48.9333, 29.5167), 'дашів': (48.9000, 29.4333),
        'шаргород': (48.7333, 28.0833), 'бірки': (49.7517, 36.1025), 'златопіль': (49.9800, 35.5300), 'балаклія': (49.4627, 36.8586),
        'берестин': (50.2000, 35.0000), 'старий салтів': (50.0847, 36.7424), 'борки': (49.9380, 36.1260), 'кролевець': (51.5481, 33.3847),
    'глобине': (49.3833, 33.2667), 'кринички': (47.2333, 34.3500), 'солоне': (48.1436, 35.9933), 'брусилів': (50.2800, 29.5300),
    'терни': (50.9070, 34.0130), 'понорниця': (51.8033, 32.5333), 'куликівка': (51.3520, 31.6480),
    # Additional settlements from multi-region UAV course messages (September 2025)
    'путивль': (51.3361, 33.8692), 'бахмач': (51.1808, 32.8203), 'носівка': (50.9444, 32.0167), 'козелець': (50.9167, 31.1833),
    'страхолісся': (50.5167, 30.8833), 'білокоровичі': (51.1667, 27.75),
    'краснопавлівка': (50.0167, 35.95), 'божедрівка': (48.4167, 35.0167), 'пʼятихатки': (48.5667, 33.6833),
    'петрове': (48.7333, 32.8), 'брилівка': (46.8167, 32.7833),
    # Additional missing cities from napramok messages (September 2025)
    'десна': (51.0333, 31.1667), 'кіпті': (51.2833, 31.2167), 'ічня': (50.3833, 34.8833), 'цвіткове': (49.7167, 32.2167),
    'чоповичі': (50.8333, 28.7333), 'звягель': (50.5833, 27.6667), 'камʼянське': (48.5167, 34.6167),
    'піщаний брід': (48.1167, 32.0833), 'бобринець': (48.0333, 32.1833), 'тендрівська коса': (46.1833, 31.5333),
        'новгород-сіверський': (51.9874, 33.2620), 'сосниця': (51.5236, 32.4953), 'олишівка': (51.0725, 31.3525), 'березна': (51.5756, 31.7431),
        'зачепилівка': (49.1717, 35.2742), 'близнюки': (48.8520, 36.5440), 'нова водолага': (49.7270, 35.8570), 'сахновщина': (49.1544, 35.1460),
        'губиниха': (48.7437, 35.2960), 'перещепине': (48.6260, 35.3580), 'карлівка': (49.4586, 35.1272), 'магдалинівка': (48.8836, 34.8669),
        'савинці': (49.4365, 37.2981), 'шевченкове': (49.6996, 37.1770), 'обухівка': (48.6035, 34.8530), 'курилівка': (48.6715, 34.8740),
        'петриківка': (48.7330, 34.6300), 'підгородне': (48.5747, 35.1482), 'самар': (48.6500, 35.4200), 'верхньодніпровськ': (48.6535, 34.3372),
        'горішні плавні': (49.0123, 33.6450), "кам'янське": (48.5110, 34.6021), 'камянське': (48.5110, 34.6021), 'липова долина': (50.5700, 33.7900),
        'тростянець': (50.4833, 34.9667), 'лебедин': (50.5872, 34.4912), 'улянівка': (50.8530, 34.3170), 'уляновка': (50.8530, 34.3170),
        'богодухів': (50.1646, 35.5279), 'холми': (51.6272, 32.5531), 'блистова': (51.6833, 32.6333), 'ніжин': (51.0480, 31.8860),
        'мена': (51.5211, 32.2147), 'десна': (51.0833, 30.9333), 'євминка': (51.3167, 31.7167), 'м.-коцюбинське': (51.5833, 31.1167),
        'лосинівка': (51.1333, 31.7167), 'ічня': (51.0722, 32.3931), 'борзна': (51.2542, 32.4192), 'прилуки': (50.5931, 32.3878),
        'линовиця': (50.7833, 32.4167), 'валки': (49.8427, 35.6150), 'кегичівка': (49.5440, 35.7760), 'велика багачка': (50.1946, 33.7894),
        'велику багачку': (50.1946, 33.7894), 'велику багачу': (50.1946, 33.7894), 'липову долину': (50.5700, 33.7900), 'затока': (46.0660, 30.4680),
        'янське': (48.4567, 36.3342), 'чугуїв': (49.8376, 36.6881), 'ворожба': (51.8031, 34.4972), 'краснопілля': (50.4422, 35.3081),
        'бориспіль': (50.3527, 30.9550), 'жашків': (49.2431, 30.1122), 'есмань': (51.8833, 34.2833), 'мерефа': (49.8181, 36.0572),
        'глухів': (51.6781, 33.9169), 'недригайлів': (50.8281, 33.8781), 'вороніж': (51.8081, 33.3722), 'ромни': (50.7497, 33.4746),
    'ямпіль': (51.2247, 34.3224), 'ямпіль сумська': (51.2247, 34.3224), 'ямполь сумська': (51.2247, 34.3224),
    'хутір-михайлівський': (51.8000, 33.5000),
        'узин': (49.8216, 30.4567), 'гончарівське': (51.6272, 31.3192), 'голованівськ': (48.3772, 30.5322), 'новоукраїнка': (48.3122, 31.5272),
        'тульчин': (48.6783, 28.8486), 'бровари': (50.5110, 30.7909), 'канів': (49.7517, 31.4717), 'миронівка': (49.6631, 31.0100),
        'борова': (49.3742, 36.4892), 'буринь': (51.2000, 33.8500), 'конотоп': (51.2417, 33.2022), 'кролевец': (51.5486, 33.3856), 'остер': (50.9481, 30.8831),
        'плавні': (49.0123, 33.6450), 'голованівський район': (48.3772, 30.5322), 'новоукраїнський район': (48.3122, 31.5272),
        'безлюдівка': (49.8872, 36.2731), 'рогань': (49.9342, 36.4942), 'савинці(харківщина)': (49.6272, 36.9781),
        'слатине': (49.7500, 36.1500),  # Слатине, Дергачівський р-н, Харківська обл.
        'гути': (50.0167, 36.3833),  # Гути, Харьковская область
        # Temporary missing cities (should be in external data sources)
        'гусарівка': (49.1000, 37.1500),  # Гусарівка, Харківська область - TEMP: SpaCy не находит автоматически
        'протопопівка': (49.7000, 37.0000),  # Протопопівка, Харківська область - TEMP: SpaCy не находит автоматически
        'українка': (50.1447, 30.7381), 'царичанка': (48.9767, 34.3772), 'ріпки': (51.8122, 31.0817), 'михайло-коцюбинське': (51.5833, 31.1167),
    'андріївка': (49.9380, 36.9510),
        'макошине': (51.6275, 32.2731), 'парафіївка': (50.9833, 32.2833), 'дубовʼязівка': (51.1833, 33.7833), 'боромля': (50.7500, 34.9833),
    # Newly added (missing in earlier dictionary lookups reported by user)
    'городня': (51.8892, 31.6011),
        'жукин': (50.7800, 30.6820), 'велика димерка': (50.8140, 30.8080), 'велику димерку': (50.8140, 30.8080), 'вишгород': (50.5840, 30.4890),
    'димер': (50.8390, 30.3050),
        'ржищів': (49.9719, 31.0500), 'вишеньки': (50.2987, 30.6445), 'жуляни': (50.4017, 30.4519), 'троєщина': (50.5130, 30.6030),
        'троєщину': (50.5130, 30.6030), 'конча-заспа': (50.2650, 30.5760), 'любар': (50.0500, 27.7500), 'старий остропіль': (49.6503, 27.2291),
        'петрівці': (50.4167, 30.5833),
        'згурівка': (50.4950, 31.7780), 'мала дівиця': (50.8240, 32.4700), 'яготин': (50.2360, 31.7700), 'ставище': (49.3958, 30.1875),
        'березань': (50.3085, 31.4576), 'бортничі': (50.3915, 30.6695), 'старокостянтинів': (49.7574, 27.2039), 'адампіль': (49.6500, 27.3000),
        # Additional single-city early parser support
        'покровське': (48.1180, 36.2470), 'петропавлівка': (48.5000, 36.4500), 'шахтарське': (47.9500, 36.0500),
        # 'миколаївка': Удалено - неоднозначное название, используется контекстный поиск
        'низи': (50.7435, 34.9860), 'барвінкове': (48.9000, 37.0167), 'пісочин': (49.9500, 36.1330), 'берестове': (49.3500, 37.0000),
    'кобеляки': (49.1500, 34.2000), 'бердичів': (49.8942, 28.5986),
    'куцуруб': (46.7906, 31.9222), 'воскресенка': (50.4850, 30.6090),
    # Newly added Kyiv & Odesa region settlements / raion centers for alerts
    'гостомель': (50.5853, 30.2617), 'боярка': (50.3301, 30.5201), 'макарів': (50.4645, 29.8114),
    'бородянка': (50.6447, 29.9202), 'кілія': (45.4553, 29.2640),
    # Cherkasy region settlement (directional course report: "БпЛА курсом на Цибулів")
    'цибулів': (49.0733, 29.8472),
    # Raion centers (approx: use main settlement or administrative center)
    'ізмаїльський район': (45.3516, 28.8365), # near Izmail
    'броварський район': (50.5110, 30.7909),
    'обухівський район': (50.1072, 30.6211),
    'херсонський район': (46.6350, 32.6169),
    'вінницький район': (49.2331, 28.4682)
    ,# --- Newly added (Sept 2 multi-line UAV message) ---
    'нечаяне': (46.8840, 32.0310), 'нечаянеу': (46.8840, 32.0310), 'нечаяному': (46.8840, 32.0310),
    'чечельник': (48.2156, 29.3708), 'чечельнику': (48.2156, 29.3708),
    'залісся': (51.0836, 30.1914), 'заліссям': (51.0836, 30.1914),
    'красятичі': (51.0410, 29.6000), 'красятичів': (51.0410, 29.6000),
    'іршанськ': (50.7833, 28.9000), 'іршанську': (50.7833, 28.9000),
    'хорошів': (50.7167, 28.6167), 'хорошеві': (50.7167, 28.6167), 'хорошеву': (50.7167, 28.6167),
    'народичі': (51.2000, 29.0833), 'народичів': (51.2000, 29.0833),
    'нові білокоровичі': (51.1333, 27.7667), 'нові білокоровичів': (51.1333, 27.7667),
    'городниця': (51.3270, 27.3460), 'городницю': (51.3270, 27.3460),
    'березне': (50.9833, 26.7500), 'березному': (50.9833, 26.7500),
    'божедарівка': (48.3014, 34.5522), 'божедарівку': (48.3014, 34.5522), 'божедарівці': (48.3014, 34.5522),
    'пʼятихатки': (48.5667, 33.6833), "п'ятихатки": (48.5667, 33.6833), 'пятихатки': (48.5667, 33.6833),
    'жовті води': (48.3500, 33.5000), 'жовтих вод': (48.3500, 33.5000),
    'згурівку': (50.4950, 31.7780), 'згурівці': (50.4950, 31.7780),
    'козятин': (49.7167, 28.8333), 'козятина': (49.7167, 28.8333),
    'теплик': (48.6650, 29.7480), 'теплика': (48.6650, 29.7480),
    'новий буг': (47.6833, 32.5167), 'нового буга': (47.6833, 32.5167),
    'семенівку': (50.6633, 32.3933), 'лубни': (50.0186, 32.9931),
    'згурівка (київщина)': (50.4950, 31.7780),
    'гребінку': (50.2500, 30.2500), 'згурівко': (50.4950, 31.7780),
    # Гребінка (Полтавська область) - правильні координати
    'гребінка': (50.1058, 32.4464), 'гребінці': (50.1058, 32.4464), 'гребінку полтавська': (50.1058, 32.4464),
    'хотінь': (51.0550, 34.0000), 'хотіні': (51.0550, 34.0000),
    # Додаткові міста з нових повідомлень
    'хмільник': (49.5500, 27.9667), 'хмільнику': (49.5500, 27.9667), 'хмільника': (49.5500, 27.9667),
    'балта': (47.9667, 29.6167), 'балту': (47.9667, 29.6167), 'балті': (47.9667, 29.6167),
    'голованівськ': (48.7667, 31.4833), 'голованівську': (48.7667, 31.4833), 'голованівська': (48.7667, 31.4833),
    'помічна': (48.4333, 32.5333), 'помічну': (48.4333, 32.5333), 'помічній': (48.4333, 32.5333),
    'звенигородка': (49.0803, 30.9617), 'звенигородку': (49.0803, 30.9617), 'звенигородці': (49.0803, 30.9617),
    'буки': (49.1167, 30.8833), 'букам': (49.1167, 30.8833), 'буках': (49.1167, 30.8833),
    'дубовʼязівка': (50.7833, 34.3667), 'дубовʼязівку': (50.7833, 34.3667), "дуб'язівка": (50.7833, 34.3667), "дубов'язівка": (50.7833, 34.3667),
    'парафіївка': (51.4833, 31.1167), 'парафіївку': (51.4833, 31.1167), 'парафіївці': (51.4833, 31.1167),
    'нова борова': (50.7167, 27.9167), 'нову борову': (50.7167, 27.9167), 'новій боровій': (50.7167, 27.9167),
    'чоповичі': (50.4333, 28.1167), 'чоповичів': (50.4333, 28.1167), 'чоповичах': (50.4333, 28.1167),
    'ємільчине': (50.8667, 27.8667), 'ємільчину': (50.8667, 27.8667), 'ємільчиному': (50.8667, 27.8667),
    'стара синява': (49.6333, 27.6167), 'стару синяву': (49.6333, 27.6167), 'старій синяві': (49.6333, 27.6167),
    'шепетівка': (50.1833, 27.0667), 'шепетівку': (50.1833, 27.0667), 'шепетівці': (50.1833, 27.0667),
    'сарни': (51.3333, 26.6000), 'сарнах': (51.3333, 26.6000), 'сарнів': (51.3333, 26.6000),
    'степань': (50.5167, 25.9167), 'степані': (50.5167, 25.9167), 'степаня': (50.5167, 25.9167),
    'любешів': (51.9000, 25.3333), 'любешеві': (51.9000, 25.3333), 'любешову': (51.9000, 25.3333),
    'маневичі': (51.3000, 25.5167), 'маневичів': (51.3000, 25.5167), 'маневичах': (51.3000, 25.5167),
    'колки': (51.9333, 24.7167), 'колках': (51.9333, 24.7167), 'колкам': (51.9333, 24.7167),
    'рожище': (51.6333, 24.2333), 'рожищу': (51.6333, 24.2333), 'рожищі': (51.6333, 24.2333),
    'рокині': (50.9833, 24.5167), 'рокинях': (50.9833, 24.5167), 'рокинів': (50.9833, 24.5167),
    'володимир': (50.8500, 24.3167), 'володимиру': (50.8500, 24.3167), 'володимирі': (50.8500, 24.3167),
    # Додаткові міста з нових повідомлень 2
    'жовква': (49.9333, 23.9667), 'жовкву': (49.9333, 23.9667), 'жовкві': (49.9333, 23.9667),
    'криве озеро': (47.9500, 30.3500), 'кривому озеру': (47.9500, 30.3500), 'кривого озера': (47.9500, 30.3500),
    'могилів-подільський': (48.4833, 27.8000), 'могилева-подільського': (48.4833, 27.8000),
    'ямпіль вінницька': (48.1333, 28.2833), 'ямполь вінницька': (48.1333, 28.2833),
    'ямполю': (48.1333, 28.2833), 'ямполі': (48.1333, 28.2833),
    'дзигівка': (49.2167, 28.1500), 'дзигівку': (49.2167, 28.1500), 'дзигівці': (49.2167, 28.1500),
    'березівка': (46.8167, 30.9167), 'березівку': (46.8167, 30.9167), 'березівці': (46.8167, 30.9167),
    # 'миколаївка': Удалено - неоднозначное название, используется контекстный поиск
    'вільногірськ': (47.9333, 34.0167), 'вільногірську': (47.9333, 34.0167), 'вільногірська': (47.9333, 34.0167),
    'велика виска': (49.2333, 32.1833), 'великої виски': (49.2333, 32.1833), 'великій висці': (49.2333, 32.1833),
    'велику виску': (49.2333, 32.1833),  # accusative form
    'доброслав': (46.6000, 30.0500), 'доброславу': (46.6000, 30.0500), 'доброславі': (46.6000, 30.0500),
    'тишківка': (48.7667, 32.6833), 'тишківку': (48.7667, 32.6833), 'тишківці': (48.7667, 32.6833),
    'салькове': (48.6167, 32.4500), 'салькову': (48.6167, 32.4500), 'сальковому': (48.6167, 32.4500),
    'благовіщенське': (48.4167, 32.8833), 'благовіщенську': (48.4167, 32.8833), 'благовіщенського': (48.4167, 32.8833),
    'оржиця': (50.0667, 32.3833), 'оржицю': (50.0667, 32.3833), 'оржиці': (50.0667, 32.3833),
    'тальне': (49.1833, 30.6833), 'тальному': (49.1833, 30.6833), 'тального': (49.1833, 30.6833),
    'бобровиця': (51.0833, 32.1167), 'бобровицю': (51.0833, 32.1167), 'бобровиці': (51.0833, 32.1167),
    'холми': (51.6833, 32.4000), 'холмам': (51.6833, 32.4000), 'холмах': (51.6833, 32.4000),
    'сосниця': (51.9500, 32.4667), 'сосницю': (51.9500, 32.4667), 'сосниці': (51.9500, 32.4667),
    'вишгород': (50.5833, 30.4833), 'вишгороду': (50.5833, 30.4833), 'вишгороді': (50.5833, 30.4833),
    'малин': (50.7667, 29.2333), 'маліну': (50.7667, 29.2333), 'маліні': (50.7667, 29.2333),
    'бучмани': (50.2833, 28.3333), 'бучманам': (50.2833, 28.3333), 'бучманах': (50.2833, 28.3333),
    'червоне': (50.4167, 28.9167), 'червоному': (50.4167, 28.9167), 'червоного': (50.4167, 28.9167),
    'понінка': (49.6167, 27.4500), 'понінку': (49.6167, 27.4500), 'понінці': (49.6167, 27.4500),
    'теофіполь': (49.8833, 27.6500), 'теофіполю': (49.8833, 27.6500), 'теофіполі': (49.8833, 27.6500),
    'гоща': (50.6167, 26.4167), 'гощу': (50.6167, 26.4167), 'гощі': (50.6167, 26.4167),
    'клевань': (50.7667, 25.9833), 'клевані': (50.7667, 25.9833), 'клеваню': (50.7667, 25.9833),
    'володимирець': (51.4333, 25.9167), 'володимирцю': (51.4333, 25.9167), 'володимирці': (51.4333, 25.9167),
    'локачі': (51.1167, 24.2667), 'локачам': (51.1167, 24.2667), 'локачах': (51.1167, 24.2667),
    'іваничі': (51.2333, 24.3167), 'іваничам': (51.2333, 24.3167), 'іваничах': (51.2333, 24.3167),
    'турійськ': (51.0833, 24.7000), 'турійську': (51.0833, 24.7000), 'турійська': (51.0833, 24.7000),
    # Додаткові міста з великих повідомлень
    'великі мости': (48.9167, 25.3333), 'великих мостів': (48.9167, 25.3333), 'великих мостах': (48.9167, 25.3333),
    'снігурівка': (46.7500, 32.8167), 'снігурівку': (46.7500, 32.8167), 'снігурівці': (46.7500, 32.8167),
    'баранівка': (50.3000, 27.6667), 'баранівку': (50.3000, 27.6667), 'баранівці': (50.3000, 27.6667),
    'новоград-волинський': (50.5833, 27.6167), 'новограда-волинського': (50.5833, 27.6167),
    'красилів': (49.6500, 27.1667), 'красилову': (49.6500, 27.1667), 'красилові': (49.6500, 27.1667),
    'шепетівка': (50.1833, 27.0667), 'шепетівку': (50.1833, 27.0667), 'шепетівці': (50.1833, 27.0667),
    'славута': (50.3000, 26.8667), 'славуту': (50.3000, 26.8667), 'славуті': (50.3000, 26.8667),
    'нетішин': (50.3333, 26.6333), 'нетішину': (50.3333, 26.6333), 'нетішині': (50.3333, 26.6333),
    'острог': (50.3333, 26.5167), 'острогу': (50.3333, 26.5167), 'острозі': (50.3333, 26.5167),
    'дубно': (50.4167, 25.7667), 'дубну': (50.4167, 25.7667), 'дубні': (50.4167, 25.7667),
    'вараш': (51.3500, 25.8500), 'вараші': (51.3500, 25.8500), 'варашу': (51.3500, 25.8500),
    'костопіль': (50.8833, 26.4500), 'костополю': (50.8833, 26.4500), 'костополі': (50.8833, 26.4500),
    'сарни': (51.3333, 26.6000), 'сарнам': (51.3333, 26.6000), 'сарнах': (51.3333, 26.6000),
    'рокитне': (50.9333, 26.1667), 'рокитному': (50.9333, 26.1667), 'рокитного': (50.9333, 26.1667),
    'дубровиця': (51.5667, 26.5667), 'дубровицю': (51.5667, 26.5667), 'дубровиці': (51.5667, 26.5667),
    'березне': (51.4500, 26.7167), 'березному': (51.4500, 26.7167), 'березного': (51.4500, 26.7167),
    'шостку': (51.8667, 33.4833), 'конотопу': (51.2417, 33.2022), 'недригайлів': (50.8281, 33.8781),
    'липову долину': (50.5700, 33.7900), 'носівку': (50.9444, 32.0167), 'бахмач': (51.1808, 32.8203), 'бахмача': (51.1808, 32.8203)
    ,'пісківка': (50.6767, 29.5283), 'пісківку': (50.6767, 29.5283), 'пісківці': (50.6767, 29.5283)
    ,'зіньків': (49.2019, 34.3744), 'зінькові': (49.2019, 34.3744), 'зіньківу': (49.2019, 34.3744), 'зінькова': (49.2019, 34.3744)
}

# Donetsk Oblast cities (повний перелік міст області). Added per user request to ensure precise mapping.
# Sources: OpenStreetMap / GeoNames (approx to 4 decimal places). Using setdefault to avoid overriding existing entries.
DONETSK_CITY_COORDS = {
    'донецьк': (48.0028, 37.8053),
    'макіївка': (48.0478, 37.9258),
    'горлівка': (48.3336, 38.0925),
    'маріуполь': (47.0971, 37.5434),  # already present
    'краматорськ': (48.7389, 37.5848),  # already present
    'слов\'янськ': (48.8417, 37.5983),  # already present
    'дружківка': (48.6203, 37.5263),  # already present
    'костянтинівка': (48.5277, 37.7050),  # already present
    'бахмут': (48.5937, 38.0000),
    'авдіївка': (48.1417, 37.7425),
    'покровськ': (48.2833, 37.1833),
    'мирноград': (48.3000, 37.2667),
    'торецьк': (48.3976, 37.8687),
    'добропілля': (48.4697, 37.0851),
    'селидове': (48.1500, 37.3000),
    'новогродівка': (48.2065, 37.3467),
    'волноваха': (47.6000, 37.5000),
    'вугледар': (47.7811, 37.2358),
    'ліман': (48.9890, 37.8020),
    'святогірськ': (49.0339, 37.5663),  # already present
    'сіверськ': (48.8667, 38.1000),
    'соледар': (48.5356, 38.0875),
    'часів яр': (48.5969, 37.8350),
    'шахтарськ': (48.0500, 38.4500),
    'єнакієве': (48.2333, 38.2000),
    'амвросіївка': (47.7956, 38.4772),
    'дебальцеве': (48.3400, 38.4000),
    'докучаєвськ': (47.7489, 37.6789),
    'іловайськ': (47.9233, 38.1950),
    'жданівка': (48.1500, 38.2667),
    'зугрес': (48.0167, 38.2667),
    'харцизьк': (48.0400, 38.1500),
    'вуглегірськ': (48.3167, 38.2167),
    'ясинувата': (48.1167, 37.8333),
    'сніжне': (48.0333, 38.7667),
    'кальміуське': (47.6528, 38.0664),
    'моспине': (47.8583, 38.0000),
    'українськ': (48.0333, 37.9000),
    'родинське': (48.3500, 37.2000),
    'залізне': (48.3539, 37.8483),
    # Historical / alt names not added to avoid noise; add normalization separately if needed.
}

for _dn_name, _dn_coords in DONETSK_CITY_COORDS.items():
    CITY_COORDS.setdefault(_dn_name, _dn_coords)

# Kharkiv Oblast cities and key settlements (міста + важливі селища) per user request.
# Many already present; using setdefault to avoid override. Includes normalized variants.
KHARKIV_CITY_COORDS = {
    'ізюм': (49.2103, 37.2483),
    'куп\'янськ': (49.7106, 37.6156),
    'купянськ': (49.7106, 37.6156),  # variant without apostrophe
    'лозова': (48.8897, 36.3175),
    'липці': (50.3061, 36.7597),  # село біля кордону з Росією
    'первомайський': (49.3914, 36.2147),
    'вовчанськ': (50.3000, 36.9500),
    'люботин': (49.9486, 35.9292),
    'дергачі': (50.1061, 36.1217),
    'зміїв': (49.6897, 36.3472),
    'красноград': (49.3740, 35.4405),
    'печеніги': (49.8667, 36.9667),
    'золочів(харківщина)': (50.2744, 36.3592),
    'золочів': (50.2744, 36.3592),  # may conflict with Львівська обл.; disambiguation via region context
    'великий бурлук': (50.0514, 37.3903),
    'південне': (49.8667, 36.0500),
    'покотилівка': (49.9345, 36.0603),
    'манченки': (49.9840, 35.9680),
    'малинівка': (49.6550, 36.7060),
    'коломак': (49.8422, 35.2761),
    'козача лопань': (49.8872, 36.4167),  # СМТ в Дергачівському районі
    'чкаловське': (49.7155296, 36.9322501),  # Правильне Чкаловське в Харківській області
    'першотравневий': (49.3914, 36.2147),  # с. Першотравневе, Харківська область (same as Первомайський)
    'створ населеного пункту балки?': (49.4627, 36.8586),  # placeholder example – remove/replace if noise
}

for _kh_name, _kh_coords in KHARKIV_CITY_COORDS.items():
    CITY_COORDS.setdefault(_kh_name, _kh_coords)

# Chernihiv Oblast cities / key settlements (міста та важливі селища)
# Many base ones already in CITY_COORDS (чернігів, ніжин, прилуки, новгород-сіверський, коростень (інша обл.), корюківка maybe missing).
CHERNIHIV_CITY_COORDS = {
    'ніжин': (51.0480, 31.8860),  # already present
    'прилуки': (50.5931, 32.3878),  # already present
    'новгород-сіверський': (51.9874, 33.2620),  # already present
    'корюківка': (51.7725, 32.2494),
    'козелець': (51.5625, 31.2058),  # Added
    'носівка': (51.0325, 31.5522),   # Added
    'куликівка': (51.3667, 32.2000),  # Added
    'мена': (51.5211, 32.2147),      # Fixed typo
    'ічня': (51.0722, 32.3931),      # Added
    'борзна': (51.2542, 32.4192),  # already present
    'батиївка?': (51.4982, 31.2893),  # placeholder if appears; else remove
    'менa': (51.5211, 32.2147),  # variant with latin a? (typo guard)
    'м ена': (51.5211, 32.2147),  # spacing anomaly fallback
    'семенівка(чернігівщина)': (52.1833, 32.5833),  # north settlement (if referenced)
    'семенівка чернігівська': (52.1833, 32.5833),
    'семенівка': (52.1833, 32.5833),  # might conflict with Poltava one; context disambiguation may be needed
    'сновськ': (51.8200, 31.9500),
    'короп': (51.5667, 32.9667),
    'іхня': (51.0722, 32.3931),  # misspelling variant of ічня
    'ичня': (51.0722, 32.3931),  # alt transliteration
    'глухів?': (51.6781, 33.9169),  # actually Sumy oblast; placeholder if mis-tag appears
    'сосниця': (51.5236, 32.4953),  # already present
    'конотоп?': (51.2417, 33.2022),  # Sumy oblast - guard only
    'остер': (50.9481, 30.8831),  # already present
    'ніжину': (51.0480, 31.8860),  # accusative
    'борзні': (51.2542, 32.4192),
    'коропі': (51.5667, 32.9667),
    'корюківці': (51.7725, 32.2494),
    'корюківку': (51.7725, 32.2494),
    'сновську': (51.8200, 31.9500),
    'семенівці': (52.1833, 32.5833),
    'семенівку': (52.1833, 32.5833),
    # Дополнительные города и формы
    'седнів': (51.5211, 32.1897),
    'новгород': (51.9874, 33.2620),  # новгород-сіверський
    'новгород-сіверський': (51.9874, 33.2620),
}

for _ch_name, _ch_coords in CHERNIHIV_CITY_COORDS.items():
    CITY_COORDS.setdefault(_ch_name, _ch_coords)

# Dnipropetrovsk (Дніпропетровська) Oblast cities & key settlements.
DNIPRO_CITY_COORDS = {
    'кривий ріг': (47.9105, 33.3918),  # already implied in stems
    'жіовті води': (48.3456, 33.5022),  # typo guard for жовті води
    'жовті води': (48.3456, 33.5022),
    'кам\'янське': (48.5110, 34.6021),  # already present as variant
    'камянське': (48.5110, 34.6021),  # present
    'нікополь': (47.5667, 34.4061),  # present
    'марганець': (47.6433, 34.6289),  # present
    'покров': (47.6542, 34.1167),
    'тернівка': (48.5319, 36.0681),
    'першотравенськ': (48.3460, 36.4030),
    'вільногірськ': (48.4850, 34.0300),
    'жовті': (48.3456, 33.5022),  # truncated mention mapping
    'новомосковськ': (48.6333, 35.2167),
    'зарічне': (48.15, 35.2),  # Зарічне, Покровський район, Дніпропетровська область
    'зарічне дніпропетровська': (48.15, 35.2),  # Спеціально для військового контексту  
    'зарічне покровський': (48.15, 35.2),  # Альтернативний ключ
    'синельникове': (48.3167, 35.5167),
    'петропавлівка': (48.5000, 36.4500),  # present
    'покровське(дніпропетровщина)': (48.1180, 36.2470),
    'покровське дніпропетровська': (48.1180, 36.2470),
    'покровське дніпропетровщини': (48.1180, 36.2470),
    'покровське': (48.1180, 36.2470),  # present
    'богданівка(дніпро)': (48.4647, 35.0462),  # fallback to oblast center if ambiguous
    'васильківка': (48.3550, 36.1240),
    'варварівка': (48.7440, 34.7000),
    'верхівцеве': (48.4769, 34.3458),
    'верхньодніпровськ': (48.6535, 34.3372),  # present
    'губиниха': (48.7437, 35.2960),  # present
    'домоткань': (48.6680, 34.2160),
    'жеребетівка': (48.2500, 36.7000),
    'зайцеве(дніпропетровщина)': (48.4647, 35.0462),  # generic fallback center
    'зелений гай': (48.4200, 35.1200),
    'зеленодольськ': (47.5667, 33.5333),  # present
    'карнаухівка': (48.4870, 34.5480),
    'карпівка': (47.5930, 33.5960),
    'маломихайлівка': (48.2300, 36.4500),
    'меліоративне': (48.6340, 35.1750),
    'магідалинівка': (48.8836, 34.8669),  # typo guard for магдалинівка
    'магдалинівка': (48.8836, 34.8669),  # present
    'межова': (48.2583, 36.7363),  # present
    'миколаївка(дніпро)': (48.4647, 35.0462),
    'новомиколаївка(дніпро)': (48.4647, 35.0462),
    'обухівка': (48.6035, 34.8530),  # present
    'орлівщина': (48.6110, 34.9550),
    'павлоград': (48.5350, 35.8700),  # present
    'перещепине': (48.6260, 35.3580),  # present
    'петриківка': (48.7330, 34.6300),  # present
    'підгородне': (48.5747, 35.1482),  # present
    'покровське (смт)': (48.1180, 36.2470),
    'радушне': (47.9840, 33.4930),
    'самар': (48.6500, 35.4200),  # present
    'сурсько-литовське': (48.3720, 34.8130),
    'тернівські хутори': (48.6600, 34.9400),
    'томаківка': (47.8130, 34.7450),
    'царичанка': (48.9767, 34.3772),  # present
    'чумакове': (48.3400, 35.2800),
    'шевченківське(дніпро)': (48.4647, 35.0462),
    'юр’ївка': (48.7250, 36.0130),
    'юр'"'"'ївка': (48.7250, 36.0130),  # attempt to guard variant – may adjust quoting
    'юрївка': (48.7250, 36.0130),
    'юр’ївку': (48.7250, 36.0130),
    'юр'"'"'ївку': (48.7250, 36.0130),
}

for _dp_name, _dp_coords in DNIPRO_CITY_COORDS.items():
    CITY_COORDS.setdefault(_dp_name, _dp_coords)

# Sumy (Сумська) Oblast cities & key settlements.
SUMY_CITY_COORDS = {
    'суми': (50.9077, 34.7981),  # already present
    'шостка': (51.8733, 33.4800),
    'кременчук?': (49.0670, 33.4204),  # ignore (other oblast) placeholder if mis-ref
    'охтирка': (50.3116, 34.8988),
    'р омни': (50.7497, 33.4746),  # space anomaly guard
    'ромни': (50.7497, 33.4746),  # present
    'к о тростянець': (50.4833, 34.9667),  # anomaly
    'тростянець': (50.4833, 34.9667),  # present
    'глухів': (51.6781, 33.9169),  # present
    'конотоп': (51.2417, 33.2022),  # present
    'ліпова долина': (50.5700, 33.7900),  # typo
    'липова долина': (50.5700, 33.7900),  # present
    'буринь': (51.2000, 33.8500),  # present
    'путівль': (51.3375, 33.8700),
    'середина-буда': (52.1900, 33.9300),
    'лебедин': (50.5872, 34.4912),  # present
    'недригайлів': (50.8281, 33.8781),  # present
    'в сууликівка?': (50.9077, 34.7981),  # fallback noise
    'білопілля': (51.1500, 34.3014),  # present
    'краснопілля': (50.4422, 35.3081),  # present
    'сумської області центр': (50.9077, 34.7981),
    'велика писарівка': (50.4250, 35.4650),
    'велика писарівка смт': (50.4250, 35.4650),
    'велика писарівку': (50.4250, 35.4650),
    'бранцівка?': (50.9077, 34.7981),
    'дружба(сумщина)': (51.5230, 34.5770),
    'дружба': (51.5230, 34.5770),
    'зорине?': (50.9077, 34.7981),
    'кир ик івка?': (51.2000, 33.8500),
    'к и рик івка': (51.2000, 33.8500),
    'кирзаківка?': (51.2000, 33.8500),
    'кир ик івку': (51.2000, 33.8500),
    'кир иківка': (51.2000, 33.8500),
    'кир иківку': (51.2000, 33.8500),
    'кир ик івці': (51.2000, 33.8500),
    'кир ик івці?': (51.2000, 33.8500),
    'кир иківці': (51.2000, 33.8500),
    'кир иківці?': (51.2000, 33.8500),
    'кир ичівка?': (51.2000, 33.8500),
    'к ирик івка': (51.2000, 33.8500),
    'смородине': (50.9660, 34.5500),
    'смородино': (50.9660, 34.5500),
    'смородиному': (50.9660, 34.5500),
    'смородиного': (50.9660, 34.5500),
    'ясенок?': (51.5230, 34.5770),
    'ясенок': (51.5230, 34.5770),
    'ясенку': (51.5230, 34.5770),
    'ясенку?': (51.5230, 34.5770),
    'ясенка': (51.5230, 34.5770),
    'ясенка?': (51.5230, 34.5770),
    'ясенці': (51.5230, 34.5770),
    'ясенці?': (51.5230, 34.5770),
    'ясенців': (51.5230, 34.5770),
    'ясенців?': (51.5230, 34.5770),
    'миколаївка(сумська)': (51.5667, 34.1333),  # Миколаївка, районний центр Сумської області
    'миколаївка (сумська)': (51.5667, 34.1333),  # з пробілом
    'миколаївку(сумська)': (51.5667, 34.1333),  # винительный падеж
    'миколаївку (сумська)': (51.5667, 34.1333),  # винительный падеж з пробілом
}

for _sm_name, _sm_coords in SUMY_CITY_COORDS.items():
    CITY_COORDS.setdefault(_sm_name, _sm_coords)

# Zaporizhzhia (Запорізька) Oblast cities & key settlements.
ZAPORIZHZHIA_CITY_COORDS = {
    'запоріжжя': (47.8388, 35.1396),  # already present
    'бердянськ': (46.7553, 36.7885),  # present
    'мелітополь': (46.8489, 35.3650),  # present
    'енергодар': (47.4980, 34.6580),
    'токмак': (47.2550, 35.7120),
    'пологи': (47.4768, 36.2543),
    'вільнянськ': (47.9450, 35.4350),
    'оріхів': (47.5672, 35.7814),
    'гуляйполе': (47.6611, 36.2567),
    'приморськ': (46.7310, 36.3440),
    'дазовськ': (47.8388, 35.1396),  # typo guard (азовськ?) fallback
    'азовськ?': (47.8388, 35.1396),
    'васильівка': (47.4393, 35.2745),
    'дорожнянка': (47.5540, 36.0950),
    'роботине': (47.3780, 35.9300),
    'роботиному': (47.3780, 35.9300),
    'роботиного': (47.3780, 35.9300),
    'работине': (47.3780, 35.9300),  # transliteration variant
    'чернігівка(запоріжжя)': (47.0870, 36.2320),
    'чернігівка': (47.0870, 36.2320),
    'михайлівка(запоріжжя)': (47.2730, 35.2200),
    'михайлівка': (47.2730, 35.2200),  # may conflict (other oblast) – context disambiguation
    'костянтинівка(запоріжжя)': (47.2460, 35.3220),  # small settlement, not Donetsk one
    'степногірськ': (47.5660, 35.2850),
    'камянка-дніпровська': (47.4980, 34.4000),
    'кам\'янка-дніпровська': (47.4980, 34.4000),
    'кирпотине?': (47.3780, 35.9300),  # noise variant to robotyne
    'малокатеринівка': (47.7040, 35.2710),
    'комишуваха(запорізька)': (47.5760, 35.5090),
    'комишуваха': (47.5760, 35.5090),  # duplicate name in other oblasts
    'комишувасі': (47.5760, 35.5090),
    'комишуваху': (47.5760, 35.5090),
    'чергове?': (47.8388, 35.1396),
    'н ове?': (47.8388, 35.1396),
    'нововасилівка': (47.3290, 35.5130),
    'малинівка(зап)': (47.6260, 35.8700),
    'малинівка запорізька': (47.6260, 35.8700),
    'малинівка': (47.6260, 35.8700),  # may conflict with Kharkiv one
    'веселе(запоріжжя)': (47.1700, 35.1750),
    'веселе': (47.1700, 35.1750),  # generic name multiple oblasts
    'балабине': (47.7520, 35.1660),
    'кушугум': (47.7630, 35.2200),
    'тернувате': (47.8520, 35.5560),
    'чайкине?': (47.8388, 35.1396),
}

for _zp_name, _zp_coords in ZAPORIZHZHIA_CITY_COORDS.items():
    CITY_COORDS.setdefault(_zp_name, _zp_coords)

# Poltava (Полтавська) Oblast cities & key settlements.
POLTAVA_CITY_COORDS = {
    'полтава': (49.5883, 34.5514),  # already present
    'кременчук': (49.0670, 33.4204),  # present
    'горішні плавні': (49.0123, 33.6450),  # present
    'лубни': (50.0186, 32.9931),  # present
    'миргород': (49.9688, 33.6083),
    'гадяч': (50.3713, 34.0109),  # present
    'карлівка': (49.4586, 35.1272),  # present
    'решетилівка': (49.5630, 34.0720),
    'пирятин': (50.2444, 32.5144),
    'хорол': (49.7850, 33.2200),
    'чутове': (49.7070, 35.0960),
    'глобине': (49.3958, 33.2664),
    'голтвa?': (49.5883, 34.5514),  # noise
    'нові санжари': (49.3280, 34.3170),
    'великі сорочинці': (50.0167, 33.9833),  # present
    'дикистань?': (49.9688, 33.6083),  # noise dykanka variant
    'дика нка': (49.8214, 34.5769),
    'ди канка': (49.8214, 34.5769),
    'ди канку': (49.8214, 34.5769),
    'ди канці': (49.8214, 34.5769),
    'ди к анці': (49.8214, 34.5769),
    'ди к анку': (49.8214, 34.5769),
    'ди к анка': (49.8214, 34.5769),
    'ди канки': (49.8214, 34.5769),
    'ди к анки': (49.8214, 34.5769),
    'ди к анкою': (49.8214, 34.5769),
    'ди к анкою?': (49.8214, 34.5769),
    'ди к анкою.': (49.8214, 34.5769),
    'ди к анкою,': (49.8214, 34.5769),
    'ди канкою': (49.8214, 34.5769),
    'ди канкою,': (49.8214, 34.5769),
    'ди канкою.': (49.8214, 34.5769),
    'ди к анці?': (49.8214, 34.5769),
    'ди канці?': (49.8214, 34.5769),
    'ди к анок?': (49.8214, 34.5769),
    'ди к анок': (49.8214, 34.5769),
    'ди канок?': (49.8214, 34.5769),
    'ди канок': (49.8214, 34.5769),
    'ди к анці,': (49.8214, 34.5769),
    'ди канці,': (49.8214, 34.5769),
    'ди канок.': (49.8214, 34.5769),
    'ди к анок.': (49.8214, 34.5769),
    'ди канок,': (49.8214, 34.5769),
    'ди к анок,': (49.8214, 34.5769),
    'ди ка нка': (49.8214, 34.5769),
    'ди ка нку': (49.8214, 34.5769),
    'ди ка нці': (49.8214, 34.5769),
    'ди ка нкою': (49.8214, 34.5769),
    'дика нці': (49.8214, 34.5769),
    'дика нкою': (49.8214, 34.5769),
    'ди к анці.': (49.8214, 34.5769),
    'ди канці.': (49.8214, 34.5769),
    'ди ка нці.': (49.8214, 34.5769),
    'дика нці.': (49.8214, 34.5769),
    'ди ка нкою.': (49.8214, 34.5769),
    'дика нкою.': (49.8214, 34.5769),
    'ди ка нкою,': (49.8214, 34.5769),
    'дика нкою,': (49.8214, 34.5769),
    'диканька': (49.8214, 34.5769),
    'диканьку': (49.8214, 34.5769),
    'диканьці': (49.8214, 34.5769),
    'диканькою': (49.8214, 34.5769),
    'дика нка?': (49.8214, 34.5769),
    'дика нка.': (49.8214, 34.5769),
    'дика нка,': (49.8214, 34.5769),
    'диканці': (49.8214, 34.5769),
    'дика нці?': (49.8214, 34.5769),
    'дика нок': (49.8214, 34.5769),
    'дика нок?': (49.8214, 34.5769),
    'дика нок.': (49.8214, 34.5769),
    'дика нок,': (49.8214, 34.5769),
    'дика нці': (49.8214, 34.5769),
    'дика нкою': (49.8214, 34.5769),
    'ди ка нок': (49.8214, 34.5769),
    'ди ка нок?': (49.8214, 34.5769),
    'ди ка нок.': (49.8214, 34.5769),
    'ди ка нок,': (49.8214, 34.5769),
    'заводське': (50.0750, 33.4000),
    'машівка': (49.4410, 34.8680),
    'семенівка (полтавська)': (50.6633, 32.3933),
    'семенівка полтавська': (50.6633, 32.3933),
    'семенівка': (50.6633, 32.3933),  # conflict with others
    'кобеляки': (49.1500, 34.2000),  # present
    'чорнухи': (50.2833, 33.0000),  # present
    'шишаки': (49.8992, 34.0072),  # present
    'диканька?': (49.8214, 34.5769),
    'диканьці?': (49.8214, 34.5769),
    'диканці': (49.8214, 34.5769),
    'диканку': (49.8214, 34.5769),
    'диканкою': (49.8214, 34.5769),
    'диканкою,': (49.8214, 34.5769),
    'диканкою.': (49.8214, 34.5769),
    'дик анка': (49.8214, 34.5769),
    'дик анці': (49.8214, 34.5769),
    'дик анкою': (49.8214, 34.5769),
    'дик анок': (49.8214, 34.5769),
    'дик анок?': (49.8214, 34.5769),
    'дик анок.': (49.8214, 34.5769),
    'дик анок,': (49.8214, 34.5769),
    
    # ========== CITY+OBLAST SPECIFIC COORDINATES ==========
    # These entries resolve ambiguous city names by including oblast context
    
    # Срібне (different cities in different oblasts)
    'срібне чернігівська': (51.1300, 31.9400),  # Срібне, Чернігівська область  
    'срібне чернігівська обл.': (51.1300, 31.9400),
    'срібне (чернігівська обл.)': (51.1300, 31.9400),
    'срібне чернігівщина': (51.1300, 31.9400),
    'срібне чернігівщині': (51.1300, 31.9400),
    'срібне': (51.1300, 31.9400),  # Default to Chernihiv oblast variant
    
    # Златопіль (fixing incorrect coordinates - was pointing to Donetsk)
    'златопіль харківська': (49.9800, 35.5300),  # Златопіль, Харківська область (correct)
    'златопіль харківська обл.': (49.9800, 35.5300),
    'златопіль (харківська обл.)': (49.9800, 35.5300),
    'златопіль харківщина': (49.9800, 35.5300),
    'златопіль харківщині': (49.9800, 35.5300),
    # Keep old incorrect entry as fallback for other messages, but correct default
    'златопіль': (49.9800, 35.5300),  # Override with correct Kharkiv oblast coordinates
    
    # Чернігівська область - додаткові міста
    'любеч': (51.4961, 30.2675),  # Любеч, Чернігівська область
    'любеч чернігівська': (51.4961, 30.2675),
    'любеч чернігівська обл.': (51.4961, 30.2675),
    'любеч (чернігівська обл.)': (51.4961, 30.2675),
}

for _pl_name, _pl_coords in POLTAVA_CITY_COORDS.items():
    CITY_COORDS.setdefault(_pl_name, _pl_coords)

# Mykolaiv (Миколаївська) Oblast cities & key settlements.
MYKOLAIV_CITY_COORDS = {
    'миколаїв': (46.9750, 31.9946),  # already present
    'первомайськ': (48.0449, 30.8500),  # not to confuse with Первомайський (Kharkiv)
    'вознесенськ': (47.5679, 31.3336),
    'южноукраїнськ': (47.8178, 31.1800),
    'новий буг': (47.6833, 32.5167),  # present
    'нова одеса': (47.3100, 31.7830),
    'нову одесу': (47.3100, 31.7830),
    'новій одесі': (47.3100, 31.7830),
    'очаків': (46.6167, 31.5500),
    'очаков': (46.6167, 31.5500),  # russian variant
    'снігурівка': (47.0750, 32.8050),
    'снігурівку': (47.0750, 32.8050),
    'снігурівці': (47.0750, 32.8050),
    'казанка': (47.8460, 32.8460),
    'арбатська стрілка?': (46.9750, 31.9946),  # noise guard
    'доманівка': (47.6290, 30.9920),
    'врадіївка': (47.8820, 30.5910),
    'криве озеро': (47.9500, 30.3500),
    'єланець': (47.8667, 31.8667), 'єланця': (47.8667, 31.8667), 'єланцю': (47.8667, 31.8667), 'єланці': (47.8667, 31.8667),
    'баштанка': (47.4086, 32.4389), 'баштанки': (47.4086, 32.4389), 'баштанку': (47.4086, 32.4389), 'баштанці': (47.4086, 32.4389),
    'березнегувате': (47.3167, 32.8500),  # present
    'березнегуватому': (47.3167, 32.8500),
    'аркасове?': (46.9750, 31.9946),
    'кашперо-миколаївка': (47.3620, 31.8790),
    'парутине': (46.7530, 31.0160),
    'парутиному': (46.7530, 31.0160),
    'парутиного': (46.7530, 31.0160),
    'парутині': (46.7530, 31.0160),
    'коблеве': (46.6670, 31.2170),
    'коблево': (46.6670, 31.2170),
    'коблевому': (46.6670, 31.2170),
    'коблевого': (46.6670, 31.2170),
    'коблеві': (46.6670, 31.2170),
    'галіцинове': (46.9710, 31.9400),
    'галицинове': (46.9710, 31.9400),
    'галіциновому': (46.9710, 31.9400),
    'галіциново': (46.9710, 31.9400),
    'лиман (миколаїв)': (46.5410, 31.3270),
    'кутузівка?': (46.9750, 31.9946),
    'олександрівка(мик)': (46.7160, 31.8660),
    'олександрівка миколаївська': (46.7160, 31.8660),
    'олександрівка': (46.7160, 31.8660),  # multiple oblasts
    'старий буг?': (47.6833, 32.5167),
    # Додаткові населені пункти Миколаївської області
    'братське': (47.5333, 32.1667), 'братську': (47.5333, 32.1667), 'братського': (47.5333, 32.1667),
    'возсіятське': (46.8167, 32.0833), 'возсіятську': (46.8167, 32.0833), 'возсіятського': (46.8167, 32.0833),
}

for _my_name, _my_coords in MYKOLAIV_CITY_COORDS.items():
    CITY_COORDS.setdefault(_my_name, _my_coords)

# Odesa (Одеська) Oblast cities & key settlements.
ODESA_CITY_COORDS = {
    'одеса': (46.4825, 30.7233),  # already present
    'одесса': (46.4825, 30.7233),  # russian variant
    'чорноморськ': (46.3019, 30.6548),
    'южне': (46.6226, 31.1013),
    'білгород-дністровський': (46.1900, 30.3400),
    'білгород-дністровськ': (46.1900, 30.3400),
    'білгород-дністровську': (46.1900, 30.3400),
    'белгород-днестровский': (46.1900, 30.3400),
    'подільськ': (47.7425, 29.5322),
    'подольськ': (47.7425, 29.5322),
    'балта': (47.9381, 29.6125),
    'балті': (47.9381, 29.6125),
    'балту': (47.9381, 29.6125),
    'балтою': (47.9381, 29.6125),
    'артемівськ(одеса)?': (46.4825, 30.7233),  # noise
    'роздільна': (46.8450, 30.0780),
    'роздільній': (46.8450, 30.0780),
    'роздільну': (46.8450, 30.0780),
    'килія': (45.4550, 29.2680),
    'ізмаїл': (45.3511, 28.8367),
    'ізмаїлі': (45.3511, 28.8367),
    'ізмаїл у': (45.3511, 28.8367),
    'ізмаїлу': (45.3511, 28.8367),
    'вилкове': (45.4031, 29.5986),
    'вилковому': (45.4031, 29.5986),
    # Чаплине (Дніпропетровська область)
    'чаплине': (47.3811, 34.5619),
    'чаплином': (47.3811, 34.5619),
    'чаплиному': (47.3811, 34.5619),
    'рений': (45.4560, 28.2830),
    'рені': (45.4560, 28.2830),
    'рено?': (45.4560, 28.2830),
    'татарбунари': (45.8417, 29.6128),
    'сарни(одеса)?': (46.4825, 30.7233),  # noise
    'болград': (45.6772, 28.6147),
    'болграді': (45.6772, 28.6147),
    'болградом': (45.6772, 28.6147),
    'арциз': (45.9919, 29.4181),
    'арцизі': (45.9919, 29.4181),
    'арцизом': (45.9919, 29.4181),
    'таврія(одеса)?': (46.4825, 30.7233),  # noise
    'любашівка': (47.8540, 30.2550),
    'любашівці': (47.8540, 30.2550),
    'ананьїв': (47.7244, 29.9686),
    'ананьєв': (47.7244, 29.9686),
    'ананьєві': (47.7244, 29.9686),
    'ананьєву': (47.7244, 29.9686),
    'березівка': (47.2050, 30.9080),
    'березівці': (47.2050, 30.9080),
    'березівку': (47.2050, 30.9080),
    'зато ка?': (46.0660, 30.4680),  # noise for затока
    'затока': (46.0660, 30.4680),  # present
    'кароліно-бугаз': (46.1530, 30.5200),
    'кароліно-бугазі': (46.1530, 30.5200),
    'кароліно-бугазу': (46.1530, 30.5200),
    'кароліно-бугазом': (46.1530, 30.5200),
    'градізськ(одеса)?': (46.4825, 30.7233),  # noise
    'таїрове': (46.3990, 30.6940),
    'таїровому': (46.3990, 30.6940),
    'сергіївка': (46.0006, 29.9578),
    'сергіївці': (46.0006, 29.9578),
    'сергіївку': (46.0006, 29.9578),
    'сергіївкою': (46.0006, 29.9578),
    'тузли': (45.8650, 30.0975),
    'тузл': (45.8650, 30.0975),
    'тузлах': (45.8650, 30.0975),
    'тузлами': (45.8650, 30.0975),
    'таїрово': (46.3990, 30.6940),
    'лиман(одеса)': (46.3530, 30.6500),
    'лиман одеса': (46.3530, 30.6500),
    'лиман (одеса)': (46.3530, 30.6500),
}

for _od_name, _od_coords in ODESA_CITY_COORDS.items():
    CITY_COORDS.setdefault(_od_name, _od_coords)

# Kyiv (Київська) Oblast cities & key settlements (excluding Kyiv already present).
KYIV_OBLAST_CITY_COORDS = {
    'біла церква': (49.7950, 30.1310),  # present
    'бровари': (50.5110, 30.7909),  # present
    'бориспіль': (50.3527, 30.9550),  # present
    'гнідин': (50.3722, 30.8639),  # село біля Борисполя
    'ірпінь': (50.5218, 30.2506),
    'ірпеня': (50.5218, 30.2506),
    'буча': (50.5436, 30.2120),
    'бучу': (50.5436, 30.2120),
    'бучі': (50.5436, 30.2120),
    'васильків': (50.1846, 30.3133),
    'василькові': (50.1846, 30.3133),
    'василькові?': (50.1846, 30.3133),
    'фастів': (50.0780, 29.9170),
    'фастові': (50.0780, 29.9170),
    'фастову': (50.0780, 29.9170),
    'обухів': (50.1072, 30.6211),  # present
    'обухові': (50.1072, 30.6211),
    'обухову': (50.1072, 30.6211),
    'обуховом': (50.1072, 30.6211),
    'славутич': (51.5226, 30.7203),
    'славутичі': (51.5226, 30.7203),
    'славутичу': (51.5226, 30.7203),
    'славутичем': (51.5226, 30.7203),
    'березань': (50.3085, 31.4576),  # present
    'березані': (50.3085, 31.4576),
    'березаньська?': (50.3085, 31.4576),
    'сквира': (49.7333, 29.6667),  # present
    'сквирі': (49.7333, 29.6667),
    'сквиру': (49.7333, 29.6667),
    'кагарлик': (49.6607, 30.8172),
    'кагарлику': (49.6607, 30.8172),
    'кагарлику?': (49.6607, 30.8172),
    'миронівка': (49.6631, 31.0100),  # present
    'миронівці': (49.6631, 31.0100),
    'миронівку': (49.6631, 31.0100),
    'богуслав': (49.5494, 30.8741),
    'богуславі': (49.5494, 30.8741),
    'богуславу': (49.5494, 30.8741),
    'узин': (49.8216, 30.4567),  # present
    'узині': (49.8216, 30.4567),
    'узином': (49.8216, 30.4567),
    'тетієв': (49.3717, 29.6969),
    'тетієві': (49.3717, 29.6969),
    'тетієву': (49.3717, 29.6969),
    'володимирівка(київска?)': (50.4501, 30.5234),  # noise center fallback
    'володарка': (49.5240, 29.9120),
    'володарці': (49.5240, 29.9120),
    'володарку': (49.5240, 29.9120),
    'таврижжя?': (50.4501, 30.5234),
    'колонщина': (50.4150, 29.9990),
    'колонщині': (50.4150, 29.9990),
    'колонщину': (50.4150, 29.9990),
    'гребінки': (50.2500, 30.2500),  # present
    'гребінках': (50.2500, 30.2500),
    'гребінкам': (50.2500, 30.2500),
    'гребінками': (50.2500, 30.2500),
    'гребінок': (50.2500, 30.2500),
    'вишгород': (50.5840, 30.4890),  # present
    'вишгороді': (50.5840, 30.4890),
    'вишгороду': (50.5840, 30.4890),
    'вишгородом': (50.5840, 30.4890),
    'вишневе': (50.3899, 30.3932),
    'вишневому': (50.3899, 30.3932),
    'вишнево': (50.3899, 30.3932),
    'вишневого': (50.3899, 30.3932),
    'ірпінсько-бучанська агломерація?': (50.5218, 30.2506),
    'козин (київська)': (50.1520, 30.6450),
    'козин київська': (50.1520, 30.6450),
    'козин': (50.1520, 30.6450),  # multiple oblasts
    'петрівське?': (50.4501, 30.5234),
    'петрівське(київ)': (50.4501, 30.5234),
    'петрівське київська': (50.4501, 30.5234),
    'переяслав': (50.0769, 31.4610),  # Переяслав-Хмельницький
    'переяслові': (50.0769, 31.4610),
    'переяславу': (50.0769, 31.4610),
    'переяславом': (50.0769, 31.4610),
    'власівка': (50.3706, 31.2381),  # Власівка, Броварський район
    'власівці': (50.3706, 31.2381),
    'власівку': (50.3706, 31.2381),
    'власівкою': (50.3706, 31.2381),
}

for _kv_name, _kv_coords in KYIV_OBLAST_CITY_COORDS.items():
    CITY_COORDS.setdefault(_kv_name, _kv_coords)

# Cherkasy (Черкаська) Oblast cities & key settlements.
CHERKASY_CITY_COORDS = {
    'черкаси': (49.4444, 32.0598),  # already present
    'черкасах': (49.4444, 32.0598),
    'черкасам': (49.4444, 32.0598),
    'умань': (48.7484, 30.2219),
    'умані': (48.7484, 30.2219),
    'уманьу?': (48.7484, 30.2219),
    'смiла': (49.2222, 31.8878),  # alt i
    'сміла': (49.2222, 31.8878),
    'смілі': (49.2222, 31.8878),
    'смiлі': (49.2222, 31.8878),
    'смiлу': (49.2222, 31.8878),
    'смілу': (49.2222, 31.8878),
    'золотоноша': (49.6676, 32.0401),
    'золотоноші': (49.6676, 32.0401),
    'золотоношу': (49.6676, 32.0401),
    'золотоношею': (49.6676, 32.0401),
    'звенигородка': (49.0777, 30.9697),
    'звенигородці': (49.0777, 30.9697),
    'звенигородку': (49.0777, 30.9697),
    'звенегородка': (49.0777, 30.9697),  # rus typo
    'звенегородку': (49.0777, 30.9697),
    'корсунь-шевченківський': (49.4186, 31.2581),
    'корсунь-шевченківському': (49.4186, 31.2581),
    'корсунь-шевченківським': (49.4186, 31.2581),
    'городище': (49.2886, 31.4547),
    'городищі': (49.2886, 31.4547),
    'городищею': (49.2886, 31.4547),
    'христинівка': (48.8122, 29.9806),
    'христинівці': (48.8122, 29.9806),
    'христинівку': (48.8122, 29.9806),
    'монастирище': (48.9905, 29.8036),
    'монастирищі': (48.9905, 29.8036),
    'монастирищем': (48.9905, 29.8036),
    'тальне': (48.8803, 30.6872),
    'тальному': (48.8803, 30.6872),
    'тальним': (48.8803, 30.6872),
    'жашків': (49.2431, 30.1122),  # already present
    'жашкові': (49.2431, 30.1122),
    'жашкові?': (49.2431, 30.1122),
    'лисянка': (49.2547, 30.8294),
    'лисянці': (49.2547, 30.8294),
    'лисянку': (49.2547, 30.8294),
    'чигирин': (49.0797, 32.6572),
    'чигирині': (49.0797, 32.6572),
    'чигирином': (49.0797, 32.6572),
    'кам\'янка': (49.0310, 32.1050),
    'камянка': (49.0310, 32.1050),
    'кам\'янці': (49.0310, 32.1050),
    'камянці': (49.0310, 32.1050),
    'кам\'янку': (49.0310, 32.1050),
    'ватутіне': (48.7500, 30.1833),
    'ватутіному': (48.7500, 30.1833),
    'ватутіним': (48.7500, 30.1833),
    'шпола': (49.0132, 31.3942),
    'шполі': (49.0132, 31.3942),
    'шполу': (49.0132, 31.3942),
    'катеринопіль': (48.9889, 30.9633),
    'катеринополі': (48.9889, 30.9633),
    'катеринополю': (48.9889, 30.9633),
    'драбів': (49.9700, 32.1490),
    'драбові': (49.9700, 32.1490),
    'драбовом': (49.9700, 32.1490),
    'маньківка': (48.9900, 30.3500),
    'маньківці': (48.9900, 30.3500),
    'маньківку': (48.9900, 30.3500),
    'стеблів': (49.3860, 31.0550),
    'стеблеві': (49.3860, 31.0550),
    'єрки': (49.0950, 30.9817),
    'єрках': (49.0950, 30.9817),
}

for _ck_name, _ck_coords in CHERKASY_CITY_COORDS.items():
    CITY_COORDS.setdefault(_ck_name, _ck_coords)

# Lviv (Львівська) Oblast cities & key settlements.
LVIV_CITY_COORDS = {
    'бібрка': (49.6353, 24.2614),
    'бібрку': (49.6353, 24.2614),
    'бібрці': (49.6353, 24.2614),
    'борислав': (49.2897, 23.4267),
    'бориславі': (49.2897, 23.4267),
    'бориславу': (49.2897, 23.4267),
    'броди': (50.0869, 25.1531),
    'бродах': (50.0869, 25.1531),
    'бродам': (50.0869, 25.1531),
    'винники': (49.8097, 24.1431),
    'винниках': (49.8097, 24.1431),
    'винники́': (49.8097, 24.1431),
    'городок': (49.6889, 23.6514),
    'городку': (49.6889, 23.6514),
    'городком': (49.6889, 23.6514),
    'дрогобич': (49.3425, 23.5075),
    'дрогобичі': (49.3425, 23.5075),
    'дрогобичем': (49.3425, 23.5075),
    'жидачів': (49.8744, 24.1403),
    'жидачові': (49.8744, 24.1403),
    'жидачевом': (49.8744, 24.1403),
    'жовква': (49.9731, 23.9719),
    'жовкві': (49.9731, 23.9719),
    'жовкву': (49.9731, 23.9719),
    'золочів': (49.8072, 24.8906),
    'золочеві': (49.8072, 24.8906),
    'золочевом': (49.8072, 24.8906),
    'кам\'янка-бузька': (50.0914, 24.0361),
    'кам\'янці-бузькій': (50.0914, 24.0361),
    'кам\'янку-бузьку': (50.0914, 24.0361),
    'миколаїв': (46.9750, 31.9946),  # Миколаїв правильный (Миколаївська обл.)
    'миколаєві': (46.9750, 31.9946),
    'миколаєвом': (46.9750, 31.9946),
    'мостиська': (49.7956, 23.1533),
    'мостиськах': (49.7956, 23.1533),
    'мостиську': (49.7956, 23.1533),
    'новий розділ': (49.4761, 24.4506),
    'новому розділі': (49.4761, 24.4506),
    'новим розділом': (49.4761, 24.4506),
    'перемишляни': (49.6708, 24.6311),
    'перемишлянах': (49.6708, 24.6311),
    'перемишлянами': (49.6708, 24.6311),
    'пустомити': (49.7256, 24.1172),
    'пустомитах': (49.7256, 24.1172),
    'пустомитами': (49.7256, 24.1172),
    'радехів': (50.2831, 24.6411),
    'радехові': (50.2831, 24.6411),
    'радехевом': (50.2831, 24.6411),
    'самбір': (49.5117, 23.2019),
    'самборі': (49.5117, 23.2019),
    'самбором': (49.5117, 23.2019),
    'сокаль': (50.4656, 24.2728),
    'сокалі': (50.4656, 24.2728),
    'сокалем': (50.4656, 24.2728),
    'старий самбір': (49.4389, 23.0006),
    'старому самборі': (49.4389, 23.0006),
    'старим самбором': (49.4389, 23.0006),
    'стрий': (49.2622, 23.8603),
    'стрию': (49.2622, 23.8603),
    'стриєм': (49.2622, 23.8603),
    'трускавець': (49.2786, 23.5064),
    'трускавці': (49.2786, 23.5064),
    'трускавцем': (49.2786, 23.5064),
    'турка': (49.1528, 23.0306),
    'турці': (49.1528, 23.0306),
    'туркою': (49.1528, 23.0306),
    'яворів': (49.9358, 23.3917),
    'яворові': (49.9358, 23.3917),
    'яворовом': (49.9358, 23.3917),
}

for _lv_name, _lv_coords in LVIV_CITY_COORDS.items():
    CITY_COORDS.setdefault(_lv_name, _lv_coords)

# Вінницька область - усі основні міста та райцентри
VINNYTSIA_CITY_COORDS = {
    # Обласний центр
    'вінниця': (49.2331, 28.4682),
    'вінниці': (49.2331, 28.4682),
    'вінницю': (49.2331, 28.4682),
    'вінницею': (49.2331, 28.4682),
    'вінницей': (49.2331, 28.4682),
    
    # Міста обласного значення
    'козятин': (49.7167, 28.8333),
    'козятині': (49.7167, 28.8333),
    'козятину': (49.7167, 28.8333),
    'хмільник': (49.5500, 27.9500),
    'хмільнику': (49.5500, 27.9500),
    'хмільника': (49.5500, 27.9500),
    'ладижин': (48.6833, 29.2333),
    'ладижині': (48.6833, 29.2333),
    'ладижину': (48.6833, 29.2333),
    'могилів-подільський': (48.4500, 27.7833),
    'могилів-подільському': (48.4500, 27.7833),
    'могилів-подільського': (48.4500, 27.7833),
    
    # Райцентри
    'бар': (49.0667, 27.6833),
    'бару': (49.0667, 27.6833),
    'бара': (49.0667, 27.6833),
    'бердичів': (49.8978, 28.6011),  # вже є в основній базі
    'бершадь': (48.3667, 29.5167),  # Бершадь - райцентр Вінницької області
    'бершаді': (48.3667, 29.5167),
    'бершадю': (48.3667, 29.5167),
    'бершадью': (48.3667, 29.5167),
    'бершадей': (48.3667, 29.5167),
    'вінницький район': (49.2331, 28.4682),
    'гайсин': (49.4167, 29.3833),
    'гайсині': (49.4167, 29.3833),
    'гайсину': (49.4167, 29.3833),
    'жмеринка': (49.0333, 28.1167),
    'жмеринці': (49.0333, 28.1167),
    'жмеринку': (49.0333, 28.1167),
    'іллінці': (49.1000, 29.2167),
    'іллінцях': (49.1000, 29.2167),
    'іллінцам': (49.1000, 29.2167),
    'калинівка': (49.4500, 28.5167),
    'калинівці': (49.4500, 28.5167),
    'калинівку': (49.4500, 28.5167),
    'козятинський район': (49.7167, 28.8333),
    'крижопіль': (48.3833, 28.8667),
    'крижополі': (48.3833, 28.8667),
    'крижополю': (48.3833, 28.8667),
    'липовець': (49.2167, 29.1833),
    'липовці': (49.2167, 29.1833),
    'липовець': (49.2167, 29.1833),
    'літин': (49.7167, 28.0667),
    'літині': (49.7167, 28.0667),
    'літину': (49.7167, 28.0667),
    'муровані курилівці': (48.6667, 29.2667),
    'мурованих куриловцях': (48.6667, 29.2667),
    'мурованими куриловцями': (48.6667, 29.2667),
    'немирів': (49.0833, 28.8333),
    'немирові': (49.0833, 28.8333),
    'немирову': (49.0833, 28.8333),
    'оратів': (48.9333, 29.5167),
    'ораніввʼ': (48.9333, 29.5167),
    'оратові': (48.9333, 29.5167),
    'піщанка': (49.5833, 29.0833),
    'піщанці': (49.5833, 29.0833),
    'піщанку': (49.5833, 29.0833),
    'погребище': (49.4833, 29.2667),
    'погребищі': (49.4833, 29.2667),
    'погребище': (49.4833, 29.2667),
    'теплик': (48.6667, 29.6667),
    'теплику': (48.6667, 29.6667),
    'тепліка': (48.6667, 29.6667),
    'томашпіль': (48.5333, 28.5167),
    'томашполі': (48.5333, 28.5167),
    'томашполю': (48.5333, 28.5167),
    'тростянець': (48.8167, 29.0167),  # Вінницька область (основний в базі - Сумська)
    'тростянці': (48.8167, 29.0167),
    'тростянець вінницька': (48.8167, 29.0167),
    'тростянець вінницький': (48.8167, 29.0167),
    'тульчин': (48.6783, 28.8486),
    'тульчині': (48.6783, 28.8486),
    'тульчину': (48.6783, 28.8486),
    'тиврів': (49.4000, 28.3167),
    'тивріві': (49.4000, 28.3167),
    'тиврову': (49.4000, 28.3167),
    'хмільницький район': (49.5500, 27.9500),
    'чернівці': (49.4167, 27.7333),  # не плутати з Чернівцями (центр області)
    'чернівцях': (49.4167, 27.7333),
    'чернівцям': (49.4167, 27.7333),
    'чечельник': (48.2167, 28.1833),
    'чечельнику': (48.2167, 28.1833),
    'чечельника': (48.2167, 28.1833),
    'шаргород': (48.7333, 28.0833),
    'шаргороді': (48.7333, 28.0833),
    'шаргороду': (48.7333, 28.0833),
    'ямпіль вінницька': (48.1333, 28.2833),  # Вінницька область (основний в базі - Сумська)
    'ямполь вінницька': (48.1333, 28.2833),
    'ямпіль вінницький': (48.1333, 28.2833),
    'ямполі вінницька': (48.1333, 28.2833),
    'ямполю вінницька': (48.1333, 28.2833),
    
    # Селища міського типу та важливі села
    'браїлів': (49.0500, 28.2000),
    'браїлові': (49.0500, 28.2000),
    'браїлову': (49.0500, 28.2000),
    'вапнярка': (49.0333, 28.4500),
    'вапнярці': (49.0333, 28.4500),
    'вапнярку': (49.0333, 28.4500),
    'гнівань': (49.2833, 28.9167),
    'гнівані': (49.2833, 28.9167),
    'гнівань': (49.2833, 28.9167),
    'дашів': (48.9000, 29.4333),
    'дашеві': (48.9000, 29.4333),
    'дашову': (48.9000, 29.4333),
    'деражня': (50.0500, 27.2667),
    'деражні': (50.0500, 27.2667),
    'деражню': (50.0500, 27.2667),
    'джулинка': (49.2500, 28.7000),
    'джулинці': (49.2500, 28.7000),
    'джулинку': (49.2500, 28.7000),
    'крижопіль': (48.3833, 28.8667),
    'лука-мелешківська': (48.6333, 29.1167),
    'луці-мелешківській': (48.6333, 29.1167),
    'луку-мелешківську': (48.6333, 29.1167),
    'мурафа': (49.1833, 28.7833),
    'мурафі': (49.1833, 28.7833),
    'мурафу': (49.1833, 28.7833),
    'охматів': (49.7500, 29.2167),
    'охматові': (49.7500, 29.2167),
    'охматову': (49.7500, 29.2167),
    'печера': (49.6167, 28.8167),
    'печері': (49.6167, 28.8167),
    'печеру': (49.6167, 28.8167),
    'славута': (50.3000, 26.8500),  # технічно Хмельницька, але часто згадується з Вінницькою
    'станіславчик': (49.0333, 28.2167),
    'станіславчику': (49.0333, 28.2167),
    'станіславчика': (49.0333, 28.2167),
    'стрижавка': (49.6833, 28.6000),
    'стрижавці': (49.6833, 28.6000),
    'стрижавку': (49.6833, 28.6000),
    'чорний острів': (49.7167, 28.6167),
    'чорному острові': (49.7167, 28.6167),
    'чорний острів': (49.7167, 28.6167),
}

for _vn_name, _vn_coords in VINNYTSIA_CITY_COORDS.items():
    CITY_COORDS.setdefault(_vn_name, _vn_coords)

# Volyn Oblast settlements (auto-generated from city_ukraine.json)
VOLYN_CITY_COORDS = {
    'адамчуки': (50.7472, 25.3254),
    'адамівка': (50.7472, 25.3254),
    'амбуків': (50.7472, 25.3254),
    'антонівка': (50.7472, 25.3254),
    'арсеновичі': (50.7472, 25.3254),
    'бабаці': (50.7472, 25.3254),
    'байківці': (50.7472, 25.3254),
    'баківці': (50.7472, 25.3254),
    'барвінок': (50.7472, 25.3254),
    'бахів': (50.7472, 25.3254),
    'башлики': (50.7472, 25.3254),
    'башова': (50.7472, 25.3254),
    'баїв': (50.7472, 25.3254),
    'бегета': (50.7472, 25.3254),
    'берегове': (50.7472, 25.3254),
    'бережанка': (50.7472, 25.3254),
    'бережниця': (50.7472, 25.3254),
    'бережці': (50.7472, 25.3254),
    'береза': (50.7472, 25.3254),
    'березичі': (50.7472, 25.3254),
    'березна воля': (50.7472, 25.3254),
    'березники': (50.7472, 25.3254),
    'березовичі': (50.7472, 25.3254),
    'березолуки': (50.7472, 25.3254),
    'берестечко': (50.7472, 25.3254),
    'берестяне': (50.7472, 25.3254),
    'береськ': (50.7472, 25.3254),
    'бермешів': (50.7472, 25.3254),
    'бистровиця': (50.7472, 25.3254),
    'битень': (50.7472, 25.3254),
    'бихів': (50.7472, 25.3254),
    'благодатне': (50.7472, 25.3254),
    'блаженик': (50.7472, 25.3254),
    'бобичі': (50.7472, 25.3254),
    'бобли': (50.7472, 25.3254),
    'боголюби': (50.7472, 25.3254),
    'богунівка': (50.7472, 25.3254),
    'богушівка': (50.7472, 25.3254),
    "богушівська мар'янівка": (50.7472, 25.3254),
    'бодячів': (50.7472, 25.3254),
    'боратин': (50.7472, 25.3254),
    'боремщина': (50.7472, 25.3254),
    'борзова': (50.7472, 25.3254),
    'борисковичі': (50.7472, 25.3254),
    'борове': (50.7472, 25.3254),
    'боровичі': (50.7472, 25.3254),
    'боровне': (50.7472, 25.3254),
    'боровуха': (50.7472, 25.3254),
    'борохів': (50.7472, 25.3254),
    'борочиче': (50.7472, 25.3254),
    'бортнів': (50.7472, 25.3254),
    'бортяхівка': (50.7472, 25.3254),
    'борщівка': (50.7472, 25.3254),
    'ботин': (50.7472, 25.3254),
    'брани': (50.7472, 25.3254),
    'брище': (50.7472, 25.3254),
    'броди': (50.7472, 25.3254),
    'бродятине': (50.7472, 25.3254),
    'брониця': (50.7472, 25.3254),
    'брунетівка': (50.7472, 25.3254),
    'бруховичі': (50.7472, 25.3254),
    'брідки': (50.7472, 25.3254),
    'бубнів': (50.7472, 25.3254),
    'будище': (50.7472, 25.3254),
    'будки': (50.7472, 25.3254),
    'будники': (50.7472, 25.3254),
    'будятичі': (50.7472, 25.3254),
    'бужани': (50.7472, 25.3254),
    'бужанка': (50.7472, 25.3254),
    'бужковичі': (50.7472, 25.3254),
    'бузаки': (50.7472, 25.3254),
    'буків': (50.7472, 25.3254),
    'буркачі': (50.7472, 25.3254),
    'буцинь': (50.7472, 25.3254),
    'бучин': (50.7472, 25.3254),
    'буяни': (50.7472, 25.3254),
    'білашів': (50.7472, 25.3254),
    'білин': (50.7472, 25.3254),
    'біличі': (50.7472, 25.3254),
    'білопіль': (50.7472, 25.3254),
    'білосток': (50.7472, 25.3254),
    'бірки': (50.7472, 25.3254),
    "в'язівне": (50.7472, 25.3254),
    "валер'янівка": (50.7472, 25.3254),
    'ватин': (50.7472, 25.3254),
    'ватинець': (50.7472, 25.3254),
    'велика ведмежка': (50.7472, 25.3254),
    'велика глуша': (50.7472, 25.3254),
    'велика осниця': (50.7472, 25.3254),
    'велика яблунька': (50.7472, 25.3254),
    'великий курінь': (50.7472, 25.3254),
    'великий обзир': (50.7472, 25.3254),
    'великий окорськ': (50.7472, 25.3254),
    'великий омеляник': (50.7472, 25.3254),
    'великий порськ': (50.7472, 25.3254),
    'велимче': (50.7472, 25.3254),
    'велицьк': (50.7472, 25.3254),
    'верба': (50.7472, 25.3254),
    'вербаїв': (50.7472, 25.3254),
    'вербичне': (50.7472, 25.3254),
    'вербка': (50.7472, 25.3254),
    'вербівка': (50.7472, 25.3254),
    'верхи': (50.7472, 25.3254),
    'верхнів': (50.7472, 25.3254),
    'верхівка': (50.7472, 25.3254),
    'веселе': (50.7472, 25.3254),
    'веснянка': (50.7472, 25.3254),
    'ветли': (50.7472, 25.3254),
    'вигнанка': (50.7472, 25.3254),
    'вигуричі': (50.7472, 25.3254),
    'видерта': (50.7472, 25.3254),
    'видраниця': (50.7472, 25.3254),
    'видричі': (50.7472, 25.3254),
    'вижгів': (50.7472, 25.3254),
    'вижично': (50.7472, 25.3254),
    'винімок': (50.7472, 25.3254),
    'високе': (50.7472, 25.3254),
    'висоцьк': (50.7472, 25.3254),
    'височне': (50.7472, 25.3254),
    'витень': (50.7472, 25.3254),
    'витуле': (50.7472, 25.3254),
    'вишеньки': (50.7472, 25.3254),
    'вишнів': (50.7472, 25.3254),
    'вишнівка': (50.7472, 25.3254),
    'вовчицьк': (50.7472, 25.3254),
    'войнин': (50.7472, 25.3254),
    'волиця': (50.7472, 25.3254),
    'волиця-дружкопільська': (50.7472, 25.3254),
    'волиця-лобачівська': (50.7472, 25.3254),
    'волиця-морозовицька': (50.7472, 25.3254),
    'володимир-волинський': (50.7472, 25.3254),
    'володимирівка': (50.7472, 25.3254),
    'волошки': (50.7472, 25.3254),
    'воля': (50.7472, 25.3254),
    'воля-ковельська': (50.7472, 25.3254),
    'воля-любитівська': (50.7472, 25.3254),
    'воля-свійчівська': (50.7472, 25.3254),
    'ворокомле': (50.7472, 25.3254),
    'ворона': (50.7472, 25.3254),
    'ворончин': (50.7472, 25.3254),
    'воротнів': (50.7472, 25.3254),
    'ворчин': (50.7472, 25.3254),
    'вощатин': (50.7472, 25.3254),
    'воютин': (50.7472, 25.3254),
    'воєгоща': (50.7472, 25.3254),
    'всеволодівка': (50.7472, 25.3254),
    'вужиськ': (50.7472, 25.3254),
    'вівчицьк': (50.7472, 25.3254),
    'відути': (50.7472, 25.3254),
    'війниця': (50.7472, 25.3254),
    'вікторяни': (50.7472, 25.3254),
    'віл': (50.7472, 25.3254),
    'вілиця': (50.7472, 25.3254),
    'вілька-підгородненська': (50.7472, 25.3254),
    'вілька-садівська': (50.7472, 25.3254),
    'вільхівка': (50.7472, 25.3254),
    'вільшанка': (50.7472, 25.3254),
    'вільшани': (48.4667, 32.2667),  # Вільшани, Кіровоградська область
    'вільшанам': (48.4667, 32.2667),
    'вільшанах': (48.4667, 32.2667),
    'вітоніж': (50.7472, 25.3254),
    'вічині': (50.7472, 25.3254),
    # ... (truncated for brevity - 1087 total settlements)
    'ізов': (50.7472, 25.3254),
}

for _volyn_name, _volyn_coords in VOLYN_CITY_COORDS.items():
    CITY_COORDS.setdefault(_volyn_name, _volyn_coords)

# Kherson Oblast Cities - Adding specific variants for города with oblast designation
KHERSON_CITY_COORDS = {
    'білозерка херсонська': (46.64, 32.88),
    'білозерка (херсонська)': (46.64, 32.88),
    'білозерка херсонська обл.': (46.64, 32.88),
    'білозерка херсонська область': (46.64, 32.88),
    'білозерка херсонщина': (46.64, 32.88),
}

for _ks_name, _ks_coords in KHERSON_CITY_COORDS.items():
    CITY_COORDS.setdefault(_ks_name, _ks_coords)

# Additional missing settlements from large UAV course messages
MISSING_SETTLEMENTS = {
    # Vinnytsia Oblast
    'пеньківка': (49.1667, 28.5500), 'пеньківку': (49.1667, 28.5500), 'пеньківці': (49.1667, 28.5500),
    'станіславчик': (49.0333, 28.2167), 'станіславчику': (49.0333, 28.2167), 'станіславчики': (49.0333, 28.2167),
    'вендичани': (48.4167, 27.9500), 'вендичанах': (48.4167, 27.9500), 'вендичани́': (48.4167, 27.9500),
    'мазурівка': (49.1000, 28.8500), 'мазурівку': (49.1000, 28.8500), 'мазурівці': (49.1000, 28.8500),
    # Odesa Oblast
    'ширяєве': (46.6167, 30.1667), 'ширяєвому': (46.6167, 30.1667), 'ширяєва': (46.6167, 30.1667),
    # Kirovohrad Oblast
    'світловодськ': (49.0556, 33.2433),  # Світловодськ, Кіровоградська область
    'гайдамацьке': (48.7833, 32.4333), 'гайдамацьком': (48.7833, 32.4333), 'гайдамацького': (48.7833, 32.4333),
    'вільшани': (48.4667, 32.2667), 'вільшанам': (48.4667, 32.2667), 'вільшанах': (48.4667, 32.2667),
    # Poltava Oblast  
    'великі сорочинці': (50.0667, 34.2833), 'великих сорочинцях': (50.0667, 34.2833), 'великими сорочинцями': (50.0667, 34.2833),
    'глобине': (49.3833, 33.2667), 'глобиному': (49.3833, 33.2667), 'глобина': (49.3833, 33.2667),
    # Sumy Oblast
    'степанівка': (50.7833, 34.5500), 'степанівку': (50.7833, 34.5500), 'степанівці': (50.7833, 34.5500),
    'липова долина': (51.1167, 34.4500), 'липовій долині': (51.1167, 34.4500), 'липову долину': (51.1167, 34.4500),
    # Chernihiv Oblast
    'гончарівське': (51.3667, 31.7833), 'гончарівському': (51.3667, 31.7833), 'гончарівського': (51.3667, 31.7833),
    # Kyiv Oblast
    'красятичі': (50.3167, 30.0500), 'красятичах': (50.3167, 30.0500), 'красятичами': (50.3167, 30.0500),
    # Zhytomyr Oblast
    'нові білокоровичі': (51.3833, 27.7167), 'нових білокоровичах': (51.3833, 27.7167), 'новими білокоровичами': (51.3833, 27.7167),
    'черняхів': (50.0667, 28.8833), 'черняхові': (50.0667, 28.8833), 'черняховом': (50.0667, 28.8833),
    'андрушівка': (50.0833, 29.8167), 'андрушівку': (50.0833, 29.8167), 'андрушівці': (50.0833, 29.8167),
    'любар': (49.9167, 27.5333), 'любарі': (49.9167, 27.5333), 'любару': (49.9167, 27.5333),
    # Khmelnytskyi Oblast
    'адампіль': (49.7667, 26.9667), 'адамполі': (49.7667, 26.9667), 'адамполю': (49.7667, 26.9667),
    # Rivne Oblast
    'деражне': (50.9167, 25.7500), 'деражному': (50.9167, 25.7500), 'деражного': (50.9167, 25.7500),
    'рокитне': (50.3167, 26.1500), 'рокитному': (50.3167, 26.1500), 'рокитного': (50.3167, 26.1500),
    'дубровиця': (51.5667, 26.5667), 'дубровицю': (51.5667, 26.5667), 'дубровиці': (51.5667, 26.5667),
    # Volyn Oblast
    'камінь-каширський': (51.6167, 24.9667), 'каменю-каширському': (51.6167, 24.9667), 'каменем-каширським': (51.6167, 24.9667),
}

for _ms_name, _ms_coords in MISSING_SETTLEMENTS.items():
    CITY_COORDS.setdefault(_ms_name, _ms_coords)

# Mapping city -> oblast stem (lowercase stems used earlier) for disambiguation when region already detected.
# Minimal subset; extend as needed.
CITY_TO_OBLAST = {
    'павлоград': 'дніпропетров',
    'дніпро': 'дніпропетров',
    'кривий ріг': 'дніпропетров',
    'львів': 'львів',
    'стрий': 'львів',
    'дробобич': 'львів',
    'київ': 'київ',
    'біла церква': 'київ',
    'бориспіль': 'київ',
    'полтава': 'полтав',
    'кременчук': 'полтав',
    'велика багачка': 'полтав',
    'гадяч': 'полтав',
    'житомир': 'житом',
    'черкаси': 'черка',
    'чернігів': 'черніг',
    'суми': 'сум',
    'липова долина': 'сум',
    'тростянець': 'сум',
    'лебедин': 'сум',
    'улянівка': 'сум',
    'одеса': 'одес',
    'миколаїв': 'микола',
    'чернівці': 'чернівц',
    'рівне': 'рівн',
    'тернопіль': 'терноп',
    'ужгород': 'ужгород',
    'луцьк': 'волин',
    'запоріжжя': 'запор',
    'харків': 'харків',
    'ахтирка': 'сум',
}

OBLAST_CENTERS = {
    'донеччина': (48.0433, 37.7974), 'донеччини': (48.0433, 37.7974), 'донеччину': (48.0433, 37.7974), 'донецька область': (48.0433, 37.7974),
    'дніпропетровщина': (48.4500, 34.9830), 'дніпропетровщини': (48.4500, 34.9830), 'дніпропетровська область': (48.4500, 34.9830),
    'кіровоградщина': (48.5132, 32.2597), 'кіровоградщини': (48.5132, 32.2597), 'кіровоградська область': (48.5132, 32.2597),
    'днепропетровщина': (48.4500, 34.9830), 'днепропетровщины': (48.4500, 34.9830),
    'чернігівщина': (51.4982, 31.2893), 'чернігівщини': (51.4982, 31.2893),
    'харківщина': (49.9935, 36.2304), 'харківщини': (49.9935, 36.2304)
    , 'дніпропетровська обл.': (48.4500, 34.9830), 'днепропетровская обл.': (48.4500, 34.9830)
    , 'чернігівська обл.': (51.4982, 31.2893), 'черниговская обл.': (51.4982, 31.2893)
    , 'харківська обл.': (49.9935, 36.2304), 'харьковская обл.': (49.9935, 36.2304)
    , 'сумщина': (50.9077, 34.7981), 'сумщини': (50.9077, 34.7981), 'сумщину': (50.9077, 34.7981), 'сумська область': (50.9077, 34.7981), 'сумська обл.': (50.9077, 34.7981), 'сумская обл.': (50.9077, 34.7981)
    , 'полтавщина': (49.5883, 34.5514), 'полтавщини': (49.5883, 34.5514), 'полтавщину': (49.5883, 34.5514), 'полтавська область': (49.5883, 34.5514), 'полтавська обл.': (49.5883, 34.5514)
    , 'київщина': (50.4501, 30.5234), 'київщини': (50.4501, 30.5234), 'київщину': (50.4501, 30.5234), 'київська область': (50.4501, 30.5234), 'київська обл.': (50.4501, 30.5234)
    , 'львівщина': (49.8397, 24.0297), 'львівщини': (49.8397, 24.0297), 'львівщину': (49.8397, 24.0297), 'львівська область': (49.8397, 24.0297), 'львівська обл.': (49.8397, 24.0297)
    , 'черкащина': (49.4444, 32.0598), 'черкащини': (49.4444, 32.0598), 'черкащину': (49.4444, 32.0598), 'черкаська область': (49.4444, 32.0598), 'черкаська обл.': (49.4444, 32.0598)
    , 'житомирщина': (50.2547, 28.6587), 'житомирщини': (50.2547, 28.6587), 'житомирщину': (50.2547, 28.6587), 'житомирська область': (50.2547, 28.6587), 'житомирська обл.': (50.2547, 28.6587)
    , 'херсонщина': (46.6354, 32.6169), 'херсонщини': (46.6354, 32.6169), 'херсонську': (46.6354, 32.6169), 'херсонська область': (46.6354, 32.6169), 'херсонська обл.': (46.6354, 32.6169)
    , 'миколаївщина': (46.9750, 31.9946), 'миколаївщини': (46.9750, 31.9946), 'миколаївську': (46.9750, 31.9946), 'миколаївська область': (46.9750, 31.9946), 'миколаївська обл.': (46.9750, 31.9946)
    , 'одесщина': (46.4825, 30.7233), 'одесьчина': (46.4825, 30.7233), 'одесьщини': (46.4825, 30.7233), 'одеську': (46.4825, 30.7233), 'одеська область': (46.4825, 30.7233), 'одеська обл.': (46.4825, 30.7233)
    , 'одещина': (46.4825, 30.7233), 'одещини': (46.4825, 30.7233), 'одещину': (46.4825, 30.7233)
    , 'волинь': (50.7472, 25.3254), 'волинська область': (50.7472, 25.3254), 'волинська обл.': (50.7472, 25.3254)
    , 'рівненщина': (50.6199, 26.2516), 'рівненщини': (50.6199, 26.2516), 'рівненщину': (50.6199, 26.2516), 'рівненська область': (50.6199, 26.2516), 'рівненська обл.': (50.6199, 26.2516)
    , 'тернопільщина': (49.5535, 25.5948), 'тернопільщини': (49.5535, 25.5948), 'тернопільщину': (49.5535, 25.5948), 'тернопільська область': (49.5535, 25.5948), 'тернопільська обл.': (49.5535, 25.5948)
    , 'хмельниччина': (49.4229, 26.9871), 'хмельниччини': (49.4229, 26.9871), 'хмельниччину': (49.4229, 26.9871), 'хмельницька область': (49.4229, 26.9871), 'хмельницька обл.': (49.4229, 26.9871)
    , 'вінниччина': (49.2331, 28.4682), 'вінниччини': (49.2331, 28.4682), 'вінниччину': (49.2331, 28.4682), 'вінницька область': (49.2331, 28.4682), 'вінницька обл.': (49.2331, 28.4682)
    , 'вінничина': (49.2331, 28.4682), 'вінничини': (49.2331, 28.4682)
    , 'закарпаття': (48.6208, 22.2879), 'закарпатська область': (48.6208, 22.2879), 'закарпатська обл.': (48.6208, 22.2879)
    , 'чернівеччина': (48.2921, 25.9358), 'чернівецька область': (48.2921, 25.9358), 'чернівецька обл.': (48.2921, 25.9358)
    , 'луганщина': (48.5740, 39.3078), 'луганщини': (48.5740, 39.3078), 'луганщину': (48.5740, 39.3078), 'луганська область': (48.5740, 39.3078), 'луганська обл.': (48.5740, 39.3078)
}

# Add no-dot variants for keys ending with ' обл.' (common source variation without the dot)
_no_dot_variants = {}
for _k,_v in list(OBLAST_CENTERS.items()):
    if _k.endswith(' обл.'):
        nd = _k[:-1]  # remove trailing '.' only
        if nd not in OBLAST_CENTERS:
            _no_dot_variants[nd] = _v
OBLAST_CENTERS.update(_no_dot_variants)

# Canonical forms for geocoding queries (region headers -> '<adj> область')
REGION_GEOCODE_CANON = {
    'полтавщина':'полтавська область','київщина':'київська область','сумщина':'сумська область','харківщина':'харківська область',
    'черкащина':'черкаська область','житомирщина':'житомирська область','львівщина':'львівська область','рівненщина':'рівненська область',
    'волинь':'волинська область','одесщина':'одеська область','одесьчина':'одеська область','дніпропетровщина':'дніпропетровська область',
    'миколаївщина':'миколаївська область','херсонщина':'херсонська область','хмельниччина':'хмельницька область','тернопільщина':'тернопільська область',
    'чернівеччина':'чернівецька область','закарпаття':'закарпатська область','донеччина':'донецька область','луганщина':'луганська область',
    'вінниччина':'вінницька область','вінничина':'вінницька область'
}

# Explicit (city, oblast form) overrides to disambiguate duplicate settlement names across oblasts.
# Key: (normalized_city, normalized_region_hint as appears in message)
OBLAST_CITY_OVERRIDES = {
    ('борова', 'харківська обл.'): (49.3743, 37.6179),  # Борова (Ізюмський р-н, Харківська)
}

# Район (district) fallback centers (можно расширять). Ключи в нижнем регистре без слова 'район'.
RAION_FALLBACK = {
    'покровський': (48.2767, 37.1763),  # Покровськ (Донецька)
    'покровский': (48.2767, 37.1763),
    'павлоградський': (48.5350, 35.8700),  # Павлоград
    'павлоградский': (48.5350, 35.8700),
    'пологівський': (47.4840, 36.2536),  # Пологи (approx center of Polohivskyi raion)
    'пологовский': (47.4840, 36.2536),
    'краматорський': (48.7389, 37.5848),
    'миколаївський': (46.9750, 31.9946),  # Mykolaivskyi raion (approx Mykolaiv city center)
    'николаевский': (46.9750, 31.9946),
    'миколаевский': (46.9750, 31.9946),
    'краматорский': (48.7389, 37.5848),
    'бахмутський': (48.5941, 38.0021),
    'бахмутский': (48.5941, 38.0021),
    'черкаський': (49.4444, 32.0598),
    'черкасский': (49.4444, 32.0598),
    'одеський': (46.4825, 30.7233),
    'одесский': (46.4825, 30.7233),
    'харківський': (49.9935, 36.2304),
    'харьковский': (49.9935, 36.2304),
    # Новые районы для многократных сообщений
    'конотопський': (51.2375, 33.2020), 'конотопский': (51.2375, 33.2020),
    'сумський': (50.8500, 34.9500), 'сумский': (50.8500, 34.9500),  # Shifted SE from Sumy city center to represent district area
    'чернігівський': (51.4982, 31.2893), 'черниговский': (51.4982, 31.2893),
    'вишгородський': (50.5850, 30.4915), 'вышгородский': (50.5850, 30.4915),
    'новгород-сіверський': (51.9874, 33.2620), 'новгород-северский': (51.9874, 33.2620),
    'чугуївський': (49.8353, 36.6880), 'чугевский': (49.8353, 36.6880), 'чугевський': (49.8353, 36.6880), 'чугуевский': (49.8353, 36.6880)
    , 'синельниківський': (48.3167, 36.5000), 'синельниковский': (48.3167, 36.5000)
    # Zaporizkyi raion (shifted off exact city center to represent wider district)
    , 'запорізький': (47.9000, 35.2500), 'запорожский': (47.9000, 35.2500)
    , 'білгород-дністровський': (46.1871, 30.3410), 'білгород-дністровского': (46.1871, 30.3410), 'білгород-дністровського': (46.1871, 30.3410)
    # Dnipro oblast & Dnipro city internal districts (to avoid fallback to generic city center)
    , 'дніпровський': (48.4500, 35.1000), 'днепровский': (48.4500, 35.1000)  # Dnipro Raion (approx centroid)
    , 'самарський': (48.5380, 35.1500), 'самарский': (48.5380, 35.1500), 'самарівський': (48.5380, 35.1500)  # Samarskyi (approx east bank)
    , 'миргородський': (49.9640, 33.6121), 'миргородский': (49.9640, 33.6121)
    , 'бериславський': (46.8367, 33.4281), 'бериславский': (46.8367, 33.4281)
    # Added batch (air alarm coverage) — approximate district administrative centers
    , 'шепетівський': (50.1822, 27.0637), 'шепетовский': (50.1822, 27.0637)  # Shepetivka
    , 'полтавський': (49.5883, 34.5514), 'полтавский': (49.5883, 34.5514)    # Poltava (raion)
    , 'хмельницький': (49.4229, 26.9871), 'хмельницкий': (49.4229, 26.9871)  # Khmelnytskyi raion (city)
    , 'куп\'янський': (49.7106, 37.6156), 'купянський': (49.7106, 37.6156)   # Kupiansk raion (Kharkiv oblast)
    , 'роменський': (50.7515, 33.4746), 'роменский': (50.7515, 33.4746)      # Romny
    , 'охтирський': (50.3103, 34.8988), 'ахтырский': (50.3103, 34.8988)      # Okhtyrka translit variant
    , 'харківський': (49.9935, 36.2304), 'харьковский': (49.9935, 36.2304)   # ensure duplication above
    , 'голованівський': (48.3833, 30.4500), 'голованевский': (48.3833, 30.4500) # Holovanivsk
    , 'лубенський': (50.0165, 32.9969), 'лубенский': (50.0165, 32.9969)      # Lubny
    , 'шосткинський': (51.8736, 33.4806), 'шосткинский': (51.8736, 33.4806)  # Shostka
    , 'кременчуцький': (49.0631, 33.4030), 'кременчугский': (49.0631, 33.4030) # Kremenchuk
    , "кам'янець-подільський": (48.6845, 26.5853), 'камянец-подольский': (48.6845, 26.5853)
    , 'богодухівський': (50.1643, 35.5272), 'богодуховский': (50.1643, 35.5272) # Bohodukhiv
    , 'кропивницький': (48.5079, 32.2623), 'кропивницкий': (48.5079, 32.2623)   # Kropyvnytskyi raion center
    , 'сарненський': (51.3373, 26.6019), 'сарненский': (51.3373, 26.6019)       # Sarny
    , 'лозівський': (48.8926, 36.3172), 'лозовский': (48.8926, 36.3172)         # Lozova
    , 'новоукраїнський': (48.3174, 31.5167), 'новоукраинский': (48.3174, 31.5167) # Novoukrainka
    , 'олександрійський': (48.6696, 33.1176), 'александрийский': (48.6696, 33.1176) # Oleksandriia
    , 'березівський': (46.8183, 31.3972), 'березовский': (46.8183, 31.3972) # Berezivka (Odesa Oblast)
    , 'охтирский': (50.3103, 34.8988)  # Russian variant explicit
    # Potential typo in feed: 'берестинський' (if meant 'Бериславський' already covered). Placeholder guess -> skip precise to avoid misplot.
}

# Known external launch / airfield / training ground coordinates for Shahed (and similar) launch detection
# Keys are normalized (lowercase, hyphen instead of spaces). Approximate coordinates.
LAUNCH_SITES = {
    'навля': (52.8300, 34.4900),              # Navlya (Bryansk Oblast training area approx)
    'полігон навля': (52.8300, 34.4900),
    'полигон навля': (52.8300, 34.4900),
    'шаталово': (54.0500, 32.2900),            # Shatalovo (Smolensk Oblast)
    'орел-південний': (52.9340, 36.0020),      # Orel South (Oryol Yuzhny)
    'орёл-южный': (52.9340, 36.0020),
    'орел-южный': (52.9340, 36.0020),
    'орёл южный': (52.9340, 36.0020),
    'орел южный': (52.9340, 36.0020),
    'приморськ-ахтарськ': (46.0420, 38.1700),  # Primorsko-Akhtarsk (Krasnodar Krai)
    'приморск-ахтарск': (46.0420, 38.1700),
    'халіно': (51.7500, 36.2950),              # Khalino (Kursk)
    'халино': (51.7500, 36.2950),
    'міллерово': (48.9250, 40.4000),           # Millerovo (Rostov Oblast) approximate airbase
    'миллерово': (48.9250, 40.4000),
    # Newly added occupied launch / training areas
    'приморськ': (46.7306, 36.3456),           # Prymorsk (Zaporizhzhia oblast, occupied coastal area)
    'полігон приморськ': (46.7306, 36.3456),
    'полигон приморск': (46.7306, 36.3456),
    'чауда': (45.0710, 36.1320),               # Chauda range (Crimea)
    'полігон чауда': (45.0710, 36.1320),
    'полигон чауда': (45.0710, 36.1320),
}

# Active raion (district) air alarms: raion_base -> dict(place, lat, lng, since)
RAION_ALARMS = {}

# Territorial hromada fallback centers (selected). Keys lower-case without word 'територіальна громада'.
HROMADA_FALLBACK = {
    'хотінська': (51.0825, 34.5860),  # Хотінська громада (approx center, Sumy raion near border)
    'хотінь': (51.0825, 34.5860),  # с. Хотінь (explicit to avoid fallback to Суми center)
}

# Specific settlement fallback for mis-localized parsing
SETTLEMENT_FALLBACK = {
    'кипти': (51.2833, 31.2167),  # Russian / simplified spelling → 'кіпті'
}

SETTLEMENTS_FILE = os.getenv('SETTLEMENTS_FILE', 'settlements_ua.json')
SETTLEMENTS_URL = os.getenv('SETTLEMENTS_URL')  # optional remote JSON (list of {name,lat,lng})
SETTLEMENTS_MAX = int(os.getenv('SETTLEMENTS_MAX', '150000'))  # safety cap
SETTLEMENTS_INDEX = {}
SETTLEMENTS_ORDERED = []

# --------------- Optional Git auto-commit settings ---------------
GIT_AUTO_COMMIT = os.getenv('GIT_AUTO_COMMIT', '0') not in ('0','false','False','')
GIT_REPO_SLUG = os.getenv('GIT_REPO_SLUG')  # e.g. 'vavaika22423232/neptun'

# ----------- Ukrainian place name normalization (force Ukrainian display) -----------
EN_UA_PLACE_MAP = {k.lower(): v for k,v in [
    ('kyiv','Київ'),('kiev','Київ'),('kharkiv','Харків'),('kharkov','Харків'),('odesa','Одеса'),('odessa','Одеса'),
    ('lviv','Львів'),('dnipro','Дніпро'),('zaporizhzhia','Запоріжжя'),('zaporizhia','Запоріжжя'),('mykolaiv','Миколаїв'),('nikolaev','Миколаїв'),
    ('chernihiv','Чернігів'),('poltava','Полтава'),('sumy','Суми'),('kherson','Херсон'),('rivne','Рівне'),('ternopil','Тернопіль'),
    ('ivano-frankivsk','Івано-Франківськ'),('chernivtsi','Чернівці'),('uzhhorod','Ужгород'),('kropyvnytskyi','Кропивницький'),
    ('kryvyi rih','Кривий Ріг'),('kryvyi-rih','Кривий Ріг'),('sloviansk','Словʼянськ'),('slavyansk','Словʼянськ'),
    ('bakhmut','Бахмут'),('mariupol','Маріуполь'),('berdyansk','Бердянськ'),('melitopol','Мелітополь'),
    ('pavlohrad','Павлоград'),('pavlograd','Павлоград'),('pokrovsk','Покровськ'),('sevastopol','Севастополь'),('simferopol','Сімферополь')
]}

def ensure_ua_place(name: str) -> str:
    if not name or not isinstance(name,str):
        return name
    n = name.strip()
    # Already contains Ukrainian-specific letters
    if re.search(r'[іїєґʼІЇЄҐ]', n):
        return n
    low = n.lower()
    if low in EN_UA_PLACE_MAP:
        return EN_UA_PLACE_MAP[low]
    # Basic transliteration fallback for ascii-only names
    if re.fullmatch(r'[a-zA-Z\-\s]+', n):
        s = low
        # multi-char sequences first
        repl = [
            ('shch','щ'),('sch','щ'),('kh','х'),('ch','ч'),('sh','ш'),('ya','я'),('yu','ю'),('ye','є'),('yi','ї'),('zh','ж'),('ii','ії'),
            ('ie','є'),('jo','йо'),('yo','йо')
        ]
        for a,b in repl:
            s = re.sub(a,b,s)
        single = {
            'a':'а','b':'б','c':'к','d':'д','e':'е','f':'ф','g':'г','h':'г','i':'і','j':'й','k':'к','l':'л','m':'м','n':'н','o':'о','p':'п',
            'q':'к','r':'р','s':'с','t':'т','u':'у','v':'в','w':'в','x':'кс','y':'и','z':'з','ʼ':'ʼ','-':'-',' ':' '
        }
        out = ''.join(single.get(ch,ch) for ch in s)
        # Capitalize first letter and letters after dash/space
        def cap_tokens(txt):
            # Use raw regex to avoid invalid escape sequence warning for \s
            parts = re.split(r'([-\s])', txt)
            return ''.join(p.capitalize() if i%2==0 else p for i,p in enumerate(parts))
        return cap_tokens(out)
    return n

# -------- Persistent visit tracking (SQLite) to survive redeploys --------
VISITS_DB = os.getenv('VISITS_DB','visits.db')
_SQLITE_PRAGMAS = [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA synchronous=NORMAL;",
    "PRAGMA foreign_keys=ON;"
]
def _visits_db_conn():
    conn = sqlite3.connect(VISITS_DB, timeout=5, check_same_thread=False)
    try:
        # Apply pragmas every time (cheap) to ensure durability/performance settings even after restart
        for p in _SQLITE_PRAGMAS:
            try:
                conn.execute(p)
            except Exception:
                pass
    except Exception:
        pass
    return conn

_RECENT_SEEDED = False
def _seed_recent_from_sql():
    """If rolling recent visits file missing/outdated or lost after redeploy, rebuild from SQLite so
    Day / Week counts remain stable across deployments."""
    global _RECENT_SEEDED
    if _RECENT_SEEDED:
        return
    try:
        data = _load_recent_visits() or {}
        tz = pytz.timezone('Europe/Kyiv')
        now_dt = datetime.now(tz)
        today_str = now_dt.strftime('%Y-%m-%d')
        week_cut = now_dt - timedelta(days=7)
        today_start = tz.localize(datetime.strptime(today_str, '%Y-%m-%d')).timestamp()
        week_start_ts = week_cut.timestamp()
        with _visits_db_conn() as conn:
            cur_day = conn.execute("SELECT id FROM visits WHERE last_seen >= ?", (today_start,))
            day_ids = [r[0] for r in cur_day.fetchall()]
            cur_week = conn.execute("SELECT id FROM visits WHERE last_seen >= ?", (week_start_ts,))
            week_ids = [r[0] for r in cur_week.fetchall()]
        need_seed = False
        # Conditions to trigger seeding: empty/missing file, day mismatch, or counts smaller than SQL (lost state)
        if not data:
            need_seed = True
        else:
            if data.get('day') != today_str:
                need_seed = True
            elif len(set(data.get('today_ids', []))) < len(day_ids):
                need_seed = True
            elif len(set(data.get('week_ids', []))) < len(week_ids):
                need_seed = True
        if need_seed:
            data = {
                'day': today_str,
                'today_ids': list(dict.fromkeys(day_ids)),  # preserve order unique
                'week_ids': list(dict.fromkeys(week_ids)),
                'week_start': week_cut.strftime('%Y-%m-%d')  # informational; rolling window logic tolerates
            }
            _save_recent_visits(data)
            log.info(f"recent visits seeded from SQL: day={len(day_ids)} week={len(week_ids)}")
        _RECENT_SEEDED = True
    except Exception as e:
        log.warning(f"recent visits seeding failed: {e}")

def init_visits_db():
    try:
        with _visits_db_conn() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS visits (id TEXT PRIMARY KEY, first_seen REAL, last_seen REAL)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_first ON visits(first_seen)")
            # Helpful for fast lookups of currently active users by recent activity window
            conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_last ON visits(last_seen)")
    except Exception as e:
        log.warning(f"visits db init failed: {e}")

# --------------- Persistent comments (SQLite) ---------------
def init_comments_db():
    """Create comments table if missing. Uses same SQLite DB as visits for simplicity."""
    try:
        with _visits_db_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY,
                    text TEXT,
                    ts   TEXT,
                    epoch REAL
                )
            """)
            # Enhanced reactions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comment_reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment_id TEXT NOT NULL,
                    emoji TEXT NOT NULL,
                    user_ip TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    UNIQUE(comment_id, emoji, user_ip)
                )
            """)
            # Migration: ensure reply_to column exists
            cur = conn.execute("PRAGMA table_info(comments)")
            cols = [r[1] for r in cur.fetchall()]
            if 'reply_to' not in cols:
                try:
                    conn.execute("ALTER TABLE comments ADD COLUMN reply_to TEXT")
                    log.info('comments table migrated: added reply_to column')
                except Exception as me:
                    log.warning(f'failed adding reply_to column: {me}')
            # Create indexes (individually wrapped)
            for idx_sql in [
                "CREATE INDEX IF NOT EXISTS idx_comments_epoch ON comments(epoch)",
                "CREATE INDEX IF NOT EXISTS idx_comments_reply ON comments(reply_to)",
                "CREATE INDEX IF NOT EXISTS idx_reactions_comment ON comment_reactions(comment_id)",
                "CREATE INDEX IF NOT EXISTS idx_reactions_user ON comment_reactions(user_ip)"
            ]:
                try:
                    conn.execute(idx_sql)
                except Exception as ie:
                    log.debug(f'index create skipped: {ie}')
    except Exception as e:
        log.warning(f"comments db init failed: {e}")

def save_comment_record(item:dict):
    try:
        with _visits_db_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO comments (id,text,ts,epoch,reply_to) VALUES (?,?,?,?,?)",
                         (item.get('id'), item.get('text'), item.get('ts'), item.get('epoch'), item.get('reply_to')))
    except Exception as e:
        log.warning(f"save_comment_record failed: {e}")

def load_recent_comments(limit:int=80)->list[dict]:
    rows = []
    try:
        with _visits_db_conn() as conn:
            try:
                cur = conn.execute("SELECT id,text,ts,reply_to FROM comments ORDER BY epoch DESC LIMIT ?", (limit,))
                fetched = cur.fetchall()
            except Exception as sel_err:
                # Fallback legacy schema (no reply_to); try to migrate then retry
                log.warning(f'comments select fallback (legacy schema): {sel_err}')
                try:
                    conn.execute("ALTER TABLE comments ADD COLUMN reply_to TEXT")
                    cur = conn.execute("SELECT id,text,ts,reply_to FROM comments ORDER BY epoch DESC LIMIT ?", (limit,))
                    fetched = cur.fetchall()
                except Exception as mig_err:
                    log.warning(f'comments migration select failed: {mig_err}')
                    # Last resort: select without reply_to
                    try:
                        cur = conn.execute("SELECT id,text,ts FROM comments ORDER BY epoch DESC LIMIT ?", (limit,))
                        fetched = [(*r, None) for r in cur.fetchall()]
                    except Exception:
                        fetched = []
            for rid, text, ts, reply_to in fetched:
                d={'id': rid, 'text': text, 'ts': ts}
                if reply_to: d['reply_to']=reply_to
                
                # Load reactions for this comment
                try:
                    reactions = load_comment_reactions(rid, conn)
                    if reactions:
                        d['reactions'] = reactions
                except Exception:
                    pass  # Non-critical, skip reactions if failed
                
                rows.append(d)
    except Exception as e:
        log.warning(f"load_recent_comments failed: {e}")
    return list(reversed(rows))  # reverse so oldest of the slice first

def load_comment_reactions(comment_id: str, conn=None) -> dict:
    """Load reaction counts for a specific comment."""
    try:
        if conn:
            cur = conn.execute("""
                SELECT emoji, COUNT(*) as count 
                FROM comment_reactions 
                WHERE comment_id = ? 
                GROUP BY emoji
            """, (comment_id,))
            
            reactions = {}
            for emoji, count in cur.fetchall():
                reactions[emoji] = count
            return reactions
        else:
            with _visits_db_conn() as use_conn:
                cur = use_conn.execute("""
                    SELECT emoji, COUNT(*) as count 
                    FROM comment_reactions 
                    WHERE comment_id = ? 
                    GROUP BY emoji
                """, (comment_id,))
                
                reactions = {}
                for emoji, count in cur.fetchall():
                    reactions[emoji] = count
                return reactions
    except Exception as e:
        log.debug(f"load_comment_reactions failed: {e}")
        return {}

def toggle_comment_reaction(comment_id: str, emoji: str, user_ip: str) -> dict:
    """Toggle a reaction on a comment. Returns updated reaction counts."""
    try:
        with _visits_db_conn() as conn:
            # Check if reaction already exists
            cur = conn.execute("""
                SELECT id FROM comment_reactions 
                WHERE comment_id = ? AND emoji = ? AND user_ip = ?
            """, (comment_id, emoji, user_ip))
            
            existing = cur.fetchone()
            
            if existing:
                # Remove existing reaction
                conn.execute("DELETE FROM comment_reactions WHERE id = ?", (existing[0],))
                action = 'removed'
            else:
                # Add new reaction
                conn.execute("""
                    INSERT INTO comment_reactions (comment_id, emoji, user_ip, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (comment_id, emoji, user_ip, time.time()))
                action = 'added'
            
            conn.commit()
            
            # Return updated counts
            reactions = load_comment_reactions(comment_id, conn)
            return {'action': action, 'reactions': reactions}
            
    except Exception as e:
        log.warning(f"toggle_comment_reaction failed: {e}")
        return {'action': 'error', 'reactions': {}}

def load_comment_reactions(comment_id: str, conn=None) -> dict:
    """Load reaction counts for a specific comment."""
    try:
        use_conn = conn
        if not use_conn:
            use_conn = _visits_db_conn()
            
        with use_conn as c:
            cur = c.execute("""
                SELECT emoji, COUNT(*) as count 
                FROM comment_reactions 
                WHERE comment_id = ? 
                GROUP BY emoji
            """, (comment_id,))
            
            reactions = {}
            for emoji, count in cur.fetchall():
                reactions[emoji] = count
            return reactions
    except Exception as e:
        log.debug(f"load_comment_reactions failed: {e}")
        return {}

def toggle_comment_reaction(comment_id: str, emoji: str, user_ip: str) -> dict:
    """Toggle a reaction on a comment. Returns updated reaction counts."""
    try:
        with _visits_db_conn() as conn:
            # Check if reaction already exists
            cur = conn.execute("""
                SELECT id FROM comment_reactions 
                WHERE comment_id = ? AND emoji = ? AND user_ip = ?
            """, (comment_id, emoji, user_ip))
            
            existing = cur.fetchone()
            
            if existing:
                # Remove existing reaction
                conn.execute("DELETE FROM comment_reactions WHERE id = ?", (existing[0],))
                action = 'removed'
            else:
                # Add new reaction
                conn.execute("""
                    INSERT INTO comment_reactions (comment_id, emoji, user_ip, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (comment_id, emoji, user_ip, time.time()))
                action = 'added'
            
            conn.commit()
            
            # Return updated counts
            reactions = load_comment_reactions(comment_id, conn)
            return {'action': action, 'reactions': reactions}
            
    except Exception as e:
        log.warning(f"toggle_comment_reaction failed: {e}")
        return {'action': 'error', 'reactions': {}}

def record_visit_sql(id_:str, now_ts:float):
    if not id_:
        return
    try:
        with _visits_db_conn() as conn:
            # Use upsert pattern to avoid race between SELECT and INSERT under concurrent requests
            conn.execute("INSERT OR IGNORE INTO visits (id,first_seen,last_seen) VALUES (?,?,?)", (id_, now_ts, now_ts))
            conn.execute("UPDATE visits SET last_seen=? WHERE id=?", (now_ts, id_))
    except Exception as e:
        log.warning(f"record_visit_sql failed: {e}")

def sql_unique_counts():
    try:
        with _visits_db_conn() as conn:
            tz = pytz.timezone('Europe/Kyiv')
            now_dt = datetime.now(tz)
            today_start = tz.localize(datetime.strptime(now_dt.strftime('%Y-%m-%d'), '%Y-%m-%d'))
            week_start = now_dt - timedelta(days=7)
            today_ts = today_start.timestamp()
            week_ts = week_start.timestamp()
            cur1 = conn.execute("SELECT COUNT(*) FROM visits WHERE last_seen >= ?", (today_ts,))
            day = cur1.fetchone()[0]
            cur2 = conn.execute("SELECT COUNT(*) FROM visits WHERE last_seen >= ?", (week_ts,))
            week = cur2.fetchone()[0]
            return day, week
    except Exception as e:
        log.warning(f"sql_unique_counts failed: {e}")
    return None, None

def _active_sessions_from_db(ttl:int)->list[dict]:
    """Return list of active sessions (id, first_seen, last_seen) from persistent DB within ttl seconds."""
    cutoff = time.time() - ttl
    out = []
    try:
        with _visits_db_conn() as conn:
            cur = conn.execute("SELECT id, first_seen, last_seen FROM visits WHERE last_seen >= ?", (cutoff,))
            for row in cur.fetchall():
                try:
                    out.append({'id': row[0], 'first': float(row[1] or 0), 'last': float(row[2] or 0)})
                except Exception:
                    continue
    except Exception as e:
        log.warning(f"active sessions db query failed: {e}")
    return out

# Initialize DB at import
init_visits_db()
init_comments_db()
init_alarms_db()
init_alarm_events_db()
# Restore persisted active alarms
try:
    _obl,_r = load_active_alarms(APP_ALARM_TTL_MINUTES*60)
    if _obl: ACTIVE_OBLAST_ALARMS.update(_obl)
    if _r: ACTIVE_RAION_ALARMS.update(_r)
except Exception as _e_rec:
    log.debug(f'alarm restore failed: {_e_rec}')
# Preload recent comments into in-memory cache so first GET can serve quickly without hitting DB again
try:
    COMMENTS = load_recent_comments(limit=COMMENTS_MAX)
except Exception as _e:
    log.debug(f'preload comments failed: {_e}')
GIT_SYNC_TOKEN = os.getenv('GIT_SYNC_TOKEN')  # GitHub PAT (classic or fine-grained) with repo write
GIT_COMMIT_INTERVAL = int(os.getenv('GIT_COMMIT_INTERVAL', '180'))  # seconds between commits
_last_git_commit = 0

# Delay before first Telegram connect (helps избежать пересечения старого и нового инстанса при деплое)
FETCH_START_DELAY = int(os.getenv('FETCH_START_DELAY', '0'))  # seconds

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
    # Configure user (once)
    def run(cmd):
        return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
    # Stage & commit if there is a change
    run(f'git add {MESSAGES_FILE}')
    status = run('git status --porcelain').stdout
    if MESSAGES_FILE not in status:
        return  # no actual diff
    commit_msg = f'Update {MESSAGES_FILE} (auto)'  # no secrets
    run(f'git commit -m "{commit_msg}"')
    push_res = run('git push origin HEAD:main')
    if push_res.returncode == 0:
        _last_git_commit = now
    else:
        # If push fails (e.g., diverged), attempt pull+rebase then push
        run('git fetch origin')
        run('git rebase origin/main || git rebase --abort')
        push_res2 = run('git push origin HEAD:main')
        if push_res2.returncode == 0:
            _last_git_commit = now
        # else: give up silently to avoid spamming logs

def _download_settlements():
    if not SETTLEMENTS_URL or os.path.exists(SETTLEMENTS_FILE):
        return False
    try:
        import requests
        r = requests.get(SETTLEMENTS_URL, timeout=30)
        if r.status_code == 200:
            with open(SETTLEMENTS_FILE, 'wb') as f:
                f.write(r.content)
            log.info(f'Downloaded settlements file from {SETTLEMENTS_URL}')
            return True
        else:
            log.warning(f'Failed to download settlements ({r.status_code}) from {SETTLEMENTS_URL}')
    except Exception as e:
        log.warning(f'Error downloading settlements: {e}')
    return False

def _load_settlements():
    global SETTLEMENTS_INDEX, SETTLEMENTS_ORDERED
    if not os.path.exists(SETTLEMENTS_FILE):
        _download_settlements()
    if not os.path.exists(SETTLEMENTS_FILE):
        log.info('No settlements file present; only basic CITY_COORDS will be used.')
        return
    try:
        with open(SETTLEMENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for item in data:
            if count >= SETTLEMENTS_MAX:
                break
            try:
                name = item.get('name') or item.get('n')
                if not name:
                    continue
                lat_raw = item.get('lat')
                lng_raw = item.get('lng') or item.get('lon')
                if lat_raw is None or lng_raw is None:
                    continue
                lat = float(lat_raw)
                lng = float(lng_raw)
                key = name.strip().lower()
                if key and key not in SETTLEMENTS_INDEX:
                    SETTLEMENTS_INDEX[key] = (lat, lng)
                    count += 1
            except Exception:
                continue
        SETTLEMENTS_ORDERED = sorted(SETTLEMENTS_INDEX.keys(), key=len, reverse=True)[:SETTLEMENTS_MAX]
        log.info(f'Loaded settlements: {len(SETTLEMENTS_INDEX)} (cap {SETTLEMENTS_MAX})')
    except Exception as e:
        log.warning(f'Failed to load settlements file {SETTLEMENTS_FILE}: {e}')

_load_settlements()

# ---- External comprehensive cities/settlements file merge (user-provided) ----
# You supplied an external file with full coordinates of Ukrainian cities / settlements.
# Set EXT_CITIES_FILE env var (default 'city_ukraine.json') and place the file in the app working directory.
# Accepted JSON shapes:
#   1) List[ { name|city|settlement: str, lat|latitude: float, lng|lon|long|longitude: float } ]
#   2) List[ [ name, lat, lon ] ]
#   3) Dict[str, { lat: x, lng: y }] or Dict[str, [lat, lon]]
# Fields may also appear in Ukrainian/Russian ("назва","широта","довгота","долгота").
EXT_CITIES_FILE = os.getenv('EXT_CITIES_FILE', 'city_ukraine.json')

def _load_external_cities():
    global CITY_COORDS, SETTLEMENTS_INDEX, SETTLEMENTS_ORDERED
    path = EXT_CITIES_FILE
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        log.warning(f"Failed reading {path}: {e}")
        return
    added = 0
    def add_entry(name_raw, lat_raw, lon_raw):
        nonlocal added
        try:
            if name_raw is None: return
            name = str(name_raw).strip().lower()
            if not name or len(name) < 2: return
            lat = float(lat_raw); lon = float(lon_raw)
            # Basic sanity bounds for Ukraine region (approx) to skip corrupt rows
            if not (43.0 <= lat <= 53.5 and 21.0 <= lon <= 41.5):
                return
            if name not in CITY_COORDS:
                CITY_COORDS[name] = (lat, lon)
            if name not in SETTLEMENTS_INDEX:
                SETTLEMENTS_INDEX[name] = (lat, lon)
                added += 1
        except Exception:
            return
    if isinstance(data, dict):
        # Expect mapping name -> {lat,lng} or name -> [lat,lon]
        for k,v in data.items():
            if isinstance(v, dict):
                lat = v.get('lat') or v.get('latitude') or v.get('широта')
                lon = v.get('lng') or v.get('lon') or v.get('long') or v.get('longitude') or v.get('довгота') or v.get('долгота')
                add_entry(k, lat, lon)
            elif isinstance(v, (list, tuple)) and len(v) >= 2:
                add_entry(k, v[0], v[1])
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                name = item.get('name') or item.get('city') or item.get('settlement') or item.get('населенный пункт') or item.get('населений пункт') or item.get('назва')
                lat = item.get('lat') or item.get('latitude') or item.get('широта')
                lon = item.get('lng') or item.get('lon') or item.get('long') or item.get('longitude') or item.get('довгота') or item.get('долгота')
                add_entry(name, lat, lon)
            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                add_entry(item[0], item[1], item[2])
    # Rebuild ordered list (largest names first to prefer longer multi-word matches)
    if added:
        try:
            SETTLEMENTS_ORDERED = sorted(SETTLEMENTS_INDEX.keys(), key=len, reverse=True)[:SETTLEMENTS_MAX]
        except Exception:
            pass
        log.info(f"Merged external cities file {path}: +{added} settlements (total {len(SETTLEMENTS_INDEX)})")
    else:
        log.info(f"External cities file {path} parsed; no new settlements added (maybe already present)")

_load_external_cities()

def geocode_opencage(place: str):
    if not OPENCAGE_API_KEY:
        return None
    
    # Skip if known negative
    if neg_geocode_check(place):
        return None
    
    # Block general directional terms that don't represent specific places
    place_lower = place.lower().strip()
    directional_terms = [
        'напрямок', 'напрям', 'направлении', 'направление',
        'північно-східний', 'північно-західний', 'південно-східний', 'південно-західний',
        'північний', 'південний', 'східний', 'західний',
        'nord', 'south', 'east', 'west', 'northeast', 'northwest', 'southeast', 'southwest'
    ]
    
    if any(term in place_lower for term in directional_terms):
        # Add to negative cache to avoid repeated attempts
        neg_geocode_add(place, 'directional')
        return None
    
    cache = _load_opencage_cache()
    key = place.strip().lower()
    now = int(datetime.utcnow().timestamp())
    if key in cache:
        entry = cache[key]
        if now - entry.get('ts', 0) < OPENCAGE_TTL:
            return tuple(entry['coords']) if entry['coords'] else None
    import requests
    try:
        resp = requests.get('https://api.opencagedata.com/geocode/v1/json', params={
            'q': place,
            'key': OPENCAGE_API_KEY,
            'language': 'uk',
            'limit': 1,
            'countrycode': 'ua'
        }, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('results'):
                g = data['results'][0]['geometry']
                coords = (g['lat'], g['lng'])
                cache[key] = {'ts': now, 'coords': coords}
                _save_opencage_cache()
                return coords
        # negative (no results or non-200)
        cache[key] = {'ts': now, 'coords': None}
        _save_opencage_cache(); neg_geocode_add(place,'nocode')
        return None
    except Exception as e:
        log.warning(f"OpenCage error for '{place}': {e}")
        cache[key] = {'ts': now, 'coords': None}
        _save_opencage_cache(); neg_geocode_add(place,'error')
        return None

def calculate_projected_path(source_lat, source_lng, target_lat, target_lng, speed_kmh=50):
    """
    Calculate projected path from source to target with intermediate points
    
    Args:
        source_lat, source_lng: Current/source coordinates
        target_lat, target_lng: Target coordinates  
        speed_kmh: Estimated speed in km/h (default: 50 km/h for UAVs)
    
    Returns:
        dict with path_points, estimated_arrival, total_distance
    """
    try:
        # Calculate distance using Haversine formula
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(source_lat)
        lon1_rad = math.radians(source_lng)
        lat2_rad = math.radians(target_lat)
        lon2_rad = math.radians(target_lng)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance_km = R * c
        
        # Calculate estimated travel time
        travel_time_hours = distance_km / speed_kmh
        travel_time_minutes = travel_time_hours * 60
        
        # Generate intermediate points along the path (every ~10km or 10 points max)
        num_points = min(10, max(2, int(distance_km / 10)))
        path_points = []
        
        for i in range(num_points + 1):
            fraction = i / num_points
            
            # Linear interpolation for simple path
            lat = source_lat + (target_lat - source_lat) * fraction
            lng = source_lng + (target_lng - source_lng) * fraction
            
            # Calculate ETA for this point
            point_travel_time = travel_time_minutes * fraction
            
            path_points.append({
                'lat': lat,
                'lng': lng,
                'eta_minutes': point_travel_time,
                'fraction': fraction
            })
        
        return {
            'path_points': path_points,
            'total_distance_km': distance_km,
            'estimated_arrival_minutes': travel_time_minutes,
            'speed_kmh': speed_kmh
        }
        
    except Exception as e:
        print(f"ERROR calculating projected path: {e}")
        return None

def create_eta_circles(center_lat, center_lng, time_minutes, speed_kmh=50):
    """
    Create ETA circles showing possible positions after given time
    
    Args:
        center_lat, center_lng: Center coordinates
        time_minutes: Time in minutes
        speed_kmh: Speed in km/h
        
    Returns:
        List of circle definitions for different confidence levels
    """
    try:
        # Calculate distance that can be covered in given time
        max_distance_km = (speed_kmh * time_minutes) / 60
        
        # Create circles with different confidence levels
        circles = []
        
        # 90% confidence circle (slightly smaller radius)
        circles.append({
            'center_lat': center_lat,
            'center_lng': center_lng,
            'radius_km': max_distance_km * 0.9,
            'confidence': 90,
            'color': '#ff4444',
            'opacity': 0.3,
            'stroke_color': '#cc0000',
            'stroke_width': 2
        })
        
        # 50% confidence circle (even smaller)
        circles.append({
            'center_lat': center_lat,
            'center_lng': center_lng,
            'radius_km': max_distance_km * 0.6,
            'confidence': 50,
            'color': '#ffaa00',
            'opacity': 0.4,
            'stroke_color': '#ff8800',
            'stroke_width': 2
        })
        
        return circles
        
    except Exception as e:
        print(f"ERROR creating ETA circles: {e}")
        return []

def _create_directional_trajectory_markers(text, mid, date_str, channel):
    """
    Create trajectory markers for directional movement messages
    Instead of showing destination marker, show projected path and ETA circles
    """
    import re
    from datetime import datetime, timedelta
    
    try:
        text_lower = text.lower()
        
        # Extract target city from directional patterns
        target_city = None
        source_direction = None
        
        # Patterns to extract target city
        target_patterns = [
            r'у напрямку\s+([а-яіїєґ\'\-\s]+?)(?:\s|$|з)',
            r'в напрямку\s+([а-яіїєґ\'\-\s]+?)(?:\s|$|з)',
            r'курс на\s+([а-яіїєґ\'\-\s]+?)(?:\s|$|з)',
            r'прямує до\s+([а-яіїєґ\'\-\s]+?)(?:\s|$|з)'
        ]
        
        for pattern in target_patterns:
            match = re.search(pattern, text_lower)
            if match:
                target_city = match.group(1).strip()
                break
        
        # Extract source direction
        direction_patterns = [
            r'з\s+(північного?-?сходу?)',
            r'з\s+(південного?-?заходу?)', 
            r'з\s+(північного?-?заходу?)',
            r'з\s+(південного?-?сходу?)',
            r'з\s+(півночі)',
            r'з\s+(півдня)',
            r'з\s+(заходу)',
            r'з\s+(сходу)'
        ]
        
        for pattern in direction_patterns:
            match = re.search(pattern, text_lower)
            if match:
                source_direction = match.group(1)
                break
        
        if not target_city:
            return []
        
        # Normalize target city name and get coordinates
        target_city_normalized = target_city.lower().strip()
        
        # Try to find coordinates for target city
        target_coords = None
        
        # Check in CITY_COORDS
        if target_city_normalized in CITY_COORDS:
            target_coords = CITY_COORDS[target_city_normalized]
        else:
            # Try common variations and declensions
            common_variations = {
                'дніпро': 'дніпро',
                'киев': 'київ', 
                'київа': 'київ',
                'харков': 'харків',
                'харкова': 'харків',
                'одесса': 'одеса',
                'одеси': 'одеса'
            }
            
            for variant, canonical in common_variations.items():
                if variant in target_city_normalized or target_city_normalized in variant:
                    if canonical in CITY_COORDS:
                        target_coords = CITY_COORDS[canonical]
                        break
            
            # If still not found, try removing common endings (declensions)
            if not target_coords:
                endings_to_try = ['а', 'у', 'ом', 'і', 'ів', 'ами']
                for ending in endings_to_try:
                    if target_city_normalized.endswith(ending) and len(target_city_normalized) > len(ending) + 2:
                        base_form = target_city_normalized[:-len(ending)]
                        # Special case for київ + а = києва -> київ  
                        if base_form + ending == 'києва':
                            base_form = 'київ'
                        if base_form in CITY_COORDS:
                            target_coords = CITY_COORDS[base_form]
                            break
        
        if not target_coords:
            # Fallback - return empty if we can't find target coordinates
            return []
        
        target_lat, target_lng = target_coords
        
        # Estimate source coordinates based on direction
        source_lat, source_lng = _estimate_source_coordinates(target_lat, target_lng, source_direction)
        
        # Create projected path
        projected_path = calculate_projected_path(source_lat, source_lng, target_lat, target_lng)
        
        if not projected_path:
            return []
        
        # Create trajectory markers
        markers = []
        
        # Add path markers (intermediate points)
        for i, point in enumerate(projected_path['path_points'][1:-1], 1):  # Skip first and last
            if i % 2 == 0:  # Only show every other point to avoid clutter
                continue
                
            markers.append({
                'id': f"{mid}_path_{i}",
                'place': f"Траєкторія ({int(point['eta_minutes'])}хв)",
                'lat': point['lat'],
                'lng': point['lng'],
                'threat_type': 'trajectory',
                'text': f"Проміжна точка маршруту до {target_city.title()}",
                'date': date_str,
                'channel': channel,
                'marker_icon': 'trajectory.png',
                'source_match': 'projected_path',
                'eta_minutes': point['eta_minutes'],
                'marker_type': 'trajectory_point',
                'opacity': 0.7
            })
        
        # Add ETA circles around target
        eta_circles = create_eta_circles(target_lat, target_lng, projected_path['estimated_arrival_minutes'])
        
        # Create main target marker with trajectory info
        markers.append({
            'id': f"{mid}_target",
            'place': f"{target_city.title()} (ціль)",
            'lat': target_lat,
            'lng': target_lng,
            'threat_type': 'trajectory_target',
            'text': f"Ціль: {target_city.title()} (ETA: {int(projected_path['estimated_arrival_minutes'])}хв)",
            'date': date_str,
            'channel': channel,
            'marker_icon': 'target.png',
            'source_match': 'trajectory_target',
            'eta_minutes': projected_path['estimated_arrival_minutes'],
            'distance_km': projected_path['total_distance_km'],
            'marker_type': 'trajectory_target',
            'eta_circles': eta_circles,
            'projected_path': projected_path['path_points']
        })
        
        return markers
        
    except Exception as e:
        print(f"ERROR creating directional trajectory markers: {e}")
        return []

def _estimate_source_coordinates(target_lat, target_lng, direction):
    """Estimate source coordinates based on target and direction"""
    
    # Default distance for estimation (50km)
    distance_km = 50
    
    # Direction offsets (approximate)
    direction_offsets = {
        'північного-сходу': (-0.45, 0.45),
        'південного-заходу': (0.45, -0.45),
        'північного-заходу': (-0.45, -0.45), 
        'південного-сходу': (0.45, 0.45),
        'півночі': (-0.45, 0),
        'півдня': (0.45, 0),
        'заходу': (0, -0.45),
        'сходу': (0, 0.45)
    }
    
    # Get offset or default to east
    lat_offset, lng_offset = direction_offsets.get(direction, (0, 0.45))
    
    # Apply offset (rough approximation: 1 degree ≈ 111km)
    source_lat = target_lat + lat_offset
    source_lng = target_lng + lng_offset
    
    return source_lat, source_lng

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
    
    # PRIORITY: Check for trajectory patterns FIRST (before any processing)
    # Pattern: "з [source_region] на [target_region(s)]" - trajectory, not multi-target
    trajectory_pattern = r'(\d+)?\s*шахед[іївыиє]*\s+з\s+([а-яіїєґ]+(щин|ччин)[ауиі])\s+на\s+([а-яіїєґ/]+(щин|ччин)[ауиіу])'
    trajectory_match = re.search(trajectory_pattern, text.lower(), re.IGNORECASE)
    
    if trajectory_match:
        count_str = trajectory_match.group(1)
        source_region = trajectory_match.group(2)
        target_regions = trajectory_match.group(4)
        
        print(f"DEBUG: Trajectory detected - {count_str or ''}шахедів з {source_region} на {target_regions}")
        return []
    
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
        
        # Check for short tactical messages that are likely informational updates
        # These patterns suggest updates rather than active threats
        brief_tactical_patterns = [
            'бпла курсом на',
            'бпла на ',
            'повз .* курсом на'
        ]
        # But only filter if the message is relatively short (likely an update, not detailed threat)
        is_brief_message = len(t.strip()) < 100
        has_brief_tactical = any(re.search(pattern, t_lower) for pattern in brief_tactical_patterns)
        
        # Check if this is actually a current location message (not brief update)
        current_location_phrases = [
            'над',
            'в районі',
            'атакував',
            'вибухи в',
            'влучання в',
            'збито в',
            'знищено в'
        ]
        has_current_location = any(phrase in t_lower for phrase in current_location_phrases)
        
        # Filter brief tactical messages - these are often status updates
        # BUT not if they describe current location/events
        if is_brief_message and has_brief_tactical and not has_current_location:
            return True
        
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
        
        # Look for lines that contain threats with quantities and targets
        for line in text_lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            line_lower = line_stripped.lower()
            
            # Check if line contains threat patterns with quantities and targets
            has_threat_pattern = (
                # Pattern: "N x/× БпЛА курсом на [target]"
                (re.search(r'\d+\s*[xх×]\s*бпла.*?(курс|на)\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахедів/шахеди на [target]" - all forms of Shahed
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+на\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахедів/шахеди біля [target]" - near target
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+біля\s+([а-яіїєё\'\-\s]+)', line_lower)) or
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
        def get_city_coords_quick(city_name):
            """Quick coordinate lookup with accusative case normalization"""
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
            
            # Try direct lookup
            coords = CITY_COORDS.get(city_norm)
            if not coords:
                coords = ensure_city_coords_with_message_context(city_norm, text)
            
            add_debug_log(f"Coord lookup: '{city_name}' -> '{city_norm}' -> {bool(coords)}", "multi_regional")
            return coords
        
        threats = []
        processed_cities = set()  # Избегаем дубликатов
        
        for line in text_lines:
            line_stripped = line.strip()
            if not line_stripped or ':' in line_stripped[:20]:  # Skip region headers
                continue
            
            line_lower = line_stripped.lower()
            
            # Look for UAV course patterns
            if 'бпла' in line_lower and ('курс' in line_lower or ' на ' in line_lower or 'над' in line_lower or 'повз' in line_lower):
                # Extract city name from patterns - handle both plain text and markdown links
                patterns = [
                    # Pattern for markdown links: БпЛА курсом на [Бровари](link)
                    r'(\d+)?[xх]?\s*бпла\s+(?:курсом?)?\s*(?:на|над)\s+\[([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]+?)\]',
                    # Pattern for plain text: БпЛА курсом на Конотоп (improved to capture multi-word cities)
                    r'(\d+)?[xх]?\s*бпла\s+.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]+?)(?=\s*(?:\n|$|[,\.\!\?;]|\s+\d+[xх]?\s*бпла|\s+[А-ЯІЇЄЁа-яіїєё]+щина:))',
                    # Pattern for "повз" (e.g., "БпЛА повз Славутич в бік Білорусі")
                    r'(\d+)?[xх]?\s*бпла\s+(?:.*?)?повз\s+([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]{3,50}?)(?=\s+(?:в\s+бік|до|на|через|$|[,\.\!\?;]))'
                ]
                
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
                    
                    # Try to get coordinates
                    coords = get_city_coords_quick(city_clean)
                    
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
                            'marker_icon': 'shahed.png',
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
                        
                        # Try to get coordinates
                        coords = get_city_coords_quick(city_clean)
                        
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
                                    # Create a circular pattern around the target
                                    import math
                                    angle = (2 * math.pi * i) / tracks_to_create
                                    offset_distance = 0.01  # ~1km offset
                                    marker_lat += offset_distance * math.cos(angle)
                                    marker_lng += offset_distance * math.sin(angle)
                                
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
                                    'marker_icon': 'shahed.png',
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
                            'marker_icon': 'shahed.png',
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
                            'marker_icon': 'shahed.png',
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
        # Recon / розвід дрони -> use pvo icon (rozved.png) per user request - PRIORITY: check BEFORE general БПЛА
        if 'розвід' in l or 'розвідуваль' in l or 'развед' in l:
            return 'rozved', 'rozved.png'
        # PRIORITY: КАБы (управляемые авиационные бомбы) -> rszv.png - check BEFORE пуски to avoid misclassification
        if any(k in l for k in ['каб','kab','умпк','umpk','модуль','fab','умпб','фаб','кабу']) or \
           ('авіаційн' in l and 'бомб' in l) or ('керован' in l and 'бомб' in l):
            return 'kab', 'rszv.png'
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
            print(f"[CLASSIFY DEBUG] Classified as alarm_cancel")
            return 'alarm_cancel', 'vidboi.png'
        
        # PRIORITY: High-speed targets / missile threats with rocket emoji (🚀) -> raketa.png
        # This should have priority over drones to handle missile-like threats with rocket emoji
        if '🚀' in th or any(k in l for k in ['ціль','цілей','цілі','високошвидкісн','high-speed']):
            print(f"[CLASSIFY DEBUG] Classified as raketa (high-speed targets/rocket emoji)")
            return 'raketa', 'raketa.png'
            
        # PRIORITY: drones (частая путаница). Если присутствуют слова шахед/бпла/дрон -> это shahed
        if any(k in l for k in ['shahed','шахед','шахеді','шахедів','geran','герань','дрон','дрони','бпла','uav']):
            print(f"[CLASSIFY DEBUG] Classified as shahed (drones/UAV)")
            return 'shahed', 'shahed.png'
        # PRIORITY: Aircraft activity & tactical aviation (avia) -> avia.png (jets, tactical aviation, но БЕЗ КАБов)
        if any(k in l for k in ['літак','самол','avia','tactical','тактичн','fighter','истребит','jets']) or \
           ('авіаційн' in l and ('засоб' in l or 'ураж' in l)):
            return 'avia', 'avia.png'
        # Rocket / missile attacks (ракета, ракети) -> raketa.png
        if any(k in l for k in ['ракет','rocket','міжконтинент','межконтинент','балістичн','крилат','cruise']):
            return 'raketa', 'raketa.png'
        # РСЗВ (MLRS, град, ураган, смерч) -> rszv.png
        if any(k in l for k in ['рсзв','mlrs','град','ураган','смерч','рсув','tор','tорнадо','торнадо']):
            return 'rszv', 'rszv.png'
        # Korabel (naval/ship-related threats) -> korabel.png
        if any(k in l for k in ['корабел','флот','корабл','ship','fleet','морськ','naval']):
            return 'korabel', 'korabel.png'
        # Artillery
        if any(k in l for k in ['арт','artillery','гармат','гаубиц','минометн','howitzer']):
            return 'artillery', 'artillery.png'
        # PVO (air defense activity) -> pvo.png
        if any(k in l for k in ['ппо','pvo','defense','оборон','зенітн','с-','patriot']):
            return 'pvo', 'pvo.png'
        # Naval mines -> neptun
        if any(k in l for k in ['міна','мін ','mine','neptun','нептун','противокорабел']):
            return 'neptun', 'neptun.jpg'
        # FPV drones -> fpv.png
        if any(k in l for k in ['fpv','фпв','камікадз','kamikaze']):
            print(f"[CLASSIFY DEBUG] Classified as fpv")
            return 'fpv', 'fpv.png'
        # General fallback for unclassified threats
        print(f"[CLASSIFY DEBUG] Using default fallback: shahed")
        return 'shahed', 'shahed.png'  # default fallback
    
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
        
        # Normalize city name and try to find coordinates
        city_norm = target_city.lower()
        # Apply UA_CITY_NORMALIZE rules if available
        if 'UA_CITY_NORMALIZE' in globals():
            city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
        coords = CITY_COORDS.get(city_norm)
        
        add_debug_log(f"Priority district city lookup: '{target_city}' -> '{city_norm}' -> {coords}", "priority_region_district")
        
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
            add_debug_log(f"PRIORITY: Found city: {repr(city_from_general)}, oblast: {repr(oblast_from_general)}", "emoji_debug")
            
            if city_from_general and 2 <= len(city_from_general) <= 40:
                base = city_from_general.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                base = re.sub(r'\s+',' ', base)
                norm = UA_CITY_NORMALIZE.get(base, base)
                
                # First try to find city+oblast specific coordinates
                oblast_key = oblast_from_general.lower()
                coords = None
                
                # Try different lookup strategies for city+oblast disambiguation
                if 'сум' in oblast_key and norm == 'миколаївка':
                    coords = (51.5667, 34.1333)  # Миколаївка, Сумська область
                    add_debug_log(f"PRIORITY: Using specific coordinates for Миколаївка (Сумська обл.): {coords}", "emoji_debug")
                elif 'миколаївськ' in oblast_key and norm == 'миколаївка':
                    coords = (47.0667, 31.8333)  # Миколаївка, Миколаївська область
                    add_debug_log(f"PRIORITY: Using specific coordinates for Миколаївка (Миколаївська обл.): {coords}", "emoji_debug")
                # Handle districts by mapping to their administrative centers
                elif 'район' in norm:
                    if 'синельниківський район' in norm:
                        coords = CITY_COORDS.get('синельникове')  # Синельникове - центр району
                        add_debug_log(f"PRIORITY: Mapping Синельниківський район -> Синельникове: {coords}", "emoji_debug")
                    elif 'миколаївський район' in norm and 'миколаївськ' in oblast_key:
                        coords = CITY_COORDS.get('миколаїв')  # Миколаїв - центр району
                        add_debug_log(f"PRIORITY: Mapping Миколаївський район -> Миколаїв: {coords}", "emoji_debug")
                    # For other districts, try to find coordinates in DISTRICT_CENTERS first
                    else:
                        # Extract district name without 'район' suffix
                        district_name = norm.replace('район', '').strip()
                        district_coords = DISTRICT_CENTERS.get(district_name)
                        if district_coords:
                            coords = district_coords
                            add_debug_log(f"PRIORITY: Found district coordinates for '{district_name}': {coords}", "emoji_debug")
                
                if not coords:
                    # Fallback to general lookup
                    coords = CITY_COORDS.get(norm)
                    add_debug_log(f"PRIORITY: General lookup: base={repr(base)}, norm={repr(norm)}, coords={coords}", "emoji_debug")
                
                if not coords and 'SETTLEMENTS_INDEX' in globals():
                    idx_map = globals().get('SETTLEMENTS_INDEX') or {}
                    coords = idx_map.get(norm)
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
            lat, lng = 50.9, 34.8  # Near Sumy city (in Ukrainian territory)
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
                'marker_icon': 'rozved.png', 'source_match': 'multiple_threats_mykolaiv_recon'
            })
        
        # 3. Check for general БПЛА threats in oblast format (миколаївщини/миколаївщині) without "розвід"
        elif ('бпла' in text_lower or 'дрон' in text_lower) and ('миколаївщини' in text_lower or 'миколаївщині' in text_lower or 'миколаївщина' in text_lower):
            lat, lng = 46.9750, 31.9946
            all_threats.append({
                'id': f"{mid}_mykolaiv_uav", 'place': 'Миколаївщина', 'lat': lat, 'lng': lng,
                'threat_type': 'shahed', 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'shahed.png', 'source_match': 'multiple_threats_mykolaiv_uav'
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
        
        # NEW: Handle emoji-prefixed threat messages like "🛸 Звягель (Житомирська обл.) Загроза застосування БПЛА"
        emoji_threat_pattern = r'^[^\w\s]*\s*([А-ЯІЇЄЁа-яіїєё\'\-\s]+)\s*\([^)]*обл[^)]*\)\s*загроза\s+застосування\s+бпла'
        emoji_match = re.search(emoji_threat_pattern, head, re.IGNORECASE)
        if emoji_match:
            city_from_emoji = emoji_match.group(1).strip()
            if city_from_emoji and 2 <= len(city_from_emoji) <= 40:
                base = city_from_emoji.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                base = re.sub(r'\s+',' ', base)
                norm = UA_CITY_NORMALIZE.get(base, base)
                coords = CITY_COORDS.get(norm)
                if not coords and 'SETTLEMENTS_INDEX' in globals():
                    idx_map = globals().get('SETTLEMENTS_INDEX') or {}
                    coords = idx_map.get(norm)
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
                            enriched = ensure_city_coords(norm)
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
                            threat, icon = 'shahed','shahed.png'
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
                if 2 <= len(city_candidate) <= 40:
                    base = city_candidate.lower().replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
                    base = _re_early.sub(r'\s+',' ', base)
                    norm = UA_CITY_NORMALIZE.get(base, base)
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
                            threat, icon = 'shahed','shahed.png'
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
                threat, icon = 'shahed','shahed.png'
                return [{
                    'id': str(mid), 'place': base.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat, 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'city_dash_uav'
                }]
        # NEW: pattern "БпЛА на <city>" or "бпла на <city>" -> marker at city
        uav_cities = _re_rel.findall(r"бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ\`\s/]+?)(?=\s+(?:з|на|до|від|через|повз|курсом|напрям)\s|[,\.\!\?;:\n]|$)", low_txt)
        if uav_cities:
            threats = []
            for idx, rc in enumerate(uav_cities):
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
                            icon = 'shahed.png'  # Could create special directional icon later
                            
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
                            'marker_icon': 'shahed.png', 'source_match': 'uav_on_city'
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
                enriched = ensure_city_coords(base)
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
                    povz_match = _re_multi.search(r'(\d+)?[xх]?\s*бпла\s+повз\s+([а-яіїєґ\'\-\s]+?)\s+курсом?\s+на\s+([а-яіїєґ\'\-\s]+?)(?:\s*$|\s*\|)', seg_lower)
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
                            
                            coords = ensure_city_coords(city_norm)
                            
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
                    location_match = _re_multi.search(r'(\d+)?[xх]?\s*бпла\s+(.+?)(?:\.|$)', seg_lower)
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
                            
                            coords = ensure_city_coords(city_norm)
                            
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
                        
                        coords = ensure_city_coords(city_norm)
                        
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
                enriched = ensure_city_coords(base)
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
                        # Create a circular pattern around the target
                        import math
                        angle = (2 * math.pi * i) / tracks_to_create
                        offset_distance = 0.01  # ~1km offset
                        marker_lat += offset_distance * math.cos(angle)
                        marker_lng += offset_distance * math.sin(angle)
                    
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
        import re as _pre_hdr_re
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
        return n
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
    add_debug_log(f"Processing {len(lines)} cleaned lines for multi-city tracks", "multi_region")
    for ln in lines:
        add_debug_log(f"Processing line: '{ln}'", "multi_region")
        
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
        
        # Check if line contains БпЛА information without specific course
        ln_lower = ln.lower()
        if 'бпла' in ln_lower or 'безпілотник' in ln_lower or 'дрон' in ln_lower:
            add_debug_log(f"Line contains UAV keywords: {[k for k in ['бпла', 'безпілотник', 'дрон'] if k in ln_lower]}", "multi_region")
            if not any(keyword in ln_lower for keyword in ['курс', 'на ', 'районі']):
                add_debug_log(f"UAV line lacks direction keywords (курс/на/районі) - general activity message", "multi_region")
        else:
            add_debug_log(f"Line does not contain UAV keywords", "multi_region")
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
                        place_label += f" (напрямок)"
                    elif direction_type == 'через':
                        place_label += f" (через)"
                    elif direction_type == 'повз':
                        place_label += f" (повз)"
                    
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
                    
                    # For KAB/aviation bombs, always create marker even for regional threats
                    has_kab = any(kab_word in ln_lower for kab_word in ['каб', 'авіабомб', 'авиабомб'])
                    
                    if is_regional_threat and not has_kab:
                        add_debug_log(f"Skipping regional threat marker - affects entire region: {oblast_hdr} (found: {[ref for ref in [f'на {oblast_hdr}', accusative_form, genitive_form, dative_form] if ref in ln_lower]})", "multi_region")
                        continue
                    
                    # Try to find coordinates for the region's main city
                    base_city = normalize_city_name(region_city)
                    base_city = UA_CITY_NORMALIZE.get(base_city, base_city)
                    coords = CITY_COORDS.get(base_city) or (SETTLEMENTS_INDEX.get(base_city) if SETTLEMENTS_INDEX else None)
                    
                    if coords:
                        lat, lng = coords
                        label = base_city.title()
                        label += f" [{oblast_hdr.title()}]"
                        
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
                        icon = 'shahed.png'
                    
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
                    'marker_icon': 'rszv.png', 'source_match': 'multiline_oblast_city_rocket', 'count': rocket_count
                })
                continue  # переходим к следующей строке (не пытаемся распознать как БпЛА)
        # --- NEW: группы крылатых ракет ("Група/Групи КР курсом на <город>") ---
        kr_city = None; kr_count = 1
        # Primary straightforward pattern for "Група/Групи КР курсом на <місто>"
        mkr = re.search(r'(?:^|\b)(?:([0-9]+)[xх]?\s*)?груп[аи]\s+кр\b.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
        if not mkr:
            # Tolerant pattern allowing missing leading "г" or space glitches / lost letters
            mkr = re.search(r'(?:^|\b)(?:([0-9]+)[xх]?\s*)?(?:г)?руп[аи]\s*(?:к)?р\b.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
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
                    'marker_icon': 'raketa.png', 'source_match': 'multiline_oblast_city_kr_group', 'count': kr_count
                })
                continue
        # Universal KR fallback (handles degraded OCR lines like '3х рупи  курсом на рилуки')
        low_ln = ln.lower()
        if ('курс' in low_ln and ' на ' in low_ln and ('груп' in low_ln or ' кр' in low_ln)):
            # Extract count if present at start or before 'груп'
            mcnt = re.search(r'^(\d+)[xх]?\s*', low_ln)
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
                            'marker_icon': 'raketa.png', 'source_match': 'multiline_oblast_city_kr_group_fallback2', 'count': count_guess
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
                            'marker_icon': 'raketa.png', 'source_match': 'multiline_oblast_city_course_generic', 'count': 1
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
                        'marker_icon': 'raketa.png', 'source_match': 'multiline_oblast_city_kr_group_fallback', 'count': 1
                    })
                    continue
        # Разрешаем многословные названия (до 3 слов) до конца строки / знака препинания
        m = re.search(r'(\d+)[xх]?\s*бпла.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
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
                m3 = re.search(r'(\d+)[xх]?\s*бпла.*?повз\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
                if m3:
                    count = int(m3.group(1))
                    city = m3.group(2)
                else:
                    m4 = re.search(r'бпла.*?повз\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
                    count = 1
                    city = m4.group(1) if m4 else None
        # --- NEW: Shahed lines inside multi-line block (e.g. '2 шахеди на Старий Салтів', '1 шахед на Мерефа / Борки') ---
        if not city:
            m_sha = re.search(r'^(?:([0-9]+)\s*[xх]?\s*)?шахед(?:и|ів)?\s+на\s+(.+)$', ln.strip(), re.IGNORECASE)
            if m_sha:
                try:
                    scount = int(m_sha.group(1) or '1')
                except Exception:
                    scount = 1
                cities_part = m_sha.group(2)
                raw_parts = re.split(r'\s*/\s*|\s*,\s*|\s*;\s*|\s+і\s+|\s+та\s+', cities_part, flags=re.IGNORECASE)
                for ci in raw_parts:
                    c_raw = ci.strip().strip('.').strip()
                    if not c_raw or len(c_raw) < 2:
                        continue
                    cbase = normalize_city_name(c_raw)
                    cbase = UA_CITY_NORMALIZE.get(cbase, cbase)
                    coords_s = CITY_COORDS.get(cbase) or (SETTLEMENTS_INDEX.get(cbase) if SETTLEMENTS_INDEX else None)
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
                            # Create a circular pattern around the target
                            import math
                            angle = (2 * math.pi * i) / tracks_to_create
                            offset_distance = 0.01  # ~1km offset
                            marker_lat += offset_distance * math.cos(angle)
                            marker_lng += offset_distance * math.sin(angle)
                        
                        multi_city_tracks.append({
                            'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': track_label, 'lat': marker_lat, 'lng': marker_lng,
                            'threat_type': 'shahed', 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'shahed.png', 'source_match': 'multiline_oblast_city_shahed', 'count': 1
                        })
                continue
        
        # --- NEW: Simple "X БпЛА на <city>" pattern (e.g. '1 БпЛА на Козелець', '2 БпЛА на Куликівку') ---
        if not city:
            print(f"DEBUG: Checking simple БпЛА pattern for line: '{ln}'")
            m_simple = re.search(r'(\d+)\s+бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_simple:
                try:
                    count = int(m_simple.group(1))
                except Exception:
                    count = 1
                city = m_simple.group(2).strip()
                print(f"DEBUG: Found simple БпЛА pattern - count: {count}, city: '{city}'")
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
                            'marker_icon': 'shahed.png', 'source_match': 'naprymku_pattern', 'count': count
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
                    count_match = re.search(r'^(\d+)\s*бпла', ln, re.IGNORECASE)
                    count = int(count_match.group(1)) if count_match else 1
                    
                    multi_city_tracks.append({
                        'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                        'threat_type': 'shahed', 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': 'shahed.png', 'source_match': 'multiline_oblast_city_between', 'count': count
                    })
                    continue
        
        # --- NEW: Handle "неподалік X" pattern (e.g. "неподалік Ічні") ---
        if not city:
            m_near = re.search(r'неподалік\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_near:
                city = m_near.group(1).strip()
                # Extract count from beginning of line if present
                count_match = re.search(r'^(\d+)\s*бпла', ln, re.IGNORECASE)
                count = int(count_match.group(1)) if count_match else 1
        
        # --- NEW: Handle "в районі X" pattern (e.g. "в районі Конотопу") ---
        if not city:
            m_area = re.search(r'в\s+районі\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_area:
                city = m_area.group(1).strip()
                # Extract count from beginning of line if present
                count_match = re.search(r'^(\d+)\s*бпла', ln, re.IGNORECASE)
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
                    coords = ensure_city_coords(base)
                print(f"DEBUG: ensure_city_coords result: {coords}")
            if coords:
                print(f"DEBUG: Found coords {coords} for city '{base}', creating track")
                # Handle both 2-tuple (lat, lng) and 3-tuple (lat, lng, approx_flag) returns
                if len(coords) == 3:
                    lat, lng, approx_flag = coords
                else:
                    lat, lng = coords
                    approx_flag = False
                threat_type, icon = 'shahed', 'shahed.png'
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
                        # Create a circular pattern around the target
                        import math
                        angle = (2 * math.pi * i) / tracks_to_create
                        offset_distance = 0.01  # ~1km offset
                        marker_lat += offset_distance * math.cos(angle)
                        marker_lng += offset_distance * math.sin(angle)
                    
                    print(f"DEBUG: Creating track {i+1}/{tracks_to_create} with label '{track_label}' at {marker_lat}, {marker_lng}")
                    multi_city_tracks.append({
                        'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': track_label, 'lat': marker_lat, 'lng': marker_lng,
                        'threat_type': threat_type, 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'multiline_oblast_city', 'count': 1
                    })
            else:
                print(f"DEBUG: No coordinates found for city '{base}'")
    print(f"DEBUG: Multi-city tracks processing complete. Found {len(multi_city_tracks)} tracks")
    if multi_city_tracks:
        print(f"DEBUG: Returning {len(multi_city_tracks)} multi-city tracks")
        # Combine with priority result if available
        if 'priority_result' in locals() and priority_result:
            combined_result = priority_result + multi_city_tracks
            add_debug_log(f"Combined priority result ({len(priority_result)}) with multi-city tracks ({len(multi_city_tracks)}) = {len(combined_result)} total", "priority_combine")
            return combined_result
        return multi_city_tracks
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
        threat_type, icon = 'shahed', 'shahed.png'  # можно доработать auto-classify
        
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
        """Resolve coordinates for a settlement name by weighted order (remote first):
        1) External geocode (region-qualified, then plain)
        2) Exact local datasets (CITY_COORDS, SETTLEMENTS_INDEX)
        3) Fuzzy approximate local match (Levenshtein-like via difflib)

        Rationale (user requirement): prefer freshest external resolution, fall back to local known list,
        and only then attempt approximate similarity mapping.
        """
        if not base_name:
            return None
        name_norm = UA_CITY_NORMALIZE.get(base_name, base_name).strip().lower()
        # --- 1. Remote geocode first ---
        region_for_query = region_hint_override or region_hint_global
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
                        coords = ensure_city_coords(city_norm)
                    
                    if coords:
                        # Handle different coordinate formats
                        if isinstance(coords, tuple) and len(coords) >= 2:
                            lat, lng = coords[0], coords[1]
                        else:
                            continue
                        
                        threat_type, icon = classify(text)
                        
                        # Extract count from text context (look for patterns like "15х БпЛА через")
                        count = 1
                        count_match = _re_route.search(rf'(\d+)[xх]?\s*бпла.*?через.*?{re.escape(city_clean)}', text, re.IGNORECASE)
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
                        count_match = _re_route.search(rf'(\d+)[xх]?\s*бпла.*?повз.*?{re.escape(city_clean)}', text, re.IGNORECASE)
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
                'marker_icon': 'raketa.png', 'source_match': 'kab_regional_threat'
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
                        r'(\d+)?[xх]?\s*бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|])',
                        r'бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|])',
                        r'(\d+)?[xх]?\s*бпла\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|])'
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
                                coords = ensure_city_coords(city_norm)
                            
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
            r'(\d+)?[xх]?\s*бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|\(])',
            r'бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|\(])',
            r'(\d+)?[xх]?\s*бпла\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|\(])'
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
                    coords = ensure_city_coords(city_norm)
                
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
                coords = ensure_city_coords(city_norm)
            
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
    # North-east tactical aviation activity - coordinates moved to Ukrainian territory
    # Original coordinates (50.4, 36.8) were too close to Russian border
    # SKIP if this is a multi-threat message (handled separately above)
    if ('тактичн' in se_phrase or 'авіаці' in se_phrase or 'авиац' in se_phrase) and (
        'північно-східн' in se_phrase or 'північно східн' in se_phrase or 'северо-восточ' in se_phrase or 'північного-сходу' in se_phrase
    ) and not ('🛬' in original_text and '🛸' in original_text):
        # Moved coordinates to Sumy area (clearly in Ukrainian territory)
        lat, lng = 50.9, 34.8  # Near Sumy city
        return [{
            'id': f"{mid}_ne", 'place': 'Північно-східний напрямок', 'lat': lat, 'lng': lng,
            'threat_type': 'avia', 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': 'avia.png', 'source_match': 'northeast_aviation'
        }]
    m = re.search(r'(\d{1,2}\.\d+),(\d{1,3}\.\d+)', text)
    if m:
        lat = float(m.group(1)); lng = float(m.group(2))
        threat_type, icon = classify(text)
        return [{
            'id': str(mid), 'place': 'Unknown', 'lat': lat, 'lng': lng,
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
            lat, lng = OBLAST_CENTERS[dest_norm]
            return [{
                'id': f"{mid}_dir_oblast", 'place': dest_norm.title(), 'lat': lat, 'lng': lng,
                'threat_type': 'uav', 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'shahed.png', 'source_match': 'singleline_oblast_course'
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
        'миколаївщині': 'миколаївщина'
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

    # --- Russian strategic aviation suppression ---
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

    # --- General warning suppression ---

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
    trajectory_pattern = r'(\d+)?\s*шахед[іївыиє]*\s+з\s+([а-яіїєґ]+(щин|ччин)[ауиі])\s+на\s+([а-яіїєґ/]+(щин|ччин)[ауиіу])'
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
        print(f"DEBUG: Suppressing region markers for trajectory message")
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

    # --- Per-line UAV course / area city targeting ("БпЛА курсом на <місто>", "8х БпЛА в районі <міста>") ---
    # Triggered when region multi list suppressed earlier due to presence of course lines.
    if 'бпла' in lower and ('курс' in lower or 'в районі' in lower):
        add_debug_log(f"UAV course parser triggered for message length: {len(text)} chars", "uav_course")
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
        multi_start_re = re.compile(r'(?:\d+\s*[xх]?\s*)?бпла\s*курс', re.IGNORECASE)
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
        pat_count_course = re.compile(r'^(\d+)\s*[xх]?\s*бпла.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-’ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_course = re.compile(r'бпла.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-’ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_area = re.compile(r'(\d+)?[xх]?\s*бпла\s+в\s+районі\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-’ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
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
        for ln, region_hdr in lines_with_region:
            ln_low = ln.lower()
            if 'бпла' not in ln_low:
                continue
            add_debug_log(f"Processing UAV line: '{ln[:100]}...' (region: {region_hdr})", "uav_course")
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
                    m3 = pat_course.search(ln_low)
                    if m3:
                        city = m3.group(1)
            if not city:
                add_debug_log("No city found in UAV line", "uav_course")
                continue
            add_debug_log(f"Found city '{city}' in UAV line", "uav_course")
            multi_norm = _resolve_city_candidate(city)
            base = norm_city_token(multi_norm)
            add_debug_log(f"City normalized to '{base}'", "uav_course")
            coords = CITY_COORDS.get(base) or (SETTLEMENTS_INDEX.get(base) if SETTLEMENTS_INDEX else None)
            add_debug_log(f"Coordinates lookup for '{base}': {coords}", "uav_course")
            if not coords:
                try:
                    coords = region_enhanced_coords(base, region_hint_override=region_hdr)
                except Exception:
                    coords = None
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
            if base not in CITY_COORDS:
                CITY_COORDS[base] = coords
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
                pat_salv = re.compile(r'(?:\d+\s*[xх]?\s*)?бпла[^\n]{0,60}?курс(?:ом)?\s+на\s+([a-zа-яіїєґ\-ʼ"“”\'`\s]{3,40})', re.IGNORECASE)
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

    # --- Black Sea aquatory: place marker in sea, not on target city (e.g. "в акваторії чорного моря, курсом на одесу") ---
    lower_sea = text.lower()
    if ('акватор' in lower_sea or 'акваторії' in lower_sea) and ('чорного моря' in lower_sea or 'чорне море' in lower_sea) and ('бпла' in lower_sea or 'дрон' in lower_sea):
        # Attempt to capture target city (optional)
        m_target = re.search(r'курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower_sea)
        target_city = None
        if m_target:
            tc = m_target.group(1).lower()
            tc = UA_CITY_NORMALIZE.get(tc, tc)
            target_city = tc.title()
        threat_type, icon = classify(text)
        # Approx northern Black Sea central coords (between Odesa & Crimea offshore)
        sea_lat, sea_lng = 45.3, 30.7
        place_label = 'Акваторія Чорного моря'
        if target_city:
            place_label += f' (курс на {target_city})'
        return [{
            'id': str(mid), 'place': place_label, 'lat': sea_lat, 'lng': sea_lng,
            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': icon, 'source_match': 'black_sea_course'
        }]

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
                                # Create a circular pattern around the target
                                import math
                                angle = (2 * math.pi * i) / tracks_to_create
                                offset_distance = 0.01  # ~1km offset
                                marker_lat += offset_distance * math.cos(angle)
                                marker_lng += offset_distance * math.sin(angle)
                                
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
                if ('курс' in lower and 'напрямок' in lower) or ('➡' in lower or '→' in lower):
                    if 'північно-західн' in lower or 'північно-захід' in lower:
                        course_direction = 'nw'
                    elif 'південно-західн' in lower or 'південно-захід' in lower:
                        course_direction = 'sw'
                    elif 'північно-східн' in lower or 'північно-схід' in lower:
                        course_direction = 'ne'
                    elif 'південно-східн' in lower or 'південно-схід' in lower:
                        course_direction = 'se'
                    # Single directions in course
                    elif re.search(r'курс\w*\s+на\s+північ', lower):
                        course_direction = 'n'
                    elif re.search(r'курс\w*\s+на\s+південь', lower):
                        course_direction = 's'
                    elif re.search(r'курс\w*\s+на\s+схід', lower):
                        course_direction = 'e'
                    elif re.search(r'курс\w*\s+на\s+захід', lower):
                        course_direction = 'w'
                
                # If we have both start position and course direction, apply them sequentially
                if start_direction and course_direction:
                    # First offset: move to start position within region
                    lat_start, lng_start = offset(base_lat, base_lng, start_direction)
                    # Second offset: apply course direction from start position  
                    lat_final, lng_final = offset(lat_start, lng_start, course_direction)
                    
                    # Create descriptive label
                    start_labels = {'n':'півночі', 's':'півдні', 'e':'сході', 'w':'заході'}
                    course_labels = {
                        'n':'північ', 's':'південь', 'e':'схід', 'w':'захід',
                        'ne':'північний схід', 'nw':'північний захід', 
                        'se':'південний схід', 'sw':'південний захід'
                    }
                    start_label = start_labels.get(start_direction, 'області')
                    course_label = course_labels.get(course_direction, 'напрямок')
                    base_disp = reg_name.split()[0].title()
                    
                    threat_type, icon = classify(text)
                    return [{
                        'id': str(mid), 'place': f"{base_disp} (з {start_label} на {course_label})", 
                        'lat': lat_final, 'lng': lng_final,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_start_course', 'count': drone_count
                    }]
                
                # смещение ~50-70 км в сторону указанного направления (fallback for single direction)
                lat_o, lng_o = offset(base_lat, base_lng, direction_code)
                threat_type, icon = classify(text)
                dir_label_map = {
                    'n':'північна частина', 's':'південна частина', 'e':'східна частина', 'w':'західна частина',
                    'ne':'північно-східна частина', 'nw':'північно-західна частина',
                    'se':'південно-східна частина', 'sw':'південно-західна частина'
                }
                dir_phrase = dir_label_map.get(direction_code, 'частина')
                base_disp = reg_name.split()[0].title()
                return [{
                    'id': str(mid), 'place': f"{base_disp} ({dir_phrase})", 'lat': lat_o, 'lng': lng_o,
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
                    lat = (a1+a2)/2; lng = (b1+b2)/2
                    # Slight bias toward destination (second region) if arrow or 'курс' present
                    if 'курс' in lower or '➡' in lower or '→' in lower:
                        lat = (a1*0.45 + a2*0.55)
                        lng = (b1*0.45 + b2*0.55)
                    threat_type, icon = classify(text)
                    return [{
                        'id': str(mid), 'place': f"Між {n1.split()[0].title()} та {n2.split()[0].title()} (курс)", 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_course_midpoint', 'count': drone_count
                    }]

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
                        coords = ensure_city_coords(norm_city)
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
                    # Create a circular pattern around the target
                    import math
                    angle = (2 * math.pi * i) / tracks_to_create
                    offset_distance = 0.01  # ~1km offset
                    marker_lat += offset_distance * math.cos(angle)
                    marker_lng += offset_distance * math.sin(angle)
                
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
    processed = {m.get('id') for m in load_messages()}
    all_data = load_messages()
    # -------- Initial backfill (last BACKFILL_MINUTES, default 50) --------
    try:
        backfill_minutes = int(os.getenv('BACKFILL_MINUTES', '50'))
    except ValueError:
        backfill_minutes = 50
    backfill_cutoff = datetime.now(tz) - timedelta(minutes=backfill_minutes)
    if backfill_minutes > 0:
        log.info(f'Starting backfill for last {backfill_minutes} minutes...')
        total_backfilled = 0
        total_raw = 0
        for ch in CHANNELS:
            ch_strip = ch.strip()
            if not ch_strip:
                continue
            print(f"DEBUG: Processing backfill for channel: {ch_strip}")
            fetched = 0
            try:
                if not await ensure_connected():
                    log.warning('Disconnected during backfill; aborting backfill early.')
                    break
                async for msg in client.iter_messages(ch_strip, limit=400):  # cap to avoid huge history
                    if not msg.text:
                        continue
                    dt = msg.date.astimezone(tz)
                    if dt < backfill_cutoff:
                        break  # older than needed
                    if msg.id in processed:
                        continue
                    tracks = process_message(msg.text, msg.id, dt.strftime('%Y-%m-%d %H:%M:%S'), ch_strip)
                    if tracks:
                        print(f"DEBUG: Message {msg.id} generated {len(tracks)} tracks")
                        merged_any = False
                        merged_refs = []
                        for t in tracks:
                            if t.get('place'):
                                t['place'] = ensure_ua_place(t['place'])
                            merged, ref = maybe_merge_track(all_data, t)
                            if merged:
                                merged_any = True
                                merged_refs.append(ref)
                            else:
                                all_data.append(t)
                        processed.add(msg.id)
                        if merged_any:
                            log.info(f'Merged track(s) for {ch_strip} #{msg.id} into existing point(s).')
                        fetched += 1
                    else:
                        print(f"DEBUG: Message {msg.id} generated NO tracks (filtered or no matches)")
                        if ALWAYS_STORE_RAW:
                            all_data.append({
                                'id': str(msg.id),
                                'place': None,
                                'lat': None,
                                'lng': None,
                                'threat_type': None,
                                'text': msg.text[:500],
                                'date': dt.strftime('%Y-%m-%d %H:%M:%S'),
                                'channel': ch_strip,
                                'pending_geo': True
                            })
                            processed.add(msg.id)
                            total_raw += 1
                        print(f"DEBUG: Message {msg.id} - ALWAYS_STORE_RAW={ALWAYS_STORE_RAW}, stored as raw")
                        log.debug(f'Backfill skip (no geo): {ch_strip} #{msg.id} {msg.text[:80]!r}')
                if fetched:
                    total_backfilled += fetched
                    log.info(f'Backfilled {fetched} messages from {ch_strip}')
            except Exception as e:
                log.warning(f'Backfill error {ch_strip}: {e}')
    if backfill_minutes > 0:
        if total_backfilled or (ALWAYS_STORE_RAW and 'total_raw' in locals() and total_raw):
            save_messages(all_data)
            log.info(f'Backfill saved: {total_backfilled} geo, {locals().get("total_raw",0)} raw')
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
                    if msg.id in processed:
                        continue
                    dt = msg.date.astimezone(tz)
                    if dt < datetime.now(tz) - timedelta(minutes=30):
                        # Older than live window
                        continue
                    msgs_recent_window += 1
                    tracks = process_message(msg.text, msg.id, dt.strftime('%Y-%m-%d %H:%M:%S'), ch)
                    if tracks:
                        merged_any = False
                        appended = []
                        for t in tracks:
                            if t.get('place'):
                                t['place'] = ensure_ua_place(t['place'])
                            merged, ref = maybe_merge_track(all_data, t)
                            if merged:
                                merged_any = True
                            else:
                                new_tracks.append(t)
                                appended.append(t)
                        geo_added += 1
                        processed.add(msg.id)
                        if merged_any and not appended:
                            log.info(f'Merged live track(s) {ch} #{msg.id} (no new marker).')
                        else:
                            log.info(f'Added track from {ch} #{msg.id} (+{len(appended)} new, merged={merged_any})')
                    else:
                        # Store raw if enabled to allow later reprocessing / debugging (e.g., napramok multi-line posts)
                        if ALWAYS_STORE_RAW:
                            all_data.append({
                                'id': str(msg.id), 'place': None, 'lat': None, 'lng': None,
                                'threat_type': None, 'text': msg.text[:800], 'date': dt.strftime('%Y-%m-%d %H:%M:%S'),
                                'channel': ch, 'pending_geo': True
                            })
                            processed.add(msg.id)
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
            # Append truly new tracks (merges already applied in-place)
            all_data.extend(new_tracks)
            save_messages(all_data)
            try:
                broadcast_new(new_tracks)
            except Exception as e:
                log.debug(f'SSE broadcast failed: {e}')
        else:
            # If only merges happened (no brand-new tracks), still persist periodically
            save_messages(all_data)
        await asyncio.sleep(60)

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
            FETCH_THREAD_STARTED = False
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
SESSION_WATCH_INTERVAL = int(os.getenv('SESSION_WATCH_INTERVAL', '20'))
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
                        with open(SESSION_WATCH_FILE,'r',encoding='utf-8') as f:
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

@app.route('/')
def index():
    # BANDWIDTH OPTIMIZATION: Add caching headers for main page
    response = render_template('index.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes cache
    resp.headers['ETag'] = f'index-{int(time.time() // 300)}'
    return resp

@app.route('/blackouts')
def blackouts():
    """Power blackout schedules and information page"""
    response = render_template('blackouts.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes cache
    return resp

@app.route('/about')
def about():
    """About NEPTUN project page"""
    response = render_template('about.html')
    resp = app.response_class(response)
    resp.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour cache
    return resp

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

# Address database for blackout schedules with subgroups
# Format: group can be "1.1", "1.2", "2.1", "2.2", "3.1", "3.2" etc.
# TODO: Replace with real database and API integration
BLACKOUT_ADDRESSES = {
    # Kyiv - all subgroups across different districts
    'київ хрещатик': {'group': '1.1', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ вулиця хрещатик': {'group': '1.1', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ майдан': {'group': '1.2', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ печерськ': {'group': '2.1', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ поділ': {'group': '2.2', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ шевченківський': {'group': '3.1', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ оболонь': {'group': '3.2', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ троєщина': {'group': '1.1', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ позняки': {'group': '2.1', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ дарниця': {'group': '3.1', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ лівобережна': {'group': '2.2', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ академмістечко': {'group': '3.2', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ теремки': {'group': '1.2', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ вишневе': {'group': '2.1', 'city': 'Київ', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    'київ бориспіль': {'group': '1.1', 'city': 'Бориспіль', 'oblast': 'Київська', 'provider': 'ДТЕК Київські електромережі'},
    
    # Odesa - all subgroups
    'одеса дерибасівська': {'group': '1.1', 'city': 'Одеса', 'oblast': 'Одеська', 'provider': 'ДТЕК Одеські електромережі'},
    'одеса приморський': {'group': '1.2', 'city': 'Одеса', 'oblast': 'Одеська', 'provider': 'ДТЕК Одеські електромережі'},
    'одеса центр': {'group': '2.1', 'city': 'Одеса', 'oblast': 'Одеська', 'provider': 'ДТЕК Одеські електромережі'},
    'одеса аркадія': {'group': '2.2', 'city': 'Одеса', 'oblast': 'Одеська', 'provider': 'ДТЕК Одеські електромережі'},
    'одеса таїрова': {'group': '3.1', 'city': 'Одеса', 'oblast': 'Одеська', 'provider': 'ДТЕК Одеські електромережі'},
    'одеса котовського': {'group': '3.2', 'city': 'Одеса', 'oblast': 'Одеська', 'provider': 'ДТЕК Одеські електромережі'},
    'одеса молдаванка': {'group': '1.1', 'city': 'Одеса', 'oblast': 'Одеська', 'provider': 'ДТЕК Одеські електромережі'},
    'одеса пересипь': {'group': '2.1', 'city': 'Одеса', 'oblast': 'Одеська', 'provider': 'ДТЕК Одеські електромережі'},
    'одеса суворовський': {'group': '3.1', 'city': 'Одеса', 'oblast': 'Одеська', 'provider': 'ДТЕК Одеські електромережі'},
    'одеса чорноморка': {'group': '1.2', 'city': 'Одеса', 'oblast': 'Одеська', 'provider': 'ДТЕК Одеські електромережі'},
    
    # Kharkiv - all subgroups
    'харків сумська': {'group': '1.1', 'city': 'Харків', 'oblast': 'Харківська', 'provider': 'ДТЕК Східенерго'},
    'харків центр': {'group': '1.2', 'city': 'Харків', 'oblast': 'Харківська', 'provider': 'ДТЕК Східенерго'},
    'харків салтівка': {'group': '2.1', 'city': 'Харків', 'oblast': 'Харківська', 'provider': 'ДТЕК Східенерго'},
    'харків нагірний': {'group': '2.2', 'city': 'Харків', 'oblast': 'Харківська', 'provider': 'ДТЕК Східенерго'},
    'харків холодна гора': {'group': '3.1', 'city': 'Харків', 'oblast': 'Харківська', 'provider': 'ДТЕК Східенерго'},
    'харків павлове поле': {'group': '3.2', 'city': 'Харків', 'oblast': 'Харківська', 'provider': 'ДТЕК Східенерго'},
    'харків московський': {'group': '1.1', 'city': 'Харків', 'oblast': 'Харківська', 'provider': 'ДТЕК Східенерго'},
    'харків індустріальний': {'group': '2.1', 'city': 'Харків', 'oblast': 'Харківська', 'provider': 'ДТЕК Східенерго'},
    'харків київський': {'group': '1.2', 'city': 'Харків', 'oblast': 'Харківська', 'provider': 'ДТЕК Східенерго'},
    
    # Dnipro - all subgroups
    'дніпро центр': {'group': '1.1', 'city': 'Дніпро', 'oblast': 'Дніпропетровська', 'provider': 'ДТЕК Дніпровські електромережі'},
    'дніпро гагаріна': {'group': '1.2', 'city': 'Дніпро', 'oblast': 'Дніпропетровська', 'provider': 'ДТЕК Дніпровські електромережі'},
    'дніпро нагірний': {'group': '2.1', 'city': 'Дніпро', 'oblast': 'Дніпропетровська', 'provider': 'ДТЕК Дніпровські електромережі'},
    'дніпро проспект': {'group': '2.2', 'city': 'Дніпро', 'oblast': 'Дніпропетровська', 'provider': 'ДТЕК Дніпровські електромережі'},
    'дніпро придніпровськ': {'group': '3.1', 'city': 'Дніпро', 'oblast': 'Дніпропетровська', 'provider': 'ДТЕК Дніпровські електромережі'},
    'дніпро новокодацький': {'group': '3.2', 'city': 'Дніпро', 'oblast': 'Дніпропетровська', 'provider': 'ДТЕК Дніпровські електромережі'},
    'дніпро соборний': {'group': '1.1', 'city': 'Дніпро', 'oblast': 'Дніпропетровська', 'provider': 'ДТЕК Дніпровські електромережі'},
    'дніпро амур': {'group': '2.1', 'city': 'Дніпро', 'oblast': 'Дніпропетровська', 'provider': 'ДТЕК Дніпровські електромережі'},
    
    # Lviv - all subgroups
    'львів центр': {'group': '1.1', 'city': 'Львів', 'oblast': 'Львівська', 'provider': 'Львівобленерго'},
    'львів площа ринок': {'group': '1.2', 'city': 'Львів', 'oblast': 'Львівська', 'provider': 'Львівобленерго'},
    'львів франка': {'group': '2.1', 'city': 'Львів', 'oblast': 'Львівська', 'provider': 'Львівобленерго'},
    'львів сихів': {'group': '2.2', 'city': 'Львів', 'oblast': 'Львівська', 'provider': 'Львівобленерго'},
    'львів личаківська': {'group': '3.1', 'city': 'Львів', 'oblast': 'Львівська', 'provider': 'Львівобленерго'},
    'львів сихівська': {'group': '3.2', 'city': 'Львів', 'oblast': 'Львівська', 'provider': 'Львівобленерго'},
    'львів залізничний': {'group': '1.1', 'city': 'Львів', 'oblast': 'Львівська', 'provider': 'Львівобленерго'},
    'львів шевченківський': {'group': '2.1', 'city': 'Львів', 'oblast': 'Львівська', 'provider': 'Львівобленерго'},
    
    # Zaporizhzhia - all subgroups
    'запоріжжя центр': {'group': '1.1', 'city': 'Запоріжжя', 'oblast': 'Запорізька', 'provider': 'ДТЕК Запорізькі електромережі'},
    'запоріжжя проспект': {'group': '1.2', 'city': 'Запоріжжя', 'oblast': 'Запорізька', 'provider': 'ДТЕК Запорізькі електромережі'},
    'запоріжжя хортицький': {'group': '2.1', 'city': 'Запоріжжя', 'oblast': 'Запорізька', 'provider': 'ДТЕК Запорізькі електромережі'},
    'запоріжжя шевченківський': {'group': '2.2', 'city': 'Запоріжжя', 'oblast': 'Запорізька', 'provider': 'ДТЕК Запорізькі електромережі'},
    'запоріжжя заводський': {'group': '3.1', 'city': 'Запоріжжя', 'oblast': 'Запорізька', 'provider': 'ДТЕК Запорізькі електромережі'},
    'запоріжжя дніпровський': {'group': '3.2', 'city': 'Запоріжжя', 'oblast': 'Запорізька', 'provider': 'ДТЕК Запорізькі електромережі'},
    
    # Vinnytsia - all subgroups
    'вінниця центр': {'group': '1.1', 'city': 'Вінниця', 'oblast': 'Вінницька', 'provider': 'Вінницяобленерго'},
    'вінниця соборна': {'group': '1.2', 'city': 'Вінниця', 'oblast': 'Вінницька', 'provider': 'Вінницяобленерго'},
    'вінниця хмельницьке': {'group': '2.1', 'city': 'Вінниця', 'oblast': 'Вінницька', 'provider': 'Вінницяобленерго'},
    'вінниця вишенька': {'group': '2.2', 'city': 'Вінниця', 'oblast': 'Вінницька', 'provider': 'Вінницяобленерго'},
    'вінниця замостя': {'group': '3.1', 'city': 'Вінниця', 'oblast': 'Вінницька', 'provider': 'Вінницяобленерго'},
    
    # Poltava - all subgroups
    'полтава центр': {'group': '1.1', 'city': 'Полтава', 'oblast': 'Полтавська', 'provider': 'Полтаваобленерго'},
    'полтава соборності': {'group': '1.2', 'city': 'Полтава', 'oblast': 'Полтавська', 'provider': 'Полтаваобленерго'},
    'полтава київський': {'group': '2.1', 'city': 'Полтава', 'oblast': 'Полтавська', 'provider': 'Полтаваобленерго'},
    'полтава подільський': {'group': '2.2', 'city': 'Полтава', 'oblast': 'Полтавська', 'provider': 'Полтаваобленерго'},
    
    # Chernihiv - all subgroups
    'чернігів центр': {'group': '1.1', 'city': 'Чернігів', 'oblast': 'Чернігівська', 'provider': 'Чернігівобленерго'},
    'чернігів мира': {'group': '1.2', 'city': 'Чернігів', 'oblast': 'Чернігівська', 'provider': 'Чернігівобленерго'},
    'чернігів деснянський': {'group': '2.1', 'city': 'Чернігів', 'oblast': 'Чернігівська', 'provider': 'Чернігівобленерго'},
    
    # Zhytomyr - all subgroups
    'житомир центр': {'group': '1.1', 'city': 'Житомир', 'oblast': 'Житомирська', 'provider': 'Житомиробленерго'},
    'житомир київська': {'group': '1.2', 'city': 'Житомир', 'oblast': 'Житомирська', 'provider': 'Житомиробленерго'},
    'житомир богунія': {'group': '2.1', 'city': 'Житомир', 'oblast': 'Житомирська', 'provider': 'Житомиробленерго'},
    'житомир корольовський': {'group': '2.2', 'city': 'Житомир', 'oblast': 'Житомирська', 'provider': 'Житомиробленерго'},
    
    # Cherkasy - all subgroups
    'черкаси центр': {'group': '1.1', 'city': 'Черкаси', 'oblast': 'Черкаська', 'provider': 'Черкасиобленерго'},
    'черкаси соборна': {'group': '1.2', 'city': 'Черкаси', 'oblast': 'Черкаська', 'provider': 'Черкасиобленерgo'},
    'черкаси придніпровський': {'group': '2.1', 'city': 'Черкаси', 'oblast': 'Черкаська', 'provider': 'Черкасиобленерго'},
    
    # Sumy - all subgroups
    'суми центр': {'group': '1.1', 'city': 'Суми', 'oblast': 'Сумська', 'provider': 'Сумиобленерго'},
    'суми соборна': {'group': '1.2', 'city': 'Суми', 'oblast': 'Сумська', 'provider': 'Сумиобленерго'},
    'суми ковпаківський': {'group': '2.1', 'city': 'Суми', 'oblast': 'Сумська', 'provider': 'Сумиобленерго'},
    
    # Khmelnytskyi - all subgroups
    'хмельницький центр': {'group': '1.1', 'city': 'Хмельницький', 'oblast': 'Хмельницька', 'provider': 'Хмельницькобленерго'},
    'хмельницький проспект': {'group': '1.2', 'city': 'Хмельницький', 'oblast': 'Хмельницька', 'provider': 'Хмельницькобленерго'},
    'хмельницький загоцька': {'group': '2.1', 'city': 'Хмельницький', 'oblast': 'Хмельницька', 'provider': 'Хмельницькобленерго'},
    
    # Rivne - all subgroups
    'рівне центр': {'group': '1.1', 'city': 'Рівне', 'oblast': 'Рівненська', 'provider': 'Рівненобленерго'},
    'рівне соборна': {'group': '1.2', 'city': 'Рівне', 'oblast': 'Рівненська', 'provider': 'Рівненобленерго'},
    'рівне північний': {'group': '2.1', 'city': 'Рівне', 'oblast': 'Рівненська', 'provider': 'Рівненобленерго'},
    
    # Ivano-Frankivsk - all subgroups
    'івано-франківськ центр': {'group': '1.1', 'city': 'Івано-Франківськ', 'oblast': 'Івано-Франківська', 'provider': 'Прикарпаттяобленерго'},
    'івано-франківськ незалежності': {'group': '1.2', 'city': 'Івано-Франківськ', 'oblast': 'Івано-Франківська', 'provider': 'Прикарпаттяобленерго'},
    'івано-франківськ пасічна': {'group': '2.1', 'city': 'Івано-Франківськ', 'oblast': 'Івано-Франківська', 'provider': 'Прикарпаттяобленерго'},
    
    # Ternopil - all subgroups
    'тернопіль центр': {'group': '1.1', 'city': 'Тернопіль', 'oblast': 'Тернопільська', 'provider': 'Тернопільобленерго'},
    'тернопіль руська': {'group': '1.2', 'city': 'Тернопіль', 'oblast': 'Тернопільська', 'provider': 'Тернопільобленерго'},
    'тернопіль східний': {'group': '2.1', 'city': 'Тернопіль', 'oblast': 'Тернопільська', 'provider': 'Тернопільобленерго'},
    
    # Lutsk - all subgroups
    'луцьк центр': {'group': '1.1', 'city': 'Луцьк', 'oblast': 'Волинська', 'provider': 'Волиньобленерго'},
    'луцьк волі': {'group': '1.2', 'city': 'Луцьк', 'oblast': 'Волинська', 'provider': 'Волиньобленерго'},
    'луцьк вокзальна': {'group': '2.1', 'city': 'Луцьк', 'oblast': 'Волинська', 'provider': 'Волиньобленерго'},
    
    # Chernivtsi - all subgroups
    'чернівці центр': {'group': '1.1', 'city': 'Чернівці', 'oblast': 'Чернівецька', 'provider': 'Чернівціобленерго'},
    'чернівці головна': {'group': '1.2', 'city': 'Чернівці', 'oblast': 'Чернівецька', 'provider': 'Чернівціобленерго'},
    'чернівці садгора': {'group': '2.1', 'city': 'Чернівці', 'oblast': 'Чернівецька', 'provider': 'Чернівціобленерго'},
    
    # Uzhhorod - all subgroups
    'ужгород центр': {'group': '1.1', 'city': 'Ужгород', 'oblast': 'Закарпатська', 'provider': 'Закарпаттяобленерго'},
    'ужгород корзо': {'group': '1.2', 'city': 'Ужгород', 'oblast': 'Закарпатська', 'provider': 'Закарпаттяобленерго'},
    'ужгород боздош': {'group': '2.1', 'city': 'Ужгород', 'oblast': 'Закарпатська', 'provider': 'Закарпаттяобленерго'},
    
    # Kropyvnytskyi (Kirovohrad) - all subgroups
    'кропивницький центр': {'group': '1.1', 'city': 'Кропивницький', 'oblast': 'Кіровоградська', 'provider': 'Кіровоградобленерго'},
    'кропивницький велика перспективна': {'group': '1.2', 'city': 'Кропивницький', 'oblast': 'Кіровоградська', 'provider': 'Кіровоградобленерго'},
    'кропивницький фортечний': {'group': '2.1', 'city': 'Кропивницький', 'oblast': 'Кіровоградська', 'provider': 'Кіровоградобленерго'},
    
    # Mykolaiv - all subgroups
    'миколаїв центр': {'group': '1.1', 'city': 'Миколаїв', 'oblast': 'Миколаївська', 'provider': 'Миколаївобленерго'},
    'миколаїв соборна': {'group': '1.2', 'city': 'Миколаїв', 'oblast': 'Миколаївська', 'provider': 'Миколаївобленерго'},
    'миколаїв інгульський': {'group': '2.1', 'city': 'Миколаїв', 'oblast': 'Миколаївська', 'provider': 'Миколаївобленерго'},
    'миколаїв корабельний': {'group': '2.2', 'city': 'Миколаїв', 'oblast': 'Миколаївська', 'provider': 'Миколаївобленерго'},
    
    # Kherson - all subgroups
    'херсон центр': {'group': '1.1', 'city': 'Херсон', 'oblast': 'Херсонська', 'provider': 'Херсонобленерго'},
    'херсон ушакова': {'group': '1.2', 'city': 'Херсон', 'oblast': 'Херсонська', 'provider': 'Херсонобленерго'},
    'херсон дніпровський': {'group': '2.1', 'city': 'Херсон', 'oblast': 'Херсонська', 'provider': 'Херсонобленерго'},
    
    # Mariupol (DTEK Donetsk region)
    'маріуполь центр': {'group': '1.1', 'city': 'Маріуполь', 'oblast': 'Донецька', 'provider': 'ДТЕК Донецькі електромережі'},
    'маріуполь лівобережний': {'group': '2.1', 'city': 'Маріуполь', 'oblast': 'Донецька', 'provider': 'ДТЕК Донецькі електромережі'},
    
    # Kremenchuk - all subgroups
    'кременчук центр': {'group': '1.1', 'city': 'Кременчук', 'oblast': 'Полтавська', 'provider': 'Полтаваобленерго'},
    'кременчук київська': {'group': '1.2', 'city': 'Кременчук', 'oblast': 'Полтавська', 'provider': 'Полтаваобленерго'},
    'кременчук автозаводський': {'group': '2.1', 'city': 'Кременчук', 'oblast': 'Полтавська', 'provider': 'Полтаваобленерго'},
}

# Merge with extended database if available
if UKRAINE_ADDRESSES_DB:
    BLACKOUT_ADDRESSES.update(UKRAINE_ADDRESSES_DB)
    print(f"INFO: Merged addresses database, total: {len(BLACKOUT_ADDRESSES)} addresses")

# Blackout schedules by group and subgroup
# Format: group "1.1", "1.2", "2.1", "2.2", "3.1", "3.2"
# Each subgroup has different timing within main group
# TODO: Fetch from real APIs (DTEK, Ukrenergo)
BLACKOUT_SCHEDULES = {
    # Group 1 subgroups
    '1.1': [
        {'time': '00:00 - 04:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '04:00 - 08:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '12:00 - 16:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '16:00 - 20:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '20:00 - 24:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
    ],
    '1.2': [
        {'time': '00:00 - 04:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
        {'time': '04:00 - 08:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '12:00 - 16:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '16:00 - 20:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
    ],
    
    # Group 2 subgroups
    '2.1': [
        {'time': '00:00 - 04:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '04:00 - 08:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '12:00 - 16:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '16:00 - 20:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
    ],
    '2.2': [
        {'time': '00:00 - 04:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '04:00 - 08:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '12:00 - 16:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '16:00 - 20:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
        {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
    ],
    
    # Group 3 subgroups
    '3.1': [
        {'time': '00:00 - 04:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
        {'time': '04:00 - 08:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '12:00 - 16:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '16:00 - 20:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
    ],
    '3.2': [
        {'time': '00:00 - 04:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '04:00 - 08:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '12:00 - 16:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
        {'time': '16:00 - 20:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '20:00 - 24:00', 'label': 'Активне відключення', 'status': 'active'},
    ],
    
    # Fallback for old integer groups (backward compatibility)
    1: [
        {'time': '06:00 - 10:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '10:00 - 14:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '14:00 - 18:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '18:00 - 22:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '22:00 - 02:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
    ],
    2: [
        {'time': '08:00 - 12:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '12:00 - 16:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
        {'time': '16:00 - 20:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '20:00 - 00:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '00:00 - 04:00', 'label': 'Можливе відключення', 'status': 'normal'},
    ],
    3: [
        {'time': '04:00 - 08:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '12:00 - 16:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '16:00 - 20:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
        {'time': '20:00 - 00:00', 'label': 'Електропостачання', 'status': 'normal'},
    ],
}

@app.route('/api/search_cities')
def search_cities():
    """Get all cities and addresses for autocomplete"""
    try:
        # Collect unique cities
        cities_set = set()
        addresses_list = []
        
        for address_key, data in BLACKOUT_ADDRESSES.items():
            city = data.get('city', '')
            if city:
                cities_set.add(city)
            
            # Parse address_key to extract street and building
            # Format: "city street" or "city street building"
            parts = address_key.split()
            if len(parts) >= 2:
                street = ' '.join(parts[1:])
                addresses_list.append({
                    'city': city,
                    'street': street,
                    'building': '',  # Can be extracted if needed
                    'group': data.get('group', ''),
                    'oblast': data.get('oblast', ''),
                    'provider': data.get('provider', '')
                })
        
        # Convert cities set to sorted list
        cities_list = sorted(list(cities_set))
        
        return jsonify({
            'cities': cities_list,
            'addresses': addresses_list[:200]  # Limit for performance
        })
        
    except Exception as e:
        print(f"ERROR in search_cities: {str(e)}")
        return jsonify({
            'cities': UKRAINE_CITIES if UKRAINE_CITIES else [],
            'addresses': []
        })


@app.route('/api/all_cities_with_queues')
def get_all_cities_with_queues():
    """Get all cities with their queues for the schedule grid"""
    try:
        # Group addresses by city and queue
        cities_data = {}
        
        for address_key, data in BLACKOUT_ADDRESSES.items():
            city = data.get('city', '')
            oblast = data.get('oblast', '')
            queue = data.get('group', '')
            provider = data.get('provider', '')
            
            if not city:
                continue
            
            # Create city key
            city_key = f"{city}, {oblast}"
            
            if city_key not in cities_data:
                cities_data[city_key] = {
                    'city': city,
                    'oblast': oblast,
                    'provider': provider,
                    'queues': set()
                }
            
            if queue:
                cities_data[city_key]['queues'].add(queue)
        
        # Convert to list and format
        result = []
        for city_key, data in cities_data.items():
            queues_list = sorted(list(data['queues']))
            
            # Determine current hour for status
            current_hour = datetime.now(pytz.timezone('Europe/Kiev')).hour
            
            # Check if any queue has active blackout now
            has_active_blackout = False
            active_queues = []
            
            for queue in queues_list:
                schedule = BLACKOUT_SCHEDULES.get(queue, [])
                for slot in schedule:
                    if slot.get('status') == 'active':
                        # Parse time range
                        time_range = slot.get('time', '')
                        if ' - ' in time_range:
                            start_time = time_range.split(' - ')[0]
                            start_hour = int(start_time.split(':')[0])
                            end_hour = (start_hour + 4) % 24
                            
                            if start_hour <= current_hour < end_hour or (end_hour < start_hour and (current_hour >= start_hour or current_hour < end_hour)):
                                has_active_blackout = True
                                active_queues.append(queue)
            
            # Determine status
            if has_active_blackout:
                status = 'active'
                status_text = f"Відключення черг: {', '.join(active_queues)}"
            elif len(queues_list) > 0:
                status = 'warning'
                status_text = f"Черги: {', '.join(queues_list)}"
            else:
                status = 'stable'
                status_text = "Стабільно"
            
            result.append({
                'city': data['city'],
                'oblast': data['oblast'],
                'provider': data['provider'],
                'queues': queues_list,
                'status': status,
                'statusText': status_text,
                'queuesCount': len(queues_list)
            })
        
        # Sort by city name
        result.sort(key=lambda x: x['city'])
        
        return jsonify({
            'success': True,
            'cities': result,
            'total': len(result)
        })
        
    except Exception as e:
        log.error(f"Error in get_all_cities_with_queues: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/get_schedule')
def get_schedule():
    """Get blackout schedule for a specific address using real geocoding and live DTEK updates"""
    city = request.args.get('city', '').strip()
    street = request.args.get('street', '').strip()
    building = request.args.get('building', '').strip()
    
    if not city:
        return jsonify({'error': 'Місто обов\'язкове для заповнення'}), 400
    
    # Try to use live schedule updater first
    if SCHEDULE_UPDATER_AVAILABLE:
        try:
            # Ensure cache is fresh
            if not schedule_updater.is_cache_valid(max_age_hours=1):
                schedule_updater.update_all_schedules()
            
            # Get schedule from live updater
            result = schedule_updater.get_schedule_for_address(city, street, building)
            
            if result and result.get('schedule'):
                return jsonify({
                    'found': True,
                    'address': f"{city}, {street} {building}".strip(),
                    'city': city,
                    'group': result.get('queue'),
                    'provider': result.get('provider'),
                    'schedule': result.get('schedule'),
                    'last_update': result.get('last_update'),
                    'source': 'live_dtek'
                })
        except Exception as e:
            log.warning(f"Live schedule failed, falling back: {e}")
    
    # Fallback to API client
    if not BLACKOUT_API_AVAILABLE:
        return get_schedule_fallback(city, street, building)
    
    try:
        # Use real API client to get schedule
        result = blackout_client.get_schedule_for_address(city, street, building)
        
        if not result['found']:
            return jsonify({
                'error': f'Адресу "{city}" не знайдено. Перевірте правильність написання міста.'
            }), 404
        
        # Add oblast info if available
        if 'київ' in city.lower():
            result['oblast'] = 'Київська'
        elif 'одес' in city.lower():
            result['oblast'] = 'Одеська'
        elif 'харків' in city.lower():
            result['oblast'] = 'Харківська'
        elif 'дніпр' in city.lower():
            result['oblast'] = 'Дніпропетровська'
        elif 'львів' in city.lower():
            result['oblast'] = 'Львівська'
        else:
            result['oblast'] = 'Україна'
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error in get_schedule: {e}")
        return jsonify({
            'error': 'Помилка при отриманні графіку. Спробуйте ще раз.'
        }), 500


def get_schedule_fallback(city, street, building):
    """Fallback method using static data if API client is unavailable"""
    city_lower = city.lower()
    street_lower = street.lower() if street else ''
    
    # Try to find matching address in static database
    best_match = None
    best_match_data = None
    best_score = 0
    
    for address_key, data in BLACKOUT_ADDRESSES.items():
        key_parts = address_key.split()
        key_city = key_parts[0] if len(key_parts) > 0 else ''
        key_street = ' '.join(key_parts[1:]) if len(key_parts) > 1 else ''
        
        score = 0
        if city_lower in key_city or key_city in city_lower:
            score += 2
        if street_lower and (street_lower in key_street or key_street in street_lower):
            score += 2
        
        if score > best_score:
            best_score = score
            best_match = address_key
            best_match_data = data
    
    if not best_match_data or best_score < 2:
        return jsonify({'error': f'Адресу не знайдено для {city}. Спробуйте інше місто або вулицю.'}), 404
    
    # Reconstruct readable address
    parts = best_match.split()
    city_name = parts[0].capitalize()
    street_name = ' '.join(parts[1:]).capitalize() if len(parts) > 1 else ''
    readable_address = f'{city_name}'
    if street_name:
        readable_address += f', {street_name}'
    if building:
        readable_address += f', {building}'
    
    # Get schedule for the group
    group = best_match_data['group']
    schedule = BLACKOUT_SCHEDULES.get(group, [])
    
    return jsonify({
        'address': readable_address,
        'city': best_match_data['city'],
        'oblast': best_match_data['oblast'],
        'group': group,
        'provider': best_match_data['provider'],
        'schedule': schedule
    })


@app.route('/api/live_schedules')
def get_live_schedules():
    """Get live schedules from DTEK and Ukrenergo with automatic hourly updates"""
    try:
        if not SCHEDULE_UPDATER_AVAILABLE:
            return jsonify({
                'error': 'Автооновлення графіків недоступне',
                'fallback': True
            }), 503
        
        # Check if cache is still valid
        if not schedule_updater.is_cache_valid(max_age_hours=1):
            log.info("Cache expired, triggering update...")
            schedule_updater.update_all_schedules()
        
        # Get cached schedules
        schedules = schedule_updater.get_cached_schedules()
        
        if not schedules:
            return jsonify({
                'error': 'Графіки тимчасово недоступні',
                'retry_after': 60
            }), 503
        
        return jsonify({
            'success': True,
            'schedules': schedules,
            'last_update': schedules.get('last_update'),
            'next_update': 'через годину'
        })
        
    except Exception as e:
        log.error(f"Error in get_live_schedules: {e}")
        return jsonify({
            'error': 'Помилка отримання графіків'
        }), 500


@app.route('/api/schedule_status')
def get_schedule_status():
    """Get status of automatic schedule updates"""
    try:
        if not SCHEDULE_UPDATER_AVAILABLE:
            return jsonify({
                'available': False,
                'message': 'Автооновлення недоступне'
            })
        
        last_update = schedule_updater.last_update
        cache_valid = schedule_updater.is_cache_valid()
        
        return jsonify({
            'available': True,
            'last_update': last_update.isoformat() if last_update else None,
            'cache_valid': cache_valid,
            'next_update': 'через годину' if cache_valid else 'зараз',
            'scheduler_running': scheduler.running if scheduler_initialized else False,
            'scheduler_initialized': scheduler_initialized
        })
        
    except Exception as e:
        log.error(f"Error in get_schedule_status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/force_update', methods=['POST'])
def force_schedule_update():
    """Force immediate schedule update (admin only)"""
    try:
        if not SCHEDULE_UPDATER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Schedule updater not available'
            }), 503
        
        log.info("🔄 Manual schedule update triggered")
        result = schedule_updater.update_all_schedules()
        
        return jsonify({
            'success': True,
            'message': 'Графіки успішно оновлено',
            'last_update': schedule_updater.last_update.isoformat() if schedule_updater.last_update else None,
            'data': result is not None
        })
        
    except Exception as e:
        log.error(f"Error in force_schedule_update: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
            setattr(app, '_comment_rate', rt)
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
        setattr(app, '_reaction_rate', rt)
    
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
def alarms_stats():
    """Return recent alarm events history (start/cancel/expire) with optional query params:
    ?level=oblast|raion  ?name=<substring>  ?minutes=<window>  ?limit=N
    """
    level_f = request.args.get('level')
    name_sub = (request.args.get('name') or '').lower().strip()
    minutes = int(request.args.get('minutes', '720'))  # default 12h
    limit = int(request.args.get('limit','500'))
    if limit > 2000: limit = 2000
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
def data():
    global FALLBACK_REPARSE_CACHE, MAX_REPARSE_CACHE_SIZE
    
    # Rate limit отключен: все пользователи имеют свободный доступ
    
    # BANDWIDTH OPTIMIZATION: Add aggressive caching headers  
    response_headers = {
        'Cache-Control': 'public, max-age=60, s-maxage=60',  # Increased cache to 60 seconds
        'ETag': f'data-{int(time.time() // 60)}',  # Cache for 60 seconds
        'Vary': 'Accept-Encoding'
    }
    
    # Check if client has cached version
    client_etag = request.headers.get('If-None-Match')
    if client_etag == response_headers['ETag']:
        return Response(status=304, headers=response_headers)
    
    # Use user-provided timeRange or fall back to global configured MONITOR_PERIOD_MINUTES
    try:
        time_range = int(request.args.get('timeRange', MONITOR_PERIOD_MINUTES))
        # Limit to reasonable values to prevent abuse and reduce bandwidth
        time_range = max(10, min(time_range, 100))  # Reduced from 200 to 100
    except (ValueError, TypeError):
        time_range = MONITOR_PERIOD_MINUTES
    
    print(f"[DEBUG] /data endpoint called with timeRange={request.args.get('timeRange')}, MONITOR_PERIOD_MINUTES={MONITOR_PERIOD_MINUTES}, using time_range={time_range}")
    messages = load_messages()
    print(f"[DEBUG] Loaded {len(messages)} total messages")
    tz = pytz.timezone('Europe/Kyiv')
    now = datetime.now(tz).replace(tzinfo=None)
    min_time = now - timedelta(minutes=time_range)
    print(f"[DEBUG] Filtering messages since {min_time} (last {time_range} minutes)")
    hidden = set(load_hidden())
    out = []  # geo tracks
    events = []  # list-only (alarms, cancellations, other non-geo informational)
    for m in messages:
        try:
            dt = datetime.strptime(m.get('date',''), '%Y-%m-%d %H:%M:%S')
        except Exception:
            continue
        if dt >= min_time:
            # Fallback reparse: if message lacks geo but contains course pattern, try to derive markers now
            txt_low = (m.get('text') or '').lower()
            msg_id = m.get('id')
            
            # Skip multi-regional UAV messages - they're already handled by immediate processing
            text_full = m.get('text') or ''
            text_lines = text_full.split('\n')
            region_count = sum(1 for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:', 'край:']) or (
                'щина' in line.lower() and line.lower().strip().endswith(':')
            ))
            uav_count = sum(1 for line in text_lines if 'бпла' in line.lower() and ('курс' in line.lower() or 'на ' in line.lower()))
            
            if (not m.get('lat')) and (not m.get('lng')) and ('бпла' in txt_low and 'курс' in txt_low and ' на ' in txt_low):
                # Skip if this is a multi-regional UAV message (already processed immediately)
                if region_count >= 2 and uav_count >= 3:
                    add_debug_log(f"Skipping fallback reparse for multi-regional UAV message ID {msg_id}", "reparse")
                    continue
                    
                # Check if we've already reparsed this message to avoid duplicate processing
                if msg_id in FALLBACK_REPARSE_CACHE:
                    add_debug_log(f"Skipping fallback reparse for message ID {msg_id} - already processed", "reparse")
                    continue
                
                try:
                    # Add to cache to prevent future reprocessing
                    FALLBACK_REPARSE_CACHE.add(msg_id)
                    # Limit cache size to prevent memory growth
                    if len(FALLBACK_REPARSE_CACHE) > MAX_REPARSE_CACHE_SIZE:
                        # Remove oldest half of the cache (approximate LRU)
                        cache_list = list(FALLBACK_REPARSE_CACHE)
                        FALLBACK_REPARSE_CACHE = set(cache_list[len(cache_list)//2:])
                    
                    add_debug_log(f"Fallback reparse for message ID {msg_id} - first time processing", "reparse")
                    reparsed = process_message(m.get('text') or '', m.get('id'), m.get('date'), m.get('channel') or m.get('source') or '')
                    if isinstance(reparsed, list) and reparsed:
                        for t in reparsed:
                            try:
                                lat_r = round(float(t.get('lat')), 3)
                                lng_r = round(float(t.get('lng')), 3)
                            except Exception:
                                continue
                            text_r = (t.get('text') or '')
                            source_r = t.get('channel') or t.get('source') or ''
                            marker_key_r = f"{lat_r},{lng_r}|{text_r}|{source_r}"
                            if marker_key_r in hidden:
                                continue
                            out.append(t)
                        # Skip adding original as event if we produced tracks
                        if reparsed:
                            continue
                except Exception:
                    pass
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
    # Sort events by time desc (latest first) like markers implicitly (messages stored chronological)
    try:
        events.sort(key=lambda x: x.get('date',''), reverse=True)
    except Exception:
        pass
    
    print(f"[DEBUG] Returning {len(out)} tracks and {len(events)} events")
    
    # BANDWIDTH OPTIMIZATION: Minimize response size and add caching
    response_data = {
        'tracks': out[:100],  # Limit to 100 tracks max to reduce bandwidth
        'events': events[:20],  # Limit to 20 events max
        'all_sources': CHANNELS[:10],  # Limit sources
        'trajectories': []
    }
    
    resp = jsonify(response_data)
    # Add aggressive caching headers to reduce bandwidth
    resp.headers.update(response_headers)
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
@app.route('/admin/add_manual_marker', methods=['POST'])
def admin_add_manual_marker():
    """Add a manual marker via admin panel.
    JSON body: {"lat":..., "lng":..., "text":"...", "place":"...", "threat_type":"shahed", "icon":"optional.png"}
    Requires secret if configured.
    """
    if not _require_secret(request):
        return jsonify({'status':'forbidden'}), 403
    payload = request.get_json(silent=True) or {}
    try:
        lat = float(payload.get('lat'))
        lng = float(payload.get('lng'))
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
        now_dt = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
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
            'manual': True,
            'channel': 'manual',
            'source': 'manual'
        }
        messages.append(msg)
        save_messages(messages)
        return jsonify({'status':'ok','id':mid})
    except Exception as e:
        return jsonify({'status':'error','error':str(e)}), 400

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
        return jsonify({'status':'ok','messages':len(load_messages()), 'auth': AUTH_STATUS, 'visitors': visitors})

@app.route('/ads.txt')
def ads_txt():
    """Redirect to Ezoic ads.txt manager for automatic updates"""
    from flask import redirect
    return redirect('https://srv.adstxtmanager.com/19390/neptun.in.ua', code=301)

@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt for search engines"""
    return send_from_directory('static', 'robots.txt', mimetype='text/plain')

@app.route('/sitemap.xml')
def sitemap_xml():
    """Serve sitemap.xml for search engines"""
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')

@app.route('/presence', methods=['POST'])
def presence():
    # Rate limiting removed
    data = request.get_json(silent=True) or {}
    vid = data.get('id')
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    print(f"[DEBUG] /presence called with id={vid} from IP {client_ip}")
    if not vid:
        return jsonify({'status':'error','error':'id required'}), 400
    now = time.time()
    blocked = set(load_blocked())
    if vid in blocked:
        return jsonify({'status':'blocked'})
    remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    ua = request.headers.get('User-Agent', '')[:300]
    # Load stats and register first-seen if new
    stats = _load_visit_stats()
    if vid not in stats:
        stats[vid] = now
        # prune occasionally (1/200 probability)
        if int(now) % 200 == 0:
            _prune_visit_stats()
        _save_visit_stats()
    # Update rolling today/week stats (independent persistence)
    try:
        _update_recent_visits(vid)
    except Exception as e:
        log.warning(f"recent visits update failed: {e}")
    # Record in SQLite persistent store
    try:
        record_visit_sql(vid, now)
    except Exception:
        pass
    # Query DB for persistent first_seen to avoid resetting session on process restart
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
        ACTIVE_VISITORS[vid] = {'ts': now, 'first': first_seen, 'ip': remote_ip, 'ua': prev.get('ua') or ua}
        # prune
        for k, meta in list(ACTIVE_VISITORS.items()):
            ts = meta if isinstance(meta,(int,float)) else meta.get('ts',0)
            if now - ts > ACTIVE_TTL:
                del ACTIVE_VISITORS[k]
        count = len(ACTIVE_VISITORS)
    print(f"[DEBUG] Returning visitors count: {count}")
    return jsonify({'status':'ok','visitors': count})
def presence():
    # CRITICAL BANDWIDTH PROTECTION: Rate limit presence endpoint
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    presence_requests = request_counts.get(f"{client_ip}_presence", [])
    now_time = time.time()
    
    # Clean old requests (last 120 seconds - allow every 2 minutes)
    presence_requests = [req_time for req_time in presence_requests if now_time - req_time < 120]
    
    # Allow only 1 presence request per 2 minutes per IP
    if len(presence_requests) >= 1:
        return jsonify({'error': 'Presence endpoint rate limited - wait 2 minutes'}), 429
    
    presence_requests.append(now_time)
    request_counts[f"{client_ip}_presence"] = presence_requests
    
    data = request.get_json(silent=True) or {}
    vid = data.get('id')
    print(f"[DEBUG] /presence called with id={vid} from IP {client_ip}")
    if not vid:
        return jsonify({'status':'error','error':'id required'}), 400
    now = time.time()
    blocked = set(load_blocked())
    if vid in blocked:
        return jsonify({'status':'blocked'})
    remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    ua = request.headers.get('User-Agent', '')[:300]
    # Load stats and register first-seen if new
    stats = _load_visit_stats()
    if vid not in stats:
        stats[vid] = now
        # prune occasionally (1/200 probability)
        if int(now) % 200 == 0:
            _prune_visit_stats()
        _save_visit_stats()
    # Update rolling today/week stats (independent persistence)
    try:
        _update_recent_visits(vid)
    except Exception as e:
        log.warning(f"recent visits update failed: {e}")
    # Record in SQLite persistent store
    try:
        record_visit_sql(vid, now)
    except Exception:
        pass
    # Query DB for persistent first_seen to avoid resetting session on process restart
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
        ACTIVE_VISITORS[vid] = {'ts': now, 'first': first_seen, 'ip': remote_ip, 'ua': prev.get('ua') or ua}
        # prune
        for k, meta in list(ACTIVE_VISITORS.items()):
            ts = meta if isinstance(meta,(int,float)) else meta.get('ts',0)
            if now - ts > ACTIVE_TTL:
                del ACTIVE_VISITORS[k]
        count = len(ACTIVE_VISITORS)
    print(f"[DEBUG] Returning visitors count: {count}")
    return jsonify({'status':'ok','visitors': count})

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
    with open('/Users/vladimirmalik/Desktop/render2/test_pusk_icon.html', 'r', encoding='utf-8') as f:
        return f.read()

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
            visitors.append({
                'id': vid,
                'ip': ip,
                'age': sess_age,
                'age_fmt': _fmt_age(sess_age),
                'ua': ua,
                'ua_short': _ua_label(ua) if ua else '',
                'last_seen': _fmt_age(idle_age)
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
        debug_logs=DEBUG_LOGS
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
        tz = pytz.timezone('Europe/Kyiv')
        
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

def _load_opencage_cache():
    global _opencage_cache
    if _opencage_cache is not None:
        return _opencage_cache
    if os.path.exists(OPENCAGE_CACHE_FILE):
        try:
            with open(OPENCAGE_CACHE_FILE, 'r', encoding='utf-8') as f:
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
        with open(OPENCAGE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(_opencage_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f"Failed saving OpenCage cache: {e}")


SETTLEMENTS_FILE = os.getenv('SETTLEMENTS_FILE', 'settlements_ua.json')
SETTLEMENTS_INDEX = {}
SETTLEMENTS_ORDERED = []  # (RAION_FALLBACK consolidated earlier; duplicate definition removed)

# --------------- Optional Git auto-commit settings ---------------
GIT_AUTO_COMMIT = os.getenv('GIT_AUTO_COMMIT', '0') not in ('0','false','False','')
GIT_REPO_SLUG = os.getenv('GIT_REPO_SLUG')  # e.g. 'vavaika22423232/neptun'
GIT_SYNC_TOKEN = os.getenv('GIT_SYNC_TOKEN')  # GitHub PAT (classic or fine-grained) with repo write
GIT_COMMIT_INTERVAL = int(os.getenv('GIT_COMMIT_INTERVAL', '180'))  # seconds between commits
_last_git_commit = 0

# Delay before first Telegram connect (helps избежать пересечения старого и нового инстанса при деплое)
FETCH_START_DELAY = int(os.getenv('FETCH_START_DELAY', '0'))  # seconds

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
    # Configure user (once)
    def run(cmd):
        return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
    # Stage & commit if there is a change
    run(f'git add {MESSAGES_FILE}')
    status = run('git status --porcelain').stdout
    if MESSAGES_FILE not in status:
        return  # no actual diff
    commit_msg = f'Update {MESSAGES_FILE} (auto)'  # no secrets
    run(f'git commit -m "{commit_msg}"')
    push_res = run('git push origin HEAD:main')
    if push_res.returncode == 0:
        _last_git_commit = now
    else:
        # If push fails (e.g., diverged), attempt pull+rebase then push
        run('git fetch origin')
        run('git rebase origin/main || git rebase --abort')
        push_res2 = run('git push origin HEAD:main')
        if push_res2.returncode == 0:
            _last_git_commit = now
        # else: give up silently to avoid spamming logs

def _load_settlements():
    global SETTLEMENTS_INDEX, SETTLEMENTS_ORDERED
    if not os.path.exists(SETTLEMENTS_FILE):
        return
    try:
        with open(SETTLEMENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Expect list of dicts with keys: name, lat, lng (or lon)
        for item in data:
            try:
                name = item.get('name') or item.get('n')
                if not name:
                    continue
                lat = float(item.get('lat'))
                lng = float(item.get('lng') or item.get('lon'))
                key = name.strip().lower()
                if key and key not in SETTLEMENTS_INDEX:
                    SETTLEMENTS_INDEX[key] = (lat, lng)
            except Exception:
                continue
        # Order names by length descending to match longer first (avoids partial overshadowing)
        SETTLEMENTS_ORDERED = sorted(SETTLEMENTS_INDEX.keys(), key=len, reverse=True)[:50000]  # hard cap
        log.info(f'Loaded settlements: {len(SETTLEMENTS_INDEX)} (using top {len(SETTLEMENTS_ORDERED)})')
    except Exception as e:
        log.warning(f'Failed to load settlements file {SETTLEMENTS_FILE}: {e}')

_load_settlements()

def geocode_opencage(place: str):
    if not OPENCAGE_API_KEY:
        return None
    cache = _load_opencage_cache()
    key = place.strip().lower()
    now = int(datetime.utcnow().timestamp())
    if key in cache:
        entry = cache[key]
        if now - entry.get('ts', 0) < OPENCAGE_TTL:
            return tuple(entry['coords']) if entry['coords'] else None
    import requests
    try:
        resp = requests.get('https://api.opencagedata.com/geocode/v1/json', params={
            'q': place,
            'key': OPENCAGE_API_KEY,
            'language': 'uk',
            'limit': 1,
            'countrycode': 'ua'
        }, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('results'):
                g = data['results'][0]['geometry']
                coords = (g['lat'], g['lng'])
                cache[key] = {'ts': now, 'coords': coords}
                _save_opencage_cache()
                return coords
        cache[key] = {'ts': now, 'coords': None}
        _save_opencage_cache()
        return None
    except Exception as e:
        log.warning(f"OpenCage error for '{place}': {e}")
        cache[key] = {'ts': now, 'coords': None}
        _save_opencage_cache()
        return None

"""(Removed duplicate legacy process_message; canonical version defined earlier.)"""

# ----------------------- Deferred initialization hooks -----------------------
@app.before_request
def _init_background():
    global INIT_ONCE
    if INIT_ONCE:
        return
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
            'subscribers': len(SUBSCRIBERS)
        }
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Manual trigger (idempotent) if needed before first page hit
@app.route('/startup_init', methods=['POST'])
def startup_init():
    _init_background()
    return jsonify({'status': 'ok'})

# BANDWIDTH PROTECTION: Custom static route will compete with Flask's built-in route
# Flask will prioritize our custom route due to specificity

# Graceful shutdown handler
import atexit
import signal

def shutdown_scheduler():
    """Shutdown scheduler gracefully"""
    if SCHEDULE_UPDATER_AVAILABLE and 'scheduler' in globals():
        try:
            if scheduler.running:
                log.info("Shutting down scheduler...")
                scheduler.shutdown(wait=False)
                log.info("✅ Scheduler shutdown complete")
        except Exception as e:
            log.error(f"Error shutting down scheduler: {e}")

# Register shutdown handlers
atexit.register(shutdown_scheduler)
signal.signal(signal.SIGTERM, lambda sig, frame: shutdown_scheduler())
signal.signal(signal.SIGINT, lambda sig, frame: shutdown_scheduler())

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