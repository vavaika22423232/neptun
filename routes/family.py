# Family Safety API routes - SOS functionality, family status tracking
# Extracted from app.py for better code organization

import logging
from datetime import datetime

import pytz
from flask import Blueprint, jsonify, request

from .config import get_kyiv_now

log = logging.getLogger(__name__)

# Create blueprint
family_bp = Blueprint('family', __name__)

# Family store reference (set by main app)
_family_store = None
_firebase_initialized = False
_messaging = None


def init_family_store(family_store, firebase_initialized=False, messaging_module=None):
    """Initialize family store reference from main app."""
    global _family_store, _firebase_initialized, _messaging
    _family_store = family_store
    _firebase_initialized = firebase_initialized
    _messaging = messaging_module


# =============================================================================
# FAMILY SAFETY API ROUTES
# =============================================================================
@family_bp.route('/api/family/status', methods=['POST'])
def get_family_status():
    """Get safety status for family members by their codes."""
    try:
        if not _family_store:
            return jsonify({'statuses': {}, 'error': 'Family store not initialized'}), 500
            
        data = request.get_json() or {}
        codes = data.get('codes', [])
        
        statuses = _family_store.get_statuses(codes)
        
        response = jsonify({'statuses': statuses, 'timestamp': get_kyiv_now().isoformat()})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        log.error(f"Error in /api/family/status: {e}")
        return jsonify({'statuses': {}, 'error': str(e)}), 500


@family_bp.route('/api/family/update', methods=['POST'])
def update_family_status():
    """Update safety status for a family member."""
    try:
        if not _family_store:
            return jsonify({'success': False, 'error': 'Family store not initialized'}), 500
            
        data = request.get_json() or {}
        code = (data.get('code', '') or '').upper()
        is_safe = data.get('is_safe', False)
        name = data.get('name', '')
        fcm_token = data.get('fcm_token')
        device_id = data.get('device_id')
        
        if not code or len(code) < 4:
            return jsonify({'success': False, 'error': 'Invalid code'}), 400
        
        _family_store.update_status(code, is_safe, name, fcm_token, device_id)
        
        response = jsonify({'success': True, 'code': code, 'is_safe': is_safe})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        log.error(f"Error in /api/family/update: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@family_bp.route('/api/family/register-token', methods=['POST'])
def register_family_fcm_token():
    """Register FCM token for family member to receive SOS notifications."""
    try:
        if not _family_store:
            return jsonify({'success': False, 'error': 'Family store not initialized'}), 500
            
        data = request.get_json() or {}
        code = (data.get('code', '') or '').upper()
        fcm_token = data.get('fcm_token')
        device_id = data.get('device_id')
        
        if not code or len(code) < 4:
            return jsonify({'success': False, 'error': 'Invalid code'}), 400
        if not fcm_token:
            return jsonify({'success': False, 'error': 'Missing FCM token'}), 400
        
        _family_store.register_fcm_token(code, fcm_token, device_id)
        
        response = jsonify({'success': True, 'code': code})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        log.error(f"Error in /api/family/register-token: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@family_bp.route('/api/family/sos', methods=['POST'])
def send_family_sos():
    """Send SOS signal to family members via push notification."""
    try:
        if not _family_store:
            return jsonify({'success': False, 'error': 'Family store not initialized'}), 500
            
        data = request.get_json() or {}
        code = (data.get('code', '') or '').upper()
        family_codes = data.get('family_codes', [])
        sender_name = data.get('name', '')
        location = data.get('location')
        
        log.info(f"[SOS] === SOS REQUEST RECEIVED ===")
        log.info(f"[SOS] Sender code: {code}")
        log.info(f"[SOS] Sender name: {sender_name}")
        log.info(f"[SOS] Family codes to notify: {family_codes}")
        
        if not code:
            return jsonify({'success': False, 'error': 'Invalid code'}), 400
        
        sos_data = _family_store.send_sos(code, family_codes)
        tokens_to_notify = sos_data.get('tokens_to_notify', [])
        
        log.info(f"[SOS] Found {len(tokens_to_notify)} family members with FCM tokens")
        
        notified_count = 0
        if tokens_to_notify and _firebase_initialized and _messaging:
            for member in tokens_to_notify:
                try:
                    sos_message = f"🆘 {sender_name or code} потребує допомоги!"
                    if location and location.get('address'):
                        sos_message += f"\n📍 {location['address']}"
                    
                    message = _messaging.Message(
                        token=member['fcm_token'],
                        data={
                            'type': 'sos',
                            'sender_code': code,
                            'sender_name': sender_name,
                            'title': '🆘 SOS Сигнал!',
                            'body': sos_message,
                            'location_lat': str(location.get('lat', '')) if location else '',
                            'location_lng': str(location.get('lng', '')) if location else '',
                            'location_address': location.get('address', '') if location else '',
                        },
                        android=_messaging.AndroidConfig(
                            priority='high',
                            ttl=3600,
                        ),
                        apns=_messaging.APNSConfig(
                            headers={'apns-priority': '10'},
                            payload=_messaging.APNSPayload(
                                aps=_messaging.Aps(
                                    alert=_messaging.ApsAlert(
                                        title='🆘 SOS Сигнал!',
                                        body=sos_message,
                                    ),
                                    sound='default',
                                    badge=1,
                                ),
                            ),
                        ),
                    )
                    
                    _messaging.send(message)
                    notified_count += 1
                    log.info(f"[SOS] Notified {member['code']} via FCM")
                    
                except Exception as fcm_error:
                    log.error(f"[SOS] Failed to notify {member['code']}: {fcm_error}")
        
        log.info(f"[SOS] Code {code} sent SOS to {len(family_codes)} family members, {notified_count} notified via FCM")
        
        response = jsonify({
            'success': True, 
            'code': code, 
            'notified': notified_count,
            'total_family': len(family_codes)
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        log.error(f"Error in /api/family/sos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@family_bp.route('/api/family/clear-sos', methods=['POST'])
def clear_family_sos():
    """Clear SOS status for a family member."""
    try:
        if not _family_store:
            return jsonify({'success': False, 'error': 'Family store not initialized'}), 500
            
        data = request.get_json() or {}
        code = (data.get('code', '') or '').upper()
        
        if not code:
            return jsonify({'success': False, 'error': 'Invalid code'}), 400
        
        _family_store.clear_sos(code)
        
        response = jsonify({'success': True, 'code': code})
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        log.error(f"Error in /api/family/clear-sos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@family_bp.route('/api/family/check-tokens', methods=['POST'])
def check_family_tokens():
    """Check if family members have valid FCM tokens registered."""
    try:
        if not _family_store:
            return jsonify({'success': False, 'error': 'Family store not initialized'}), 500
            
        data = request.get_json() or {}
        codes = data.get('codes', [])
        
        if not codes:
            return jsonify({'success': False, 'error': 'No codes provided'}), 400
        
        token_status = {}
        for code in codes:
            code_upper = code.upper()
            has_token = _family_store.has_fcm_token(code_upper)
            token_status[code_upper] = has_token
        
        response = jsonify({
            'success': True,
            'token_status': token_status,
            'timestamp': get_kyiv_now().isoformat()
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        log.error(f"Error in /api/family/check-tokens: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
