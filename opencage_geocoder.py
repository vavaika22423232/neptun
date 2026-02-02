"""
OpenCage Geocoder with MAXIMUM economy mode
- Single API call per unique city
- Persistent JSON cache
- Negative cache for not-found cities
- Rate limiting and batch processing
"""

import json
import os
import requests
import time
import threading

OPENCAGE_API_KEY = os.environ.get('OPENCAGE_API_KEY', 'c30fbe219d5d49ada3657da3326ca9b7')

# Hardcoded coordinates for ambiguous cities that confuse geocoder
# These override geocoder results to prevent wrong locations
HARDCODED_COORDS = {
    # === MAJOR CITIES ===
    'харків': (50.0047, 36.2314),
    'харків|харківська': (50.0047, 36.2314),
    'київ': (50.4501, 30.5234),
    'одеса': (46.4825, 30.7233),
    'дніпро': (48.4647, 35.0462),
    'дніпро|дніпропетровська': (48.4647, 35.0462),
    'запоріжжя': (47.8388, 35.1396),
    'запоріжжя|запорізька': (47.8388, 35.1396),
    'львів': (49.8397, 24.0297),
    'кривій ріг': (47.9108, 33.3917),
    'миколаїв': (46.9750, 31.9946),
    'маріуполь': (47.0951, 37.5494),
    'луганськ': (48.5740, 39.3078),
    'севастополь': (44.6167, 33.5250),
    'вінниця': (49.2331, 28.4682),
    'сімферополь': (44.9521, 34.1024),
    'макіївка': (48.0472, 37.9658),
    'херсон': (46.6354, 32.6169),
    'полтава': (49.5883, 34.5514),
    'чернігів': (51.4982, 31.2893),
    'черкаси': (49.4444, 32.0598),
    'суми': (50.9077, 34.7981),
    'житомир': (50.2547, 28.6587),
    'хмельницький': (49.4229, 26.9871),
    'чернівці': (48.2921, 25.9358),
    'рівне': (50.6199, 26.2516),
    'кропивницький': (48.5079, 32.2623),
    'івано-франківськ': (48.9226, 24.7111),
    'кременчук': (49.0647, 33.4157),
    'тернопіль': (49.5535, 25.5948),
    'луцьк': (50.7472, 25.3254),
    'біла церква': (49.7878, 30.1119),
    'краматорськ': (48.7233, 37.5562),
    'краматорськ|донецька': (48.7233, 37.5562),
    'мелітополь': (46.8483, 35.3669),
    'мелітополь|запорізька': (46.8483, 35.3669),
    'керч': (45.3569, 36.4706),
    'ужгород': (48.6208, 22.2879),
    'бровари': (50.5108, 30.7897),
    'алчевськ': (48.4706, 38.8000),
    'павлоград': (48.5333, 35.8667),
    'слов\'янськ': (48.8575, 37.6200),
    'слов\'янськ|донецька': (48.8575, 37.6200),
    'євпаторія': (45.1897, 33.3669),
    'каміянець-подільський': (48.6819, 26.5856),
    'лисичанськ': (48.9167, 38.4333),
    'ялта': (44.4953, 34.1664),
    
    # === FRONTLINE CITIES (updated names) ===
    'бахмут': (48.5963, 37.9989),
    'бахмут|донецька': (48.5963, 37.9989),
    'торецьк': (48.4000, 37.8500),
    'торецьк|донецька': (48.4000, 37.8500),
    'лиман': (48.9833, 37.8000),
    'лиман|донецька': (48.9833, 37.8000),
    'мирноград': (48.2833, 37.2667),
    'мирноград|донецька': (48.2833, 37.2667),
    'покровськ': (48.2833, 37.1833),
    'покровськ|донецька': (48.2833, 37.1833),
    'селидове': (48.1458, 37.3028),
    'селидове|донецька': (48.1458, 37.3028),
    'авдіївка': (48.1400, 37.7500),
    'авдіївка|донецька': (48.1400, 37.7500),
    'часів яр': (48.5900, 37.8500),
    'часів яр|донецька': (48.5900, 37.8500),
    'новогродівка': (48.3167, 37.4000),
    'новогродівка|донецька': (48.3167, 37.4000),
    'вугледар': (47.7833, 37.2500),
    'вугледар|донецька': (47.7833, 37.2500),
    'курахове': (47.9833, 37.2833),
    'курахове|донецька': (47.9833, 37.2833),
    'новоолександрівка': (48.2667, 37.1000),
    'новоолександрівка|донецька': (48.2667, 37.1000),
    
    # === KHARKIV OBLAST ===
    'ізюм': (49.2167, 37.2667),
    'ізюм|харківська': (49.2167, 37.2667),
    'куп\'янськ': (49.7167, 37.6167),
    'куп\'янськ|харківська': (49.7167, 37.6167),
    'балаклія': (49.4667, 36.8333),
    'балаклія|харківська': (49.4667, 36.8333),
    'вовчанськ': (50.2889, 36.9417),
    'вовчанськ|харківська': (50.2889, 36.9417),
    'чугуїв': (49.8333, 36.6833),
    'чугуїв|харківська': (49.8333, 36.6833),
    'лозова': (48.8833, 36.3167),
    'лозова|харківська': (48.8833, 36.3167),
    'первомайський': (49.3833, 37.4000),
    'первомайський|харківська': (49.3833, 37.4000),
    
    # === ZAPORIZHZHIA OBLAST ===
    'енергодар': (47.5000, 34.6500),
    'енергодар|запорізька': (47.5000, 34.6500),
    'токмак': (47.2500, 35.7167),
    'токмак|запорізька': (47.2500, 35.7167),
    'оріхів': (47.5667, 35.7833),
    'оріхів|запорізька': (47.5667, 35.7833),
    'пологи': (47.4833, 36.2500),
    'пологи|запорізька': (47.4833, 36.2500),
    'василівка': (47.4403, 35.2808),
    'василівка|запорізька': (47.4403, 35.2808),
    'гуляйполе': (47.6667, 36.2500),
    'гуляйполе|запорізька': (47.6667, 36.2500),
    
    # === KHERSON OBLAST ===
    'нова каховка': (46.7500, 33.3667),
    'нова каховка|херсонська': (46.7500, 33.3667),
    'каховка': (46.8167, 33.4833),
    'каховка|херсонська': (46.8167, 33.4833),
    'скадовськ': (46.1167, 32.9167),
    'скадовськ|херсонська': (46.1167, 32.9167),
    'олешки': (46.6167, 32.7167),
    'олешки|херсонська': (46.6167, 32.7167),
    'генічеськ': (46.1764, 34.8042),
    'генічеськ|херсонська': (46.1764, 34.8042),
    
    # === DONETSK OBLAST (more cities) ===
    'костянтинівка': (48.5167, 37.7167),
    'костянтинівка|донецька': (48.5167, 37.7167),
    'дружківка': (48.6167, 37.5500),
    'дружківка|донецька': (48.6167, 37.5500),
    'добропілля': (48.4667, 37.0833),
    'добропілля|донецька': (48.4667, 37.0833),
    'волноваха': (47.6000, 37.5000),
    'волноваха|донецька': (47.6000, 37.5000),
    'маріїнка': (47.9417, 37.5083),
    'маріїнка|донецька': (47.9417, 37.5083),
    'красногорівка': (48.0250, 37.5417),
    'красногорівка|донецька': (48.0250, 37.5417),
    
    # === AMBIGUOUS CITIES (same name in different oblasts) ===
    'степногірськ|запорізька': (47.295, 35.482),
    'степногірськ': (47.295, 35.482),
    'біленьке|запорізька': (47.8525, 35.1883),
    'біленьке': (47.8525, 35.1883),
    'комишуваха|запорізька': (47.6667, 35.3167),
    'комишуваха|донецька': (47.9167, 37.8333),
    'петрівка|харківська': (49.4167, 36.2833),
    'петрівка|донецька': (48.1833, 37.8000),
    'петрівка|запорізька': (47.5833, 35.0167),
    'новопетрівка|харківська': (49.3833, 36.3167),
    'михайлівка|запорізька': (47.2667, 35.2333),
    'михайлівка|донецька': (48.3500, 37.6167),
}

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

# Rate limiting for API calls
_api_call_times = []
_api_rate_limit_lock = threading.Lock()
_MAX_API_CALLS_PER_SECOND = 1  # OpenCage free tier: 1 req/sec
_MAX_API_CALLS_PER_DAY = 2500  # OpenCage free tier daily limit


def _check_rate_limit() -> bool:
    """Check if we can make an API call within rate limits"""
    with _api_rate_limit_lock:
        now = time.time()
        
        # Clean old timestamps (older than 24 hours)
        _api_call_times[:] = [t for t in _api_call_times if now - t < 86400]
        
        # Check daily limit
        if len(_api_call_times) >= _MAX_API_CALLS_PER_DAY:
            print(f"[OPENCAGE] Daily rate limit reached ({_MAX_API_CALLS_PER_DAY} calls)", flush=True)
            return False
        
        # Check per-second limit
        recent_calls = [t for t in _api_call_times if now - t < 1.0]
        if len(recent_calls) >= _MAX_API_CALLS_PER_SECOND:
            # Wait a bit
            sleep_time = 1.0 - (now - recent_calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        _api_call_times.append(now)
        return True


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
        'олександрію': 'Олександрія',
        'кіровограду': 'Кропивницький',
        'кропивницькому': 'Кропивницький',
        'світловодську': 'Світловодськ',
        'знам\'янку': 'Знам\'янка',
        'долинську': 'Долинська',
        'краматорську': 'Краматорськ',
        'костянтинівку': 'Костянтинівка',
        'слов\'янську': 'Слов\'янськ',
        'лиману': 'Лиман',
        'торецьку': 'Торецьк',
        'часів яру': 'Часів Яр',
        'новогродівку': 'Новогродівка',
        'селидову': 'Селидове',
        'мирнограду': 'Мирноград',
        'авдіївку': 'Авдіївка',
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
        'пантаївку': 'Пантаївка',
        'новоукраїнку': 'Новоукраїнка',
        'голованівську': 'Голованівськ',
        'добровеличківку': 'Добровеличківка',
        'устинівку': 'Устинівка',
        'компаніївку': 'Компаніївка',
        'петрівку': 'Петрівка',
        'новомиргороду': 'Новомиргород',
        'гайворону': 'Гайворон',
        # Ambiguous cities that can be confused with other countries
        'степногірську': 'Степногірськ',
        'степногорськ': 'Степногірськ',
        # Latinized/transliterated variants
        'kharkiv': 'Харків',
        'kyiv': 'Київ',
        'odesa': 'Одеса',
        'dnipro': 'Дніпро',
        'lviv': 'Львів',
        'zaporizhzhia': 'Запоріжжя',
        'mariupol': 'Маріуполь',
    }
    
    if city_lower in known_transforms:
        return known_transforms[city_lower]
    
    # General rules for accusative -> nominative
    # -ку -> -ка (villages ending in -ка: Пантаївку -> Пантаївка)
    if city_lower.endswith('ку') and len(city_lower) > 3:
        return city_norm[:-1] + 'а'
    # -лю -> -ля (Хотімлю -> Хотімля)
    if city_lower.endswith('лю') and len(city_lower) > 3:
        return city_norm[:-1] + 'я'
    # -ську -> -ськ (Донецьку -> Донецьк)
    if city_lower.endswith('ську') and len(city_lower) > 4:
        return city_norm[:-1]
    # -івку -> -івка (Костянтинівку -> Костянтинівка)
    if city_lower.endswith('івку') and len(city_lower) > 4:
        return city_norm[:-1] + 'а'
    
    return city_norm


def _normalize_spelling_variants(text: str) -> str:
    """Normalize common spelling variations in Ukrainian"""
    # і/и variants
    text = text.replace('и', 'і')
    # є/е variants (keep є as is, but normalize russian е to ukrainian е)
    # ї/и variants (keep ї)
    # Remove soft/hard sign variations
    text = text.replace('ъ', '')
    # Normalize apostrophes
    text = text.replace('\u02bc', "'").replace('ʼ', "'").replace("'", "'").replace('`', "'")
    text = text.replace('ё', 'е')
    return text


def _normalize_key(city: str, region: str = None) -> str:
    """Create normalized cache key from city and region"""
    if not city:
        return ""
    
    # First normalize accusative case to nominative
    city_normalized = _normalize_city_name(city)
    
    # Then lowercase and clean
    city_norm = city_normalized.lower().strip()
    
    # Normalize spelling variants for better matching
    city_norm = _normalize_spelling_variants(city_norm)
    
    # Normalize region - keep original form, just lowercase
    if region:
        region_norm = region.lower().strip()
        region_norm = _normalize_spelling_variants(region_norm)
        # Only remove "область" and "обл" words, keep regional suffix like "ська"
        region_norm = region_norm.replace(' область', '').replace(' обл.', '').replace(' обл', '')
        region_norm = region_norm.strip()
        if region_norm:
            return f"{city_norm}|{region_norm}"
    
    return city_norm


def _load_cache():
    """Load cache from disk and automatically clean bad entries"""
    global _cache, _negative_cache
    
    # Load positive cache
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                bad_entries = []
                # Handle both formats: {key: [lat, lon]} and {key: {coords: [lat, lon], ...}}
                for k, v in data.items():
                    coords = None
                    if isinstance(v, dict) and 'coords' in v:
                        # New format with metadata
                        coords = v['coords']
                        coords = tuple(coords) if isinstance(coords, list) else coords
                    elif isinstance(v, list):
                        # Simple format [lat, lon]
                        coords = tuple(v)
                    elif isinstance(v, tuple):
                        coords = v
                    
                    # VALIDATION: Skip bad "round" coordinates (region center fallbacks)
                    if coords and len(coords) >= 2:
                        lat, lng = coords[0], coords[1]
                        # Check for round coordinates (region centers)
                        lat_decimal = round(lat % 1, 4)
                        lng_decimal = round(lng % 1, 4)
                        round_values = {0.0, 0.25, 0.5, 0.75}
                        is_round = (lat_decimal in round_values and lng_decimal in round_values) or \
                                   (lat == round(lat, 1) and lng == round(lng, 1))
                        
                        if is_round:
                            bad_entries.append((k, coords))
                            continue  # Skip this bad entry
                    
                    if coords:
                        _cache[k] = coords
                
                # Report cleanup
                if bad_entries:
                    print(f"[OPENCAGE] Cache loaded: {len(_cache)} cities (removed {len(bad_entries)} bad entries on load)", flush=True)
                    for key, coords in bad_entries[:10]:
                        print(f"  - Removed '{key}' -> {coords}", flush=True)
                    if len(bad_entries) > 10:
                        print(f"  ... and {len(bad_entries) - 10} more", flush=True)
                    # Save cleaned cache
                    _save_cache()
                else:
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


def _is_region_center_fallback(lat: float, lng: float) -> bool:
    """
    Detect if coordinates are suspiciously 'round' - likely a region center fallback.
    OpenCage returns these when it can't find the specific settlement.
    Examples: (48.5, 35.0), (50.25, 30.5), (51.0, 34.0)
    """
    # Check if coordinates are "too round" - sign of region center fallback
    lat_decimal = round(lat % 1, 4)
    lng_decimal = round(lng % 1, 4)
    
    # Round values that indicate region centers
    round_values = {0.0, 0.25, 0.5, 0.75}
    
    # Both coordinates being round is very suspicious
    is_lat_round = lat_decimal in round_values
    is_lng_round = lng_decimal in round_values
    
    if is_lat_round and is_lng_round:
        return True
    
    # Also check for 1 decimal place coordinates (e.g., 48.5, 35.0)
    if lat == round(lat, 1) and lng == round(lng, 1):
        return True
    
    return False


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings (for fuzzy matching)"""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def _fuzzy_match_score(name1: str, name2: str) -> float:
    """
    Calculate fuzzy match score (0-1, higher is better).
    Uses Levenshtein distance normalized by string length.
    """
    if not name1 or not name2:
        return 0.0
    
    name1_lower = name1.lower().strip()
    name2_lower = name2.lower().strip()
    
    # Exact match
    if name1_lower == name2_lower:
        return 1.0
    
    # Substring match
    if name1_lower in name2_lower or name2_lower in name1_lower:
        return 0.9
    
    # Levenshtein distance
    max_len = max(len(name1_lower), len(name2_lower))
    if max_len == 0:
        return 0.0
    
    distance = _levenshtein_distance(name1_lower, name2_lower)
    similarity = 1.0 - (distance / max_len)
    
    return max(0.0, similarity)


def _is_valid_settlement_result(result: dict, city: str, region: str = None) -> tuple:
    """
    Validate that OpenCage result is actually a settlement, not a region-level fallback.
    
    STRICT VALIDATION: Better to return None than show wrong location!
    
    Returns: (is_valid: bool, reason: str, lat: float, lng: float, confidence: int)
    """
    components = result.get('components', {})
    geometry = result.get('geometry', {})
    confidence = result.get('confidence', 0)
    formatted = result.get('formatted', '')
    
    lat = geometry.get('lat')
    lng = geometry.get('lng')
    
    if not lat or not lng:
        return (False, "no coordinates", None, None, 0)
    
    # STRICT: Minimum confidence threshold
    MIN_CONFIDENCE = 5  # Confidence 1-10, below 5 is too unreliable
    if confidence < MIN_CONFIDENCE:
        return (False, f"confidence too low ({confidence} < {MIN_CONFIDENCE})", lat, lng, confidence)
    
    # Must be in Ukraine
    country_code = components.get('country_code', '').lower()
    if country_code != 'ua':
        return (False, f"not in Ukraine (country={country_code})", lat, lng, confidence)
    
    # Check result type - reject region-level results
    result_type = components.get('_type', '')
    
    # These types are NOT settlements
    region_level_types = {'state', 'state_district', 'county', 'region', 'province'}
    if result_type in region_level_types:
        return (False, f"region-level type: {result_type}", lat, lng, confidence)
    
    # Check for settlement indicators in components
    settlement_keys = [
        'city', 'town', 'village', 'hamlet', 'suburb', 
        'neighbourhood', 'locality', 'municipality', 
        'city_district', 'quarter', 'residential'
    ]
    has_settlement = any(components.get(key) for key in settlement_keys)
    
    # Settlement-type results
    settlement_types = {
        'city', 'town', 'village', 'hamlet', 'suburb', 
        'neighbourhood', 'locality', 'municipality',
        'residential', 'quarter', 'city_district'
    }
    is_settlement_type = result_type in settlement_types
    
    # Verify the returned name matches what we're looking for
    returned_name = (components.get('city') or 
                     components.get('town') or 
                     components.get('village') or 
                     components.get('hamlet') or
                     components.get('locality', '')).lower()
    
    city_normalized = _normalize_city_name(city).lower()
    
    # Use fuzzy matching for better name validation
    fuzzy_score = _fuzzy_match_score(city_normalized, returned_name) if returned_name else 0.0
    name_matches = fuzzy_score >= 0.7  # 70% similarity threshold
    
    # LOW confidence + NO settlement indicators = definitely a fallback
    if confidence <= 4 and not has_settlement and not is_settlement_type:
        return (False, f"low confidence ({confidence}) + no settlement indicators", lat, lng, confidence)
    
    # Check for suspiciously round coordinates (region center fallback)
    if _is_region_center_fallback(lat, lng):
        # Only reject if we also have low confidence or no settlement type
        if confidence <= 6 or not is_settlement_type:
            return (False, f"round coordinates ({lat:.2f}, {lng:.2f}) - likely region center", lat, lng, confidence)
    
    # If we have high confidence but name doesn't match well - might be wrong city
    if confidence >= 7 and returned_name and fuzzy_score < 0.6:
        # Log warning but don't reject if other indicators are strong
        print(f"[OPENCAGE] Warning: name mismatch (fuzzy={fuzzy_score:.2f}): '{city}' vs '{returned_name}'", flush=True)
        # Reject if very low similarity and not high confidence
        if confidence < 8 and fuzzy_score < 0.4:
            return (False, f"poor name match (fuzzy={fuzzy_score:.2f}): '{city}' vs '{returned_name}'", lat, lng, confidence)
    
    # If region specified, check coordinates are in that region
    if region and not _coords_in_oblast(lat, lng, region):
        return (False, f"outside {region} bounds", lat, lng, confidence)
    
    # Check if result is in a conflict zone or annexed territory (Crimea, occupied Donbas)
    # Crimea: lat 44-46, lng 33-36.5
    if 44.0 <= lat <= 46.0 and 33.0 <= lng <= 36.5:
        state_district = components.get('state_district', '').lower()
        if 'крим' in state_district or 'crimea' in state_district:
            # Crimea - still valid but lower confidence
            pass
    
    return (True, f"valid settlement (type={result_type}, conf={confidence})", lat, lng, confidence)


def _call_api(city: str, region: str = None) -> tuple:
    """Make actual API call to OpenCage. Returns (lat, lon) or None."""
    
    # Check rate limit
    if not _check_rate_limit():
        print(f"[OPENCAGE] Rate limit exceeded, skipping API call for '{city}'", flush=True)
        return None
    
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
            'limit': 10,  # Get more results to find valid settlement
            'no_annotations': 0,  # We need annotations for better filtering
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
        
        # Evaluate each result and find best valid settlement
        best_match = None
        best_score = 0
        best_info = None
        rejection_reasons = []
        
        for i, r in enumerate(results):
            is_valid, reason, lat, lng, conf = _is_valid_settlement_result(r, city, region)
            
            if not is_valid:
                rejection_reasons.append(f"Result #{i+1}: {reason} ({lat:.2f}, {lng:.2f} conf={conf})" if lat else f"Result #{i+1}: {reason}")
                continue
            
            # Score result based on confidence and name match
            components = r.get('components', {})
            returned_name = (components.get('city') or 
                            components.get('town') or 
                            components.get('village') or 
                            components.get('hamlet') or
                            components.get('locality', '')).lower()
            
            city_normalized = _normalize_city_name(city).lower()
            
            # Calculate fuzzy match score
            fuzzy_score = _fuzzy_match_score(city_normalized, returned_name) if returned_name else 0.0
            
            # Combined score: confidence + fuzzy match bonus
            score = conf
            if returned_name:
                if fuzzy_score >= 0.95:  # Near exact match
                    score += 5
                elif fuzzy_score >= 0.85:  # Very close match
                    score += 3
                elif fuzzy_score >= 0.70:  # Good match
                    score += 1.5
                elif fuzzy_score >= 0.50:  # Acceptable match
                    score += 0.5
                # Below 0.5 similarity - no bonus or penalty
            
            # Region match bonus
            if region:
                result_state = components.get('state', '').lower()
                result_district = components.get('state_district', '').lower()
                region_lower = region.lower()
                if region_lower in result_state or region_lower in result_district:
                    score += 2  # Bonus for matching region
            
            # Take best scored match
            if best_match is None or score > best_score:
                best_match = (lat, lng)
                best_score = score
                best_info = {
                    'name': returned_name,
                    'formatted': r.get('formatted', ''),
                    'confidence': conf,
                    'fuzzy': fuzzy_score,
                    'score': score
                }
        
        if best_match:
            print(f"[OPENCAGE] Found valid settlement: {best_match} ({best_info['name']}) score={best_info['score']:.1f} (conf={best_info['confidence']}, fuzzy={best_info['fuzzy']:.2f}) in {region or 'Ukraine'}", flush=True)
            return best_match
        
        # Log why all results were rejected
        if rejection_reasons:
            print(f"[OPENCAGE] All {len(results)} results rejected for '{city}' ({region or 'any'}):", flush=True)
            for reason in rejection_reasons[:5]:  # Show first 5 reasons
                print(f"  - {reason}", flush=True)
        else:
            print(f"[OPENCAGE] No valid results found in {region or 'any region'} for '{city}'", flush=True)
        
        return None
        
    except Exception as e:
        print(f"[OPENCAGE] API exception: {e}", flush=True)
        return None


def geocode_batch(cities: list, region: str = None) -> dict:
    """
    Geocode multiple cities at once for better efficiency.
    Returns dict: {city: (lat, lon) or None}
    """
    results = {}
    uncached = []
    
    # Check cache first for all cities
    for city in cities:
        cache_key = _normalize_key(city, region)
        if not cache_key:
            results[city] = None
            continue
        
        # Check hardcoded
        if cache_key in HARDCODED_COORDS:
            results[city] = HARDCODED_COORDS[cache_key]
            continue
        
        # Check positive cache
        if cache_key in _cache:
            results[city] = _cache[cache_key]
            _stats['hits'] += 1
            continue
        
        # Check negative cache
        if cache_key in _negative_cache:
            results[city] = None
            _stats['hits'] += 1
            continue
        
        uncached.append(city)
    
    # Geocode uncached cities
    for city in uncached:
        results[city] = geocode(city, region)
    
    return results


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
    
    # === STEP 0: Check hardcoded coordinates (for ambiguous cities) ===
    if cache_key in HARDCODED_COORDS:
        print(f"[OPENCAGE] Using hardcoded coords for '{cache_key}': {HARDCODED_COORDS[cache_key]}", flush=True)
        return HARDCODED_COORDS[cache_key]
    
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
    
    # === STEP 4: If no result, try alternative queries ===
    if not result:
        # Try without region if region was specified (last resort)
        if region:
            print(f"[OPENCAGE] No result with region, trying without region context...", flush=True)
            alt_cache_key = _normalize_key(city, None)
            if alt_cache_key != cache_key and alt_cache_key not in _negative_cache:
                result = _call_api(city, None)
                if result:
                    # Verify it's in the right region if region was specified
                    if _coords_in_oblast(result[0], result[1], region):
                        print(f"[OPENCAGE] Alternative query successful and in correct region", flush=True)
                    else:
                        print(f"[OPENCAGE] Alternative query found result but outside {region}, rejecting", flush=True)
                        result = None
    
    # === STEP 5: Cache result ===
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


def cleanup_bad_cache_entries() -> dict:
    """
    Remove bad cache entries with round coordinates (region center fallbacks).
    Call this once to clean up existing cache.
    Returns: dict with cleanup stats
    """
    global _cache, _negative_cache
    
    removed = []
    kept = []
    
    for key, coords in list(_cache.items()):
        if coords and len(coords) >= 2:
            lat, lng = coords[0], coords[1]
            if _is_region_center_fallback(lat, lng):
                removed.append((key, coords))
                del _cache[key]
            else:
                kept.append(key)
    
    if removed:
        _save_cache()
        print(f"[OPENCAGE] Cache cleanup: removed {len(removed)} bad entries:", flush=True)
        for key, coords in removed[:20]:  # Show first 20
            print(f"  - '{key}' -> {coords}", flush=True)
        if len(removed) > 20:
            print(f"  ... and {len(removed) - 20} more", flush=True)
    
    return {
        'removed_count': len(removed),
        'kept_count': len(kept),
        'removed_entries': removed
    }


def invalidate_cache_entry(city: str, region: str = None) -> bool:
    """
    Remove a specific entry from cache (both positive and negative).
    Useful for fixing incorrect geocoding results.
    """
    global _cache, _negative_cache
    
    cache_key = _normalize_key(city, region)
    removed = False
    
    if cache_key in _cache:
        del _cache[cache_key]
        _save_cache()
        removed = True
        print(f"[OPENCAGE] Invalidated cache entry: '{cache_key}'", flush=True)
    
    if cache_key in _negative_cache:
        _negative_cache.discard(cache_key)
        _save_negative_cache()
        removed = True
        print(f"[OPENCAGE] Invalidated negative cache entry: '{cache_key}'", flush=True)
    
    return removed


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
