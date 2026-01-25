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

# Use /data for persistent storage on Render, fallback to local dir
def _get_cache_path(filename):
    persistent_dir = os.environ.get('PERSISTENT_DATA_DIR', '/data')
    if os.path.isdir(persistent_dir):
        return os.path.join(persistent_dir, filename)
    return os.path.join(os.path.dirname(__file__), filename)

CACHE_FILE = _get_cache_path('geocode_cache.json')
NEGATIVE_CACHE_FILE = _get_cache_path('geocode_cache_negative.json')

# Global caches
_cache = {}  # city_key -> (lat, lon)
_negative_cache = set()  # city_keys that were not found

# Stats
_stats = {'hits': 0, 'misses': 0, 'api_calls': 0}


def _normalize_city_name(city: str) -> str:
    """Normalize Ukrainian city name from accusative to nominative case"""
    city_norm = city.strip()
    city_lower = city_norm.lower()
    
    # Specific known transformations (accusative -> nominative)
    known_transforms = {
        'хотімлю': 'Хотімля',
        'балаклію': 'Балаклія',
        'вовчанську': 'Вовчанськ',
        'богодухову': 'Богодухів',
        'мену': 'Мена',
        'конотопу': 'Конотоп',
        'шостку': 'Шостка',
        'суму': 'Суми',
        'харкову': 'Харків',
        'києву': 'Київ',
        'одесу': 'Одеса',
        'полтаву': 'Полтава',
        'дніпру': 'Дніпро',
        'херсону': 'Херсон',
        'запоріжжю': 'Запоріжжя',
        'миколаєву': 'Миколаїв',
        'чернігову': 'Чернігів',
        'ізюму': 'Ізюм',
        'куп\'янську': 'Куп\'янськ',
        'павлограду': 'Павлоград',
        'кременчуку': 'Кременчук',
        'бахмуту': 'Бахмут',
        'покровську': 'Покровськ',
        'маріуполю': 'Маріуполь',
        'мелітополю': 'Мелітополь',
        'енергодару': 'Енергодар',
        'лозову': 'Лозова',
        'бровари': 'Бровари',
        'славутичу': 'Славутич',
        # Multi-word cities in accusative case
        'гнилицю першу': 'Гнилиця Перша',
        'велику димерку': 'Велика Димерка',
        'велику виску': 'Велика Виска',
        'стару салтівку': 'Стара Салтівка',
        'козачу лопань': 'Козача Лопань',
        'малу данилівку': 'Мала Данилівка',
        'нову водолагу': 'Нова Водолага',
        'стару водолагу': 'Стара Водолага',
        # Single-word accusative endings -у/-ю
        'грушуваху': 'Грушуваха',
        'комишуваху': 'Комишуваха',
        'оріль': 'Орілька',
        'орільку': 'Орілька',
        # More multi-word cities
        'велику бабку': 'Велика Бабка',
        'малу бабку': 'Мала Бабка',
        'стару бабку': 'Стара Бабка',
        'нову бабку': 'Нова Бабка',
        'велику писарівку': 'Велика Писарівка',
        'малу писарівку': 'Мала Писарівка',
        'велику кохнівку': 'Велика Кохнівка',
        'зеленому': 'Зелене',
        # Cities with -у/-ну endings
        'березну': 'Березна',
        'васильківку': 'Васильківка',
        'дмитрівку': 'Дмитрівка',
    }
    
    if city_lower in known_transforms:
        return known_transforms[city_lower]
    
    # General rules for accusative -> nominative
    # -лю -> -ля (Хотімлю -> Хотімля)
    if city_lower.endswith('лю') and len(city_lower) > 3:
        return city_norm[:-1] + 'я'
    
    return city_norm


def _normalize_key(city: str, region: str = None) -> str:
    """Create normalized cache key from city and region"""
    if not city:
        return ""
    
    # First normalize accusative case to nominative
    city_normalized = _normalize_city_name(city)
    
    # Then lowercase and clean
    city_norm = city_normalized.lower().strip()
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


# Bounding boxes for EASTERN/FRONTLINE oblasts (priority regions for war context)
# Format: (lat_min, lat_max, lng_min, lng_max)
PRIORITY_OBLAST_BOUNDS = {
    'харківська': (48.5, 50.5, 34.5, 38.5),
    'харківськ': (48.5, 50.5, 34.5, 38.5),
    'донецька': (47.0, 49.5, 36.5, 39.5),
    'донецьк': (47.0, 49.5, 36.5, 39.5),
    'луганська': (48.0, 50.0, 37.5, 40.5),
    'луганськ': (48.0, 50.0, 37.5, 40.5),
    'запорізька': (46.5, 48.5, 34.0, 37.5),
    'запорізьк': (46.5, 48.5, 34.0, 37.5),
    'херсонська': (45.5, 47.5, 32.0, 35.5),
    'херсонськ': (45.5, 47.5, 32.0, 35.5),
    'дніпропетровська': (47.5, 49.5, 33.5, 36.5),
    'дніпропетровськ': (47.5, 49.5, 33.5, 36.5),
    'миколаївська': (46.0, 48.5, 30.5, 33.5),
    'миколаївськ': (46.0, 48.5, 30.5, 33.5),
    'одеська': (45.0, 48.5, 28.5, 33.5),
    'одеськ': (45.0, 48.5, 28.5, 33.5),
    'полтавська': (48.5, 50.5, 32.0, 35.5),
    'полтавськ': (48.5, 50.5, 32.0, 35.5),
    'сумська': (50.0, 52.5, 32.5, 35.5),
    'сумськ': (50.0, 52.5, 32.5, 35.5),
    'чернігівська': (50.5, 52.5, 30.5, 33.5),
    'чернігівськ': (50.5, 52.5, 30.5, 33.5),
    'київська': (49.0, 51.5, 29.0, 32.5),
    'київськ': (49.0, 51.5, 29.0, 32.5),
    'черкаська': (48.5, 50.0, 30.5, 33.0),
    'черкаськ': (48.5, 50.0, 30.5, 33.0),
    'кіровоградська': (47.5, 49.5, 30.5, 33.5),
    'кіровоградськ': (47.5, 49.5, 30.5, 33.5),
}


def _coords_in_oblast(lat: float, lng: float, region: str) -> bool:
    """Check if coordinates fall within oblast bounds"""
    if not region:
        return True
    region_lower = region.lower().strip()
    for oblast_key, bounds in PRIORITY_OBLAST_BOUNDS.items():
        if oblast_key in region_lower:
            lat_min, lat_max, lng_min, lng_max = bounds
            return lat_min <= lat <= lat_max and lng_min <= lng <= lng_max
    return True  # Unknown oblast - accept any coords


def _call_api(city: str, region: str = None) -> tuple:
    """Make actual API call to OpenCage. Returns (lat, lon) or None."""
    _stats['api_calls'] += 1
    
    # Normalize city name (accusative -> nominative)
    city_normalized = _normalize_city_name(city)
    
    # Build query with region context
    if region:
        region_clean = region.replace('область', '').replace('обл.', '').replace('обл', '').strip()
        query = f"{city_normalized}, {region_clean} область, Україна"
    else:
        query = f"{city_normalized}, Україна"
    
    print(f"[OPENCAGE] API call #{_stats['api_calls']}: '{query}'", flush=True)
    
    try:
        url = "https://api.opencagedata.com/geocode/v1/json"
        params = {
            'q': query,
            'key': OPENCAGE_API_KEY,
            'countrycode': 'ua',
            'limit': 5,  # Get more results to choose easternmost
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
            print(f"[OPENCAGE] No results for '{city}' in {region or 'any region'}", flush=True)
            return None
        
        # Simple logic: return first result that matches the specified region
        best_match = None
        
        for r in results:
            components = r.get('components', {})
            
            # Must be in Ukraine
            if components.get('country_code', '').lower() != 'ua':
                continue
            
            geo = r.get('geometry', {})
            lat = geo.get('lat')
            lng = geo.get('lng')
            if not lat or not lng:
                continue
            
            # If region specified, STRICTLY check coords fall within that region
            if region and not _coords_in_oblast(lat, lng, region):
                print(f"[OPENCAGE] Skipping ({lat:.2f}, {lng:.2f}) - outside {region}", flush=True)
                continue
            
            # Found a match in the correct region (or any region if not specified)
            print(f"[OPENCAGE] Found match: ({lat:.4f}, {lng:.4f}) in {region or 'Ukraine'}", flush=True)
            return (lat, lng)
        
        # No results in specified region
        if region:
            print(f"[OPENCAGE] No results found in {region} for '{city}'", flush=True)
        
        return None
        
    except Exception as e:
        print(f"[OPENCAGE] API exception: {e}", flush=True)
        return None


def geocode(city: str, region: str = None) -> tuple:
    """
    Geocode a city. Uses cache first, only calls API if needed.
    
    IMPORTANT: When region is specified, we ONLY use cache with matching region key.
    This prevents returning wrong city when same name exists in multiple oblasts.
    
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
    
    # === STEP 1.5: If region specified but not in cache, DON'T fall back to no-region key ===
    # This prevents "Комишуваха|запорізька" from using cached "Комишуваха" (which may be Донецька)
    
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
        print(f"[OPENCAGE] Cached: '{cache_key}' -> {result}", flush=True)
    else:
        _negative_cache.add(cache_key)
        _save_negative_cache()
        print(f"[OPENCAGE] Not found (cached negative): '{cache_key}'", flush=True)
    
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
