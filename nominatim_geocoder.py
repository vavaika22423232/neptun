"""
Nominatim Geocoding Integration for Ukrainian Cities
Provides fallback geocoding for cities not in the local database
"""

import requests
import time
import logging
from typing import Optional, Tuple

log = logging.getLogger(__name__)

# Try to import persistent cache
try:
    from nominatim_cache import get_from_cache, add_to_cache
    PERSISTENT_CACHE = True
except ImportError:
    PERSISTENT_CACHE = False
    def get_from_cache(city, region=None): return None
    def add_to_cache(city, coords, region=None): pass

# Nominatim API endpoint (using OpenStreetMap's public instance)
NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"

# Rate limiting: max 1 request per second as per Nominatim usage policy
last_request_time = 0
MIN_REQUEST_INTERVAL = 1.0  # seconds

# User agent as required by Nominatim policy
USER_AGENT = "UkraineAlertMap/1.0 (alert mapping service)"

# In-memory cache to avoid repeated requests during session
_cache = {}


def get_coordinates_nominatim(city_name: str, region: Optional[str] = None) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a Ukrainian city using Nominatim API
    
    Args:
        city_name: Name of the city/settlement
        region: Optional region/oblast name for better accuracy
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    global last_request_time
    
    # Check in-memory cache first
    cache_key = f"{city_name}_{region or ''}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    # Check persistent cache
    if PERSISTENT_CACHE:
        cached_coords = get_from_cache(city_name, region)
        if cached_coords:
            _cache[cache_key] = cached_coords
            log.debug(f"Found in persistent cache: {city_name} -> {cached_coords}")
            return cached_coords
    
    # Prepare search query
    query_parts = [city_name]
    
    # Add region if provided
    if region:
        # Convert region aliases to full names
        region_map = {
            'київщина': 'Київська область',
            'харківщина': 'Харківська область',
            'одещина': 'Одеська область',
            'дніпропетровщина': 'Дніпропетровська область',
            'львівщина': 'Львівська область',
            'запорізька': 'Запорізька область',
            'донецька': 'Донецька область',
            'луганська': 'Луганська область',
            'миколаївщина': 'Миколаївська область',
            'черкащина': 'Черкаська область',
            'чернігівщина': 'Чернігівська область',
            'сумщина': 'Сумська область',
            'полтавщина': 'Полтавська область',
            'житомирщина': 'Житомирська область',
            'вінниччина': 'Вінницька область',
            'хмельниччина': 'Хмельницька область',
            'рівненщина': 'Рівненська область',
            'волинь': 'Волинська область',
            'закарпаття': 'Закарпатська область',
            'івано-франківщина': 'Івано-Франківська область',
            'тернопільщина': 'Тернопільська область',
            'херсонщина': 'Херсонська область',
            'кіровоградщина': 'Кіровоградська область',
        }
        region_full = region_map.get(region.lower(), region)
        query_parts.append(region_full)
    
    query_parts.append('Ukraine')
    search_query = ', '.join(query_parts)
    
    # Rate limiting
    current_time = time.time()
    time_since_last = current_time - last_request_time
    if time_since_last < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - time_since_last)
    
    try:
        # Make request to Nominatim API
        params = {
            'q': search_query,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'ua',  # Restrict to Ukraine
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': USER_AGENT
        }
        
        log.debug(f"Nominatim request: {search_query}")
        response = requests.get(NOMINATIM_ENDPOINT, params=params, headers=headers, timeout=5)
        last_request_time = time.time()
        
        if response.status_code == 200:
            results = response.json()
            if results and len(results) > 0:
                result = results[0]
                lat = float(result['lat'])
                lon = float(result['lon'])
                
                # Verify coordinates are within Ukraine bounds (approximate)
                if 43.0 <= lat <= 52.5 and 22.0 <= lon <= 41.0:
                    coords = (lat, lon)
                    _cache[cache_key] = coords
                    # Save to persistent cache
                    if PERSISTENT_CACHE:
                        try:
                            add_to_cache(city_name, coords, region)
                        except Exception as e:
                            log.warning(f"Failed to save to persistent cache: {e}")
                    log.info(f"Nominatim found: {city_name} -> {coords}")
                    return coords
                else:
                    log.warning(f"Nominatim returned coordinates outside Ukraine for {city_name}: {lat}, {lon}")
            else:
                log.debug(f"Nominatim found no results for {search_query}")
        else:
            log.warning(f"Nominatim API returned status {response.status_code}")
            
    except requests.RequestException as e:
        log.error(f"Nominatim API request failed for {city_name}: {e}")
    except Exception as e:
        log.error(f"Nominatim geocoding error for {city_name}: {e}")
    
    # Cache negative results too (to avoid repeated failed requests)
    _cache[cache_key] = None
    return None


def clear_cache():
    """Clear the geocoding cache"""
    global _cache
    _cache = {}
    log.info("Nominatim cache cleared")
