"""
Data API blueprint.

Endpoint для отримання треків/маркерів для карти.
"""
import logging
import time
from functools import wraps
from typing import Callable

from flask import Blueprint, jsonify, request

log = logging.getLogger(__name__)

data_bp = Blueprint('data', __name__)


# Rate limiting decorator
def rate_limit(requests_per_minute: int = 60):
    """Simple rate limiting decorator."""
    request_times = {}

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get client identifier
            client_id = request.headers.get('X-Forwarded-For', request.remote_addr)
            now = time.time()

            # Clean old entries
            cutoff = now - 60
            if client_id in request_times:
                request_times[client_id] = [
                    t for t in request_times[client_id]
                    if t > cutoff
                ]
            else:
                request_times[client_id] = []

            # Check limit
            if len(request_times[client_id]) >= requests_per_minute:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': 60,
                }), 429

            # Record this request
            request_times[client_id].append(now)

            return f(*args, **kwargs)
        return wrapper
    return decorator


# Dependency injection - these will be set by the app
_track_store = None
_geocoder = None
_get_legacy_data = None  # Fallback to old app.py function


def init_data_api(track_store=None, geocoder=None, legacy_data_fn=None):
    """Initialize data API with dependencies."""
    global _track_store, _geocoder, _get_legacy_data
    _track_store = track_store
    _geocoder = geocoder
    _get_legacy_data = legacy_data_fn


@data_bp.route('/data')
@rate_limit(requests_per_minute=120)
def get_data():
    """
    Get all current track markers for the map.

    Returns:
        JSON object with tracks, events, metadata (compatible with app.py format)
    """
    try:
        tracks = []
        events = []
        
        # If we have the new track store, use it
        if _track_store:
            markers = _track_store.to_api_format(include_hidden=False)
            tracks = markers

        # Fall back to legacy function
        elif _get_legacy_data:
            return _get_legacy_data()

        # Build response in app.py compatible format
        response_data = {
            'tracks': tracks,
            'events': events,
            'all_sources': [],  # TODO: add channel list
            'ballistic_threat': {
                'active': False,
                'region': None,
                'timestamp': None,
            },
            'threat_tracking': None,
            'ai_ttl': {
                'enabled': False,
                'stats': None
            },
            '_meta': {
                'tracks_total': len(tracks),
                'tracks_returned': len(tracks),
                'tracks_truncated': False,
                'events_total': len(events),
                'events_returned': len(events),
                'events_truncated': False,
                'time_range_minutes': 60,
            }
        }
        
        return jsonify(response_data)

    except Exception as e:
        log.error(f"Error in /data endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@data_bp.route('/data/recent')
@rate_limit(requests_per_minute=60)
def get_recent_data():
    """
    Get tracks from the last N minutes.

    Query params:
        minutes: int (default 60)
    """
    try:
        minutes = request.args.get('minutes', 60, type=int)
        minutes = max(1, min(1440, minutes))  # Clamp to 1-1440

        if _track_store:
            tracks = _track_store.get_recent(minutes=minutes, include_hidden=False)
            result = [
                {
                    'id': t.id,
                    'lat': t.lat,
                    'lng': t.lng,
                    'place': t.place or '',
                    'text': t.text[:300] if t.text else '',
                    'date': t.timestamp.strftime('%Y-%m-%d %H:%M:%S') if t.timestamp else '',
                    'type': t.threat_type or 'unknown',
                }
                for t in tracks
                if t.lat is not None and t.lng is not None
            ]
            return jsonify(result)

        return jsonify([])

    except Exception as e:
        log.error(f"Error in /data/recent: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@data_bp.route('/data/stats')
def get_data_stats():
    """
    Get track statistics.

    Returns:
        JSON object with counts and metadata
    """
    try:
        if _track_store:
            # Get counts
            total = _track_store.count(include_hidden=True)
            visible = _track_store.count(include_hidden=False)
            pending = len(_track_store.get_ungeocodeded())

            # Get type breakdown
            tracks = _track_store.get_all(include_hidden=False)
            by_type = {}
            for t in tracks:
                threat_type = t.threat_type or 'unknown'
                by_type[threat_type] = by_type.get(threat_type, 0) + 1

            return jsonify({
                'total': total,
                'visible': visible,
                'pending_geocode': pending,
                'by_type': by_type,
            })

        return jsonify({
            'total': 0,
            'visible': 0,
            'pending_geocode': 0,
            'by_type': {},
        })

    except Exception as e:
        log.error(f"Error in /data/stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@data_bp.route('/data/by-oblast/<oblast>')
@rate_limit(requests_per_minute=30)
def get_data_by_oblast(oblast: str):
    """
    Get tracks for a specific oblast.

    Args:
        oblast: Oblast name (partial match)
    """
    try:
        if not oblast or len(oblast) < 2:
            return jsonify({'error': 'Invalid oblast parameter'}), 400

        if _track_store:
            tracks = _track_store.get_by_oblast(oblast)
            result = [
                {
                    'id': t.id,
                    'lat': t.lat,
                    'lng': t.lng,
                    'place': t.place or '',
                    'text': t.text[:300] if t.text else '',
                    'date': t.timestamp.strftime('%Y-%m-%d %H:%M:%S') if t.timestamp else '',
                    'type': t.threat_type or 'unknown',
                }
                for t in tracks
                if t.lat is not None and t.lng is not None
            ]
            return jsonify(result)

        return jsonify([])

    except Exception as e:
        log.error(f"Error in /data/by-oblast: {e}")
        return jsonify({'error': 'Internal server error'}), 500
