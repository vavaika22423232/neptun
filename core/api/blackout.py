"""
Neptun Alarm - Blackout Schedules API
Power outage schedules for DTEK regions
"""
from flask import Blueprint, jsonify, request
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

blackout_api = Blueprint('blackout', __name__, url_prefix='/api')

# Cache for schedules
SCHEDULES_CACHE: Dict[str, dict] = {}
SCHEDULES_FILE = Path('blackout_schedules.json')


def load_schedules() -> Dict:
    """Load schedules from file"""
    global SCHEDULES_CACHE
    try:
        if SCHEDULES_FILE.exists():
            SCHEDULES_CACHE = json.loads(SCHEDULES_FILE.read_text(encoding='utf-8'))
    except Exception as e:
        log.warning(f"Failed to load schedules: {e}")
    return SCHEDULES_CACHE


def save_schedules():
    """Save schedules to file"""
    try:
        SCHEDULES_FILE.write_text(
            json.dumps(SCHEDULES_CACHE, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    except Exception as e:
        log.warning(f"Failed to save schedules: {e}")


# DTEK queues by city
BLACKOUT_QUEUES = {
    'київ': ['1.1', '1.2', '2.1', '2.2', '3.1', '3.2'],
    'дніпро': ['1', '2', '3', '4', '5', '6'],
    'одеса': ['1', '2', '3', '4'],
    'запоріжжя': ['1', '2', '3'],
}


@blackout_api.route('/search_cities')
def search_cities():
    """Search cities with blackout schedules"""
    query = request.args.get('q', '').lower().strip()
    
    if not query or len(query) < 2:
        return jsonify({'cities': []})
    
    # Simple search in known cities
    cities = []
    for city in BLACKOUT_QUEUES.keys():
        if query in city:
            cities.append({
                'name': city.capitalize(),
                'queues': BLACKOUT_QUEUES[city]
            })
    
    return jsonify({'cities': cities})


@blackout_api.route('/all_cities_with_queues')
def all_cities_with_queues():
    """Get all cities with their queues"""
    cities = []
    for city, queues in BLACKOUT_QUEUES.items():
        cities.append({
            'name': city.capitalize(),
            'queues': queues
        })
    
    return jsonify({'cities': cities})


@blackout_api.route('/get_schedule')
def get_schedule():
    """Get blackout schedule for city and queue"""
    city = request.args.get('city', '').lower().strip()
    queue = request.args.get('queue', '').strip()
    
    if not city or not queue:
        return jsonify({'error': 'city and queue required'}), 400
    
    schedules = load_schedules()
    key = f"{city}_{queue}"
    
    schedule = schedules.get(key, {})
    
    return jsonify({
        'city': city,
        'queue': queue,
        'schedule': schedule,
        'last_updated': schedule.get('updated', None)
    })


@blackout_api.route('/live_schedules')
def live_schedules():
    """Get current blackout status"""
    schedules = load_schedules()
    
    now = datetime.now()
    hour = now.hour
    
    active = []
    upcoming = []
    
    for key, schedule in schedules.items():
        city, queue = key.rsplit('_', 1)
        hours = schedule.get('hours', [])
        
        if hour in hours:
            active.append({
                'city': city,
                'queue': queue,
                'status': 'blackout'
            })
        elif (hour + 1) % 24 in hours:
            upcoming.append({
                'city': city,
                'queue': queue,
                'starts_in': 'менше години'
            })
    
    return jsonify({
        'active': active,
        'upcoming': upcoming,
        'current_hour': hour
    })


@blackout_api.route('/schedule_status')
def schedule_status():
    """Get schedule update status"""
    schedules = load_schedules()
    
    return jsonify({
        'total_schedules': len(schedules),
        'cities': list(BLACKOUT_QUEUES.keys()),
        'last_check': datetime.now().isoformat()
    })


# Load on import
load_schedules()
