"""
API Blueprint for tracks and threats.

Ендпоінти для отримання треків, активних загроз,
історії та статистики.

Працює з TrackEntry з services.tracks.store.
"""
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

tracks_bp = Blueprint('tracks', __name__, url_prefix='/api/tracks')


def track_entry_to_dict(entry) -> Dict[str, Any]:
    """Convert TrackEntry to API response format."""
    return {
        'id': entry.id,
        'coordinates': {
            'lat': entry.lat,
            'lng': entry.lng,
        },
        'lat': entry.lat,
        'lng': entry.lng,
        'threat_type': entry.threat_type or 'unknown',
        'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
        'location': entry.place,
        'place': entry.place,
        'oblast': entry.oblast,
        'direction': entry.direction,
        'source': entry.source,
        'target': entry.target,
        'count': entry.count,
        'text': entry.text[:200] if entry.text else '',
        'channel': entry.channel,
    }


@tracks_bp.route('/', methods=['GET'])
@tracks_bp.route('/active', methods=['GET'])
def get_active_tracks():
    """
    Get active tracks.
    
    Query params:
        - max_age: Maximum age in minutes (default: 60)
        - threat_type: Filter by threat type
        - region: Filter by region/oblast
        - limit: Maximum number of results
    """
    track_store = current_app.extensions.get('track_store')
    if not track_store:
        return jsonify({'error': 'Track store not configured'}), 503
    
    # Parse parameters
    max_age = request.args.get('max_age', 60, type=int)
    threat_type = request.args.get('threat_type')
    region = request.args.get('region')
    limit = request.args.get('limit', 100, type=int)
    
    # Get active markers
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age)
    entries = track_store.get_active(since=cutoff)
    
    # Apply filters
    if threat_type:
        entries = [e for e in entries if e.threat_type == threat_type]
    
    if region:
        region_lower = region.lower()
        entries = [e for e in entries 
                  if (e.oblast and region_lower in e.oblast.lower()) or
                     (e.place and region_lower in e.place.lower())]
    
    # Apply limit
    entries = entries[:limit]
    
    # Convert to response format
    tracks = [track_entry_to_dict(e) for e in entries if e.lat and e.lng]
    
    return jsonify({
        'tracks': tracks,
        'count': len(tracks),
        'max_age_minutes': max_age,
    })


@tracks_bp.route('/history', methods=['GET'])
def get_track_history():
    """
    Get track history.
    
    Query params:
        - hours: Number of hours to look back (default: 24)
        - threat_type: Filter by threat type
        - region: Filter by region
        - page: Page number (default: 1)
        - per_page: Items per page (default: 50)
    """
    track_store = current_app.extensions.get('track_store')
    if not track_store:
        return jsonify({'error': 'Track store not configured'}), 503
    
    # Parse parameters
    hours = request.args.get('hours', 24, type=int)
    threat_type = request.args.get('threat_type')
    region = request.args.get('region')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Get history
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_entries = track_store.get_all()
    
    # Filter by time
    entries = [e for e in all_entries if e.timestamp and e.timestamp >= cutoff]
    
    # Apply filters
    if threat_type:
        entries = [e for e in entries if e.threat_type == threat_type]
    
    if region:
        region_lower = region.lower()
        entries = [e for e in entries 
                  if (e.oblast and region_lower in e.oblast.lower()) or
                     (e.place and region_lower in e.place.lower())]
    
    # Sort by timestamp (newest first)
    entries.sort(key=lambda e: e.timestamp or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    
    # Paginate
    total = len(entries)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = entries[start:end]
    
    # Convert to response
    history = [track_entry_to_dict(e) for e in paginated if e.lat and e.lng]
    
    return jsonify({
        'history': history,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
        },
    })


@tracks_bp.route('/stats', methods=['GET'])
def get_track_stats():
    """Get track statistics."""
    track_store = current_app.extensions.get('track_store')
    pipeline = current_app.extensions.get('pipeline')
    
    store_stats = track_store.stats() if track_store else {}
    pipeline_stats = pipeline.stats() if pipeline else {}
    
    return jsonify({
        'store': store_stats,
        'pipeline': pipeline_stats,
    })


@tracks_bp.route('/by-type', methods=['GET'])
def get_tracks_by_type():
    """
    Get tracks grouped by threat type.
    
    Query params:
        - max_age: Maximum age in minutes (default: 60)
    """
    track_store = current_app.extensions.get('track_store')
    if not track_store:
        return jsonify({'error': 'Track store not configured'}), 503
    
    max_age = request.args.get('max_age', 60, type=int)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age)
    entries = track_store.get_active(since=cutoff)
    
    # Group by type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        if not entry.lat or not entry.lng:
            continue
        
        ttype = entry.threat_type or 'unknown'
        if ttype not in by_type:
            by_type[ttype] = []
        by_type[ttype].append(track_entry_to_dict(entry))
    
    return jsonify({
        'by_type': by_type,
        'types': list(by_type.keys()),
        'counts': {k: len(v) for k, v in by_type.items()},
    })


@tracks_bp.route('/by-region', methods=['GET'])
def get_tracks_by_region():
    """
    Get tracks grouped by region/oblast.
    
    Query params:
        - max_age: Maximum age in minutes (default: 60)
    """
    track_store = current_app.extensions.get('track_store')
    if not track_store:
        return jsonify({'error': 'Track store not configured'}), 503
    
    max_age = request.args.get('max_age', 60, type=int)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age)
    entries = track_store.get_active(since=cutoff)
    
    # Group by oblast
    by_region: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        if not entry.lat or not entry.lng:
            continue
        
        oblast = entry.oblast or 'unknown'
        if oblast not in by_region:
            by_region[oblast] = []
        by_region[oblast].append(track_entry_to_dict(entry))
    
    return jsonify({
        'by_region': by_region,
        'regions': list(by_region.keys()),
        'counts': {k: len(v) for k, v in by_region.items()},
    })


@tracks_bp.route('/geojson', methods=['GET'])
def get_tracks_geojson():
    """
    Get tracks as GeoJSON FeatureCollection.
    
    Query params:
        - max_age: Maximum age in minutes (default: 60)
        - threat_type: Filter by threat type
    """
    track_store = current_app.extensions.get('track_store')
    if not track_store:
        return jsonify({'error': 'Track store not configured'}), 503
    
    max_age = request.args.get('max_age', 60, type=int)
    threat_type = request.args.get('threat_type')
    
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age)
    entries = track_store.get_active(since=cutoff)
    
    if threat_type:
        entries = [e for e in entries if e.threat_type == threat_type]
    
    # Build GeoJSON
    features = []
    for entry in entries:
        if not entry.lat or not entry.lng:
            continue
        
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [entry.lng, entry.lat],  # GeoJSON: [lng, lat]
            },
            'properties': {
                'id': entry.id,
                'threat_type': entry.threat_type or 'unknown',
                'place': entry.place,
                'oblast': entry.oblast,
                'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                'direction': entry.direction,
                'source': entry.source,
                'target': entry.target,
            },
        }
        features.append(feature)
    
    return jsonify({
        'type': 'FeatureCollection',
        'features': features,
    })


@tracks_bp.route('/<track_id>', methods=['GET'])
def get_single_track(track_id: str):
    """Get single track by ID."""
    track_store = current_app.extensions.get('track_store')
    if not track_store:
        return jsonify({'error': 'Track store not configured'}), 503
    
    entry = track_store.get(track_id)
    if not entry:
        return jsonify({'error': 'Track not found'}), 404
    
    return jsonify(track_entry_to_dict(entry))


@tracks_bp.route('/<track_id>', methods=['DELETE'])
def delete_track(track_id: str):
    """
    Delete a track.
    
    Requires admin authorization.
    """
    # Check auth
    auth_header = request.headers.get('Authorization', '')
    admin_secret = current_app.config.get('ADMIN_API_KEY')
    
    if not admin_secret:
        return jsonify({'error': 'Admin API not configured'}), 503
    
    expected = f'Bearer {admin_secret}'
    if auth_header != expected:
        return jsonify({'error': 'Unauthorized'}), 401
    
    track_store = current_app.extensions.get('track_store')
    if not track_store:
        return jsonify({'error': 'Track store not configured'}), 503
    
    removed = track_store.remove(track_id)
    if removed:
        return jsonify({'success': True, 'deleted': track_id})
    else:
        return jsonify({'error': 'Track not found'}), 404


@tracks_bp.route('/<track_id>/hide', methods=['POST'])
def hide_track(track_id: str):
    """
    Hide a track (soft delete).
    
    Requires admin authorization.
    """
    # Check auth
    auth_header = request.headers.get('Authorization', '')
    admin_secret = current_app.config.get('ADMIN_API_KEY')
    
    if not admin_secret:
        return jsonify({'error': 'Admin API not configured'}), 503
    
    expected = f'Bearer {admin_secret}'
    if auth_header != expected:
        return jsonify({'error': 'Unauthorized'}), 401
    
    track_store = current_app.extensions.get('track_store')
    if not track_store:
        return jsonify({'error': 'Track store not configured'}), 503
    
    hidden = track_store.hide(track_id)
    if hidden:
        return jsonify({'success': True, 'hidden': track_id})
    else:
        return jsonify({'error': 'Track not found'}), 404


# Export
__all__ = ['tracks_bp']
