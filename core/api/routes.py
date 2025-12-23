"""
Neptun Alarm - Main API Routes
"""
from flask import Blueprint, jsonify, request, render_template
from datetime import datetime
import logging

from core.services.storage import message_store, device_store, visits_db
from core.utils.helpers import get_kyiv_time

log = logging.getLogger(__name__)

api = Blueprint('api', __name__, url_prefix='/api')


@api.route('/messages')
def get_messages():
    """Get threat messages for map"""
    messages = message_store.get_messages()
    tracks = message_store.get_tracks()
    
    # Filter hidden messages
    show_hidden = request.args.get('show_hidden', 'false').lower() == 'true'
    if not show_hidden:
        messages = [m for m in messages if not m.get('hidden')]
    
    return jsonify({
        'messages': messages,
        'tracks': tracks,
        'timestamp': get_kyiv_time().isoformat(),
        'count': len(messages)
    })


@api.route('/events')
def get_events():
    """Get events for SSE or polling"""
    since = request.args.get('since')
    messages = message_store.get_messages()
    
    if since:
        messages = [m for m in messages if m.get('timestamp', '') > since]
    
    return jsonify({
        'events': messages,
        'timestamp': get_kyiv_time().isoformat()
    })


@api.route('/visitor_count')
def visitor_count():
    """Get visitor statistics"""
    hours = int(request.args.get('hours', 24))
    count = visits_db.get_visitor_count(hours)
    active = len(visits_db.get_active_sessions(5))
    
    return jsonify({
        'total': count,
        'active': active,
        'period_hours': hours
    })


@api.route('/register-device', methods=['POST'])
def register_device():
    """Register device for push notifications"""
    data = request.get_json()
    
    device_id = data.get('device_id')
    fcm_token = data.get('fcm_token')
    platform = data.get('platform', 'android')
    regions = data.get('regions', [])
    
    if not device_id or not fcm_token:
        return jsonify({'error': 'device_id and fcm_token required'}), 400
    
    device = device_store.register(device_id, fcm_token, platform, regions)
    
    return jsonify({
        'success': True,
        'device': device
    })


@api.route('/update-regions', methods=['POST'])
def update_regions():
    """Update device notification regions"""
    data = request.get_json()
    
    device_id = data.get('device_id')
    regions = data.get('regions', [])
    
    if not device_id:
        return jsonify({'error': 'device_id required'}), 400
    
    success = device_store.update_regions(device_id, regions)
    
    return jsonify({
        'success': success
    })


@api.route('/registered-devices')
def get_devices():
    """Get registered devices (admin)"""
    devices = device_store.get_all()
    return jsonify({
        'devices': devices,
        'count': len(devices)
    })


@api.route('/test-notification', methods=['POST'])
def test_notification():
    """Send test notification"""
    from core.services.notifications import send_notification
    
    data = request.get_json()
    token = data.get('fcm_token')
    
    if not token:
        return jsonify({'error': 'fcm_token required'}), 400
    
    success = send_notification(
        token=token,
        title='🧪 Тестове сповіщення',
        body='Сповіщення працюють коректно!',
        data={'type': 'test'}
    )
    
    return jsonify({'success': success})
