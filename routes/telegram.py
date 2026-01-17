# Telegram integration module - FCM notifications for Telegram threat messages
# Extracted from app.py for better code organization

import os
import re
import json
import time
import logging
import threading
from datetime import datetime, timedelta

import pytz
from flask import Blueprint

from .config import DISTRICT_TO_OBLAST, REGION_TOPIC_MAP

log = logging.getLogger(__name__)

# Create blueprint (currently no routes, just shared functions)
telegram_bp = Blueprint('telegram', __name__)

# =============================================================================
# TELEGRAM ALERT TRACKING
# =============================================================================
_telegram_alert_sent = {}
_telegram_alert_lock = threading.Lock()
_telegram_region_notified = {}

# Firebase reference (set by main app)
_firebase_initialized = False
_messaging = None

def init_firebase_messaging(firebase_initialized, messaging_module):
    """Initialize Firebase messaging reference from main app."""
    global _firebase_initialized, _messaging
    _firebase_initialized = firebase_initialized
    _messaging = messaging_module

# =============================================================================
# DYNAMIC CHANNELS MANAGEMENT
# =============================================================================
CHANNELS_FILE = 'channels_dynamic.json'

def load_dynamic_channels():
    """Load dynamic channel list from file."""
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Failed to load dynamic channels: {e}")
    return []

def save_dynamic_channels(channels):
    """Save dynamic channel list to file."""
    try:
        with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
            json.dump(channels, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f"Failed to save dynamic channels: {e}")

# =============================================================================
# TELEGRAM THREAT NOTIFICATION
# =============================================================================
def send_telegram_threat_notification(message_text: str, location: str, message_id: str):
    """Send FCM notification for threat messages from Telegram."""
    if not _firebase_initialized or not _messaging:
        return
    
    # Deduplicate - don't send same message within 5 minutes
    with _telegram_alert_lock:
        now = time.time()
        # Clean old entries
        if len(_telegram_alert_sent) > 1000:
            _telegram_alert_sent.clear()
        for mid in list(_telegram_alert_sent.keys()):
            if now - _telegram_alert_sent[mid] > 300:
                del _telegram_alert_sent[mid]
        
        if message_id in _telegram_alert_sent:
            return
        _telegram_alert_sent[message_id] = now
    
    try:
        msg_lower = message_text.lower()
        
        # Determine threat type
        if 'каб' in msg_lower:
            threat_type = 'каби'
            emoji = '💣'
            is_critical = True
        elif 'ракет' in msg_lower or 'балістичн' in msg_lower:
            threat_type = 'ракети'
            emoji = '🚀'
            is_critical = True
        elif 'бпла' in msg_lower or 'дрон' in msg_lower or 'шахед' in msg_lower:
            threat_type = 'дрони'
            emoji = '🛩️'
            is_critical = True
        elif 'вибух' in msg_lower:
            threat_type = 'вибухи'
            emoji = '💥'
            is_critical = True
        else:
            return  # Not a threat message
        
        # Extract region from location
        region_name = location
        city_name = ''
        if '(' in location and 'обл' in location:
            city_match = re.match(r'^([^(]+)\s*\(', location)
            if city_match:
                city_name = city_match.group(1).strip()
            oblast_match = re.search(r'\(([^)]*обл[^)]*)\)', location)
            if oblast_match:
                region_name = oblast_match.group(1).replace('обл.', 'область').strip()
        
        title = f"{emoji} {region_name}"
        tts_location = city_name if city_name else region_name
        
        # Extract message body
        body = message_text
        if ')' in body:
            parts = body.split(')', 1)
            if len(parts) > 1 and parts[1].strip():
                body = parts[1].strip()
        
        # Remove emoji from start
        if body and body[0] in '💣🚀🛩️💥🚨⚠️':
            body = body[1:].strip()
        
        log.info(f"=== TELEGRAM THREAT NOTIFICATION ===")
        log.info(f"Location: {location} -> {region_name}")
        log.info(f"Threat: {threat_type}")
        log.info(f"Message: {title} - {body}")
        
        # Get topic for this region
        topic = REGION_TOPIC_MAP.get(region_name)
        
        # Try matching by city
        if not topic and '(' in location:
            city = location.split('(')[0].strip()
            for oblast_name in REGION_TOPIC_MAP.keys():
                if oblast_name.replace(' область', '').lower() in location.lower():
                    topic = REGION_TOPIC_MAP.get(oblast_name)
                    break
        
        if not topic:
            log.info(f"No topic mapping for region: {region_name}")
            return
        
        log.info(f"Sending telegram threat to topic: {topic}")
        
        # Map threat codes to human-readable
        threat_type_readable = {
            'каби': 'Загроза КАБів',
            'ракети': 'Ракетна небезпека',
            'дрони': 'Загроза БПЛА',
            'вибухи': 'Повідомляють про вибухи',
        }.get(threat_type, 'Повітряна тривога')
        
        try:
            tz = pytz.timezone('Europe/Kiev')
            message = _messaging.Message(
                data={
                    'type': 'telegram_threat',
                    'title': title,
                    'body': body,
                    'location': tts_location,
                    'region': region_name,
                    'alarm_state': 'active',
                    'is_critical': 'true' if is_critical else 'false',
                    'threat_type': threat_type_readable,
                    'timestamp': datetime.now(tz).isoformat(),
                    'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                },
                android=_messaging.AndroidConfig(
                    priority='high',
                    ttl=timedelta(seconds=300),
                ),
                apns=_messaging.APNSConfig(
                    headers={
                        'apns-priority': '10',
                        'apns-push-type': 'alert',
                    },
                    payload=_messaging.APNSPayload(
                        aps=_messaging.Aps(
                            alert=_messaging.ApsAlert(title=title, body=body),
                            sound='default',
                            badge=1,
                            content_available=True,
                        ),
                    ),
                ),
                topic=topic,
            )
            
            response = _messaging.send(message)
            log.info(f"✅ Telegram threat notification sent to topic {topic}: {response}")
            
            # Mark region as notified
            with _telegram_alert_lock:
                region_key = region_name.lower()
                _telegram_region_notified[region_key] = time.time()
                if '(' in location:
                    city = location.split('(')[0].strip().lower()
                    _telegram_region_notified[city] = time.time()
                log.info(f"Marked region '{region_key}' as telegram-notified")
                
        except Exception as e:
            log.error(f"Failed to send telegram threat to topic {topic}: {e}")
            
    except Exception as e:
        log.error(f"Error in send_telegram_threat_notification: {e}")

def is_region_telegram_notified(region_name: str) -> bool:
    """Check if region was recently notified via Telegram."""
    with _telegram_alert_lock:
        now = time.time()
        
        # Clean old entries
        for key in list(_telegram_region_notified.keys()):
            if now - _telegram_region_notified[key] > 300:
                del _telegram_region_notified[key]
        
        region_lower = region_name.lower()
        region_root = region_lower.replace('ський район', '').replace('ська область', '').strip()[:6]
        
        for notified_region, timestamp in _telegram_region_notified.items():
            notified_root = notified_region.replace('ський район', '').replace('ська область', '').strip()[:6]
            
            if (notified_region in region_lower or
                region_lower in notified_region or
                (region_root and notified_root and region_root == notified_root)):
                return True
        
        return False

# =============================================================================
# CHAT MESSAGE INTEGRATION
# =============================================================================
def add_telegram_message_to_chat(text: str, location: str, threat_type: str):
    """Add Telegram message to chat history (for display in app)."""
    # This would integrate with the chat module
    # Currently a placeholder for future implementation
    pass

def add_system_chat_message(text: str, message_type: str = 'system'):
    """Add system message to chat."""
    # This would integrate with the chat module
    pass

# =============================================================================
# BALLISTIC STATE TRACKING
# =============================================================================
_ballistic_state = {'active': False, 'regions': [], 'last_update': 0}
_ballistic_lock = threading.Lock()

def update_ballistic_state(active: bool, regions: list = None):
    """Update ballistic threat state."""
    global _ballistic_state
    with _ballistic_lock:
        _ballistic_state = {
            'active': active,
            'regions': regions or [],
            'last_update': time.time()
        }

def get_ballistic_state():
    """Get current ballistic threat state."""
    with _ballistic_lock:
        return _ballistic_state.copy()
