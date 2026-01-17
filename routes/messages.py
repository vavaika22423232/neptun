# Messages module - Message storage, loading, saving, and deduplication
# Extracted from app.py for better code organization

import os
import json
import time
import logging
import random
from datetime import datetime, timedelta
from math import radians, sin, cos, asin, sqrt

import pytz
from flask import Blueprint, jsonify, request

from .config import RESPONSE_CACHE, get_kyiv_now, UKRAINE_ADDRESSES_DB

log = logging.getLogger(__name__)

# Create blueprint (currently no routes, used for shared message functions)
messages_bp = Blueprint('messages', __name__)

# =============================================================================
# MESSAGES CONFIGURATION
# =============================================================================
MESSAGES_FILE = os.getenv('MESSAGES_FILE', 'messages.json')
HIDDEN_FILE = 'hidden_messages.json'
BLOCKED_FILE = 'blocked_ids.json'
MESSAGES_RETENTION_MINUTES = int(os.getenv('MESSAGES_RETENTION_MINUTES', '0'))  # 0 = no time pruning
MESSAGES_MAX_COUNT = int(os.getenv('MESSAGES_MAX_COUNT', '2000'))

# Deduplication configuration
DEDUP_ENABLED = False  # Set to True to enable merging
DEDUP_TIME_MIN = int(os.getenv('DEDUP_TIME_MIN', '5'))
DEDUP_DIST_KM = float(os.getenv('DEDUP_DIST_KM', '7'))
DEDUP_SCAN_BACK = int(os.getenv('DEDUP_SCAN_BACK', '400'))

# =============================================================================
# MESSAGE CACHE
# =============================================================================
_MESSAGES_CACHE = {'data': None, 'expires': 0}
_MESSAGES_CACHE_TTL = 5  # 5 second cache

def load_messages_cached():
    """Load messages with caching to reduce disk I/O."""
    global _MESSAGES_CACHE
    now = time.time()
    if _MESSAGES_CACHE['data'] is not None and now < _MESSAGES_CACHE['expires']:
        return _MESSAGES_CACHE['data']
    # Load fresh
    data = load_messages()
    _MESSAGES_CACHE = {'data': data, 'expires': now + _MESSAGES_CACHE_TTL}
    return data

def invalidate_messages_cache():
    """Invalidate messages cache - call after saving."""
    global _MESSAGES_CACHE
    _MESSAGES_CACHE = {'data': None, 'expires': 0}

# =============================================================================
# MESSAGE PRUNING
# =============================================================================
def _prune_messages(data):
    """Apply retention policies (time / count). Mutates and returns list."""
    if not data:
        return data
    
    # Time based pruning
    if MESSAGES_RETENTION_MINUTES > 0:
        cutoff = datetime.utcnow() - timedelta(minutes=MESSAGES_RETENTION_MINUTES)
        pruned = []
        for m in data:
            if m.get('manual'):
                pruned.append(m)
                continue
            try:
                dt = datetime.strptime(m.get('date', ''), '%Y-%m-%d %H:%M:%S')
            except Exception:
                pruned.append(m)
                continue
            if dt.replace(tzinfo=None) >= cutoff:
                pruned.append(m)
        data = pruned
    
    # Count based pruning (keep newest by date)
    if MESSAGES_MAX_COUNT > 0 and len(data) > MESSAGES_MAX_COUNT:
        try:
            manual_items = [m for m in data if m.get('manual')]
            auto_items = [m for m in data if not m.get('manual')]
            allow_auto = max(0, MESSAGES_MAX_COUNT - len(manual_items))
            if len(auto_items) > allow_auto:
                auto_items = sorted(auto_items, key=lambda x: x.get('date', ''))[-allow_auto:]
            combined = manual_items + auto_items
            data = sorted(combined, key=lambda x: x.get('date', ''))
        except Exception:
            data = data[-MESSAGES_MAX_COUNT:]
    
    return data

# =============================================================================
# MESSAGE FILE OPERATIONS
# =============================================================================
def load_messages():
    """Load messages from JSON file."""
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.warning(f'Failed to load messages: {e}')
    return []

def save_messages(data, prune=True):
    """Save messages to JSON file with optional pruning."""
    try:
        if prune:
            data = _prune_messages(data)
        
        invalidate_messages_cache()
        
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return data
    except Exception as e:
        log.error(f'Failed to save messages: {e}')
        return data

# =============================================================================
# HIDDEN MESSAGES
# =============================================================================
def load_hidden():
    """Load hidden message IDs."""
    if os.path.exists(HIDDEN_FILE):
        try:
            with open(HIDDEN_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_hidden(data):
    """Save hidden message IDs."""
    try:
        with open(HIDDEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f'Failed saving hidden: {e}')

# =============================================================================
# BLOCKED IDS
# =============================================================================
def load_blocked():
    """Load blocked IDs."""
    if os.path.exists(BLOCKED_FILE):
        try:
            with open(BLOCKED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_blocked(blocked):
    """Save blocked IDs."""
    try:
        with open(BLOCKED_FILE, 'w', encoding='utf-8') as f:
            json.dump(blocked, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f'Failed saving blocked: {e}')

# =============================================================================
# DEDUPLICATION / MERGE FUNCTIONS
# =============================================================================
def _parse_dt(s: str):
    """Parse datetime string."""
    try:
        return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None

def _haversine_km(lat1, lon1, lat2, lon2):
    """Calculate haversine distance in km between two points."""
    try:
        R = 6371.0
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        return R * c
    except Exception:
        return 999999

def maybe_merge_track(all_data: list, new_track: dict):
    """Try to merge new_track into an existing recent track.
    Returns tuple (merged: bool, track_ref: dict).
    
    If DEDUP_ENABLED is False, adds small random offset to prevent overlapping.
    """
    # If dedup disabled, add small offset and return as new track
    if not DEDUP_ENABLED:
        lat = new_track.get('lat')
        lng = new_track.get('lng')
        if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
            # Add small random offset (about 500m-1.5km)
            offset_lat = random.uniform(-0.012, 0.012)
            offset_lng = random.uniform(-0.015, 0.015)
            new_track['lat'] = lat + offset_lat
            new_track['lng'] = lng + offset_lng
        return False, new_track
    
    try:
        if not all_data:
            return False, new_track
        
        tt = (new_track.get('threat_type') or '').lower()
        if not tt:
            return False, new_track
        
        lat = new_track.get('lat')
        lng = new_track.get('lng')
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            return False, new_track
        
        new_dt = _parse_dt(new_track.get('date', '')) or datetime.utcnow()
        
        # Scan recent slice only for performance
        scan_slice = all_data[-DEDUP_SCAN_BACK:]
        
        # Iterate reversed (newest first)
        for existing in reversed(scan_slice):
            if existing is new_track:
                continue
            if (existing.get('threat_type') or '').lower() != tt:
                continue
            
            e_lat = existing.get('lat')
            e_lng = existing.get('lng')
            if not isinstance(e_lat, (int, float)) or not isinstance(e_lng, (int, float)):
                continue
            
            dist = _haversine_km(lat, lng, e_lat, e_lng)
            if dist > DEDUP_DIST_KM:
                continue
            
            e_dt = _parse_dt(existing.get('date', '')) or new_dt
            dt_min = abs((new_dt - e_dt).total_seconds()) / 60.0
            if dt_min > DEDUP_TIME_MIN:
                continue
            
            # Merge
            existing['count'] = int(existing.get('count') or 1) + 1
            
            # Merge text
            new_text = (new_track.get('text') or '').strip()
            if new_text:
                ex_text = existing.get('text') or ''
                if new_text not in ex_text:
                    combined = (ex_text + ' | ' + new_text).strip(' |') if ex_text else new_text
                    if len(combined) > 800:
                        combined = combined[:790] + '…'
                    existing['text'] = combined
            
            # Maintain list of merged ids
            if 'merged_ids' not in existing:
                existing['merged_ids'] = [existing.get('id')]
            nid = new_track.get('id')
            if nid and nid not in existing['merged_ids']:
                existing['merged_ids'].append(nid)
            
            # Update date to most recent
            if new_dt >= e_dt:
                existing['date'] = new_track.get('date') or existing.get('date')
            
            # Capture first occurrence time
            if 'first_date' not in existing:
                existing['first_date'] = e_dt.strftime('%Y-%m-%d %H:%M:%S')
            
            existing['merged'] = True
            return True, existing
    except Exception as e:
        log.debug(f'dedup merge error: {e}')
    
    return False, new_track

# =============================================================================
# MESSAGE TIMESTAMP UTILITIES
# =============================================================================
def _msg_timestamp(msg):
    """Extract timestamp from message for sorting and filtering."""
    if not msg:
        return 0
    
    date_str = msg.get('date') or msg.get('timestamp') or msg.get('time')
    if not date_str:
        return 0
    
    try:
        if isinstance(date_str, (int, float)):
            return float(date_str)
        
        if isinstance(date_str, str):
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.timestamp()
                except ValueError:
                    continue
            
            # Fallback to dateutil
            try:
                from dateutil import parser
                dt = parser.parse(date_str)
                return dt.timestamp()
            except:
                pass
    except Exception:
        pass
    
    return 0

# =============================================================================
# NOTIFICATION DEDUPLICATION
# =============================================================================
SENT_NOTIFICATIONS_CACHE = {}
NOTIFICATION_CACHE_TTL = 300  # 5 minutes

def _normalize_location_name(name: str) -> str:
    """Normalize location name for deduplication."""
    if not name:
        return ''
    name = name.lower().strip()
    suffixes = [' район', ' область', ' громада', ' міська', ' селищна', ' сільська',
                ' (міська)', ' (районна)', ' (обласна)', 'ська', 'ський']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    return name.strip()

def _get_notification_hash(msg: dict) -> str:
    """Generate unique hash for notification based on content."""
    import hashlib
    
    place = (msg.get('place', '') or msg.get('location', '') or '')[:100]
    place = _normalize_location_name(place)
    
    msg_type = (msg.get('threat_type', '') or msg.get('type', '') or '')[:50].lower()
    
    # Normalize threat type
    if 'бпла' in msg_type or 'дрон' in msg_type or 'шахед' in msg_type:
        msg_type = 'drone'
    elif 'ракет' in msg_type or 'балістичн' in msg_type or 'крилат' in msg_type:
        msg_type = 'rocket'
    elif 'каб' in msg_type or 'бомб' in msg_type:
        msg_type = 'kab'
    elif 'відбій' in msg_type or 'знято' in msg_type:
        msg_type = 'clear'
    else:
        msg_type = 'alert'
    
    content = f"{place}|{msg_type}"
    return hashlib.md5(content.encode()).hexdigest()

def _should_send_notification(msg: dict) -> bool:
    """Check if notification should be sent (not a duplicate)."""
    global SENT_NOTIFICATIONS_CACHE
    
    msg_hash = _get_notification_hash(msg)
    now = time.time()
    
    # Clean old entries
    SENT_NOTIFICATIONS_CACHE = {
        h: t for h, t in SENT_NOTIFICATIONS_CACHE.items()
        if now - t < NOTIFICATION_CACHE_TTL
    }
    
    if msg_hash in SENT_NOTIFICATIONS_CACHE:
        log.info(f"Skipping duplicate notification (hash: {msg_hash[:8]}...)")
        return False
    
    SENT_NOTIFICATIONS_CACHE[msg_hash] = now
    return True


# =============================================================================
# API ROUTES FOR MESSAGES
# =============================================================================
@messages_bp.route('/api/events')
def get_events():
    """Get recent air alarm events from Telegram."""
    MAX_PROCESS_MESSAGES = 500  # HARD LIMIT: max messages to scan
    MAX_RETURN_EVENTS = 100     # HARD LIMIT: max events to return
    
    try:
        messages = load_messages()
        events = []
        
        # PROTECTION: Only process last 500 messages
        for msg in messages[-MAX_PROCESS_MESSAGES:]:
            if not isinstance(msg, dict):
                continue
                
            text = msg.get('text', '').strip()
            channel = msg.get('channel', '')
            timestamp = msg.get('time', '')
            
            # Detect alarm type by emoji or text
            emoji = None
            status = None
            
            if '🚨' in text or 'Повітряна тривога' in text:
                emoji = '🚨'
                status = 'Повітряна тривога'
            elif '🟢' in text or 'Відбій тривоги' in text or 'відбій тривоги' in text:
                emoji = '🟢'
                status = 'Відбій тривоги'
            else:
                continue
            
            # Extract region from multiple formats
            region = ''
            
            if '**' in text:
                parts = text.split('**')
                for part in parts:
                    part = part.strip()
                    if '🚨' in part or '🟢' in part:
                        region = part.replace('🚨', '').replace('🟢', '').strip()
                        break
            
            # Fallback: extract from first line
            if not region and text:
                first_line = text.split('\n')[0].strip()
                region = first_line.replace('**', '').replace('🚨', '').replace('🟢', '').strip()
                region = region.replace('Повітряна тривога.', '').replace('Прямуйте в укриття!', '').strip()
                region = region.replace('Відбій тривоги.', '').replace('Будьте обережні!', '').strip()
            
            if not region:
                continue
            
            events.append({
                'timestamp': timestamp,
                'channel': channel,
                'emoji': emoji,
                'region': region,
                'status': status,
                'text': text[:200]
            })
        
        # Sort by timestamp (newest first) and return last 100 events
        events.reverse()
        returned_events = events[:MAX_RETURN_EVENTS]
        
        response = jsonify(returned_events)
        response.headers['Cache-Control'] = 'public, max-age=30'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        log.error(f"/api/events failed: {e}")
        return jsonify([]), 500


@messages_bp.route('/api/messages')
def get_messages():
    """Get recent alarm messages with coordinates for mobile apps."""
    # Check cache first (30 second TTL)
    cache_key = 'api_messages'
    cached = RESPONSE_CACHE.get(cache_key)
    if cached:
        response = jsonify(cached)
        response.headers['Cache-Control'] = 'public, max-age=30'
        response.headers['X-Cache'] = 'HIT'
        return response
    
    MAX_MESSAGES = 100  # HARD LIMIT
    
    try:
        messages = load_messages()
        result_messages = []
        kyiv_tz = pytz.timezone('Europe/Kiev')
        
        for msg in messages[-MAX_MESSAGES:]:
            if not isinstance(msg, dict):
                continue
            
            text = msg.get('text', '').strip()
            
            # Detect alarm type
            alarm_type = 'Тривога'
            if 'БпЛА' in text or 'дрон' in text:
                alarm_type = 'БпЛА/Дрони'
            elif 'ракет' in text or 'балістич' in text:
                alarm_type = 'Ракетна загроза'
            elif 'Повітряна тривога' in text:
                alarm_type = 'Повітряна тривога'
            
            # Try to extract location and coordinates
            location = ''
            latitude = 48.3794  # Default: center of Ukraine
            longitude = 31.1656
            
            # Extract region/city from text
            if '**' in text:
                parts = text.split('**')
                for part in parts:
                    part = part.strip()
                    if '🚨' in part or '🟢' in part or 'область' in part.lower():
                        location = part.replace('🚨', '').replace('🟢', '').strip()
                        break
            
            # If no location found, try first line
            if not location and text:
                first_line = text.split('\n')[0].strip()
                location = first_line.replace('**', '').replace('🚨', '').replace('🟢', '').strip()[:100]
            
            # Try to get coordinates from UKRAINE_ADDRESSES_DB
            if location:
                location_lower = location.lower()
                for city_name, coords in UKRAINE_ADDRESSES_DB.items():
                    if city_name.lower() in location_lower or location_lower in city_name.lower():
                        latitude = coords['lat']
                        longitude = coords['lon']
                        if not location:
                            location = city_name
                        break
            
            # Get timestamp in Kyiv time
            msg_time = msg.get('time', '') or msg.get('timestamp', '') or msg.get('date', '')
            
            if not msg_time:
                msg_time = datetime.now(kyiv_tz).strftime('%d.%m.%Y %H:%M')
            else:
                try:
                    if not isinstance(msg_time, str):
                        dt = datetime.fromtimestamp(msg_time, tz=pytz.UTC)
                        msg_time = dt.astimezone(kyiv_tz).strftime('%d.%m.%Y %H:%M')
                except:
                    if isinstance(msg_time, str):
                        pass
                    else:
                        msg_time = datetime.now(kyiv_tz).strftime('%d.%m.%Y %H:%M')
            
            result_messages.append({
                'type': alarm_type,
                'location': location or 'Україна',
                'timestamp': msg_time,
                'text': text[:300],
                'latitude': latitude,
                'longitude': longitude,
                'channel': msg.get('channel', ''),
            })
        
        # Sort by timestamp (newest first)
        result_messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Cache the result
        result_data = {
            'messages': result_messages,
            'count': len(result_messages),
            'timestamp': datetime.now().isoformat()
        }
        RESPONSE_CACHE.set(cache_key, result_data, ttl=30)
        
        response = jsonify(result_data)
        response.headers['Cache-Control'] = 'public, max-age=30'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['X-Cache'] = 'MISS'
        return response
        
    except Exception as e:
        log.error(f"/api/messages failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'messages': [], 'count': 0, 'error': str(e)}), 500


@messages_bp.route('/api/stats')
def get_alarm_stats():
    """Get alarm statistics for a region."""
    try:
        region = request.args.get('region', 'Дніпропетровська')
        
        # Load messages from file to calculate stats
        messages = load_messages()
        filtered_msgs = []
        
        for msg in messages:
            msg_region = msg.get('region', '') or msg.get('location', '')
            if region.lower() in msg_region.lower():
                filtered_msgs.append(msg)
        
        # Calculate stats
        kyiv_tz = pytz.timezone('Europe/Kyiv')
        now = datetime.now(kyiv_tz)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        
        today_count = 0
        week_count = 0
        month_count = 0
        
        for msg in filtered_msgs:
            try:
                timestamp = msg.get('timestamp', '')
                msg_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if msg_time.tzinfo is None:
                    msg_time = kyiv_tz.localize(msg_time)
                
                if msg_time >= today_start:
                    today_count += 1
                if msg_time >= week_start:
                    week_count += 1
                if msg_time >= month_start:
                    month_count += 1
                    
            except (ValueError, TypeError):
                continue
        
        avg_duration = 25  # Default 25 min if no data
        
        return jsonify({
            'region': region,
            'today_alarms': today_count,
            'week_alarms': week_count,
            'month_alarms': month_count,
            'avg_duration_min': avg_duration,
        })
    except Exception as e:
        log.error(f"Error getting stats: {e}")
        return jsonify({
            'today_alarms': 0,
            'week_alarms': 0,
            'month_alarms': 0,
            'avg_duration_min': 0,
        })
