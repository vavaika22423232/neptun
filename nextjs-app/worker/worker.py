import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

KYIV_TZ = ZoneInfo('Europe/Kyiv')

import requests as http_requests
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Configuration
from constants import API_ID, API_HASH, CHANNELS
from db import db

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# Initialize Client
# On Render, the worker has NO persistent disk, so file-based sessions are lost
# on every deploy. Use StringSession from TELEGRAM_SESSION env var instead.
# To generate a session string, run: python -c "from telethon.sync import TelegramClient; from telethon.sessions import StringSession; c = TelegramClient(StringSession(), API_ID, API_HASH); c.start(); print(c.session.save())"
_session_string = os.getenv('TELEGRAM_SESSION', '')
if _session_string:
    log.info("Using StringSession from TELEGRAM_SESSION env var")
    client = TelegramClient(StringSession(_session_string), API_ID, API_HASH)
else:
    log.warning("TELEGRAM_SESSION not set — using file session (will NOT survive Render deploys!)")
    client = TelegramClient('anon_worker', API_ID, API_HASH)

# ── Ingest: push markers to Next.js web service ──────────────────────────────
# On Render, the worker and web service have SEPARATE disks.
# The worker cannot write to the web service's /data/messages.json directly.
# Instead, it POSTs marker data to /api/ingest on the web service.

INGEST_URL = os.getenv('INGEST_URL', '')          # e.g. https://neptun-alerts.onrender.com/api/ingest
INGEST_SECRET = os.getenv('AUTH_SECRET', '')       # shared secret with web service

if INGEST_URL:
    log.info(f"Ingest endpoint configured: {INGEST_URL}")
else:
    log.warning("INGEST_URL not set — markers will NOT appear on the web frontend!")

if not INGEST_SECRET:
    log.warning("AUTH_SECRET not set — ingest requests will be rejected by the web service!")


# ── Recent events buffer (for proximity scoring) ─────────────────────────────

_recent_events: list[dict] = []
MAX_RECENT = 50


def _add_recent(data: dict):
    _recent_events.append(data)
    if len(_recent_events) > MAX_RECENT:
        _recent_events.pop(0)


# ── Learning loop ────────────────────────────────────────────────────────────

async def _learning_loop():
    """Run feedback learning every 6 hours."""
    while True:
        await asyncio.sleep(6 * 3600)  # 6 hours
        try:
            from geo.feedback import learn_from_corrections
            stats = learn_from_corrections()
            log.info(f"Learning completed: {stats}")
        except Exception as e:
            log.error(f"Learning loop error: {e}", exc_info=True)


async def main():
    """Main worker loop."""
    log.info(f"Worker starting... Channels: {len(CHANNELS)}")

    # ── Pre-flight checks ─────────────────────────────────────────────────
    log.info(f"  INGEST_URL  = {'SET (' + INGEST_URL + ')' if INGEST_URL else 'NOT SET'}")
    log.info(f"  AUTH_SECRET = {'SET (len={})'.format(len(INGEST_SECRET)) if INGEST_SECRET else 'NOT SET'}")
    log.info(f"  DB type     = {type(db).__name__}")
    log.info(f"  API_ID      = {'SET' if API_ID else 'NOT SET'}")
    log.info(f"  API_HASH    = {'SET (len={})'.format(len(API_HASH)) if API_HASH else 'NOT SET'}")
    log.info(f"  Channels    = {CHANNELS}")

    if not INGEST_URL or not INGEST_SECRET:
        log.warning(
            "*** Markers will NOT reach the frontend! "
            "Set INGEST_URL and AUTH_SECRET in Render environment variables. ***"
        )

    if not API_ID or not API_HASH:
        log.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set! Exiting.")
        return

    # Ensure DB connection (in-memory DB is always "connected")
    if not db.is_connected():
        log.error("DB not connected! Exiting.")
        return

    # Start Telegram Client
    await client.start()
    log.info("Telegram Client Connected")

    # Start learning loop in background
    asyncio.create_task(_learning_loop())

    # Register event handlers
    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        try:
            await process_new_message(event)
        except Exception as e:
            log.error(f"Error processing message: {e}", exc_info=True)

    # Keep running
    await client.run_until_disconnected()


from core.parser_v2 import extract_entities
from constants import OBLAST_CENTERS
import uuid


def _fallback_coords_for_oblast(oblast: str):
    """Get approximate center coords for an oblast name.
    
    Returns (lat, lng) or None if oblast not recognized.
    """
    if not oblast:
        return None
    oblast_lower = oblast.lower().replace(' область', '').replace(' обл', '').strip()
    for key, coords in OBLAST_CENTERS.items():
        if oblast_lower.startswith(key) or key.startswith(oblast_lower[:4]):
            return coords
    return None


async def process_new_message(event):
    """
    Core processing pipeline:
    1. Deduplication
    2. Entity extraction (parser_v2)
    3. Geo resolution (geo/resolver)
    4. State update (Redis + POST to web service)
    """
    msg_text = event.message.message
    if not msg_text:
        return

    channel_id = event.chat_id
    msg_id = event.message.id
    
    # 1. Deduplication
    if db.is_message_processed(channel_id, msg_id):
        return
    db.mark_message_processed(channel_id, msg_id)

    # 2. Extract entities (no geocoding yet)
    entities = extract_entities(msg_text)

    if entities.is_negation or entities.event_type == 'unknown':
        return

    # 3. Resolve location via GeoResolver pipeline
    resolved = None
    try:
        from geo.resolver import resolve
        resolved = resolve(
            entities.to_entities_dict(),
            channel=str(channel_id),
            prev_events=_recent_events[-10:],
        )
    except ImportError:
        log.warning("geo.resolver not available")
    except Exception as e:
        log.error(f"Resolver error: {e}", exc_info=True)

    # Build output data (Kyiv timezone)
    now_kyiv = datetime.now(KYIV_TZ)
    threat_id = f"evt_{int(now_kyiv.timestamp())}_{str(uuid.uuid4())[:4]}"
    now_iso = now_kyiv.isoformat()

    if resolved and resolved.status != 'rejected':
        location = resolved.place_name
        region = resolved.oblast
        coords = (resolved.lat, resolved.lng) if resolved.lat != 0 else None
        confidence = resolved.confidence
        resolve_status = resolved.status
        candidates_json = [c.to_dict() for c in resolved.chosen_from[:3]]
    else:
        location = entities.place_name or 'Unknown'
        region = entities.oblast
        coords = None
        confidence = 0.0
        resolve_status = 'rejected' if resolved else 'no_resolver'
        candidates_json = []

    # Fallback: if no exact coords, use oblast center
    used_fallback = False
    if not coords and region:
        fallback = _fallback_coords_for_oblast(region)
        if fallback:
            coords = fallback
            used_fallback = True
            confidence = max(confidence, 0.1)  # at least minimal confidence
            resolve_status = 'oblast_fallback'
            log.info(f"Using oblast center fallback for {region}: {coords}")

    log.info(
        f"MATCH: {entities.event_type} @ {location} ({region}) "
        f"conf={confidence:.2f} status={resolve_status}"
    )

    data = {
        'id': threat_id,
        'type': entities.event_type,
        'threat_type': entities.event_type,  # frontend compatibility
        'location': location,
        'place': location,                   # frontend compatibility
        'region': region,
        'text': msg_text,
        'lat': coords[0] if coords else None,
        'lng': coords[1] if coords else None,
        'channel_id': channel_id,
        'msg_id': msg_id,
        'ts': now_iso,
        'date': now_iso,                     # frontend compatibility
        'confidence': round(confidence, 3),
        'resolve_status': resolve_status,
        'candidates': candidates_json,
        'resolver_version': 'v2',
    }

    # Add to recent events buffer
    _add_recent(data)

    # 4. Save to Redis
    # TTL based on type and confidence
    if entities.event_type in ['launch', 'explosion']:
        ttl = 1800  # 30min
    else:
        ttl = 7200  # 2h

    # Extend TTL for high-confidence results
    if confidence >= 0.8:
        ttl = int(ttl * 1.5)

    # Confidence-based degradation: don't show very low confidence on map
    # But always show oblast_fallback markers (they're the best we have)
    if confidence < 0.3 and resolve_status in ('low_confidence', 'rejected') and not used_fallback:
        data['hidden'] = True  # frontend won't show it, but it's logged

    db.save_threat(threat_id, data, ttl=ttl)
    db.publish_update('new_threat', data)

    # 5. Push marker to Next.js web service (for frontend)
    # Worker and web service have separate disks on Render,
    # so we POST data to /api/ingest instead of writing to a local file.
    if not INGEST_URL:
        log.warning(f"Skipping ingest: INGEST_URL not configured")
    elif not coords:
        log.warning(f"Skipping ingest for {threat_id}: no coordinates even after fallback")
    elif data.get('hidden'):
        log.info(f"Skipping ingest for {threat_id}: marker is hidden (low confidence)")
    else:
        try:
            resp = http_requests.post(
                INGEST_URL,
                json={'marker': data},
                headers={'X-Auth-Secret': INGEST_SECRET},
                timeout=10,
            )
            if resp.ok:
                body = resp.json()
                log.info(f"Ingested to web: {threat_id} ({body.get('total', '?')} total)")
            else:
                log.error(
                    f"Ingest failed [{resp.status_code}]: {resp.text[:300]} "
                    f"(URL={INGEST_URL}, secret={'set' if INGEST_SECRET else 'EMPTY'})"
                )
        except http_requests.exceptions.ConnectionError as e:
            log.error(f"Ingest connection failed (is web service running?): {e}")
        except http_requests.exceptions.Timeout:
            log.error(f"Ingest timed out after 10s: {INGEST_URL}")
        except Exception as e:
            log.error(f"Failed to POST to ingest: {e}", exc_info=True)


def shutdown_handler(sig, frame):
    log.info("Shutting down worker...")
    asyncio.create_task(client.disconnect())
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
