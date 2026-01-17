# Alarms API routes - UkraineAlarm API proxy and alarm status endpoints
# Extracted from app.py for better code organization

import json
import logging
import time
import threading
from datetime import datetime, timedelta

import requests as http_requests
import pytz
from flask import Blueprint, jsonify, request

from .config import (
    ALARM_API_KEY,
    ALARM_API_BASE,
    RESPONSE_CACHE,
    DISTRICT_TO_OBLAST,
    REGION_TOPIC_MAP,
    MESSAGES_FILE,
    get_kyiv_now,
)

log = logging.getLogger(__name__)

# Create blueprint
alarms_bp = Blueprint('alarms', __name__)

# =============================================================================
# ALARM STATE TRACKING
# =============================================================================
_alarm_states = {}  # region_id -> {active: bool, types: list, last_changed: timestamp, notified: bool}
_first_run = True
_monitoring_active = False
_telegram_alert_sent = {}
_telegram_alert_lock = threading.Lock()
_telegram_region_notified = {}

# Firebase reference (set by main app)
_firebase_initialized = False
_messaging = None

def init_firebase_messaging(firebase_initialized, messaging_module):
    """Initialize Firebase messaging reference from main app."""
    global _firebase_initialized, _messaging
    _firebase_initialized = firebase_initialized
    _messaging = messaging_module

# =============================================================================
# ALARM API ROUTES
# =============================================================================
@alarms_bp.route('/api/alarms/proxy')
def alarms_proxy():
    """Proxy endpoint for UkraineAlarm API with caching."""
    try:
        # Check cache first
        cache_key = 'alarms_all'
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            return jsonify(cached)
        
        response = http_requests.get(
            f'{ALARM_API_BASE}/alerts',
            headers={'Authorization': ALARM_API_KEY},
            timeout=10
        )
        
        if response.ok:
            data = response.json()
            RESPONSE_CACHE.set(cache_key, data, ttl=10)  # Cache for 10 seconds
            return jsonify(data)
        else:
            return jsonify({'error': 'API unavailable'}), response.status_code
            
    except Exception as e:
        log.error(f"Alarms proxy error: {e}")
        return jsonify({'error': str(e)}), 500


@alarms_bp.route('/api/alarms/all')
@alarms_bp.route('/api/alarms')
def alarms_all():
    """Get all current alarms with oblast grouping."""
    try:
        cache_key = 'alarms_formatted'
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            response = jsonify(cached)
            response.headers['Cache-Control'] = 'public, max-age=10'
            return response
        
        api_response = http_requests.get(
            f'{ALARM_API_BASE}/alerts',
            headers={'Authorization': ALARM_API_KEY},
            timeout=10
        )
        
        if not api_response.ok:
            return jsonify({'error': 'API unavailable', 'alarms': []}), 502
        
        data = api_response.json()
        
        # Group by oblast
        oblasts = {}
        districts = []
        
        for region in data:
            region_id = region.get('regionId', '')
            region_name = region.get('regionName', '')
            region_type = region.get('regionType', '')
            active_alerts = region.get('activeAlerts', [])
            
            if not active_alerts:
                continue
            
            alert_types = [alert.get('type', 'AIR') for alert in active_alerts]
            
            if region_type == 'State':
                oblasts[region_name] = {
                    'region_id': region_id,
                    'region_name': region_name,
                    'alert_types': alert_types,
                    'districts': []
                }
            else:
                districts.append({
                    'region_id': region_id,
                    'region_name': region_name,
                    'alert_types': alert_types,
                    'oblast': DISTRICT_TO_OBLAST.get(region_name, '')
                })
        
        # Attach districts to oblasts
        for district in districts:
            oblast_name = district.get('oblast')
            if oblast_name and oblast_name in oblasts:
                oblasts[oblast_name]['districts'].append(district)
        
        result = {
            'alarms': list(oblasts.values()),
            'all_districts': districts,
            'timestamp': get_kyiv_now().isoformat(),
            'count': len(oblasts)
        }
        
        RESPONSE_CACHE.set(cache_key, result, ttl=10)
        
        response = jsonify(result)
        response.headers['Cache-Control'] = 'public, max-age=10'
        return response
        
    except Exception as e:
        log.error(f"Alarms all error: {e}")
        return jsonify({'error': str(e), 'alarms': []}), 500


@alarms_bp.route('/api/alarm-status')
def alarm_status():
    """Get current alarm status for mobile app AlarmTimerWidget."""
    try:
        region = request.args.get('region', 'Дніпропетровська')
        
        cache_key = f'alarm_status_{region}'
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            return jsonify(cached)
        
        api_response = http_requests.get(
            f'{ALARM_API_BASE}/alerts',
            headers={'Authorization': ALARM_API_KEY},
            timeout=8
        )
        
        if not api_response.ok:
            return jsonify({
                'active': False,
                'region': region,
                'error': 'API unavailable'
            })
        
        data = api_response.json()
        
        # Find region
        is_active = False
        alert_types = []
        started_at = None
        
        for r in data:
            r_name = r.get('regionName', '')
            if region.lower() in r_name.lower():
                active_alerts = r.get('activeAlerts', [])
                if active_alerts:
                    is_active = True
                    alert_types = [a.get('type', '') for a in active_alerts]
                    # Get earliest start time
                    for alert in active_alerts:
                        last_update = alert.get('lastUpdate', '')
                        if last_update:
                            started_at = last_update
                            break
                break
        
        result = {
            'active': is_active,
            'region': region,
            'alert_types': alert_types,
            'started_at': started_at,
            'timestamp': get_kyiv_now().isoformat()
        }
        
        RESPONSE_CACHE.set(cache_key, result, ttl=15)
        
        response = jsonify(result)
        response.headers['Cache-Control'] = 'public, max-age=15'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        log.error(f"Alarm status error: {e}")
        return jsonify({
            'active': False,
            'region': request.args.get('region', ''),
            'error': str(e)
        })


@alarms_bp.route('/api/alarm-history')
def alarm_history():
    """Get alarm history for a region (based on message log)."""
    try:
        region = request.args.get('region', '')
        days = min(int(request.args.get('days', 7)), 30)  # Max 30 days
        MAX_RESULTS = 100  # Limit results
        
        cache_key = f'alarm_history_{region}_{days}'
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            return jsonify(cached)
        
        # Load messages
        messages = []
        try:
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
        except FileNotFoundError:
            pass
        
        # Filter by region and time
        cutoff = get_kyiv_now() - timedelta(days=days)
        history = []
        
        for msg in messages:
            try:
                timestamp_str = msg.get('timestamp', '')
                if not timestamp_str:
                    continue
                
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if timestamp.tzinfo is None:
                    timestamp = pytz.UTC.localize(timestamp)
                
                if timestamp < cutoff:
                    continue
                
                location = msg.get('location', '') or msg.get('region', '')
                if region and region.lower() not in location.lower():
                    continue
                
                text = msg.get('text', '').lower()
                is_start = 'тривога' in text and 'відбій' not in text
                alarm_type = 'air_raid'
                if 'бпла' in text or 'дрон' in text:
                    alarm_type = 'drone'
                elif 'ракет' in text:
                    alarm_type = 'missile'
                
                history.append({
                    'start_time': timestamp.isoformat(),
                    'end_time': None,
                    'type': alarm_type,
                    'region': location[:50],
                    'is_start': is_start,
                    'duration_minutes': 30
                })
                
            except Exception:
                continue
        
        history.sort(key=lambda x: x['start_time'], reverse=True)
        returned_history = history[:MAX_RESULTS]
        
        result = {
            'history': returned_history,
            'count': len(returned_history),
            'total_count': len(history),
            'truncated': len(history) > MAX_RESULTS,
            'region': region,
            'days': days,
            'timestamp': get_kyiv_now().isoformat()
        }
        
        RESPONSE_CACHE.set(cache_key, result, ttl=60)
        
        response = jsonify(result)
        response.headers['Cache-Control'] = 'public, max-age=60'
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        log.error(f"Alarm history error: {e}")
        return jsonify({'history': [], 'error': str(e)}), 500


@alarms_bp.route('/api/monitoring-status')
def monitoring_status():
    """Check alarm monitoring status (for debugging)."""
    active_districts = [
        region_id for region_id, state in _alarm_states.items()
        if state.get('active')
    ]
    
    return jsonify({
        'monitoring_active': _monitoring_active,
        'first_run': _first_run,
        'firebase_initialized': _firebase_initialized,
        'alarm_states_count': len(_alarm_states),
        'active_alarms': len(active_districts),
        'active_region_ids': active_districts[:20],
        'server_time': get_kyiv_now().isoformat(),
    })


# =============================================================================
# ALARM MONITORING (Background thread) 
# =============================================================================
def send_alarm_notification(region_data, alarm_started=True):
    """Send FCM push notification for alarm state change."""
    if not _firebase_initialized or not _messaging:
        return
    
    try:
        region_name = region_data.get('regionName', '')
        region_id = str(region_data.get('regionId', ''))
        region_type = region_data.get('regionType', '')
        active_alerts = region_data.get('activeAlerts', [])
        
        # Determine alert type for notification
        alert_types = [alert.get('type', '') for alert in active_alerts]
        
        # Critical threats
        is_critical = any(t in ['AIR', 'BALLISTIC', 'CHEMICAL'] for t in alert_types)
        
        # Build notification content
        threat_detail = ''
        tts_location = None
        
        if alarm_started:
            if 'BALLISTIC' in alert_types:
                threat_detail = 'ракети'
                emoji = '🚀'
            elif 'ARTILLERY' in alert_types:
                threat_detail = 'каби'
                emoji = '💣'
            elif 'UAV' in alert_types:
                threat_detail = 'дрони'
                emoji = '🛩️'
            else:
                threat_detail = 'повітряна тривога'
                emoji = '🚨'
            
            title = f"{emoji} Тривога: {region_name}"
            body = f"Загроза: {threat_detail}"
        else:
            emoji = '✅'
            title = f"{emoji} Відбій: {region_name}"
            body = "Тривогу скасовано"
        
        # Get FCM topic
        topic = REGION_TOPIC_MAP.get(region_name)
        
        # For districts, also notify oblast
        oblast_topic = None
        if region_type == 'District':
            oblast = DISTRICT_TO_OBLAST.get(region_name, '')
            if oblast:
                oblast_topic = REGION_TOPIC_MAP.get(oblast)
        
        if not topic and not oblast_topic:
            log.info(f"No topic mapping for region: {region_name}")
            return
        
        topics_to_send = []
        if topic:
            topics_to_send.append(topic)
        if oblast_topic and oblast_topic != topic:
            topics_to_send.append(oblast_topic)
        
        # Determine TTS threat type
        if alarm_started:
            tts_threat_map = {
                'ракети': 'Ракетна небезпека',
                'каби': 'Загроза КАБів',
                'дрони': 'Загроза БПЛА',
            }
            tts_threat = tts_threat_map.get(threat_detail, 'Повітряна тривога')
        else:
            tts_threat = 'Відбій тривоги'
        
        fcm_location = tts_location if tts_location else region_name
        
        for target_topic in topics_to_send:
            try:
                message = _messaging.Message(
                    data={
                        'type': 'alarm',
                        'title': title,
                        'body': body,
                        'location': fcm_location,
                        'region': region_name,
                        'region_id': region_id,
                        'alarm_state': 'active' if alarm_started else 'ended',
                        'is_critical': 'true' if is_critical else 'false',
                        'threat_type': tts_threat,
                        'timestamp': get_kyiv_now().isoformat(),
                        'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                    },
                    android=_messaging.AndroidConfig(
                        priority='high',
                        ttl=timedelta(seconds=300),
                    ),
                    apns=_messaging.APNSConfig(
                        headers={
                            'apns-priority': '10',
                            'apns-push-type': 'alert',
                        },
                        payload=_messaging.APNSPayload(
                            aps=_messaging.Aps(
                                alert=_messaging.ApsAlert(title=title, body=body),
                                sound='default',
                                badge=1,
                                content_available=True,
                            ),
                        ),
                    ),
                    topic=target_topic,
                )
                
                response = _messaging.send(message)
                log.info(f"✅ Alarm notification sent to topic {target_topic}: {response}")
            except Exception as e:
                log.error(f"Failed to send alarm to topic {target_topic}: {e}")
        
    except Exception as e:
        log.error(f"Error in send_alarm_notification: {e}")


def monitor_alarms():
    """Background task to monitor ukrainealarm API and send notifications on state changes."""
    global _alarm_states, _first_run, _monitoring_active
    
    log.info("=== ALARM MONITORING STARTED ===")
    
    consecutive_failures = 0
    MAX_FAILURES_BEFORE_WARN = 5
    last_successful_fetch = 0
    
    while _monitoring_active:
        try:
            data = None
            for attempt in range(3):
                try:
                    response = http_requests.get(
                        f'{ALARM_API_BASE}/alerts',
                        headers={'Authorization': ALARM_API_KEY},
                        timeout=15
                    )
                    if response.ok:
                        data = response.json()
                        consecutive_failures = 0
                        last_successful_fetch = time.time()
                        break
                except Exception as e:
                    log.warning(f"API attempt {attempt+1}/3 error: {e}")
                
                if attempt < 2:
                    time.sleep(2)
            
            if data is None:
                consecutive_failures += 1
                if consecutive_failures >= MAX_FAILURES_BEFORE_WARN:
                    log.error(f"API unavailable for {consecutive_failures} consecutive cycles!")
                time.sleep(30)
                continue
            
            current_time = time.time()
            current_active_regions = set()
            
            if _first_run:
                log.info("First run - storing initial alarm states WITHOUT notifications")
                for region in data:
                    region_id = region.get('regionId', '')
                    active_alerts = region.get('activeAlerts', [])
                    if active_alerts:
                        current_active_regions.add(region_id)
                        _alarm_states[region_id] = {
                            'active': True,
                            'types': [alert.get('type') for alert in active_alerts],
                            'last_changed': current_time,
                            'notified': True
                        }
                _first_run = False
                log.info(f"Initial state stored - {len(current_active_regions)} active alarms")
            else:
                for region in data:
                    region_id = region.get('regionId', '')
                    region_type = region.get('regionType', '')
                    active_alerts = region.get('activeAlerts', [])
                    has_alarm = len(active_alerts) > 0
                    
                    if has_alarm:
                        current_active_regions.add(region_id)
                    
                    previous_state = _alarm_states.get(region_id, {})
                    was_active = previous_state.get('active', False)
                    was_notified = previous_state.get('notified', False)
                    
                    if has_alarm and not was_active:
                        if not was_notified and region_type == 'District':
                            log.info(f"🚨 DISTRICT ALARM STARTED: {region.get('regionName')}")
                            send_alarm_notification(region, alarm_started=True)
                        _alarm_states[region_id] = {
                            'active': True,
                            'types': [alert.get('type') for alert in active_alerts],
                            'last_changed': current_time,
                            'notified': True
                        }
                    elif not has_alarm and was_active:
                        if region_type == 'District':
                            log.info(f"✅ DISTRICT ALARM ENDED: {region.get('regionName')}")
                            send_alarm_notification(region, alarm_started=False)
                        _alarm_states[region_id] = {
                            'active': False,
                            'types': [],
                            'last_changed': current_time,
                            'notified': False
                        }
        
        except Exception as e:
            log.error(f"Error in alarm monitoring: {e}")
            consecutive_failures += 1
        
        time.sleep(45)
    
    log.info("=== ALARM MONITORING STOPPED ===")


def start_alarm_monitoring():
    """Start the alarm monitoring background thread."""
    global _monitoring_active
    
    if _monitoring_active:
        log.info("Alarm monitoring already active")
        return
    
    _monitoring_active = True
    monitor_thread = threading.Thread(target=monitor_alarms, daemon=True)
    monitor_thread.start()
    log.info("Alarm monitoring thread started")


def stop_alarm_monitoring():
    """Stop the alarm monitoring."""
    global _monitoring_active
    _monitoring_active = False
