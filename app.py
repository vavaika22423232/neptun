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
CHANNELS = os.getenv('TELEGRAM_CHANNELS', 'UkraineAlarmSignal,war_monitor,kpszsu,napramok,kudy_letyt,AerisRimor').split(',')
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
client = None
session_str = os.getenv('TELEGRAM_SESSION')  # Telethon string session (recommended for Render)
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # optional bot token fallback
AUTH_SECRET = os.getenv('AUTH_SECRET')  # simple shared secret to protect /auth endpoints
FETCH_THREAD_STARTED = False
AUTH_STATUS = {'authorized': False, 'reason': 'init'}
SUBSCRIBERS = set()  # queues for SSE clients
INIT_ONCE = False  # guard to ensure background startup once
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

# Simplified message processor placeholder
import math

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
    ,'ніжин': (51.0480, 31.8860)
    ,'сосниця': (51.5236, 32.4953)
    ,'олишівка': (51.1042, 31.6817)
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
}

# Район (district) fallback centers (можно расширять). Ключи в нижнем регистре без слова 'район'.
RAION_FALLBACK = {
    'покровський': (48.2767, 37.1763),  # Покровськ (Донецька)
    'покровский': (48.2767, 37.1763),
    'павлоградський': (48.5350, 35.8700),  # Павлоград
    'павлоградский': (48.5350, 35.8700),
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

def process_message(text, mid, date_str, channel):
    """Extract coordinates or try simple city geocoding (lightweight)."""
    original_text = text
    # Санитизация: убираем точную фразу "Повітряна тривога" (реквест пользователя)
    text = text.replace('Повітряна тривога', '').replace('повітряна тривога','').strip()
    # Убираем markdown * _ ` и базовые эмодзи-иконки в начале строк
    text = re.sub(r'[\*`_]+', '', text)
    # Удаляем ведущие эмодзи/иконки перед словами
    text = re.sub(r'^[\W_]+', '', text)
    # Если сообщение по сути только про тревогу (без упоминаний угроз) — пропускаем (не строим маркер)
    low_orig = original_text.lower()
    if 'повітряна тривога' in low_orig and not any(k in low_orig for k in ['бпла','дрон','шахед','shahed','geran','ракета','missile','iskander','s-300','s300','артил','града','смерч','ураган','mlrs']):
        return None
    # Общий набор ключевых слов угроз
    THREAT_KEYS = ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile','iskander','s-300','s300','каб','артил','града','смерч','ураган','mlrs','avia','авіа','авиа','бомба']
    def has_threat(txt: str):
        l = txt.lower()
        return any(k in l for k in THREAT_KEYS)
    # direct coordinates pattern
    def classify(th: str):
        l = th.lower()
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
    lower = text.lower()

    # --- Pattern: City (Oblast ...) e.g. "Павлоград (Дніпропетровська обл.)" ---
    bracket_city = re.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})\s*\(([^)]+)\)', text)
    if bracket_city:
        raw_city = bracket_city.group(1).strip().lower()
        raw_inside = bracket_city.group(2).lower()
        # Не интерпретировать 'район' как город
        if raw_city != 'район':
            norm_city = UA_CITY_NORMALIZE.get(raw_city, raw_city)
            coords = CITY_COORDS.get(norm_city)
            if not coords and OPENCAGE_API_KEY:
                coords = geocode_opencage(norm_city)
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
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
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

    # --- Settlement matching using external dataset (if provided) (single first match) ---
    if SETTLEMENTS_INDEX and not region_hits:
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
    # одиночное 'район'
    raion_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё\-]{4,})\s+район', re.IGNORECASE)
    for m_r in raion_pattern.finditer(text):
        base = norm_raion(m_r.group(1))
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
            tracks.append({
                'id': f"{mid}_d{idx}", 'place': title, 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'raion'
            })
        if tracks:
            log.debug(f"RAION_MATCH mid={mid} -> {[t['place'] for t in tracks]}")
            return tracks

    # Region boundary logic (fallback single or midpoint for exactly two)
    matched_regions = []
    for name, coords in OBLAST_CENTERS.items():
        if name in lower:
            matched_regions.append((name, coords))
    if matched_regions:
        # Если только области упомянуты и нет ключей угроз, пропускаем
        if not has_threat(text):
            return None
        # --- Направления внутри области (північно-західний / південно-західний и т.п.) ---
        def detect_direction(lower_txt: str):
            # порядок важен: сначала составные
            if 'північно-захід' in lower_txt: return 'nw'
            if 'південно-захід' in lower_txt: return 'sw'
            if 'північно-схід' in lower_txt: return 'ne'
            if 'південно-схід' in lower_txt: return 'se'
            # одиночные стороны света (избегаем ложных с составными за счёт предыдущих проверок)
            # "північ" north, "південь" south, "схід" east, "захід" west
            # избегаем совпадения внутри составных уже обработанных
            if ' північ' in lower_txt or lower_txt.startswith('північ'):
                return 'n'
            if ' південь' in lower_txt or lower_txt.startswith('південь'):
                return 's'
            if ' схід' in lower_txt or lower_txt.startswith('схід'):
                return 'e'
            if ' захід' in lower_txt or lower_txt.startswith('захід'):
                return 'w'
            return None
        direction_code = None
        if len(matched_regions) == 1 and not raion_matches:
            direction_code = detect_direction(lower)
            if direction_code:
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
                    'marker_icon': icon, 'source_match': 'region_direction'
                }]
            # если нет направления — продолжаем анализ (ищем конкретные цели типа "курс на <місто>")
        if len(matched_regions) == 2 and any(w in lower for w in ['межі','межу','межа','между','границі','граница']):
            (n1,(a1,b1)), (n2,(a2,b2)) = matched_regions
            lat = (a1+a2)/2; lng = (b1+b2)/2
            threat_type, icon = classify(text)
            return [{
                'id': str(mid), 'place': f"Межа {n1.split()[0].title()}/{n2.split()[0].title()}", 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon
            }]
        else:
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
                    'marker_icon': icon, 'source_match': 'region_multi_simple'
                })
            if tracks:
                return tracks
    for city in UA_CITIES:
        if city in lower:
            norm = UA_CITY_NORMALIZE.get(city, city)
            coords = geocode_opencage(norm)
            if not coords:
                coords = CITY_COORDS.get(norm)
            if coords:
                lat, lng = coords
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': norm.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon
                }]
            # if city found but no coords even in fallback, continue scanning others (no break)
    # --- Drone course target parsing (e.g. "БпЛА курсом на Ніжин") ---
    def _normalize_course_city(w: str):
        w = w.strip('.,:;"'"'"" ).-" ).lower()
        w = re.sub(r'[^a-zа-яїієґё\-]', '', w)
        # простая нормализация украинских женских окончаний винительного падежа
        if w.endswith(('у','ю')) and len(w) > 4:
            w = w[:-1] + 'а'
        return w
    course_matches = []
    # Ищем каждую строку с шаблоном
    for line in text.split('\n'):
        line_low = line.lower()
        if 'бпла' in line_low and 'курс' in line_low and (' на ' in line_low or ' в ' in line_low or ' у ' in line_low):
            m = re.search(r'курс(?:ом)?\s+(?:на|в|у)\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', line, flags=re.IGNORECASE)
            if m:
                raw_city = m.group(1)
                norm_city = _normalize_course_city(raw_city)
                if norm_city:
                    # пытаемся найти координаты в приоритетном порядке
                    coords = CITY_COORDS.get(norm_city)
                    if not coords and SETTLEMENTS_INDEX:
                        coords = SETTLEMENTS_INDEX.get(norm_city)
                    if not coords and OPENCAGE_API_KEY:
                        try:
                            coords = geocode_opencage(norm_city)
                        except Exception:
                            coords = None
                    if coords:
                        course_matches.append((norm_city.title(), coords, line[:200]))
    if course_matches:
        threat_type, icon = classify(text)
        tracks = []
        seen_places = set()
        for idx,(name,(lat,lng),snippet) in enumerate(course_matches,1):
            if name in seen_places: continue
            seen_places.add(name)
            tracks.append({
                'id': f"{mid}_c{idx}", 'place': name, 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': snippet[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'course_target'
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
                log.warning(f'Error reading {ch}: {e}')
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
    return render_template('index.html', google_maps_key=GOOGLE_MAPS_KEY)

@app.route('/data')
def data():
    try:
        time_range = int(request.args.get('timeRange', 50))
    except Exception: time_range = 50
    messages = load_messages()
    tz = pytz.timezone('Europe/Kyiv')
    now = datetime.now(tz).replace(tzinfo=None)
    min_time = now - timedelta(minutes=time_range)
    hidden = set(load_hidden())
    out = []
    for m in messages:
        try:
            dt = datetime.strptime(m.get('date',''), '%Y-%m-%d %H:%M:%S')
        except Exception:
            continue
        if dt >= min_time:
            # build marker key similar to frontend hide logic (rounded lat/lng + text + source/channel)
            try:
                lat = round(float(m.get('lat')), 3)
                lng = round(float(m.get('lng')), 3)
            except Exception:
                continue
            text = (m.get('text') or '')
            source = m.get('source') or m.get('channel') or ''
            marker_key = f"{lat},{lng}|{text}|{source}"
            if marker_key in hidden:
                continue
            out.append(m)
    resp = jsonify({'tracks': out, 'all_sources': CHANNELS, 'trajectories': []})
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp

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

@app.route('/health')
def health():
    """Health & basic stats; also prunes stale presence entries."""
    now = time.time()
    with ACTIVE_LOCK:
        # Iterate explicitly to avoid comprehension indentation edge cases on some environments
        for vid, meta in list(ACTIVE_VISITORS.items()):
            ts = meta if isinstance(meta, (int, float)) else meta.get('ts', 0)
            if now - ts > ACTIVE_TTL:
                del ACTIVE_VISITORS[vid]
        visitors = len(ACTIVE_VISITORS)
    return jsonify({
        'status': 'ok',
        'messages': len(load_messages()),
        'auth': AUTH_STATUS,
        'visitors': visitors
    })

@app.route('/presence', methods=['POST'])
def presence():
    # Client sends a generated uuid every ~30s
    data = request.get_json(silent=True) or {}
    vid = data.get('id')
    if not vid:
        return jsonify({'status':'error','error':'id required'}), 400
    now = time.time()
    blocked = set(load_blocked())
    if vid in blocked:
        return jsonify({'status':'blocked'})
    remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    with ACTIVE_LOCK:
        ACTIVE_VISITORS[vid] = {'ts': now, 'ip': remote_ip}
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
                visitors.append({'id':vid,'ip':'','age':age,'age_fmt':_fmt_age(age)})
            else:
                age = int(now - meta.get('ts',0))
                visitors.append({'id':vid,'ip':meta.get('ip',''),'age':age,'age_fmt':_fmt_age(age)})
    blocked = load_blocked()
    return render_template('admin.html', visitors=visitors, blocked=blocked, secret=(request.args.get('secret') or ''))

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
}

# Район (district) fallback centers (можно расширять). Ключи в нижнем регистре без слова 'район'.
RAION_FALLBACK = {
    'покровський': (48.2767, 37.1763),  # Покровськ (Донецька)
    'покровский': (48.2767, 37.1763),
    'павлоградський': (48.5350, 35.8700),  # Павлоград
    'павлоградский': (48.5350, 35.8700),
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

def process_message(text, mid, date_str, channel):
    """Extract coordinates or try simple city geocoding (lightweight)."""
    original_text = text
    # Санитизация: убираем точную фразу "Повітряна тривога" (реквест пользователя)
    text = text.replace('Повітряна тривога', '').replace('повітряна тривога','').strip()
    # Убираем markdown * _ ` и базовые эмодзи-иконки в начале строк
    text = re.sub(r'[\*`_]+', '', text)
    # Удаляем ведущие эмодзи/иконки перед словами
    text = re.sub(r'^[\W_]+', '', text)
    # Если сообщение по сути только про тревогу (без упоминаний угроз) — пропускаем (не строим маркер)
    low_orig = original_text.lower()
    if 'повітряна тривога' in low_orig and not any(k in low_orig for k in ['бпла','дрон','шахед','shahed','geran','ракета','missile','iskander','s-300','s300','артил','града','смерч','ураган','mlrs']):
        return None
    # Общий набор ключевых слов угроз
    THREAT_KEYS = ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile','iskander','s-300','s300','каб','артил','града','смерч','ураган','mlrs','avia','авіа','авиа','бомба']
    def has_threat(txt: str):
        l = txt.lower()
        return any(k in l for k in THREAT_KEYS)
    # direct coordinates pattern
    def classify(th: str):
        l = th.lower()
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
    lower = text.lower()

    # --- Pattern: City (Oblast ...) e.g. "Павлоград (Дніпропетровська обл.)" ---
    bracket_city = re.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})\s*\(([^)]+)\)', text)
    if bracket_city:
        raw_city = bracket_city.group(1).strip().lower()
        raw_inside = bracket_city.group(2).lower()
        # Не интерпретировать 'район' как город
        if raw_city != 'район':
            norm_city = UA_CITY_NORMALIZE.get(raw_city, raw_city)
            coords = CITY_COORDS.get(norm_city)
            if not coords and OPENCAGE_API_KEY:
                coords = geocode_opencage(norm_city)
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
    lines = [ln.strip() for ln in text.split('\n') if ln.strip()]
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

    # --- Settlement matching using external dataset (if provided) (single first match) ---
    if SETTLEMENTS_INDEX and not region_hits:
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
    # одиночное 'район'
    raion_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё\-]{4,})\s+район', re.IGNORECASE)
    for m_r in raion_pattern.finditer(text):
        base = norm_raion(m_r.group(1))
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
            tracks.append({
                'id': f"{mid}_d{idx}", 'place': title, 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'raion'
            })
        if tracks:
            log.debug(f"RAION_MATCH mid={mid} -> {[t['place'] for t in tracks]}")
            return tracks

    # Region boundary logic (fallback single or midpoint for exactly two)
    matched_regions = []
    for name, coords in OBLAST_CENTERS.items():
        if name in lower:
            matched_regions.append((name, coords))
    if matched_regions:
        # Если только области упомянуты и нет ключей угроз, пропускаем
        if not has_threat(text):
            return None
        # --- Направления внутри области ---
        def detect_direction(lower_txt: str):
            if 'північно-захід' in lower_txt: return 'nw'
            if 'південно-захід' in lower_txt: return 'sw'
            if 'північно-схід' in lower_txt: return 'ne'
            if 'південно-схід' in lower_txt: return 'se'
            if ' північ' in lower_txt or lower_txt.startswith('північ'):
                return 'n'
            if ' південь' in lower_txt or lower_txt.startswith('південь'):
                return 's'
            if ' схід' in lower_txt or lower_txt.startswith('схід'):
                return 'e'
            if ' захід' in lower_txt or lower_txt.startswith('захід'):
                return 'w'
            return None
        direction_code = None
        if len(matched_regions) == 1 and not raion_matches:
            direction_code = detect_direction(lower)
            if direction_code:
                (reg_name, (base_lat, base_lng)) = matched_regions[0]
                def offset(lat, lng, code):
                    lat_step = 0.55
                    lng_step = 0.85 / max(0.2, abs(math.cos(math.radians(lat))))
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
                    'marker_icon': icon, 'source_match': 'region_direction'
                }]
            return None
        if len(matched_regions) == 2 and any(w in lower for w in ['межі','межу','межа','между','границі','граница','граніца','границю']):
            (n1,(a1,b1)), (n2,(a2,b2)) = matched_regions
            lat = (a1+a2)/2; lng = (b1+b2)/2
            threat_type, icon = classify(text)
            return [{
                'id': str(mid), 'place': f"Межа {n1.split()[0].title()}/{n2.split()[0].title()}", 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'region_boundary'
            }]
        else:
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
                    'marker_icon': icon, 'source_match': 'region_multi_simple'
                })
            if tracks:
                return tracks
    for city in UA_CITIES:
        if city in lower:
            norm = UA_CITY_NORMALIZE.get(city, city)
            coords = geocode_opencage(norm)
            if not coords:
                coords = CITY_COORDS.get(norm)
            if coords:
                lat, lng = coords
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': norm.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon
                }]
            # if city found but no coords even in fallback, continue scanning others
    return None

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