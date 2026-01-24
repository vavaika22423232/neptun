"""
Nominatim geocoder for Ukrainian cities
Uses OpenStreetMap Nominatim API
"""

import requests
import time
import json
import os

# Cache file
NOMINATIM_CACHE_FILE = 'nominatim_cache.json'
NOMINATIM_CACHE_TTL = 60 * 60 * 24 * 30  # 30 days

_nominatim_cache = None
_last_request_time = 0
MIN_REQUEST_INTERVAL = 1.0  # Nominatim requires 1 second between requests


def _load_cache():
    global _nominatim_cache
    if _nominatim_cache is not None:
        return _nominatim_cache
    if os.path.exists(NOMINATIM_CACHE_FILE):
        try:
            with open(NOMINATIM_CACHE_FILE, encoding='utf-8') as f:
                _nominatim_cache = json.load(f)
        except Exception:
            _nominatim_cache = {}
    else:
        _nominatim_cache = {}
    return _nominatim_cache


def _save_cache():
    if _nominatim_cache is None:
        return
    try:
        # Limit cache size
        cache_to_save = _nominatim_cache
        if len(_nominatim_cache) > 2000:
            items = list(_nominatim_cache.items())
            cache_to_save = dict(items[-2000:])
        with open(NOMINATIM_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_to_save, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_coordinates_nominatim(city_name: str, region: str = None):
    """
    Get coordinates for a Ukrainian city using Nominatim API.
    
    Args:
        city_name: Name of the city/town/village
        region: Optional oblast/region name for disambiguation
        
    Returns:
        Tuple (lat, lng) or None if not found
    """
    global _last_request_time
    
    if not city_name:
        return None
    
    city_name = city_name.strip()
    if not city_name:
        return None
    
    # Build cache key
    cache_key = f"{city_name.lower()}|{(region or '').lower()}"
    
    # Check cache
    cache = _load_cache()
    if cache_key in cache:
        entry = cache[cache_key]
        if time.time() - entry.get('ts', 0) < NOMINATIM_CACHE_TTL:
            coords = entry.get('coords')
            if coords:
                return tuple(coords)
            return None
    
    # Rate limiting - Nominatim requires 1 request per second
    elapsed = time.time() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    
    # Build search queries
    queries = []
    if region:
        # Clean region name
        region_clean = region.replace('область', '').replace('обл.', '').replace('обл', '').strip()
        queries.append(f"{city_name}, {region_clean} область, Україна")
        queries.append(f"{city_name}, {region_clean}, Ukraine")
    queries.append(f"{city_name}, Україна")
    queries.append(f"{city_name}, Ukraine")
    
    url = 'https://nominatim.openstreetmap.org/search'
    headers = {
        'User-Agent': 'NeptunAlarm/2.0 (https://neptun.in.ua; contact@neptun.in.ua)'
    }
    
    for query in queries:
        try:
            params = {
                'q': query,
                'format': 'json',
                'limit': 5,
                'addressdetails': 1,
                'countrycodes': 'ua'
            }
            
            _last_request_time = time.time()
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.ok:
                data = response.json()
                
                for item in data:
                    item_type = item.get('type', '')
                    item_class = item.get('class', '')
                    
                    # Filter for settlements only
                    valid_types = ['village', 'town', 'city', 'hamlet', 'suburb', 
                                   'neighbourhood', 'residential', 'administrative']
                    if item_type not in valid_types and item_class != 'place':
                        continue
                    
                    lat = item.get('lat')
                    lng = item.get('lon')
                    
                    if lat and lng:
                        try:
                            lat_f = float(lat)
                            lng_f = float(lng)
                            
                            # Validate Ukraine bounds
                            if 43.0 <= lat_f <= 53.0 and 22.0 <= lng_f <= 41.0:
                                # If region specified, verify it matches
                                if region:
                                    display_name = item.get('display_name', '').lower()
                                    region_lower = region.lower()
                                    region_clean_lower = region_clean.lower() if region_clean else ''
                                    
                                    if region_lower not in display_name and region_clean_lower not in display_name:
                                        continue
                                
                                coords = (lat_f, lng_f)
                                cache[cache_key] = {'coords': list(coords), 'ts': time.time()}
                                _save_cache()
                                return coords
                        except (ValueError, TypeError):
                            continue
                            
        except requests.exceptions.Timeout:
            print(f"Nominatim timeout for: {query}")
            continue
        except Exception as e:
            print(f"Nominatim error for '{query}': {e}")
            continue
    
    # Cache negative result
    cache[cache_key] = {'coords': None, 'ts': time.time()}
    _save_cache()
    return None


# Quick test
if __name__ == '__main__':
    # Test cases
    tests = [
        ('Київ', None),
        ('Харків', 'Харківська область'),
        ('Борова', 'Харківська область'),
        ('Миколаївка', 'Донецька область'),
        ('Запоріжжя', None),
    ]
    
    for city, region in tests:
        coords = get_coordinates_nominatim(city, region)
        print(f"{city} ({region}): {coords}")
