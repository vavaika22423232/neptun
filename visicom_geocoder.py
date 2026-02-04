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


def _normalize_single_word(word: str) -> list:
    """Normalize a single Ukrainian word to nominative form."""
    variants = [word]
    
    # Feminine adjectives: -ої -> -а (Білої -> Біла)
    if word.endswith('ої'):
        variants.append(word[:-2] + 'а')
    if word.endswith('ої'):
        variants.append(word[:-2] + 'ий')  # masculine
    
    # Feminine nouns: -и -> -а (Церкви -> Церква)
    if word.endswith('и'):
        variants.append(word[:-1] + 'а')
        variants.append(word[:-1] + 'я')
    if word.endswith('і'):
        variants.append(word[:-1] + 'а')
        variants.append(word[:-1] + 'я')
        variants.append(word[:-1] + 'ь')
    
    # Masculine: -а/-я ending (genitive)
    if word.endswith('а') and len(word) > 2:
        variants.append(word[:-1])
    if word.endswith('я') and len(word) > 2:
        variants.append(word[:-1] + 'ь')
        variants.append(word[:-1])
    
    # -ого/-ому -> -е/-ий (adjectives)
    if word.endswith('ого'):
        variants.append(word[:-3] + 'е')
        variants.append(word[:-3] + 'ий')
    if word.endswith('ому'):
        variants.append(word[:-3] + 'е')
        variants.append(word[:-3] + 'ий')
    
    return variants


# Special name mappings that can't be handled by generic rules
# Format: 'incorrect_form': 'correct_form'
SPECIAL_NAME_MAPPINGS = {
    # Genitive singular to plural nominative
    "близнюка": "Близнюки",
    "п'ятихатка": "П'ятихатки",
    "глухи": "Глухів",  # Might be Глухів in Sumy oblast
    # Genitive forms
    "поблизу світлогірське": "Світлогірське",
    "поблизу": "",  # Remove prefix
}


def _normalize_ukrainian_name(name: str) -> list:
    """
    Normalize Ukrainian place name from any grammatical case to nominative.
    Returns list of possible nominative forms to try.
    
    Ukrainian cases:
    - Називний (Nominative): Затока, Харків, Покровське
    - Родовий (Genitive): Затоки, Харкова, Покровського  
    - Давальний (Dative): Затоці, Харкову, Покровському
    - Знахідний (Accusative): Затоку, Харків, Покровське
    - Орудний (Instrumental): Затокою, Харковом, Покровським
    - Місцевий (Locative): Затоці, Харкові, Покровському/Покровськім
    """
    if not name:
        return [name]
    
    original = name.strip()
    
    # Check special mappings first
    name_lower = original.lower()
    if name_lower in SPECIAL_NAME_MAPPINGS:
        mapped = SPECIAL_NAME_MAPPINGS[name_lower]
        if mapped:
            return [mapped, original]  # Try mapped first, then original
        else:
            return [original]
    
    # Handle "Поблизу X" pattern
    if name_lower.startswith('поблизу '):
        cleaned = original[8:].strip()
        return _normalize_ukrainian_name(cleaned)
    
    variants = [original]
    
    # Special: singular -а ending that should be plural -и (П'ятихатка -> П'ятихатки)
    if original.endswith('ка') and len(original) > 4:
        variants.append(original[:-1] + 'и')  # П'ятихатка -> П'ятихатки
    
    # Feminine nouns ending in -а/-я (Затока, Одеса, Березанка)
    # Genitive: -и/-і (Затоки, Одеси)
    if original.endswith('и'):
        variants.append(original[:-1] + 'а')  # Затоки -> Затока
        variants.append(original[:-1] + 'я')  # Чернігови -> Чернігов'я (rare)
    if original.endswith('і'):
        variants.append(original[:-1] + 'а')  # Березанкі -> Березанка
        variants.append(original[:-1] + 'я')  # Одесі -> Одеся (wrong but try)
    
    # Dative/Locative: -і/-ці (Затоці, Одесі)
    if original.endswith('ці'):
        variants.append(original[:-2] + 'ка')  # Затоці -> Затока
        variants.append(original[:-2] + 'ця')  # Вінниці -> Вінниця
    if original.endswith('сі'):
        variants.append(original[:-2] + 'са')  # Одесі -> Одеса
    if original.endswith('зі'):
        variants.append(original[:-2] + 'за')  # Березі -> Береза
        variants.append(original[:-2] + 'га')  # soft g
    
    # Accusative: -у/-ю (Затоку, Одесу)
    if original.endswith('у') and len(original) > 3:
        variants.append(original[:-1] + 'а')  # Затоку -> Затока
        variants.append(original[:-1] + 'о')  # Дніпру -> Дніпро
    if original.endswith('ю'):
        variants.append(original[:-1] + 'я')  # Вінницю -> Вінниця
        variants.append(original[:-1] + 'а')
    
    # Instrumental: -ою/-ею/-єю (Затокою, Одесою)
    if original.endswith('ою'):
        variants.append(original[:-2] + 'а')  # Затокою -> Затока
    if original.endswith('ею') or original.endswith('єю'):
        variants.append(original[:-2] + 'я')  # Вінницею -> Вінниця
        variants.append(original[:-2] + 'е')  # Рівнею -> Рівне
    
    # Masculine nouns (Харків, Київ, Львів)
    # Genitive: -а/-я (Харкова, Києва)
    if original.endswith('ова'):
        variants.append(original[:-3] + 'ів')  # Харкова -> Харків
        variants.append(original[:-3] + 'ов')  # Харкова -> Харков
    if original.endswith('ева') or original.endswith('єва'):
        variants.append(original[:-3] + 'ів')  # Києва -> Київ
        variants.append(original[:-3] + 'їв')
    if original.endswith('ська'):
        variants.append(original[:-1])  # keep as adjective
    
    # Dative: -у/-ові/-еві (Харкову, Києву, Харкові)
    if original.endswith('ові'):
        variants.append(original[:-3] + 'ів')  # Харкові -> Харків
        variants.append(original[:-3])  # Львові -> Львов (try)
    if original.endswith('еві'):
        variants.append(original[:-3] + 'ів')  # Києві -> Київ
    
    # Instrumental: -ом/-ем (Харковом, Києвом)
    if original.endswith('ом') and len(original) > 4:
        variants.append(original[:-2] + 'ів')  # Харковом -> Харків
        variants.append(original[:-2])  # Миколаєвом -> Миколаєв
    if original.endswith('ем'):
        variants.append(original[:-2] + 'ів')
        variants.append(original[:-2] + 'е')  # Рівнем -> Рівне
    
    # Locative: -і/-ові (Харкові, Києві)  
    if original.endswith('ві') and len(original) > 3:
        variants.append(original[:-2] + 'в')  # Києві -> Київ
        variants.append(original[:-2] + 'ів')  # alternative
    
    # Neuter nouns ending in -е/-о (Покровське, Дніпро)
    # Genitive: -ого/-ього (Покровського)
    if original.endswith('ого'):
        variants.append(original[:-3] + 'е')  # Покровського -> Покровське
        variants.append(original[:-3] + 'ий')  # adjective form
    if original.endswith('ього'):
        variants.append(original[:-4] + 'е')
        variants.append(original[:-4] + 'є')
    
    # Dative/Locative: -ому/-ьому (Покровському)
    if original.endswith('ому'):
        variants.append(original[:-3] + 'е')  # Покровському -> Покровське
        variants.append(original[:-3] + 'о')  # Дніпрому -> Дніпро
        variants.append(original[:-3] + 'ий')
    if original.endswith('ьому'):
        variants.append(original[:-4] + 'е')
        variants.append(original[:-4] + 'є')
    
    # Instrumental: -им/-ім (Покровським)
    if original.endswith('им'):
        variants.append(original[:-2] + 'е')  # Покровським -> Покровське
        variants.append(original[:-2] + 'ий')
    if original.endswith('ім'):
        variants.append(original[:-2] + 'е')
        variants.append(original[:-2] + 'ій')
    
    # Plural forms (Суми, Черкаси, Чернівці)
    # Genitive plural: (Сум, Черкас, Чернівців)
    if original.endswith('ів'):
        variants.append(original[:-2] + 'і')  # Чернівців -> Чернівці
        variants.append(original[:-2] + 'и')  # alternative
    if original.endswith('ей'):
        variants.append(original[:-2] + 'і')
        variants.append(original[:-2] + 'ї')
    
    # Dative plural: -ам/-ям (Сумам, Черкасам)
    if original.endswith('ам'):
        variants.append(original[:-2] + 'и')  # Сумам -> Суми
        variants.append(original[:-2] + 'і')  # Черкасам -> Черкаси
    if original.endswith('ям'):
        variants.append(original[:-2] + 'і')
        variants.append(original[:-2] + 'ї')
    
    # Instrumental plural: -ами/-ями (Сумами, Черкасами)
    if original.endswith('ами'):
        variants.append(original[:-3] + 'и')  # Сумами -> Суми
        variants.append(original[:-3] + 'і')
    if original.endswith('ями'):
        variants.append(original[:-3] + 'і')
        variants.append(original[:-3] + 'ї')
    
    # Locative plural: -ах/-ях (Сумах, Черкасах)
    if original.endswith('ах'):
        variants.append(original[:-2] + 'и')  # Сумах -> Суми
        variants.append(original[:-2] + 'і')  # Черкасах -> Черкаси
    if original.endswith('ях'):
        variants.append(original[:-2] + 'і')
        variants.append(original[:-2] + 'ї')
    
    # Adjective-like endings (Тендрівської, Кінбурнської)
    if original.endswith('ої'):
        variants.append(original[:-2] + 'а')  # Тендрівської -> Тендрівська
        variants.append(original[:-2] + 'ий')  # masculine
    if original.endswith('ій'):
        variants.append(original[:-2] + 'а')
        variants.append(original[:-2] + 'ий')
    
    # Special case: words ending in soft sign
    if original.endswith('і') and len(original) > 2:
        base = original[:-1]
        variants.append(base + 'ь')  # Харкові -> Харків (try soft sign)
    
    # Masculine genitive: -а/-я (Кременчука -> Кременчук, Ірпеня -> Ірпінь)
    if original.endswith('а') and len(original) > 3 and not original.endswith('ова'):
        variants.append(original[:-1])  # Кременчука -> Кременчук
        variants.append(original[:-1] + 'ь')  # Маріупола -> Маріуполь (rare)
    if original.endswith('я') and len(original) > 3:
        variants.append(original[:-1] + 'ь')  # Ірпеня -> Ірпінь
        variants.append(original[:-1])  # Маріуполя -> Маріупол
        # Special: ня -> нь (Ірпеня -> Ірпінь with vowel change)
        if original.endswith('еня'):
            variants.append(original[:-3] + 'інь')  # Ірпеня -> Ірпінь
        if original.endswith('оля'):
            variants.append(original[:-1] + 'ь')  # Маріуполя -> Маріуполь
            variants.append(original[:-2] + 'ль')  # Нікополя -> Нікополь
    
    # Instrumental: -ям (Запоріжжям -> Запоріжжя)
    if original.endswith('ям'):
        variants.append(original[:-1])  # Запоріжжям -> Запоріжжя
        variants.append(original[:-2] + 'я')  # Запоріжжям -> Запоріжжя
        variants.append(original[:-2] + 'е')  # try -е ending
    
    # Compound names: normalize each word (Білої Церкви -> Біла Церква)
    if ' ' in original:
        words = original.split()
        if len(words) >= 2:
            # Try normalizing each word separately
            first_variants = _normalize_single_word(words[0])
            second_variants = _normalize_single_word(words[1])
            for fv in first_variants[:3]:  # limit combinations
                for sv in second_variants[:3]:
                    compound = f"{fv} {sv}"
                    if compound != original:
                        variants.append(compound)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for v in variants:
        if v.lower() not in seen:
            seen.add(v.lower())
            unique_variants.append(v)
    
    return unique_variants


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
    
    # Normalize apostrophes: ʼ (U+02BC), ʻ (U+02BB), ` (backtick), ' (curly) -> ' (standard)
    city = city.replace('\u02bc', "'").replace('\u02bb', "'").replace('`', "'").replace(''', "'").replace(''', "'")
    
    city_lower = city.lower().strip()
    
    # Skip garbage words (verbs, directions, etc.) - these are not locations
    SKIP_WORDS = {
        'летить', 'летит', 'летять', 'летят', 'летів', 'летіла',
        'рухається', 'рухаються', 'рух', 'курс',
        'напрямок', 'напрямку', 'напрям',
        'північ', 'південь', 'схід', 'захід',
        'швидкість', 'висота',
    }
    if city_lower in SKIP_WORDS:
        print(f"[VISICOM] Skipping garbage word: '{city}'", flush=True)
        return None
    
    # Special locations (sea, coasts, etc.) - not in regular API
    # Тендрівська коса - sandbar in Black Sea (Kherson region)
    if 'тендр' in city_lower and ('кос' in city_lower or 'коси' in city_lower):
        print(f"[VISICOM] Special: Тендрівська коса at (46.3, 31.5)", flush=True)
        return (46.3, 31.5)
    
    # Кінбурнська коса
    if 'кінбурн' in city_lower:
        print(f"[VISICOM] Special: Кінбурнська коса at (46.5, 31.5)", flush=True)
        return (46.5, 31.5)
    
    # Must be exact "чорне море" or "чорному морі", not "чорноморськ"
    if ('чорне мор' in city_lower or 'чорному мор' in city_lower or 'чорним мор' in city_lower):
        print(f"[VISICOM] Special: Чорне море at (44.5, 31.5)", flush=True)
        return (44.5, 31.5)  # Black Sea coordinates
    
    if ('азовське мор' in city_lower or 'азовському мор' in city_lower or 'азовським мор' in city_lower):
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
    
    # Get all possible name variations (nominative case forms)
    name_variants = _normalize_ukrainian_name(city)
    
    # Build query list - try all normalized variants
    queries_to_try = []
    for variant in name_variants:
        queries_to_try.append(variant)
    
    # Also add variants with region
    if region:
        region_clean = region.replace(' обл.', '').replace(' область', '').strip()
        for variant in name_variants[:3]:  # Top 3 variants with region
            queries_to_try.append(f"{variant}, {region_clean}")
    
    # Remove duplicates
    queries_to_try = list(dict.fromkeys(queries_to_try))
    
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
                
                # Prefer settlements, but accept any feature with coordinates
                settlement_features = [
                    f for f in features 
                    if f.get('properties', {}).get('categories') == 'adm_settlement'
                ]
                
                # If no settlements, use all features (districts, POIs, etc.)
                features_to_check = settlement_features if settlement_features else features
                
                if features_to_check:
                    best_match = None
                    
                    # If we have region, ONLY accept features from that region
                    if target_region_key:
                        for feature in features_to_check:
                            if _feature_matches_region(feature, target_region_key):
                                best_match = feature
                                break
                        
                        # If region specified but no match found - DON'T use wrong region, try next query
                        if not best_match:
                            print(f"[VISICOM] No match for '{query}' in region '{target_region_key}', trying next...", flush=True)
                            continue
                    else:
                        # No region filter - take first settlement
                        if settlement_features:
                            best_match = settlement_features[0]
                        elif features_to_check:
                            best_match = features_to_check[0]
                    
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
        
        # Not found - don't show marker
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
