"""
Alarms API blueprint.

Endpoints для отримання статусу тривог.
"""
import logging

from flask import Blueprint, Response, jsonify, request

log = logging.getLogger(__name__)

alarms_bp = Blueprint('alarms', __name__)

# Dependencies (injected)
_alarm_client = None
_alarm_state = None
_district_to_oblast = {}


def init_alarms_api(alarm_client=None, alarm_state=None, district_mapping=None):
    """Initialize alarms API with dependencies."""
    global _alarm_client, _alarm_state, _district_to_oblast
    _alarm_client = alarm_client
    _alarm_state = alarm_state
    _district_to_oblast = district_mapping or {}


@alarms_bp.route('/api/alarms')
@alarms_bp.route('/api/alarms/all')
def get_all_alarms():
    """
    Get all active alarms.

    Returns:
        JSON array of alarm regions with ETag support
    """
    if not _alarm_client:
        return jsonify([])

    try:
        # Get raw data with ETag
        data, etag = _alarm_client.get_alerts_raw()

        # Filter to only active alarms
        result = []
        for region in data:
            if region.get('activeAlerts') and len(region['activeAlerts']) > 0:
                result.append({
                    'regionId': region.get('regionId'),
                    'regionName': region.get('regionName'),
                    'regionType': region.get('regionType'),
                    'activeAlerts': region.get('activeAlerts'),
                })

        # Check ETag for 304 response
        if etag:
            client_etag = request.headers.get('If-None-Match')
            if client_etag == etag:
                return Response(status=304, headers={'ETag': etag})

        resp = jsonify(result)
        resp.headers['Cache-Control'] = 'public, max-age=30'
        if etag:
            resp.headers['ETag'] = etag
        return resp

    except Exception as e:
        log.error(f"Error in /api/alarms: {e}")
        return jsonify([])


@alarms_bp.route('/api/alarms/proxy')
def alarm_proxy():
    """
    Proxy for ukrainealarm.com API - returns grouped by State/District.

    Legacy endpoint for backwards compatibility.
    """
    if not _alarm_client:
        return jsonify({'states': [], 'districts': [], 'totalAlerts': 0})

    try:
        data, _ = _alarm_client.get_alerts_raw()

        states = []
        districts = []

        for region in data:
            if not region.get('activeAlerts') or len(region['activeAlerts']) == 0:
                continue

            region_type = region.get('regionType', '')
            region_name = region.get('regionName', '')

            alert_info = {
                'regionName': region_name,
                'regionType': region_type,
                'activeAlerts': region.get('activeAlerts'),
            }

            if region_type == 'State':
                states.append(alert_info)
            elif region_type == 'District':
                oblast = _district_to_oblast.get(region_name, '')
                alert_info['oblast'] = oblast
                districts.append(alert_info)

        return jsonify({
            'states': states,
            'districts': districts,
            'totalAlerts': len(states) + len(districts),
        })

    except Exception as e:
        log.error(f"Error in alarm_proxy: {e}")
        return jsonify({
            'states': [],
            'districts': [],
            'totalAlerts': 0,
            'error': str(e),
        })


@alarms_bp.route('/api/alarms/oblasts')
def get_oblast_alarms():
    """Get only oblast-level alarms."""
    if not _alarm_client:
        return jsonify([])

    try:
        regions = _alarm_client.get_active_oblasts()
        return jsonify([r.to_dict() for r in regions])
    except Exception as e:
        log.error(f"Error in /api/alarms/oblasts: {e}")
        return jsonify([])


@alarms_bp.route('/api/alarms/districts')
def get_district_alarms():
    """Get only district-level alarms."""
    if not _alarm_client:
        return jsonify([])

    try:
        regions = _alarm_client.get_active_districts()
        result = []
        for r in regions:
            d = r.to_dict()
            # Add oblast mapping
            d['oblast'] = _district_to_oblast.get(r.region_name, '')
            result.append(d)
        return jsonify(result)
    except Exception as e:
        log.error(f"Error in /api/alarms/districts: {e}")
        return jsonify([])


@alarms_bp.route('/api/alarms/status')
def get_alarm_status():
    """Get alarm monitoring status."""
    result = {
        'client_configured': _alarm_client is not None,
        'state_configured': _alarm_state is not None,
    }

    if _alarm_client:
        result['client_stats'] = _alarm_client.stats()

    if _alarm_state:
        result['state_stats'] = _alarm_state.stats()

    return jsonify(result)


@alarms_bp.route('/api/alarms/count')
def get_alarm_count():
    """Get quick count of active alarms."""
    if not _alarm_client:
        return jsonify({'count': 0})

    try:
        regions = _alarm_client.get_active_regions()
        oblasts = sum(1 for r in regions if r.is_oblast)
        districts = sum(1 for r in regions if r.is_district)

        return jsonify({
            'total': len(regions),
            'oblasts': oblasts,
            'districts': districts,
        })
    except Exception as e:
        log.error(f"Error in /api/alarms/count: {e}")
        return jsonify({'count': 0, 'error': str(e)})
