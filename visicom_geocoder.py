"""
Visicom Geocoder - Ukrainian geocoding service
Much better for Ukrainian city names with all grammatical cases (відмінки)
"""

import json
import os
import requests
import time
import threading

VISICOM_API_KEY = os.environ.get('VISICOM_API_KEY', '')

# Hardcoded coordinates for critical/ambiguous cities
HARDCODED_COORDS = {
    # === MAJOR CITIES ===
    'харків': (50.0047, 36.2314),
    'київ': (50.4501, 30.5234),
    'одеса': (46.4825, 30.7233),
    'дніпро': (48.4647, 35.0462),
    'запоріжжя': (47.8388, 35.1396),
    'львів': (49.8397, 24.0297),
    'кривий ріг': (47.9108, 33.3917),
    'миколаїв': (46.9750, 31.9946),
    'херсон': (46.6354, 32.6169),
    'полтава': (49.5883, 34.5514),
    'чернігів': (51.4982, 31.2893),
    'суми': (50.9077, 34.7981),
    'житомир': (50.2547, 28.6587),
    'вінниця': (49.2331, 28.4682),
    'черкаси': (49.4444, 32.0598),
    'кропивницький': (48.5079, 32.2623),
    
    # === FRONTLINE ===
    'бахмут': (48.5963, 37.9989),
    'покровськ': (48.2833, 37.1833),
    'торецьк': (48.4000, 37.8500),
    'часів яр': (48.5900, 37.8500),
    'авдіївка': (48.1400, 37.7500),
    'вугледар': (47.7833, 37.2500),
    'курахове': (47.9833, 37.2833),
    
    # === KHARKIV OBLAST ===
    'вовчанськ': (50.2889, 36.9417),
    'куп\'янськ': (49.7167, 37.6167),
    'ізюм': (49.2167, 37.2667),
    'богодухів': (50.1594, 35.5264),
    'гути': (50.2200, 35.5800),
    'краснокутськ': (49.9500, 35.1500),
    'лозова': (48.8833, 36.3167),
    'орілька': (49.1833, 35.7833),
    'балаклія': (49.4667, 36.8333),
    'первомайський': (49.3833, 37.4000),
    
    # === DNIPROPETROVSKA ===
    'павлоград': (48.5333, 35.8667),
    'синельникове': (48.3167, 35.5167),
    'межова': (48.2554, 36.7323),
    'межову': (48.2554, 36.7323),  # Accusative case
    'чаплине': (48.5833, 35.9500),
    'дмитрівка': (48.3500, 35.1667),
    'марганець': (47.6333, 34.6167),
    'нікополь': (47.5706, 34.3919),
    
    # === ZAPORIZKA ===
    'мелітополь': (46.8483, 35.3669),
    'токмак': (47.2500, 35.7167),
    'енергодар': (47.5000, 34.6500),
    'оріхів': (47.5667, 35.7833),
    'вільнянськ': (47.9431, 35.4083),
    'гуляйполе': (47.6667, 36.2500),
    'пологи': (47.4833, 36.2500),
    
    # === KHERSONSKA ===
    'нова каховка': (46.7500, 33.3667),
    'олешки': (46.6167, 32.7167),
    'генічеськ': (46.1764, 34.8042),
    'берислав': (46.8431, 33.4214),
    'бериславський район': (46.8431, 33.4214),  # District -> center city
    'скадовськ': (46.1167, 32.9167),
    'скадовський район': (46.1167, 32.9167),
    'каховка': (46.8167, 33.4833),
    'каховський район': (46.8167, 33.4833),
    'чаплинка': (46.3667, 33.5333),
    'чаплинський район': (46.3667, 33.5333),
    
    # === MYKOLAIVSKA ===
    'вознесенськ': (47.5667, 31.3167),
    'первомайськ': (48.0500, 30.8500),
    'дніпровське': (47.0000, 32.3500),
    'миколаївський район': (46.9750, 31.9946),  # District -> Mykolaiv city
    'баштанка': (47.4167, 32.4333),
    'баштанський район': (47.4167, 32.4333),
    'снігурівка': (47.0667, 32.8000),
    'снігурівський район': (47.0667, 32.8000),
    
    # === POLTAVSKA ===
    'кременчук': (49.0647, 33.4157),
    'семенівка': (50.0833, 33.5333),
    'хорол': (49.7833, 33.2667),
    'миргород': (49.9667, 33.6000),
    'лубни': (50.0167, 32.9833),
    
    # === SUMSKA ===
    'конотоп': (51.2333, 33.2000),
    'охтирка': (50.3000, 34.9000),
    'шостка': (51.8667, 33.4833),
    'глухів': (51.6833, 33.9167),
    'есмань': (51.7667, 33.8667),
    'ромни': (50.7500, 33.4667),
    'лебедин': (50.5833, 34.4833),
    'тростянець': (50.4833, 34.9667),
    'білопілля': (51.1500, 34.3000),
    'сумський район': (50.9077, 34.7981),  # District -> Sumy city
    
    # === CHERNIHIVSKA ===
    'сновськ': (51.8167, 32.0333),
    'городня': (51.9333, 31.5833),
    'ніжин': (51.0500, 31.8833),
    'прилуки': (50.5833, 32.4000),
    'новгород-сіверський': (52.0000, 33.2667),
    'щорс': (51.8167, 32.0333),  # Old name for Сновськ
    
    # === DUPLICATE NAMES (with region key) ===
    # Покровське - є в багатьох областях
    'покровське|дніпропетров': (48.1333, 36.2500),  # Дніпропетровська
    'покровське|кіровоград': (48.5500, 32.4833),    # Кіровоградська
    'покровське|донец': (48.2833, 37.1833),         # Донецька (Покровськ)
    'покровське|запоріз': (47.4000, 35.5000),       # Запорізька
    'покровське|харків': (49.9167, 36.3500),        # Харківська
    
    # Петрівка - дуже поширена назва
    'петрівка|дніпропетров': (48.4167, 35.8333),
    'петрівка|кіровоград': (48.4500, 32.5000),
    'петрівка|запоріз': (47.3500, 35.1667),
    'петрівка|харків': (49.8333, 36.4167),
    
    # Новоселівка - теж багато
    'новоселівка|дніпропетров': (48.3833, 35.4500),
    'новоселівка|донец': (48.1500, 37.5000),
    'новоселівка|харків': (49.6667, 36.5833),
    'новоселівка|запоріз': (47.2833, 35.3333),
    
    # Степове
    'степове|дніпропетров': (48.5000, 35.2500),
    'степове|запоріз': (47.4167, 35.6667),
    'степове|херсон': (46.7500, 33.5000),
    
    # Зелене
    'зелене|дніпропетров': (48.4833, 35.5500),
    'зелене|запоріз': (47.5167, 35.7500),
    'зелене|харків': (49.7500, 36.4167),
    
    # Калинівка
    'калинівка|дніпропетров': (48.4000, 35.3333),
    'калинівка|вінниц': (49.4500, 28.5167),
    'калинівка|київ': (50.5500, 30.3000),
    
    # Шевченкове
    'шевченкове|дніпропетров': (48.3667, 35.6500),
    'шевченкове|харків': (49.7000, 37.1000),
    'шевченкове|кіровоград': (48.6167, 32.6333),
    
    # Михайлівка
    'михайлівка|дніпропетров': (48.4333, 35.7500),
    'михайлівка|запоріз': (47.1833, 35.2167),
    'михайлівка|харків': (49.9500, 36.7833),
    
    # === ZAPORIZKA DISTRICTS ===
    'запорізький район': (47.8388, 35.1396),
    'мелітопольський район': (46.8483, 35.3669),
    'бердянський район': (46.7500, 36.7833),
    'бердянськ': (46.7500, 36.7833),
    
    # === DNIPROPETROVSKA DISTRICTS ===
    'дніпровський район': (48.4647, 35.0462),
    'криворізький район': (47.9108, 33.3917),
    'нікопольський район': (47.5706, 34.3919),
    'павлоградський район': (48.5333, 35.8667),
    'синельниківський район': (48.3167, 35.5167),
    
    # === KHARKIVSKA DISTRICTS ===
    'харківський район': (50.0047, 36.2314),
    'ізюмський район': (49.2167, 37.2667),
    'куп\'янський район': (49.7167, 37.6167),
    'богодухівський район': (50.1594, 35.5264),
    'чугуївський район': (49.8333, 36.6833),
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

# Rate limiting
_api_call_times = []
_api_rate_limit_lock = threading.Lock()


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
    region_clean = region_clean.replace('ська', '')
    region_clean = region_clean.replace('ський', '')
    region_clean = region_clean.strip()
    
    return f"{city_clean}|{region_clean}"


def _check_hardcoded(city: str, region: str = None) -> tuple:
    """Check hardcoded coordinates first"""
    city_lower = city.lower().strip()
    
    # Try with region first
    if region:
        key = _normalize_key(city, region)
        if key in HARDCODED_COORDS:
            return HARDCODED_COORDS[key]
    
    # Try city only
    if city_lower in HARDCODED_COORDS:
        return HARDCODED_COORDS[city_lower]
    
    return None


def visicom_geocode(city: str, region: str = None) -> tuple:
    """
    Geocode a Ukrainian city using Visicom API
    
    Args:
        city: City name (can be in any grammatical case)
        region: Oblast name (optional)
    
    Returns:
        (lat, lng) tuple or None if not found
    """
    _load_cache()
    
    if not city:
        return None
    
    # 1. Check hardcoded first
    hardcoded = _check_hardcoded(city, region)
    if hardcoded:
        _stats['hits'] += 1
        return hardcoded
    
    # 2. Check cache
    key = _normalize_key(city, region)
    if key in _cache:
        _stats['hits'] += 1
        return _cache[key]
    
    # 3. Check negative cache
    if key in _negative_cache:
        _stats['hits'] += 1
        return None
    
    # 4. No API key - can't make requests
    if not VISICOM_API_KEY:
        print(f"[VISICOM] No API key, skipping API call for '{city}'", flush=True)
        return None
    
    # 5. Call Visicom API
    _stats['misses'] += 1
    _stats['api_calls'] += 1
    
    # Build query
    if region:
        # Clean region name
        region_clean = region.replace(' обл.', '').replace(' область', '').strip()
        query = f"{city}, {region_clean}"
    else:
        query = city
    
    try:
        url = "https://api.visicom.ua/data-api/5.0/uk/geocode.json"
        params = {
            'text': query,
            'categories': 'adm_settlement',  # Only settlements
            'country': 'ua',
            'limit': 5,
            'key': VISICOM_API_KEY
        }
        
        print(f"[VISICOM] API call: '{query}'", flush=True)
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Visicom returns features array
            features = data.get('features', [])
            
            if features:
                # Get first result
                feature = features[0]
                props = feature.get('properties', {})
                geo = feature.get('geo_centroid', {})
                
                # Extract coordinates
                if geo and 'type' in geo and geo['type'] == 'Point':
                    coords = geo.get('coordinates', [])
                    if len(coords) >= 2:
                        lng, lat = coords[0], coords[1]  # Visicom returns [lng, lat]
                        
                        name = props.get('name', city)
                        settlement_type = props.get('settlement_type', 'unknown')
                        
                        print(f"[VISICOM] Found: {name} ({settlement_type}) at ({lat}, {lng})", flush=True)
                        
                        # Cache result
                        result = (lat, lng)
                        _cache[key] = result
                        _save_cache()
                        
                        return result
            
            # Not found
            print(f"[VISICOM] No results for '{query}'", flush=True)
            _negative_cache.add(key)
            _save_negative_cache()
            return None
            
        elif response.status_code == 403:
            print(f"[VISICOM] API key invalid or expired", flush=True)
            return None
        else:
            print(f"[VISICOM] API error: {response.status_code}", flush=True)
            return None
            
    except requests.exceptions.Timeout:
        print(f"[VISICOM] Request timeout for '{query}'", flush=True)
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


# Test
if __name__ == "__main__":
    test_cities = [
        ('Межову', 'Дніпропетровська обл.'),
        ('Чаплине', 'Дніпропетровська обл.'),
        ('Семенівка', 'Полтавська обл.'),
        ('Хорол', 'Полтавська обл.'),
        ('Богодухів', 'Харківська обл.'),
        ('Гути', 'Харківська обл.'),
        ('Павлоград', 'Дніпропетровська обл.'),
        ('Запоріжжя', 'Запорізька обл.'),
        ('Херсон', 'Херсонська обл.'),
    ]
    
    print("=== VISICOM GEOCODER TEST ===\n")
    for city, region in test_cities:
        result = visicom_geocode(city, region)
        status = '✓' if result else '✗'
        print(f"{status} {city} ({region}) => {result}")
