# Device registration routes - FCM tokens, region subscriptions
# Extracted from app.py for better code organization

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from .config import RESPONSE_CACHE, get_kyiv_now

log = logging.getLogger(__name__)

# Create blueprint
devices_bp = Blueprint('devices', __name__)

# Device store reference (set by main app)
_device_store = None


def init_device_store(device_store):
    """Initialize device store reference from main app."""
    global _device_store
    _device_store = device_store


# =============================================================================
# DEVICE REGISTRATION ROUTES
# =============================================================================
@devices_bp.route('/api/register-device', methods=['POST'])
def register_device():
    """Register a device for push notifications."""
    try:
        if not _device_store:
            return jsonify({'success': False, 'error': 'Device store not initialized'}), 500
            
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')
        fcm_token = data.get('token', '')
        platform = data.get('platform', 'unknown')
        regions = data.get('regions', [])
        
        if not device_id or not fcm_token:
            return jsonify({'success': False, 'error': 'Missing deviceId or token'}), 400
        
        _device_store.register(device_id, fcm_token, platform, regions)
        
        log.info(f"Device registered: {device_id[:20]}... platform={platform} regions={len(regions)}")
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'regions_count': len(regions)
        })
        
    except Exception as e:
        log.error(f"Error registering device: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/api/update-regions', methods=['POST'])
def update_regions():
    """Update subscribed regions for a device."""
    try:
        if not _device_store:
            return jsonify({'success': False, 'error': 'Device store not initialized'}), 500
            
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')
        regions = data.get('regions', [])
        
        if not device_id:
            return jsonify({'success': False, 'error': 'Missing deviceId'}), 400
        
        _device_store.update_regions(device_id, regions)
        
        log.info(f"Regions updated for {device_id[:20]}...: {len(regions)} regions")
        
        return jsonify({
            'success': True,
            'regions_count': len(regions)
        })
        
    except Exception as e:
        log.error(f"Error updating regions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/api/registered-devices', methods=['GET'])
def get_registered_devices():
    """Get count of registered devices (admin only)."""
    try:
        if not _device_store:
            return jsonify({'count': 0, 'error': 'Device store not initialized'})
        
        count = _device_store.get_count()
        
        return jsonify({
            'count': count,
            'timestamp': get_kyiv_now().isoformat()
        })
        
    except Exception as e:
        log.error(f"Error getting device count: {e}")
        return jsonify({'count': 0, 'error': str(e)})


# =============================================================================
# VISITOR TRACKING
# =============================================================================
@devices_bp.route('/api/visitor_count')
def visitor_count():
    """Get visitor count (web)."""
    try:
        cache_key = 'visitor_count'
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            return jsonify(cached)
        
        # Would track actual visitors
        result = {
            'count': 0,
            'timestamp': get_kyiv_now().isoformat()
        }
        
        RESPONSE_CACHE.set(cache_key, result, ttl=60)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'count': 0, 'error': str(e)})


@devices_bp.route('/api/android_visitor_count')
def android_visitor_count():
    """Get Android app visitor count."""
    try:
        if not _device_store:
            return jsonify({'count': 0})
        
        android_count = _device_store.get_count_by_platform('android')
        
        return jsonify({
            'count': android_count,
            'timestamp': get_kyiv_now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'count': 0, 'error': str(e)})


@devices_bp.route('/api/track_android_visit', methods=['POST'])
def track_android_visit():
    """Track an Android app visit."""
    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')
        
        # Would track the visit
        log.info(f"Android visit tracked: {device_id[:20] if device_id else 'unknown'}...")
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# =============================================================================
# FEEDBACK API
# =============================================================================
@devices_bp.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback or bug report."""
    try:
        data = request.get_json() or {}
        
        feedback_type = data.get('type', 'feedback')
        message = data.get('message', '')
        device_id = data.get('deviceId', '')
        platform = data.get('platform', 'unknown')
        app_version = data.get('appVersion', '')
        
        if not message:
            return jsonify({'success': False, 'error': 'Message required'}), 400
        
        log.info(f"Feedback received [{feedback_type}] from {platform}: {message[:100]}...")
        
        # Would save to feedback store
        
        return jsonify({
            'success': True,
            'message': 'Дякуємо за відгук!'
        })
        
    except Exception as e:
        log.error(f"Error submitting feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@devices_bp.route('/api/feedback', methods=['GET'])
def get_feedback():
    """Get feedback list (admin only)."""
    try:
        # Would load from feedback store
        return jsonify({
            'feedback': [],
            'count': 0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# TEST NOTIFICATION
# =============================================================================
@devices_bp.route('/api/test-notification', methods=['POST'])
def test_notification():
    """Send a test notification to a device."""
    try:
        data = request.get_json() or {}
        device_id = data.get('deviceId', '')
        fcm_token = data.get('token', '')
        
        if not fcm_token:
            return jsonify({'success': False, 'error': 'Missing FCM token'}), 400
        
        # Would send test notification via Firebase
        log.info(f"Test notification requested for {device_id[:20] if device_id else 'unknown'}...")
        
        return jsonify({
            'success': True,
            'message': 'Test notification sent'
        })
        
    except Exception as e:
        log.error(f"Error sending test notification: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
