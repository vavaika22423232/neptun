# Blackout schedule API routes - YASNO schedules, power outage data
# Extracted from app.py for better code organization

import os
import json
import logging
from datetime import datetime

import requests
import pytz
from flask import Blueprint, jsonify, request

from .config import (
    RESPONSE_CACHE,
    get_kyiv_now,
)

log = logging.getLogger(__name__)

# Create blueprint
blackout_bp = Blueprint('blackout', __name__)

# =============================================================================
# BLACKOUT DATA (Sample - will be loaded from external source)
# =============================================================================
BLACKOUT_ADDRESSES = {}  # Will be populated from main app

BLACKOUT_SCHEDULES = {
    # Group 1 subgroups
    '1.1': [
        {'time': '00:00 - 04:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '04:00 - 08:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '12:00 - 16:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '16:00 - 20:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '20:00 - 24:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
    ],
    '1.2': [
        {'time': '00:00 - 04:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '04:00 - 08:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
        {'time': '12:00 - 16:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '16:00 - 20:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
    ],
    # Group 2 subgroups
    '2.1': [
        {'time': '00:00 - 04:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '04:00 - 08:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '08:00 - 12:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '12:00 - 16:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '16:00 - 20:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
    ],
    '2.2': [
        {'time': '00:00 - 04:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '04:00 - 08:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '12:00 - 16:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '16:00 - 20:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
        {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
    ],
    # Group 3 subgroups
    '3.1': [
        {'time': '00:00 - 04:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
        {'time': '04:00 - 08:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '12:00 - 16:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '16:00 - 20:00', 'label': 'Активне відключення', 'status': 'active'},
        {'time': '20:00 - 24:00', 'label': 'Електропостачання', 'status': 'normal'},
    ],
    '3.2': [
        {'time': '00:00 - 04:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '04:00 - 08:00', 'label': 'Можливе відключення', 'status': 'normal'},
        {'time': '08:00 - 12:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '12:00 - 16:00', 'label': 'Можливе відключення', 'status': 'upcoming'},
        {'time': '16:00 - 20:00', 'label': 'Електропостачання', 'status': 'normal'},
        {'time': '20:00 - 24:00', 'label': 'Активне відключення', 'status': 'active'},
    ],
}

# UKRAINE_CITIES will be imported from main app
UKRAINE_CITIES = []

# =============================================================================
# BLACKOUT API ROUTES
# =============================================================================
@blackout_bp.route('/api/search_cities')
def search_cities():
    """Get all cities and addresses for autocomplete."""
    try:
        cities_set = set()
        addresses_list = []
        
        for address_key, data in BLACKOUT_ADDRESSES.items():
            city = data.get('city', '')
            if city:
                cities_set.add(city)
            
            parts = address_key.split()
            if len(parts) >= 2:
                street = ' '.join(parts[1:])
                addresses_list.append({
                    'city': city,
                    'street': street,
                    'building': '',
                    'group': data.get('group', ''),
                    'oblast': data.get('oblast', ''),
                    'provider': data.get('provider', '')
                })
        
        cities_list = sorted(list(cities_set))
        
        return jsonify({
            'cities': cities_list,
            'addresses': addresses_list[:200]
        })
        
    except Exception as e:
        log.error(f"Error in search_cities: {e}")
        return jsonify({
            'cities': UKRAINE_CITIES if UKRAINE_CITIES else [],
            'addresses': []
        })


@blackout_bp.route('/api/all_cities_with_queues')
def get_all_cities_with_queues():
    """Get all cities with their queues for the schedule grid."""
    try:
        cities_data = {}
        
        for address_key, data in BLACKOUT_ADDRESSES.items():
            city = data.get('city', '')
            oblast = data.get('oblast', '')
            queue = data.get('group', '')
            provider = data.get('provider', '')
            
            if not city:
                continue
            
            city_key = f"{city}, {oblast}"
            
            if city_key not in cities_data:
                cities_data[city_key] = {
                    'city': city,
                    'oblast': oblast,
                    'provider': provider,
                    'queues': set()
                }
            
            if queue:
                cities_data[city_key]['queues'].add(queue)
        
        result = []
        current_hour = get_kyiv_now().hour
        
        for city_key, data in cities_data.items():
            queues_list = sorted(list(data['queues']))
            
            has_active_blackout = False
            active_queues = []
            
            for queue in queues_list:
                schedule = BLACKOUT_SCHEDULES.get(queue, [])
                for slot in schedule:
                    if slot.get('status') == 'active':
                        time_range = slot.get('time', '')
                        if ' - ' in time_range:
                            start_time = time_range.split(' - ')[0]
                            start_hour = int(start_time.split(':')[0])
                            end_hour = (start_hour + 4) % 24
                            
                            if start_hour <= current_hour < end_hour or \
                               (end_hour < start_hour and (current_hour >= start_hour or current_hour < end_hour)):
                                has_active_blackout = True
                                active_queues.append(queue)
            
            if has_active_blackout:
                status = 'active'
                status_text = f"Відключення черг: {', '.join(active_queues)}"
            elif len(queues_list) > 0:
                status = 'warning'
                status_text = f"Черги: {', '.join(queues_list)}"
            else:
                status = 'stable'
                status_text = "Стабільно"
            
            result.append({
                'city': data['city'],
                'oblast': data['oblast'],
                'provider': data['provider'],
                'queues': queues_list,
                'status': status,
                'statusText': status_text,
                'queuesCount': len(queues_list)
            })
        
        result.sort(key=lambda x: x['city'])
        
        return jsonify({
            'success': True,
            'cities': result,
            'total': len(result)
        })
        
    except Exception as e:
        log.error(f"Error in get_all_cities_with_queues: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@blackout_bp.route('/api/get_schedule')
def get_schedule():
    """Get blackout schedule for a specific address using YASNO API with fallback."""
    city = request.args.get('city', '').strip()
    street = request.args.get('street', '').strip()
    building = request.args.get('building', '').strip()
    group = request.args.get('group', '').strip()
    refresh = request.args.get('refresh', '').lower() in ('true', '1', 'yes')
    
    # Check cache
    cache_key = f'schedule_{city}_{group}'
    if not refresh:
        cached = RESPONSE_CACHE.get(cache_key)
        if cached:
            return jsonify(cached)
    
    try:
        # Try YASNO API first
        yasno_url = 'https://api.yasno.com.ua/api/v1/pages/home/schedule-turn-off-electricity'
        
        response = requests.get(yasno_url, timeout=10)
        
        if response.ok:
            yasno_data = response.json()
            
            # Parse YASNO response for the requested group
            schedule = []
            
            # Extract schedule from YASNO API (format varies)
            if 'components' in yasno_data:
                for component in yasno_data.get('components', []):
                    if component.get('template') == 'electricity-schedule':
                        schedule_data = component.get('schedule', {})
                        # Process schedule data...
                        
            result = {
                'success': True,
                'city': city,
                'group': group,
                'schedule': schedule if schedule else BLACKOUT_SCHEDULES.get(group, []),
                'source': 'yasno' if schedule else 'fallback',
                'timestamp': get_kyiv_now().isoformat()
            }
            
            RESPONSE_CACHE.set(cache_key, result, ttl=300)  # Cache 5 minutes
            return jsonify(result)
            
    except Exception as e:
        log.warning(f"YASNO API error: {e}")
    
    # Fallback to static schedule
    schedule = BLACKOUT_SCHEDULES.get(group, BLACKOUT_SCHEDULES.get('1.1', []))
    
    result = {
        'success': True,
        'city': city,
        'group': group,
        'schedule': schedule,
        'source': 'fallback',
        'timestamp': get_kyiv_now().isoformat()
    }
    
    RESPONSE_CACHE.set(cache_key, result, ttl=300)
    return jsonify(result)


@blackout_bp.route('/api/live_schedules')
def live_schedules():
    """Get live schedules for all groups."""
    try:
        schedules = {}
        for group_id, schedule in BLACKOUT_SCHEDULES.items():
            schedules[group_id] = schedule
        
        return jsonify({
            'success': True,
            'schedules': schedules,
            'timestamp': get_kyiv_now().isoformat()
        })
        
    except Exception as e:
        log.error(f"Error in live_schedules: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@blackout_bp.route('/api/schedule_status')
def schedule_status():
    """Get current blackout status for a group."""
    group = request.args.get('group', '1.1')
    
    try:
        schedule = BLACKOUT_SCHEDULES.get(group, [])
        current_hour = get_kyiv_now().hour
        
        current_status = 'unknown'
        current_slot = None
        
        for slot in schedule:
            time_range = slot.get('time', '')
            if ' - ' in time_range:
                start_str, end_str = time_range.split(' - ')
                start_hour = int(start_str.split(':')[0])
                end_hour = int(end_str.split(':')[0])
                
                if start_hour <= current_hour < end_hour or \
                   (end_hour == 0 and current_hour >= start_hour):
                    current_status = slot.get('status', 'unknown')
                    current_slot = slot
                    break
        
        return jsonify({
            'success': True,
            'group': group,
            'current_status': current_status,
            'current_slot': current_slot,
            'current_hour': current_hour,
            'timestamp': get_kyiv_now().isoformat()
        })
        
    except Exception as e:
        log.error(f"Error in schedule_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@blackout_bp.route('/api/force_update', methods=['POST'])
def force_update():
    """Force update schedule cache."""
    try:
        RESPONSE_CACHE.clear_expired()
        return jsonify({
            'success': True,
            'message': 'Cache cleared',
            'timestamp': get_kyiv_now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
