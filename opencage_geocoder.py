"""
OpenCage Geocoder with persistent cache
- Checks cache first, only calls API if not found
- Deduplicates requests in-flight
- Saves to JSON file for persistence
"""

import json
import os
import threading
import time
import requests

OPENCAGE_API_KEY = os.environ.get('OPENCAGE_API_KEY', 'c30fbe219d5d49ada3657da3326ca9b7')
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'geocode_cache.json')

# In-memory cache
_cache = {}
_cache_lock = threading.Lock()

# Track in-flight requests to avoid duplicates
_pending_requests = {}
_pending_lock = threading.Lock()

# Negative cache (cities not found)
_negative_cache = set()

def _load_cache():
    """Load cache from file on startup"""
    global _cache, _negative_cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _cache = {k: tuple(v) if isinstance(v, list) else v for k, v in data.items()}
                print(f"[OPENCAGE] Loaded {len(_cache)} entries from cache", flush=True)
    except Exception as e:
        print(f"[OPENCAGE] Error loading cache: {e}", flush=True)
        _cache = {}
    
    # Load negative cache
    neg_file = CACHE_FILE.replace('.json', '_negative.json')
    try:
        if os.path.exists(neg_file):
            with open(neg_file, 'r', encoding='utf-8') as f:
                _negative_cache = set(json.load(f))
                print(f"[OPENCAGE] Loaded {len(_negative_cache)} negative cache entries", flush=True)
    except:
        _negative_cache = set()

def _save_cache():
    """Save cache to file"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({k: list(v) if isinstance(v, tuple) else v for k, v in _cache.items()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[OPENCAGE] Error saving cache: {e}", flush=True)

def _save_negative_cache():
    """Save negative cache to file"""
    neg_file = CACHE_FILE.replace('.json', '_negative.json')
    try:
        with open(neg_file, 'w', encoding='utf-8') as f:
            json.dump(list(_negative_cache), f, ensure_ascii=False)
    except:
        pass

def _normalize_key(city: str, region: str = None) -> str:
    """Normalize cache key"""
    city_norm = city.lower().strip()
    # Normalize apostrophes
    city_norm = city_norm.replace('\u02bc', "'").replace('ʼ', "'").replace("'", "'").replace('`', "'")
    
    if region:
        region_norm = region.lower().strip()
        region_norm = region_norm.replace('область', '').replace('обл.', '').replace('обл', '').strip()
        return f"{city_norm}|{region_norm}"
    return city_norm

def geocode(city: str, region: str = None) -> tuple:
    """
    Geocode a city name, using cache first.
    
    Args:
        city: City name (e.g., "Харків", "Богодухів")
        region: Optional region/oblast (e.g., "Харківська", "Харківська область")
    
    Returns:
        (lat, lon) tuple or None if not found
    """
    if not city or len(city) < 2:
        return None
    
    cache_key = _normalize_key(city, region)
    
    # 1. Check memory cache
    with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key]
    
    # 2. Check negative cache (previously not found)
    if cache_key in _negative_cache:
        return None
    
    # 3. Check if request already in-flight (deduplication)
    with _pending_lock:
        if cache_key in _pending_requests:
            # Wait for the other request to complete
            event = _pending_requests[cache_key]
        else:
            event = threading.Event()
            _pending_requests[cache_key] = event
    
    # If we're waiting for another request
    if event.is_set() or (cache_key in _pending_requests and _pending_requests[cache_key] != event):
        event.wait(timeout=10)
        with _cache_lock:
            return _cache.get(cache_key)
    
    # 4. Call OpenCage API
    try:
        result = _call_opencage_api(city, region)
        
        with _cache_lock:
            if result:
                _cache[cache_key] = result
                _save_cache()
                print(f"[OPENCAGE] Geocoded '{city}' (region={region}) -> {result}", flush=True)
            else:
                _negative_cache.add(cache_key)
                _save_negative_cache()
                print(f"[OPENCAGE] Not found: '{city}' (region={region})", flush=True)
        
        return result
        
    except Exception as e:
        print(f"[OPENCAGE] Error geocoding '{city}': {e}", flush=True)
        return None
    finally:
        # Signal waiting threads
        with _pending_lock:
            if cache_key in _pending_requests:
                _pending_requests[cache_key].set()
                del _pending_requests[cache_key]

def _call_opencage_api(city: str, region: str = None) -> tuple:
    """Call OpenCage API"""
    
    # Build query
    if region:
        region_clean = region.replace('область', '').replace('обл.', '').replace('обл', '').strip()
        query = f"{city}, {region_clean} область, Україна"
    else:
        query = f"{city}, Україна"
    
    url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        'q': query,
        'key': OPENCAGE_API_KEY,
        'countrycode': 'ua',
        'limit': 3,
        'no_annotations': 1,
        'language': 'uk'
    }
    
    response = requests.get(url, params=params, timeout=5)
    
    if response.status_code == 402:
        print("[OPENCAGE] API quota exceeded!", flush=True)
        return None
    
    if not response.ok:
        print(f"[OPENCAGE] API error: {response.status_code}", flush=True)
        return None
    
    data = response.json()
    results = data.get('results', [])
    
    if not results:
        # Try without region
        if region:
            return _call_opencage_api(city, None)
        return None
    
    # Filter results - prefer settlements
    for r in results:
        components = r.get('components', {})
        comp_type = components.get('_type', '')
        
        # Check if it's in Ukraine
        if components.get('country_code', '').lower() != 'ua':
            continue
        
        # Prefer cities/villages/towns
        if comp_type in ['city', 'town', 'village', 'hamlet', 'suburb', 'neighbourhood']:
            geo = r.get('geometry', {})
            lat = geo.get('lat')
            lng = geo.get('lng')
            if lat and lng:
                return (lat, lng)
    
    # Fallback to first UA result
    for r in results:
        components = r.get('components', {})
        if components.get('country_code', '').lower() == 'ua':
            geo = r.get('geometry', {})
            lat = geo.get('lat')
            lng = geo.get('lng')
            if lat and lng:
                return (lat, lng)
    
    return None

def get_cache_stats() -> dict:
    """Get cache statistics"""
    return {
        'cached': len(_cache),
        'negative': len(_negative_cache),
        'pending': len(_pending_requests)
    }

# Load cache on module import
_load_cache()
