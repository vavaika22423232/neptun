"""
Admin API blueprint.

Endpoints для адміністрування:
- Ручні маркери
- Статистика
- Налаштування
"""
import os
import time
import uuid
import logging
from datetime import datetime
from functools import wraps
from typing import Callable, Optional, Dict, Any, List

from flask import Blueprint, jsonify, request, Response

log = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Dependencies (injected)
_admin_secret: Optional[str] = None
_track_store = None
_load_messages_fn = None
_save_messages_fn = None


def init_admin_api(
    admin_secret: Optional[str] = None,
    track_store=None,
    load_messages_fn=None,
    save_messages_fn=None,
):
    """Initialize admin API with dependencies."""
    global _admin_secret, _track_store, _load_messages_fn, _save_messages_fn
    _admin_secret = admin_secret
    _track_store = track_store
    _load_messages_fn = load_messages_fn
    _save_messages_fn = save_messages_fn


def require_secret(f: Callable) -> Callable:
    """Decorator to require admin secret."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if _admin_secret:
            # Check header or query param
            provided = request.headers.get('X-Admin-Secret') or request.args.get('secret')
            if provided != _admin_secret:
                return Response('Forbidden', status=403)
        return f(*args, **kwargs)
    return wrapper


def safe_float(val) -> Optional[float]:
    """Safely convert to float."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


# Ukraine bounding box
UKRAINE_BOUNDS = {
    'lat_min': 43.0,
    'lat_max': 53.8,
    'lng_min': 21.0,
    'lng_max': 41.5,
}

ALLOWED_THREAT_TYPES = {
    'shahed', 'raketa', 'avia', 'pvo', 'vibuh', 
    'alarm', 'alarm_cancel', 'mlrs', 'artillery', 
    'obstril', 'fpv', 'pusk', 'manual', 'drone',
    'rocket', 'kab', 'ballistic',
}


@admin_bp.route('/add_manual_marker', methods=['POST'])
@require_secret
def add_manual_marker():
    """
    Add a manual marker.
    
    JSON body:
        lat: float - latitude
        lng: float - longitude  
        text: str - marker text
        place: str - place name (optional)
        threat_type: str - type of threat
        rotation: float - rotation angle (optional)
    """
    payload = request.get_json(silent=True) or {}
    
    try:
        # Validate coordinates
        lat = safe_float(payload.get('lat'))
        lng = safe_float(payload.get('lng'))
        
        if lat is None or lng is None:
            return jsonify({'status': 'error', 'error': 'invalid_coordinates'}), 400
        
        if not (UKRAINE_BOUNDS['lat_min'] <= lat <= UKRAINE_BOUNDS['lat_max']):
            return jsonify({'status': 'error', 'error': 'lat_out_of_bounds'}), 400
        
        if not (UKRAINE_BOUNDS['lng_min'] <= lng <= UKRAINE_BOUNDS['lng_max']):
            return jsonify({'status': 'error', 'error': 'lng_out_of_bounds'}), 400
        
        # Validate text
        text = (payload.get('text') or '').strip()
        if not text:
            return jsonify({'status': 'error', 'error': 'empty_text'}), 400
        
        # Optional fields
        place = (payload.get('place') or '').strip()
        threat_type = (payload.get('threat_type') or 'manual').strip().lower()
        if threat_type not in ALLOWED_THREAT_TYPES:
            threat_type = 'manual'
        
        rotation = safe_float(payload.get('rotation')) or 0
        
        # Course info
        course_direction = (payload.get('course_direction') or '').strip() or None
        course_target = (payload.get('course_target') or '').strip() or None
        course_source = (payload.get('course_source') or '').strip() or place or None
        
        # Generate ID and timestamp
        marker_id = f'manual-{uuid.uuid4().hex[:12]}'
        try:
            import pytz
            tz = pytz.timezone('Europe/Kyiv')
            now_dt = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        except ImportError:
            now_dt = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build marker
        marker = {
            'id': marker_id,
            'date': now_dt,
            'text': text,
            'place': place,
            'lat': round(lat, 6),
            'lng': round(lng, 6),
            'threat_type': threat_type,
            'rotation': rotation,
            'manual': True,
            'channel': 'manual',
            'source': 'manual',
        }
        
        if course_direction:
            marker['course_direction'] = course_direction
        if course_target:
            marker['course_target'] = course_target
        if course_source:
            marker['course_source'] = course_source
        
        # Save using provided function or track store
        if _load_messages_fn and _save_messages_fn:
            messages = _load_messages_fn()
            messages.append(marker)
            _save_messages_fn(messages)
        elif _track_store:
            from services.tracks.store import TrackEntry
            entry = TrackEntry(
                id=marker_id,
                text=text,
                timestamp=datetime.strptime(now_dt, '%Y-%m-%d %H:%M:%S'),
                lat=lat,
                lng=lng,
                place=place,
                threat_type=threat_type,
                manual=True,
            )
            _track_store.add(entry)
        
        log.info(f"Added manual marker: {marker_id} at ({lat}, {lng})")
        return jsonify({'status': 'ok', 'id': marker_id})
        
    except Exception as e:
        log.error(f"Error adding manual marker: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 400


@admin_bp.route('/update_manual_marker', methods=['POST'])
@require_secret
def update_manual_marker():
    """Update existing manual marker."""
    payload = request.get_json(silent=True) or {}
    marker_id = (payload.get('id') or '').strip()
    
    if not marker_id:
        return jsonify({'status': 'error', 'error': 'missing_id'}), 400
    
    try:
        lat = safe_float(payload.get('lat'))
        lng = safe_float(payload.get('lng'))
        
        if lat is None or lng is None:
            return jsonify({'status': 'error', 'error': 'invalid_coordinates'}), 400
        
        text = (payload.get('text') or '').strip()
        if not text:
            return jsonify({'status': 'error', 'error': 'empty_text'}), 400
        
        place = (payload.get('place') or '').strip()
        threat_type = (payload.get('threat_type') or 'manual').strip().lower()
        if threat_type not in ALLOWED_THREAT_TYPES:
            threat_type = 'manual'
        
        # Update via provided function
        if _load_messages_fn and _save_messages_fn:
            messages = _load_messages_fn()
            found = False
            for msg in messages:
                if msg.get('id') == marker_id:
                    msg['lat'] = round(lat, 6)
                    msg['lng'] = round(lng, 6)
                    msg['text'] = text
                    msg['place'] = place
                    msg['threat_type'] = threat_type
                    found = True
                    break
            
            if not found:
                return jsonify({'status': 'error', 'error': 'marker_not_found'}), 404
            
            _save_messages_fn(messages)
        elif _track_store:
            success = _track_store.update(
                marker_id,
                lat=lat,
                lng=lng,
                text=text,
                place=place,
                threat_type=threat_type,
            )
            if not success:
                return jsonify({'status': 'error', 'error': 'marker_not_found'}), 404
        
        log.info(f"Updated manual marker: {marker_id}")
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        log.error(f"Error updating manual marker: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 400


@admin_bp.route('/delete_manual_marker', methods=['POST'])
@require_secret
def delete_manual_marker():
    """Delete a manual marker."""
    payload = request.get_json(silent=True) or {}
    marker_id = (payload.get('id') or '').strip()
    
    if not marker_id:
        return jsonify({'status': 'error', 'error': 'missing_id'}), 400
    
    try:
        if _load_messages_fn and _save_messages_fn:
            messages = _load_messages_fn()
            original_len = len(messages)
            messages = [m for m in messages if m.get('id') != marker_id]
            
            if len(messages) == original_len:
                return jsonify({'status': 'error', 'error': 'marker_not_found'}), 404
            
            _save_messages_fn(messages)
        elif _track_store:
            success = _track_store.remove(marker_id)
            if not success:
                return jsonify({'status': 'error', 'error': 'marker_not_found'}), 404
        
        log.info(f"Deleted manual marker: {marker_id}")
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        log.error(f"Error deleting manual marker: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 400


@admin_bp.route('/markers')
@require_secret
def list_markers():
    """List all markers (for admin panel)."""
    try:
        markers = []
        
        if _load_messages_fn:
            messages = _load_messages_fn()
            markers = [
                {
                    'id': m.get('id'),
                    'lat': m.get('lat'),
                    'lng': m.get('lng'),
                    'text': (m.get('text') or '')[:100],
                    'place': m.get('place'),
                    'type': m.get('threat_type'),
                    'date': m.get('date'),
                    'manual': m.get('manual', False),
                }
                for m in messages
                if m.get('lat') and m.get('lng')
            ]
        elif _track_store:
            tracks = _track_store.get_all(include_hidden=True)
            markers = [
                {
                    'id': t.id,
                    'lat': t.lat,
                    'lng': t.lng,
                    'text': (t.text or '')[:100],
                    'place': t.place,
                    'type': t.threat_type,
                    'date': t.timestamp.strftime('%Y-%m-%d %H:%M:%S') if t.timestamp else '',
                    'manual': t.manual,
                }
                for t in tracks
                if t.lat and t.lng
            ]
        
        return jsonify(markers)
        
    except Exception as e:
        log.error(f"Error listing markers: {e}")
        return jsonify([])


@admin_bp.route('/stats')
@require_secret
def admin_stats():
    """Get admin statistics."""
    stats = {
        'timestamp': time.time(),
    }
    
    if _track_store:
        stats['tracks'] = {
            'total': _track_store.count(include_hidden=True),
            'visible': _track_store.count(include_hidden=False),
            'manual': sum(1 for t in _track_store.get_all(include_hidden=True) if t.manual),
        }
    
    return jsonify(stats)


@admin_bp.route('/config', methods=['GET', 'POST'])
@require_secret
def admin_config():
    """Get or update configuration."""
    if request.method == 'GET':
        # Return current config (non-sensitive)
        return jsonify({
            'message': 'Use POST to update settings',
        })
    
    # POST - update config
    payload = request.get_json(silent=True) or {}
    
    # Handle specific settings
    updated = {}
    
    # Example: monitor period
    if 'monitor_period' in payload:
        try:
            period = int(payload['monitor_period'])
            if 1 <= period <= 360:
                updated['monitor_period'] = period
        except (ValueError, TypeError):
            pass
    
    return jsonify({'status': 'ok', 'updated': updated})
