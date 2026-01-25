"""
OpenCage Geocoder with MAXIMUM economy mode
- Single API call per unique city
- Persistent JSON cache
- Negative cache for not-found cities
"""

import json
import os
import requests

OPENCAGE_API_KEY = os.environ.get('OPENCAGE_API_KEY', 'c30fbe219d5d49ada3657da3326ca9b7')
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'geocode_cache.json')
NEGATIVE_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'geocode_cache_negative.json')

# Global caches
_cache = {}  # city_key -> (lat, lon)
_negative_cache = set()  # city_keys that were not found

# Stats
_stats = {'hits': 0, 'misses': 0, 'api_calls': 0}


def _normalize_key(city: str, region: str = None) -> str:
    """Create normalized cache key from city and region"""
    if not city:
        return ""
    
    # Normalize city
    city_norm = city.lower().strip()
    city_norm = city_norm.replace('\u02bc', "'").replace('ʼ', "'").replace("'", "'").replace('`', "'")
    city_norm = city_norm.replace('ё', 'е')  # normalize ё -> е
    
    # Normalize region - keep original form, just lowercase
    if region:
        region_norm = region.lower().strip()
        # Only remove "область" and "обл" words, keep regional suffix like "ська"
        region_norm = region_norm.replace(' область', '').replace(' обл.', '').replace(' обл', '')
        region_norm = region_norm.strip()
        if region_norm:
            return f"{city_norm}|{region_norm}"
    
    return city_norm


def _load_cache():
    """Load cache from disk"""
    global _cache, _negative_cache
    
    # Load positive cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both formats: {key: [lat, lon]} and {key: {coords: [lat, lon], ...}}
                for k, v in data.items():
                    if isinstance(v, dict) and 'coords' in v:
                        # New format with metadata
                        coords = v['coords']
                        _cache[k] = tuple(coords) if isinstance(coords, list) else coords
                    elif isinstance(v, list):
                        # Simple format [lat, lon]
                        _cache[k] = tuple(v)
                    elif isinstance(v, tuple):
                        _cache[k] = v
                print(f"[OPENCAGE] Cache loaded: {len(_cache)} cities", flush=True)
    except Exception as e:
        print(f"[OPENCAGE] Error loading cache: {e}", flush=True)
        _cache = {}
    
    # Load negative cache
    try:
        if os.path.exists(NEGATIVE_CACHE_FILE):
            with open(NEGATIVE_CACHE_FILE, 'r', encoding='utf-8') as f:
                _negative_cache = set(json.load(f))
                print(f"[OPENCAGE] Negative cache loaded: {len(_negative_cache)} entries", flush=True)
    except:
        _negative_cache = set()


def _save_cache():
    """Save positive cache to disk"""
    try:
        data = {k: list(v) if isinstance(v, tuple) else v for k, v in _cache.items()}
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[OPENCAGE] Error saving cache: {e}", flush=True)


def _save_negative_cache():
    """Save negative cache to disk"""
    try:
        with open(NEGATIVE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(_negative_cache), f, ensure_ascii=False)
    except:
        pass


def _call_api(city: str, region: str = None) -> tuple:
    """Make actual API call to OpenCage. Returns (lat, lon) or None."""
    _stats['api_calls'] += 1
    
    # Build query with region context
    if region:
        region_clean = region.replace('область', '').replace('обл.', '').replace('обл', '').strip()
        query = f"{city}, {region_clean} область, Україна"
    else:
        query = f"{city}, Україна"
    
    print(f"[OPENCAGE] API call #{_stats['api_calls']}: '{query}'", flush=True)
    
    try:
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
            print("[OPENCAGE] QUOTA EXCEEDED!", flush=True)
            return None
        
        if not response.ok:
            print(f"[OPENCAGE] API error: {response.status_code}", flush=True)
            return None
        
        data = response.json()
        results = data.get('results', [])
        
        if not results:
            # Retry without region if we had one
            if region:
                print(f"[OPENCAGE] No results with region, retrying without...", flush=True)
                return _call_api(city, None)
            return None
        
        # Filter results - prefer settlements in Ukraine
        for r in results:
            components = r.get('components', {})
            
            # Must be in Ukraine
            if components.get('country_code', '').lower() != 'ua':
                continue
            
            # Prefer specific place types
            comp_type = components.get('_type', '')
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
        
    except Exception as e:
        print(f"[OPENCAGE] API exception: {e}", flush=True)
        return None


def geocode(city: str, region: str = None) -> tuple:
    """
    Geocode a city. Uses cache first, only calls API if needed.
    
    Returns: (lat, lon) tuple or None
    """
    if not city or len(city) < 2:
        return None
    
    cache_key = _normalize_key(city, region)
    if not cache_key:
        return None
    
    # === STEP 1: Check positive cache ===
    if cache_key in _cache:
        _stats['hits'] += 1
        return _cache[cache_key]
    
    # === STEP 2: Check negative cache ===
    if cache_key in _negative_cache:
        _stats['hits'] += 1
        return None
    
    # === STEP 3: Call API ===
    _stats['misses'] += 1
    result = _call_api(city, region)
    
    if result:
        _cache[cache_key] = result
        _save_cache()
        print(f"[OPENCAGE] Cached: '{city}' -> {result}", flush=True)
    else:
        _negative_cache.add(cache_key)
        _save_negative_cache()
        print(f"[OPENCAGE] Not found (cached negative): '{city}'", flush=True)
    
    return result


def get_cache_stats() -> dict:
    """Get geocoding statistics"""
    return {
        'cached': len(_cache),
        'negative_cached': len(_negative_cache),
        'hits': _stats['hits'],
        'misses': _stats['misses'],
        'api_calls': _stats['api_calls']
    }


def preload_from_dict(coords_dict: dict):
    """Preload cache from existing coordinates dictionary (e.g., CITY_COORDS)"""
    count = 0
    with _cache_lock:
        for key, coords in coords_dict.items():
            if coords and isinstance(coords, (tuple, list)) and len(coords) >= 2:
                cache_key = _normalize_key(key)
                if cache_key and cache_key not in _cache:
                    _cache[cache_key] = (coords[0], coords[1])
                    count += 1
    if count:
        _save_cache()
        print(f"[OPENCAGE] Preloaded {count} entries from existing coords", flush=True)


# Load cache on module import
_load_cache()
