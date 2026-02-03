"""
Visicom Geocoder - Ukrainian geocoding service
API-based geocoding with smart region filtering
"""

import json
import os
import requests
import re
import threading

VISICOM_API_KEY = os.environ.get('VISICOM_API_KEY', '')

# Oblast name mappings for region filtering (short key -> full variations)
OBLAST_KEYS = {
    'київ': ['київ', 'київська', 'м. київ'],
    'харків': ['харків', 'харківська'],
    'одес': ['одеса', 'одеська'],
    'дніпр': ['дніпро', 'дніпропетровська', 'дніпропетров'],
    'запоріж': ['запоріжжя', 'запорізька', 'запоріз'],
    'львів': ['львів', 'львівська'],
    'миколаїв': ['миколаїв', 'миколаївська'],
    'херсон': ['херсон', 'херсонська'],
    'полтав': ['полтава', 'полтавська'],
    'сум': ['суми', 'сумська'],
    'чернігів': ['чернігів', 'чернігівська'],
    'вінниц': ['вінниця', 'вінницька'],
    'житомир': ['житомир', 'житомирська'],
    'черкас': ['черкаси', 'черкаська'],
    'кропивниц': ['кропивницький', 'кіровоградська', 'кіровоград'],
    'донец': ['донецьк', 'донецька'],
    'луганськ': ['луганськ', 'луганська'],
    'хмельниц': ['хмельницький', 'хмельницька'],
    'рівн': ['рівне', 'рівненська'],
    'волин': ['волинь', 'волинська', 'луцьк'],
    'тернопіл': ['тернопіль', 'тернопільська'],
    'івано-франків': ['івано-франківськ', 'івано-франківська'],
    'закарпат': ['ужгород', 'закарпатська', 'закарпаття'],
    'чернівц': ['чернівці', 'чернівецька'],
    'крим': ['крим', 'автономна республіка крим', 'севастополь'],
}

# Fallback: oblast centers for cases when city is not found
OBLAST_CENTERS = {
    'київ': (50.4501, 30.5234),
    'харків': (49.9935, 36.2304),
    'одес': (46.4825, 30.7233),
    'дніпр': (48.4647, 35.0462),
    'запоріж': (47.8388, 35.1396),
    'львів': (49.8397, 24.0297),
    'миколаїв': (46.9750, 31.9946),
    'херсон': (46.6354, 32.6169),
    'полтав': (49.5883, 34.5514),
    'сум': (50.9077, 34.7981),
    'чернігів': (51.4982, 31.2893),
    'вінниц': (49.2331, 28.4682),
    'житомир': (50.2547, 28.6587),
    'черкас': (49.4444, 32.0598),
    'кропивниц': (48.5079, 32.2623),
    'донец': (48.0159, 37.8028),
    'луганськ': (48.5740, 39.3078),
    'хмельниц': (49.4229, 26.9871),
    'рівн': (50.6199, 26.2516),
    'волин': (50.7472, 25.3254),
    'тернопіл': (49.5535, 25.5948),
    'івано-франків': (48.9226, 24.7111),
    'закарпат': (48.6208, 22.2879),
    'чернівц': (48.2921, 25.9358),
    'крим': (44.9521, 34.1024),
}

# Use /data for persistent storage on Render
def _get_cache_path(filename):
    persistent_dir = os.environ.get('PERSISTENT_DATA_DIR', '/data')
    if os.path.isdir(persistent_dir):
        return os.path.join(persistent_dir, filename)
    return os.path.join(os.path.dirname(__file__), filename)

CACHE_FILE = _get_cache_path('visicom_cache.json')
NEGATIVE_CACHE_FILE = _get_cache_path('visicom_cache_negative.json')

# Global caches
_cache = {}
_negative_cache = set()
_stats = {'hits': 0, 'misses': 0, 'api_calls': 0}
_cache_loaded = False


def _load_cache():
    """Load cache from disk"""
    global _cache, _negative_cache, _cache_loaded
    if _cache_loaded:
        return
    
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _cache = {k: tuple(v) for k, v in data.items()}
                print(f"[VISICOM] Cache loaded: {len(_cache)} cities", flush=True)
    except Exception as e:
        print(f"[VISICOM] Failed to load cache: {e}", flush=True)
    
    try:
        if os.path.exists(NEGATIVE_CACHE_FILE):
            with open(NEGATIVE_CACHE_FILE, 'r', encoding='utf-8') as f:
                _negative_cache = set(json.load(f))
                print(f"[VISICOM] Negative cache loaded: {len(_negative_cache)} entries", flush=True)
    except Exception as e:
        print(f"[VISICOM] Failed to load negative cache: {e}", flush=True)
    
    _cache_loaded = True


def _save_cache():
    """Save cache to disk"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({k: list(v) for k, v in _cache.items()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[VISICOM] Failed to save cache: {e}", flush=True)


def _save_negative_cache():
    """Save negative cache to disk"""
    try:
        with open(NEGATIVE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(_negative_cache), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[VISICOM] Failed to save negative cache: {e}", flush=True)


def _normalize_key(city: str, region: str = None) -> str:
    """Create cache key from city and region"""
    city_clean = city.lower().strip()
    
    if not region:
        return city_clean
    
    region_clean = region.lower().strip()
    # Remove common suffixes
    region_clean = region_clean.replace(' область', '')
    region_clean = region_clean.replace(' обл.', '')
    region_clean = region_clean.replace(' обл', '')
    region_clean = region_clean.strip()
    
    return f"{city_clean}|{region_clean}"


def _get_oblast_key(region: str) -> str:
    """Extract normalized oblast key from region string"""
    if not region:
        return None
    
    region_lower = region.lower().strip()
    region_lower = region_lower.replace(' область', '').replace(' обл.', '').replace(' обл', '').strip()
    
    # Find matching oblast
    for key, variants in OBLAST_KEYS.items():
        for variant in variants:
            if variant in region_lower or region_lower in variant:
                return key
    
    return region_lower[:6]  # First 6 chars as fallback


def _feature_matches_region(feature: dict, target_region_key: str) -> bool:
    """Check if Visicom feature belongs to target region"""
    if not target_region_key:
        return True  # No region filter
    
    props = feature.get('properties', {})
    
    # Visicom returns region in 'level1' field (e.g., "Дніпропетровська область")
    level1 = props.get('level1', '')
    name = props.get('name', '').lower()
    
    # Special case: Київ (capital) has no level1, but is its own region
    if not level1 and target_region_key == 'київ':
        if 'київ' in name:
            return True
    
    if not level1:
        return False
    
    level1 = level1.lower()
    
    # Direct match with key
    if target_region_key in level1:
        return True
    
    # Check all variants for this region
    for key, variants in OBLAST_KEYS.items():
        if key == target_region_key:
            for v in variants:
                if v in level1:
                    return True
    
    return False


def visicom_geocode(city: str, region: str = None) -> tuple:
    """
    Geocode a Ukrainian city using Visicom API with smart region filtering
    
    Args:
        city: City name (can be in any grammatical case)
        region: Oblast name (optional but helps with disambiguation)
    
    Returns:
        (lat, lng) tuple or None if not found
    """
    _load_cache()
    
    if not city:
        return None
    
    city_lower = city.lower().strip()
    
    # Special locations (sea, etc.) - not in API
    if 'чорн' in city_lower and 'мор' in city_lower:
        # Чорне море / Чорному морі - coordinates in Black Sea near Odesa
        print(f"[VISICOM] Special: Чорне море at (44.5, 31.5)", flush=True)
        return (44.5, 31.5)  # Black Sea coordinates
    
    if 'азов' in city_lower and 'мор' in city_lower:
        # Азовське море / Азовському морі
        print(f"[VISICOM] Special: Азовське море at (46.0, 36.5)", flush=True)
        return (46.0, 36.5)  # Azov Sea coordinates
    
    # 1. Check cache first
    key = _normalize_key(city, region)
    if key in _cache:
        _stats['hits'] += 1
        return _cache[key]
    
    # Also check city-only cache
    if city_lower in _cache:
        _stats['hits'] += 1
        return _cache[city_lower]
    
    # 2. Check negative cache
    if key in _negative_cache:
        _stats['hits'] += 1
        return None
    
    # 3. No API key - can't make requests
    if not VISICOM_API_KEY:
        print(f"[VISICOM] No API key, skipping '{city}'", flush=True)
        return None
    
    # 4. Call Visicom API
    _stats['misses'] += 1
    _stats['api_calls'] += 1
    
    target_region_key = _get_oblast_key(region)
    
    # Build query - try first with city only for more consistent results
    queries_to_try = [city]  # Start with just city name
    if region:
        region_clean = region.replace(' обл.', '').replace(' область', '').strip()
        queries_to_try.append(f"{city}, {region_clean}")  # Then try with region
    
    try:
        url = "https://api.visicom.ua/data-api/5.0/uk/geocode.json"
        
        for query in queries_to_try:
            params = {
                'text': query,
                'country': 'ua',
                'limit': 10,  # Get more results for filtering
                'key': VISICOM_API_KEY
            }
            
            print(f"[VISICOM] API: '{query}' (region_key: {target_region_key})", flush=True)
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', [])
                
                # Filter only settlement features
                settlement_features = [
                    f for f in features 
                    if f.get('properties', {}).get('categories') == 'adm_settlement'
                ]
                
                if settlement_features:
                    best_match = None
                    
                    # If we have region, try to find matching feature
                    if target_region_key:
                        for feature in settlement_features:
                            if _feature_matches_region(feature, target_region_key):
                                best_match = feature
                                break
                    
                    # Fallback to first settlement if no region match
                    if not best_match and not target_region_key:
                        best_match = settlement_features[0]
                    
                    if best_match:
                        # Extract coordinates
                        geo = best_match.get('geo_centroid', {})
                        props = best_match.get('properties', {})
                        
                        if geo and geo.get('type') == 'Point':
                            coords = geo.get('coordinates', [])
                            if len(coords) >= 2:
                                lng, lat = coords[0], coords[1]  # Visicom: [lng, lat]
                                
                                name = props.get('name', city)
                                level1 = props.get('level1', '')
                                
                                print(f"[VISICOM] Found: {name} ({level1}) at ({lat}, {lng})", flush=True)
                                
                                # Cache result
                                result = (lat, lng)
                                _cache[key] = result
                                _save_cache()
                                
                                return result
                    
            elif response.status_code == 403:
                print(f"[VISICOM] API key invalid", flush=True)
                return None
            elif response.status_code != 200:
                print(f"[VISICOM] API error: {response.status_code}", flush=True)
        
        # Not found after all queries - use oblast center as fallback
        if target_region_key and target_region_key in OBLAST_CENTERS:
            fallback = OBLAST_CENTERS[target_region_key]
            print(f"[VISICOM] City '{city}' not found, using {target_region_key} oblast center: {fallback}", flush=True)
            _cache[key] = fallback
            _save_cache()
            return fallback
        
        print(f"[VISICOM] No results for '{city}' in {region or 'any region'}", flush=True)
        _negative_cache.add(key)
        _save_negative_cache()
        return None
            
    except requests.exceptions.Timeout:
        print(f"[VISICOM] Timeout for '{query}'", flush=True)
        return None
    except Exception as e:
        print(f"[VISICOM] Error: {e}", flush=True)
        return None


def get_stats() -> dict:
    """Return geocoding statistics"""
    return _stats.copy()


def clear_negative_cache():
    """Clear the negative cache"""
    global _negative_cache
    _negative_cache = set()
    _save_negative_cache()
    print("[VISICOM] Negative cache cleared", flush=True)


def clear_all_cache():
    """Clear all caches"""
    global _cache, _negative_cache
    _cache = {}
    _negative_cache = set()
    _save_cache()
    _save_negative_cache()
    print("[VISICOM] All caches cleared", flush=True)


# Test
if __name__ == "__main__":
    test_cities = [
        ('Тузли', 'Одеська обл.'),
        ('Покровське', 'Дніпропетровська обл.'),
        ('Покровське', 'Донецька обл.'),
        ('Межову', 'Дніпропетровська обл.'),
        ('Богодухів', 'Харківська обл.'),
        ('Запоріжжя', 'Запорізька обл.'),
        ('Херсон', 'Херсонська обл.'),
        ('Миколаїв', 'Миколаївська обл.'),
    ]
    
    print("=== VISICOM GEOCODER TEST (API-based) ===\n")
    for city, region in test_cities:
        result = visicom_geocode(city, region)
        status = '✓' if result else '✗'
        print(f"{status} {city} ({region}) => {result}\n")
