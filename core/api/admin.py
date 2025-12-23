"""
Neptun Alarm - Admin API Routes
"""
from flask import Blueprint, jsonify, request, render_template
import logging

from core.services.storage import message_store, device_store, visits_db, alarms_db
from core.services.telegram import telegram_service
from core.utils.helpers import get_kyiv_time

log = logging.getLogger(__name__)

admin_api = Blueprint('admin', __name__, url_prefix='/admin')


@admin_api.route('/')
def admin_panel():
    """Admin panel page"""
    return render_template('admin.html')


@admin_api.route('/stats')
def get_stats():
    """Get system statistics"""
    messages = message_store.get_messages()
    devices = device_store.get_all()
    alarms = alarms_db.get_active()
    
    return jsonify({
        'messages_count': len(messages),
        'devices_count': len(devices),
        'active_alarms': len(alarms),
        'visitors_24h': visits_db.get_visitor_count(24),
        'visitors_1h': visits_db.get_visitor_count(1),
        'active_sessions': len(visits_db.get_active_sessions(5)),
        'telegram_status': telegram_service.get_status(),
        'timestamp': get_kyiv_time().isoformat()
    })


@admin_api.route('/markers')
def get_markers():
    """Get all markers for admin"""
    messages = message_store.get_messages()
    tracks = message_store.get_tracks()
    
    return jsonify({
        'messages': messages,
        'tracks': tracks
    })


@admin_api.route('/add_manual_marker', methods=['POST'])
def add_manual_marker():
    """Add manual marker"""
    from core.utils.helpers import generate_id
    
    data = request.get_json()
    
    marker = {
        'id': generate_id(data.get('text', 'manual')),
        'type': data.get('type', 'drone'),
        'location': data.get('location', ''),
        'lat': data.get('lat'),
        'lng': data.get('lng'),
        'text': data.get('text', ''),
        'channel': 'manual',
        'timestamp': get_kyiv_time().isoformat(),
        'manual': True
    }
    
    message_store.add_message(marker)
    
    return jsonify({'success': True, 'marker': marker})


@admin_api.route('/delete_manual_marker', methods=['POST'])
def delete_manual_marker():
    """Delete marker"""
    data = request.get_json()
    marker_id = data.get('id')
    
    if not marker_id:
        return jsonify({'error': 'id required'}), 400
    
    # For now, just hide it
    message_store.hide_message(marker_id)
    
    return jsonify({'success': True})


@admin_api.route('/hide_marker', methods=['POST'])
def hide_marker():
    """Hide marker"""
    data = request.get_json()
    marker_id = data.get('id')
    
    message_store.hide_message(marker_id)
    return jsonify({'success': True})


@admin_api.route('/unhide_marker', methods=['POST'])
def unhide_marker():
    """Unhide marker"""
    data = request.get_json()
    marker_id = data.get('id')
    
    message_store.unhide_message(marker_id)
    return jsonify({'success': True})


@admin_api.route('/cleanup', methods=['POST'])
def cleanup():
    """Cleanup old data"""
    hours = int(request.args.get('hours', 6))
    
    message_store.prune_old(hours)
    alarms_db.prune_old(hours)
    
    return jsonify({
        'success': True,
        'cleaned_hours': hours
    })


@admin_api.route('/channels')
def get_channels():
    """Get monitored channels"""
    return jsonify({
        'channels': telegram_service.channels
    })


@admin_api.route('/add_channel', methods=['POST'])
def add_channel():
    """Add channel to monitor"""
    data = request.get_json()
    channel = data.get('channel', '').strip()
    
    if not channel:
        return jsonify({'error': 'channel required'}), 400
    
    telegram_service.add_channel(channel)
    
    return jsonify({
        'success': True,
        'channels': telegram_service.channels
    })


@admin_api.route('/remove_channel', methods=['POST'])
def remove_channel():
    """Remove channel from monitoring"""
    data = request.get_json()
    channel = data.get('channel', '').strip()
    
    telegram_service.remove_channel(channel)
    
    return jsonify({
        'success': True,
        'channels': telegram_service.channels
    })
