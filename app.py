import os, re, json, asyncio, threading, logging, pytz
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from telethon import TelegramClient
from telethon.errors import (
    AuthKeyDuplicatedError,
    AuthKeyUnregisteredError,
    FloodWaitError,
    RpcError
)
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)
client = None
session_str = os.getenv('TELEGRAM_SESSION')  # Telethon string session (recommended for Render)
if API_ID and API_HASH:
    if session_str:
        log.info('Initializing Telegram client with TELEGRAM_SESSION string.')
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
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
    'київ','харків','одеса','одесса','дніпро','дніпропетровськ','львів','запоріжжя','запорожье','вінниця','миколаїв','николаев','маріуполь','полтава','чернігів','чернигов','черкаси','житомир','суми','хмельницький','чернівці','рівне','івано-франківськ','луцьк','тернопіль','ужгород','кропивницький','кіровоград','кременчук','краматорськ','біла церква','мелітополь','бердянськ'
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
    # direct coordinates pattern
    m = re.search(r'(\d{1,2}\.\d+),(\d{1,3}\.\d+)', text)
    if m:
        lat = float(m.group(1)); lng = float(m.group(2))
        return [{
            'id': str(mid), 'place': 'Unknown', 'lat': lat, 'lng': lng,
            'threat_type': 'shahed', 'text': text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': 'shahed.png'
        }]
    lower = text.lower()
    for city in UA_CITIES:
        if city in lower:
            norm = UA_CITY_NORMALIZE.get(city, city)
            coords = geocode_opencage(norm)
            if coords:
                lat, lng = coords
                return [{
                    'id': str(mid), 'place': norm.title(), 'lat': lat, 'lng': lng,
                    'threat_type': 'shahed', 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': 'shahed.png'
                }]
            break
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
            if not await client.is_user_authorized():
                log.error('Telegram client NOT authorized. Provide TELEGRAM_SESSION env var or re-generate session.')
                return False
            return True
        except AuthKeyDuplicatedError:
            log.error('AuthKeyDuplicatedError: The TELEGRAM_SESSION is in use elsewhere or duplicated. Generate a NEW session string and redeploy. Stopping fetch loop.')
            return False
        except AuthKeyUnregisteredError:
            log.error('AuthKeyUnregisteredError: Session invalid/expired. Generate new TELEGRAM_SESSION.')
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
        # Give user time to fix session
        await asyncio.sleep(180)
        return
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
                        log.debug(f'Backfill skip (no geo): {ch_strip} #{msg.id} {msg.text[:80]!r}')
                if fetched:
                    total_backfilled += fetched
                    log.info(f'Backfilled {fetched} messages from {ch_strip}')
            except Exception as e:
                log.warning(f'Backfill error {ch_strip}: {e}')
        if total_backfilled:
            save_messages(all_data)
            log.info(f'Backfill saved: {total_backfilled} new messages with geo')
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
                return
            except FloodWaitError as fe:
                wait = int(getattr(fe, 'seconds', 60))
                log.warning(f'FloodWait while reading {ch}: sleep {wait}s')
                await asyncio.sleep(wait)
            except RpcError as re:
                log.warning(f'RPC error reading {ch}: {re}')
            except Exception as e:
                log.warning(f'Error reading {ch}: {e}')
        if new_tracks:
            all_data.extend(new_tracks)
            save_messages(all_data)
        await asyncio.sleep(60)

def start_fetch_thread():
    if not client: return
    loop = asyncio.new_event_loop()
    def runner():
        asyncio.set_event_loop(loop)
        with client:
            loop.run_until_complete(fetch_loop())
    t = threading.Thread(target=runner, daemon=True)
    t.start()

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
    return jsonify({'status':'ok','messages':len(load_messages())})

 # (Dynamic asset loader removed since template now static)

if __name__ == '__main__':
    start_fetch_thread()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT','8080')))
