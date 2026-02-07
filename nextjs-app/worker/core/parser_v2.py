"""
parser_v2.py — Deterministic NLP parser for Ukrainian threat messages.

Extracts structured entities from raw Telegram text:
  - event type (uav, missile, kab, explosion, launch)
  - oblast authority (region lock from text context)
  - place names (settlement candidates)
  - direction / near references
  - negation detection

Does NOT geocode.  Geocoding is handled by geo/resolver.py.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from constants import OBLAST_CENTERS

log = logging.getLogger(__name__)

# ─── CONFIGURATION ───────────────────────────────────────────────────────────

# Priority: Markers that define the "Authority" Region
RE_OBLAST_AUTHORITY = re.compile(r'\(([^)]+?)\s*(?:обл|region)[^)]*\)', re.IGNORECASE)
RE_OBLAST_EXPLICIT_FULL = re.compile(r'([а-яіїєґ]+(?:ська|ька|цька|ську|ьку|цьку))\s+(?:область|обл)', re.IGNORECASE)
RE_OBLAST_SUFFIX = re.compile(r'(?:на|в|по|у|над)?\s*([а-яіїєґ]+(?:щина|ччина|щині|ччині|щини|ччини|щину|ччину))', re.IGNORECASE)

# Direction patterns: "напрямок на X", "курс на Y", "у напрямку Z"
RE_DIRECTION = re.compile(r'(?:напрям(?:ок|ку)?|курс|рух|вектор)\s+(?:на|до|в)\s+([а-яіїєґ\'\-]+(?:\s+[а-яіїєґ\'\-]+)?)', re.IGNORECASE)
# Near patterns: "поблизу X", "біля Y", "район Z"
RE_NEAR = re.compile(r'(?:поблизу|біля|повз|район|околиці?|поряд з)\s+([а-яіїєґ\'\-]+(?:\s+[а-яіїєґ\'\-]+)?)', re.IGNORECASE)

OBLAST_NORMALIZATION = {
    'чернігів': 'Чернігівська область',
    'київ': 'Київська область',
    'сум': 'Сумська область',
    'сумськ': 'Сумська область',
    'сумщ': 'Сумська область',
    'полтав': 'Полтавська область',
    'харків': 'Харківська область',
    'дніпропетров': 'Дніпропетровська область',
    'дніпр': 'Дніпропетровська область',
    'херсон': 'Херсонська область',
    'миколаїв': 'Миколаївська область',
    'одес': 'Одеська область',
    'одещ': 'Одеська область',
    'запорі': 'Запорізька область',
    'вінниц': 'Вінницька область',
    'віннич': 'Вінницька область',
    'житомир': 'Житомирська область',
    'черкас': 'Черкаська область',
    'черкащ': 'Черкаська область',
    'кіровоград': 'Кіровоградська область',
    'донец': 'Донецька область',
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
    'хмельниц': 'Хмельницька область',
}

STEM_PROPER_NAMES = {
    'сум': 'Суми', 'одес': 'Одеса', 'вінниц': 'Вінниця',
    'кропивниц': 'Кропивницький', 'запоріж': 'Запоріжжя', 'дніпр': 'Дніпро',
    'хмельниц': 'Хмельницький', 'чернівц': 'Чернівці', 'тернопіл': 'Тернопіль',
    'рівн': 'Рівне', 'луцьк': 'Луцьк', 'ужгород': 'Ужгород',
    'умань': 'Умань', 'уман': 'Умань', 'львів': 'Львів',
    'київ': 'Київ', 'харків': 'Харків', 'чернігів': 'Чернігів',
    'миколаїв': 'Миколаїв', 'херсон': 'Херсон', 'полтав': 'Полтава',
    'житомир': 'Житомир', 'черкас': 'Черкаси', 'донец': 'Донецьк',
    'луганськ': 'Луганськ', 'крим': 'Сімферополь',
}

NOISE_WORDS = [
    'біля', 'повз', 'на', 'над', 'у напрямку', 'напрямок', 'курс',
    'зі сходу', 'з півночі', 'з півдня', 'із заходу',
    'вектор', 'рух', 'летить', 'бачимо', 'чути', 'увага', 'тривога',
]

EVENT_TYPES = {
    'launch':    ['пуск', 'виліт', 'запуск', 'зліт', 'активність', 'загроза', 'угроза'],
    'uav':       ['бпла', 'дрон', 'шахед', 'мопед', 'герань', 'shahed', 'розвідник', 'розвідка', 'шахид'],
    'missile':   ['ракета', 'ракети', 'калібр', 'х-101', 'х-59', 'кинджал', 'іскандер', 'балістик', 'ракта'],
    'kab':       ['каб', 'авіація', 'бомба'],
    'explosion': ['вибух', 'гучно', 'обстріл', 'взрыв', 'громко'],
}

NEGATION_KEYWORDS = [
    'не підтверди', 'відбій', 'фейк', 'fake', 'спростуван', 'навчання', 'тренування',
]

CITY_ALIASES = {
    'kiev': 'київ', 'kyiv': 'київ', 'kievi': 'київ', 'киїїв': 'київ', 'киев': 'київ',
    'kharkiv': 'харків', 'kharkov': 'харків', 'харков': 'харків', 'харьков': 'харків',
    'dnipro': 'дніпр', 'dnepropetrovsk': 'дніпр', 'dnepr': 'дніпр', 'днепр': 'дніпр',
    'odesa': 'одес', 'odessa': 'одес', 'odessu': 'одес', 'одессу': 'одес',
    'lviv': 'львів', 'lvov': 'львів', 'львов': 'львів',
    'uman': 'умань', "uman'": 'умань',
    'vinnytsia': 'вінниц', 'vinnitsa': 'вінниц', 'винница': 'вінниц',
    'zhitomir': 'житомир', 'zhytomyr': 'житомир',
}


# ─── Data classes ────────────────────────────────────────────────────────────

@dataclass
class ParsedEntities:
    """Structured entities extracted from a message (no coordinates)."""
    event_type: str           # 'uav', 'missile', 'kab', 'explosion', 'launch', 'unknown', 'info'
    place_name: Optional[str] = None  # primary settlement name
    oblast: Optional[str] = None      # normalized oblast e.g. "Харківська область"
    direction: Optional[str] = None   # "напрямок на Павлоград"
    near: Optional[str] = None        # "поблизу Миргорода"
    raion: Optional[str] = None
    raw_text: str = ''
    is_negation: bool = False

    def to_entities_dict(self) -> dict:
        """Convert to dict for resolver.resolve()."""
        return {
            'place_name': self.place_name or '',
            'oblast': self.oblast,
            'direction': self.direction,
            'near': self.near,
            'raion': self.raion,
            'threat_type': self.event_type,
        }


class ThreatEvent:
    """Legacy: keeps backward compatibility with existing worker.py."""
    def __init__(self, type, location, region, raw_text, coords=None,
                 confidence=0.0, resolve_status='', candidates=None):
        self.type = type
        self.location = location
        self.region = region
        self.raw_text = raw_text
        self.coords = coords
        self.confidence = confidence
        self.resolve_status = resolve_status
        self.candidates = candidates or []

    def to_dict(self):
        return {
            'type': self.type,
            'location': self.location,
            'region': self.region,
            'text': self.raw_text,
            'lat': self.coords[0] if self.coords else None,
            'lng': self.coords[1] if self.coords else None,
            'confidence': round(self.confidence, 3),
            'resolve_status': self.resolve_status,
            'candidates': self.candidates[:3],
            'ts': 0,
            'resolver_version': 'v2',
        }


# ─── Core extraction functions ───────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Lowercase and basic cleanup."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s\(\)\.,-]', '', text)
    return text.strip()


def classify_event(text: str) -> str:
    """Determine event type from normalized text."""
    text = normalize_text(text)
    # Priority: KAB > Missile > UAV > Explosion > Launch
    for etype in ['kab', 'missile', 'uav', 'explosion']:
        for kw in EVENT_TYPES[etype]:
            if kw in text:
                return etype
    for kw in EVENT_TYPES['launch']:
        if kw in text:
            return 'launch'
    return 'unknown'


def extract_oblast_authority(text: str) -> Optional[str]:
    """Extract region/oblast authority from text."""
    candidates = []
    for m in RE_OBLAST_AUTHORITY.finditer(text):
        candidates.append(m.group(1).lower().strip())
    for m in RE_OBLAST_SUFFIX.finditer(text):
        candidates.append(m.group(1).lower().strip())
    for m in RE_OBLAST_EXPLICIT_FULL.finditer(text):
        candidates.append(m.group(1).lower().strip())

    for cand in candidates:
        for stem, official_name in OBLAST_NORMALIZATION.items():
            if stem in cand:
                return official_name
    return None


def clean_noise(text: str) -> str:
    """Remove directional/noise words."""
    t = text.lower()
    pattern = r'\b(?:' + '|'.join(map(re.escape, NOISE_WORDS)) + r')\b'
    return re.sub(pattern, ' ', t)


def _extract_place_names(text: str, oblast: Optional[str]) -> list[str]:
    """
    Extract settlement names from text.
    Returns list of candidate place names (most specific first).
    """
    cleaned = clean_noise(text)
    found: list[tuple[int, str]] = []

    # Build a set of threat keywords to filter out
    _threat_words = set()
    for keywords in EVENT_TYPES.values():
        _threat_words.update(kw.lower() for kw in keywords)
    _threat_words.update(kw.lower() for kw in NOISE_WORDS)
    _threat_words.update(kw.lower() for kw in NEGATION_KEYWORDS)

    # 1. Check OBLAST_CENTERS (major cities)
    for city_stem in OBLAST_CENTERS:
        pattern = r'\b' + re.escape(city_stem) + r'(?:а|у|і|е|ом|ам|ів|и|ин|ського|ському|ським|ю)?\b'
        if city_stem == 'київ':
            pattern = r'\b(?:київ|києв|києві|києва)\b'
        elif city_stem == 'харків':
            pattern = r'\b(?:харків|харков|харкові|харкова)\b'
        elif city_stem == 'львів':
            pattern = r'\b(?:львів|львов|львові|львова)\b'
        elif city_stem == 'умань':
            pattern = r'\b(?:умань|уман|умані)\b'

        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            display_name = STEM_PROPER_NAMES.get(city_stem, city_stem.title())
            found.append((match.start(), display_name))

    # 2. Check city aliases
    for alias, canonical_key in CITY_ALIASES.items():
        match = re.search(r'\b' + re.escape(alias) + r'[a-zа-яіїєґ]*\b', cleaned, re.IGNORECASE)
        if match and canonical_key in OBLAST_CENTERS:
            display_name = STEM_PROPER_NAMES.get(canonical_key, canonical_key.title())
            found.append((match.start(), display_name))

    # 3. Extract "preposition + City" patterns (у Харкові, по Куп'янську, в Одесі)
    prep_matches = re.finditer(
        r'(?:у|в|по|на|до|під|над|з|із|від|для|через|біля|повз)\s+'
        r'([А-ЯІЇЄҐа-яіїєґ][а-яіїєґ\'\'\-]{2,}(?:[\s\-][А-ЯІЇЄҐа-яіїєґ][а-яіїєґ\'\'\-]+)?)',
        text, re.IGNORECASE
    )
    for pm in prep_matches:
        noun = pm.group(1).strip()
        if noun.lower() not in _threat_words and not any(
            stem in noun.lower() for stem in ['область', 'обл', 'щина', 'ччина', 'район']
        ):
            if not any(noun.lower() == f[1].lower() for f in found):
                found.append((pm.start(1), noun))

    # 4. Extract capitalized proper nouns from ORIGINAL text (before lowercasing)
    # These might be settlement names not in our dictionaries
    proper_nouns = re.findall(
        r'(?:^|[\s,(])([А-ЯІЇЄҐ][а-яіїєґ\'\'\-]{2,}(?:\s+[А-ЯІЇЄҐ][а-яіїєґ\'\'\-]+)?)',
        text
    )
    for noun in proper_nouns:
        noun = noun.strip()
        # Skip oblast names and noise
        if any(stem in noun.lower() for stem in ['область', 'обл', 'щина', 'ччина', 'район']):
            continue
        if noun.lower() in _threat_words:
            continue
        # Don't duplicate
        if not any(noun.lower() == f[1].lower() for f in found):
            found.append((text.index(noun) if noun in text else 999, noun))

    # Sort by position in text (first mentioned = most likely primary)
    found.sort(key=lambda x: x[0])
    # Filter out threat keywords from results
    return [name for _, name in found if name.lower() not in _threat_words]


def _extract_direction(text: str) -> Optional[str]:
    """Extract direction target: 'напрямок на X'."""
    m = RE_DIRECTION.search(text)
    if m:
        return m.group(1).strip()
    return None


def _extract_near(text: str) -> Optional[str]:
    """Extract 'near' reference: 'поблизу X'."""
    m = RE_NEAR.search(text)
    if m:
        return m.group(1).strip()
    return None


# ─── Public API ──────────────────────────────────────────────────────────────

def extract_entities(text: str) -> ParsedEntities:
    """
    Extract all structured entities from raw message text.
    Does NOT geocode — just parses.
    """
    normalized = normalize_text(text)

    # Negation check
    for neg in NEGATION_KEYWORDS:
        if neg in normalized:
            return ParsedEntities(
                event_type='info', raw_text=text, is_negation=True,
            )

    event_type = classify_event(normalized)
    oblast = extract_oblast_authority(text)
    place_names = _extract_place_names(text, oblast)
    direction = _extract_direction(text)
    near = _extract_near(text)

    return ParsedEntities(
        event_type=event_type,
        place_name=place_names[0] if place_names else None,
        oblast=oblast,
        direction=direction,
        near=near,
        raw_text=text,
    )


def parse_message(text: str) -> ThreatEvent:
    """
    Legacy entry point — extracts entities and resolves location.
    Uses geo/resolver if available, falls back to old dict-based lookup.
    """
    entities = extract_entities(text)

    if entities.is_negation:
        return ThreatEvent('info', 'Unknown', None, text, None)

    if entities.event_type == 'unknown':
        return ThreatEvent('unknown', 'Unknown', None, text, None)

    # Try new geo resolver
    try:
        from geo.resolver import resolve
        resolved = resolve(
            entities.to_entities_dict(),
            channel=None,  # channel is set by worker.py
            prev_events=None,
        )
        return ThreatEvent(
            type=entities.event_type,
            location=resolved.place_name,
            region=resolved.oblast or entities.oblast,
            raw_text=text,
            coords=(resolved.lat, resolved.lng) if resolved.lat != 0 else None,
            confidence=resolved.confidence,
            resolve_status=resolved.status,
            candidates=[c.to_dict() for c in resolved.chosen_from[:3]],
        )
    except ImportError:
        log.warning("geo.resolver not available, using fallback")
    except Exception as e:
        log.error(f"Resolver error: {e}", exc_info=True)

    # Fallback: use OBLAST_CENTERS for basic resolution
    location = entities.place_name or 'Unknown'
    coords = None
    for stem, center_coords in OBLAST_CENTERS.items():
        if location.lower().startswith(stem) or stem in location.lower():
            coords = center_coords
            break

    return ThreatEvent(
        type=entities.event_type,
        location=location,
        region=entities.oblast,
        raw_text=text,
        coords=coords,
    )
