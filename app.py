import os, re, json, asyncio, threading, logging, pytz, time, subprocess
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
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
client = None
session_str = os.getenv('TELEGRAM_SESSION')  # Telethon string session (recommended for Render)
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # optional bot token fallback
AUTH_SECRET = os.getenv('AUTH_SECRET')  # simple shared secret to protect /auth endpoints
FETCH_THREAD_STARTED = False
AUTH_STATUS = {'authorized': False, 'reason': 'init'}
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

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_messages(data):
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
    'харьковский': (49.9935, 36.2304)
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
    # Санитизация: убираем точную фразу "Повітряна тривога" (реквест пользователя)
    text = text.replace('Повітряна тривога', '').replace('повітряна тривога','').strip()
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
    # Ищем конструкции вида "Покровський район" или просто "Покровський район" в тексте.
    raion_matches = []
    raion_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё\-]{4,})\s+район', re.IGNORECASE)
    for m_r in raion_pattern.finditer(text):
        base = m_r.group(1).strip().lower()
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
            return tracks

    # Region boundary logic (fallback single or midpoint for exactly two)
    matched_regions = []
    for name, coords in OBLAST_CENTERS.items():
        if name in lower:
            matched_regions.append((name, coords))
    if matched_regions:
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
    return jsonify({'tracks': out, 'all_sources': CHANNELS, 'trajectories': []})

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
    return jsonify({'status':'ok','messages':len(load_messages()), 'auth': AUTH_STATUS})

# ---------- Simple interactive auth endpoints (semi-automatic) ----------
# Use only with a secret: set AUTH_SECRET env var. These allow supplying a code
# without opening a shell. DO NOT expose without secret: anyone could take over session.
auth_state = {}
auth_lock = threading.Lock()
auth_sessions = {}

def _check_secret():
    if not AUTH_SECRET:
        return True  # if not set, allow (not recommended)
    provided = request.args.get('auth') or request.headers.get('X-Auth-Secret') or (request.json or {}).get('auth') if request.is_json else None
    return provided == AUTH_SECRET

@app.route('/auth/start', methods=['POST'])
def auth_start():
    if not _check_secret():
        return jsonify({'status':'forbidden'}), 403
    if not API_ID or not API_HASH:
        return jsonify({'status':'error','error':'API credentials missing'}), 400
    phone = (request.json or {}).get('phone') if request.is_json else None
    if not phone:
        return jsonify({'status':'error','error':'phone required'}), 400
    if not client:
        return jsonify({'status':'error','error':'client not initialized'}), 500
    async def _send():
        async with client:
            await client.connect()
            sent = await client.send_code_request(phone)
            with auth_lock:
                auth_state['phone'] = phone
                auth_state['phone_code_hash'] = sent.phone_code_hash
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(_send())
    else:
        loop.run_until_complete(_send())
    return jsonify({'status':'ok','message':'code sent (check Telegram/SMS)'})

@app.route('/auth/complete', methods=['POST'])
def auth_complete():
    if not _check_secret():
        return jsonify({'status':'forbidden'}), 403
    payload = request.json or {}
    code = payload.get('code')
    phone = payload.get('phone') or auth_state.get('phone')
    if not (code and phone):
        return jsonify({'status':'error','error':'phone and code required'}), 400
    pch = auth_state.get('phone_code_hash')
    if not pch:
        return jsonify({'status':'error','error':'start auth first'}), 400
    async def _sign_in():
        async with client:
            await client.connect()
            try:
                await client.sign_in(phone=phone, code=code, phone_code_hash=pch)
            except SessionPasswordNeededError:  # 2FA enabled
                return {'status':'error','error':'2FA password needed (not implemented)'}
            # produce new string session
            new_session = StringSession.save(client.session)
            return {'status':'ok','session': new_session}
    # Need import for exception
    from telethon.errors import SessionPasswordNeededError
    loop = asyncio.get_event_loop()
    if loop.is_running():
        fut = asyncio.ensure_future(_sign_in())
        # Can't await directly in sync route; simple busy wait (short)
        import time
        for _ in range(100):
            if fut.done(): break
            time.sleep(0.05)
        if not fut.done():
            return jsonify({'status':'error','error':'timeout'}), 500
        res = fut.result()
    else:
        res = loop.run_until_complete(_sign_in())
    if res.get('status')=='ok' and res.get('session'):
        try:
            with open('new_session.txt','w',encoding='utf-8') as f:
                f.write(res['session'])
        except Exception:
            pass
        # hot swap client for current runtime (will not persist after redeploy unless env updated)
        replace_client(res['session'])
        log.info('Session hot-swapped. Set TELEGRAM_SESSION env + redeploy for persistence.')
    return jsonify(res)

@app.route('/auth/status')
def auth_status():
    if not _check_secret():
        return jsonify({'status':'forbidden'}), 403
    return jsonify({'status':'ok','auth': AUTH_STATUS})

 # (Dynamic asset loader removed since template now static)

if __name__ == '__main__':
    start_fetch_thread()
    start_session_watcher()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT','8080')))
