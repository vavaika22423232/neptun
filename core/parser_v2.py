import re
import logging
from constants import OBLAST_CENTERS, REGION_TO_OBLAST_ID

log = logging.getLogger(__name__)

# --- CONFIGURATION ---

# Priority: Markers that define the "Authority" Region
# Matches: "(Чернігівська обл)", "(Київська область)", "на Харківщині"
# Group 1: The name part before 'обл'
RE_OBLAST_AUTHORITY = re.compile(r'\(([^)]+?)\s*(?:обл|region)[^)]*\)', re.IGNORECASE)
# Matches explicit "XXX область/обл" without parentheses
RE_OBLAST_EXPLICIT_FULL = re.compile(r'([а-яіїєґ]+(?:ська|ька|цька|ську|ьку|цьку))\s+(?:область|обл)', re.IGNORECASE)
# Matches suffix like "Сумщині", "Харківщини", "Харківщину" possibly preceded by preposition
RE_OBLAST_SUFFIX = re.compile(r'(?:на|в|по|у|над)?\s*([а-яіїєґ]+(?:щина|ччина|щині|ччині|щини|ччини|щину|ччину))', re.IGNORECASE)

# Mapping simplified stems to official names
# Keys are lowered stems
OBLAST_NORMALIZATION = {
    'чернігів': 'Чернігівська область',
    'київ': 'Київська область',
    'сум': 'Сумська область',
    'сумськ': 'Сумська область', # сумська
    'сумщ': 'Сумська область',   # сумщині
    'полтав': 'Полтавська область',
    'харків': 'Харківська область',
    'дніпропетров': 'Дніпропетровська область',
    'дніпр': 'Дніпропетровська область', # Common short
    'херсон': 'Херсонська область',
    'миколаїв': 'Миколаївська область',
    'одес': 'Одеська область', # stem 'одес' covers 'одеська', 'одещину' etc if logic aligns
    'одещ': 'Одеська область',
    'запорі': 'Запорізька область', # 'запорізька', 'запоріжжя'
    'вінниц': 'Вінницька область',
    'віннич': 'Вінницька область',
    'житомир': 'Житомирська область',
    'черкас': 'Черкаська область',
    'черкащ': 'Черкаська область',
    'кіровоград': 'Кіровоградська область',
    'донец': 'Донецька область', # stem 'донецька'
    'донеч': 'Донецька область',
    'луган': 'Луганська область',
    'львів': 'Львівська область',
    'волин': 'Волинська область',
    'рівнен': 'Рівненська область',
    'рівн': 'Рівненська область',
    'тернопіль': 'Тернопільська область',
    'івано-франків': 'Івано-Франківська область',
    'закарпат': 'Закарпатська область',
    'чернівець': 'Чернівецька область',
    'буковин': 'Чернівецька область',
    'буковин': 'Чернівецька область',
    'хмельниц': 'Хмельницька область',
}

# Mapping for pretty printing keys from OBLAST_CENTERS which are stems
STEM_PROPER_NAMES = {
    'сум': 'Суми',
    'одес': 'Одеса',
    'вінниц': 'Вінниця',
    'кропивниц': 'Кропивницький',
    'запоріж': 'Запоріжжя',
    'дніпр': 'Дніпро',
    'хмельниц': 'Хмельницький',
    'чернівц': 'Чернівці',
    'тернопіл': 'Тернопіль',
    'рівн': 'Рівне',
    'луцьк': 'Луцьк',
    'ужгород': 'Ужгород',
    'умань': 'Умань',
    'уман': 'Умань',
    'львів': 'Львів',
    'київ': 'Київ',
    'харків': 'Харків',
    'чернігів': 'Чернігів',
    'миколаїв': 'Миколаїв',
    'херсон': 'Херсон',
    'полтав': 'Полтава',
    'житомир': 'Житомир',
    'черкас': 'Черкаси',
    'донец': 'Донецьк',
    'луганськ': 'Луганськ',
    'крим': 'Сімферополь',
}

# Words to REMOVE before geocoding (Anti-Noise)
NOISE_WORDS = [
    'біля', 'повз', 'на', 'над', 'у напрямку', 'напрямок', 'курс', 'зі сходу', 'з півночі', 
    'з півдня', 'із заходу', 'вектор', 'рух', 'летить', 'бачимо', 'чути', 'увага', 'тривога'
]

# Event Types
EVENT_TYPES = {
    'launch': ['пуск', 'виліт', 'запуск', 'зліт', 'активність', 'загроза', 'угроза'], 
    'uav': ['бпла', 'дрон', 'шахед', 'мопед', 'герань', 'shahed', 'розвідник', 'розвідка', 'шахид', 'шахед'],
    'missile': ['ракета', 'ракети', 'калібр', 'х-101', 'х-59', 'кинджал', 'іскандер', 'балістик', 'ракта'],
    'kab': ['каб', 'авіація', 'бомба'],
    'explosion': ['вибух', 'гучно', 'обстріл', 'взрыв', 'громко'],
} 

# Negation/Ignore Keywords
NEGATION_KEYWORDS = [
    'не підтверди', 'відбій', 'фейк', 'fake', 'спростуван', 'навчання', 'тренування'
]

# Aliases for Russian/Translit -> Ukrainian Canonical (key in OBLAST_CENTERS)
CITY_ALIASES = {
    'kiev': 'київ', 'kyiv': 'київ', 'kievi': 'київ', 'киїїв': 'київ', 'киев': 'київ',
    'kharkiv': 'харків', 'kharkov': 'харків', 'харков': 'харків', 'харьков': 'харків',
    'dnipro': 'дніпр', 'dnepropetrovsk': 'дніпр', 'dnepr': 'дніпр', 'днепр': 'дніпр',
    'odesa': 'одес', 'odessa': 'одес', 'odessu': 'одес', 'одессу': 'одес',
    'lviv': 'львів', 'lvov': 'львів', 'львов': 'львів',
    'uman': 'умань', 'uman\'': 'умань',
    'vinnytsia': 'вінниц', 'vinnitsa': 'вінниц', 'винница': 'вінниц', 'винницу': 'вінниц',
    'zhitomir': 'житомир', 'zhytomyr': 'житомир', 'житомир': 'житомир',
} 

# PRIORITY: If multiple match, which one wins?
# Current logic returns first match in dict order. 
# 'launch' comes first, so "Пуски КАБів" matches 'пуск' -> 'launch'.
# We need KAB to override launch if both present. Or change iteration order.

class ThreatEvent:
    def __init__(self, type, location, region, raw_text, coords=None):
        self.type = type
        self.location = location
        self.region = region
        self.raw_text = raw_text
        self.coords = coords  # (lat, lng)

    def to_dict(self):
        return {
            'type': self.type,
            'location': self.location,
            'region': self.region,
            'text': self.raw_text,
            'lat': self.coords[0] if self.coords else None,
            'lng': self.coords[1] if self.coords else None,
            'ts': 0 # timestamp to be added by worker
        }

def normalize_text(text: str) -> str:
    """Lowercase and basic cleanup."""
    if not text: return ""
    text = text.lower()
    # Remove emojis (simplistic approach)
    text = re.sub(r'[^\w\s\(\)\.,-]', '', text) 
    return text.strip()

def classify_event(text: str) -> str:
    """Router: Determine event type."""
    text = normalize_text(text)
    
    # Priority Order: Explicit Threat > Launch/Activity
    # 1. Check for KAB/Missile/UAV/Explosion specifically
    priority_types = ['kab', 'missile', 'uav', 'explosion']
    for etype in priority_types:
        for kw in EVENT_TYPES[etype]:
            if kw in text:
                return etype
                
    # 2. If no specific threat, check for generic 'launch' or 'activity'
    # 'launch' keywords are generic fallback
    for kw in EVENT_TYPES['launch']:
        if kw in text:
            return 'launch'
        
    return 'unknown'

from typing import Optional

def extract_oblast_authority(text: str) -> Optional[str]:
    """
    Step 2: Geographic Authority (Oblast Lock).
    Returns normalized official "XY область" string or None.
    """
def extract_oblast_authority(text: str) -> Optional[str]:
    """
    Step 2: Geographic Authority (Oblast Lock).
    Returns normalized official "XY область" string or None.
    """
    candidates = []
    
    # 1. Parentheses "(Херсонська обл)"
    for m in RE_OBLAST_AUTHORITY.finditer(text):
        candidates.append(m.group(1).lower().strip())
    
    # 2. Suffix "-щина"
    for m in RE_OBLAST_SUFFIX.finditer(text):
        candidates.append(m.group(1).lower().strip())

    # 3. Explicit "Херсонська область/обл" (No parentheses)
    for m in RE_OBLAST_EXPLICIT_FULL.finditer(text):
        candidates.append(m.group(1).lower().strip())
        
    # Check candidates against stems
    for cand in candidates:
        for stem, official_name in OBLAST_NORMALIZATION.items():
            if stem in cand:
                return official_name
                
    return None

def clean_noise(text: str) -> str:
    """Step 4: Direction Filtering (Anti-Noise)."""
    t = text.lower()
    # Use regex to replace ONLY whole words
    pattern = r'\b(?:' + '|'.join(map(re.escape, NOISE_WORDS)) + r')\b'
    t = re.sub(pattern, ' ', t)
    return t

# --- GEO DATA IMPORTS ---
try:
    from ukraine_all_settlements import UKRAINE_ALL_SETTLEMENTS, UKRAINE_SETTLEMENTS_BY_OBLAST
except ImportError:
    # Fallback/Mock for development if files missing
    UKRAINE_ALL_SETTLEMENTS = {}
    UKRAINE_SETTLEMENTS_BY_OBLAST = {}

def is_unique_global(city_name: str) -> bool:
    """Check if city name is unique in the whole country."""
    # Simplified check: if it appears only once or is a major city
    return True # Placeholder for now, requires better data structure

def resolve_location(text: str, authority_region: Optional[str]):
    """
    Step 3: Location Resolution (Deterministic).
    Returns (official_name, coords).
    """
    cleaned_text = clean_noise(text)
    
    # Remove authority mentions (using stems)
    if authority_region:
         for stem in OBLAST_NORMALIZATION.keys():
             if stem in cleaned_text:
                 cleaned_text = cleaned_text.replace(stem, '') 
    
    # 1. Authority Region Locked Search
    if authority_region:
        region_db = UKRAINE_SETTLEMENTS_BY_OBLAST.get(authority_region, {})
        best_match = None
        longest_len = 0
        
        for city_name, coords in region_db.items():
            # Regex: \bCITY(?:suffixes)?\b
            escaped_city = re.escape(city_name)
            pattern = fr'\b{escaped_city}(?:а|у|і|ом|ам|ів|ів|и|ин)?\b'
            
            if re.search(pattern, cleaned_text, re.IGNORECASE):
                if len(city_name) > longest_len:
                    longest_len = len(city_name)
                    best_match = (city_name.title(), coords)
        
        if best_match:
            return best_match
            
        # Fallback 1: Try to map authority region to a known major center via stems
        # "Сумська область" -> stem "сум" -> match "Суми" key in OBLAST_CENTERS
        stems = [k for k, v in OBLAST_NORMALIZATION.items() if v == authority_region]
        for stem in stems:
             for center_key in OBLAST_CENTERS.keys():
                 if center_key.startswith(stem) or stem.startswith(center_key):
                     # Use proper name if available, else title()
                     display_name = STEM_PROPER_NAMES.get(center_key, center_key.title())
                     return (display_name, OBLAST_CENTERS[center_key])
        
        # Fallback 2: Just return the region name as location (better than nothing)
        return (authority_region, None)

    # 2. Global Unique Search (No Authority)
    # Check major cities first
    # We want to find the FIRST occurrence in text to handle "Pavlohrad -> Dnipro" cases correctly
    # Scan text for ALL possible city matches and pick the one with lowest index?
    
    found_cities = []
    
    for city in OBLAST_CENTERS.keys():
        # Manual patches for irregular declensions
        pattern = r'\b' + re.escape(city) + r'(?:а|у|і|е|ом|ам|ів|и|ин|ського|ському|ським|ю)?\b'
        
        if city == 'київ':
             pattern = r'\b(?:київ|києв|києві|києва)\b'
        elif city == 'харків':
             pattern = r'\b(?:харків|харков|харкові|харкова)\b'
        elif city == 'львів':
             pattern = r'\b(?:львів|львов|львові|львова)\b'
        elif city == 'умань':
             pattern = r'\b(?:умань|уман|умані)\b'

        match = re.search(pattern, cleaned_text, re.IGNORECASE)
        if match:
             display_name = STEM_PROPER_NAMES.get(city, city.title())
             found_cities.append( (match.start(), display_name, OBLAST_CENTERS[city]) )

    # Also check full DB if needed
    for city_name, coords in UKRAINE_ALL_SETTLEMENTS.items():
         match = re.search(r'\b' + re.escape(city_name) + r'(?:а|у|і|ом|ам|ів|и|ин)?\b', cleaned_text, re.IGNORECASE)
         if match:
             found_cities.append( (match.start(), city_name.title(), coords) )

    # Check Aliases (Russian/Translit)
    for alias, canonical_key in CITY_ALIASES.items():
         # Strict alias match
         match = re.search(r'\b' + re.escape(alias) + r'[a-zа-яіїєґ]*\b', cleaned_text, re.IGNORECASE)
         if match:
             if canonical_key in OBLAST_CENTERS:
                 display_name = STEM_PROPER_NAMES.get(canonical_key, canonical_key.title())
                 found_cities.append( (match.start(), display_name, OBLAST_CENTERS[canonical_key]) )
             
    if found_cities:
        # Sort by index (start position)
        found_cities.sort(key=lambda x: x[0])
        return (found_cities[0][1], found_cities[0][2])

    return (None, None)

def parse_message(text: str) -> ThreatEvent:
    """Main Pipeline Entry Point."""
    normalized = normalize_text(text)
    
    # 0. Negation Check
    for neg in NEGATION_KEYWORDS:
        if neg in normalized:
            # Return a 'safe' event or None?
            # For now, let's return a dummy event with type 'info' to signal ignore
            return ThreatEvent('info', 'Unknown', None, text, None)

    event_type = classify_event(normalized)
    
    # 1. Authority
    authority_region = extract_oblast_authority(text)
    
    # 2. Location
    loc_name, loc_coords = resolve_location(text, authority_region)
    
    return ThreatEvent(
        type=event_type,
        location=loc_name if loc_name else "Unknown",
        region=authority_region,
        raw_text=text,
        coords=loc_coords
    )
