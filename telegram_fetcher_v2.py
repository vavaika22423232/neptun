#!/usr/bin/env python3
import os, asyncio, json, logging, sys
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient
from telethon.sessions import StringSession

# Ensure we run relative to project directory (GMhost cron-safe)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

# Import app to reuse env loader, settings, and processing/merge utilities
try:
    import app as app_module
except Exception as e:
    print(f"ERROR: Cannot import app.py: {e}")
    sys.exit(1)

# Load .env (if present) before reading env vars
try:
    if hasattr(app_module, '_load_local_env'):
        app_module._load_local_env()
except Exception:
    pass

# Pull settings from app
process_message = getattr(app_module, 'process_message')
maybe_merge_track = getattr(app_module, 'maybe_merge_track')
ensure_ua_place = getattr(app_module, 'ensure_ua_place', lambda x: x)
load_messages = getattr(app_module, 'load_messages')
save_messages = getattr(app_module, 'save_messages')
CHANNELS = getattr(app_module, 'CHANNELS', [])
MESSAGES_FILE = getattr(app_module, 'MESSAGES_FILE', os.path.join(BASE_DIR, 'messages.json'))

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger('gmhost_fetch')

async def fetch_messages():
    api_id = os.environ.get('TELEGRAM_API_ID')
    api_hash = os.environ.get('TELEGRAM_API_HASH')
    session_string = os.environ.get('TELEGRAM_SESSION')

    if not api_id or not api_hash or not session_string:
        log.error('Missing TELEGRAM_API_ID/TELEGRAM_API_HASH/TELEGRAM_SESSION in environment (.env)')
        return

    try:
        api_id_int = int(api_id)
    except Exception:
        log.error('TELEGRAM_API_ID must be an integer')
        return

    client = TelegramClient(StringSession(session_string), api_id_int, api_hash)
    tz = pytz.timezone('Europe/Kyiv')
    cutoff = datetime.now(tz) - timedelta(minutes=int(os.getenv('BACKFILL_MINUTES', '60')))

    data = load_messages() or []
    log.info(f'Loaded current messages: {len(data)} from {MESSAGES_FILE}')

    try:
        await client.start()
        log.info('Telegram client connected successfully')
        total_new = 0
        for ch in CHANNELS:
            ch = ch.strip()
            if not ch:
                continue
            added_for_channel = 0
            try:
                async for message in client.iter_messages(ch, limit=200):
                    if not message.text:
                        continue
                    dt = message.date.astimezone(tz)
                    if dt < cutoff:
                        break
                    tracks = process_message(message.text, message.id, dt.strftime('%Y-%m-%d %H:%M:%S'), ch)
                    if not tracks:
                        continue
                    for t in tracks:
                        if t.get('place'):
                            t['place'] = ensure_ua_place(t['place'])
                        merged, ref = maybe_merge_track(data, t)
                        if not merged:
                            data.append(t)
                            added_for_channel += 1
                if added_for_channel:
                    log.info(f'Channel {ch}: added {added_for_channel} new tracks')
                total_new += added_for_channel
            except Exception as ce:
                log.warning(f'Error reading {ch}: {ce}')
        # Persist
        save_messages(data)
        log.info(f'Fetch complete. Added {total_new} new tracks. Total now: {len(data)}')
    except Exception as e:
        log.error(f'Telegram client error: {e}')
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

if __name__ == '__main__':
    asyncio.run(fetch_messages())
