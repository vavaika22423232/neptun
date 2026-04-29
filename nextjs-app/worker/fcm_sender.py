"""
fcm_sender.py — Firebase Cloud Messaging push notification sender.

Sends topic-based push notifications when new threats are detected.
Each Ukrainian region maps to an FCM topic (e.g. 'region_kyivska').
Users subscribe to topics on the Flutter client side.
"""

import base64
import json
import logging
import os
import tempfile
import time
from typing import Optional

from constants import REGION_TO_OBLAST_ID, RAION_NAME_TO_ID
from geo_bounds import is_plausible_threat_coord

log = logging.getLogger(__name__)

# Lazy-initialized Firebase app
_firebase_app = None
_initialized = False

# ── Rate-limiting for threat pushes ──
# Key: (region, threat_group) → timestamp of last sent push
_push_cooldown_cache: dict[tuple[str, str], float] = {}

_THREAT_GROUP = {
    'ballistic': 'critical', 'missile': 'critical', 'raketa': 'critical',
    'cruise': 'critical', 'kab': 'critical', 'pusk': 'critical',
    'launch': 'critical',
    'vibuh': 'explosion', 'explosion': 'explosion',
    'shahed': 'uav', 'drone': 'uav', 'uav': 'uav', 'fpv': 'uav',
    'rozved': 'recon',
    'avia': 'avia', 'helicopter': 'avia',
}

_GROUP_COOLDOWN_SEC = {
    'critical':  90,   # ballistic/missiles/KAB — 1.5 min
    'explosion': 120,  # explosions — 2 min
    'uav':       180,  # shaheds/drones — 3 min
    'recon':     300,  # recon drones — 5 min
    'avia':      180,  # aviation — 3 min
}
_DEFAULT_COOLDOWN = 180
_BLOCKED_PLACEMENT_MODES = {
    'multi_reference_suppressed',
    'sea_context_mismatch',
    'low_map_confidence',
}
_BLOCKED_TRACK_STATES = {'lost', 'stale', 'split_candidate'}


def _is_push_rate_limited(region: str, threat_type: str) -> bool:
    """Return True if a push for this region+threat_group was sent recently."""
    group = _THREAT_GROUP.get(threat_type, threat_type)
    key = (region, group)
    now = time.monotonic()
    last_sent = _push_cooldown_cache.get(key)
    cooldown = _GROUP_COOLDOWN_SEC.get(group, _DEFAULT_COOLDOWN)
    if last_sent and (now - last_sent) < cooldown:
        return True
    return False


def _record_push_sent(region: str, threat_type: str) -> None:
    """Record that a push was just sent for this region+threat_group."""
    group = _THREAT_GROUP.get(threat_type, threat_type)
    key = (region, group)
    _push_cooldown_cache[key] = time.monotonic()
    # Evict stale entries periodically (keep cache bounded)
    if len(_push_cooldown_cache) > 500:
        cutoff = time.monotonic() - 600
        stale = [k for k, v in _push_cooldown_cache.items() if v < cutoff]
        for k in stale:
            del _push_cooldown_cache[k]


def _effective_confidence(data: dict, min_confidence: float) -> float:
    """Return normalized marker confidence using the same 0..1 semantics as the map API."""
    raw = data.get('confidence')
    if isinstance(raw, (int, float)):
        return max(0.0, min(1.0, float(raw)))
    raw_100 = data.get('confidence_0_100')
    if isinstance(raw_100, (int, float)):
        return max(0.0, min(1.0, float(raw_100) / 100.0))
    return min_confidence


def _passes_public_push_gate(data: dict, min_confidence: float) -> tuple[bool, str]:
    """Mirror the public-map hard gates before sending an FCM threat push."""
    if data.get('manual'):
        return True, 'manual'
    if data.get('hidden'):
        return False, 'hidden'
    if str(data.get('placement_mode') or '') in _BLOCKED_PLACEMENT_MODES:
        return False, f"placement_mode={data.get('placement_mode')}"
    if str(data.get('track_state') or '') in _BLOCKED_TRACK_STATES:
        return False, f"track_state={data.get('track_state')}"
    track_confidence = data.get('track_confidence')
    if isinstance(track_confidence, (int, float)) and float(track_confidence) < 0.5:
        return False, f"track_confidence={track_confidence}"
    lat = data.get('lat')
    lng = data.get('lng')
    if not is_plausible_threat_coord(lat, lng, manual=bool(data.get('manual'))):
        return False, 'implausible_coords'
    confidence = _effective_confidence(data, min_confidence)
    if confidence < min_confidence:
        return False, f"confidence={confidence:.2f}<min={min_confidence:.2f}"
    return True, 'ok'


def _init_firebase():
    """Initialize Firebase Admin SDK from env credentials (once)."""
    global _firebase_app, _initialized
    if _initialized:
        return _firebase_app is not None

    _initialized = True

    try:
        import firebase_admin  # type: ignore[reportMissingImports]
        from firebase_admin import credentials  # type: ignore[reportMissingImports]
    except ImportError:
        log.warning("firebase-admin package not installed — FCM disabled")
        return False

    creds_b64 = os.getenv('FIREBASE_CREDENTIALS_BASE64')
    creds_file = os.getenv('FIREBASE_CREDENTIALS_FILE')

    # Try base64 credentials first
    if creds_b64:
        try:
            creds_json = base64.b64decode(creds_b64).decode('utf-8')
            creds_dict = json.loads(creds_json)
            cred = credentials.Certificate(creds_dict)
            _firebase_app = firebase_admin.initialize_app(cred)
            log.info("Firebase initialized from FIREBASE_CREDENTIALS_BASE64")
            return True
        except Exception as e:
            log.warning(f"FIREBASE_CREDENTIALS_BASE64 failed: {e}")
            # Fall through to try file-based credentials

    # Try file-based credentials
    if creds_file and os.path.exists(creds_file):
        try:
            cred = credentials.Certificate(creds_file)
            _firebase_app = firebase_admin.initialize_app(cred)
            log.info(f"Firebase initialized from file: {creds_file}")
            return True
        except Exception as e:
            log.error(f"Firebase file init failed: {e}", exc_info=True)
            return False

    log.warning("No Firebase credentials configured — FCM disabled")
    return False


# Threat type display names (Ukrainian)
# Keys include both parser_v2 originals AND LEGACY_TYPE_MAP outputs
THREAT_NAMES = {
    'shahed': 'Шахеди',
    'drone': 'БПЛА',
    'uav': 'БПЛА',
    'rozved': 'Розвідувальний БПЛА',
    'missile': 'Ракети',
    'raketa': 'Ракети',
    'ballistic': 'Балістика',
    'kab': 'КАБ',
    'cruise': 'Крилаті ракети',
    'avia': 'Авіація',
    'helicopter': 'Гелікоптери',
    'vibuh': 'Вибухи',
    'pusk': 'Пуск ракет',
    'explosion': 'Вибухи',
    'launch': 'Пуск ракет',
    'alarm': 'Повітряна тривога',
    'alarm_cancel': 'Відбій тривоги',
}


def send_threat_push(data: dict, region_topic_map: dict, *, min_confidence: float = 0.65) -> bool:
    """
    Send FCM push notification for a new threat.

    Args:
        data: Threat data dict with at least 'region', 'threat_type', 'city'.
        region_topic_map: Mapping from region name to FCM topic.

    Returns:
        True if notification was sent successfully, False otherwise.
    """
    passes_gate, gate_reason = _passes_public_push_gate(data, min_confidence)
    if not passes_gate:
        log.info(f"FCM threat push gated: {gate_reason} id={data.get('id')}")
        return False

    region = data.get('region', '')
    if not region:
        return False

    threat_type = data.get('threat_type', 'unknown')

    # Rate-limit: skip if we already pushed this region+threat_group recently
    if _is_push_rate_limited(region, threat_type):
        log.debug(f"FCM rate-limited: {threat_type} in {region}")
        return False

    if not _init_firebase():
        return False

    # Find matching topic
    topic = region_topic_map.get(region)
    if not topic:
        for key, val in region_topic_map.items():
            if region in key or key in region:
                topic = val
                break
    if not topic:
        log.warning(f"No FCM topic for region: {region}")
        return False

    extra_topics = []
    if topic == 'region_kyiv_city':
        extra_topics.append('region_kyivska')
    elif topic == 'region_kyivska':
        extra_topics.append('region_kyiv_city')

    try:
        from firebase_admin import messaging  # type: ignore[reportMissingImports]

        threat_name = THREAT_NAMES.get(threat_type, threat_type)
        city = data.get('city', data.get('place', ''))
        count = data.get('count', 1)

        # Build notification text
        title = f"⚠️ {threat_name}"
        if count and count > 1:
            title += f" ({count}x)"

        body_parts = []
        if city:
            body_parts.append(city)
        if region and region != city:
            body_parts.append(region)
        body = ', '.join(body_parts) if body_parts else 'Нова загроза виявлена'

        # Resolve oblast_id for ID-based filtering on Flutter side
        oblast_id = REGION_TO_OBLAST_ID.get(region, '')
        if not oblast_id:
            # Try partial match
            for k, v in REGION_TO_OBLAST_ID.items():
                if region in k or k in region:
                    oblast_id = v
                    break

        # Resolve raion_id for district-level filtering on Flutter side
        raion_name = data.get('raion', '')
        raion_id = ''
        if raion_name:
            raion_id = RAION_NAME_TO_ID.get(raion_name, '')
            if not raion_id:
                # Try partial match
                for k, v in RAION_NAME_TO_ID.items():
                    if raion_name in k or k in raion_name:
                        raion_id = v
                        break

        # Map threat type to appropriate Android notification channel
        channel_map = {
            'ballistic': 'critical_alerts',
            'missile': 'critical_alerts',
            'raketa': 'critical_alerts',
            'cruise': 'critical_alerts',
            'kab': 'critical_alerts',
            'vibuh': 'critical_alerts',
            'pusk': 'critical_alerts',
            'explosion': 'critical_alerts',
            'launch': 'critical_alerts',
            'alarm': 'critical_alerts',
            'alarm_cancel': 'all_clear_alerts',
            'shahed': 'normal_alerts',
            'drone': 'normal_alerts',
            'uav': 'normal_alerts',
            'rozved': 'normal_alerts',
            'avia': 'normal_alerts',
            'helicopter': 'normal_alerts',
        }
        android_channel = channel_map.get(threat_type, 'normal_alerts')

        threat_group = _THREAT_GROUP.get(threat_type, threat_type)
        collapse_key = f"{topic}_{threat_group}"

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={
                'type': 'threat',
                'threat_type': threat_type,
                'region': region,
                'city': city or '',
                'location': city or '',
                'title': title,
                'body': body,
                'oblast_id': oblast_id,
                'raion_id': raion_id,
                'is_critical': 'true' if android_channel == 'critical_alerts' else 'false',
                'id': str(data.get('id', '')),
                'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            },
            topic=topic,
            android=messaging.AndroidConfig(
                priority='high',
                collapse_key=collapse_key,
                notification=messaging.AndroidNotification(
                    channel_id=android_channel,
                    priority='max',
                    sound='default',
                    icon='ic_notification',
                    tag=collapse_key,
                ),
                ttl=300,
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body,
                        ),
                        sound='default',
                        badge=1,
                        content_available=True,
                    ),
                ),
                headers={
                    'apns-priority': '10',
                    'apns-collapse-id': collapse_key,
                },
            ),
        )

        result = messaging.send(message)
        _record_push_sent(region, threat_type)
        log.info(f"FCM sent: {threat_name} in {region} → topic:{topic} (id:{result})")

        # Send to extra topics (e.g. Kyiv city ↔ Kyiv oblast)
        for extra_topic in extra_topics:
            try:
                extra_msg = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=message.data,
                    topic=extra_topic,
                    android=message.android,
                    apns=message.apns,
                )
                extra_result = messaging.send(extra_msg)
                log.info(f"FCM extra: {threat_name} in {region} → topic:{extra_topic} (id:{extra_result})")
            except Exception as ex:
                log.warning(f"FCM extra topic {extra_topic} failed: {ex}")

        return True

    except Exception as e:
        log.error(f"FCM send failed: {e}", exc_info=True)
        return False


# --- Air Raid Alarm Push ---

# ukrainealarm API alert type → display info
ALARM_TYPE_INFO = {
    'BALLISTIC':    ('🚀 Ракетна небезпека',     'critical_alerts'),
    'DRONES':       ('🛩️ Загроза БПЛА',           'normal_alerts'),
    'ARTILLERY':    ('💥 Артилерійський обстріл',  'critical_alerts'),
    'CHEMICAL':     ('☢️ Хімічна загроза',         'critical_alerts'),
    'NUCLEAR':      ('☢️ Ядерна загроза',          'critical_alerts'),
    'AIR':          ('🚨 Повітряна тривога',       'critical_alerts'),
    'UNKNOWN':      ('🚨 Повітряна тривога',       'critical_alerts'),
}


def send_alarm_push(
    region_name: str,
    alarm_type: str,
    is_start: bool,
    region_topic_map: dict,
) -> bool:
    """
    Send FCM push for air raid alarm start / end.

    Args:
        region_name: Ukrainian region name (e.g. 'Харківська область').
        alarm_type: Alert type from ukrainealarm API (e.g. 'BALLISTIC', 'DRONES', 'AIR').
        is_start: True = alarm started, False = alarm ended (відбій).
        region_topic_map: Mapping from region name to FCM topic.

    Returns:
        True if sent successfully.
    """
    if not _init_firebase():
        return False

    # Resolve topic
    topic = region_topic_map.get(region_name)
    if not topic:
        for key, val in region_topic_map.items():
            if region_name in key or key in region_name:
                topic = val
                break
    if not topic:
        log.debug(f"[ALARM-FCM] No topic for region: {region_name}")
        return False

    # Kyiv ↔ Kyivska dual-topic
    extra_topics = []
    if topic == 'region_kyiv_city':
        extra_topics.append('region_kyivska')
    elif topic == 'region_kyivska':
        extra_topics.append('region_kyiv_city')

    try:
        from firebase_admin import messaging

        # Resolve display info
        if is_start:
            type_info = ALARM_TYPE_INFO.get(alarm_type, ALARM_TYPE_INFO['AIR'])
            title = type_info[0]
            android_channel = type_info[1]
            body = region_name
        else:
            title = '✅ Відбій тривоги'
            body = region_name
            android_channel = 'all_clear_alerts'

        # Resolve oblast_id for Flutter region filtering
        oblast_id = REGION_TO_OBLAST_ID.get(region_name, '')
        if not oblast_id:
            for k, v in REGION_TO_OBLAST_ID.items():
                if region_name in k or k in region_name:
                    oblast_id = v
                    break

        alarm_state = 'start' if is_start else 'end'

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={
                'type': 'alarm',
                'alarm_state': alarm_state,
                'alarm_type': alarm_type,
                'region': region_name,
                'location': region_name,
                'title': title,
                'body': body,
                'oblast_id': oblast_id,
                'is_critical': 'true' if android_channel == 'critical_alerts' else 'false',
                'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            },
            topic=topic,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id=android_channel,
                    priority='max',
                    sound='default',
                    icon='ic_notification',
                ),
                ttl=300,
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body,
                        ),
                        sound='default',
                        badge=1,
                        content_available=True,
                    ),
                ),
                headers={'apns-priority': '10'},
            ),
        )

        result = messaging.send(message)
        log.info(f"[ALARM-FCM] {alarm_state} {alarm_type} → {region_name} topic:{topic} (id:{result})")

        for extra_topic in extra_topics:
            try:
                extra_msg = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data=message.data,
                    topic=extra_topic,
                    android=message.android,
                    apns=message.apns,
                )
                messaging.send(extra_msg)
                log.info(f"[ALARM-FCM] extra → topic:{extra_topic}")
            except Exception as ex:
                log.warning(f"[ALARM-FCM] extra topic {extra_topic} failed: {ex}")

        return True

    except Exception as e:
        log.error(f"[ALARM-FCM] send failed: {e}", exc_info=True)
        return False
