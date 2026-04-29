"""
worker.py — Multi-channel Telegram listener for Ukrainian threat alerts.

Monitors 12+ Telegram channels, extracts threat entities (shaheds, missiles,
ballistics, KABs, recon drones), geocodes them, and pushes markers to the
Next.js web frontend via /api/ingest. Server-side Spatial Correlator
handles cross-channel fusion (merging nearby markers of the same type).
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import math
import os
import re
import signal
import sys
import threading
import uuid
from collections import deque
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[import-not-found]

KYIV_TZ = ZoneInfo('Europe/Kyiv')

import aiohttp
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from dotenv import load_dotenv

# Configuration
from constants import API_ID, API_HASH, CHANNELS, CHANNEL_META, THREAT_SPEEDS, LAUNCH_SITES, KAB_AIRFIELDS, CARDINAL_AIRFIELDS, CHANNEL_DEFAULT_OBLAST, REGION_TOPIC_MAP, RAION_NAME_TO_ID, REGION_TO_OBLAST_ID, is_gpt_parser_enabled
from channel_profiles.kherson_non_drone import (
    CHANNEL_USERNAME as KHERSON_NON_DRONE_CH,
    GEO_CITY_HINT as KHERSON_GEO_CITY_HINT,
    MARKER_ICON_FILENAME as KHERSON_MARKER_ICON,
    extract_kherson_non_drone_place_hint,
    is_kherson_non_drone_raion_allowed,
    normalize_kherson_non_drone_message,
)
from db import db
from fcm_sender import send_threat_push
from alarm_monitor import alarm_monitor_loop
from ingest_queue import IngestQueue
from geo_bounds import is_plausible_threat_coord
from geo.maritime_region import normalize_maritime_marker_fields
from geo.place_guardrails import validate_place_candidate
from geo.rules import oblast_uk_name_to_hasc
from core.chain_tracker import MessageChainTracker

# [NEW] Import Track Manager (legacy — kept for fallback reference)
from core.tracker_engine import tracker, Observation as TrackerObs
# [NEW] Cross-channel Target Aggregator (primary)
from core.target_aggregator import target_aggregator, Observation as AggObs

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# Initialize Client
_session_string = os.getenv('TELEGRAM_SESSION', '')
if _session_string:
    log.info("Using StringSession from TELEGRAM_SESSION env var")
    client = TelegramClient(StringSession(_session_string), API_ID, API_HASH)
else:
    log.warning("TELEGRAM_SESSION not set — using file session")
    client = TelegramClient('anon_worker', API_ID, API_HASH)

# ── Ingest endpoint ──────────────────────────────────────────────────────────
INGEST_URL = os.getenv('INGEST_URL', '')
# Prefer INGEST_SECRET so a leaked worker key does not equal admin API secret (see server-secrets.ts).
INGEST_SECRET = os.getenv('INGEST_SECRET') or os.getenv('AUTH_SECRET', '')

if INGEST_URL:
    log.info(f"Ingest endpoint: {INGEST_URL}")
else:
    log.warning("INGEST_URL not set — markers will NOT appear on the web frontend!")

if is_gpt_parser_enabled():
    log.info('GPT parser + AI analyzer enabled (DISABLE_GPT_PARSER=0)')
else:
    log.info('GPT parser + AI analyzer disabled (default) — regex-primary; set DISABLE_GPT_PARSER=0 to enable OpenAI')

if not INGEST_SECRET:
    log.warning("INGEST_SECRET / AUTH_SECRET not set — ingest requests will be rejected!")

# ── Admin feed endpoint ─────────────────────────────────────────────────────
# Derive from INGEST_URL: replace /api/ingest with /api/admin/feed/ingest
FEED_URL = ''
CLEAR_REGION_URL = ''
DATA_URL = ''
if INGEST_URL:
    _base = INGEST_URL.rsplit('/api/ingest', 1)[0]
    FEED_URL = f"{_base}/api/admin/feed/ingest"
    CLEAR_REGION_URL = f"{_base}/api/ingest/clear-region"
    DATA_URL = f"{_base}/api/data"
    log.info(f"Feed endpoint: {FEED_URL}")
    log.info(f"Clear-region endpoint: {CLEAR_REGION_URL}")

# ── Retry queue for failed ingests ───────────────────────────────────────────
ingest_queue = IngestQueue(INGEST_URL, INGEST_SECRET)

# ── Message chain tracker for follow-up detection ───────────────────────────────
chain_tracker = MessageChainTracker()


def _ingest_coords_ok(data: dict) -> bool:
    """Same rules as Next.js `validateIngestMarker` / `geo-bounds.ts`."""
    try:
        return is_plausible_threat_coord(
            data.get('lat'), data.get('lng'),
            manual=bool(data.get('manual')),
        )
    except Exception:
        return False


# Event types that bypass the alarm check — these are instant/critical threats
# where the alarm siren may not have been activated yet.
_ALARM_BYPASS_TYPES = frozenset({
    'ballistic', 'launch', 'missile', 'explosion', 'kab',
    'shahed', 'uav', 'drone', 'fpv', 'rozved',
})


def _should_ingest_by_alarm(region: str | None, event_type: str, raion: str | None = None) -> bool:
    """Check if a marker should be ingested based on active alarms.

    Returns True (allow ingest) when:
    - event type is instant/critical (ballistic, launch, missile, kab, explosion)
    - alarm state is not loaded yet (fail-open)
    - region is unknown
    - region has an active alarm (state or district level)
    """
    if event_type in _ALARM_BYPASS_TYPES:
        return True
    try:
        from alarm_monitor import is_region_under_alarm, is_district_under_alarm
        if is_region_under_alarm(region):
            return True
        if raion and is_district_under_alarm(raion):
            return True
        return False
    except ImportError:
        return True


def _distinct_toponym_signals(entities_list: list) -> int:
    """Rough count of unique geo strings across entities (multi-threat / ambiguous text)."""
    keys: set[str] = set()
    for e in entities_list:
        if getattr(e, 'is_negation', False) or getattr(e, 'is_allclear', False):
            continue
        for raw in (
            getattr(e, 'place_name', None),
            getattr(e, 'target_city', None),
            getattr(e, 'near', None),
            getattr(e, 'direction', None),
        ):
            if not raw or not str(raw).strip():
                continue
            token = str(raw).strip().lower()
            if len(token) < 3:
                continue
            keys.add(token[:96])
    return len(keys)


def _message_multi_place_risk(entities_list: list, msg_text: str) -> bool:
    """True when message likely mixes several places — point pin is often wrong."""
    if len(entities_list) >= 3:
        return True
    if _distinct_toponym_signals(entities_list) >= 3:
        return True
    lines = [ln.strip() for ln in (msg_text or '').split('\n') if ln.strip()]
    numbered = sum(1 for ln in lines if re.match(r'^\d+[\).\s]', ln))
    if numbered >= 3:
        return True
    return False


def _sea_context_inland_mismatch(msg_text: str, lat: float, lng: float) -> bool:
    """Sea / aquatory mentioned but coords land deep inland — typical bad geocode."""
    ml = (msg_text or '').lower()
    sea_kw = (
        'море', 'акватор', 'над мор', 'чорним мор', 'чорного мор',
        'флотил', 'морськ', 'над водою',
    )
    if not any(k in ml for k in sea_kw):
        return False
    if not (44.0 < lat < 53.0 and 22.0 < lng < 41.0):
        return False
    # Crude inland boxes (Kyiv–Chernihiv–north Zhytomyr) — not coast
    if 50.15 <= lat <= 51.75 and 29.8 <= lng <= 32.2:
        return True
    if 49.8 <= lat <= 51.2 and 28.5 <= lng <= 30.0:
        return True
    return False


_COARSE_PLACEMENT_STATUSES = frozenset({
    'oblast_fallback',
    'oblast_direction_only',
    'estimated_oblast_center',
    'estimated_offset_coastal',
    'ambiguous_no_point',
})


_http_session: aiohttp.ClientSession | None = None


def _close_aiohttp_sessions():
    """Close aiohttp sessions on exit to avoid 'Unclosed client session' warnings."""
    global _http_session
    try:
        loop = asyncio.new_event_loop()
        if _http_session and not _http_session.closed:
            loop.run_until_complete(_http_session.close())
        if ingest_queue._session and not ingest_queue._session.closed:
            loop.run_until_complete(ingest_queue._session.close())
    except Exception:
        pass
    finally:
        if 'loop' in dir() and loop is not None:
            try:
                loop.close()
            except Exception:
                pass


atexit.register(_close_aiohttp_sessions)


def get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session

async def _clear_region_markers(
    oblast: str,
    threat_types: list[str] | None = None,
    place_contains: str | None = None,
) -> int:
    """Remove markers in an oblast from the Next.js store, optionally only those whose place/location matches.
    Called on allclear / дорозвідка. Returns removed count.
    Immediate server-side delete (not TTL); see nextjs-app/docs/ALLCLEAR_AND_PUBLIC_MAP.md."""
    if not CLEAR_REGION_URL or not oblast:
        return 0
    try:
        payload: dict = {'region': oblast}
        if threat_types:
            payload['threat_types'] = threat_types
        if place_contains and str(place_contains).strip():
            payload['place_contains'] = str(place_contains).strip()
        
        session = get_http_session()
        async with session.post(
            CLEAR_REGION_URL,
            json=payload,
            headers={'X-Auth-Secret': INGEST_SECRET},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                removed = data.get('removed', 0)
                if removed > 0:
                    log.info(f"CLEAR-REGION: removed {removed} markers in {oblast}" +
                             (f" (types: {threat_types})" if threat_types else ""))
                return removed
            else:
                body_text = await resp.text()
                log.warning(f"CLEAR-REGION failed [{resp.status}]: {body_text[:200]}")
    except Exception as e:
        log.error(f"CLEAR-REGION error for {oblast}: {e}")
    return 0


# ── Recent events buffer (for proximity scoring) ─────────────────────────────

_recent_events: deque = deque(maxlen=100)
MAX_RECENT = 100


def _add_recent(data: dict):
    _recent_events.append(data)


ingest_queue.on_ingest_success = _add_recent

# ── Admin feed publisher ─────────────────────────────────────────────────────
# Fire-and-forget POST to /api/admin/feed/ingest for pipeline visibility.
# Non-blocking: runs in a thread, errors silently ignored (feed is non-critical).

async def _publish_feed_event(
    *,
    status: str,
    channel_name: str,
    msg_text: str,
    channel_id: int = 0,
    msg_id: int = 0,
    reason: str = '',
    threat_type: str = '',
    entities_count: int = 0,
    parser: str = '',
    place: str = '',
    region: str = '',
    lat: float | None = None,
    lng: float | None = None,
    speed_kmh: float | None = None,
    course_bearing: float | None = None,
    track_id: str = '',
    confidence: float | None = None,
    resolve_status: str = '',
    marker_id: str = '',
    origin: str = '',
    impact_place: str = '',
):
    """Push a pipeline event to the admin feed. Non-blocking."""
    if not FEED_URL:
        return
    now_iso = datetime.now(KYIV_TZ).isoformat()
    event = {
        'ts': now_iso,
        'status': status,
        'channel_name': channel_name,
        'channel_id': channel_id,
        'msg_id': msg_id,
        'msg_text': msg_text[:300],
        'reason': reason,
        'threat_type': threat_type,
        'entities_count': entities_count,
        'parser': parser,
        'place': place,
        'region': region,
        'lat': lat,
        'lng': lng,
        'speed_kmh': speed_kmh,
        'course_bearing': course_bearing,
        'track_id': track_id,
        'confidence': confidence,
        'resolve_status': resolve_status,
        'marker_id': marker_id,
        'origin': origin,
        'impact_place': impact_place,
    }
    normalize_maritime_marker_fields(event)
    # Remove None/empty values to save bandwidth
    _STRIP_ZERO_KEYS = {'channel_id', 'msg_id', 'entities_count'}
    event = {
        k: v for k, v in event.items()
        if v is not None and v != '' and not (v == 0 and k in _STRIP_ZERO_KEYS)
    }
    event['status'] = status
    event['channel_name'] = channel_name
    event['ts'] = now_iso

    try:
        session = get_http_session()
        async with session.post(
            FEED_URL,
            json={'event': event},
            headers={'X-Auth-Secret': INGEST_SECRET},
            timeout=aiohttp.ClientTimeout(total=3),
        ) as resp:
            await resp.read()  # Fire-and-forget, but must consume body to release socket
            if resp.status >= 400:
                log.warning('admin feed POST %s: HTTP %s', FEED_URL, resp.status)
    except Exception as e:
        log.warning('admin feed POST failed: %s', e)


# ── Cross-channel deduplication: REMOVED ─────────────────────────────────────
# Dedup was replaced by Cross-Channel Fusion (Feb 2026).
# Every message now goes through full processing (GPT → geo → chain → ingest).
# The server-side Spatial Correlator (markers-store.ts) merges nearby markers
# of the same type instead of creating duplicates.
# This ensures NO information is lost from secondary channel reports.


# ── Learning loop ────────────────────────────────────────────────────────────

# ── Learning loop ────────────────────────────────────────────────────────────

async def _learning_loop():
    """DEPRECATED: TrackManager handles learning internally if needed."""
    pass

async def _intelligence_save_loop():
    """Periodically save trajectory intelligence to disk + log status."""
    while True:
        await asyncio.sleep(600)  # every 10 min
        try:
            tracker.prune_stale_tracks(datetime.now(KYIV_TZ).timestamp(), 60)
            agg_stats = target_aggregator.get_stats()
            log.info(
                f"Tracker Status: {len(tracker.get_tracks())} legacy tracks, "
                f"Aggregator: {agg_stats['active_targets']} targets {agg_stats['by_group']}"
            )
            from ai_trajectory import flush_learned_targets_disk
            flush_learned_targets_disk()
        except Exception as e:
            log.error(f"Intelligence save error: {e}", exc_info=True)


# ── Global Settings Sync ─────────────────────────────────────────────────────

MIN_CONFIDENCE_THRESHOLD = 0.65


def _min_trusted_resolver_conf() -> float:
    """Trust resolver lat/lng only if confidence clears admin map bar + margin."""
    raw = os.getenv('NEPTUN_MIN_RESOLVED_POINT_CONF', '').strip()
    if raw:
        try:
            v = float(raw)
            if 0.2 <= v <= 0.95:
                return v
        except ValueError:
            pass
    return max(0.32, float(MIN_CONFIDENCE_THRESHOLD) + 0.02)


def _cap_confidence_coarse_placements(confidence: float, resolve_status: str) -> float:
    """Centroid / heuristic sectors are not pin-accurate — stay below map threshold so UI filters them."""
    coarse = frozenset({
        'oblast_fallback',
        'oblast_direction_only',
        'estimated_oblast_center',
        'estimated_offset_coastal',
    })
    if resolve_status not in coarse:
        return confidence
    ceiling = max(0.06, MIN_CONFIDENCE_THRESHOLD - 0.02)
    return min(float(confidence), ceiling)


async def _sync_settings_loop():
    """Background task to fetch global threshold settings periodically."""
    global MIN_CONFIDENCE_THRESHOLD
    # Wait for the INGEST_URL to be set, otherwise default to local 0.3
    if not INGEST_URL:
        return

    _base = INGEST_URL.rsplit('/api/ingest', 1)[0]
    settings_url = f"{_base}/api/settings"

    settings_headers = {'X-Auth-Secret': INGEST_SECRET} if INGEST_SECRET else {}

    # Immediate first fetch so worker respects admin threshold from startup
    try:
        session = get_http_session()
        async with session.get(settings_url, timeout=5, headers=settings_headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                new_min = data.get('minConfidence')
                if isinstance(new_min, (int, float)):
                    MIN_CONFIDENCE_THRESHOLD = float(new_min)
                    log.info(f"Settings sync: MIN_CONFIDENCE_THRESHOLD = {MIN_CONFIDENCE_THRESHOLD}")
            await resp.read()
    except Exception as e:
        log.debug(f"Initial settings fetch failed: {e}")

    while True:
        try:
            session = get_http_session()
            async with session.get(settings_url, timeout=5, headers=settings_headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    new_min = data.get('minConfidence')
                    if isinstance(new_min, (int, float)):
                        if MIN_CONFIDENCE_THRESHOLD != new_min:
                            log.info(f"Admin Config Update: Changed MIN_CONFIDENCE_THRESHOLD from {MIN_CONFIDENCE_THRESHOLD} to {new_min}")
                            MIN_CONFIDENCE_THRESHOLD = new_min
                await resp.read()
        except Exception as e:
            log.debug(f"Failed to fetch global settings: {e}")
        finally:
            await asyncio.sleep(30)


# ── Channel name resolver ────────────────────────────────────────────────────

_channel_name_cache: dict[int, str] = {}


async def _resolve_channel_name(event) -> str:
    """Get the human-readable channel username from an event."""
    chat_id = event.chat_id
    if chat_id in _channel_name_cache:
        return _channel_name_cache[chat_id]
    try:
        entity = await event.get_chat()
        name = getattr(entity, 'username', None) or str(chat_id)
        _channel_name_cache[chat_id] = name
        return name
    except Exception:
        return str(chat_id)


# ── Main ─────────────────────────────────────────────────────────────────────

async def main():
    """Main worker loop."""
    log.info(f"Worker starting... Channels: {len(CHANNELS)}")
    log.info(f"  INGEST_URL  = {'SET (' + INGEST_URL + ')' if INGEST_URL else 'NOT SET'}")
    log.info(
        f"  ingest auth = {'SET (len=' + str(len(INGEST_SECRET)) + ')' if INGEST_SECRET else 'NOT SET'} "
        f"(INGEST_SECRET or AUTH_SECRET)"
    )
    log.info(f"  DB type     = {type(db).__name__}")
    log.info(f"  API_ID      = {'SET' if API_ID else 'NOT SET'}")
    log.info(f"  API_HASH    = {'SET (len={})'.format(len(API_HASH)) if API_HASH else 'NOT SET'}")
    log.info(f"  Channels    = {CHANNELS}")

    if not INGEST_URL or not INGEST_SECRET:
        log.warning("*** Markers will NOT reach the frontend! Set INGEST_URL and INGEST_SECRET (or AUTH_SECRET). ***")

    if not API_ID or not API_HASH:
        log.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set! Exiting.")
        return

    if not db.is_connected():
        log.error("DB not connected! Exiting.")
        return

    # Start Telegram Client
    await client.start()
    log.info("Telegram Client Connected")

    # Resolve channel entities ONCE at startup (avoid repeated get_dialogs calls
    # which cause flood wait errors and block the event handler registration).
    _resolved_ids: set[int] = set()
    for ch in CHANNELS:
        try:
            entity = await client.get_input_entity(ch)
            _channel_id = getattr(entity, 'channel_id', None) or getattr(entity, 'chat_id', None)
            if _channel_id:
                _resolved_ids.add(_channel_id)
                _channel_name_cache[_channel_id] = ch  # pre-fill name cache
                log.info(f"  Resolved channel: {ch} -> {_channel_id}")
            else:
                log.warning(f"  Could not resolve channel ID for: {ch}")
        except Exception as e:
            log.warning(f"  Failed to resolve channel '{ch}': {e}")

    log.info(f"Resolved {len(_resolved_ids)}/{len(CHANNELS)} channels")

    # Join / subscribe to each channel so Telegram delivers updates.
    # get_input_entity() only resolves the ID — it does NOT subscribe.
    # Without this, events.NewMessage() only fires for already-joined channels.
    joined_count = 0
    for ch in CHANNELS:
        try:
            await client(JoinChannelRequest(ch))
            joined_count += 1
            log.info(f"  Joined channel: {ch}")
        except Exception as e:
            log.warning(f"  Could not join channel '{ch}': {e}")
    log.info(f"Joined {joined_count}/{len(CHANNELS)} channels")

    # (Removed trajectory_intelligence load)

    # Start learning loop in background
    asyncio.create_task(_learning_loop())
    asyncio.create_task(_intelligence_save_loop())

    # Start global settings sync (confidence threshold from admin)
    asyncio.create_task(_sync_settings_loop())

    # Start air raid alarm monitor (polls ukrainealarm API → FCM push)
    asyncio.create_task(alarm_monitor_loop(REGION_TOPIC_MAP))

    # Start ingest retry queue (retries failed marker POSTs every 15s)
    ingest_queue.start_retry_loop()
    log.info(f"  Ingest queue: {ingest_queue.pending_count} pending markers")

    # Register event handler WITHOUT chats= filter to avoid get_dialogs flood.
    # Filter by resolved channel IDs manually in the handler.
    async def _dispatch(event):
        chat_id = event.chat_id
        abs_id = abs(chat_id)
        if abs_id > 10**12:
            abs_id = abs_id - 10**12 * (abs_id // 10**12)
        if abs_id not in _resolved_ids and chat_id not in _resolved_ids:
            return
        try:
            await process_new_message(event)
        except Exception as e:
            log.error(f"Error processing message: {e}", exc_info=True)

    client.on(events.NewMessage())(_dispatch)
    # Many channels (rozvidkaneba, sectorv666) edit messages to add new drone targets.
    # Without this, updated positions are silently lost.
    client.on(events.MessageEdited())(_dispatch)
    log.info("Registered handlers: NewMessage + MessageEdited")

    # Keep running
    await client.run_until_disconnected()


# ── Imports for processing ───────────────────────────────────────────────────

from core.parser_v2 import (
    extract_all_entities,
    CARDINAL_DIRECTIONS,
    OBLAST_NORMALIZATION,
    regional_oblast_nickname_covers_place,
)
from core.message_filter import is_skip_message, extract_header_oblast, detect_allclear_keywords
from constants import OBLAST_CENTERS
from ai_trajectory import predict_trajectory as ai_predict_trajectory
from ai_message_analyzer import analyze_message as ai_analyze_message, get_variable_speed, resolve_origin_coords, get_sea_waypoints
from gpt_parser import gpt_parse_message, gpt_to_parsed_entities
import uuid


# ── Cardinal direction → bearing offset (for computing synthetic target) ─────
CARDINAL_BEARINGS = {
    'north': 0, 'northeast': 45, 'east': 90, 'southeast': 135,
    'south': 180, 'southwest': 225, 'west': 270, 'northwest': 315,
}


def _direction_to_bearing(entities) -> float | None:
    """Extract numeric bearing from entities.
    Priority: 1) GPT course_bearing_degrees, 2) CARDINAL_DIRECTIONS lookup on direction string.
    Returns bearing 0-360 or None."""
    # Priority 1: GPT already computed numeric bearing
    gpt_brg = getattr(entities, 'course_bearing_degrees', None)
    if gpt_brg is not None:
        return float(gpt_brg) % 360

    # Priority 2: cardinal direction string → bearing
    if entities.direction:
        direction_lower = entities.direction.lower().strip()
        cardinal = CARDINAL_DIRECTIONS.get(direction_lower)
        if cardinal:
            return float(CARDINAL_BEARINGS[cardinal])
    return None


def _geocode_origin(origin_str: str, *, allow_resolver_fallback: bool = False) -> tuple[float, float] | None:
    """Geocode a launch origin / source location (Крим, Чорне море, Курськ).
    Checks LAUNCH_SITES → OBLAST_CENTERS. Only falls back to the general resolver
    when allow_resolver_fallback=True (for bearing computation, not for launch-site checks)."""
    if not origin_str or len(origin_str) < 2:
        return None
    origin_lower = origin_str.lower().strip()

    # Check LAUNCH_SITES (exact then partial)
    if origin_lower in LAUNCH_SITES:
        return LAUNCH_SITES[origin_lower]
    for key, coords in LAUNCH_SITES.items():
        if origin_lower in key or key in origin_lower:
            return coords

    # Check OBLAST_CENTERS
    for key, coords in OBLAST_CENTERS.items():
        if origin_lower.startswith(key) or key.startswith(origin_lower[:4]):
            return coords

    if allow_resolver_fallback:
        return _geocode_direction_target(origin_str, None)
    return None


def _fallback_coords_for_oblast(oblast: str):
    """Get approximate center coords for an oblast name."""
    if not oblast:
        return None
    oblast_lower = oblast.lower().replace(' область', '').replace(' обл', '').strip()
    for key, coords in OBLAST_CENTERS.items():
        if oblast_lower.startswith(key) or key.startswith(oblast_lower[:4]):
            return coords
    return None


def _compute_bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Compute geodetic bearing (degrees, 0=N, 90=E) between two points."""
    lat1r, lat2r = math.radians(lat1), math.radians(lat2)
    dlng = math.radians(lng2 - lng1)
    x = math.sin(dlng) * math.cos(lat2r)
    y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlng)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Jitter coords for count-splitting (worker creates N markers per group) ───

_JITTER_RADIUS_KM = 10  # scatter radius for individual drone markers
_KM_TO_DEG_LAT = 1 / 111.32  # approximate km → degree latitude
# Default ON: deterministic jitter prevents markers stacking; set NEPTUN_COORD_JITTER=0 to disable
_COORD_JITTER_ENABLED = os.getenv('NEPTUN_COORD_JITTER', '1').lower() not in ('0', 'false', 'no', 'off')

# Geo quality (see QUALITY.md): recent-events bearing is a weak heuristic — off by default
_RECENT_EVENTS_BEARING = os.getenv('NEPTUN_RECENT_EVENTS_BEARING', '').lower() in ('1', 'true', 'yes')
_USE_OBLAST_CENTER = os.getenv('NEPTUN_USE_OBLAST_CENTER', '').lower() in ('1', 'true', 'yes')
# Default ON: drop pin when resolver has multiple tied candidates (reduces wrong-city pins).
_OMIT_AMBIGUOUS_COORDS = os.getenv('NEPTUN_OMIT_COORDS_ON_AMBIGUOUS', '1').lower() not in (
    '0', 'false', 'no', 'off',
)


def _jitter_coords(lat: float, lng: float, unit_idx: int, seed_str: str, radius_km: float = _JITTER_RADIUS_KM) -> tuple[float, float]:
    """
    Deterministic coordinate jitter for splitting drone groups into individual markers.
    Disabled unless NEPTUN_COORD_JITTER=1 — otherwise returns the same point (no visual "random").
    unit_idx == 0 returns original coords. For i > 0, generates a random offset
    within `radius_km` using a seeded PRNG (mulberry32-style) so offsets are stable.
    """
    if not _COORD_JITTER_ENABLED or unit_idx == 0:
        return (lat, lng)
    # Seeded PRNG (mulberry32)
    seed = (hash(f"{seed_str}_{unit_idx}") & 0xFFFFFFFF)

    def _rand():
        nonlocal seed
        seed = (seed + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((seed ^ (seed >> 15)) * (1 | seed)) & 0xFFFFFFFF
        t = ((t + ((t ^ (t >> 7)) * (61 | t))) ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    angle = _rand() * 2 * math.pi
    r = math.sqrt(_rand()) * radius_km  # sqrt for uniform area distribution
    d_lat = math.cos(angle) * r * _KM_TO_DEG_LAT
    d_lng = math.sin(angle) * r * _KM_TO_DEG_LAT
    return (lat + d_lat, lng + d_lng)


def _geocode_direction_target(
    direction: str,
    oblast: str | None,
    *,
    min_confidence: float = 0.3,
) -> tuple[float, float] | None:
    """
    Geocode a direction target city name to coordinates.
    Uses the same resolver pipeline as main geocoding.
    Returns (lat, lng) or None.
    """
    if not direction or len(direction) < 2:
        return None
    try:
        from geo.resolver import resolve
        entity_dict = {
            'place_name': direction,
            'oblast': oblast,
            'direction': None,
            'near': None,
            'raion': None,
            'threat_type': 'uav',
        }
        resolved = resolve(entity_dict, channel=None, prev_events=[])
        if resolved and resolved.lat != 0 and resolved.confidence >= min_confidence:
            return (resolved.lat, resolved.lng)
    except ImportError:
        pass
    except Exception as e:
        log.debug(f"Direction geocode failed for '{direction}': {e}")

    # Fallback: check OBLAST_CENTERS and LAUNCH_SITES
    direction_lower = direction.lower().strip()
    for key, coords in OBLAST_CENTERS.items():
        if direction_lower.startswith(key) or key.startswith(direction_lower[:4]):
            return coords
    return None


def _apply_oblast_coherence_for_moving_air(
    coords: tuple[float, float] | None,
    region: str | None,
    claimed_oblast: str | None,
    place_name: str | None,
    direction_alt: str | None,
    event_type: str,
    confidence: float,
    resolve_status: str,
    location: str,
) -> tuple[tuple[float, float] | None, str | None, float, str, str]:
    """
    Якщо маркер БПЛА/розвідки/КАБ потрапив за межі розширеного bbox заявленої області —
    повторний геокод у цій області або центр області (занижена впевненість).
    """
    if not coords or not claimed_oblast:
        return coords, region, confidence, resolve_status, location
    try:
        from geo.oblast_coherence import is_moving_air_threat, repair_coords_to_claimed_oblast
        from geo.rules import find_oblast_for_coords, resolve_oblast_bbox_key
    except ImportError:
        return coords, region, confidence, resolve_status, location
    _leg = LEGACY_TYPE_MAP.get(event_type, event_type)
    if not is_moving_air_threat(event_type, _leg):
        return coords, region, confidence, resolve_status, location
    clat, clng = coords[0], coords[1]

    # Якщо place_name сам є назвою області і координати лежать у ній —
    # це правильний результат, навіть якщо claimed_oblast (канальний дефолт) інша.
    _pn = (place_name or '').strip()
    if _pn:
        _pn_ob = resolve_oblast_bbox_key(_pn)
        if _pn_ob and _pn_ob != claimed_oblast:
            _actual_ob = find_oblast_for_coords(clat, clng)
            if _actual_ob and _actual_ob == _pn_ob:
                log.info(
                    f"COHERENCE_SKIP: coords match place_name oblast '{_pn_ob}' "
                    f"(claimed was '{claimed_oblast}') — keeping"
                )
                return coords, _pn_ob, confidence, resolve_status, location

    def _geocode_strict(place: str, ob: str | None) -> tuple[float, float] | None:
        return _geocode_direction_target(place, ob, min_confidence=0.46)

    (nlat, nlng), coh = repair_coords_to_claimed_oblast(
        clat,
        clng,
        claimed_oblast,
        place_name=place_name,
        direction_alt=direction_alt,
        geocode_in_oblast=_geocode_strict,
        fallback_center=_fallback_coords_for_oblast,
    )
    if coh == 'ok':
        return coords, region, confidence, resolve_status, location
    conf_cap = (
        0.52
        if coh in ('oblast_coherence_regeocode', 'oblast_coherence_regeocode_dir')
        else 0.30
    )
    return (
        (nlat, nlng),
        claimed_oblast,
        min(float(confidence or 0), conf_cap),
        coh,
        location if (location and location != 'Unknown') else claimed_oblast,
    )


def _build_trajectory(
    coords: tuple[float, float],
    entities,
    event_type: str,
    region: str | None,
    channel_name: str = '',
    ai_analysis: dict | None = None,
    target_city_coords: tuple[float, float] | None = None,
) -> dict | None:
    """
    Build trajectory dict for a threat marker.
    AI-enhanced fallback chain:
      0. Consensus from multiple channels (2+ channels agree on target)
      1. AI deep analysis (GPT-4o-mini on every message)
      2. Explicit direction from parser (city name → geocode)
      3. Cardinal direction → synthetic target 150km away
      4. Group bearing (from ThreatGroup cluster)
      5. Learned targets (frequency-based from real channel data)
      6. AI trajectory prediction (legacy fallback)
    Returns {"start", "end", "predicted", "source", "prediction_confidence",
            "waypoints", "flight_phase", "origin_coords"} or None.
    """
    lat, lng = coords
    target_coords = None
    predicted = True
    source = 'unknown'
    prediction_confidence = 0.0
    waypoints = None
    flight_phase = 'cruise'
    origin_coords = None

    # Kinematic update: див. process_new_message — один process_observation на повідомлення.

    # ── Pre-0. Target-city coords from GPT target_city field ──
    if target_city_coords and not target_coords:
        target_coords = target_city_coords
        source = 'target_city'
        predicted = False
        prediction_confidence = 0.75
        log.info(f"Trajectory: TARGET_CITY coords ({target_city_coords[0]:.3f}, {target_city_coords[1]:.3f})")

    # ── 0. Consensus from multiple channels ──
    ct = None
    if ct:
        pass

    # ── 1. AI deep analysis (GPT-4o-mini on every message) ──
    if not target_coords and ai_analysis:
        ai_target = ai_analysis.get('target_city')
        if ai_target:
            ai_coords = _geocode_direction_target(ai_target, region)
            if ai_coords:
                target_coords = ai_coords
                source = 'ai_analyzer'
                predicted = True
                prediction_confidence = ai_analysis.get('confidence', 0.6)
                log.info(f"Trajectory: AI analyzer → {ai_target} (conf={prediction_confidence:.2f})")
        # Extract AI metadata regardless of target
        flight_phase = ai_analysis.get('flight_phase', 'cruise')
        if ai_analysis.get('origin_coords'):
            origin_coords = ai_analysis['origin_coords']
        if ai_analysis.get('waypoints'):
            waypoints = ai_analysis['waypoints']

    # ── 2. Explicit direction from parser (city name) ──
    if not target_coords and entities.direction:
        direction_lower = entities.direction.lower().strip()
        cardinal = CARDINAL_DIRECTIONS.get(direction_lower)
        if cardinal:
            bearing_deg = CARDINAL_BEARINGS.get(cardinal)
            if bearing_deg is not None:
                target_coords = _project_point(lat, lng, bearing_deg, 150)
                if target_coords:
                    source = 'cardinal'
                    predicted = False
                    prediction_confidence = 0.75
                    log.info(f"Trajectory: cardinal '{entities.direction}' → {bearing_deg}° [{event_type}]")
        else:
            target_coords = _geocode_direction_target(entities.direction, region)
            if target_coords:
                source = 'direction'
                predicted = False
                prediction_confidence = 0.9
                log.debug(f"Trajectory: direction '{entities.direction}' → {target_coords}")

    # ── 3. Try 'near' field ──
    if not target_coords and entities.near:
        target_coords = _geocode_direction_target(entities.near, region)
        if target_coords:
            source = 'direction'
            predicted = False
            prediction_confidence = 0.8

    # ── 5. Learned targets (frequency-based, persisted on disk) ──
    if not target_coords:
        try:
            from learned_trajectory_targets import suggest_city_for_threat
            lc = suggest_city_for_threat(
                region or '',
                event_type,
                getattr(entities, 'place_name', None),
            )
            if lc:
                target_coords = _geocode_direction_target(lc, region)
                if target_coords:
                    source = 'learned'
                    predicted = True
                    prediction_confidence = 0.42
                    log.info(f"Trajectory: learned → {lc} [{event_type}]")
        except Exception as e:
            log.debug(f'Learned trajectory: {e}')

    # ── 6. AI trajectory prediction (legacy fallback) ──
    if not target_coords:
        ai_result = ai_predict_trajectory(
            lat, lng, event_type, region,
            entities.place_name,
            list(_recent_events)[-20:],
        )
        if ai_result and ai_result.get('target_city'):
            target_city = ai_result['target_city']
            ai_coords = _geocode_direction_target(target_city, region)
            if ai_coords:
                target_coords = ai_coords
                source = ai_result['source']  # 'ai' or 'heuristic'
                predicted = True
                prediction_confidence = ai_result.get('confidence', 0.4)
                log.info(f"Trajectory: {source} → {target_city} (conf={prediction_confidence:.2f})")

    # Apply circling penalty
    # (Removed group tracker circling penalty logic)
    pass

    return _finalize_trajectory(
        lat, lng, target_coords, predicted, source, prediction_confidence,
        event_type, waypoints=waypoints, flight_phase=flight_phase,
        origin_coords=origin_coords, ai_analysis=ai_analysis,
    )


# ── Finalize trajectory replaced by Kinematic Tracking updates ──
def _finalize_trajectory(
    lat: float, lng: float,
    target_coords: tuple[float, float] | None,
    predicted: bool,
    source: str,
    prediction_confidence: float,
    event_type: str = '',
    waypoints: list | None = None,
    flight_phase: str = 'cruise',
    origin_coords: list | None = None,
    ai_analysis: dict | None = None,
) -> dict | None:
    if not target_coords:
        return None
    from geo.track_sanitize import (
        sanitize_origin_coords,
        sanitize_waypoints,
        trajectory_geometry_ok,
    )

    elat = float(target_coords[0])
    elng = float(target_coords[1])
    if not trajectory_geometry_ok(lat, lng, elat, elng, event_type):
        log.warning(
            f"Trajectory rejected: implausible chord or coords "
            f"({lat:.3f},{lng:.3f})→({elat:.3f},{elng:.3f}) [{event_type}] src={source}"
        )
        return None

    wps = sanitize_waypoints(waypoints, event_type)
    oc = sanitize_origin_coords(origin_coords)

    out: dict = {
        'start': [lat, lng],
        'end': [elat, elng],
        'predicted': predicted,
        'source': source,
        'prediction_confidence': prediction_confidence,
        'flight_phase': flight_phase,
    }
    if wps and len(wps) >= 2:
        out['waypoints'] = wps
    if oc is not None:
        out['origin_coords'] = oc
    return out


def _project_point(lat: float, lng: float, bearing_deg: float, distance_km: float) -> tuple[float, float]:
    """Project a point from (lat, lng) at given bearing and distance."""
    import math
    R = 6371.0
    d = distance_km / R
    brng = math.radians(bearing_deg)
    lat1 = math.radians(lat)
    lng1 = math.radians(lng)
    lat2 = math.asin(math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(brng))
    lng2 = lng1 + math.atan2(math.sin(brng) * math.sin(d) * math.cos(lat1),
                              math.cos(d) - math.sin(lat1) * math.sin(lat2))
    return (math.degrees(lat2), math.degrees(lng2))


# Map parser event_type to frontend icon names (must match THREAT_ICONS keys)
LEGACY_TYPE_MAP = {
    'uav': 'shahed',
    'recon': 'rozved',        # rozvedka2.png
    'missile': 'raketa',
    'ballistic': 'ballistic', # distinct icon for ballistic missiles
    'explosion': 'vibuh',
    'launch': 'pusk',
    'kab': 'kab',
    'avia': 'avia',            # phantom aviation marker (auto-generated)
    'alert': 'alarm',          # not used as marker (skipped), but mapped correctly
    'allclear': 'alarm_cancel',
}


def _resolve_airfield(region: str | None, direction: str | None) -> tuple[str, float, float] | None:
    """Find nearest tactical aviation airfield for KAB/avia phantom marker.
    Tries oblast-based mapping first, then cardinal direction fallback."""
    from core.parser_v2 import CARDINAL_DIRECTIONS
    # 1. Try by oblast
    if region:
        region_lower = region.lower()
        for stem, airfield_data in KAB_AIRFIELDS.items():
            if stem in region_lower or region_lower.startswith(stem):
                return airfield_data
    # 2. Try by cardinal direction
    if direction:
        direction_lower = direction.lower().strip()
        cardinal = CARDINAL_DIRECTIONS.get(direction_lower)
        if cardinal and cardinal in CARDINAL_AIRFIELDS:
            return CARDINAL_AIRFIELDS[cardinal]
    return None


def _spawn_phantom_avia(
    kab_coords: tuple[float, float] | None,
    region: str | None,
    direction: str | None,
    msg_text: str,
    channel_id: int,
    channel_name: str,
    channel_meta: dict,
    now_iso: str,
    parent_threat_id: str,
) -> dict | None:
    """Create a phantom 'avia' marker at the nearest Russian airfield
    when KAB/tactical aviation activity is detected."""
    airfield = _resolve_airfield(region, direction)
    if not airfield:
        log.debug(f"Phantom avia: no airfield found for region={region}, direction={direction}")
        return None

    airfield_name, af_lat, af_lng = airfield
    avia_id = f"avia_{parent_threat_id}"

    # Build trajectory from airfield toward KAB impact zone
    trajectory_data = None
    course_bearing = None
    distance_km = None
    if kab_coords:
        course_bearing = round(_compute_bearing(af_lat, af_lng, kab_coords[0], kab_coords[1]), 1)
        distance_km = round(_haversine_km(af_lat, af_lng, kab_coords[0], kab_coords[1]), 1)
        if 20 < distance_km < 800:
            trajectory_data = {
                'start': [af_lat, af_lng],
                'end': [kab_coords[0], kab_coords[1]],
                'predicted': False,
                'source': 'airfield',
                'prediction_confidence': 0.85,
            }

    avia_data = {
        'id': avia_id,
        'type': 'avia',
        'threat_type': 'avia',
        'location': airfield_name,
        'place': f'✈ {airfield_name}',
        'region': region,
        'text': msg_text,
        'lat': af_lat,
        'lng': af_lng,
        'channel_id': channel_id,
        'channel_name': channel_name,
        'channel_priority': channel_meta.get('priority', 3),
        'msg_id': 0,
        'count': 1,
        'ts': now_iso,
        'date': now_iso,
        'confidence': 0.9,
        'resolve_status': 'phantom_avia',
        'candidates': [],
        'resolver_version': 'v2',
        'trajectory': trajectory_data,
        'trajectory_source': 'airfield' if trajectory_data else None,
        'prediction_confidence': 0.85 if trajectory_data else None,
        'course_bearing': course_bearing,
        'course_direction': direction,
        'speed_kmh': 900,
        'distance_km': distance_km,
        'origin': None,
    }

    log.info(f"Phantom avia: {airfield_name} ({af_lat:.3f}, {af_lng:.3f}) for KAB → {region or direction}")
    return avia_data


async def process_new_message(event):
    """
    Core processing pipeline (GPT-primary):
    1. Deduplication (message-level — exact msg_id only)
    2. Pre-filter (spam/summary/negation — no API cost)
    3. GPT-4o-mini entity extraction (primary) with regex fallback
    4. Allclear safety cross-check (regex keywords vs GPT)
    5. Chain tracking (link follow-up messages to existing markers)
    6. Geo resolution
    7. State update (Redis + POST to web service)
    """
    msg_text = event.message.message
    if not msg_text:
        return

    # Drop stale messages delivered after worker restart (Telegram backlog)
    MAX_MESSAGE_AGE_SEC = 300  # 5 minutes
    msg_date = event.message.date
    if msg_date:
        now_utc = datetime.now(timezone.utc)
        if msg_date.tzinfo is None:
            msg_date = msg_date.replace(tzinfo=timezone.utc)
        age_sec = (now_utc - msg_date).total_seconds()
        if age_sec > MAX_MESSAGE_AGE_SEC:
            log.info(f"DROP [stale]: message {age_sec:.0f}s old from {event.chat_id}")
            return

    channel_id = event.chat_id
    msg_id = event.message.id
    channel_name = await _resolve_channel_name(event)
    channel_meta = CHANNEL_META.get(channel_name, {'priority': 3, 'format': 'semi', 'name': channel_name})

    if channel_name == KHERSON_NON_DRONE_CH:
        msg_text = normalize_kherson_non_drone_message(msg_text)

    is_edit = getattr(event.message, 'edit_date', None) is not None
    log.info(f"MSG [{channel_name}]{' [EDIT]' if is_edit else ''}: {msg_text[:100]}")

    # Extract reply-to message ID for chain tracking
    reply_to_msg_id = None
    if event.message.reply_to:
        reply_to_msg_id = event.message.reply_to.reply_to_msg_id

    # 1. Message-level deduplication (skip for edited messages — content changed)
    if not is_edit and db.is_message_processed(channel_id, msg_id):
        await _publish_feed_event(
            status='skipped', channel_name=channel_name, msg_text=msg_text,
            channel_id=channel_id, msg_id=msg_id, reason='already processed (msg dedup)',
        )
        return
    db.mark_message_processed(channel_id, msg_id)

    # 2. GPT-primary pipeline with regex fallback
    # Step 2a: Fast pre-filter (spam, summaries, negations) — no API cost
    if is_skip_message(msg_text):
        log.debug(f"FILTER [{channel_name}]: skipped: {msg_text[:80]}")
        await _publish_feed_event(
            status='skipped', channel_name=channel_name, msg_text=msg_text,
            channel_id=channel_id, msg_id=msg_id, reason='pre-filter (spam/summary)',
        )
        return

    # Step 2b: Extract header oblast for GPT context
    header_oblast = extract_header_oblast(msg_text)

    # Step 2b+: Early chain lookup for reply context (before GPT call)
    # If this message is a reply, inject parent context into GPT prompt
    _parent_context_str = None
    if reply_to_msg_id:
        _early_parent = chain_tracker.find_parent(
            channel_id=channel_id,
            reply_to_msg_id=reply_to_msg_id,
            event_type='uav',  # placeholder — reply_to match ignores event_type
        )
        if _early_parent:
            _parent_context_str = _early_parent.to_context_string()
            log.info(f"REPLY_CONTEXT [{channel_name}]: msg reply_to={reply_to_msg_id} → {_parent_context_str}")

    # Step 2c: GPT parse (primary)
    gpt_result = None
    try:
        gpt_result = await asyncio.to_thread(
            gpt_parse_message, msg_text, channel_name, header_oblast, _parent_context_str
        )
    except Exception as e:
        log.warning(f"GPT parser exception (non-fatal): {e}")

    # Step 2d: Convert GPT results to ParsedEntities, or fallback to regex
    if gpt_result is not None:
        gpt_entities, gpt_is_threat = gpt_result
        _gpt_raw_len = len(gpt_entities or [])
        all_entities = gpt_to_parsed_entities(gpt_entities, msg_text)
        # Safety cross-check: if regex allclear keywords detected but GPT missed allclear
        if detect_allclear_keywords(msg_text):
            has_allclear = any(e.is_allclear for e in all_entities)
            if not has_allclear:
                from core.parser_v2 import ParsedEntities, extract_oblast_authority
                ac_oblast = header_oblast or extract_oblast_authority(msg_text)
                all_entities.append(ParsedEntities(
                    event_type='allclear',
                    oblast=ac_oblast,
                    raw_text=msg_text[:200],
                    is_allclear=True,
                ))
                log.info(f"ALLCLEAR_CROSSCHECK [{channel_name}]: forced allclear for {ac_oblast}")
        if all_entities:
            log.info(f"GPT_PRIMARY [{channel_name}]: {len(all_entities)} entities: "
                     f"{[e.event_type for e in all_entities]}")
        elif gpt_is_threat and _gpt_raw_len == 0:
            # GPT said is_threat=true but returned zero raw entities → parsing glitch, try regex
            all_entities = extract_all_entities(msg_text)
            if all_entities:
                log.warning(f"GPT_EMPTY_FALLBACK [{channel_name}]: regex recovered → "
                            f"{len(all_entities)} entities: {[e.event_type for e in all_entities]}")
        elif gpt_is_threat and _gpt_raw_len > 0:
            # GPT повернув JSON-сутності, але після санітизації/фільтрів лишилось 0 — не піднімати regex
            log.info(
                f"GPT_ALL_STRIPPED [{channel_name}]: raw={_gpt_raw_len} entities → 0 usable "
                f"(sanitize/filter); skip regex fallback"
            )
        elif (
            channel_meta.get('priority') == 1
            and channel_meta.get('format') == 'structured'
            and _gpt_raw_len == 0
        ):
            # UkraineAlarmSignal, povitryanatrivogaaa: critical alerts must not be dropped
            # "🛸 Яготин (Київська обл.) Загроза застосування БПЛА" — GPT may return empty
            all_entities = extract_all_entities(msg_text)
            if all_entities:
                log.warning(f"GPT_EMPTY_FORCE_FALLBACK [{channel_name}]: regex recovered → "
                            f"{len(all_entities)} entities: {[e.event_type for e in all_entities]}")
        # else: GPT explicitly said is_threat=false → do NOT fall back to regex, keep all_entities=[]
    else:
        # GPT failed (timeout/error) → full regex fallback
        gpt_entities = None  # ensure defined for parser= in _publish_feed_event
        all_entities = extract_all_entities(msg_text)
        if all_entities:
            log.warning(f"GPT_FAIL [{channel_name}]: using regex fallback → "
                        f"{len(all_entities)} entities")
        else:
            log.warning(f"GPT_FAIL [{channel_name}]: regex also empty for: {msg_text[:80]}")

    if not all_entities:
        log.debug(f"DROP [{channel_name}]: both parsers returned empty for: {msg_text[:80]}")
        await _publish_feed_event(
            status='dropped', channel_name=channel_name, msg_text=msg_text,
            channel_id=channel_id, msg_id=msg_id, reason='both parsers empty',
            parser='both_empty',
        )
        return

    # Skip negation-only messages
    if len(all_entities) == 1 and all_entities[0].is_negation:
        await _publish_feed_event(
            status='skipped', channel_name=channel_name, msg_text=msg_text,
            channel_id=channel_id, msg_id=msg_id, reason='negation-only',
        )
        return

    now_kyiv = datetime.now(KYIV_TZ)

    for entities in all_entities:
        # Skip negations and bare alerts
        if entities.is_negation:
            continue

        # After merge, unknown entities only remain if BOTH parsers failed
        if entities.event_type == 'unknown':
            log.debug(f"DROP [{channel_name}]: unknown type after merge: {entities.raw_text[:60]}")
            await _publish_feed_event(
                status='dropped', channel_name=channel_name, msg_text=msg_text,
                channel_id=channel_id, msg_id=msg_id, reason='unknown type after merge',
                threat_type='unknown',
            )
            continue
        if entities.is_allclear:
            oblast = entities.oblast
            if not oblast:
                from core.parser_v2 import extract_oblast_authority
                oblast = extract_oblast_authority(msg_text)
            threat_types = [entities.cleared_threat_type] if entities.cleared_threat_type else None
            if oblast:
                # Remove existing markers for this oblast from the map
                _clear_types = None
                if threat_types:
                    _clear_types = [LEGACY_TYPE_MAP.get(t, t) for t in threat_types]
                _place_filter: str | None = None
                if channel_name == KHERSON_NON_DRONE_CH:
                    _place_filter = extract_kherson_non_drone_place_hint(msg_text) or (
                        (entities.place_name or "").strip() or None
                    )
                    if _place_filter and len(_place_filter.strip()) < 3:
                        _place_filter = None
                await _clear_region_markers(oblast, _clear_types, place_contains=_place_filter)
            else:
                log.info(f"ALL-CLEAR from {channel_name} (no oblast): {entities.raw_text[:80]}")
            await _publish_feed_event(
                status='processed', channel_name=channel_name, msg_text=msg_text,
                channel_id=channel_id, msg_id=msg_id, threat_type='allclear',
                region=oblast, place=entities.place_name,
            )
            continue
        if entities.event_type == 'alert':
            log.debug(f"ALERT skip (shown via SVG): {entities.place_name} ({entities.oblast})")
            await _publish_feed_event(
                status='skipped', channel_name=channel_name, msg_text=msg_text,
                channel_id=channel_id, msg_id=msg_id, reason='alert (shown via SVG)',
                threat_type='alert', region=entities.oblast, place=entities.place_name,
            )
            continue

        # ── Post-GPT type correction ──────────────────────────────────
        # GPT sometimes classifies drone chains as 'pusk'. If text has clear
        # drone indicators and NO missile keywords, override type to 'uav'.
        if entities.event_type == 'pusk':
            _drone_kw = re.search(r'ланцюг|ланцюгом|бпла|шахед|shahed|дрон', msg_text, re.IGNORECASE)
            _missile_kw = re.search(r'ракет|балістик|пуск|ту-95|ту-160|калібр|кінжал|Х-|крилат', msg_text, re.IGNORECASE)
            if _drone_kw and not _missile_kw:
                log.info(f"TYPE_FIX [{channel_name}]: pusk → uav (drone keyword '{_drone_kw.group()}', no missile context)")
                entities.event_type = 'uav'

        # ── Clean place_name: strip directional prefixes ──────────────
        if entities.place_name:
            _cleaned = re.sub(
                r'^(?:курс(?:ом)?\s+на\s+|напрямку?\s+(?:на\s+)?|у\s+бік\s+|в\s+бік\s+|в\s+район[іу]?\s+)',
                '', entities.place_name, flags=re.IGNORECASE
            ).strip()
            if _cleaned and _cleaned != entities.place_name:
                log.info(f"PLACE_CLEAN [{channel_name}]: '{entities.place_name}' → '{_cleaned}'")
                entities.place_name = _cleaned

        # ── NLP Augmentation ─────────────────────────────────────────
        try:
            from core.parser_nlp import augment_parsed_entities_with_nlp
            _nlp_place = augment_parsed_entities_with_nlp(entities.raw_text or msg_text, entities.place_name)
            if _nlp_place != entities.place_name:
                log.info(f"PLACE_NLP_AUGMENT [{channel_name}]: '{entities.place_name}' → '{_nlp_place}'")
                entities.place_name = _nlp_place
        except ImportError:
            pass

        # ── Reject generic non-place words from GPT ──────────────────
        _GENERIC_NON_PLACES = {
            'місто', 'міста', 'містом', 'містах', 'містечко',
            'район', 'району', 'районі', 'районом',
            'область', 'області', 'областю',
            'село', 'села', 'селом', 'селі',
            'селище', 'селища', 'селищем',
            'центр', 'центру', 'околиці', 'околиця',
            'передмістя', 'приміська', 'приміський',
            'unknown', 'невідомо',
        }
        if entities.place_name and entities.place_name.lower().strip() in _GENERIC_NON_PLACES:
            log.info(f"PLACE_REJECT [{channel_name}]: '{entities.place_name}' is a generic word, not a place name")
            entities.place_name = None

        if entities.place_name:
            _guarded, _ok = validate_place_candidate(entities.place_name, gazetteer_hit=False)
            if not _ok:
                log.info(
                    f"PLACE_GUARD [{channel_name}]: reject non-toponym token {entities.place_name!r}"
                )
                entities.place_name = None
            else:
                entities.place_name = _guarded

        if channel_name == KHERSON_NON_DRONE_CH:
            _kh_hint = extract_kherson_non_drone_place_hint(msg_text)
            _pn = (entities.place_name or "").strip()
            if _kh_hint and (len(_pn) < 3 or _pn.lower() in _GENERIC_NON_PLACES):
                log.info(f"KHERSON_PLACE_HINT [{channel_name}]: '{_pn or '(empty)'}' → '{_kh_hint}'")
                entities.place_name = _kh_hint

        # Recon/дорозвідка suppresses UAV groups
        # Oblast-level "дорозвідка" (keyword present, no place_name) = allclear for UAVs
        # Place-level recon = suppress at place only (still ingest marker)
        # Generic recon without "дорозвідк" keyword = regular recon sighting (ingest marker)
        if entities.event_type == 'recon' and entities.oblast:
            _is_dorozvidka = bool(re.search(r'дорозвідк', msg_text, re.IGNORECASE))
            if not entities.place_name and _is_dorozvidka:
                # Oblast-level дорозвідка — clear all UAV markers in this oblast
                await _clear_region_markers(entities.oblast, ['shahed', 'rozved'])
                log.info(f"RECON-ALLCLEAR [{channel_name}]: cleared UAVs in {entities.oblast}")
                await _publish_feed_event(
                    status='processed', channel_name=channel_name, msg_text=msg_text,
                    channel_id=channel_id, msg_id=msg_id, threat_type='recon',
                    region=entities.oblast, place=entities.place_name,
                )
                continue
            # Recon marker with place_name still gets ingested below (shown on map as rozvedka2.png)

        # 3. Chain tracking: find parent for follow-up messages.
        # Used for chain-tracking (linking replies to existing markers).
        # No dedup — every message gets fully processed. Server-side Spatial
        # Correlator handles merging nearby markers of the same type.
        _pre_dup_parent = chain_tracker.find_parent(
            channel_id=channel_id,
            reply_to_msg_id=reply_to_msg_id,
            event_type=entities.event_type,
            place=entities.place_name,
            oblast=entities.oblast or '',
            origin=getattr(entities, 'origin', None),
            raw_text=msg_text,
            exclude_msg_id=msg_id if len(all_entities) > 1 else None,
        )
        if _pre_dup_parent:
            log.info(
                f"CHAIN_PARENT [{channel_name}]: {entities.event_type} @ "
                f"Chain match (followup): '{msg_text[:50]}...' → marker="
                f"{getattr(_pre_dup_parent, 'marker_id', '?')}"
            )

        # 4. Resolve location via GeoResolver pipeline
        # Channel-default oblast boosts geocoding but must NOT alone trigger the hard oblast bbox gate
        # (wrong lock-in if the channel default is generic). Gate uses parser oblast or "(… область)" in text.
        _ent_dict = entities.to_entities_dict()
        if channel_name == KHERSON_NON_DRONE_CH:
            _ent_dict['geo_city_hint'] = KHERSON_GEO_CITY_HINT
        _oblast_from_explicit_paren = False
        # Явна область у дужках у тексті — завжди сильніша за GPT (раніше ігнорувалась, якщо GPT вже підставив область).
        # Дужки + скорочення «обл.»; підтримка дефіса (Івано-Франківська)
        _region_paren = re.search(
            r'\((?:Республіка\s+)?([\s\-А-ЯІЇЄҐа-яіїєґ]+?(?:\s+область|\s+обл\.?)?)\)',
            msg_text,
            re.IGNORECASE,
        )
        if _region_paren:
            _explicit_region = _region_paren.group(1).strip()
            for _stem, _full in OBLAST_NORMALIZATION.items():
                if _stem in _explicit_region.lower():
                    _ent_dict['oblast'] = _full
                    _oblast_from_explicit_paren = True
                    log.debug(f"Explicit region from parentheses: '{_explicit_region}' → {_full}")
                    break
        # Повна назва області в тексті (без дужок) — сильніший сигнал за GPT; не перекриває дужки.
        # BUT: skip this override when the parser already assigned a per-section oblast
        # (multi-entity messages with section headers like "Сумщина:" / "Вінниччина:").
        # find_explicit_oblast_mention scans the FULL message and would pick up a random
        # "Запорізька область:" section header, incorrectly applying it to ALL entities.
        _oblast_from_explicit_text = False
        _parser_provided_oblast = (_ent_dict.get('oblast') or '').strip()
        if not _oblast_from_explicit_paren and not _parser_provided_oblast:
            try:
                from geo.oblast_coherence import find_explicit_oblast_mention
                _ob_mentioned = find_explicit_oblast_mention(msg_text)
                if _ob_mentioned:
                    _ent_dict['oblast'] = _ob_mentioned
                    _oblast_from_explicit_text = True
                    log.debug(f"Explicit oblast in message body: → {_ob_mentioned}")
            except ImportError:
                pass
        _oblast_explicit_any = _oblast_from_explicit_paren or _oblast_from_explicit_text
        # Якщо place_name сам є назвою області — не дозволяти каналу перекривати
        _pn_as_oblast = None
        if not _oblast_explicit_any:
            _pn_raw = (_ent_dict.get('place_name') or '').strip()
            if _pn_raw:
                try:
                    from geo.rules import resolve_oblast_bbox_key
                    _pn_as_oblast = resolve_oblast_bbox_key(_pn_raw)
                except ImportError:
                    pass
                if _pn_as_oblast:
                    _ent_dict['oblast'] = _pn_as_oblast
                    _oblast_explicit_any = True
                    log.debug(f"place_name IS an oblast name: '{_pn_raw}' → {_pn_as_oblast}")
        _oblast_gate_hint = (_ent_dict.get('oblast') or '').strip() or None
        if not _ent_dict.get('oblast') and channel_name in CHANNEL_DEFAULT_OBLAST:
            _ent_dict['oblast'] = CHANNEL_DEFAULT_OBLAST[channel_name]
            log.debug(f"Injecting channel-default oblast hint: {_ent_dict['oblast']} for {channel_name}")
            _oblast_gate_hint = (_ent_dict.get('oblast') or '').strip() or None
        # Регіональні канали (eyes_everywhere → Запоріжжя): GPT часто «переносить» топонім в іншу область-омонім.
        # Без явних дужок у тексті — геокодимо рухомі загрози в «домашній» області каналу, не в Чернівцях тощо.
        # КАБ/ракети не форсуємо «домашньою» областю каналу — лише БПЛА/розвідка.
        _REGIONAL_CHANNEL_MOVING = frozenset({'uav', 'recon', 'fpv', 'drone'})
        if (
            channel_name in CHANNEL_DEFAULT_OBLAST
            and not _oblast_explicit_any
            and entities.event_type in _REGIONAL_CHANNEL_MOVING
        ):
            _home_ob = CHANNEL_DEFAULT_OBLAST[channel_name]
            _cur_ob = (_ent_dict.get('oblast') or '').strip()
            if _cur_ob and _cur_ob != _home_ob:
                log.warning(
                    f"CHANNEL_HOME_OBLAST [{channel_name}]: parser/GPT oblast '{_cur_ob}' → '{_home_ob}' "
                    f"for moving threat ({entities.event_type}); no explicit (…)область in text"
                )
                _ent_dict['oblast'] = _home_ob
                _oblast_gate_hint = _home_ob
        resolved = None
        try:
            from geo.resolver import resolve
            resolved = resolve(
                _ent_dict,
                channel=channel_name,
                prev_events=list(_recent_events)[-10:],
                oblast_gate_hint=_oblast_gate_hint,
            )
        except ImportError:
            log.warning("geo.resolver not available")
        except Exception as e:
            log.error(f"Resolver error: {e}", exc_info=True)

        # Debug: log resolver return value for diagnostics
        if resolved:
            log.info(
                f"RESOLVER_RESULT [{channel_name}]: place={resolved.place_name} "
                f"lat={resolved.lat} lng={resolved.lng} conf={resolved.confidence:.2f} "
                f"status={resolved.status}"
            )

        # Build output data
        threat_id = f"evt_{int(now_kyiv.timestamp())}_{str(uuid.uuid4())[:4]}"
        now_iso = now_kyiv.isoformat()

        raion_name = None
        _used_launch_site = False
        # For launch/kab/avia etc., place_name may be a Russian airfield (e.g. Морозовськ, Єйськ).
        # Prefer LAUNCH_SITES over resolver — resolver penalizes outside-Ukraine and yields wrong coords.
        # IMPORTANT: Only check for uav/shahed/drone types — those place_names are Ukrainian cities,
        # NOT launch sites. Calling _geocode_origin on them triggers its fallback resolver which
        # geocodes ANY city, falsely activating LAUNCH_SITE override (e.g. Переяслав → launch site).
        _LAUNCH_EVENT_TYPES = {'launch', 'pusk', 'missile', 'ballistic', 'balistic', 'kab', 'avia', 'raketa'}
        _launch_coords = _geocode_origin(entities.place_name or '') if entities.event_type in _LAUNCH_EVENT_TYPES else None
        if _launch_coords:
            location = entities.place_name or 'Unknown'
            region = (
                getattr(entities, 'origin', None) or 'АР Крим'
                if entities.event_type == 'launch'
                else (entities.oblast or resolved.oblast if resolved else None)
            )
            coords = _launch_coords
            confidence = 0.85
            resolve_status = 'launch_site'
            candidates_json = []
            raion_name = None
            _used_launch_site = True
            log.info(f"LAUNCH_SITE override: {location} → {coords}")

        if not _used_launch_site and resolved and resolved.lat != 0 and resolved.confidence >= _min_trusted_resolver_conf():
            location = resolved.place_name
            region = resolved.oblast
            coords = (resolved.lat, resolved.lng)
            confidence = resolved.confidence
            resolve_status = resolved.status
            candidates_json = [c.to_dict() for c in resolved.chosen_from[:3]]
            raion_name = resolved.raion
            # Major gazetteer hit: slight boost so borderline resolver scores still map
            if resolved.chosen_from and confidence < MIN_CONFIDENCE_THRESHOLD + 0.05:
                best = resolved.chosen_from[0]
                if (getattr(best, 'source', '') or '').startswith('gazetteer') and getattr(best, 'population', 0) >= 50000:
                    confidence = max(confidence, min(0.55, MIN_CONFIDENCE_THRESHOLD + 0.12))
                    log.info(f"Gazetteer major city boost: {location} (pop={best.population}) → conf={confidence:.2f}")

            # «на Житомирщині» + place Житомир = область, не центр міста (GPT/газетиєр люблять обласний центр)
            _pn_check = (getattr(entities, 'place_name', None) or '') or (resolved.place_name or '')
            try:
                from geo.oblast_coherence import is_moving_air_threat

                _leg_ty = LEGACY_TYPE_MAP.get(entities.event_type, entities.event_type)
                if (
                    regional_oblast_nickname_covers_place(msg_text, _pn_check)
                    and is_moving_air_threat(entities.event_type, _leg_ty)
                ):
                    _ob_ctx = (_ent_dict.get('oblast') or region or '').strip()
                    _alt_gc = None
                    _alt_label = None
                    for cand in filter(None, [getattr(entities, 'direction', None), getattr(entities, 'near', None)]):
                        cs = str(cand).strip()
                        if len(cs) < 3:
                            continue
                        if cs.lower() in CARDINAL_DIRECTIONS:
                            continue
                        _g = _geocode_direction_target(cs, _ob_ctx or None, min_confidence=0.32)
                        if _g:
                            _alt_gc = _g
                            _alt_label = cs
                            break
                    if _alt_gc:
                        coords = _alt_gc
                        location = _alt_label or location
                        confidence = min(float(confidence), 0.72)
                        resolve_status = 'regional_oblast_direction_target'
                        log.info(
                            f"REGIONAL-NOT-CITY [{channel_name}]: -щин(а) у тексті, "
                            f"було «{entities.place_name!r}» як місто → ціль напрямку "
                            f"{location!r} ({coords[0]:.3f},{coords[1]:.3f})"
                        )
                    elif _ob_ctx:
                        fb = _fallback_coords_for_oblast(_ob_ctx)
                        if fb:
                            coords = fb
                            location = _ob_ctx
                            confidence = min(float(confidence), 0.48)
                            resolve_status = 'regional_oblast_centroid'
                            log.info(
                                f"REGIONAL-NOT-CITY [{channel_name}]: -щин(а), без геокоду напрямку → "
                                f"центроїд {_ob_ctx}"
                            )
            except Exception as e:
                log.debug(f"regional_oblast_nickname override skipped: {e}")
        else:
            location = entities.place_name or 'Unknown'
            # Після CHANNEL_HOME_OBLAST у _ent_dict уже правильніша область, ніж у entities.oblast
            region = (_ent_dict.get('oblast') or '').strip() or entities.oblast
            coords = None
            confidence = 0.0
            resolve_status = 'rejected' if resolved else 'no_resolver'
            candidates_json = []

        # Drop resolver point when status is ambiguous (two+ candidates) — less false precision
        if (
            _OMIT_AMBIGUOUS_COORDS
            and not _used_launch_site
            and resolved
            and getattr(resolved, 'status', None) == 'ambiguous'
            and getattr(resolved, 'chosen_from', None)
            and len(resolved.chosen_from) >= 2
            and coords
        ):
            log.info(
                f"NEPTUN_OMIT_COORDS_ON_AMBIGUOUS: clearing coords "
                f"(place={resolved.place_name!r}, n_cand={len(resolved.chosen_from)})"
            )
            coords = None
            resolve_status = 'ambiguous_no_point'
            confidence = min(confidence, 0.28)

        # Channel-default oblast: regional channels that don't mention oblast in text
        if not region and channel_name in CHANNEL_DEFAULT_OBLAST:
            region = CHANNEL_DEFAULT_OBLAST[channel_name]
            log.debug(f"Using channel-default oblast: {region} for {channel_name}")

        # ── Estimated-offset: shift marker from target to estimated current position ──
        # Must run BEFORE oblast fallback so target_city offset takes priority
        _target_coords = None
        _target_city = getattr(entities, 'target_city', None)
        if not _target_city and entities.direction:
            _dir_lower = entities.direction.lower().strip()
            if _dir_lower not in CARDINAL_DIRECTIONS:
                from core.parser_v2 import normalize_place_case
                _target_city = normalize_place_case(entities.direction)
        _origin_raw = getattr(entities, 'origin', None)

        # Normalize target_city and origin via ORIGIN_NORMALIZATION so "Полтавщина"→"Полтава",
        # "Сумщина"→"Суми" — geocoders need city names, not oblique oblast forms
        from core.parser_v2 import ORIGIN_NORMALIZATION, OBLAST_DIRECTION_KEYS
        _target_from_direction_only = bool(not getattr(entities, 'target_city', None) and entities.direction)
        _direction_is_oblast_only = (
            _target_from_direction_only and entities.direction
            and entities.direction.lower().strip() in OBLAST_DIRECTION_KEYS
        )
        if _target_city:
            _tc_lower = _target_city.lower().strip()
            for _k, _canon in ORIGIN_NORMALIZATION.items():
                if _tc_lower == _k or _tc_lower.startswith(_k):
                    _target_city = _canon
                    break
        # "у напрямку Черкащини/Вінниччини" = oblast, NOT city — НІКОЛИ не ставити метку в цільовій області.
        # Маркер має бути в поточному місці (place_name) або області (region), не в напрямку руху.
        _msg_lower = msg_text.lower()
        _target_is_oblast_from_msg = (
            _target_city and region
            and any(
                _k in _msg_lower and _target_city and _target_city.lower() == _canon.lower()
                for _k, _canon in ORIGIN_NORMALIZATION.items()
                if _k in OBLAST_DIRECTION_KEYS
            )
        )
        if _direction_is_oblast_only or _target_is_oblast_from_msg:
            # Only suppress if we DON'T have a clear origin. If we have an origin,
            # we WANT the trajectory from origin to this target oblast.
            if not _origin_raw:
                _target_city = None  # Не використовувати target-offset — маркер не в цільовій області
            
            if not coords and region:
                # Спочатку спробувати place_name (де зараз), потім центр поточної області
                if entities.place_name:
                    _gc = _geocode_direction_target(entities.place_name, region)
                    if _gc:
                        coords = _gc
                        location = entities.place_name
                        confidence = max(confidence, 0.5)
                        resolve_status = 'oblast_direction_place'
                        log.info(
                            f"OBLAST-DIRECTION [{channel_name}]: direction='{entities.direction}' (oblast), "
                            f"placing at place_name '{entities.place_name}' ({coords[0]:.3f},{coords[1]:.3f})"
                        )
                if not coords:
                    coords = _fallback_coords_for_oblast(region)
                    if coords:
                        location = region
                        confidence = max(confidence, 0.3)
                        resolve_status = 'oblast_direction_only'
                        log.info(
                            f"OBLAST-DIRECTION [{channel_name}]: '{entities.direction}' = oblast, "
                            f"placing at {region} ({coords[0]:.3f},{coords[1]:.3f}) "
                            f"(coarse centroid — may be hidden on map by confidence cap)"
                        )
        if _origin_raw:
            _orig_lower = _origin_raw.lower().strip()
            for _k, _canon in ORIGIN_NORMALIZATION.items():
                if _orig_lower == _k or _orig_lower.startswith(_k):
                    _origin_raw = _canon
                    break

        # Auto-promote: if origin is set + place_name resolved + no target_city,
        # the "place" is likely the TARGET (e.g. "→Полтава з Харківщини").
        # Promote place_name → target_city so estimated-offset fires.
        if _origin_raw and not _target_city and entities.place_name and coords:
            _has_arrow = any(c in msg_text for c in '→➡►▶')
            _has_from_pattern = bool(re.search(
                r'\bз\s+[А-ЯІЇЄҐа-яіїєґ]+(?:щини|щину|ської|зької|області)',
                msg_text, re.IGNORECASE
            ))
            if _has_arrow or _has_from_pattern:
                _target_city = entities.place_name
                entities.target_city = _target_city
                coords = None  # clear resolved coords — let estimated-offset place it correctly
                log.info(
                    f"AUTO-PROMOTE [{channel_name}]: place_name '{entities.place_name}' → "
                    f"target_city (origin='{_origin_raw}', arrow={_has_arrow})"
                )

        if _target_city and not coords:
            # Case B: No place_name resolved — use target_city + reverse offset
            _tc = _geocode_direction_target(_target_city, region)
            if _tc:
                _target_coords = _tc

                # ── RETARGET is handled by TrackManager.associate_observation now ──
                pass

                # Bearing priority: 1) GPT/cardinal, 2) origin→target, 3) infer from wave analysis
                bearing_to_target = _direction_to_bearing(entities)
                if bearing_to_target is None:
                    if _origin_raw:
                        _oc = _geocode_origin(_origin_raw, allow_resolver_fallback=True)
                        if _oc:
                            bearing_to_target = _compute_bearing(
                                _oc[0], _oc[1], _tc[0], _tc[1]
                            )
                            log.info(
                                f"EST: origin '{_origin_raw}' ({_oc[0]:.2f},{_oc[1]:.2f}) "
                                f"→ target bearing {bearing_to_target:.1f}°"
                            )

                # Fallback 3: infer bearing from recent events (same region) — optional (weak signal)
                if (
                    _RECENT_EVENTS_BEARING
                    and bearing_to_target is None
                    and region
                ):
                    for evt in reversed(list(_recent_events)[-15:]):
                        evt_lat, evt_lng = evt.get('lat'), evt.get('lng')
                        if evt_lat is not None and evt_lng is not None:
                            evt_region = evt.get('region') or ''
                            if evt_region and region and evt_region != region:
                                continue
                            dist_km = _haversine_km(evt_lat, evt_lng, _tc[0], _tc[1])
                            if 20 < dist_km < 400:  # plausible same-threat distance
                                bearing_to_target = _compute_bearing(
                                    evt_lat, evt_lng, _tc[0], _tc[1]
                                )
                                log.info(
                                    f"EST: recent event ({evt_lat:.2f},{evt_lng:.2f}) "
                                    f"→ target bearing {bearing_to_target:.1f}° (dist={dist_km:.0f}km)"
                                )
                                break

                if bearing_to_target is not None:
                    # Use ORIGIN coords (where threat was observed) instead of target-offset.
                    # Target-offset placed marker 15-20km from target → often in target oblast
                    # with no alarm, causing confusion ("marker under Kyiv but no alarm there").
                    # Origin = реальне місце виявлення (Черкащина), trajectory показує напрям.
                    if _origin_raw:
                        _oc = _geocode_origin(_origin_raw, allow_resolver_fallback=True)
                        if _oc:
                            # Place along great-circle origin→target, not only at origin centroid
                            try:
                                from geo.resolver import point_along_great_circle
                                _traj_frac = float(os.getenv('NEPTUN_TRAJECTORY_FRACTION', '0.10'))
                            except ValueError:
                                _traj_frac = 0.10
                            _seg_km = _haversine_km(_oc[0], _oc[1], _tc[0], _tc[1])
                            if _seg_km > 3.0:
                                _plat, _plng = point_along_great_circle(
                                    _oc[0], _oc[1], _tc[0], _tc[1], _traj_frac
                                )
                                coords = (_plat, _plng)
                                resolve_status = 'estimated_trajectory'
                                confidence = max(confidence, 0.6)
                                log.info(
                                    f"EST-TRAJECTORY: origin '{_origin_raw}' → target {_target_city} "
                                    f"t={_traj_frac:.2f} seg={_seg_km:.0f}km ({coords[0]:.3f},{coords[1]:.3f}) "
                                    f"bearing={bearing_to_target:.1f}°"
                                )
                            else:
                                coords = _oc
                                resolve_status = 'estimated_offset'
                                confidence = max(confidence, 0.6)
                                log.info(
                                    f"EST-OFFSET: origin '{_origin_raw}' ({_oc[0]:.3f},{_oc[1]:.3f}) "
                                    f"→ target {_target_city} ({_tc[0]:.3f},{_tc[1]:.3f}) bearing={bearing_to_target:.1f}°"
                                )
                        else:
                            # Origin failed to geocode — fall back to target-offset
                            reverse_bearing = (bearing_to_target + 180) % 360
                            _offset_km = 15.0 if _tc[0] >= 47.0 else 20.0
                            offset_lat, offset_lng = _project_point(
                                _tc[0], _tc[1], reverse_bearing, _offset_km
                            )
                            coords = (offset_lat, offset_lng)
                            resolve_status = 'estimated_offset'
                            confidence = max(confidence, 0.6)
                            log.info(
                                f"EST-OFFSET (no origin): target={_target_city} "
                                f"→ {_offset_km:.0f}km offset ({offset_lat:.3f},{offset_lng:.3f})"
                            )
                    else:
                        reverse_bearing = (bearing_to_target + 180) % 360
                        _offset_km = 15.0 if _tc[0] >= 47.0 else 20.0
                        offset_lat, offset_lng = _project_point(
                            _tc[0], _tc[1], reverse_bearing, _offset_km
                        )
                        coords = (offset_lat, offset_lng)
                        resolve_status = 'estimated_offset'
                        confidence = max(confidence, 0.6)
                        log.info(
                            f"EST-OFFSET: target={_target_city} ({_tc[0]:.3f},{_tc[1]:.3f}) "
                            f"bearing={bearing_to_target:.1f}° → {_offset_km:.0f}km offset ({offset_lat:.3f},{offset_lng:.3f})"
                        )
                else:
                    # No bearing — try placing at origin coords directly
                    if _origin_raw:
                        _oc = _geocode_origin(_origin_raw, allow_resolver_fallback=True)
                        if _oc:
                            coords = _oc
                            resolve_status = 'origin_coords'
                            confidence = max(confidence, 0.5)
                            log.info(f"EST: no bearing, using origin '{_origin_raw}' coords: {_oc}")
                    if not coords:
                        coastal_regions = ['Одеська область', 'Миколаївська область', 'Херсонська область', 'Запорізька область', 'АР Крим']
                        if region in coastal_regions:
                            # Region-specific offset: tracking threats entering mostly from south
                            _offset_km = 15.0 if _tc[0] >= 47.0 else 25.0
                            offset_lat, offset_lng = _project_point(
                                _tc[0], _tc[1], 180.0, _offset_km
                            )
                            coords = (offset_lat, offset_lng)
                            resolve_status = 'estimated_offset_coastal'
                            # Higher confidence when target_city is geocoded and region is known (0.3 passes default minConf)
                            confidence = max(confidence, 0.30 if (_target_city and region) else 0.15)
                            log.info(
                                f"EST-OFFSET (coastal fallback): target={_target_city} → "
                                f"{_offset_km:.0f}km south ({offset_lat:.3f},{offset_lng:.3f})"
                            )
                        else:
                            _oblast_center = (
                                _fallback_coords_for_oblast(region) if region and _USE_OBLAST_CENTER else None
                            )
                            if _oblast_center:
                                coords = _oblast_center
                                resolve_status = 'estimated_oblast_center'
                                confidence = max(confidence, 0.2)
                                log.info(
                                    f"EST-FALLBACK: no bearing for {_target_city}, "
                                    f"using oblast center of {region}: ({coords[0]:.3f},{coords[1]:.3f})"
                                )
                            else:
                                # Default: place at geocoded target city (predictable) instead of oblast centroid
                                coords = _tc
                                resolve_status = 'estimated_fallback_target'
                                confidence = max(confidence, 0.25)
                                log.info(
                                    f"EST-OFFSET (no bearing, no oblast): placing directly at target={_target_city} -> {_tc}"
                                )

        elif _target_city and coords:
            # Case A: place_name resolved — keep resolved coords, just set trajectory target
            _tc = _geocode_direction_target(_target_city, region)
            if _tc:
                _target_coords = _tc
                log.info(f"EST: place resolved, target_city={_target_city} → trajectory only")

        # Estimated-offset produced coords but location is still Unknown — use target_city as place
        if _target_city and coords and location == 'Unknown':
            location = _target_city
            log.info(f"PLACE-FROM-TARGET: '{_target_city}' (place was Unknown, estimated-offset gave coords)")

        # Fallback: try geocoding place_name/direction before oblast center
        used_fallback = False
        if not coords:
            _place_to_try = entities.place_name or (entities.direction if getattr(entities, 'direction', '') and getattr(entities, 'direction', '').lower() not in CARDINAL_DIRECTIONS else None)
            if _place_to_try:
                _geo_hint = (_ent_dict.get('oblast') or '').strip() or region
                _gc = _geocode_direction_target(_place_to_try, _geo_hint)
                if _gc:
                    coords = _gc
                    confidence = max(confidence, 0.5)
                    resolve_status = 'direction_geocode_fallback'
                    location = _place_to_try
                    if _geo_hint and _geo_hint != region:
                        region = _geo_hint
                    log.info(f"Direction geocode fallback: {_place_to_try} ({_geo_hint}) → {coords}")
        if not coords and region:
            fallback = _fallback_coords_for_oblast(region)
            if fallback:
                coords = fallback
                used_fallback = True
                confidence = max(confidence, 0.1)
                resolve_status = 'oblast_fallback'
                log.info(f"Oblast fallback for {region}: {coords}")

        # Узгодження координат із контекстом області (омоніми, помилковий геокод)
        _claimed_ob_for_coherence = (_ent_dict.get('oblast') or '').strip() or (region or '').strip()
        _dir_for_coherence = getattr(entities, 'direction', None)
        if _dir_for_coherence and _dir_for_coherence.lower().strip() in CARDINAL_DIRECTIONS:
            _dir_for_coherence = None
        coords, region, confidence, resolve_status, location = _apply_oblast_coherence_for_moving_air(
            coords,
            region,
            _claimed_ob_for_coherence or None,
            entities.place_name,
            _dir_for_coherence,
            entities.event_type,
            confidence,
            resolve_status,
            location,
        )

        # Region must match coords: avoid "Черкаси + Кіровоградська область" when marker is at Cherkasy
        if coords and region:
            try:
                from geo.rules import find_oblast_for_coords
                actual_oblast = find_oblast_for_coords(coords[0], coords[1])
                if actual_oblast and actual_oblast != region:
                    log.info(
                        f"REGION-CORRECT: coords ({coords[0]:.3f},{coords[1]:.3f}) in {actual_oblast}, "
                        f"was {region} (place={location})"
                    )
                    region = actual_oblast
            except Exception:
                pass

        legacy_type = LEGACY_TYPE_MAP.get(entities.event_type, entities.event_type)

        if coords:
            confidence = _cap_confidence_coarse_placements(
                float(confidence), str(resolve_status or '')
            )

        # ── AI deep analysis (on every message) ─────────────────────
        ai_analysis = None
        try:
            ai_analysis = ai_analyze_message(
                raw_text=msg_text,
                event_type=entities.event_type,
                oblast=region,
                place=entities.place_name,
                origin=getattr(entities, 'origin', None),
                direction=entities.direction,
                recent_context=list(_recent_events)[-15:],
                lat=coords[0] if coords else None,
                lng=coords[1] if coords else None,
            )
        except Exception as e:
            log.warning(f"AI analysis failed: {e}")

        # ── Variable speed (from AI or range-based) ──────────────────
        ai_speed = ai_analysis.get('estimated_speed_kmh') if ai_analysis else None
        speed_kmh = get_variable_speed(entities.event_type, ai_speed)
        if speed_kmh == 0:
            speed_kmh = THREAT_SPEEDS.get(entities.event_type, 0)

        # ── Update count from AI if parser missed it ─────────────────
        if ai_analysis and ai_analysis.get('count') and ai_analysis['count'] > entities.count:
            entities.count = ai_analysis['count']

        # ── Build trajectory (direction → target coords) ──────────────
        trajectory_data = None
        course_bearing = None
        distance_km = None

        # Sources whose trajectory endpoint is reliable enough to derive icon bearing from
        _RELIABLE_BEARING_SOURCES = {
            'target_city', 'consensus', 'direction', 'cardinal',
            'group_bearing', 'wave_analysis', 'airfield', 'retarget',
        }

        if coords and speed_kmh > 0:
            trajectory_data = _build_trajectory(
                coords, entities, entities.event_type, region,
                channel_name=channel_name,
                ai_analysis=ai_analysis,
                target_city_coords=_target_coords,
            )
            if trajectory_data:
                end = trajectory_data['end']
                distance_km = round(_haversine_km(
                    coords[0], coords[1], end[0], end[1]
                ), 1)
                # Only derive course_bearing from RELIABLE sources.
                # 'learned', 'ai', 'ai_analyzer', 'heuristic' targets are guesses —
                # using them for icon rotation causes ALL arrows to point at Mykolaiv/Odesa.
                traj_source = trajectory_data.get('source', '')
                if traj_source in _RELIABLE_BEARING_SOURCES:
                    course_bearing = round(_compute_bearing(
                        coords[0], coords[1], end[0], end[1]
                    ), 1)
                else:
                    log.info(
                        f"Trajectory source '{traj_source}' — skipping course_bearing "
                        f"(not reliable enough for icon rotation)"
                    )

        # Fallback: use GPT bearing or cardinal direction even if no trajectory built
        if course_bearing is None:
            course_bearing_fallback = _direction_to_bearing(entities)
            if course_bearing_fallback is not None:
                course_bearing = round(course_bearing_fallback, 1)

        # ticker_bearing: bearing for server-side motion (can use ANY trajectory source).
        # Unlike course_bearing (for icon rotation, reliable sources only),
        # this ensures markers keep moving even with learned/ai trajectories.
        ticker_bearing = course_bearing
        if ticker_bearing is None and trajectory_data:
            end = trajectory_data['end']
            ticker_bearing = round(_compute_bearing(
                coords[0], coords[1], end[0], end[1]
            ), 1)

        # Persist explicit directions / target cities for long-horizon trajectory hints
        if trajectory_data and region and entities.event_type:
            _tsrc = trajectory_data.get('source')
            _learn_city = None
            if _tsrc == 'direction' and entities.direction:
                _dlow = entities.direction.lower().strip()
                if _dlow not in CARDINAL_DIRECTIONS:
                    _learn_city = entities.direction.strip()
            elif _tsrc == 'target_city':
                _learn_city = (
                    (getattr(entities, 'target_city', None) or (ai_analysis or {}).get('target_city') or '')
                ).strip()
            if _learn_city and len(_learn_city) >= 2:
                try:
                    from learned_trajectory_targets import record_trajectory_target
                    record_trajectory_target(region, entities.event_type, _learn_city)
                except Exception:
                    pass

        log.info(
            f"MATCH [{channel_name}]: {entities.event_type}({entities.count}x) "
            f"@ {location} ({region}) conf={confidence:.2f} status={resolve_status}"
        )

        # === Offshore placement when coastal oblast has no air alarm (shahed/uav) ===
        if coords:
            try:
                from geo.offshore_policy import apply_offshore_uav_when_no_alarm

                _prior_coords = (float(coords[0]), float(coords[1]))
                coords, resolve_status, confidence = apply_offshore_uav_when_no_alarm(
                    _prior_coords,
                    region,
                    entities.event_type,
                    resolve_status,
                    float(confidence),
                )
                if (float(coords[0]), float(coords[1])) != _prior_coords:
                    log.info(
                        f"OFFSHORE-NO-ALARM [{channel_name}]: {region} {entities.event_type} "
                        f"{_prior_coords[0]:.4f},{_prior_coords[1]:.4f} → "
                        f"{float(coords[0]):.4f},{float(coords[1]):.4f} "
                        f"status={resolve_status}"
                    )
            except Exception as _off_e:
                log.debug(f"offshore policy skipped: {_off_e}")

        # === Target Aggregator (cross-channel dedup + trajectory) ===
        _target = None
        _aggregator_merged = False
        _bearing_hint = None
        if ticker_bearing is not None and isinstance(ticker_bearing, (int, float)) and math.isfinite(
            float(ticker_bearing)
        ):
            _bearing_hint = float(ticker_bearing) % 360.0

        if coords:
            _is_estimated = bool(resolve_status and resolve_status.startswith('estimated_'))
            agg_obs = AggObs(
                lat=coords[0],
                lng=coords[1],
                ts=now_kyiv.timestamp(),
                event_type=entities.event_type,
                region=region or '',
                channel=channel_name,
                bearing_hint=_bearing_hint,
                place_name=location or '',
                msg_text=msg_text[:200],
                is_estimated=_is_estimated,
                count=entities.count,
            )
            _target, _aggregator_merged = target_aggregator.ingest(agg_obs)

            if _target and _target.observation_count > 1:
                speed_kmh = _target.speed_kmh
                ticker_bearing = _target.bearing
                coords = (_target.lat, _target.lng)

            # Legacy tracker kept for chain_tracker backward compat
            legacy_obs = TrackerObs(
                lat=coords[0], lng=coords[1],
                ts=now_kyiv.timestamp(),
                event_type=entities.event_type,
                oblast=region or '',
                place_name=location,
                channel_name=channel_name,
                bearing_hint=_bearing_hint,
            )
            tracker.process_observation(legacy_obs)

        data = {
            'id': threat_id,
            'type': legacy_type,
            'threat_type': legacy_type,
            'event_type': entities.event_type,
            'track_id': _target.id if _target else None,
            'location': location,
            'place': location,
            'region': region,
            'text': msg_text,
            'lat': coords[0] if coords else None,
            'lng': coords[1] if coords else None,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'channel_priority': channel_meta.get('priority', 3),
            'msg_id': msg_id,
            'count': _target.count if (_target and getattr(_target, 'count', None)) else entities.count,
            'ts': now_iso,
            'date': now_iso,
            'created_at_epoch': int(now_kyiv.timestamp() * 1000),
            'confidence': round(confidence, 3),
            'resolve_status': resolve_status,
            'candidates': candidates_json,
            'resolver_version': 'v2',
            'trajectory': trajectory_data,
            'trajectory_source': trajectory_data.get('source') if trajectory_data else None,
            'prediction_confidence': trajectory_data.get('prediction_confidence') if trajectory_data else None,
            'course_bearing': course_bearing,
            'ticker_bearing': ticker_bearing,
            'raion': raion_name,
            'course_direction': entities.direction,
            'speed_kmh': round(speed_kmh, 1) if speed_kmh > 0 else None,
            'distance_km': distance_km,
            'origin': (ai_analysis or {}).get('origin') or getattr(entities, 'origin', None),
            'positions': _target.to_positions_list(30) if _target else None,
            'observation_count': _target.observation_count if _target else 1,
            'flight_phase': (ai_analysis or {}).get('flight_phase', 'cruise') if trajectory_data else None,
            'is_estimated': resolve_status.startswith('estimated_') if resolve_status else False,
            'confidence_0_100': int(max(0, min(100, round(float(confidence) * 100)))),
            'placement_mode': 'point',
        }

        normalize_maritime_marker_fields(data)
        _r = data.get('region')
        region = str(_r).strip() if _r is not None and str(_r).strip() else None

        _hasc = oblast_uk_name_to_hasc(region)
        if _hasc:
            data['resolved_oblast_hasc'] = _hasc
            data['region_key'] = _hasc

        if channel_name == KHERSON_NON_DRONE_CH:
            data['marker_icon'] = KHERSON_MARKER_ICON

        log.info(
            f"COORD_TRACE [{channel_name}] resolve_status={resolve_status} "
            f"track_id={data.get('track_id')} place={location!r} region={region!r} "
            f"conf={confidence:.2f} jitter_env={_COORD_JITTER_ENABLED} "
            f"obs_count={data.get('observation_count')}"
        )

        # ── Check for follow-up: should we PATCH an existing marker? ──
        # For multi-entity messages, exclude our own msg_id from fuzzy matching
        # so sibling entities don't incorrectly chain to each other.
        _exclude_mid = msg_id if len(all_entities) > 1 else None
        parent = chain_tracker.find_parent(
            channel_id=channel_id,
            reply_to_msg_id=reply_to_msg_id,
            event_type=entities.event_type,
            place=entities.place_name,
            oblast=region,
            origin=getattr(entities, 'origin', None),
            raw_text=msg_text,
            exclude_msg_id=_exclude_mid,
        )

        # Follow-ups must keep the server's track_id — local kinematic IDs can desync
        # after association misses, causing duplicate markers for one threat.
        if parent and getattr(parent, 'track_id', None):
            data['track_id'] = parent.track_id

        try:
            _multi_max = float(os.getenv('NEPTUN_MULTI_REF_MAX_CONF', '0.82'))
        except ValueError:
            _multi_max = 0.82
        _multi_risk = _message_multi_place_risk(all_entities, msg_text)
        if coords and _sea_context_inland_mismatch(msg_text, coords[0], coords[1]):
            data['placement_mode'] = 'sea_context_mismatch'
            data['hidden'] = True
            log.info(
                f"PLACEMENT [{channel_name}]: sea_context_mismatch — suppress pin "
                f"({coords[0]:.3f},{coords[1]:.3f})"
            )
        elif _multi_risk and float(confidence) < _multi_max:
            data['placement_mode'] = 'multi_reference_suppressed'
            data['hidden'] = True
            log.info(
                f"PLACEMENT [{channel_name}]: multi_reference_suppressed "
                f"(entities={len(all_entities)} conf={confidence:.2f} < {_multi_max})"
            )
        else:
            _rs = str(resolve_status or '')
            if _rs in _COARSE_PLACEMENT_STATUSES:
                data['placement_mode'] = 'approximate'
            elif _rs.startswith('estimated_'):
                data['placement_mode'] = 'predictive'

        if parent and coords and INGEST_URL:
            # Follow-up message — send as track update via POST (upsert by track_id)
            follow_track_id = data.get('track_id')
            if follow_track_id:
                _chain_all_ok = True

                try:
                    if not _ingest_coords_ok(data):
                        _chain_all_ok = False
                        log.warning(
                            f"CHAIN→TRACK skipped: implausible coords lat={data.get('lat')} lng={data.get('lng')}"
                        )
                    else:
                        session = get_http_session()
                        async with session.post(
                            INGEST_URL,
                            json={'marker': data},
                            headers={'X-Auth-Secret': INGEST_SECRET},
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as resp:
                            if resp.status == 200:
                                try:
                                    body = await resp.json()
                                except Exception:
                                    body = {}
                                log.info(
                                    f"CHAIN→TRACK [{channel_name}]: {follow_track_id} "
                                    f"mode={body.get('mode', '?')} → {location} ({entities.direction or 'no-dir'})"
                                )
                                _add_recent(data)
                                chain_tracker.register(
                                    channel_id=channel_id,
                                    msg_id=msg_id,
                                    marker_id=body.get('id', threat_id),
                                    event_type=entities.event_type,
                                    place=entities.place_name,
                                    oblast=region,
                                    origin=getattr(entities, 'origin', None),
                                    direction=entities.direction,
                                    target_city=getattr(entities, 'target_city', None),
                                    track_id=data.get('track_id'),
                                    raw_text=msg_text,
                                )
                            else:
                                _chain_all_ok = False
                                body_text = await resp.text()
                                log.warning(
                                    f"CHAIN→TRACK failed [{resp.status}]: {body_text[:200]}. "
                                    f"Falling back to PATCH."
                                )
                except Exception as e:
                    _chain_all_ok = False
                    log.warning(f"CHAIN→TRACK error: {e}. Falling back to PATCH.")

                if _chain_all_ok:
                    await _publish_feed_event(
                        status='chain_update', channel_name=channel_name, msg_text=msg_text,
                        channel_id=channel_id, msg_id=msg_id,
                        threat_type=entities.event_type,
                        region=region, place=location,
                        lat=coords[0] if coords else None,
                        lng=coords[1] if coords else None,
                        speed_kmh=round(speed_kmh, 1) if speed_kmh > 0 else None,
                        course_bearing=course_bearing,
                        track_id=follow_track_id,
                        confidence=round(confidence, 3),
                        resolve_status=resolve_status,
                        entities_count=len(all_entities),
                    )
                    continue  # Skip legacy POST/PATCH — all units updated

            # Fallback: legacy PATCH by marker ID
            patch_updates = {
                'lat': coords[0],
                'lng': coords[1],
                'location': location,
                'place': location,
                'text': msg_text,
                'course_direction': entities.direction,
                'trajectory': trajectory_data,
                'trajectory_source': trajectory_data.get('source') if trajectory_data else None,
                'course_bearing': course_bearing,
                'speed_kmh': round(speed_kmh, 1) if speed_kmh > 0 else None,
                'distance_km': distance_km,
            }
            # Filter None values
            patch_updates = {k: v for k, v in patch_updates.items() if v is not None}

            if not is_plausible_threat_coord(coords[0], coords[1], manual=False):
                log.warning(
                    f"CHAIN PATCH skipped: implausible coords lat={coords[0]} lng={coords[1]}"
                )
            else:
                try:
                    session = get_http_session()
                    async with session.patch(
                        INGEST_URL,
                        json={'id': parent.marker_id, 'updates': patch_updates},
                        headers={'X-Auth-Secret': INGEST_SECRET},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        body_text = await resp.text()
                        if resp.status == 200:
                            log.info(
                                f"CHAIN PATCH [{channel_name}]: {parent.marker_id} → "
                                f"{location} ({entities.direction or 'no-dir'})"
                            )
                            _add_recent(data)
                            chain_tracker.register(
                                channel_id=channel_id,
                                msg_id=msg_id,
                                marker_id=parent.marker_id,
                                event_type=entities.event_type,
                                place=entities.place_name,
                                oblast=region,
                                origin=getattr(entities, 'origin', None),
                                direction=entities.direction,
                                target_city=getattr(entities, 'target_city', None),
                                track_id=getattr(parent, 'track_id', None),
                                raw_text=msg_text,
                            )
                            await _publish_feed_event(
                                status='chain_update', channel_name=channel_name, msg_text=msg_text,
                                channel_id=channel_id, msg_id=msg_id,
                                threat_type=entities.event_type,
                                region=region, place=location,
                                lat=coords[0] if coords else None,
                                lng=coords[1] if coords else None,
                                speed_kmh=round(speed_kmh, 1) if speed_kmh > 0 else None,
                                course_bearing=course_bearing,
                                track_id=parent.marker_id,
                                confidence=round(confidence, 3),
                                resolve_status=resolve_status,
                                marker_id=parent.marker_id,
                            )
                            continue
                        log.warning(
                            f"CHAIN PATCH failed [{resp.status}]: {body_text[:200]}. "
                            f"Falling back to POST."
                        )
                except Exception as e:
                    log.warning(f"CHAIN PATCH error: {e}. Falling back to POST.")

        # ── Phantom avia marker for KAB/tactical aviation ──
        if entities.event_type == 'kab' and coords:
            avia_data = _spawn_phantom_avia(
                kab_coords=coords,
                region=region,
                direction=entities.direction,
                msg_text=msg_text,
                channel_id=channel_id,
                channel_name=channel_name,
                channel_meta=channel_meta,
                now_iso=now_iso,
                parent_threat_id=threat_id,
            )
            if avia_data:
                avia_ttl = 1800  # 30min for aviation
                db.save_threat(avia_data['id'], avia_data, ttl=avia_ttl)
                db.publish_update('new_threat', avia_data)
                if INGEST_URL and _ingest_coords_ok(avia_data):
                    try:
                        session = get_http_session()
                        async with session.post(
                            INGEST_URL,
                            json={'marker': avia_data},
                            headers={'X-Auth-Secret': INGEST_SECRET},
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as resp:
                            txt = await resp.text()
                            if resp.status == 200:
                                log.info(f"Phantom avia ingested: {avia_data['id']}")
                                _add_recent(avia_data)
                                await _publish_feed_event(
                                    status='processed', channel_name=channel_name, msg_text=msg_text,
                                    channel_id=channel_id, msg_id=msg_id,
                                    threat_type='avia',
                                    reason='phantom avia for KAB',
                                    place=avia_data.get('place') or avia_data.get('location') or '',
                                    impact_place=location or '',
                                    region=region,
                                    lat=avia_data.get('lat'), lng=avia_data.get('lng'),
                                    marker_id=avia_data['id'],
                                    resolve_status='phantom_avia',
                                )
                            else:
                                log.error(f"Phantom avia ingest failed: {resp.status} {txt[:200]}")
                    except Exception as e:
                        log.error(f"Phantom avia ingest error: {e}")
                elif INGEST_URL and avia_data:
                    log.warning(
                        f"Phantom avia skipped: implausible coords lat={avia_data.get('lat')} "
                        f"lng={avia_data.get('lng')}"
                    )

        # 5. Save to Redis & Ingest — single marker per entity (count shown as badge)
        if entities.event_type in ['launch', 'explosion']:
            ttl = 1800  # 30min
        elif entities.event_type == 'ballistic':
            ttl = 1200  # 20min (fast events)
        elif entities.event_type == 'kab':
            ttl = 3600  # 1h for KABs
        else:
            ttl = 7200  # 2h

        # Store the computed overall confidence before threshold evaluations
        if confidence >= 0.8:
            ttl = int(ttl * 1.5)

        if confidence < MIN_CONFIDENCE_THRESHOLD:
            data['hidden'] = True
            if data.get('placement_mode') in ('point', 'approximate', 'predictive'):
                data['placement_mode'] = 'low_map_confidence'

        try:
            from geo.geo_audit_log import append_record as _geo_audit_append

            _geo_audit_append(
                {
                    'ts': now_iso,
                    'channel': channel_name,
                    'channel_id': channel_id,
                    'msg_id': msg_id,
                    'reply_to_msg_id': reply_to_msg_id,
                    'text_excerpt': (msg_text or '')[:800],
                    'entities': {
                        'place_name': getattr(entities, 'place_name', None),
                        'oblast': getattr(entities, 'oblast', None),
                        'direction': getattr(entities, 'direction', None),
                        'target_city': getattr(entities, 'target_city', None),
                        'near': getattr(entities, 'near', None),
                        'origin': getattr(entities, 'origin', None),
                        'event_type': entities.event_type,
                        'count': entities.count,
                    },
                    'outcome': {
                        'marker_id': threat_id,
                        'track_id': data.get('track_id'),
                        'aggregator_merged': bool(_aggregator_merged),
                        'lat': data.get('lat'),
                        'lng': data.get('lng'),
                        'confidence': data.get('confidence'),
                        'confidence_0_100': data.get('confidence_0_100'),
                        'placement_mode': data.get('placement_mode'),
                        'hidden': bool(data.get('hidden')),
                        'resolve_status': resolve_status,
                        'trajectory_source': data.get('trajectory_source'),
                        'is_estimated': data.get('is_estimated'),
                    },
                }
            )
        except Exception:
            pass

        db.save_threat(threat_id, data, ttl=ttl)
        db.publish_update('new_threat', data)

        # Push marker to Next.js web service
        if not INGEST_URL:
            log.warning(f"Skipping ingest: INGEST_URL not configured")
        elif not coords:
            log.warning(f"Skipping ingest for {threat_id}: no coordinates")
            await _publish_feed_event(
                status='dropped', channel_name=channel_name, msg_text=msg_text,
                channel_id=channel_id, msg_id=msg_id,
                threat_type=legacy_type,
                reason='no coordinates after geolocation',
                place=location, region=region,
            )
        elif data.get('hidden'):
            log.info(f"Skipping ingest for {threat_id}: hidden (low confidence)")
            await _publish_feed_event(
                status='dropped', channel_name=channel_name, msg_text=msg_text,
                channel_id=channel_id, msg_id=msg_id,
                threat_type=legacy_type,
                reason='hidden (low confidence)',
                place=location, region=region,
                confidence=round(confidence, 3),
            )
        elif not _ingest_coords_ok(data):
            log.warning(
                f"Skipping ingest for {threat_id}: implausible coords lat={data.get('lat')} lng={data.get('lng')}"
            )
            await _publish_feed_event(
                status='dropped', channel_name=channel_name, msg_text=msg_text,
                channel_id=channel_id, msg_id=msg_id,
                threat_type=legacy_type,
                reason='implausible coordinates',
                place=location, region=region,
            )
        elif channel_name == KHERSON_NON_DRONE_CH and not is_kherson_non_drone_raion_allowed(raion_name):
            log.info(
                f"Skipping ingest for {threat_id}: kherson_non_drone outside Херсонський район UA-65-01 "
                f"(raion={raion_name!r})"
            )
            await _publish_feed_event(
                status='dropped', channel_name=channel_name, msg_text=msg_text,
                channel_id=channel_id, msg_id=msg_id,
                threat_type=legacy_type,
                reason='outside_kherson_raion',
                place=location, region=region,
            )
        elif not _should_ingest_by_alarm(region, entities.event_type, raion=raion_name):
            log.info(
                f"Skipping ingest for {threat_id}: no active alarm in {region} "
                f"(raion={raion_name}, type={entities.event_type})"
            )
            await _publish_feed_event(
                status='dropped', channel_name=channel_name, msg_text=msg_text,
                channel_id=channel_id, msg_id=msg_id,
                threat_type=legacy_type,
                reason=f'no active alarm in region',
                place=location, region=region,
            )
        else:
            # Кілька спроб: під час рестарту neptun-web (деплой) з'єднання падає —
            # це не помилка парсингу, маркер усе одно потрапляє в ingest_queue.
            _ingest_delays_sec = (0.0, 0.75, 2.0, 4.0)
            _ingest_timeout = aiohttp.ClientTimeout(total=12)
            _posted = False
            for _ing_i, _ing_wait in enumerate(_ingest_delays_sec):
                if _ing_wait > 0:
                    await asyncio.sleep(_ing_wait)
                try:
                    session = get_http_session()
                    async with session.post(
                        INGEST_URL,
                        json={'marker': data},
                        headers={'X-Auth-Secret': INGEST_SECRET},
                        timeout=_ingest_timeout,
                    ) as resp:
                        if resp.status == 200:
                            try:
                                body = await resp.json()
                            except Exception:
                                body = {}
                            _ingest_marker_id = body.get('id', threat_id)
                            _public_broadcast = body.get('public_broadcast') is True
                            _count_str = f" (count={entities.count})" if entities.count > 1 else ""
                            log.info(f"Ingested: {threat_id}{_count_str} ({body.get('total', '?')} total)")
                            _add_recent(data)
                            chain_tracker.register(
                                channel_id=channel_id,
                                msg_id=msg_id,
                                marker_id=_ingest_marker_id,
                                event_type=entities.event_type,
                                place=entities.place_name,
                                oblast=region,
                                origin=getattr(entities, 'origin', None),
                                direction=entities.direction,
                                target_city=getattr(entities, 'target_city', None),
                                track_id=data.get('track_id'),
                                raw_text=msg_text,
                            )
                            await _publish_feed_event(
                                status='processed', channel_name=channel_name, msg_text=msg_text,
                                channel_id=channel_id, msg_id=msg_id,
                                threat_type=legacy_type,
                                entities_count=len(all_entities),
                                parser='gpt' if gpt_entities else 'regex',
                                place=location, region=region,
                                lat=coords[0] if coords else None,
                                lng=coords[1] if coords else None,
                                speed_kmh=round(speed_kmh, 1) if speed_kmh > 0 else None,
                                course_bearing=course_bearing,
                                track_id=data.get('track_id'),
                                confidence=round(confidence, 3),
                                resolve_status=resolve_status,
                                marker_id=_ingest_marker_id,
                                origin=getattr(entities, 'origin', None),
                            )
                            if _public_broadcast:
                                try:
                                    fcm_ok = send_threat_push(
                                        data,
                                        REGION_TOPIC_MAP,
                                        min_confidence=float(MIN_CONFIDENCE_THRESHOLD),
                                    )
                                    if not fcm_ok:
                                        log.info(
                                            f"FCM push gated after public ingest for {threat_id}: "
                                            f"region={region}, type={legacy_type}, hidden={data.get('hidden')}"
                                        )
                                except Exception as e:
                                    log.error(f"FCM push failed for {threat_id}: {e}")
                            else:
                                log.info(
                                    f"FCM push skipped for {threat_id}: ingest accepted but marker is not public"
                                )
                            _posted = True
                            break
                        body_text = await resp.text()
                        if resp.status in (502, 503, 504) and _ing_i < len(_ingest_delays_sec) - 1:
                            log.warning(
                                f"Ingest HTTP {resp.status} (transient), retry {_ing_i + 1}/"
                                f"{len(_ingest_delays_sec)}: {body_text[:120]}"
                            )
                            continue
                        log.error(f"Ingest failed [{resp.status}]: {body_text[:300]}")
                        ingest_queue.enqueue(data)
                        await _publish_feed_event(
                            status='error', channel_name=channel_name, msg_text=msg_text,
                            channel_id=channel_id, msg_id=msg_id,
                            threat_type=legacy_type,
                            reason=f'ingest HTTP {resp.status}',
                            place=location, region=region,
                        )
                        _posted = True
                        break
                except (aiohttp.ClientError, asyncio.TimeoutError) as _ing_e:
                    _is_last = _ing_i >= len(_ingest_delays_sec) - 1
                    log.warning(
                        f"Ingest unreachable (attempt {_ing_i + 1}/{len(_ingest_delays_sec)}): {_ing_e}"
                    )
                    if not _is_last:
                        continue
                    log.error(f"Ingest gave up after {len(_ingest_delays_sec)} attempts: {_ing_e}")
                    ingest_queue.enqueue(data)
                    await _publish_feed_event(
                        status='error', channel_name=channel_name, msg_text=msg_text,
                        channel_id=channel_id, msg_id=msg_id,
                        threat_type=legacy_type,
                        reason='ingest unreachable (web restarting?); queued for retry',
                        place=location, region=region,
                    )
                    _posted = True
                except Exception as e:
                    log.error(f"Failed to POST to ingest: {e}", exc_info=True)
                    ingest_queue.enqueue(data)
                    await _publish_feed_event(
                        status='error', channel_name=channel_name, msg_text=msg_text,
                        channel_id=channel_id, msg_id=msg_id,
                        threat_type=legacy_type,
                        reason=f'ingest exception: {str(e)[:100]}',
                        place=location, region=region,
                    )
                    _posted = True
                    break
            if not _posted:
                log.error('Ingest loop exited without handling response')
                ingest_queue.enqueue(data)


def shutdown_handler(sig, frame):
    log.info("Shutting down worker...")
    try:
        from ai_trajectory import flush_learned_targets_disk
        flush_learned_targets_disk()
    except Exception:
        pass
    asyncio.ensure_future(ingest_queue.stop())
    try:
        # client.disconnect() returns a Future (asyncio.shield), not a coroutine
        # Use ensure_future which accepts both coroutines and futures
        asyncio.ensure_future(client.disconnect())
    except Exception:
        pass
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    asyncio.run(main())
