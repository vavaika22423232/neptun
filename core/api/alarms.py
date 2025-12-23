"""
Neptun Alarm - Alarms API
Air raid alarm status by region
"""
from flask import Blueprint, jsonify, request
import logging
import requests
from datetime import datetime
from typing import Dict, List

from core.services.storage import alarms_db
from core.data.regions import OBLAST_PCODE, normalize_region_name

log = logging.getLogger(__name__)

alarms_api = Blueprint('alarms', __name__)

# Cache for external API
ALARMS_CACHE: Dict[str, dict] = {}
LAST_FETCH: datetime = None


def fetch_alerts_api() -> Dict:
    """Fetch current alarms from alerts.in.ua API"""
    global ALARMS_CACHE, LAST_FETCH
    
    # Rate limit - max once per 30 seconds
    if LAST_FETCH and (datetime.now() - LAST_FETCH).seconds < 30:
        return ALARMS_CACHE
    
    try:
        resp = requests.get(
            'https://alerts.in.ua/api/states',
            headers={'Accept': 'application/json'},
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            ALARMS_CACHE = data
            LAST_FETCH = datetime.now()
            
            # Update our database
            update_alarms_from_api(data)
            
            return data
            
    except Exception as e:
        log.warning(f"Failed to fetch alerts API: {e}")
    
    return ALARMS_CACHE


def update_alarms_from_api(data: Dict):
    """Update local alarms database from API data"""
    try:
        states = data.get('states', [])
        
        for state in states:
            name = state.get('name', '')
            alert = state.get('alert', False)
            
            if alert:
                alarms_db.set_alarm('oblast', name)
            else:
                alarms_db.clear_alarm('oblast', name)
                
    except Exception as e:
        log.warning(f"Failed to update alarms: {e}")


@alarms_api.route('/active_alarms')
def active_alarms():
    """Get currently active alarms"""
    # Fetch fresh data
    api_data = fetch_alerts_api()
    
    # Get from database
    db_alarms = alarms_db.get_active()
    
    # Merge data
    active = []
    for alarm in db_alarms:
        active.append({
            'level': alarm['level'],
            'name': alarm['name'],
            'since': alarm['since'],
            'last_update': alarm['last_update']
        })
    
    return jsonify({
        'alarms': active,
        'count': len(active),
        'timestamp': datetime.now().isoformat()
    })


@alarms_api.route('/alarms_stats')
def alarms_stats():
    """Get alarm statistics"""
    alarms = alarms_db.get_active()
    
    by_level = {}
    for alarm in alarms:
        level = alarm['level']
        by_level[level] = by_level.get(level, 0) + 1
    
    return jsonify({
        'total': len(alarms),
        'by_level': by_level,
        'oblasts_with_alarm': by_level.get('oblast', 0)
    })


@alarms_api.route('/raion_alarms')
def raion_alarms():
    """Get raion-level alarms"""
    alarms = alarms_db.get_active()
    
    raion_alarms = [a for a in alarms if a['level'] == 'raion']
    
    return jsonify({
        'alarms': raion_alarms,
        'count': len(raion_alarms)
    })


@alarms_api.route('/check_alarm/<region>')
def check_alarm(region: str):
    """Check if specific region has alarm"""
    region_norm = normalize_region_name(region)
    
    alarms = alarms_db.get_active()
    
    for alarm in alarms:
        if normalize_region_name(alarm['name']) == region_norm:
            return jsonify({
                'region': region,
                'alarm': True,
                'since': alarm['since']
            })
    
    return jsonify({
        'region': region,
        'alarm': False
    })
