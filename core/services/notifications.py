"""
Neptun Alarm - Firebase Cloud Messaging Service
Push notifications to mobile devices
"""
import json
import logging
import base64
import hashlib
import time
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from core.config import FIREBASE_CREDENTIALS, FCM_ENABLED, NOTIFICATION_CACHE_TTL
from core.data.regions import match_region, REGION_ALIASES

log = logging.getLogger(__name__)

# Firebase Admin SDK
firebase_app = None
messaging = None

# Notification deduplication cache
# key: content hash, value: timestamp
_notification_cache: Dict[str, float] = {}


def init_firebase():
    """Initialize Firebase Admin SDK"""
    global firebase_app, messaging
    
    if not FCM_ENABLED:
        log.info("Firebase disabled - no credentials")
        return False
    
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging as fb_messaging
        
        # Decode credentials from base64
        creds_json = base64.b64decode(FIREBASE_CREDENTIALS).decode('utf-8')
        creds_dict = json.loads(creds_json)
        
        cred = credentials.Certificate(creds_dict)
        firebase_app = firebase_admin.initialize_app(cred)
        messaging = fb_messaging
        
        log.info("Firebase initialized successfully")
        return True
        
    except Exception as e:
        log.error(f"Firebase initialization failed: {e}")
        return False


def _get_notification_hash(title: str, body: str, location: str) -> str:
    """Generate hash for notification deduplication"""
    content = f"{title}|{body}|{location}"
    return hashlib.md5(content.encode()).hexdigest()


def _should_send_notification(title: str, body: str, location: str) -> bool:
    """Check if notification should be sent (not duplicate)"""
    global _notification_cache
    
    # Clean old entries
    now = time.time()
    _notification_cache = {
        k: v for k, v in _notification_cache.items()
        if now - v < NOTIFICATION_CACHE_TTL
    }
    
    # Check for duplicate
    hash_key = _get_notification_hash(title, body, location)
    if hash_key in _notification_cache:
        return False
    
    # Mark as sent
    _notification_cache[hash_key] = now
    return True


def send_notification(
    token: str,
    title: str,
    body: str,
    data: Dict = None
) -> bool:
    """
    Send push notification to a single device
    
    Args:
        token: FCM device token
        title: Notification title
        body: Notification body text
        data: Additional data payload
        
    Returns:
        True if sent successfully
    """
    if not messaging:
        return False
    
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            token=token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    priority='high',
                    channel_id='threat_alerts'
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1
                    )
                )
            )
        )
        
        response = messaging.send(message)
        log.debug(f"Notification sent: {response}")
        return True
        
    except Exception as e:
        log.warning(f"Failed to send notification: {e}")
        return False


def send_to_topic(
    topic: str,
    title: str,
    body: str,
    data: Dict = None
) -> bool:
    """Send notification to a topic (all subscribed devices)"""
    if not messaging:
        return False
    
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            topic=topic
        )
        
        response = messaging.send(message)
        log.debug(f"Topic notification sent: {response}")
        return True
        
    except Exception as e:
        log.warning(f"Failed to send topic notification: {e}")
        return False


def broadcast_threat(
    threat_type: str,
    location: str,
    direction: str = None,
    devices: List[Dict] = None
) -> int:
    """
    Broadcast threat notification to relevant devices
    
    Args:
        threat_type: Type of threat (drone, missile, etc)
        location: Location name
        direction: Movement direction
        devices: List of device dicts with 'fcm_token' and 'regions'
        
    Returns:
        Number of notifications sent
    """
    if not messaging or not devices:
        return 0
    
    # Build notification
    title = f"⚠️ Загроза: {threat_type}"
    body = location
    if direction:
        body += f" (напрямок: {direction})"
    
    # Check for duplicate
    if not _should_send_notification(title, body, location):
        log.debug(f"Skipping duplicate notification for {location}")
        return 0
    
    sent_count = 0
    failed_tokens = []
    
    for device in devices:
        token = device.get('fcm_token')
        regions = device.get('regions', [])
        
        if not token:
            continue
        
        # Check if device is subscribed to this region
        if regions and not match_region(location, regions):
            continue
        
        # Send notification
        try:
            success = send_notification(
                token=token,
                title=title,
                body=body,
                data={
                    'type': 'threat',
                    'threat_type': threat_type,
                    'location': location,
                    'direction': direction or '',
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            if success:
                sent_count += 1
            else:
                failed_tokens.append(token)
                
        except Exception as e:
            log.warning(f"Error sending to device: {e}")
            failed_tokens.append(token)
    
    if failed_tokens:
        log.info(f"Failed to send to {len(failed_tokens)} devices")
    
    return sent_count


def cleanup_invalid_token(token: str, devices_store):
    """Remove invalid token from device store"""
    try:
        devices_store.remove_by_token(token)
        log.info(f"Removed invalid FCM token")
    except Exception as e:
        log.warning(f"Failed to remove invalid token: {e}")
