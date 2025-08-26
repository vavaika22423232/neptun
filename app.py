import os, re, json, asyncio, threading, logging, pytz, time, subprocess, queue, sys, platform, traceback
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, Response
from telethon import TelegramClient
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
_DEFAULT_CHANNELS = 'UkraineAlarmSignal,kpszsu,war_monitor,deraketaua'
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
MONITOR_PERIOD_MINUTES = 50  # default; editable only via admin panel

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
MESSAGES_RETENTION_MINUTES = int(os.getenv('MESSAGES_RETENTION_MINUTES', '0'))  # 0 = keep forever
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
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # After each save attempt optional git auto-commit
    try:
        maybe_git_autocommit()
    except Exception as e:
        log.debug(f'git auto-commit skipped: {e}')

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

UA_CITIES = [
    'київ','харків','одеса','одесса','дніпро','дніпропетровськ','львів','запоріжжя','запорожье','вінниця','миколаїв','николаев','маріуполь','полтава','чернігів','чернигов','черкаси','житомир','суми','хмельницький','чернівці','рівне','івано-франківськ','луцьк','тернопіль','ужгород','кропивницький','кіровоград','кременчук','краматорськ','біла церква','мелітополь','бердянськ','павлоград'
    ,'ніжин','шостка','короп','кролевець'
]
UA_CITY_NORMALIZE = {
    'одесса':'одеса',
    'запорожье':'запоріжжя',
    'дніпропетровськ':'дніпро',
    'кировоград':'кропивницький',
    'кіровоград':'кропивницький',
    'николаев':'миколаїв',
    'чернигов':'чернігів',
    'липову долину':'липова долина'
}

# Static fallback coordinates (approximate city centers) to avoid relying solely on OpenCage.
# Minimal fallback city coords (will be superseded if full settlements file present)
CITY_COORDS = {
    'київ': (50.4501, 30.5234),
    'харків': (49.9935, 36.2304),
    'одеса': (46.4825, 30.7233),
    'дніпро': (48.4647, 35.0462),
    'львів': (49.8397, 24.0297),
    'запоріжжя': (47.8388, 35.1396),
    'вінниця': (49.2331, 28.4682),
    'миколаїв': (46.9750, 31.9946),
    'маріуполь': (47.0971, 37.5434),
    'полтава': (49.5883, 34.5514),
    'чернігів': (51.4982, 31.2893),
    'черкаси': (49.4444, 32.0598),
    'житомир': (50.2547, 28.6587),
    'суми': (50.9077, 34.7981),
    'хмельницький': (49.4229, 26.9871),
    'чернівці': (48.2921, 25.9358),
    'рівне': (50.6199, 26.2516),
    'івано-франківськ': (48.9226, 24.7111),
    'луцьк': (50.7472, 25.3254),
    'тернопіль': (49.5535, 25.5948),
    'ужгород': (48.6208, 22.2879),
    'кропивницький': (48.5079, 32.2623),
    'кременчук': (49.0670, 33.4204),
    'краматорськ': (48.7389, 37.5848),
    'біла церква': (49.7950, 30.1310),
    'мелітополь': (46.8489, 35.3650),
    'бердянськ': (46.7553, 36.7885)
    ,'павлоград': (48.5350, 35.8700)
    ,'ніжин': (51.0480, 31.8860)
    ,'шостка': (51.8667, 33.4833)
    ,'короп': (51.5667, 32.9667)
    ,'кролевець': (51.5481, 33.3847)
    ,'новгород-сіверський': (51.9874, 33.2620)
    ,'сосниця': (51.5236, 32.4953)
    ,'олишівка': (51.1042, 31.6817)
    ,'березна': (51.5756, 31.7431)
    # Additional smaller settlements for course-target parsing
    ,'зачепилівка': (49.1717, 35.2742)
    ,'сахновщина': (49.1544, 35.1460)
    ,'губиниха': (48.7437, 35.2960)
    ,'перещепине': (48.6260, 35.3580)
    ,'обухівка': (48.6035, 34.8530)
    ,'курилівка': (48.6715, 34.8740)
    ,'петриківка': (48.7330, 34.6300)
    ,'підгородне': (48.5747, 35.1482)
    ,'самар': (48.6500, 35.4200)
    ,'верхньодніпровськ': (48.6535, 34.3372)
    ,'горішні плавні': (49.0123, 33.6450)
    ,"кам'янське": (48.5110, 34.6021)
    ,'камянське': (48.5110, 34.6021)
    ,'липова долина': (50.5700, 33.7900)
}

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
    'житомир': 'житом',
    'черкаси': 'черка',
    'чернігів': 'черніг',
    'суми': 'сум',
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
    'днепропетровщина': (48.4500, 34.9830), 'днепропетровщины': (48.4500, 34.9830),
    'чернігівщина': (51.4982, 31.2893), 'чернігівщини': (51.4982, 31.2893),
    'харківщина': (49.9935, 36.2304), 'харківщини': (49.9935, 36.2304)
    , 'дніпропетровська обл.': (48.4500, 34.9830), 'днепропетровская обл.': (48.4500, 34.9830)
    , 'чернігівська обл.': (51.4982, 31.2893), 'черниговская обл.': (51.4982, 31.2893)
    , 'харківська обл.': (49.9935, 36.2304), 'харьковская обл.': (49.9935, 36.2304)
    , 'сумщина': (50.9077, 34.7981), 'сумщини': (50.9077, 34.7981), 'сумщину': (50.9077, 34.7981), 'сумська область': (50.9077, 34.7981), 'сумська обл.': (50.9077, 34.7981), 'сумская обл.': (50.9077, 34.7981)
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
    'сумський': (50.9077, 34.7981), 'сумский': (50.9077, 34.7981),
    'новгород-сіверський': (51.9874, 33.2620), 'новгород-северский': (51.9874, 33.2620),
    'чугуївський': (49.8353, 36.6880), 'чугевский': (49.8353, 36.6880), 'чугевський': (49.8353, 36.6880), 'чугуевский': (49.8353, 36.6880)
    , 'синельниківський': (48.3167, 36.5000), 'синельниковский': (48.3167, 36.5000)
    # Zaporizkyi raion (shifted off exact city center to represent wider district)
    , 'запорізький': (47.9000, 35.2500), 'запорожский': (47.9000, 35.2500)
}

# Active raion (district) air alarms: raion_base -> dict(place, lat, lng, since)
RAION_ALARMS = {}

# Territorial hromada fallback centers (selected). Keys lower-case without word 'територіальна громада'.
HROMADA_FALLBACK = {
    'хотінська': (51.0825, 34.5860),  # Хотінська громада (approx center, Sumy raion near border)
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
            parts = re.split('([-\s])', txt)
            return ''.join(p.capitalize() if i%2==0 else p for i,p in enumerate(parts))
        return cap_tokens(out)
    return n

# -------- Persistent visit tracking (SQLite) to survive redeploys --------
VISITS_DB = os.getenv('VISITS_DB','visits.db')
def _visits_db_conn():
    return sqlite3.connect(VISITS_DB, timeout=5)

def init_visits_db():
    try:
        with _visits_db_conn() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS visits (id TEXT PRIMARY KEY, first_seen REAL, last_seen REAL)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_first ON visits(first_seen)")
    except Exception as e:
        log.warning(f"visits db init failed: {e}")

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

# Initialize DB at import
init_visits_db()
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

def process_message(text, mid, date_str, channel):
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

    def region_enhanced_coords(base_name: str):
        """Resolve coordinates for a settlement name using (in order): static list, settlements dataset,
        region-qualified OpenCage (city + region), then plain OpenCage.
        This enforces the user requirement to bind every settlement to the oblast mentioned in the message text.
        base_name should already be lower-case / normalized.
        """
        if not base_name:
            return None
        name = UA_CITY_NORMALIZE.get(base_name, base_name).strip().lower()
        # Static minimal city coords first
        coord = CITY_COORDS.get(name)
        if coord:
            return coord
        # Settlements dataset
        if SETTLEMENTS_INDEX:
            coord = SETTLEMENTS_INDEX.get(name)
            if coord:
                return coord
        # Region-qualified remote geocode
        if region_hint_global and OPENCAGE_API_KEY:
            try:
                combo = f"{name} {region_hint_global}".replace('  ', ' ').strip()
                combo_c = geocode_opencage(combo)
                if combo_c:
                    return combo_c
            except Exception:
                pass
        # Plain remote geocode fallback
        if OPENCAGE_API_KEY:
            try:
                plain_c = geocode_opencage(name)
                if plain_c:
                    return plain_c
            except Exception:
                pass
        return None
    # ---- Fundraising / donation solicitation filter (do not display on public site) ----
    low_full = original_text.lower()
    if any(k in low_full for k in [
        'монобанк','monobank','mono.bank','privat24','приват24','реквізит','реквизит','донат','donat','iban','paypal','patreon','send.monobank.ua','jar/','банка: http','карта(','карта(monobank)','карта(privat24)'
    ]) or re.search(r'\b\d{16}\b', low_full):
        # Return a suppressed entry (not geo, not shown on map); prevents raw storing duplication
        return [{
            'id': str(mid), 'place': None, 'lat': None, 'lng': None,
            'threat_type': None, 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'list_only': True, 'suppress': True
        }]
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
    # Если сообщение по сути только про тревогу (без упоминаний угроз) — пропускаем (не строим маркер)
    low_orig = original_text.lower()
    if 'повітряна тривога' in low_orig and not any(k in low_orig for k in ['бпла','дрон','шахед','shahed','geran','ракета','missile','iskander','s-300','s300','артил','града','смерч','ураган','mlrs']):
        # Always event-only record (list), user wants always displayed in updateEventList
        place = None
        low = low_orig.lower()
        for name in OBLAST_CENTERS.keys():
            if name in low:
                place = name.title()
                break
        # Keep original text
        return [{
            'id': str(mid), 'place': place, 'lat': None, 'lng': None,
            'threat_type': 'alarm', 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': 'trivoga.png', 'list_only': True
        }]
    # Общий набор ключевых слов угроз
    THREAT_KEYS = ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile','iskander','s-300','s300','каб','артил','града','смерч','ураган','mlrs','avia','авіа','авиа','бомба']
    def has_threat(txt: str):
        l = txt.lower()
        return any(k in l for k in THREAT_KEYS)
    # --- Trajectory phrase pattern: "з дніпропетровщини через харківщину у напрямку полтавщини" ---
    # We map region stems to canonical OBLAST_CENTERS keys (simplistic stem matching).
    lower_full = text.lower()
    if has_threat(lower_full) and ' через ' in lower_full and (' у напрямку ' in lower_full or ' напрямку ' in lower_full or ' в напрямку ' in lower_full):
        # Extract sequence tokens after prepositions з/із/від -> start, через -> middle(s), напрямку -> target
        # Very heuristic; splits by key words.
        try:
            # Normalize spacing
            norm = re.sub(r'\s+', ' ', lower_full)
            # Replace variants
            norm = norm.replace('із ', 'з ').replace('від ', 'з ')
            # Identify segments
            # split at ' через '
            front, after = norm.split(' через ', 1)
            start_token = front.split(' з ')[-1].strip()
            # target part
            target_part = None
            for marker in [' у напрямку ', ' в напрямку ', ' напрямку ']:
                if marker in after:
                    mid_part, target_part = after.split(marker, 1)
                    break
            if target_part:
                mid_token = mid_part.strip().split('.')[0]
                target_token = target_part.strip().split('.')[0]
                def region_center(token:str):
                    for k,(lat,lng) in OBLAST_CENTERS.items():
                        if token.startswith(k.split()[0][:6]) or token in k:
                            return (k, (lat,lng))
                    return None
                seq = []
                for tk in [start_token, mid_token, target_token]:
                    rc = region_center(tk)
                    if rc:
                        # avoid duplicates in order
                        if not seq or seq[-1][0] != rc[0]:
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
    def classify(th: str):
        l = th.lower()
        # Recon / розвід дрони -> use pvo icon (rozved.png) per user request
        if 'розвід' in l or 'развед' in l:
            return 'pvo', 'rozved.png'
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
        # Artillery shelling warning (обстріл / загроза обстрілу) -> use obstril.png
        if 'обстріл' in l or 'обстрел' in l or 'загроза обстрілу' in l or 'угроза обстрела' in l:
            return 'artillery', 'obstril.png'
        # Alarm cancellation (відбій тривоги / отбой тревоги)
        if ('відбій' in l and 'тривог' in l) or ('отбой' in l and 'тревог' in l):
            return 'alarm_cancel', 'vidboi.png'
        # PRIORITY: drones first (частая путаница). Если присутствуют слова шахед/бпла/дрон -> это shahed
        if any(k in l for k in ['shahed','шахед','шахеді','шахедів','geran','герань','дрон','дрони','бпла','uav']):
            return 'shahed', 'shahed.png'
        # KAB (guided bomb) treat as raketa per user request
        if 'каб' in l:
            return 'raketa', 'raketa.png'
        # Missiles / rockets
        if any(k in l for k in ['ракета','ракети','ракетний','ракетная','ракетный','missile','iskander','крылат','крилат','кр ','s-300','s300','КАБ']):
            return 'raketa', 'raketa.png'
        # Aviation
        if any(k in l for k in ['avia','авіа','авиа','літак','самолет','бомба','бомби','бомбаки']):
            return 'avia', 'avia.png'
        # Air defense mention
        if any(k in l for k in ['пво','зеніт','зенит']):
            return 'pvo', 'rozved.png'
        # Artillery / MLRS
        if any(k in l for k in ['артил', 'mlrs','града','градів','смерч','ураган']):
            return 'artillery', 'artillery.png'
        # default assume shahed (консервативно)
        return 'shahed', 'shahed.png'
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
    region_hits = []  # list of (display_name, (lat,lng), snippet)
    # Treat semicolons as separators like newlines for multi-segment parsing
    seg_text = text.replace(';', '\n')
    lines = [ln.strip() for ln in seg_text.split('\n') if ln.strip()]
    for ln in lines:
        ln_low = ln.lower()
        local_regions = []
        for name, coords in OBLAST_CENTERS.items():
            if name in ln_low:
                local_regions.append((name, coords))
        # если в строке более 1— сохраняем все, иначе одну
        for (rn, rc) in local_regions:
            region_hits.append((rn.title(), rc, ln[:180]))
    # Если нашли >=2 региональных маркеров в разных пунктах списка — формируем множественные треки
    if len(region_hits) >= 2:
        # Если присутствуют построчные указания курса на конкретные города ("БпЛА курсом на <місто>") –
        # не возвращаем обобщённые областные маркеры, даём исполниться более детальному парсингу ниже.
        course_line_present = any(
            ('курс' in ln.lower()) and
            ((' на ' in ln.lower()) or (' в ' in ln.lower()) or (' у ' in ln.lower())) and
            (('бпла' in ln.lower()) or ('дрон' in ln.lower()))
            for ln in lines
        )
        if not course_line_present:
            # Пропускаем если нет ни одного упоминания угрозы вообще
            if not has_threat(text):
                return None
            threat_type, icon = classify(text)
            tracks = []
            # deduplicate by name
            seen_names = set()
            for idx, (rname, (lat,lng), snippet) in enumerate(region_hits, 1):
                if rname in seen_names:
                    continue
                seen_names.add(rname)
                tracks.append({
                    'id': f"{mid}_{idx}", 'place': rname, 'lat': lat, 'lng': lng,
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
        # 2) Single settlement search (fallback)
        if SETTLEMENTS_INDEX:
            for name in SETTLEMENTS_ORDERED:
                if name in lower:
                    lat, lng = SETTLEMENTS_INDEX[name]
                    threat_type, icon = classify(text)
                    return [{
                        'id': str(mid), 'place': name.title(), 'lat': lat, 'lng': lng,
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
        parts = [p.strip() for p in re.split(r'/|\\', left_part) if p.strip()]
        found = []
        for p in parts:
            base = UA_CITY_NORMALIZE.get(p, p)
            coords = CITY_COORDS.get(base)
            if not coords and SETTLEMENTS_INDEX:
                coords = SETTLEMENTS_INDEX.get(base)
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

    # Region boundary logic (fallback single or midpoint for exactly two)
    matched_regions = []
    for name, coords in OBLAST_CENTERS.items():
        if name in lower:
            matched_regions.append((name, coords))
    if matched_regions:
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
            if 'північно-захід' in lower_txt: return 'nw'
            if 'південно-захід' in lower_txt: return 'sw'
            if 'північно-схід' in lower_txt: return 'ne'
            if 'південно-схід' in lower_txt: return 'se'
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
                # смещение ~50-70 км в сторону указанного направления
                def offset(lat, lng, code):
                    # базовые дельты в градусах (широта ~111 км, долгота * cos(lat))
                    lat_step = 0.55
                    lng_step = 0.85 / max(0.2, abs(math.cos(math.radians(lat))))
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
                tracks = []
                seen = set()
                for idx,(n1,(lat,lng)) in enumerate(matched_regions,1):
                    base = n1.split()[0].title()
                    if base in seen: continue
                    seen.add(base)
                    tracks.append({
                        'id': f"{mid}_r{idx}", 'place': base, 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_multi_simple', 'count': drone_count
                    })
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
        # Accusative to nominative heuristic for last word only
        parts = w.split(' ')
        if parts:
            last = parts[-1]
            if last.endswith(('у','ю')) and len(last) > 4:
                last = last[:-1] + 'а'
            parts[-1] = last
            w = ' '.join(parts)
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
                    coords = region_enhanced_coords(norm_city)
                    if coords:
                        # Extract line-specific drone count if present (e.g. "4х БпЛА")
                        line_count = None
                        m_lc = re.search(r'(\b\d{1,3})\s*[xх]\s*бпла', line_low)
                        if m_lc:
                            try:
                                line_count = int(m_lc.group(1))
                            except Exception:
                                line_count = None
                        course_matches.append((norm_city.title(), coords, line[:200], line_count))
    if course_matches:
        threat_type, icon = classify(text)
        tracks = []
        seen_places = set()
        for idx,(name,(lat,lng),snippet,line_count) in enumerate(course_matches,1):
            if name in seen_places: continue
            seen_places.add(name)
            tracks.append({
                'id': f"{mid}_c{idx}", 'place': name, 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': snippet[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'course_target', 'count': line_count if line_count else drone_count
            })
        if tracks:
            return tracks
    return None

async def fetch_loop():
    if not client:
        log.warning('Telegram client not configured; skipping fetch loop.')
        return
    async def ensure_connected():
        if client.is_connected():
            return True
        try:
            await client.connect()
            # If bot token provided and not authorized yet, try bot login
            if BOT_TOKEN and not await client.is_user_authorized():
                try:
                    await client.start(bot_token=BOT_TOKEN)
                except Exception as be:
                    log.error(f'Bot start failed: {be}')
            if not await client.is_user_authorized():
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
                        for t in tracks:
                            if t.get('place'):
                                t['place'] = ensure_ua_place(t['place'])
                        all_data.extend(tracks)
                        processed.add(msg.id)
                        fetched += 1
                    else:
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
                continue
            try:
                if not await ensure_connected():
                    # If session invalid we stop loop gracefully
                    if not client.is_connected():
                        log.error('Stopping live loop due to lost/invalid session.')
                        AUTH_STATUS.update({'authorized': False, 'reason': 'lost_session'})
                        return
                async for msg in client.iter_messages(ch, limit=20):
                    if msg.id in processed or not msg.text:
                        continue
                    dt = msg.date.astimezone(tz)
                    if dt < datetime.now(tz) - timedelta(minutes=30):
                        continue
                    tracks = process_message(msg.text, msg.id, dt.strftime('%Y-%m-%d %H:%M:%S'), ch)
                    if tracks:
                        for t in tracks:
                            if t.get('place'):
                                t['place'] = ensure_ua_place(t['place'])
                        new_tracks.extend(tracks)
                        processed.add(msg.id)
                        log.info(f'Added track from {ch} #{msg.id}')
                    else:
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
        if new_tracks:
            all_data.extend(new_tracks)
            save_messages(all_data)
            try:
                broadcast_new(new_tracks)
            except Exception as e:
                log.debug(f'SSE broadcast failed: {e}')
        await asyncio.sleep(60)

def start_fetch_thread():
    global FETCH_THREAD_STARTED
    if not client or FETCH_THREAD_STARTED:
        return
    FETCH_THREAD_STARTED = True
    loop = asyncio.new_event_loop()
    def runner():
        if FETCH_START_DELAY > 0:
            log.info(f'Delaying Telegram fetch start for {FETCH_START_DELAY}s (FETCH_START_DELAY).')
            time.sleep(FETCH_START_DELAY)
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(fetch_loop())
        except AuthKeyDuplicatedError:
            AUTH_STATUS.update({'authorized': False, 'reason': 'authkey_duplicated_runner'})
            log.error('Fetch loop stopped: duplicated auth key.')
        except Exception as e:
            AUTH_STATUS.update({'authorized': False, 'reason': f'crash:{e.__class__.__name__}'})
            log.error(f'Fetch loop crashed: {e}')
        finally:
            FETCH_THREAD_STARTED = False
    threading.Thread(target=runner, daemon=True).start()

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
    # Leaflet version of frontend no longer needs Google Maps key
    return render_template('index.html')

@app.route('/data')
def data():
    # Ignore user-provided timeRange; use global configured MONITOR_PERIOD_MINUTES
    time_range = MONITOR_PERIOD_MINUTES
    messages = load_messages()
    tz = pytz.timezone('Europe/Kyiv')
    now = datetime.now(tz).replace(tzinfo=None)
    min_time = now - timedelta(minutes=time_range)
    hidden = set(load_hidden())
    out = []  # geo tracks
    events = []  # list-only (alarms, cancellations, other non-geo informational)
    for m in messages:
        try:
            dt = datetime.strptime(m.get('date',''), '%Y-%m-%d %H:%M:%S')
        except Exception:
            continue
        if dt >= min_time:
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
    resp = jsonify({'tracks': out, 'events': events, 'all_sources': CHANNELS, 'trajectories': []})
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp

@app.route('/channels')
def list_channels():
    return jsonify({'channels': CHANNELS, 'invalid': list(INVALID_CHANNELS)})

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

@app.route('/health')
def health():
    # Basic stats + prune visitors
    now = time.time()
    with ACTIVE_LOCK:
        for vid, meta in list(ACTIVE_VISITORS.items()):
            ts = meta if isinstance(meta,(int,float)) else meta.get('ts',0)
            if now - ts > ACTIVE_TTL:
                del ACTIVE_VISITORS[vid]
        visitors = len(ACTIVE_VISITORS)
    return jsonify({'status':'ok','messages':len(load_messages()), 'auth': AUTH_STATUS, 'visitors': visitors})

@app.route('/presence', methods=['POST'])
def presence():
    data = request.get_json(silent=True) or {}
    vid = data.get('id')
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
    with ACTIVE_LOCK:
        prev = ACTIVE_VISITORS.get(vid) if isinstance(ACTIVE_VISITORS.get(vid), dict) else {}
        ACTIVE_VISITORS[vid] = {'ts': now, 'ip': remote_ip, 'ua': prev.get('ua') or ua}
        # prune
        for k, meta in list(ACTIVE_VISITORS.items()):
            ts = meta if isinstance(meta,(int,float)) else meta.get('ts',0)
            if now - ts > ACTIVE_TTL:
                del ACTIVE_VISITORS[k]
        count = len(ACTIVE_VISITORS)
    return jsonify({'status':'ok','visitors': count})

@app.route('/raion_alarms')
def raion_alarms():
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
    with ACTIVE_LOCK:
        prev = ACTIVE_VISITORS.get(vid) if isinstance(ACTIVE_VISITORS.get(vid), dict) else {}
        ACTIVE_VISITORS[vid] = {'ts': now, 'ip': remote_ip, 'ua': prev.get('ua') or ua}
        stale = [k for k,v in ACTIVE_VISITORS.items() if now - (v if isinstance(v,(int,float)) else v.get('ts',0)) > ACTIVE_TTL]
        for k in stale: del ACTIVE_VISITORS[k]
        count = len(ACTIVE_VISITORS)
    return jsonify({'status':'ok','visitors':count})

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

@app.route('/admin')
def admin_panel():
    if not _require_secret(request):
        return Response('Forbidden', status=403)
    now = time.time()
    with ACTIVE_LOCK:
        visitors = []
        for vid, meta in ACTIVE_VISITORS.items():
            if isinstance(meta,(int,float)):
                age = int(now - meta)
                visitors.append({'id':vid,'ip':'','age':age,'age_fmt':_fmt_age(age),'ua':'','ua_short':''})
            else:
                age = int(now - meta.get('ts',0))
                ua = meta.get('ua','')
                visitors.append({
                    'id':vid,
                    'ip':meta.get('ip',''),
                    'age':age,
                    'age_fmt':_fmt_age(age),
                    'ua': ua,
                    'ua_short': _ua_label(ua)
                })
    blocked = load_blocked()
    # Load raw (pending geo) messages
    all_msgs = load_messages()
    raw_msgs = [m for m in reversed(all_msgs) if m.get('pending_geo')][:100]  # latest 100
    # Collect last N geo markers (exclude pending geo) for hide management
    recent_markers = [m for m in reversed(all_msgs) if m.get('lat') and m.get('lng') and not m.get('pending_geo')][:120]
    # --- Visit stats aggregation ---
    # Prefer rolling sets for stability across deploy
    daily_unique, week_unique = _recent_counts()
    if daily_unique is None:
        daily_unique, week_unique = sql_unique_counts()
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
        hidden_markers=parsed_hidden
    )

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
        return jsonify({'status':'ok','monitor_period':MONITOR_PERIOD_MINUTES})
    except Exception as e:
        return jsonify({'status':'error','error':str(e)}), 400

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

UA_CITIES = [
    'київ','харків','одеса','одесса','дніпро','дніпропетровськ','львів','запоріжжя','запорожье','вінниця','миколаїв','николаев','маріуполь','полтава','чернігів','чернигов','черкаси','житомир','суми','хмельницький','чернівці','рівне','івано-франківськ','луцьк','тернопіль','ужгород','кропивницький','кіровоград','кременчук','краматорськ','біла церква','мелітополь','бердянськ','павлоград'
]
UA_CITY_NORMALIZE = {
    'одесса':'одеса',
    'запорожье':'запоріжжя',
    'дніпропетровськ':'дніпро',
    'кировоград':'кропивницький',
    'кіровоград':'кропивницький',
    'николаев':'миколаїв',
    'чернигов':'чернігів'
}

# Static fallback coordinates (approximate city centers) to avoid relying solely on OpenCage.
# Minimal fallback city coords (will be superseded if full settlements file present)
CITY_COORDS = {
    'київ': (50.4501, 30.5234),
    'харків': (49.9935, 36.2304),
    'одеса': (46.4825, 30.7233),
    'дніпро': (48.4647, 35.0462),
    'львів': (49.8397, 24.0297),
    'запоріжжя': (47.8388, 35.1396),
    'вінниця': (49.2331, 28.4682),
    'миколаїв': (46.9750, 31.9946),
    'маріуполь': (47.0971, 37.5434),
    'полтава': (49.5883, 34.5514),
    'чернігів': (51.4982, 31.2893),
    'черкаси': (49.4444, 32.0598),
    'житомир': (50.2547, 28.6587),
    'суми': (50.9077, 34.7981),
    'хмельницький': (49.4229, 26.9871),
    'чернівці': (48.2921, 25.9358),
    'рівне': (50.6199, 26.2516),
    'івано-франківськ': (48.9226, 24.7111),
    'луцьк': (50.7472, 25.3254),
    'тернопіль': (49.5535, 25.5948),
    'ужгород': (48.6208, 22.2879),
    'кропивницький': (48.5079, 32.2623),
    'кременчук': (49.0670, 33.4204),
    'краматорськ': (48.7389, 37.5848),
    'біла церква': (49.7950, 30.1310),
    'мелітополь': (46.8489, 35.3650),
    'бердянськ': (46.7553, 36.7885)
    ,'павлоград': (48.5350, 35.8700)
}

OBLAST_CENTERS = {
    'донеччина': (48.0433, 37.7974), 'донеччини': (48.0433, 37.7974), 'донецька область': (48.0433, 37.7974),
    'дніпропетровщина': (48.4500, 34.9830), 'дніпропетровщини': (48.4500, 34.9830), 'дніпропетровська область': (48.4500, 34.9830),
    'днепропетровщина': (48.4500, 34.9830), 'днепропетровщины': (48.4500, 34.9830),
    'чернігівщина': (51.4982, 31.2893), 'чернігівщини': (51.4982, 31.2893),
    'харківщина': (49.9935, 36.2304), 'харківщини': (49.9935, 36.2304)
    , 'дніпропетровська обл.': (48.4500, 34.9830), 'днепропетровская обл.': (48.4500, 34.9830)
    , 'чернігівська обл.': (51.4982, 31.2893), 'черниговская обл.': (51.4982, 31.2893)
    , 'харківська обл.': (49.9935, 36.2304), 'харьковская обл.': (49.9935, 36.2304)
    , 'сумщина': (50.9077, 34.7981), 'сумщини': (50.9077, 34.7981), 'сумська область': (50.9077, 34.7981), 'сумська обл.': (50.9077, 34.7981), 'сумская обл.': (50.9077, 34.7981)
    , 'полтавщина': (49.5883, 34.5514), 'полтавщини': (49.5883, 34.5514), 'полтавська обл.': (49.5883, 34.5514), 'полтавська область': (49.5883, 34.5514)
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
    'сумський': (50.9077, 34.7981), 'сумский': (50.9077, 34.7981),
    'новгород-сіверський': (51.9874, 33.2620), 'новгород-северский': (51.9874, 33.2620),
    'чугуївський': (49.8353, 36.6880), 'чугевский': (49.8353, 36.6880), 'чугевський': (49.8353, 36.6880), 'чугуевский': (49.8353, 36.6880)
}

SETTLEMENTS_FILE = os.getenv('SETTLEMENTS_FILE', 'settlements_ua.json')
SETTLEMENTS_INDEX = {}
SETTLEMENTS_ORDERED = []

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