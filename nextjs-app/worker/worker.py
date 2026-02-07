import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timedelta

from telethon import TelegramClient, events

# Configuration
from constants import API_ID, API_HASH, CHANNELS
from db import db
from core.message_store import MessageStore

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# Initialize Client
client = TelegramClient('anon_worker', API_ID, API_HASH)

# ── Messages file storage (shared with Next.js frontend via /data) ────────────

MESSAGES_FILE = os.getenv('MESSAGES_FILE', '/data/messages.json')
# Fallback: if /data doesn't exist (local dev), use local file
if not os.path.isdir(os.path.dirname(MESSAGES_FILE)):
    MESSAGES_FILE = 'messages.json'

MAX_MESSAGES = 500
RETENTION_HOURS = 3


def _prune_old_messages(messages: list[dict]) -> list[dict]:
    """Remove messages older than RETENTION_HOURS, keep manual markers, cap at MAX_MESSAGES."""
    cutoff = datetime.now() - timedelta(hours=RETENTION_HOURS)
    cutoff_iso = cutoff.isoformat()

    result = []
    for m in messages:
        # Always keep manual markers (added by admin)
        if m.get('manual'):
            result.append(m)
            continue

        # Check timestamp
        ts = m.get('ts') or m.get('timestamp') or m.get('date') or ''
        if ts and ts < cutoff_iso:
            continue  # too old, drop

        result.append(m)

    # Cap at MAX_MESSAGES (keep newest)
    if len(result) > MAX_MESSAGES:
        # Sort by ts descending, keep newest
        result.sort(key=lambda x: x.get('ts') or x.get('timestamp') or x.get('date') or '', reverse=True)
        result = result[:MAX_MESSAGES]

    return result


message_store = MessageStore(
    path=MESSAGES_FILE,
    prune_fn=_prune_old_messages,
    preserve_manual=True,
    backup_count=2,
)

log.info(f"MessageStore initialized: {MESSAGES_FILE}")


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
    
    # Ensure Redis connection
    if not db.is_connected():
        log.error("Redis not connected! Exiting.")
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
import uuid
import json


async def process_new_message(event):
    """
    Core processing pipeline:
    1. Deduplication
    2. Entity extraction (parser_v2)
    3. Geo resolution (geo/resolver)
    4. State update (Redis + messages.json)
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

    # Build output data
    threat_id = f"evt_{int(datetime.now().timestamp())}_{str(uuid.uuid4())[:4]}"
    now_iso = datetime.now().isoformat()

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
    if confidence < 0.3 and resolve_status in ('low_confidence', 'rejected'):
        data['hidden'] = True  # frontend won't show it, but it's logged

    db.save_threat(threat_id, data, ttl=ttl)
    db.publish_update('new_threat', data)

    # 5. Save to messages.json (for Next.js frontend)
    # Only save markers that have coordinates and are not hidden
    if coords and not data.get('hidden'):
        try:
            current = message_store.load()
            current.append(data)
            message_store.save(current)
            log.info(f"Saved to messages.json: {threat_id} ({len(current)+1} total)")
        except Exception as e:
            log.error(f"Failed to save to messages.json: {e}", exc_info=True)


def shutdown_handler(sig, frame):
    log.info("Shutting down worker...")
    asyncio.create_task(client.disconnect())
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
