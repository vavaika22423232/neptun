
# ---------------- Admin & blocking endpoints -----------------

# ...existing code...

import os, re, json, asyncio, threading, logging, pytz, time, subprocess, queue, sys, platform, traceback, uuid
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

def log_alarm_event(level:str, name:str, event:str, ts:float|None=None):
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
NEG_GEOCODE_FILE = 'negative_geocode_cache.json'
NEG_GEOCODE_TTL = 60 * 60 * 24 * 3  # 3 days for 'not found' entries
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
    # Мала дівиця
    'малу дівицю':'мала дівиця','мала дівицю':'мала дівиця',
    # Additional safety normalizations
    'олишівку':'олишівка','згурівку':'згурівка','ставищею':'ставище','кегичівку':'кегичівка','кегичевку':'кегичівка',
    'старому салтову':'старий салтів','старому салтові':'старий салтів','карлівку':'карлівка','магдалинівку':'магдалинівка',
    'балаклію':'балаклія','білу церкву':'біла церква','баришівку':'баришівка','сквиру':'сквира','сосницю':'сосниця',
    'васильківку':'васильківка','понорницю':'понорниця','куликівку':'куликівка','терни':'терни',
    'шостку':'шостка','березну':'березна','зачепилівку':'зачепилівка','нову водолагу':'нова водолага',
    'убни':'лубни','олми':'холми','летичів':'летичів','летичев':'летичів','летичеве':'летичів','деражню':'деражня',
    'деражне':'деражня','деражні':'деражня','корюківку':'корюківка','борзну':'борзна','жмеринку':'жмеринка','лосинівку':'лосинівка',
    'ніжину':'ніжин','межову':'межова','святогірську':'святогірськ'
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

def ensure_city_coords(name: str):
    """Return (lat,lng,approx_bool) for settlement, performing lazy geocoding.
    approx_bool True means we used oblast center fallback (low precision)."""
    if not name:
        return None
    n = name.strip().lower()
    if n in CITY_COORDS:
        lat,lng = CITY_COORDS[n]; return (lat,lng,False)
    if 'SETTLEMENTS_INDEX' in globals() and n in (globals().get('SETTLEMENTS_INDEX') or {}):
        lat,lng = globals()['SETTLEMENTS_INDEX'][n]; return (lat,lng,False)
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

# Consolidated static fallback coordinates
CITY_COORDS = {
        # Core cities
        'київ': (50.4501, 30.5234), 'харків': (49.9935, 36.2304), 'одеса': (46.4825, 30.7233), 'дніпро': (48.4647, 35.0462),
        'львів': (49.8397, 24.0297), 'запоріжжя': (47.8388, 35.1396), 'вінниця': (49.2331, 28.4682), 'миколаїв': (46.9750, 31.9946),
        'маріуполь': (47.0971, 37.5434), 'полтава': (49.5883, 34.5514), 'чернігів': (51.4982, 31.2893), 'черкаси': (49.4444, 32.0598),
        'житомир': (50.2547, 28.6587), 'суми': (50.9077, 34.7981), 'хмельницький': (49.4229, 26.9871), 'чернівці': (48.2921, 25.9358),
    'малин': (50.7726, 29.2360), 'малині': (50.7726, 29.2360), 'малину': (50.7726, 29.2360), 'малином': (50.7726, 29.2360),
    # Added per user report (обстріл alert should map): Костянтинівка (Donetsk Obl.)
    'костянтинівка': (48.5277, 37.7050),
    # Mezhova (Дніпропетровська обл.) to avoid fallback to Dnipro
    'межова': (48.2583, 36.7363),
    # Sviatohirsk (Святогірськ) Donetsk Oblast
    'святогірськ': (49.0339, 37.5663),
    # Antonivka (Kherson urban-type settlement, user report for UAV threat)
    'антонівка': (46.6925, 32.7186),
    # Baturyn (Chernihiv Obl.) for directional course reports
    'батурин': (51.3450, 32.8761),
        'рівне': (50.6199, 26.2516), 'івано-франківськ': (48.9226, 24.7111), 'луцьк': (50.7472, 25.3254), 'тернопіль': (49.5535, 25.5948),
        'ужгород': (48.6208, 22.2879), 'кропивницький': (48.5079, 32.2623), 'кременчук': (49.0670, 33.4204), 'краматорськ': (48.7389, 37.5848),
        'мелітополь': (46.8489, 35.3650), 'бердянськ': (46.7553, 36.7885), 'павлоград': (48.5350, 35.8700), 'нікополь': (47.5667, 34.4061),
        'марганець': (47.6433, 34.6289), 'херсон': (46.6350, 32.6169),
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
        'шаргород': (48.7333, 28.0833), 'бірки': (49.7517, 36.1025), 'златопіль': (48.3640, 38.1500), 'балаклія': (49.4627, 36.8586),
        'берестин': (50.2000, 35.0000), 'старий салтів': (50.0847, 36.7424), 'борки': (49.9380, 36.1260), 'кролевець': (51.5481, 33.3847),
    'терни': (50.9070, 34.0130), 'понорниця': (51.8033, 32.5333), 'куликівка': (51.3520, 31.6480),
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
        'узин': (49.8216, 30.4567), 'гончарівське': (51.6272, 31.3192), 'голованівськ': (48.3772, 30.5322), 'новоукраїнка': (48.3122, 31.5272),
        'тульчин': (48.6783, 28.8486), 'бровари': (50.5110, 30.7909), 'канів': (49.7517, 31.4717), 'миронівка': (49.6631, 31.0100),
        'борова': (49.3742, 36.4892), 'буринь': (51.2000, 33.8500), 'конотоп': (51.2417, 33.2022), 'остер': (50.9481, 30.8831),
        'плавні': (49.0123, 33.6450), 'голованівський район': (48.3772, 30.5322), 'новоукраїнський район': (48.3122, 31.5272),
        'безлюдівка': (49.8872, 36.2731), 'рогань': (49.9342, 36.4942), 'савинці(харківщина)': (49.6272, 36.9781),
        'українка': (50.1447, 30.7381), 'царичанка': (48.9767, 34.3772), 'ріпки': (51.8122, 31.0817), 'михайло-коцюбинське': (51.5833, 31.1167),
        'макошине': (51.6275, 32.2731), 'парафіївка': (50.9833, 32.2833), 'дубовʼязівка': (51.1833, 33.7833), 'боромля': (50.7500, 34.9833),
    # Newly added (missing in earlier dictionary lookups reported by user)
    'городня': (51.8892, 31.6011),
        'жукин': (50.7800, 30.6820), 'велика димерка': (50.8140, 30.8080), 'велику димерку': (50.8140, 30.8080), 'вишгород': (50.5840, 30.4890),
        'ржищів': (49.9719, 31.0500), 'вишеньки': (50.2987, 30.6445), 'жуляни': (50.4017, 30.4519), 'троєщина': (50.5130, 30.6030),
        'троєщину': (50.5130, 30.6030), 'конча-заспа': (50.2650, 30.5760), 'любар': (50.0500, 27.7500), 'старий остропіль': (49.6503, 27.2291),
        'згурівка': (50.4950, 31.7780), 'мала дівиця': (50.8240, 32.4700), 'яготин': (50.2360, 31.7700), 'ставище': (49.3958, 30.1875),
        'березань': (50.3085, 31.4576), 'бортничі': (50.3915, 30.6695), 'старокостянтинів': (49.7574, 27.2039), 'адампіль': (49.6500, 27.3000),
        # Additional single-city early parser support
        'покровське': (48.1180, 36.2470), 'петропавлівка': (48.5000, 36.4500), 'шахтарське': (47.9500, 36.0500), 'миколаївка': (49.1667, 36.2333),
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
    'сумський': (50.9077, 34.7981), 'сумский': (50.9077, 34.7981),
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

# Specific settlement fallback for mis-localized parsing (e.g., 'Кіпті' message wrongly geocoded to Lviv oblast)
SETTLEMENT_FALLBACK = {
    'кіпті': (51.0925, 31.3190),  # Kiptsi (Chernihiv oblast, along M01/E95 near junction). Approx center.
    'кипти': (51.0925, 31.3190),  # Russian / simplified spelling
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
                "CREATE INDEX IF NOT EXISTS idx_comments_reply ON comments(reply_to)"
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
                rows.append(d)
    except Exception as e:
        log.warning(f"load_recent_comments failed: {e}")
    return list(reversed(rows))  # reverse so oldest of the slice first

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

def process_message(text, mid, date_str, channel):
    # Strip embedded links (Markdown [text](url) or raw URLs) while keeping core message text.
    # Requested: if message contains links, remove them but keep the rest.
    try:
        import re as _re_strip
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
                        return []
            # NEW suppression: reconnaissance-only notes ("дорозвідка по БпЛА") should not produce a marker
            # Pattern triggers if word 'дорозвідк' present together with UAV terms but no other threat verbs
            if 'дорозвідк' in lt and any(k in lt for k in ['бпла','shahed','шахед','дрон']):
                # Avoid suppressing if explosions or launches also present
                if not any(k in lt for k in ['вибух','удар','пуск','прил','обстріл','обстрел','зліт','злет']):
                    return []
    except Exception:
        pass
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
                        enriched = ensure_city_coords(norm)
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
        if ('курс' in lorig or '➡' in lorig or '→' in lorig or 'напрям' in lorig) and ('бпла' in lorig or 'дрон' in lorig or 'груп' in lorig):
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
                    # Extra guard: if a well-known large city (e.g. дніпро, харків, київ) appears ONLY because it's substring of region
                    # we still treat as region directional, not city marker
                    # But if message contains multiple explicit directional part-of-region clauses ("на сході <області>" ... "на сході <області>")
                    # then we want to produce separate segment markers instead of a single list-only event.
                    import re as _re_dd
                    dir_clause_count = len(_re_dd.findall(r'на\s+(?:північ|півден|схід|заход|північно|південно)[^\.]{0,40}?(?:щина|щини|щину)', lorig))
                    if dir_clause_count < 2:
                        return [{
                            'id': str(mid), 'text': text[:600], 'date': date_str, 'channel': channel,
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
                    'threat_type': threat, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'city_dash_uav'
                }]
        # NEW: pattern "БпЛА на <city>" or "бпла на <city>" -> marker at city
        m_on = _re_rel.search(r"бпла\s+на\s+([a-zа-яіїєґ'ʼ’`\-]{3,40})", low_txt)
        if m_on:
            rc = m_on.group(1)
            rc = rc.replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
            base = UA_CITY_NORMALIZE.get(rc, rc)
            coords = CITY_COORDS.get(base)
            if not coords and 'SETTLEMENTS_INDEX' in globals():
                coords = (globals().get('SETTLEMENTS_INDEX') or {}).get(base)
            if coords:
                lat,lng = coords
                return [{
                    'id': str(mid), 'place': base.title(), 'lat': lat, 'lng': lng,
                    'threat_type': 'shahed', 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': 'shahed.png', 'source_match': 'uav_on_city'
                }]
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
    # Course towards single city ("курс(ом) на Батурин") -> place marker at that city
    try:
        import re as _re_course
        low_txt2 = text.lower()
        m_course = _re_course.search(r'курс(?:ом)?\s+на\s+([a-zа-яіїєґ\'ʼ’`\-]{3,40})', low_txt2)
        if m_course:
            raw_city = m_course.group(1)
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
                    'marker_icon': icon, 'source_match': 'course_to_city'
                }]
    except Exception:
        pass
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
    cleaned_for_multiline = []
    import re as _re_clean
    donation_keys = ['монобанк','send.monobank','patreon','donat','донат','підтримати канал','підтримати','напрямок ракет','napramok']
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
    for ln in lines:
        # Если строка — это заголовок области (например, "Сумщина:")
        # Заголовок области: строка, заканчивающаяся на ':' (возможен пробел перед / после) или формой '<область>:' с лишними пробелами
        import re
        if re.match(r'^[A-Za-zА-Яа-яЇїІіЄєҐґ\-ʼ`\s]+:\s*$', ln):
            oblast_hdr = ln.split(':')[0].strip().lower()
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
            continue
        try:
            log.info(f"MLINE_LINE oblast={oblast_hdr} raw='{ln}'")
        except Exception:
            pass
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
                    'threat_type': 'rszv', 'text': ln[:500], 'date': date_str, 'channel': channel,
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
        m = re.search(r'(\d+)[xх]?\s*бпла.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
        if m:
            count = int(m.group(1))
            city = m.group(2)
        else:
            # Дополнительно поддерживаем строки вида "7х БпЛА повз <місто> ..." или "БпЛА повз <місто>"
            m2 = re.search(r'бпла.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
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
                    if per_count > 1:
                        label += f" ({per_count})"
                    if oblast_hdr and oblast_hdr not in label.lower():
                        label += f" [{oblast_hdr.title()}]"
                    multi_city_tracks.append({
                        'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                        'threat_type': 'shahed', 'text': ln[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': 'shahed.png', 'source_match': 'multiline_oblast_city_shahed', 'count': per_count
                    })
                continue
        if city:
            base = normalize_city_name(city)
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
            coords = CITY_COORDS.get(base)
            if not coords and SETTLEMENTS_INDEX:
                coords = SETTLEMENTS_INDEX.get(base)
            # coords lookup done
            # Если не найдено — пробуем добавить область к названию
            if not coords and oblast_hdr:
                combo = f"{base} {oblast_hdr}"
                coords = CITY_COORDS.get(combo)
                if not coords and SETTLEMENTS_INDEX:
                    coords = SETTLEMENTS_INDEX.get(combo)
            if not coords:
                coords = ensure_city_coords(base)
            if coords:
                lat, lng = coords
                threat_type, icon = 'shahed', 'shahed.png'
                label = UA_CITY_NORMALIZE.get(base, base).title()
                if count > 1:
                    label += f" ({count})"
                if oblast_hdr and oblast_hdr not in label.lower():
                    label += f" [{oblast_hdr.title()}]"
                multi_city_tracks.append({
                    'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'multiline_oblast_city', 'count': count
                })
    if multi_city_tracks:
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
        for idx, (city, (lat, lng)) in enumerate(found_cities, 1):
            multi_city_tracks.append({
                'id': f"{mid}_mc{idx}", 'place': city.title(), 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'multi_city_auto'
            })
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
        'монобанк','monobank','mono.bank','privat24','приват24','реквізит','реквизит','донат','donat','iban','paypal','patreon','send.monobank.ua','jar/','банка: http','карта(','карта(monobank)','карта(privat24)'
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
            # Remove lines containing donation keywords to salvage threat content
            kept_lines = []
            for ln in original_text.splitlines():
                ll = ln.lower()
                if any(k in ll for k in DONATION_KEYS) or re.search(r'\b\d{16}\b', ll):
                    continue
                kept_lines.append(ln)
            text = '\n'.join(kept_lines)
            original_text = text  # treat stripped version as canonical for later stages
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
    THREAT_KEYS = ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile','iskander','s-300','s300','каб','артил','града','смерч','ураган','mlrs','avia','авіа','авиа','бомба','високошвидкісн']
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
    def classify(th: str):
        l = th.lower()
        # Recon / розвід дрони -> use pvo icon (rozved.png) per user request
        if 'розвід' in l or 'розвідуваль' in l or 'развед' in l:
            return 'pvo', 'rozved.png'
        # Launch site detections for Shahed / UAV launches ("пуски" + origin phrases). User wants pusk.png marker.
        if ('пуск' in l or 'пуски' in l) and (any(k in l for k in ['shahed','шахед','шахеді','шахедів','бпла','uav','дрон']) or ('аеродром' in l) or ('аэродром' in l)):
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
        # High-speed targets explicit alert (custom icon)
        if 'високошвидкісн' in l:
            return 'rszv', 'rszv.png'
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
    # North-east tactical aviation activity (approx between Svatove & Kupiansk) -> avia marker
    if ('тактичн' in se_phrase or 'авіаці' in se_phrase or 'авиац' in se_phrase) and (
        'північно-східн' in se_phrase or 'північно східн' in se_phrase or 'северо-восточ' in se_phrase or 'північного-сходу' in se_phrase
    ):
        # Approximate midpoint NE front (lat near 49.7, lng 37.9)
        lat, lng = 49.7, 37.9
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
        'чернігівщині': 'чернігівщина'
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
    # Если нашли >=2 региональных маркеров в разных пунктах списка — формируем множественные треки
    if len(region_hits) >= 2 and not launch_mode:
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
        original_text_norm = re.sub(r'(?i)(\b[А-Яа-яЇїІіЄєҐґ\-]{3,}(?:щина|область|обл\.)):(?!\s*\n)', r'\1:\n', original_text)
        lines_with_region = []
        current_region_hdr = None
        for raw_ln in original_text_norm.splitlines():
            ln_stripped = raw_ln.strip()
            if not ln_stripped:
                continue
            low_ln = ln_stripped.lower()
            if low_ln.endswith(':'):
                base_hdr = low_ln[:-1]
                if base_hdr in OBLAST_CENTERS:
                    current_region_hdr = base_hdr
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
        pat_count_course = re.compile(r'^(\d+)\s*[xх]?\s*бпла.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-’ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_course = re.compile(r'бпла.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-’ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
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
            t = t.replace('’',"'")
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
            count = None; city = None
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
                continue
            multi_norm = _resolve_city_candidate(city)
            base = norm_city_token(multi_norm)
            coords = CITY_COORDS.get(base) or (SETTLEMENTS_INDEX.get(base) if SETTLEMENTS_INDEX else None)
            if not coords:
                try:
                    coords = region_enhanced_coords(base, region_hint_override=region_hdr)
                except Exception:
                    coords = None
            if not coords:
                continue
            if base not in CITY_COORDS:
                CITY_COORDS[base] = coords
            lat, lng = coords
            threat_type, icon = classify(text)
            label = base.title()
            if count:
                label += f" ({count})"
            if region_hdr and region_hdr not in label.lower():
                label += f" [{region_hdr.title()}]"
            course_tracks.append({
                'id': f"{mid}_c{len(course_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'course_city', 'count': count or 1
            })
        if course_tracks:
            return course_tracks

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
                    if re.search(r'(щина|область)$', norm_city):
                        log.debug(f'skip course_target oblast_only={norm_city} mid={mid}')
                        continue
                    coords = region_enhanced_coords(norm_city)
                    if not coords:
                        log.debug(f'course_target_lookup miss city={norm_city} mid={mid} line={line.strip()[:120]!r} region_hint={region_hint_global}')
                        coords = ensure_city_coords(norm_city)
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

@app.route('/active_alarms')
def active_alarms_endpoint():
    """Return current active oblast & raion air alarms (for polygon styling)."""
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
            # Fallback reparse: if message lacks geo but contains course pattern, try to derive markers now
            if (not m.get('lat')) and (not m.get('lng')) and not m.get('list_only'):
                txt_low = (m.get('text') or '').lower()
                if 'бпла' in txt_low and 'курс' in txt_low and ' на ' in txt_low:
                    try:
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
                            continue  # don't treat original raw message further
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
    resp = jsonify({'tracks': out, 'events': events, 'all_sources': CHANNELS, 'trajectories': []})
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp

@app.route('/channels')
def list_channels():
    return jsonify({'channels': CHANNELS, 'invalid': list(INVALID_CHANNELS)})

@app.route('/locate')
def locate_place():
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
    neg_geocode=list(_load_neg_geocode_cache().items())[:150]
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
    , 'хмельниччина': (49.4229, 26.9871), 'хмельниччини': (49.4229, 26.9871), 'хмельницька обл.': (49.4229, 26.9871), 'хмельницька область': (49.4229, 26.9871)
}


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