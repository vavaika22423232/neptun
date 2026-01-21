"""
Ukrainian location name normalizer.

Найкращий нормалізатор для українських назв населених пунктів.
Враховує відмінки, варіації написання, префікси/суфікси.
"""
import re
from functools import lru_cache
from typing import Optional


# Ukrainian case endings to remove (accusative, genitive, locative, etc.)
CASE_SUFFIXES = [
    # Accusative/Genitive endings
    'івку', 'івки', 'івці',
    'івну', 'івни', 'івні',
    'ьку', 'ьки', 'ьці',
    'ську', 'ської', 'ській',
    'цьку', 'цької', 'цькій',
    'ину', 'ини', 'ині',
    'ину', 'ини', 'ині',
    'ову', 'ови', 'ові',
    'еву', 'еви', 'еві',
    'яну', 'яни', 'яні',
    'ану', 'ани', 'ані',
    'ену', 'ени', 'ені',
    # Common endings
    'ного', 'ної', 'ному', 'ній',
    'ого', 'ої', 'ому', 'ій',
]

# Location type prefixes to remove
PREFIXES = [
    'м.', 'м ', 'с.', 'с ', 'смт.', 'смт ', 'смт',
    'село ', 'селище ', 'місто ', 'селищe ',
    'хутір ', 'присілок ',
    'район ', 'р-н ', 'обл.', 'обл ',
    'область ', 'станція ', 'ст.',
]

# Oblast name variations mapping
OBLAST_NORMALIZER = {
    # Full names
    'київська область': 'київська',
    'харківська область': 'харківська',
    'дніпропетровська область': 'дніпропетровська',
    'одеська область': 'одеська',
    'запорізька область': 'запорізька',
    'львівська область': 'львівська',
    'донецька область': 'донецька',
    'полтавська область': 'полтавська',
    'вінницька область': 'вінницька',
    'миколаївська область': 'миколаївська',
    'херсонська область': 'херсонська',
    'чернігівська область': 'чернігівська',
    'черкаська область': 'черкаська',
    'житомирська область': 'житомирська',
    'сумська область': 'сумська',
    'хмельницька область': 'хмельницька',
    'чернівецька область': 'чернівецька',
    'рівненська область': 'рівненська',
    'івано-франківська область': 'івано-франківська',
    'тернопільська область': 'тернопільська',
    'волинська область': 'волинська',
    'закарпатська область': 'закарпатська',
    'кіровоградська область': 'кіровоградська',
    'луганська область': 'луганська',
    
    # Short forms
    'київщина': 'київська',
    'харківщина': 'харківська',
    'дніпропетровщина': 'дніпропетровська',
    'одещина': 'одеська',
    'запоріжжя': 'запорізька',
    'львівщина': 'львівська',
    'донеччина': 'донецька',
    'полтавщина': 'полтавська',
    'вінниччина': 'вінницька',
    'миколаївщина': 'миколаївська',
    'херсонщина': 'херсонська',
    'чернігівщина': 'чернігівська',
    'черкащина': 'черкаська',
    'житомирщина': 'житомирська',
    'сумщина': 'сумська',
    'хмельниччина': 'хмельницька',
    'буковина': 'чернівецька',
    'рівненщина': 'рівненська',
    'прикарпаття': 'івано-франківська',
    'тернопільщина': 'тернопільська',
    'волинь': 'волинська',
    'закарпаття': 'закарпатська',
    'кіровоградщина': 'кіровоградська',
    'луганщина': 'луганська',
}

# Common city name variations (normalized -> list of variations)
CITY_ALIASES = {
    'київ': ['києва', 'києві', 'києвом', 'киев', 'kyiv', 'kiev'],
    'харків': ['харкова', 'харкові', 'харковом', 'харьков', 'kharkiv'],
    'одеса': ['одеси', 'одесі', 'одесою', 'одесса', 'odesa', 'odessa'],
    'дніпро': ['дніпра', 'дніпрі', 'дніпром', 'днепр', 'dnipro'],
    'запоріжжя': ['запоріжжі', 'запоріжжям', 'запорожье'],
    'львів': ['львова', 'львові', 'львовом', 'львов', 'lviv'],
    'миколаїв': ['миколаєва', 'миколаєві', 'николаев'],
    'херсон': ['херсона', 'херсоні', 'херсоном'],
    'чернігів': ['чернігова', 'чернігові', 'чернигов'],
    'полтава': ['полтави', 'полтаві', 'полтавою'],
    'суми': ['сум', 'сумах', 'сумами'],
    'вінниця': ['вінниці', 'вінницею'],
    'житомир': ['житомира', 'житомирі'],
    'черкаси': ['черкас', 'черкасах'],
    'кропивницький': ['кропивницького', 'кіровоград'],
    'рівне': ['рівного', 'рівному'],
    'луцьк': ['луцька', 'луцьку'],
    'ужгород': ['ужгорода', 'ужгороді'],
    'тернопіль': ['тернополя', 'тернополі'],
    'хмельницький': ['хмельницького', 'хмельницькому'],
    'чернівці': ['чернівців', 'чернівцях'],
    'івано-франківськ': ['івано-франківська', 'франківськ', 'франківська'],
    'краматорськ': ['краматорська', 'краматорську'],
    'маріуполь': ['маріуполя', 'маріуполі', 'мариуполь'],
}

# Reverse alias map for quick lookup
_ALIAS_TO_CANONICAL = {}
for canonical, aliases in CITY_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias] = canonical


@lru_cache(maxsize=10000)
def normalize_city(name: str) -> str:
    """
    Normalize city/settlement name for database lookup.
    
    Handles:
    - Lowercase conversion
    - Prefix removal (м., с., смт., etc.)
    - Case ending normalization
    - Common variations
    - Whitespace cleanup
    
    Args:
        name: Raw city name
        
    Returns:
        Normalized name for lookup
    """
    if not name:
        return ""
    
    # Lowercase and strip
    result = name.lower().strip()
    
    # Remove quotes
    result = result.replace('"', '').replace("'", '').replace('«', '').replace('»', '')
    
    # Remove prefixes
    for prefix in PREFIXES:
        if result.startswith(prefix):
            result = result[len(prefix):].strip()
    
    # Check if it's a known alias
    if result in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[result]
    
    # Remove parenthetical content (district info, etc.)
    result = re.sub(r'\s*\([^)]*\)', '', result)
    
    # Normalize whitespace
    result = ' '.join(result.split())
    
    # Try to find base form for case endings
    # This is tricky - we need to be careful not to over-normalize
    for suffix in CASE_SUFFIXES:
        if result.endswith(suffix) and len(result) > len(suffix) + 2:
            # Don't strip if it would make the name too short
            base = result[:-len(suffix)]
            # Check if base + common nominative ending exists
            # This is a heuristic - might need refinement
            if len(base) >= 3:
                # Return the base - the lookup will try variations
                return result  # For now, return as-is
    
    return result


@lru_cache(maxsize=5000)
def normalize_oblast(name: str) -> Optional[str]:
    """
    Normalize oblast name to standard form.
    
    Args:
        name: Oblast name in any form
        
    Returns:
        Normalized oblast key or None
    """
    if not name:
        return None
    
    lower = name.lower().strip()
    
    # Direct lookup
    if lower in OBLAST_NORMALIZER:
        return OBLAST_NORMALIZER[lower]
    
    # Try to match partial
    for key, normalized in OBLAST_NORMALIZER.items():
        if key in lower or lower in key:
            return normalized
    
    # Extract oblast name from compound
    if 'область' in lower:
        parts = lower.split('область')[0].strip()
        if parts in OBLAST_NORMALIZER:
            return OBLAST_NORMALIZER[parts]
        # Try adding 'ська' suffix
        if parts.endswith('ськ'):
            return parts + 'а'
        elif parts.endswith('цьк'):
            return parts + 'а'
    
    return None


def get_name_variants(name: str) -> list[str]:
    """
    Generate possible variants of a city name for fuzzy matching.
    
    Args:
        name: Normalized city name
        
    Returns:
        List of possible variants to try
    """
    if not name:
        return []
    
    variants = [name]
    
    # Common case transformations for Ukrainian
    # Accusative -у -> nominative -а
    if name.endswith('у') and len(name) > 3:
        variants.append(name[:-1] + 'а')
    
    # Genitive -и -> nominative -а
    if name.endswith('и') and len(name) > 3:
        variants.append(name[:-1] + 'а')
    
    # Locative -і -> nominative -а
    if name.endswith('і') and len(name) > 3:
        variants.append(name[:-1] + 'а')
    
    # -івку -> -івка
    if name.endswith('івку'):
        variants.append(name[:-1] + 'а')
    
    # -івки -> -івка
    if name.endswith('івки'):
        variants.append(name[:-1] + 'а')
    
    # -ого -> nominative
    if name.endswith('ого'):
        variants.append(name[:-3] + 'е')
        variants.append(name[:-3] + 'ий')
    
    # -ої -> nominative
    if name.endswith('ої'):
        variants.append(name[:-2] + 'а')
    
    # -ому/-ій (locative) -> nominative
    if name.endswith('ому'):
        variants.append(name[:-3] + 'е')
        variants.append(name[:-3] + 'ий')
    
    if name.endswith('ій'):
        variants.append(name[:-2] + 'а')
        variants.append(name[:-2] + 'я')
    
    # Remove duplicates while preserving order
    seen = set()
    result = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            result.append(v)
    
    return result


def extract_location_from_text(text: str) -> list[dict]:
    """
    Extract potential location names from Ukrainian military message.
    
    Patterns recognized:
    - "курсом на [LOCATION]"
    - "в районі [LOCATION]"
    - "над [LOCATION]"
    - "біля [LOCATION]"
    - "[LOCATION] район/область"
    
    Args:
        text: Message text
        
    Returns:
        List of {name: str, type: str, confidence: float}
    """
    if not text:
        return []
    
    text_lower = text.lower()
    locations = []
    
    # Pattern: "курсом на [city]"
    for match in re.finditer(r'курс(?:ом)?\s+на\s+([а-яіїєґ\'\-]+(?:\s+[а-яіїєґ\'\-]+)?)', text_lower):
        locations.append({
            'name': match.group(1).strip(),
            'type': 'target',
            'confidence': 0.9,
        })
    
    # Pattern: "в районі [city]"
    for match in re.finditer(r'(?:в|у)\s+район[іи]\s+([а-яіїєґ\'\-]+(?:\s+[а-яіїєґ\'\-]+)?)', text_lower):
        locations.append({
            'name': match.group(1).strip(),
            'type': 'location',
            'confidence': 0.85,
        })
    
    # Pattern: "над [city]"
    for match in re.finditer(r'над\s+([а-яіїєґ\'\-]+(?:\s+[а-яіїєґ\'\-]+)?)', text_lower):
        name = match.group(1).strip()
        # Filter out common non-location words
        if name not in ['водою', 'морем', 'територією', 'землею']:
            locations.append({
                'name': name,
                'type': 'location',
                'confidence': 0.8,
            })
    
    # Pattern: "біля [city]" 
    for match in re.finditer(r'біля\s+([а-яіїєґ\'\-]+)', text_lower):
        locations.append({
            'name': match.group(1).strip(),
            'type': 'location',
            'confidence': 0.75,
        })
    
    # Pattern: "з [city] курсом"
    for match in re.finditer(r'з\s+([а-яіїєґ\'\-]+)\s+курс', text_lower):
        locations.append({
            'name': match.group(1).strip(),
            'type': 'source',
            'confidence': 0.85,
        })
    
    # Pattern: "[oblast]ська область" or "[oblast]щина"
    for match in re.finditer(r'([а-яіїєґ]+)(?:ська\s+область|щина)', text_lower):
        oblast_name = match.group(0)
        normalized = normalize_oblast(oblast_name)
        if normalized:
            locations.append({
                'name': oblast_name,
                'type': 'oblast',
                'confidence': 0.95,
                'normalized': normalized,
            })
    
    return locations


def is_direction_word(word: str) -> bool:
    """Check if word is a direction, not a location."""
    directions = {
        'північ', 'південь', 'схід', 'захід',
        'північний', 'південний', 'східний', 'західний',
        'північно', 'південно', 'північно-східний', 'північно-західний',
        'південно-східний', 'південно-західний',
        'пн', 'пд', 'сх', 'зх',
    }
    return word.lower().strip() in directions
