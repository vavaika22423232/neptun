# Geocoding module - Ukrainian settlement geocoding with multiple providers
# Extracted from app.py for better code organization

import os
import re
import json
import time
import logging
from functools import lru_cache

from flask import Blueprint

log = logging.getLogger(__name__)

# Create blueprint (currently no routes, used for shared geocoding functions)
geocoding_bp = Blueprint('geocoding', __name__)

# =============================================================================
# GEOCODING CONFIGURATION
# =============================================================================
OPENCAGE_CACHE_FILE = 'opencage_cache.json'
NEG_GEOCODE_FILE = 'neg_geocode_cache.json'
NEG_GEOCODE_TTL = 86400 * 7  # 7 days

# Groq AI integration
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_ENABLED = bool(GROQ_API_KEY)
groq_client = None

if GROQ_ENABLED:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("INFO: Groq AI initialized successfully")
    except ImportError:
        GROQ_ENABLED = False
        print("WARNING: Groq library not installed")
    except Exception as e:
        GROQ_ENABLED = False
        print(f"WARNING: Groq initialization failed: {e}")

# SpaCy integration (disabled by default for memory savings)
SPACY_AVAILABLE = False
nlp = None

# Nominatim geocoder
try:
    from nominatim_geocoder import get_coordinates_nominatim
    NOMINATIM_AVAILABLE = True
except ImportError:
    NOMINATIM_AVAILABLE = False
    def get_coordinates_nominatim(city_name, region=None):
        return None

# =============================================================================
# CITY NORMALIZATION DICTIONARIES
# =============================================================================
UA_CITIES = [
    'київ','харків','одеса','одесса','дніпро','дніпропетровськ','львів','запоріжжя','запорожье','вінниця','миколаїв','николаев',
    'маріуполь','полтава','чернігів','чернигов','черкаси','житомир','суми','хмельницький','чернівці','рівне','івано-франківськ',
    'луцьк','тернопіль','ужгород','кропивницький','кіровоград','кременчук','краматорськ','біла церква','мелітополь','бердянськ',
    'павлоград','ніжин','шостка','короп','кролевець'
]

UA_CITY_NORMALIZE = {
    'одесса':'одеса','запорожье':'запоріжжя','запоріжжі':'запоріжжя','дніпропетровськ':'дніпро',
    'кировоград':'кропивницький','кіровоград':'кропивницький','николаев':'миколаїв','чернигов':'чернігів',
    # Accusative / variant forms
    'липову долину':'липова долина','липову долина':'липова долина',
    'великий багачку':'велика багачка','велику багачу':'велика багачка','велику багачку':'велика багачка',
    'улянівку':'улянівка','уляновку':'улянівка',
    # Велика Димерка падежные формы
    'велику димерку':'велика димерка','велика димерку':'велика димерка','великої димерки':'велика димерка',
    # Велика Виска падежные формы  
    'велику виску':'велика виска','великої виски':'велика виска','великій висці':'велика виска',
    # Мала дівиця
    'малу дівицю':'мала дівиця','мала дівицю':'мала дівиця',
    # Additional safety normalizations
    'олишівку':'олишівка','згурівку':'згурівка','ставищею':'ставище','кегичівку':'кегичівка',
    # Voznesensk variants
    'вознесенська':'вознесенськ',
    # Mykolaiv variants  
    'миколаєва':'миколаїв',
    'корабел':'корабельний район херсон',
    'корабельний':'корабельний район херсон',
    # Novoukrainka variants
    'новоукраїнку':'новоукраїнка',
    'старому салтову':'старий салтів','старому салтові':'старий салтів','карлівку':'карлівка',
    'балаклію':'балаклія','білу церкву':'біла церква','баришівку':'баришівка','сквиру':'сквира',
    'шостку':'шостка','березну':'березна','зачепилівку':'зачепилівка','нову водолагу':'нова водолага',
    'убни':'лубни','олми':'холми','летичів':'летичів','деражню':'деражня',
    'корюківку':'корюківка','борзну':'борзна','жмеринку':'жмеринка','лосинівку':'лосинівка',
    'ніжину':'ніжин','ніжина':'ніжин','межову':'межова','святогірську':'святогірськ',
    # Extended city normalizations
    'городню':'городня','городні':'городня','городне':'городня',
    'кролевця':'кролевець','кролевцу':'кролевець','кролевце':'кролевець',
    'дубовʼязівку':'дубовʼязівка','дубовязівку':'дубовʼязівка',
    'батурина':'батурин','батурині':'батурин','батурином':'батурин',
    'бердичев':'бердичів','бердичева':'бердичів','бердичеве':'бердичів',
    'гостомеля':'гостомель','гостомелю':'гостомель','гостомелі':'гостомель',
    'боярки':'боярка','боярку':'боярка','боярці':'боярка',
    'седнів':'седнів','седніву':'седнів','седніва':'седнів',
    'макарова':'макарів','макарові':'макарів','макаров':'макарів',
    'бородянки':'бородянка','бородянку':'бородянка','бородянці':'бородянка',
    'кілії':'кілія','кілію':'кілія','кілією':'кілія',
    'куцуруба':'куцуруб','воскресенку':'воскресенка','воскресенки':'воскресенка',
    # Цибулів (Черкаська обл.) падежные формы
    'цибулева':'цибулів','цибулеві':'цибулів','цибулеву':'цибулів',
    # UAV course parsing batch
    'борзну':'борзна','царичанку':'царичанка','андріївку':'андріївка',
    'ямполь':'ямпіль','ямполя':'ямпіль','ямпіль':'ямпіль','димеру':'димер','чорнобилю':'чорнобиль',
    'дмитрівку':'дмитрівка','семенівку':'семенівка','глобине':'глобине','глобину':'глобине',
    'кринички':'кринички','криничок':'кринички','солоне':'солоне',
    'краснопалівку':'краснопавлівка','краснопалівка':'краснопавлівка',
    'брусилів':'брусилів','брусилова':'брусилів','брусилові':'брусилів',
    # September 2025 messages
    'десну':'десна','кіпті':'кіпті','ічню':'ічня','цвіткове':'цвіткове',
    'чоповичі':'чоповичі','звягель':'звягель','сахновщину':'сахновщина',
    'камʼянське':'камʼянське','піщаний брід':'піщаний брід','бобринець':'бобринець',
    'тендрівську косу':'тендрівська коса',
    # Одеська область
    'вилково':'вилкове','вилкову':'вилкове',
    # Common accusative forms
    'одесу':'одеса','полтаву':'полтава','сумами':'суми','суму':'суми',
    # Donetsk front
    "словянськ": "слов'янськ",
    'лиман': 'ліман',
}

# =============================================================================
# OBLAST CENTERS (for fallback geocoding)
# =============================================================================
OBLAST_CENTERS = {
    'київська обл.': (50.4501, 30.5234),
    'харківська обл.': (49.9935, 36.2304),
    'одеська обл.': (46.4825, 30.7233),
    'дніпропетровська область': (48.4647, 35.0462),
    'львівська область': (49.8397, 24.0297),
    'запорізька область': (47.8388, 35.1396),
    'вінницька область': (49.2331, 28.4682),
    'миколаївська обл.': (46.9750, 31.9946),
    'полтавська область': (49.5883, 34.5514),
    'чернігівська обл.': (51.4982, 31.2893),
    'черкаська область': (49.4444, 32.0598),
    'житомирська область': (50.2547, 28.6587),
    'сумська область': (50.9077, 34.7981),
    'хмельницька область': (49.4229, 26.9871),
    'чернівецька область': (48.2921, 25.9358),
    'рівненська область': (50.6199, 26.2516),
    'волинська область': (50.7472, 25.3254),
    'тернопільська область': (49.5535, 25.5948),
    'івано-франківська область': (48.9226, 24.7111),
    'закарпатська область': (48.6208, 22.2879),
    'кіровоградська область': (48.5079, 32.2623),
    'херсонська обл.': (46.6354, 32.6169),
    'донецька область': (48.0159, 37.8029),
    'луганська область': (48.5740, 39.3078),
}

# =============================================================================
# CITY COORDINATES DATABASE (Legacy - now primarily using APIs)
# =============================================================================
CITY_COORDS = {
    # Core cities
    'київ': (50.4501, 30.5234), 'харків': (49.9935, 36.2304), 'одеса': (46.4825, 30.7233),
    'дніпро': (48.4647, 35.0462), 'львів': (49.8397, 24.0297), 'запоріжжя': (47.8388, 35.1396),
    'вінниця': (49.2331, 28.4682), 'миколаїв': (46.9750, 31.9946), 'маріуполь': (47.0971, 37.5434),
    'полтава': (49.5883, 34.5514), 'чернігів': (51.4982, 31.2893), 'черкаси': (49.4444, 32.0598),
    'житомир': (50.2547, 28.6587), 'суми': (50.9077, 34.7981), 'хмельницький': (49.4229, 26.9871),
    'чернівці': (48.2921, 25.9358), 'рівне': (50.6199, 26.2516), 'кропивницький': (48.5079, 32.2623),
    'кременчук': (49.0659, 33.4199), 'краматорськ': (48.7287, 37.5558), 'біла церква': (49.7939, 30.1014),
    # Житомирська область
    'овруч': (51.3244, 28.8006), 'коростень': (50.9550, 28.6336), 'бердичів': (49.8978, 28.6011),
    'звягель': (50.5833, 27.6167), 'малин': (50.7726, 29.2360), 'радомишль': (50.4972, 29.2292),
    'баранівка': (50.3000, 27.6667), 'попільня': (49.9333, 28.4167), 'олевськ': (51.2167, 27.6667),
    'коростишів': (50.3167, 29.0333), 'чорнобиль': (51.2768, 30.2219),
}

# Dnipro region specific coords for disambiguation
DNIPRO_CITY_COORDS = {
    'зарічне дніпропетровська': (48.7833, 34.0333),
}

# =============================================================================
# NAME-REGION MAPPING
# =============================================================================
NAME_REGION_MAP = {}

def _load_name_region_map():
    """Load settlement-to-region mapping from city_ukraine.json"""
    global NAME_REGION_MAP
    if NAME_REGION_MAP:
        return
    path = 'city_ukraine.json'
    if not os.path.exists(path):
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        added = 0
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get('object_name') or '').strip().lower()
            region = str(item.get('region') or '').strip().title()
            if not name or len(name) < 2:
                continue
            if name in NAME_REGION_MAP:
                continue
            NAME_REGION_MAP[name] = region
            added += 1
        log.info(f"Loaded NAME_REGION_MAP entries: {added}")
    except Exception as e:
        log.warning(f"Failed load city_ukraine.json names: {e}")

# Initialize on module load
_load_name_region_map()

# Remove problematic entries
for entry in ['кривий', 'старий', 'нова', 'велика', 'мала', 'білозерка']:
    NAME_REGION_MAP.pop(entry, None)

# =============================================================================
# GEOCODING CACHE MANAGEMENT
# =============================================================================
_opencage_cache = None
_neg_geocode_cache = None

def _load_opencage_cache():
    global _opencage_cache
    if _opencage_cache is not None:
        return _opencage_cache
    if os.path.exists(OPENCAGE_CACHE_FILE):
        try:
            with open(OPENCAGE_CACHE_FILE, 'r', encoding='utf-8') as f:
                _opencage_cache = json.load(f)
        except Exception:
            _opencage_cache = {}
    else:
        _opencage_cache = {}
    return _opencage_cache

def _save_opencage_cache():
    if _opencage_cache is None:
        return
    try:
        cache_to_save = _opencage_cache
        if len(_opencage_cache) > 1000:
            items = list(_opencage_cache.items())
            cache_to_save = dict(items[-1000:])
        with open(OPENCAGE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f"Failed saving OpenCage cache: {e}")

def _load_neg_geocode_cache():
    global _neg_geocode_cache
    if _neg_geocode_cache is not None:
        return _neg_geocode_cache
    if os.path.exists(NEG_GEOCODE_FILE):
        try:
            with open(NEG_GEOCODE_FILE, 'r', encoding='utf-8') as f:
                _neg_geocode_cache = json.load(f)
        except Exception:
            _neg_geocode_cache = {}
    else:
        _neg_geocode_cache = {}
    return _neg_geocode_cache

def _save_neg_geocode_cache():
    if _neg_geocode_cache is None:
        return
    try:
        cache_to_save = _neg_geocode_cache
        if len(_neg_geocode_cache) > 500:
            items = list(_neg_geocode_cache.items())
            cache_to_save = dict(items[-500:])
        with open(NEG_GEOCODE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f"Failed saving negative geocode cache: {e}")

def neg_geocode_check(name: str) -> bool:
    """Check if name is in negative geocode cache."""
    if not name:
        return False
    cache = _load_neg_geocode_cache()
    key = name.strip().lower()
    entry = cache.get(key)
    if not entry:
        return False
    if int(time.time()) - entry.get('ts', 0) > NEG_GEOCODE_TTL:
        try:
            del cache[key]
            _save_neg_geocode_cache()
        except Exception:
            pass
        return False
    return True

def neg_geocode_add(name: str, reason: str = 'not_found'):
    """Add name to negative geocode cache."""
    if not name:
        return
    cache = _load_neg_geocode_cache()
    key = name.strip().lower()
    cache[key] = {'ts': int(time.time()), 'reason': reason}
    _save_neg_geocode_cache()

# =============================================================================
# COORDINATE VALIDATION
# =============================================================================
def safe_float(value, default=None):
    """Safely convert value to float."""
    if value is None:
        return default
    try:
        result = float(value)
        if result != result or result == float('inf') or result == float('-inf'):
            return default
        return result
    except (ValueError, TypeError):
        return default

def validate_ukraine_coords(lat, lng) -> bool:
    """Validate that coordinates are within Ukraine bounds."""
    if lat is None or lng is None:
        return False
    try:
        lat_f = float(lat)
        lng_f = float(lng)
        # Ukraine bounding box (approximate)
        if not (44.0 <= lat_f <= 52.5):
            return False
        if not (22.0 <= lng_f <= 40.5):
            return False
        return True
    except (ValueError, TypeError):
        return False

# =============================================================================
# GROQ AI LOCATION EXTRACTION
# =============================================================================
def extract_location_with_groq_ai(message_text: str):
    """Use Groq AI to extract location from Ukrainian military message."""
    if not GROQ_ENABLED or not groq_client or not message_text:
        return None
    
    try:
        prompt = f"""Ти експерт з аналізу повідомлень про повітряні тривоги в Україні.

Витягни з повідомлення:
1. Назву населеного пункту (місто/село) - ОБОВ'ЯЗКОВО в називному відмінку
2. Назву району (якщо вказано явно)
3. Назву області

КРИТИЧНО ВАЖЛИВО:
- "курсом на X" - X це МІСТО (city), а НЕ район!
- "в районі X" означає "біля X", а НЕ назву району
- Нормалізуй назви до називного відмінку
- "Дніпропетровщина" → "Дніпропетровська область"

Повідомлення:
{message_text}

Відповідь ТІЛЬКИ у форматі JSON:
{{"city": "назва або null", "district": "назва або null", "oblast": "назва або null", "confidence": 0.95}}"""

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Ти аналізуєш повідомлення про повітряні тривоги. Відповідай ТІЛЬКИ валідним JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300,
            top_p=0.9
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks
        if result_text.startswith('```'):
            result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
            result_text = re.sub(r'\s*```$', '', result_text)
        
        result = json.loads(result_text)
        
        if not isinstance(result, dict):
            return None
        
        city = result.get('city')
        district = result.get('district')
        oblast = result.get('oblast')
        confidence = result.get('confidence', 0.5)
        
        if not city and not oblast:
            return None
        
        # Convert null strings to None
        if city in ['null', 'None', '']:
            city = None
        if district in ['null', 'None', '']:
            district = None
        if oblast in ['null', 'None', '']:
            oblast = None
        
        log.debug(f"Groq AI: city='{city}', district='{district}', oblast='{oblast}', confidence={confidence}")
        
        return {
            'city': city.strip() if city else None,
            'district': district.strip() if district else None,
            'oblast': oblast.strip() if oblast else None,
            'confidence': float(confidence)
        }
        
    except json.JSONDecodeError as e:
        log.warning(f"Groq AI returned invalid JSON: {e}")
        return None
    except Exception as e:
        log.warning(f"Groq AI extraction failed: {e}")
        return None

# =============================================================================
# DISTRICT AND OBLAST CONTEXT EXTRACTION
# =============================================================================
def extract_district_and_oblast_context(message_text: str) -> dict:
    """Extract district and oblast context from message."""
    if not message_text:
        return {'district': None, 'oblast_key': None, 'excluded_oblast': None}
    
    message_lower = message_text.lower()
    result = {'district': None, 'oblast_key': None, 'excluded_oblast': None}
    
    # Extract explicit district mentions
    district_patterns = [
        r'([а-яїієґ]{3,}ськ(?:ий|ому|ого))\s+район',
        r'([а-яїієґ]{3,})\s+район(?:і)?(?:\s|$)',
    ]
    
    for pattern in district_patterns:
        match = re.search(pattern, message_lower)
        if match:
            district = match.group(1).strip()
            skip_words = ['в', 'на', 'за', 'до', 'від', 'при', 'під', 'над', 'між', 'про', 'для']
            if district in skip_words or len(district) < 3:
                continue
            if district.endswith('ому') or district.endswith('ого'):
                district = district[:-3] + 'ий'
            result['district'] = district
            break
    
    # Check for "з [область]" pattern - city is NOT in that oblast
    from_oblast_pattern = r'з\s+([а-яїіє]+щини|[а-яїіє]+ської\s+обл)'
    from_match = re.search(from_oblast_pattern, message_lower)
    if from_match:
        excluded = from_match.group(1).strip()
        result['excluded_oblast'] = excluded
    
    # Look for oblast mention
    oblast_patterns = [
        r'^([а-яїіє]+(?:ч)?чина|[а-яїіє]+щина|волинь):',
        r'([а-яїіє]+ська\s+обл\.?)',
        r'([а-яїіє]+ська\s+область)',
    ]
    
    oblast_normalizations = {
        'харківщина': 'харківська обл.',
        'чернігівщина': 'чернігівська обл.',
        'полтавщина': 'полтавська область',
        'дніпропетровщина': 'дніпропетровська область',
        'сумщина': 'сумська область',
        'миколаївщина': 'миколаївська обл.',
        'одещина': 'одеська обл.',
        'запоріжжя': 'запорізька область',
        'херсонщина': 'херсонська обл.',
        'київщина': 'київська обл.',
        'черкащина': 'черкаська область',
        'вінниччина': 'вінницька область',
        'хмельниччина': 'хмельницька область',
        'тернопільщина': 'тернопільська область',
        'житомирщина': 'житомирська область',
        'волинь': 'волинська область',
        'донеччина': 'донецька область',
        'луганщина': 'луганська область',
    }
    
    for pattern in oblast_patterns:
        match = re.search(pattern, message_lower, re.MULTILINE)
        if match:
            oblast_mention = match.group(1).strip()
            if oblast_mention in oblast_normalizations:
                result['oblast_key'] = oblast_normalizations[oblast_mention]
            elif oblast_mention in OBLAST_CENTERS:
                result['oblast_key'] = oblast_mention
            break
    
    return result

# =============================================================================
# PHOTON API GEOCODING
# =============================================================================
def geocode_with_photon(city: str, region_name: str = None):
    """Geocode using Photon API with optional region filtering."""
    if not city:
        return None
    
    try:
        import requests
        
        photon_url = 'https://photon.komoot.io/api/'
        params = {'q': city, 'limit': 15}
        
        response = requests.get(photon_url, params=params, timeout=3)
        if response.ok:
            data = response.json()
            
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                state = props.get('state', '')
                country = props.get('country', '')
                osm_key = props.get('osm_key', '')
                osm_value = props.get('osm_value', '')
                
                # Filter out POIs
                if osm_key not in ['place', 'boundary']:
                    continue
                valid_place_types = ['city', 'town', 'village', 'hamlet', 'suburb', 
                                    'neighbourhood', 'administrative', 'borough', 'quarter', 'district']
                if osm_key == 'place' and osm_value not in valid_place_types:
                    continue
                
                if country in ['Україна', 'Ukraine']:
                    # Filter by region if provided
                    if region_name and region_name not in state:
                        continue
                    
                    coords_arr = feature.get('geometry', {}).get('coordinates', [])
                    if coords_arr and len(coords_arr) >= 2:
                        lng_val = safe_float(coords_arr[0])
                        lat_val = safe_float(coords_arr[1])
                        if lat_val is not None and lng_val is not None:
                            if validate_ukraine_coords(lat_val, lng_val):
                                return (lat_val, lng_val, False)
    except Exception as e:
        log.debug(f"Photon API error: {e}")
    
    return None

# =============================================================================
# NOMINATIM API GEOCODING
# =============================================================================
def geocode_with_nominatim(city: str, region: str = None):
    """Geocode using Nominatim API with transliteration."""
    if not city:
        return None
    
    try:
        import requests
        
        # Transliterate Ukrainian to Latin
        def transliterate_ua_to_latin(text):
            translit_map = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g', 'д': 'd', 'е': 'e', 'є': 'ye',
                'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l',
                'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ь': '', 'ю': 'yu', 'я': 'ya',
                'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'H', 'Ґ': 'G', 'Д': 'D', 'Е': 'E', 'Є': 'Ye',
                'Ж': 'Zh', 'З': 'Z', 'И': 'Y', 'І': 'I', 'Ї': 'Yi', 'Й': 'Y', 'К': 'K', 'Л': 'L',
                'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
                'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ь': '', 'Ю': 'Yu', 'Я': 'Ya'
            }
            return ''.join(translit_map.get(c, c) for c in text)
        
        name_latin = transliterate_ua_to_latin(city)
        
        nominatim_url = 'https://nominatim.openstreetmap.org/search'
        params = {
            'q': f'{name_latin}, Ukraine',
            'format': 'json',
            'limit': 5,
            'addressdetails': 1
        }
        headers = {'User-Agent': 'NeptunAlarmMap/1.0 (https://neptun.in.ua)'}
        
        response = requests.get(nominatim_url, params=params, headers=headers, timeout=4)
        if response.ok:
            results = response.json()
            if not isinstance(results, list):
                results = []
            
            for result in results:
                if not isinstance(result, dict):
                    continue
                
                if region:
                    address = result.get('address', {})
                    result_state = address.get('state', '')
                    if region not in result_state.lower() and result_state.lower() not in region:
                        continue
                
                lat_val = safe_float(result.get('lat'))
                lng_val = safe_float(result.get('lon'))
                if lat_val is not None and lng_val is not None:
                    if validate_ukraine_coords(lat_val, lng_val):
                        return (lat_val, lng_val, False)
    except Exception as e:
        log.debug(f"Nominatim API error: {e}")
    
    return None

# =============================================================================
# MAIN GEOCODING FUNCTIONS
# =============================================================================
def ensure_city_coords(name: str, region_hint: str = None):
    """Get coordinates for settlement using multiple APIs.
    Returns (lat, lng, is_approximate) or None."""
    if not name:
        return None
    
    n = name.strip().lower()
    
    # Apply normalizations
    if n in UA_CITY_NORMALIZE:
        n = UA_CITY_NORMALIZE[n]
    
    # Normalize declensions to nominative case
    original_n = n
    if n.endswith('ку') and len(n) > 4:
        n = n[:-2] + 'ка'
    elif n.endswith('цю') and len(n) > 4:
        n = n[:-2] + 'ця'
    elif n.endswith('у') and len(n) > 3:
        if n[-2] not in 'аеиоуяюєї' and n[-2] in 'вгджзклмнпрстфхцчшщ':
            n = n[:-1]
    elif n.endswith('ові') and len(n) > 5:
        n = n[:-3]
    elif n.endswith('ом') and len(n) > 4:
        n = n[:-2]
    
    if n != original_n:
        log.debug(f"Declension normalized '{original_n}' -> '{n}'")
    
    # Check local database first
    if n in CITY_COORDS:
        coords = CITY_COORDS[n]
        return (coords[0], coords[1], False)
    
    # Check oblast centers
    if n in OBLAST_CENTERS:
        coords = OBLAST_CENTERS[n]
        return (coords[0], coords[1], True)
    
    # Get region hint from NAME_REGION_MAP if not provided
    if not region_hint:
        region_hint = NAME_REGION_MAP.get(n)
    
    # Try Photon API
    result = geocode_with_photon(n, region_hint)
    if result:
        return result
    
    # Try Nominatim API
    result = geocode_with_nominatim(n, region_hint)
    if result:
        return result
    
    # Fallback to oblast center
    if region_hint:
        reg_low = region_hint.lower()
        for oblast_key, (olat, olng) in OBLAST_CENTERS.items():
            if oblast_key in reg_low or reg_low in oblast_key:
                return (olat, olng, True)
    
    return None

def ensure_city_coords_with_message_context(name: str, message_text: str = ""):
    """Enhanced geocoding that uses message context to determine region."""
    if not name:
        return None
    
    name_lower = name.strip().lower()
    
    # Apply normalizations
    if name_lower in UA_CITY_NORMALIZE:
        name_lower = UA_CITY_NORMALIZE[name_lower]
    
    # Extract oblast context from message
    context = extract_district_and_oblast_context(message_text)
    detected_oblast_key = context.get('oblast_key')
    
    # Try Groq AI first if available
    if GROQ_ENABLED and message_text:
        try:
            ai_result = extract_location_with_groq_ai(message_text)
            if ai_result and ai_result.get('confidence', 0) > 0.7:
                ai_city = ai_result.get('city')
                ai_oblast = ai_result.get('oblast')
                
                if ai_city:
                    target_city = ai_city.lower()
                    
                    # Build context for geocoding
                    oblast_key = None
                    if ai_oblast:
                        oblast_normalizations = {
                            'дніпропетровська область': 'дніпропетровська область',
                            'харківська область': 'харківська обл.',
                            'полтавська область': 'полтавська область',
                            'сумська область': 'сумська область',
                            'чернігівська область': 'чернігівська обл.',
                            'миколаївська область': 'миколаївська обл.',
                            'одеська область': 'одеська обл.',
                            'запорізька область': 'запорізька область',
                            'херсонська область': 'херсонська обл.',
                            'київська область': 'київська обл.',
                        }
                        ai_oblast_lower = ai_oblast.lower()
                        oblast_key = oblast_normalizations.get(ai_oblast_lower, ai_oblast_lower)
                    
                    # Try geocoding with AI-provided context
                    coords = ensure_city_coords(target_city, oblast_key)
                    if coords:
                        return coords
        except Exception as e:
            log.debug(f"Groq AI geocoding failed: {e}")
    
    # Fallback to standard geocoding
    return ensure_city_coords(name_lower, detected_oblast_key)

def geocode_with_context(city: str, oblast_key: str, district: str = None):
    """Geocode city using Photon API with oblast and optional district context."""
    if not city:
        return None
    
    try:
        import requests
        
        oblast_to_region_map = {
            'дніпропетровська область': 'Дніпропетровська область',
            'харківська обл.': 'Харківська область',
            'полтавська область': 'Полтавська область',
            'сумська область': 'Сумська область',
            'чернігівська обл.': 'Чернігівська область',
            'миколаївська обл.': 'Миколаївська область',
            'одеська обл.': 'Одеська область',
            'запорізька область': 'Запорізька область',
            'херсонська обл.': 'Херсонська область',
            'київська обл.': 'Київська область',
            'донецька область': 'Донецька область',
            'луганська область': 'Луганська область',
        }
        
        region_name = oblast_to_region_map.get(oblast_key.lower(), oblast_key)
        
        photon_url = 'https://photon.komoot.io/api/'
        params = {'q': city, 'limit': 15}
        
        response = requests.get(photon_url, params=params, timeout=3)
        if response.ok:
            data = response.json()
            
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                state = props.get('state', '')
                county = props.get('county', '')
                country = props.get('country', '')
                osm_key = props.get('osm_key', '')
                osm_value = props.get('osm_value', '')
                
                if osm_key not in ['place', 'boundary']:
                    continue
                valid_place_types = ['city', 'town', 'village', 'hamlet', 'suburb', 
                                    'neighbourhood', 'administrative']
                if osm_key == 'place' and osm_value not in valid_place_types:
                    continue
                
                if (country == 'Україна' or country == 'Ukraine'):
                    if region_name in state:
                        coords_arr = feature.get('geometry', {}).get('coordinates', [])
                        if coords_arr and len(coords_arr) >= 2:
                            lng_val = safe_float(coords_arr[0])
                            lat_val = safe_float(coords_arr[1])
                            if lat_val is None or lng_val is None:
                                continue
                            if not validate_ukraine_coords(lat_val, lng_val):
                                continue
                            
                            # If district provided, prefer district match
                            if district:
                                county_lower = county.lower()
                                district_lower = district.lower()
                                if district_lower in county_lower or county_lower.startswith(district_lower):
                                    log.debug(f"Found '{city}' in {county}, {state} (district match)")
                                    return (lat_val, lng_val, False)
                                else:
                                    continue
                            
                            log.debug(f"Found '{city}' in {state}")
                            return (lat_val, lng_val, False)
    except Exception as e:
        log.debug(f"geocode_with_context error: {e}")
    
    return None

# =============================================================================
# TOPONYM NORMALIZATION
# =============================================================================
def normalize_ukrainian_toponym(lemmatized_name: str, original_text: str, grammatical_case: str = None) -> str:
    """Normalize Ukrainian place name using linguistic patterns."""
    
    # Special exceptions
    special_exceptions = {
        'чкаловський': 'чкаловське',
        'чкаловського': 'чкаловське',
        'чкаловському': 'чкаловське',
        'олексадрія': 'олександрія',
    }
    
    if lemmatized_name in special_exceptions:
        return special_exceptions[lemmatized_name]
    
    # Adjective to city patterns
    adjective_to_city_patterns = [
        (r'(.+)ський$', r'\1ськ'),
        (r'(.+)цький$', r'\1цьк'),
        (r'(.+)рський$', r'\1рськ'),
        (r'(.+)нський$', r'\1нськ'),
        (r'(.+)льський$', r'\1льськ'),
    ]
    
    for pattern, replacement in adjective_to_city_patterns:
        if re.match(pattern, lemmatized_name):
            return re.sub(pattern, replacement, lemmatized_name)
    
    # Case-specific fixes
    case_specific_fixes = {
        'зарічний': 'зарічне',
        'новоукраїнськом': 'новоукраїнськ',
        'краматорськом': 'краматорськ',
        'покровськом': 'покровськ',
    }
    
    if lemmatized_name in case_specific_fixes:
        return case_specific_fixes[lemmatized_name]
    
    return lemmatized_name

# =============================================================================
# KYIV DIRECTIONAL GEOCODING
# =============================================================================
def get_kyiv_directional_coordinates(threat_text: str, original_city: str = "київ"):
    """For Kyiv threats, calculate directional coordinates based on threat patterns."""
    kyiv_lat, kyiv_lng = 50.4501, 30.5234
    threat_lower = threat_text.lower()
    
    # Try to extract source city/direction
    course_patterns = [
        r'бпла.*?курс.*?на.*?київ.*?з\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
        r'бпла.*?курс.*?на.*?київ.*?від\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
        r'([а-яіїєё\s\-\']+?).*?курс.*?на.*?київ',
    ]
    
    source_city = None
    for pattern in course_patterns:
        matches = re.findall(pattern, threat_lower)
        if matches:
            potential_city = matches[0].strip()
            if potential_city and len(potential_city) > 2:
                noise_words = {'бпла', 'курсом', 'курс', 'на', 'над', 'області', 'область', 'обл', 'район'}
                clean_city = ' '.join([word for word in potential_city.split() if word not in noise_words])
                if clean_city:
                    source_city = clean_city
                    break
    
    if source_city:
        approach_directions = {
            'чернігів': (51.4982, 31.2893, "↘ Київ"),
            'суми': (50.9077, 34.7981, "↙ Київ"),
            'харків': (49.9935, 36.2304, "← Київ"),
            'полтава': (49.5883, 34.5514, "↖ Київ"),
            'черкаси': (49.4444, 32.0598, "↑ Київ"),
            'житомир': (50.2547, 28.6587, "→ Київ"),
            'біла церква': (49.7939, 30.1014, "↗ Київ")
        }
        
        if source_city in approach_directions:
            source_lat, source_lng, direction_label = approach_directions[source_city]
            
            # Place marker 70% of the way from source to Kyiv
            progress = 0.7
            approach_lat = source_lat + (kyiv_lat - source_lat) * progress
            approach_lng = source_lng + (kyiv_lng - source_lng) * progress
            
            return approach_lat, approach_lng, direction_label, source_city
    
    return kyiv_lat, kyiv_lng, "Київ", None
