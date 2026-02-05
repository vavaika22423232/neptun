import json
import logging
import math
import os
import re
import time
import uuid
from datetime import datetime, timedelta

import pytz

from constants import LAUNCH_SITES, OBLAST_CENTERS

log = logging.getLogger(__name__)

# Dependency placeholders (bound from app.py)
ensure_city_coords_with_message_context = None
opencage_geocode = None
_extract_oblast_from_text = None
predict_route_with_ai = None
extract_trajectory_with_ai = None
add_debug_log = lambda *args, **kwargs: None
spacy_enhanced_geocoding = None
update_route_pattern_with_ai = None
_create_directional_trajectory_markers = None
CITY_COORDS = None
SETTLEMENTS_INDEX = None
GROQ_ENABLED = False
SPACY_AVAILABLE = False

_FORCE_OVERRIDE = {
    'add_debug_log',
    'ensure_city_coords_with_message_context',
    'opencage_geocode',
    '_extract_oblast_from_text',
    'predict_route_with_ai',
    'extract_trajectory_with_ai',
    'spacy_enhanced_geocoding',
    'update_route_pattern_with_ai',
    '_create_directional_trajectory_markers',
    'CITY_COORDS',
    'SETTLEMENTS_INDEX',
    'GROQ_ENABLED',
    'SPACY_AVAILABLE',
}

def bind_dependencies(source_globals: dict):
    for name, value in source_globals.items():
        if name in _FORCE_OVERRIDE:
            globals()[name] = value
            continue
        if name not in globals() or globals().get(name) is None:
            globals()[name] = value

# --- Hot-path regex (compiled once) ---
RE_PARENS_STRIP = re.compile(r"\s*\([^)]*\)\s*")
RE_OBLAST_IN_PARENS = re.compile(r"\(([^)]*обл[^)]*)\)", re.IGNORECASE)
RE_CITY_BEFORE_PARENS = re.compile(r"^([^(]+)\s*\(")
RE_OBLAST_SUFFIX = re.compile(r"обл\.?$", re.IGNORECASE)
RE_OBLAST_PARENS_NAME = re.compile(r"\(([А-Яа-яЇїІіЄєҐґ]+(?:ська|ський|ка)?)\s*обл", re.IGNORECASE)
RE_OBLAST_ANYWHERE = re.compile(r"([А-Яа-яЇїІіЄєҐґ]+)\s*(?:обл|область)", re.IGNORECASE)
RE_PLACE_PREFIX = re.compile(r"^(м\.|смт|с\.|місто|селище)\s+", re.IGNORECASE)
RE_MULTI_SPACE = re.compile(r"\s+")
RE_OBLAST_SUFFIX_REMOVE = re.compile(r"( область| обл\.?| обл)\b", re.IGNORECASE)
RE_RAION_SUFFIX_REMOVE = re.compile(r"( район| р-н)\b", re.IGNORECASE)
RE_REGION_IN_TEXT = re.compile(r"([\w\-]+(?:ська|ький|ка)\s*(?:область|район))", re.IGNORECASE)

UA_CITIES = [
    'київ','харків','одеса','одесса','дніпро','дніпропетровськ','львів','запоріжжя','запорожье','вінниця','миколаїв','николаев',
    'маріуполь','полтава','чернігів','чернигов','черкаси','житомир','суми','хмельницький','чернівці','рівне','івано-франківськ',
    'луцьк','тернопіль','ужгород','кропивницький','кіровоград','кременчук','краматорськ','біла церква','мелітополь','бердянськ',
    'павлоград','ніжин','шостка','короп','кролевець'
]
UA_CITY_NORMALIZE = {
    'одесса':'одеса','запорожье':'запоріжжя','запоріжжі':'запоріжжя','дніпропетровськ':'дніпро','кировоград':'кропивницький','кіровоград':'кропивницький',
    'николаев':'миколаїв','чернигов':'чернігів',
    # Accusative / variant forms
    'липову долину':'липова долина','липову долина':'липова долина',
    'великий багачку':'велика багачка','велику багачу':'велика багачка','велику багачку':'велика багачка','велику багачка':'велика багачка',
    'улянівку':'улянівка','уляновку':'улянівка',
    # Велика Димерка падежные формы
    'велику димерку':'велика димерка','велика димерку':'велика димерка','великої димерки':'велика димерка','великій димерці':'велика димерка',
    # Велика Виска падежные формы
    'велику виску':'велика виска','великої виски':'велика виска','великій висці':'велика виска',
    # Мала дівиця
    'малу дівицю':'мала дівиця','мала дівицю':'мала дівиця',
    # Additional safety normalizations
    'олишівку':'олишівка','згурівку':'згурівка','ставищею':'ставище','кегичівку':'кегичівка','кегичевку':'кегичівка',
    # Voznesensk variants
    'вознесенська':'вознесенськ',
    # Mykolaiv variants
    'миколаєва':'миколаїв',
    'корабел':'корабельний район херсон',
    'корабельний':'корабельний район херсон',
    'корабельному':'корабельний район херсон',
    'корабельному херсоні':'корабельний район херсон',
    # Novoukrainka variants
    'новоукраїнку':'новоукраїнка',
    'старому салтову':'старий салтів','старому салтові':'старий салтів','карлівку':'карлівка','магдалинівку':'магдалинівка',
    'балаклію':'балаклія','білу церкву':'біла церква','баришівку':'баришівка','сквиру':'сквира','сосницю':'сосниця',
    'васильківку':'васильківка','понорницю':'понорниця','куликівку':'куликівка','терни':'терни',
    'шостку':'шостка','березну':'березна','зачепилівку':'зачепилівка','нову водолагу':'нова водолага',
    'нову':'нова водолага',  # Fallback for partial regex matches
    'убни':'лубни','олми':'холми','летичів':'летичів','летичев':'летичів','летичеве':'летичів','деражню':'деражня',
    'деражне':'деражня','деражні':'деражня','корюківку':'корюківка','борзну':'борзна','жмеринку':'жмеринка','лосинівку':'лосинівка',
    'ніжину':'ніжин','ніжина':'ніжин','межову':'межова','межової':'межова','святогірську':'святогірськ'
}

# Add accusative / genitive / variant forms for reported missing settlements
UA_CITY_NORMALIZE.update({
    'городню':'городня','городні':'городня','городне':'городня','городни':'городня',
    'кролевця':'кролевець','кролевцу':'кролевець','кролевце':'кролевець',
    'дубовʼязівку':'дубовʼязівка','дубовязівку':'дубовʼязівка','дубовязовку':'дубовʼязівка','дубовязовка':'дубовʼязівка',
    'батурина':'батурин','батурині':'батурин','батурином':'батурин'
    ,'бердичев':'бердичів','бердичева':'бердичів','бердичеве':'бердичів','бердичеву':'бердичів','бердичеві':'бердичів','бердичевом':'бердичів','бердичіву':'бердичів','бердичіва':'бердичів'
    ,'гостомеля':'гостомель','гостомелю':'гостомель','гостомелі':'гостомель','гостомель':'гостомель'
    ,'боярки':'боярка','боярку':'боярка','боярці':'боярка','боярка':'боярка'
    # Черниговская область - дополнительные формы
    ,'седнів':'седнів','седніву':'седнів','седніва':'седнів'
    ,'новгороду':'новгород','новгороді':'новгород','новгородом':'новгород'
    ,'мену':'мена','мені':'мена','меною':'мена'
    ,'макарова':'макарів','макарові':'макарів','макаров':'макарів','макарову':'макарів','макарів':'макарів'
    ,'бородянки':'бородянка','бородянку':'бородянка','бородянці':'бородянка','бородянка':'бородянка'
    ,'кілії':'кілія','кілію':'кілія','кілією':'кілія','кілія':'кілія'
    ,'ізмаїльського':'ізмаїльський','ізмаїльському':'ізмаїльський','ізмаїльський':'ізмаїльський'
    ,'броварського':'броварський','броварському':'броварський','броварський':'броварський'
    ,'обухівського':'обухівський','обухівському':'обухівський','обухівський':'обухівський'
    ,'херсонського':'херсонський','херсонському':'херсонський','херсонський':'херсонський'
    ,'вінницького':'вінницький','вінницькому':'вінницький','вінницький':'вінницький'
    ,'куцуруба':'куцуруб','воскресенку':'воскресенка','воскресенки':'воскресенка'
    # Цибулів (Черкаська обл.) падежные / вариантные формы
    ,'цибулева':'цибулів','цибулеві':'цибулів','цибулеву':'цибулів','цибулевом':'цибулів','цибулів':'цибулів'
    # New accusative / variants for UAV course parsing batch
    ,'борзну':'борзна','царичанку':'царичанка','андріївку':'андріївка','ямполь':'ямпіль','ямполя':'ямпіль','ямпіль':'ямпіль','димеру':'димер','чорнобилю':'чорнобиль'
    ,'дмитрівку':'дмитрівка','дмитрівку чернігівська':'дмитрівка','берестин':'берестин'
    ,'семенівку':'семенівка','глобине':'глобине','глобину':'глобине','глобиному':'глобине','глобина':'глобине'
    ,'кринички':'кринички','криничок':'кринички','солоне':'солоне','солоного':'солоне','солоному':'солоне'
    ,'краснопалівку':'краснопавлівка','краснопалівка':'краснопавлівка'
    ,'велику димерку':'велика димерка','великій димерці':'велика димерка','великої димерки':'велика димерка'
    ,'брусилів':'брусилів','брусилова':'брусилів','брусилові':'брусилів'
    # New cities from napramok messages September 2025
    ,'десну':'десна','кіпті':'кіпті','ічню':'ічня','цвіткове':'цвіткове'
    ,'чоповичі':'чоповичі','звягель':'звягель','сахновщину':'сахновщина'
    ,'камʼянське':'камʼянське','піщаний брід':'піщаний брід','бобринець':'бобринець'
    ,'тендрівську косу':'тендрівська коса'
    # Одеська область
    ,'вилково':'вилкове','вилкову':'вилкове'
    ,'черноморск':'чорноморськ','черноморское':'чорноморськ','черноморське':'чорноморськ'
    ,'чорноморське':'чорноморськ','чорноморске':'чорноморськ'
    # Common accusative forms for major cities
    ,'одесу':'одеса','полтаву':'полтава','сумами':'суми','суму':'суми'
})
# Apostrophe-less fallback for Sloviansk
UA_CITY_NORMALIZE['словянськ'] = "слов'янськ"

# Donetsk front city normalization (latin/ukr vowel variants)
UA_CITY_NORMALIZE['лиман'] = 'ліман'

# ---------------- Dynamic settlement name → region map (from city_ukraine.json, no coords there) ---------------
NAME_REGION_MAP = {}

def _load_name_region_map():
    global NAME_REGION_MAP
    if NAME_REGION_MAP:
        return
    path = 'city_ukraine.json'
    if not os.path.exists(path):
        return
    try:
        with open(path,encoding='utf-8') as f:
            data = json.load(f)
        added = 0
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get('object_name') or '').strip().lower()
            region = str(item.get('region') or '').strip().title()
            if not name or len(name) < 2:
                continue
            # Skip obviously generic words
            if name in NAME_REGION_MAP:
                continue
            NAME_REGION_MAP[name] = region
            added += 1
        log.info(f"Loaded NAME_REGION_MAP entries: {added}")
    except Exception as e:
        log.warning(f"Failed load city_ukraine.json names: {e}")

_load_name_region_map()

# Fix problematic entries in NAME_REGION_MAP that cause wrong city resolution
# Remove incomplete city names that point to wrong regions
PROBLEMATIC_ENTRIES = [
    'кривий',     # Should be 'кривий ріг' not just 'кривий' -> causes wrong region lookup
    'старий',     # Too generic, causes conflicts
    'нова',       # Too generic
    'велика',     # Too generic
    'мала',       # Too generic
    'білозерка',  # Conflicts with Херсонська область when message clearly specifies region
]

for entry in PROBLEMATIC_ENTRIES:
    NAME_REGION_MAP.pop(entry, None)


# =============================================================================
# TRAJECTORY PARSER - Parse various Ukrainian message formats for drone courses
# =============================================================================
# Supports formats like:
# - "БпЛА з півночі на Суми" (direction + target city)
# - "Група БпЛА на сході Миколаївщини курсом на Кіровоградщину" (region + direction + target)
# - "БпЛА з Херсонщини на Миколаївщину" (source region → target region)
# - "БпЛА курсом на м.Запоріжжя з північно-східного напрямку" (city target + direction)
# - "Харків: БпЛА на місто з північно-східного напрямку" (city prefix + direction)
# - "БпЛА на Дніпропетровщині, напрямок Синельникове" (region + target city)
# =============================================================================

# Direction mappings (Ukrainian → offset vector)
DIRECTION_VECTORS = {
    # Cardinal directions - all forms
    'північ': (-0.5, 0), 'півночі': (-0.5, 0), 'північн': (-0.5, 0), 'північний': (-0.5, 0),
    'південь': (0.5, 0), 'півдня': (0.5, 0), 'півд': (0.5, 0), 'південн': (0.5, 0), 'півдні': (0.5, 0), 'південний': (0.5, 0),
    'схід': (0, 0.5), 'сходу': (0, 0.5), 'східн': (0, 0.5), 'сході': (0, 0.5), 'східний': (0, 0.5),
    'захід': (0, -0.5), 'заходу': (0, -0.5), 'західн': (0, -0.5), 'заході': (0, -0.5), 'західний': (0, -0.5),
    # Intercardinal directions - all forms
    'північно-східн': (-0.35, 0.35), 'північний схід': (-0.35, 0.35), 'північного сходу': (-0.35, 0.35),
    'північно-східний': (-0.35, 0.35), 'північно-схід': (-0.35, 0.35),
    'північно-західн': (-0.35, -0.35), 'північний захід': (-0.35, -0.35), 'північного заходу': (-0.35, -0.35),
    'північно-західний': (-0.35, -0.35), 'північно-захід': (-0.35, -0.35),
    'південно-східн': (0.35, 0.35), 'південний схід': (0.35, 0.35), 'південного сходу': (0.35, 0.35),
    'південно-східний': (0.35, 0.35), 'південно-схід': (0.35, 0.35),
    'південно-західн': (0.35, -0.35), 'південний захід': (0.35, -0.35), 'південного заходу': (0.35, -0.35),
    'південно-західний': (0.35, -0.35), 'південно-захід': (0.35, -0.35),
}

# Direction keywords in messages (source direction - "з" pattern)
DIRECTION_FROM_KEYWORDS = [
    'з північно-східного напрямку', 'з північно-західного напрямку',
    'з південно-східного напрямку', 'з південно-західного напрямку',
    'з північного напрямку', 'з південного напрямку',
    'з східного напрямку', 'з західного напрямку',
    'з півночі', 'з півдня', 'з сходу', 'з заходу',
    'з північного сходу', 'з північного заходу',
    'з південного сходу', 'з південного заходу',
]

# Course keywords in messages (target direction - "курс" pattern)
DIRECTION_COURSE_KEYWORDS = [
    'курс північно-східний', 'курс північно-західний',
    'курс південно-східний', 'курс південно-західний',
    'курс північний', 'курс південний', 'курс східний', 'курс західний',
    'курсом на північ', 'курсом на південь', 'курсом на схід', 'курсом на захід',
]

def _get_direction_vector(direction_text):
    """Get lat/lng offset vector for a direction text"""
    direction_lower = direction_text.lower().strip()
    for key, vector in DIRECTION_VECTORS.items():
        if key in direction_lower:
            return vector
    return None

def _get_region_center(region_name):
    """Get center coordinates for a region (oblast)"""
    region_lower = region_name.lower().strip()
    # Check in OBLAST_CENTERS directly
    if region_lower in OBLAST_CENTERS:
        return OBLAST_CENTERS[region_lower]

    # Normalize instrumental case "над вінницькою областю" → "вінницька область"
    # Pattern: Xькою областю → Xька область
    instrumental_match = re.match(r'^(.+?)(ькою|ською|цькою)\s*(областю|обл\.?)$', region_lower)
    if instrumental_match:
        base = instrumental_match.group(1)
        # Convert back to nominative: ькою→ька, ською→ська, цькою→цька
        suffix_map = {'ькою': 'ька', 'ською': 'ська', 'цькою': 'цька'}
        new_suffix = suffix_map.get(instrumental_match.group(2), 'ька')
        normalized = f"{base}{new_suffix} область"
        if normalized in OBLAST_CENTERS:
            return OBLAST_CENTERS[normalized]
        # Try without ' область'
        normalized_short = f"{base}{new_suffix}"
        if normalized_short in OBLAST_CENTERS:
            return OBLAST_CENTERS[normalized_short]

    # Try removing common endings and searching again
    # Ukrainian oblast name endings: -щина/-щини/-щині/-щину, -ччина/-ччини/-ччині
    base_region = region_lower
    for ending in ['щині', 'щину', 'щини', 'щина', 'ччині', 'ччину', 'ччини', 'ччина']:
        if region_lower.endswith(ending):
            base_region = region_lower[:-len(ending)]
            break

    # Try to find with base + common endings
    for ending in ['щина', 'щини', 'ччина', 'ччини']:
        test_key = base_region + ending
        if test_key in OBLAST_CENTERS:
            return OBLAST_CENTERS[test_key]

    # Try partial match
    for key, coords in OBLAST_CENTERS.items():
        if base_region in key or key.startswith(base_region):
            return coords

    return None

def _get_city_coords(city_name, context=None):
    """Get coordinates for a city - uses ONLY OpenCage API"""
    if not city_name:
        return None
    return ensure_city_coords_with_message_context(city_name, context)

def _ai_trajectory_to_coords(ai_result):
    """Convert AI trajectory result to coordinates.

    Takes AI result with source_type, source_name, target_type, target_name
    and returns trajectory dict with start/end coordinates.
    """
    if not ai_result:
        return None

    source_type = ai_result.get('source_type')
    source_name = ai_result.get('source_name')
    target_type = ai_result.get('target_type')
    target_name = ai_result.get('target_name')
    source_position = ai_result.get('source_position')  # e.g. "схід" for "на сході Сумщини"

    # Get target coordinates
    end_coords = None
    if target_type == 'city' and target_name:
        end_coords = _get_city_coords(target_name)
    elif target_type == 'region' and target_name:
        end_coords = _get_region_center(target_name)
    elif target_type == 'direction' and target_name:
        # Direction only - need source to calculate end
        pass

    # Get source coordinates
    start_coords = None
    if source_type == 'city' and source_name:
        start_coords = _get_city_coords(source_name)
    elif source_type == 'region' and source_name:
        start_coords = _get_region_center(source_name)
        # Apply position offset if specified (e.g. "на сході Сумщини")
        if start_coords and source_position:
            pos_vec = _get_direction_vector(source_position)
            if pos_vec:
                start_coords = (start_coords[0] + pos_vec[0] * 0.3, start_coords[1] + pos_vec[1] * 0.3)
    elif source_type == 'direction' and source_name:
        # Direction source - calculate from target
        if end_coords:
            dir_vec = _get_direction_vector(source_name)
            if dir_vec:
                # Invert direction to get source position
                start_coords = (end_coords[0] - dir_vec[0], end_coords[1] - dir_vec[1])

    # Handle target direction (when target is a direction like "курс південний")
    if target_type == 'direction' and target_name and start_coords and not end_coords:
        dir_vec = _get_direction_vector(target_name)
        if dir_vec:
            end_coords = (start_coords[0] + dir_vec[0] * 0.5, start_coords[1] + dir_vec[1] * 0.5)

    # =========================================================================
    # AI ROUTE PREDICTION: If we have source but no target, use AI to predict
    # MAX DISTANCE: 300 km (only neighboring regions) - prevents Kharkiv->Lutsk errors
    # =========================================================================
    MAX_PREDICTION_DISTANCE_KM = 300  # ~neighboring oblast

    if start_coords and not end_coords and GROQ_ENABLED:
        try:
            prediction = predict_route_with_ai(source_name or '')
            if prediction and prediction.get('confidence', 0) >= 0.6:
                predicted_targets = prediction.get('predicted_targets', [])
                if predicted_targets:
                    # Try each predicted target, use first within distance limit
                    for target in predicted_targets:
                        predicted_coords = _get_region_center(target) or _get_city_coords(target)
                        if predicted_coords:
                            # Calculate distance between start and predicted end
                            from math import atan2, cos, radians, sin, sqrt
                            lat1, lon1 = radians(start_coords[0]), radians(start_coords[1])
                            lat2, lon2 = radians(predicted_coords[0]), radians(predicted_coords[1])
                            dlat, dlon = lat2 - lat1, lon2 - lon1
                            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                            distance_km = 6371 * 2 * atan2(sqrt(a), sqrt(1-a))

                            if distance_km <= MAX_PREDICTION_DISTANCE_KM:
                                end_coords = predicted_coords
                                target_name = target + ' (прогноз)'
                                print(f"DEBUG AI Route Prediction used: {source_name} -> {target} ({distance_km:.0f}km, conf={prediction.get('confidence')})")
                                break
                            else:
                                print(f"DEBUG AI Route Prediction REJECTED (too far): {source_name} -> {target} ({distance_km:.0f}km > {MAX_PREDICTION_DISTANCE_KM}km)")
        except Exception as e:
            print(f"DEBUG: AI route prediction failed: {e}")

    # Need both start and end to create trajectory
    if not start_coords or not end_coords:
        return None

    return {
        'start': [start_coords[0], start_coords[1]],
        'end': [end_coords[0], end_coords[1]],
        'source_name': source_name or 'unknown',
        'target_name': target_name or 'unknown',
        'kind': f'ai_{source_type}_to_{target_type}',
        'predicted': end_coords and '(прогноз)' in (target_name or '')
    }

def parse_trajectory_from_message(text):
    """
    Parse trajectory info from Ukrainian drone movement messages.

    Uses AI (Groq) when available for intelligent parsing, with regex fallback.

    Returns dict with:
        - start: [lat, lng] - source coordinates
        - end: [lat, lng] - target coordinates
        - source_name: str - source location name
        - target_name: str - target location name
        - kind: str - type of trajectory match
    Or None if no trajectory pattern found.
    """
    import re
    if not text:
        return None

    # ==========================================================================
    # TRY AI FIRST (if enabled) - much smarter than regex
    # ==========================================================================
    if GROQ_ENABLED:
        try:
            ai_result = extract_trajectory_with_ai(text)
            if ai_result and ai_result.get('confidence', 0) >= 0.7:
                trajectory = _ai_trajectory_to_coords(ai_result)
                if trajectory:
                    print(f"DEBUG: AI trajectory parsed successfully: {trajectory.get('kind')}")
                    return trajectory
        except Exception as e:
            print(f"DEBUG: AI trajectory failed, falling back to regex: {e}")

    # ==========================================================================
    # FALLBACK TO REGEX PATTERNS
    # ==========================================================================
    text_lower = text.lower()
    # Remove emoji prefixes for pattern matching
    text_clean = re.sub(r'^[^\w\s]*\s*', '', text_lower)

    # =========================================================================
    # Pattern 1: "БпЛА з [напрямок] на [місто]"
    # Example: "БпЛА з півночі на Суми"
    # =========================================================================
    p1 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+(півноч[іи]|півдн[яю]|сход[уі]|заход[уі]|північн\w*[\s-]*схо\w*|північн\w*[\s-]*захо\w*|південн\w*[\s-]*схо\w*|південн\w*[\s-]*захо\w*)\s+на\s+([а-яіїєґ\'\-]+)', text_lower)
    if p1:
        direction_text = p1.group(1)
        target_city = p1.group(2)

        target_coords = _get_city_coords(target_city)
        if target_coords:
            direction_vec = _get_direction_vector(direction_text)
            if direction_vec:
                # Invert direction to get source (from direction -> opposite)
                start_lat = target_coords[0] - direction_vec[0]
                start_lng = target_coords[1] - direction_vec[1]
                return {
                    'start': [start_lat, start_lng],
                    'end': [target_coords[0], target_coords[1]],
                    'source_name': f'з {direction_text}',
                    'target_name': target_city.title(),
                    'kind': 'direction_to_city'
                }

    # =========================================================================
    # Pattern 2: "БпЛА з [регіон] на [регіон]"
    # Example: "БпЛА з Херсонщини на Миколаївщину"
    # =========================================================================
    p2 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+([а-яіїєґ]+(щин|ччин)[ауиіи])\s+на\s+([а-яіїєґ]+(щин|ччин)[ауиію])', text_lower)
    if p2:
        source_region = p2.group(1)
        target_region = p2.group(3)

        source_coords = _get_region_center(source_region)
        target_coords = _get_region_center(target_region)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': target_region.title(),
                'kind': 'region_to_region'
            }

    # =========================================================================
    # Pattern 2a: "БпЛА з [регіон] курсом на [регіон], напрямок [місто/міста]"
    # Example: "БпЛА з Київщини курсом на Житомирщину, напрямок Коростень/Овруч"
    # =========================================================================
    p2a = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+([а-яіїєґ]+(щин|ччин)[иіау])\s+курсом\s+на\s+([а-яіїєґ]+(щин|ччин)[у|ю])[,\s]+(?:напрямок|напрям)\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-/]+)', text_lower)
    if p2a:
        source_region = p2a.group(1)
        target_region = p2a.group(3)
        target_cities = p2a.group(5)  # May contain multiple cities like "Коростень/Овруч"

        source_coords = _get_region_center(source_region)
        # Try to get coords for the first city mentioned
        first_city = target_cities.split('/')[0].split(',')[0].strip()
        target_coords = _get_city_coords(first_city)

        # Fallback to region center if city not found
        if not target_coords:
            target_coords = _get_region_center(target_region)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': target_cities.title(),
                'kind': 'region_course_to_city'
            }

    # =========================================================================
    # Pattern 2b: "БпЛА з [регіон] курсом на [регіон]" (без напрямку)
    # Example: "БпЛА з Київщини курсом на Житомирщину"
    # =========================================================================
    p2b = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+([а-яіїєґ]+(щин|ччин)[иіау])\s+курсом\s+на\s+([а-яіїєґ]+(щин|ччин)[уюі])', text_lower)
    if p2b:
        source_region = p2b.group(1)
        target_region = p2b.group(3)

        source_coords = _get_region_center(source_region)
        target_coords = _get_region_center(target_region)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': target_region.title(),
                'kind': 'region_course_to_region'
            }

    # =========================================================================
    # Pattern 3: "БпЛА на [напрямок] [регіон] курсом на [регіон]"
    # Example: "Група БпЛА на сході Миколаївщини курсом на Кіровоградщину"
    # =========================================================================
    p3 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+(півноч[іи]|півдн[іи]|сход[іиі]|заход[іиі]|північн\w*[\s-]*схо\w*|північн\w*[\s-]*захо\w*|південн\w*[\s-]*схо\w*|південн\w*[\s-]*захо\w*)\s+([а-яіїєґ]+(щин|ччин)[иі])\s+курсом\s+на\s+([а-яіїєґ]+(щин|ччин)[ауиію])', text_lower)
    if p3:
        direction_in_region = p3.group(1)
        source_region = p3.group(2)
        target_region = p3.group(4)

        source_coords = _get_region_center(source_region)
        target_coords = _get_region_center(target_region)

        if source_coords and target_coords:
            # Offset source by direction within the region
            direction_vec = _get_direction_vector(direction_in_region)
            if direction_vec:
                start_lat = source_coords[0] + direction_vec[0] * 0.3
                start_lng = source_coords[1] + direction_vec[1] * 0.3
            else:
                start_lat, start_lng = source_coords

            return {
                'start': [start_lat, start_lng],
                'end': [target_coords[0], target_coords[1]],
                'source_name': f'{direction_in_region} {source_region}'.title(),
                'target_name': target_region.title(),
                'kind': 'region_direction_to_region'
            }

    # =========================================================================
    # Pattern 4: "БпЛА курсом на м.[місто] з [напрямок] напрямку"
    # Example: "БпЛА курсом на м.Запоріжжя з північно-східного напрямку"
    # =========================================================================
    p4 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+курсом\s+на\s+(?:м\.?|місто\s+)?([а-яіїєґ\'\-]+)\s+з\s+(північн\w*[\s-]*схід\w*|північн\w*[\s-]*захід\w*|південн\w*[\s-]*схід\w*|південн\w*[\s-]*захід\w*|північн\w*|південн\w*|східн\w*|західн\w*)\s*напрямку', text_lower)
    if p4:
        target_city = p4.group(1)
        direction_text = p4.group(2)

        target_coords = _get_city_coords(target_city)
        if target_coords:
            direction_vec = _get_direction_vector(direction_text)
            if direction_vec:
                start_lat = target_coords[0] - direction_vec[0]
                start_lng = target_coords[1] - direction_vec[1]
                return {
                    'start': [start_lat, start_lng],
                    'end': [target_coords[0], target_coords[1]],
                    'source_name': f'з {direction_text} напрямку',
                    'target_name': target_city.title(),
                    'kind': 'city_from_direction'
                }

    # =========================================================================
    # Pattern 5: "[Місто]: БпЛА на місто з [напрямок] напрямку"
    # Example: "🛵 Харків: БпЛА на місто з північно-східного напрямку"
    # =========================================================================
    p5 = re.search(r'([а-яіїєґ\'\-]+)\s*:\s*(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+місто\s+з\s+(північн\w*[\s-]*схід\w*|північн\w*[\s-]*захід\w*|південн\w*[\s-]*схід\w*|південн\w*[\s-]*захід\w*|північн\w*|південн\w*|східн\w*|західн\w*)\s*напрямку', text_clean)
    if p5:
        target_city = p5.group(1)
        direction_text = p5.group(2)

        target_coords = _get_city_coords(target_city)
        if target_coords:
            direction_vec = _get_direction_vector(direction_text)
            if direction_vec:
                start_lat = target_coords[0] - direction_vec[0]
                start_lng = target_coords[1] - direction_vec[1]
                return {
                    'start': [start_lat, start_lng],
                    'end': [target_coords[0], target_coords[1]],
                    'source_name': f'з {direction_text}',
                    'target_name': target_city.title(),
                    'kind': 'city_prefix_direction'
                }

    # =========================================================================
    # Pattern 6: "[Місто]: БпЛА з [напрямок]"
    # Example: "🛵 Харків: БпЛА з півночі"
    # =========================================================================
    p6 = re.search(r'([а-яіїєґ\'\-]+)\s*:\s*(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+(півноч[іи]|півдн[яю]|сход[уі]|заход[уі]|північн\w*[\s-]*схо\w*|північн\w*[\s-]*захо\w*|південн\w*[\s-]*схо\w*|південн\w*[\s-]*захо\w*)', text_clean)
    if p6:
        target_city = p6.group(1)
        direction_text = p6.group(2)

        target_coords = _get_city_coords(target_city)
        if target_coords:
            direction_vec = _get_direction_vector(direction_text)
            if direction_vec:
                start_lat = target_coords[0] - direction_vec[0]
                start_lng = target_coords[1] - direction_vec[1]
                return {
                    'start': [start_lat, start_lng],
                    'end': [target_coords[0], target_coords[1]],
                    'source_name': f'з {direction_text}',
                    'target_name': target_city.title(),
                    'kind': 'city_prefix_from'
                }

    # =========================================================================
    # Pattern 7: "БпЛА на [регіон], напрямок/курс на [місто]"
    # Example: "БпЛА на Дніпропетровщині, напрямок Синельникове"
    # Example: "Група БпЛА на Одещині, курс на н.п. Кілія"
    # =========================================================================
    p7 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+([а-яіїєґ]+(щин|ччин)[іиї])[,.\s]+(?:напрямок|напрям|у напрямку|в напрямку|курс на|курс)\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-\s]+?)(?:\.|$)', text_lower)
    if p7:
        source_region = p7.group(1)
        target_city = p7.group(3).strip()

        source_coords = _get_region_center(source_region)
        target_coords = _get_city_coords(target_city)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': target_city.title(),
                'kind': 'region_to_city'
            }

    # =========================================================================
    # Pattern 7b: "БпЛА над [регіон] курсом на [напрямок]"
    # Example: "🛵 Шахед над Вінницькою областю курсом на північ"
    # =========================================================================
    p7b = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+(?:над|на)\s+([а-яіїєґ]+(?:ою|ій)\s+област[іиюь]|[а-яіїєґ]+(щин|ччин)[іиою])\s*,?\s*курсом?\s+на\s+(північ|південь|схід|захід|північний[\s-]*схід|північний[\s-]*захід|південний[\s-]*схід|південний[\s-]*захід)', text_lower)
    if p7b:
        source_region = p7b.group(1)
        direction = p7b.group(3)

        source_coords = _get_region_center(source_region)
        if source_coords:
            direction_vec = _get_direction_vector(direction)
            if direction_vec:
                end_lat = source_coords[0] + direction_vec[0] * 0.5
                end_lng = source_coords[1] + direction_vec[1] * 0.5
                return {
                    'start': [source_coords[0], source_coords[1]],
                    'end': [end_lat, end_lng],
                    'source_name': source_region.title(),
                    'target_name': f'курс на {direction}',
                    'kind': 'region_course_direction'
                }

    # =========================================================================
    # Pattern 7c: "Група БпЛА на [регіон] в напрямку [місто]"
    # Example: "🛵 Група БпЛА на Одещині в напрямку Миколаєва"
    # =========================================================================
    p7c = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+(?:на|над)\s+([а-яіїєґ]+(щин|ччин)[іиї])\s*,?\s*(?:в|у)\s+напрямку\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)', text_lower)
    if p7c:
        source_region = p7c.group(1)
        target_city = p7c.group(3).strip()

        source_coords = _get_region_center(source_region)
        target_coords = _get_city_coords(target_city)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': target_city.title(),
                'kind': 'region_towards_city_v2'
            }

    # =========================================================================
    # Pattern 7a: "БпЛА з акваторії [море] на [регіон], курс на [місто]"
    # Example: "Група БпЛА з акваторії Чорного моря на Одещині. курс на Старі Трояни."
    # =========================================================================
    p7a = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+акваторії\s+([а-яіїєґ\'\-\s]+моря)\s+на\s+([а-яіїєґ]+(щин|ччин)[іиї])[,.\s]+курс\s+(?:на\s+)?(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-\s]+?)(?:\.|$)', text_lower)
    if p7a:
        sea_name = p7a.group(1)
        region = p7a.group(2)
        target_city = p7a.group(4).strip()

        # Coordinates for seas (approximate entry points to Ukraine)
        sea_coords = {
            'чорного моря': (45.5, 31.5),  # Black Sea south of Odesa
            'азовського моря': (46.5, 36.5),  # Azov Sea
        }

        source_coords = sea_coords.get(sea_name, (45.5, 31.5))  # Default to Black Sea
        target_coords = _get_city_coords(target_city)

        # Fallback to region center if city not found
        if not target_coords:
            target_coords = _get_region_center(region)

        if target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': sea_name.title(),
                'target_name': target_city.title(),
                'kind': 'sea_to_city'
            }

    # =========================================================================
    # Pattern 8: "БпЛА на [напрямок] [регіон]" (position only, no course)
    # Example: "БпЛА на півдні Миколаївщини"
    # Note: This is just a position, not a full trajectory
    # =========================================================================
    p8 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+(півноч[іи]|півдн[іи]|сход[іи]|заход[іи]|північн\w*[\s-]*схо\w*|північн\w*[\s-]*захо\w*|південн\w*[\s-]*схо\w*|південн\w*[\s-]*захо\w*)\s+([а-яіїєґ]+(щин|ччин)[иі])', text_lower)
    if p8:
        direction_in_region = p8.group(1)
        region = p8.group(2)

        # Check if there's a course direction mentioned later in the text
        # Put compound directions FIRST to match them before simple ones
        course_match = re.search(r'курс\s+(північн\w*-?схід\w*|північн\w*-?захід\w*|південн\w*-?схід\w*|південн\w*-?захід\w*|північн\w*|південн\w*|східн\w*|західн\w*)', text_lower)

        source_coords = _get_region_center(region)
        if source_coords:
            direction_vec = _get_direction_vector(direction_in_region)
            if direction_vec:
                start_lat = source_coords[0] + direction_vec[0] * 0.3
                start_lng = source_coords[1] + direction_vec[1] * 0.3

                if course_match:
                    course_direction = course_match.group(1)
                    course_vec = _get_direction_vector(course_direction)
                    if course_vec:
                        end_lat = start_lat + course_vec[0] * 0.5
                        end_lng = start_lng + course_vec[1] * 0.5
                        return {
                            'start': [start_lat, start_lng],
                            'end': [end_lat, end_lng],
                            'source_name': f'{direction_in_region} {region}'.title(),
                            'target_name': f'курс {course_direction}',
                            'kind': 'region_position_with_course'
                        }

    # =========================================================================
    # Pattern 9: "БпЛА на [регіон], повз м.[місто] курсом на [регіон]"
    # Example: "БпЛА на Миколаївщині, повз М.Миколаїв курсом на Одещину"
    # =========================================================================
    p9 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+([а-яіїєґ]+(щин|ччин)[іиї])[,\s]+повз\s+(?:м\.?|місто\s+)?([а-яіїєґ\'\-]+)\s+курсом\s+на\s+([а-яіїєґ]+(щин|ччин)[ауиію])', text_lower)
    if p9:
        source_region = p9.group(1)
        via_city = p9.group(3)
        target_region = p9.group(4)

        via_coords = _get_city_coords(via_city)
        target_coords = _get_region_center(target_region)

        if via_coords and target_coords:
            return {
                'start': [via_coords[0], via_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': f'{via_city} ({source_region})'.title(),
                'target_name': target_region.title(),
                'kind': 'via_city_to_region'
            }

    # =========================================================================
    # Pattern 10: "БпЛА з [регіон] на [регіон], напрямок м.[місто]"
    # Example: "БпЛА з Херсонщини на Миколаївщину, напрямок м.Миколаїв"
    # =========================================================================
    p10 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+з\s+([а-яіїєґ]+(щин|ччин)[иі])\s+на\s+([а-яіїєґ]+(щин|ччин)[ауиію])[,\s]+(?:напрямок|напрям)\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)', text_lower)
    if p10:
        source_region = p10.group(1)
        mid_region = p10.group(3)
        target_city = p10.group(5)

        source_coords = _get_region_center(source_region)
        target_coords = _get_city_coords(target_city)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],
                'end': [target_coords[0], target_coords[1]],
                'source_name': source_region.title(),
                'target_name': f'{target_city} ({mid_region})'.title(),
                'kind': 'region_via_region_to_city'
            }

    # =========================================================================
    # Pattern 11: "БпЛА на [напрямок] [регіон], напрямок н.п.[місто]"
    # Example: "БпЛА на сході Сумщини, напрямок н.п.Лебедин"
    # =========================================================================
    p11 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+(півноч[іи]|півдн[іи]|сход[іи]|заход[іи]|північн\w*[\s-]*схо\w*|північн\w*[\s-]*захо\w*|південн\w*[\s-]*схо\w*|південн\w*[\s-]*захо\w*)\s+([а-яіїєґ]+(щин|ччин)[иі])[,\s]+(?:напрямок|напрям)\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)', text_lower)
    if p11:
        direction_in_region = p11.group(1)
        source_region = p11.group(2)
        target_city = p11.group(4)

        source_coords = _get_region_center(source_region)
        target_coords = _get_city_coords(target_city)

        if source_coords and target_coords:
            direction_vec = _get_direction_vector(direction_in_region)
            if direction_vec:
                start_lat = source_coords[0] + direction_vec[0] * 0.3
                start_lng = source_coords[1] + direction_vec[1] * 0.3
            else:
                start_lat, start_lng = source_coords

            return {
                'start': [start_lat, start_lng],
                'end': [target_coords[0], target_coords[1]],
                'source_name': f'{direction_in_region} {source_region}'.title(),
                'target_name': target_city.title(),
                'kind': 'region_position_to_city'
            }

    # =========================================================================
    # Pattern 12: "БпЛА на межі [регіон1] та [регіон2] областей, курс [напрямок]"
    # Example: "БпЛА на межі Сумської та Чернігівської областей,курс південний"
    # =========================================================================
    p12 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+на\s+меж[іи]\s+([а-яіїєґ]+)\w*\s+(?:та|і|й)\s+([а-яіїєґ]+)\w*\s+(?:областей|обл)[,\s]*курс\s+(північн\w*|південн\w*|східн\w*|західн\w*|північн\w*[\s-]*схід\w*|північн\w*[\s-]*захід\w*|південн\w*[\s-]*схід\w*|південн\w*[\s-]*захід\w*)', text_lower)
    if p12:
        region1_base = p12.group(1)
        region2_base = p12.group(2)
        course_direction = p12.group(3)

        # Try to find both regions
        region1_coords = None
        region2_coords = None

        for key, coords in OBLAST_CENTERS.items():
            if region1_base in key:
                region1_coords = coords
            if region2_base in key:
                region2_coords = coords

        if region1_coords and region2_coords:
            # Start at midpoint between regions
            start_lat = (region1_coords[0] + region2_coords[0]) / 2
            start_lng = (region1_coords[1] + region2_coords[1]) / 2

            course_vec = _get_direction_vector(course_direction)
            if course_vec:
                end_lat = start_lat + course_vec[0] * 0.5
                end_lng = start_lng + course_vec[1] * 0.5
                return {
                    'start': [start_lat, start_lng],
                    'end': [end_lat, end_lng],
                    'source_name': f'межа {region1_base}/{region2_base}',
                    'target_name': f'курс {course_direction}',
                    'kind': 'border_with_course'
                }

    # =========================================================================
    # Pattern 13: "БпЛА в напрямку м.[місто]"
    # Example: "БпЛА на Дніпропетровщині в напрямку м.Павлоград"
    # =========================================================================
    p13 = re.search(r'(?:бпла|шахед|дрон|група\s+бпла)\s+(?:на\s+)?([а-яіїєґ]+(щин|ччин)[іи])?\s*(?:в|у)\s+напрямку\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)', text_lower)
    if p13:
        source_region = p13.group(1) if p13.group(1) else None
        target_city = p13.group(3)

        target_coords = _get_city_coords(target_city)

        if target_coords:
            if source_region:
                source_coords = _get_region_center(source_region)
                if source_coords:
                    return {
                        'start': [source_coords[0], source_coords[1]],
                        'end': [target_coords[0], target_coords[1]],
                        'source_name': source_region.title(),
                        'target_name': target_city.title(),
                        'kind': 'region_towards_city'
                    }

    # =========================================================================
    # Pattern 14: "БпЛА [місто] курсом на [місто]"
    # Example: "БпЛА Боромля курсом на Тростянець"
    # CRITICAL: Marker should be at SOURCE city (where drone IS), NOT at target!
    # =========================================================================
    p14 = re.search(r'(?:група\s+)?(?:бпла|шахед|дрон)\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)\s+курсом\s+на\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-]+)', text_lower)
    if p14:
        source_city = p14.group(1)
        target_city = p14.group(2)

        source_coords = _get_city_coords(source_city)
        target_coords = _get_city_coords(target_city)

        if source_coords and target_coords:
            return {
                'start': [source_coords[0], source_coords[1]],  # SOURCE - current position
                'end': [target_coords[0], target_coords[1]],    # TARGET - where going
                'source_name': source_city.title(),
                'target_name': target_city.title(),
                'kind': 'city_course_to_city'
            }

    # =========================================================================
    # Pattern 15: "БпЛА [місто] ([область])" - Simple city with region
    # Example: "БПЛА Кривий Ріг (Дніпропетровська обл.)"
    # =========================================================================
    p15 = re.search(r'(?:бпла|шахед|дрон)и?\s+(?:м\.?|н\.?п\.?)?\s*([а-яіїєґ\'\-\s]{3,30}?)\s*\([^)]*(?:обл|область|щина)[^)]*\)', text_lower)
    if p15:
        city = p15.group(1).strip()
        city_coords = _get_city_coords(city)
        if city_coords:
            return {
                'start': [city_coords[0], city_coords[1]],
                'end': None,
                'source_name': city.title(),
                'target_name': None,
                'kind': 'city_position'
            }

    return None

def process_message(text, mid, date_str, channel, _disable_multiline=False):  # type: ignore
    import re

    # Helper function to clean text from subscription prompts
    def clean_text(text_to_clean):
        if not text_to_clean:
            return text_to_clean
        import re as re_import
        cleaned = []
        for ln in text_to_clean.splitlines():
            ln2 = ln.strip()
            if not ln2:
                continue
            # Remove invisible/unicode spaces and normalize
            ln2 = re_import.sub(r'[\u200B-\u200D\uFEFF\u3164\u2060\u00A0\u1680\u180E\u2000-\u200F\u202A-\u202E\u2028\u2029\u205F\u3000]+', ' ', ln2)
            ln2 = ln2.strip()

            # Check if line ends with subscription text after meaningful content (including bold **text**)
            subscription_match = re_import.search(r'^(.+?)\s+[➡→>⬇⬆⬅⬌↗↘↙↖]\s*(\*\*)?підписатися(\*\*)?\s*$', ln2, re_import.IGNORECASE)
            if subscription_match:
                # Extract the part before the subscription text
                main_content = subscription_match.group(1).strip()
                if main_content and len(main_content) > 5:  # Only keep if meaningful content
                    cleaned.append(main_content)
                continue

            # remove any line that is ONLY a subscribe CTA (including bold)
            if re_import.search(r'^[➡→>⬇⬆⬅⬌↗↘↙↖]?\s*(\*\*)?підписатися(\*\*)?\s*$', ln2, re_import.IGNORECASE):
                continue

            # Remove URLs and links from text
            ln2 = re_import.sub(r'https?://[^\s]+', '', ln2)  # Remove http/https links
            ln2 = re_import.sub(r'www\.[^\s]+', '', ln2)      # Remove www links
            ln2 = re_import.sub(r't\.me/[^\s]+', '', ln2)     # Remove Telegram links
            ln2 = re_import.sub(r'@[a-zA-Z0-9_]+', '', ln2)  # Remove @mentions
            ln2 = re_import.sub(r'_+', '', ln2)  # Remove leftover underscores
            ln2 = re_import.sub(r'[✙✚]+[^✙✚]*✙[^✙✚]*✙', '', ln2)  # Remove ✙...✙ patterns

            # Remove card numbers and bank details
            ln2 = re_import.sub(r'\d{4}\s*\d{4}\s*\d{4}\s*\d{4}', '', ln2)  # Card numbers
            ln2 = re_import.sub(r'[—-]\s*Картка:', '', ln2)  # Card labels
            ln2 = re_import.sub(r'[—-]\s*Банка:', '', ln2)   # Bank labels
            ln2 = re_import.sub(r'[—-]\s*Конверт:', '', ln2) # Envelope labels

            # Clean up multiple spaces and trim
            ln2 = re_import.sub(r'\s+', ' ', ln2).strip()

            # Skip empty lines after cleaning
            if not ln2:
                continue

            cleaned.append(ln2)
        return '\n'.join(cleaned)

    # PRIORITY: Check for trajectory patterns FIRST using the comprehensive parser
    trajectory_data = parse_trajectory_from_message(text)
    if trajectory_data:
        print(f"DEBUG: Trajectory parsed - kind={trajectory_data.get('kind')}, source={trajectory_data.get('source_name')}, target={trajectory_data.get('target_name')}")

        # IMPORTANT: Marker should be at SOURCE (current position), NOT at target!
        # The drone is at source and flying TOWARDS target
        source_coords = trajectory_data['start']
        target_coords = trajectory_data['end']

        # Classify threat type based on message text
        text_lower = text.lower()
        if 'шахед' in text_lower or 'shahed' in text_lower:
            threat_type, icon = 'shahed', 'shahed3.webp'
        elif 'бпла' in text_lower or 'дрон' in text_lower:
            threat_type, icon = 'shahed', 'shahed3.webp'
        elif 'ракет' in text_lower:
            threat_type, icon = 'raketa', 'icon_balistic.svg'
        else:
            threat_type, icon = 'shahed', 'shahed3.webp'

        # =====================================================================
        # ENHANCED AI PREDICTION: Add ETA, multi-targets, confidence
        # DISABLED - function not implemented
        # =====================================================================
        # enhanced_trajectory = get_enhanced_trajectory_prediction(trajectory_data, text)
        # if enhanced_trajectory:
        #     trajectory_data = enhanced_trajectory
        #     # Update icon based on refined threat type
        #     if enhanced_trajectory.get('threat_type') == 'ballistic':
        #         icon = 'icon_balistic.svg'
        #     elif enhanced_trajectory.get('threat_type') == 'cruise':
        #         icon = 'icon_rocket.svg'

        # Place name shows direction: Source → Target
        place_name = f"{trajectory_data.get('source_name', 'Джерело')} → {trajectory_data.get('target_name', 'Ціль')}"

        # ETA in place name - DISABLED
        # eta_info = trajectory_data.get('eta', {})
        # if eta_info.get('formatted'):
        #     place_name += f" (ETA: {eta_info['formatted']})"

        trajectory_marker = {
            'id': str(mid),
            'place': place_name,
            'lat': source_coords[0],  # MARKER AT SOURCE (current position)
            'lng': source_coords[1],  # NOT at target!
            'threat_type': threat_type,
            'text': text[:500],
            'date': date_str,
            'channel': channel,
            'marker_icon': icon,
            'source_match': f'trajectory_{trajectory_data.get("kind", "unknown")}',
            'trajectory': trajectory_data
        }

        # Add enhanced prediction data
        if trajectory_data.get('eta'):
            trajectory_marker['eta'] = trajectory_data['eta']
        if trajectory_data.get('alternative_targets'):
            trajectory_marker['alternative_targets'] = trajectory_data['alternative_targets']
        if trajectory_data.get('confidence'):
            trajectory_marker['prediction_confidence'] = trajectory_data['confidence']
        if trajectory_data.get('confidence_level'):
            trajectory_marker['confidence_level'] = trajectory_data['confidence_level']
        if trajectory_data.get('distance_km'):
            trajectory_marker['distance_km'] = trajectory_data['distance_km']
        if trajectory_data.get('speed_kmh'):
            trajectory_marker['speed_kmh'] = trajectory_data['speed_kmh']

        # AUTO-RECORD: Save observed route for pattern learning (non-blocking)
        try:
            if not trajectory_data.get('predicted'):  # Only record confirmed routes
                update_route_pattern_with_ai({
                    'source_region': trajectory_data.get('source_name'),
                    'target_region': trajectory_data.get('target_name'),
                    'waypoints': [],
                    'threat_type': threat_type
                })
        except Exception as e:
            print(f"DEBUG: Failed to record route pattern: {e}")

        return [trajectory_marker]

    # EARLY FILTERS: Check for messages that should be completely filtered out
    def _is_russian_strategic_aviation(t: str) -> bool:
        """Suppress messages about Russian strategic aviation (Tu-95, etc.) from Russian airbases"""
        t_lower = t.lower()

        # Check for Russian strategic bombers
        russian_bombers = ['ту-95', 'tu-95', 'ту-160', 'tu-160', 'ту-22', 'tu-22']
        has_bomber = any(bomber in t_lower for bomber in russian_bombers)

        # Check for Russian airbases and regions
        russian_airbases = ['енгельс', 'engels', 'энгельс', 'саратов', 'рязань', 'муром', 'украінка', 'українка']
        has_russian_airbase = any(airbase in t_lower for airbase in russian_airbases)

        # Check for Russian regions/areas
        russian_regions = ['саратовській області', 'саратовской области', 'тульській області', 'рязанській області']
        has_russian_region = any(region in t_lower for region in russian_regions)

        # Check for terms indicating Russian territory/airbases
        russian_territory_terms = ['аеродрома', 'аэродрома', 'з аеродрому', 'с аэродрома', 'мета вильоту невідома', 'цель вылета неизвестна']
        has_russian_territory = any(term in t_lower for term in russian_territory_terms)

        # Check for generic relocation/transfer terms without specific threats
        relocation_terms = ['передислокація', 'передислокация', 'переліт', 'перелет', 'відмічено', 'отмечено']
        has_relocation = any(term in t_lower for term in relocation_terms)

        # Suppress if it's about Russian bombers from Russian territory
        if has_bomber and (has_russian_airbase or has_russian_territory or has_russian_region):
            return True

        # Suppress relocation/transfer messages between Russian airbases
        if has_relocation and has_bomber and (has_russian_airbase or has_russian_region):
            return True

        # Also suppress general strategic aviation reports without specific Ukrainian targets
        if ('борт' in t_lower or 'борти' in t_lower) and ('мета вильоту невідома' in t_lower or 'цель вылета неизвестна' in t_lower):
            return True

        return False

    def _is_general_warning_without_location(t: str) -> bool:
        """Suppress general warnings without specific locations or threat details"""
        t_lower = t.lower()

        # Check for general warning phrases
        warning_phrases = [
            'протягом ночі уважним бути',
            'протягом дня уважним бути',
            'уважним бути',
            'загальне попередження',
            'общее предупреждение'
        ]
        has_general_warning = any(phrase in t_lower for phrase in warning_phrases)

        # Check for alert messages that should only be in events, not on map
        alert_phrases = [
            'відбій тривоги',
            'повітряна тривога',
            'відбой тревоги',
            'воздушная тревога'
        ]
        has_alert_message = any(phrase in t_lower for phrase in alert_phrases)

        # Suppress alert messages - they should only be in events
        if has_alert_message:
            return True

        # Check for tactical threat messages first - these should NEVER be filtered
        tactical_phrases = [
            'бпла',
            'крилаті ракети',
            'ракет',
            'ракета',
            'ракети',
            'загроза',
            'курсом на',
            'наближається',
            'повз',
            'поблизу',
            'напрямок',
            'напрямку',
            'у напрямку',
            'кв шахед',
            'шахед',
            'каб',
            'умп',
            'іскандер'
        ]
        has_tactical_info = any(phrase in t_lower for phrase in tactical_phrases)

        # Check for informational/historical messages that should be filtered
        # even if they contain tactical terms
        informational_phrases = [
            'пролетів',
            'відвернув',
            'здійснив посадку',
            'посадку на аеродром',
            'активність бортів',
            'буду оновлювати',
            'в разі додаткової інформації',
            'наразі це єдина',
            'фактична активність'
        ]
        has_informational_content = any(phrase in t_lower for phrase in informational_phrases)

        # Check if this is actually a current location message (not brief update)
        current_location_phrases = [
            'над',
            'в районі',
            'атакував',
            'вибухи в',
            'влучання в',
            'збито в',
            'знищено в',
            'на херсонщині',
            'на дніпропетровщині',
            'на запоріжжі',
            'на харківщині',
            'в області',
            'область',
            'щині'
        ]
        has_current_location = any(phrase in t_lower for phrase in current_location_phrases)

        # Check for count prefix (e.g., "16х БпЛА", "3х БпЛА") - these are real threats
        has_count_prefix = re.search(r'\d+\s*[xх]\s*бпла', t_lower)

        # If message has threat count or current location, do NOT filter it
        if has_count_prefix or has_current_location:
            return False

        # Check for general status messages that contain tactical terms but are informational
        status_phrases = [
            'український | ппошник',
            'український|ппошник',
            'поділ лук\'янівка'
        ]
        has_status_message = any(phrase in t_lower for phrase in status_phrases)

        # Check for route/location listing messages (format: "city — city1/city2 | region:")
        route_listing_pattern = r'київ.*—.*жуляни.*вишневе.*київ'
        has_route_listing = re.search(route_listing_pattern, t_lower, re.IGNORECASE)

        # Filter route listing messages as they are informational
        if has_route_listing:
            return True

        # If message is informational/historical, filter it out
        if has_informational_content:
            return True

        # If message is a general status update with tactical info, filter it out
        if has_status_message and has_tactical_info:
            return True

        # If message contains tactical information and is not informational, do NOT filter it
        if has_tactical_info:
            return False

        # Check for donation/fundraising messages (use more specific phrases)
        donation_phrases = [
            'підтримайте мене',
            'підтримати канал',
            'реквізити',
            'картка:',
            'банка:',
            'грн на каву',
            'на каву та енергетики',
            'по бажанню',
            'підтримка тільки',
            'monobank.ua',
            'privat24.ua',
            'send.monobank',
            'www.privat24',
            'донати',
            'донат',
            'дуже вдячний',
            'вдячний вам за підтримку',
            'за підтримку',
            'дякую за підтримку'
        ]
        has_donation_message = any(phrase in t_lower for phrase in donation_phrases)

        # Suppress donation messages
        if has_donation_message:
            return True

        # Check for channel promotion messages
        promotion_phrases = [
            'підтримати канал',
            'спасибо за подписку',
            'подписывайтесь',
            'наш канал',
            'наш телеграм'
        ]
        has_promotion_message = any(phrase in t_lower for phrase in promotion_phrases)

        # Suppress promotion messages
        if has_promotion_message:
            return True

        # Check for general informational messages without threats
        info_phrases = [
            'наразі це єдина',
            'фактична активність',
            'буду оновлювати',
            'в разі додаткової інформації',
            'здійснив посадку',
            'посадку на аеродром',
            'активність бортів'
        ]
        has_info_message = any(phrase in t_lower for phrase in info_phrases)

        # Suppress general info messages
        if has_info_message:
            return True

        # Check for very broad regions without specific cities
        broad_regions = [
            'києву, київщина і західна україна',
            'київ, київщина і західна україна',
            'центр і північ',
            'південь і схід'
        ]
        has_broad_region = any(region in t_lower for region in broad_regions)

        # Suppress if it's a general warning with broad regions
        if has_general_warning and has_broad_region:
            return True

        # Also suppress very short messages that are just general alerts
        if len(t.strip()) < 50 and has_general_warning:
            return True

        return False

    # Apply early filters
    if _is_russian_strategic_aviation(text):
        return []

    if _is_general_warning_without_location(text):
        return []

    # PRIORITY: Handle directional movement patterns (у напрямку, в направлении)
    # These should show trajectory/direction, not markers at destination
    def _is_directional_movement_message(t: str) -> bool:
        """Check if message describes movement towards a destination"""
        t_lower = t.lower()

        # Patterns indicating movement toward destination, not presence at location
        directional_patterns = [
            'у напрямку',
            'в напрямку',
            'напрямок',
            'рухається в напрямку',
            'летить у напрямку',
            'курс на',
            'прямує до'
        ]

        # Additional context that suggests this is about movement, not current location
        movement_context = [
            'з північного-сходу',
            'з півдня',
            'з заходу',
            'з сходу',
            'рухається',
            'летить',
            'прямує'
        ]

        has_directional = any(pattern in t_lower for pattern in directional_patterns)
        has_movement_context = any(context in t_lower for context in movement_context)

        return has_directional and has_movement_context

    # Handle directional movement messages - create projected path instead of filtering
    if _is_directional_movement_message(text):
        return _create_directional_trajectory_markers(text, mid, date_str, channel)

    # PRIORITY: Try SpaCy enhanced processing first
    if SPACY_AVAILABLE:
        try:
            spacy_results = spacy_enhanced_geocoding(text)
            if spacy_results:
                # Convert SpaCy results to the format expected by the rest of the system
                threat_markers = []

                # Process cities with coordinates first
                cities_with_coords = [city for city in spacy_results if city['coords']]

                for spacy_city in cities_with_coords:
                    lat, lng = spacy_city['coords']

                    # Determine threat type using our classify function
                    threat_type, icon = classify(text, spacy_city['name'])

                    # Create a proper place label
                    place_label = spacy_city['name'].title()
                    if spacy_city['region']:
                        place_label += f" [{spacy_city['region'].title()}]"

                    marker = {
                        'id': f"{mid}_spacy_{len(threat_markers)+1}",
                        'place': place_label,
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': clean_text(text)[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': f'spacy_{spacy_city["source"]}',
                        'count': 1,
                        'confidence': spacy_city['confidence']
                    }
                    threat_markers.append(marker)

                    add_debug_log(f"SPACY: Created marker for {spacy_city['name']} -> {spacy_city['normalized']} "
                                f"(case: {spacy_city.get('case', 'unknown')}, confidence: {spacy_city['confidence']})",
                                "spacy_integration")

                if threat_markers:
                    add_debug_log(f"SPACY: Successfully processed message with {len(threat_markers)} markers", "spacy_integration")
                    return threat_markers

        except Exception as e:
            add_debug_log(f"SPACY: Error processing message: {e}", "spacy_integration")
            # Continue with fallback processing

    # FALLBACK: Original regex-based processing continues below

    # PRIORITY: Handle "[city] на [region]" patterns early to avoid misprocessing
    regional_city_match = re.search(r'(\d+)\s+шахед[а-яіїєёыийї]*\s+на\s+([а-яіїєё\'\-\s]+?)\s+на\s+([а-яіїє]+щині?)', text.lower()) if text else None
    if regional_city_match:
        count_str = regional_city_match.group(1)
        city_raw = regional_city_match.group(2).strip()
        region_raw = regional_city_match.group(3).strip()

        # Use context-aware resolution
        coords = ensure_city_coords_with_message_context(city_raw, text)
        if coords:
            lat, lng, approx = coords
            add_debug_log(f"PRIORITY: Regional city pattern - {city_raw} на {region_raw} -> ({lat}, {lng})", "priority_regional_city")

            result_entry = {
                'id': f"{mid}_priority_regional",
                'place': f"{city_raw.title()} на {region_raw.title()}",
                'lat': lat, 'lng': lng,
                'type': 'shahed', 'count': int(count_str),
                'timestamp': date_str, 'channel': channel
            }
            return [result_entry]

    # EARLY CHECK: General multi-line threat detection (before specific cases)
    if not _disable_multiline:
        text_lines = (text or '').split('\n')
        threat_lines = []

        # Track current oblast context from headers like "Полтавщина:", "Харківщина:"
        current_oblast = None
        oblast_header_pattern = re.compile(r'^([а-яіїєґ]+(?:щина|ська\s+обл(?:асть)?\.?)):?\s*$', re.IGNORECASE)
        # Pattern for inline oblast: "Сумщина: 2 шахеди на Лебедин"
        inline_oblast_pattern = re.compile(r'^([а-яіїєґ]+(?:щина|ська\s+обл(?:асть)?\.?)):\s+(.+)$', re.IGNORECASE)

        # Look for lines that contain threats with quantities and targets
        for line in text_lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Check if this line has inline oblast format: "Область: threat text"
            inline_match = inline_oblast_pattern.match(line_stripped)
            if inline_match:
                oblast_name = inline_match.group(1).lower()
                threat_text = inline_match.group(2).strip()

                # Add the threat with oblast context
                enhanced_line = f"{oblast_name}: {threat_text}"
                threat_lines.append(enhanced_line)
                add_debug_log(f"MULTI-LINE: Detected inline oblast threat: {oblast_name} -> {threat_text[:50]}", "multi_line_inline_oblast")
                continue

            # Check if this line is a standalone oblast header
            oblast_match = oblast_header_pattern.match(line_stripped)
            if oblast_match:
                current_oblast = oblast_match.group(1).lower()
                add_debug_log(f"MULTI-LINE: Detected oblast header: {current_oblast}", "multi_line_oblast")
                continue

            line_lower = line_stripped.lower()

            # Check if line contains threat patterns with quantities and targets
            has_threat_pattern = (
                # Pattern: "Ціль на [target]" - target city for missiles/drones
                (re.search(r'ціль\s+на\s+([а-яіїєё\'\-\s]+)', line_lower, re.IGNORECASE)) or
                # Pattern: "N БпЛА на [region]щині" - regional threats like "16х БпЛА на Херсонщині"
                (re.search(r'\d+\s*[xх×]?\s*бпла\s+на\s+([а-яіїєё]+щині)', line_lower, re.IGNORECASE)) or
                # Pattern: "БпЛА на [direction] [region]" - regional directional threats
                (re.search(r'бпла\s+на\s+(півночі|півдні|сході|заході|північ|південь|схід|захід)\s+([а-яіїєё]+щин[іауи]?)', line_lower, re.IGNORECASE)) or
                # Pattern: "БпЛА ... з акваторії Чорного моря" - Black Sea threats
                (re.search(r'бпла.*?(з\s+акваторії|з\s+моря|з\s+чорного\s+моря)', line_lower, re.IGNORECASE)) or
                # Pattern: "N x/× БпЛА курсом на [target]"
                (re.search(r'\d+\s*[xх×]\s*бпла.*?(курс|на)\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахедів/шахеди на [target]" - all forms of Shahed
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+на\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахедів/шахеди біля [target]" - near target
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+біля\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахед маневрує в районі [target]" - maneuvering in area
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+маневру[юєї]+\s+в\s+район[іуи]\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N ударних БпЛА на [target]"
                (re.search(r'\d+\s+ударн.*?бпла.*?на\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N БпЛА на [target]" or "N бпла на [target]"
                (re.search(r'\d+\s+бпла.*?на\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "БпЛА курсом на [target]" (without count)
                (re.search(r'бпла.*?курс.*?на\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахедів через [target]" - via target
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+через\s+([а-яіїєё\'\-\s]+)', line_lower)) or
                # Pattern: "N шахедів з боку [target]" - from direction of target
                (re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+з\s+боку\s+([а-яіїєё\'\-\s]+)', line_lower))
            )

            if has_threat_pattern:
                # If we have oblast context, prepend it to the line
                if current_oblast:
                    # Add oblast context to help city resolution
                    enhanced_line = f"{current_oblast}: {line_stripped}"
                    threat_lines.append(enhanced_line)
                    add_debug_log(f"MULTI-LINE: Added threat with oblast context: {current_oblast} -> {line_stripped[:50]}", "multi_line_context")
                else:
                    threat_lines.append(line_stripped)

        # If we have multiple threat lines, process them separately
        if len(threat_lines) >= 2:
            add_debug_log(f"MULTI-LINE THREAT PROCESSING: {len(threat_lines)} threat lines detected", "multi_line_threats")

            all_tracks = []
            for i, line in enumerate(threat_lines):
                if not line.strip():
                    continue

                add_debug_log(f"Processing threat line {i+1}: {line[:100]}", "threat_line")

                # Process each line as a separate message with multiline disabled
                line_result = process_message(line.strip(), f"{mid}_threat_{i+1}", date_str, channel, _disable_multiline=True)
                if line_result and isinstance(line_result, list):
                    all_tracks.extend(line_result)
                    add_debug_log(f"Threat line {i+1} produced {len(line_result)} tracks", "threat_line_result")
                else:
                    add_debug_log(f"Threat line {i+1} produced no tracks", "threat_line_result")

            if all_tracks:
                add_debug_log(f"Multi-line threat processing complete: {len(all_tracks)} total tracks", "multi_line_threats_complete")
                return all_tracks

    # PRIORITY FIRST: All air alarm messages should be list-only (no map markers)
    # This must be checked BEFORE any other processing to prevent other logic from creating markers
    original_text = text or ''
    low_orig = original_text.lower()

    # Clear any previous priority result
    globals()['_current_priority_result'] = None

    # PRIORITY CHECK: Black Sea aquatory - must check BEFORE multi-regional processing
    # Messages like "БпЛА курсом на Миколаїв з акваторії Чорного моря" or "15 шахедів з моря на Ізмаїл" should NOT place markers on cities
    lower_text = original_text.lower()
    # Check for Black Sea references: акваторія OR "з моря" OR "з чорного моря"
    is_black_sea = (('акватор' in lower_text or 'акваторії' in lower_text) and ('чорного моря' in lower_text or 'чорне море' in lower_text or 'чорному морі' in lower_text)) or \
                   ('з моря' in lower_text and ('курс' in lower_text or 'на ' in lower_text)) or \
                   ('з чорного моря' in lower_text)

    if is_black_sea:
        # Extract target region/direction if mentioned
        m_target = re.search(r'курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower_text)
        m_direction = re.search(r'на\s+(північ|південь|схід|захід|північний\s+схід|північний\s+захід|південний\s+схід|південний\s+захід)', lower_text)
        m_region = re.search(r'(одещин|одеськ|миколаїв|херсон)', lower_text)

        target_info = None
        sea_lat, sea_lng = 45.3, 30.7  # Default: northern Black Sea central coords

        # Adjust position based on direction/region
        if m_direction:
            direction = m_direction.group(1)
            if 'південь' in direction:
                sea_lat = 45.0  # Further south
            elif 'північ' in direction:
                sea_lat = 45.6  # Further north
            if 'схід' in direction:
                sea_lng = 31.2  # Further east
            elif 'захід' in direction:
                sea_lng = 30.2  # Further west

        if m_region:
            region_name = m_region.group(1)
            if 'одещин' in region_name or 'одеськ' in region_name:
                # South of Odesa region - in the sea 50km offshore
                sea_lat, sea_lng = 45.7, 30.7
                target_info = 'Одещини'
            elif 'миколаїв' in region_name:
                sea_lat, sea_lng = 45.9, 31.4
                target_info = 'Миколаївщини'
            elif 'херсон' in region_name:
                sea_lat, sea_lng = 45.7, 32.5
                target_info = 'Херсонщини'

        if m_target:
            tc = m_target.group(1).lower()
            tc = UA_CITY_NORMALIZE.get(tc, tc)
            target_info = tc.title()

        threat_type, icon = classify(original_text)
        place_label = 'Акваторія Чорного моря'
        if target_info:
            place_label += f' (на {target_info})'

        # Try to find target city coordinates for trajectory
        target_coords = None
        if m_target:
            tc_normalized = m_target.group(1).lower()
            tc_normalized = UA_CITY_NORMALIZE.get(tc_normalized, tc_normalized)
            if tc_normalized in CITY_COORDS:
                target_coords = CITY_COORDS[tc_normalized]

        result = {
            'id': str(mid), 'place': place_label, 'lat': sea_lat, 'lng': sea_lng,
            'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': icon, 'source_match': 'black_sea_course_priority'
        }

        # Add trajectory data if we have target coordinates
        if target_coords:
            result['trajectory'] = {
                'start': [sea_lat, sea_lng],
                'end': list(target_coords),
                'target': target_info
            }

        return [result]

    # IMMEDIATE CHECK: Multi-regional UAV messages (highest priority)
    text_lines = original_text.split('\n')
    region_count = sum(1 for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:', 'край:']) or (
        'щина' in line.lower() and line.lower().strip().endswith(':')
    ) or any(region in line.lower() for region in ['щина)', 'щини', 'щину', 'одещина', 'чернігівщина', 'дніпропетровщина', 'харківщина', 'київщина']))
    # Look for lines with emoji + UAV mentions (more flexible detection)
    uav_lines = [line for line in text_lines if 'бпла' in line.lower() and ('🛵' in line or '🛸' in line)]
    uav_count = len(uav_lines)

    # NEW: Look for lines with Shahed mentions and regions (without emoji requirement)
    shahed_region_lines = [line for line in text_lines if
                          ('шахед' in line.lower() or 'shahed' in line.lower()) and
                          ('щина' in line.lower() or 'щину' in line.lower() or 'щині' in line.lower())]
    shahed_count = len(shahed_region_lines)

    # NEW: Check for multiple regional aviation/БПЛА threats in one message
    # Pattern: "🛫 Донеччина та Дніпропетровщина - загроза застосування авіаційних засобів ураження. 🛵 Харківщина - загроза застосування ударних БпЛА"
    aviation_threat_lines = []
    for line in text_lines:
        line_lower = line.lower().strip()
        if not line_lower:
            continue
        # Check if line contains region + aviation/БПЛА threat
        has_region = any(region in line_lower for region in ['щина', 'область'])
        has_aviation = any(pattern in line_lower for pattern in ['авіаційних засобів', 'авіації', 'тактична авіація'])
        has_bpla = 'бпла' in line_lower or 'безпілотн' in line_lower

        if has_region and (has_aviation or has_bpla):
            aviation_threat_lines.append(line)

    aviation_threat_count = len(aviation_threat_lines)

    add_debug_log(f"DEBUG COUNT CHECK: {region_count} regions, {uav_count} UAV lines, {shahed_count} Shahed+region lines, {aviation_threat_count} aviation threat lines", "count_check")

    # Process multiple regional aviation threats
    if aviation_threat_count >= 1:
        add_debug_log(f"MULTI-REGIONAL AVIATION THREATS: {aviation_threat_count} lines detected", "multi_aviation")

        all_tracks = []

        # Regional aviation coordinates mapping (Black Sea / oblast centers)
        region_aviation_coords = {
            'одещина': (46.373528, 31.284023),  # Black Sea near Odesa
            'одесщина': (46.373528, 31.284023),
            'донеччина': (48.5, 37.8),  # Donetsk oblast center
            'дніпропетровщина': (48.45, 35.0),  # Dnipro
            'харківщина': (49.9935, 36.2304),  # Kharkiv
            'луганщина': (48.567, 39.317),  # Luhansk oblast
            'запорожжя': (47.8388, 35.1396),  # Zaporizhzhia
            'херсонщина': (46.6354, 32.6169),  # Kherson
            'миколаївщина': (46.975, 32.0),  # Mykolaiv oblast
        }

        for line in aviation_threat_lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Split by emoji or sentence patterns to separate different threats
            # Pattern: "🛫 Region - threat. 🛵 Region - threat"
            import re

            # Split by emoji patterns or full stops followed by emoji
            segments = re.split(r'[\.\!]\s*(?=[🛫🛵🛸⚠️])|(?<=[🛫🛵🛸⚠️])\s+(?=[А-ЯІЇЄа-яіїє])', line_stripped)
            if len(segments) <= 1:
                # No clear segments, treat as one line
                segments = [line_stripped]

            for segment in segments:
                segment = segment.strip()
                if not segment or len(segment) < 10:
                    continue

                segment_lower = segment.lower()

                # Extract all regions from this segment
                regions_found = re.findall(r'(одещина|одесщина|донеччина|дніпропетровщина|харківщина|луганщина|запорожжя|херсонщина|миколаївщина)', segment_lower)

                # Determine threat type from segment content
                is_aviation = any(pattern in segment_lower for pattern in ['авіаційних засобів', 'авіації', 'тактична авіація'])
                is_bpla = 'бпла' in segment_lower or 'безпілотн' in segment_lower
                is_strike_bpla = 'ударних бпла' in segment_lower or 'ударних безпілотн' in segment_lower

                threat_type = 'avia' if is_aviation else ('shahed' if is_bpla else 'artillery')
                icon = 'avia.png' if is_aviation else ('shahed3.webp' if is_bpla else 'artillery.png')
                threat_label = 'Авіація' if is_aviation else ('Ударні БпЛА' if is_strike_bpla else 'БпЛА')

                # Create marker for each region mentioned in this segment
                for region in regions_found:
                    if region in region_aviation_coords:
                        coords = region_aviation_coords[region]
                        lat, lng = coords

                        region_display = region.title()
                        place_name = f"{threat_label} [{region_display}]"

                        track = {
                            'id': f"{mid}_aviation_{region}_{len(all_tracks)}",
                            'place': place_name,
                            'lat': lat,
                            'lng': lng,
                            'threat_type': threat_type,
                            'text': segment[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'multi_regional_aviation',
                            'count': 1
                        }

                        all_tracks.append(track)
                        add_debug_log(f"Aviation threat: {place_name} at {coords} (segment: {segment[:50]})", "multi_aviation")
                    else:
                        add_debug_log(f"No coords for region: {region}", "multi_aviation")

        if all_tracks:
            add_debug_log(f"Multi-regional aviation processing complete: {len(all_tracks)} total tracks", "multi_aviation_complete")
            return all_tracks

    add_debug_log(f"DEBUG COUNT CHECK: {region_count} regions, {uav_count} UAV lines, {shahed_count} Shahed+region lines", "count_check")

    # If we have multiple Shahed lines with regions, process them separately
    if shahed_count >= 2:
        add_debug_log(f"MULTI-LINE SHAHED PROCESSING: {shahed_count} Shahed+region lines detected", "multi_shahed")

        all_tracks = []
        for i, line in enumerate(shahed_region_lines):
            if not line.strip():
                continue

            add_debug_log(f"Processing Shahed line {i+1}: {line[:100]}", "shahed_line")

            # Process each line as a separate message
            line_result = process_message(line.strip(), f"{mid}_shahed_{i+1}", date_str, channel, _disable_multiline=True)
            if line_result and isinstance(line_result, list):
                all_tracks.extend(line_result)
                add_debug_log(f"Shahed line {i+1} produced {len(line_result)} tracks", "shahed_line_result")
            else:
                add_debug_log(f"Shahed line {i+1} produced no tracks", "shahed_line_result")

        if all_tracks:
            add_debug_log(f"Multi-line Shahed processing complete: {len(all_tracks)} total tracks", "multi_shahed_complete")
            return all_tracks

    # If we have multiple UAV lines with emojis, process them separately even if they don't have explicit regions
    if uav_count >= 2 and (region_count >= 1 or any('району' in line.lower() or 'області' in line.lower() or 'обл.' in line.lower() for line in uav_lines)):
        add_debug_log(f"MULTI-LINE UAV PROCESSING: {uav_count} UAV lines detected", "multi_uav")

        all_tracks = []
        for i, line in enumerate(uav_lines):
            if not line.strip():
                continue

            add_debug_log(f"Processing UAV line {i+1}: {line[:100]}", "uav_line")

            # Process each line as a separate message
            line_result = process_message(line.strip(), f"{mid}_line_{i+1}", date_str, channel, _disable_multiline=True)
            if line_result and isinstance(line_result, list):
                all_tracks.extend(line_result)
                add_debug_log(f"Line {i+1} produced {len(line_result)} tracks", "uav_line_result")
            else:
                add_debug_log(f"Line {i+1} produced no tracks", "uav_line_result")

        if all_tracks:
            add_debug_log(f"Multi-line UAV processing complete: {len(all_tracks)} total tracks", "multi_uav_complete")
            return all_tracks

    # Legacy multi-regional detection (keep for backward compatibility)
    if region_count >= 2 and sum(1 for line in text_lines if 'бпла' in line.lower() and ('курс' in line.lower() or 'на ' in line.lower())) >= 3:
        add_debug_log(f"IMMEDIATE MULTI-REGIONAL UAV: {region_count} regions, {uav_count} UAVs - ENTERING EARLY PROCESSING", "multi_regional")
        # Process directly without going through other logic
        import re

        # Define essential functions inline for immediate processing
        def get_city_coords_quick(city_name, region_hint=None):
            """Quick coordinate lookup with accusative case normalization and regional context"""
            city_norm = city_name.strip().lower()

            # Handle specific multi-word cities in accusative case
            if city_norm == 'велику димерку':
                city_norm = 'велика димерка'
            elif city_norm == 'велику виску':
                city_norm = 'велика виска'
            elif city_norm == 'мену':
                city_norm = 'мена'
            elif city_norm == 'пісківку':
                city_norm = 'пісківка'
            elif city_norm == 'новгород-сіверський':
                city_norm = 'новгород-сіверський'
            elif city_norm == 'києвом':
                city_norm = 'київ'

            # General accusative case endings (винительный падеж)
            elif city_norm.endswith('у') and len(city_norm) > 3:
                city_norm = city_norm[:-1] + 'а'
            elif city_norm.endswith('ю') and len(city_norm) > 3:
                city_norm = city_norm[:-1] + 'я'
            elif city_norm.endswith('ку') and len(city_norm) > 4:
                city_norm = city_norm[:-2] + 'ка'

            # Apply UA_CITY_NORMALIZE rules
            if city_norm in UA_CITY_NORMALIZE:
                city_norm = UA_CITY_NORMALIZE[city_norm]

            # ONLY OpenCage API - no local dictionaries!
            # Build context with region if available
            if region_hint:
                context_text = f"({region_hint} обл.) {city_norm}"
            else:
                context_text = text
            
            coords = ensure_city_coords_with_message_context(city_norm, context_text)
            add_debug_log(f"OpenCage lookup: '{city_name}' -> '{city_norm}' (region={region_hint}) -> {coords}", "multi_regional")
            return coords

        # Map regional header patterns to oblast names for API
        region_header_to_oblast = {
            'сумщина': 'Сумська область',
            'чернігівщина': 'Чернігівська область',
            'київщина': 'Київська область',
            'полтавщина': 'Полтавська область',
            'дніпропетровщина': 'Дніпропетровська область',
            'харківщина': 'Харківська область',
            'миколаївщина': 'Миколаївська область',
            'одещина': 'Одеська область',
            'запоріжжя': 'Запорізька область',
            'херсонщина': 'Херсонська область',
            'черкащина': 'Черкаська область',
            'вінниччина': 'Вінницька область',
            'житомирщина': 'Житомирська область',
            'рівненщина': 'Рівненська область',
            'волинь': 'Волинська область',
            'львівщина': 'Львівська область',
            'донеччина': 'Донецька область',
            'луганщина': 'Луганська область',
        }

        threats = []
        processed_cities = set()  # Избегаем дубликатов
        current_region = None  # Track current region from headers

        for line in text_lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            line_lower = line_stripped.lower()

            # CHECK FOR REGION HEADER (e.g., "Київщина:", "Харківщина:")
            # This is CRITICAL for multi-regional messages
            region_header_match = re.match(r'^([а-яіїєґ]+щина|[а-яіїєґ]+ь):?\s*$', line_lower)
            if region_header_match:
                region_name = region_header_match.group(1)
                if region_name in region_header_to_oblast:
                    current_region = region_header_to_oblast[region_name]
                    add_debug_log(f"REGION HEADER detected: '{line_stripped}' -> current_region = '{current_region}'", "multi_regional")
                continue  # Skip processing the header line itself

            # Also check for inline region header like "Сумщина: БпЛА..."
            inline_region_match = re.match(r'^([а-яіїєґ]+щина|[а-яіїєґ]+ь):\s*(.+)$', line_lower)
            if inline_region_match:
                region_name = inline_region_match.group(1)
                if region_name in region_header_to_oblast:
                    current_region = region_header_to_oblast[region_name]
                    line_stripped = inline_region_match.group(2).strip()  # Process the rest of the line
                    line_lower = line_stripped.lower()
                    add_debug_log(f"INLINE REGION HEADER: '{region_name}' -> current_region = '{current_region}', processing: '{line_stripped}'", "multi_regional")

            line_lower = line_stripped.lower()

            # PRIORITY: Handle "напрямок м.X" or "напрямок на X" pattern first
            napryamok_match = re.search(r'напрямок\s+(?:м\.|місто|на)?\s*([а-яїієґ\-]+)', line_lower)
            if napryamok_match:
                target_city = napryamok_match.group(1).strip()
                target_norm = target_city
                if target_norm.endswith('у') and len(target_norm) > 3:
                    target_norm = target_norm[:-1] + 'а'
                elif target_norm.endswith('ку') and len(target_norm) > 4:
                    target_norm = target_norm[:-2] + 'ка'
                if target_norm in UA_CITY_NORMALIZE:
                    target_norm = UA_CITY_NORMALIZE[target_norm]

                # Get coordinates using region context from headers
                target_coords = get_city_coords_quick(target_norm, current_region)

                if target_coords:
                    if len(target_coords) == 3:
                        lat, lng, approx = target_coords
                    else:
                        lat, lng = target_coords[:2]

                    # Check if not already processed
                    city_key = target_norm
                    if city_key not in processed_cities:
                        processed_cities.add(city_key)

                        uav_count = 1
                        # Try to extract UAV count from line
                        count_match = re.search(r'(\d+)\s*[xх×]?\s*бпла', line_lower)
                        if count_match:
                            uav_count = int(count_match.group(1))

                        threat_id = f"{mid}_napryamok_{len(threats)}"
                        threats.append({
                            'id': threat_id,
                            'place': target_norm.title(),
                            'lat': lat,
                            'lng': lng,
                            'threat_type': 'shahed',
                            'text': f"Напрямок → {target_norm.title()}",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': 'shahed3.webp',
                            'source_match': 'immediate_napryamok',
                            'count': uav_count
                        })

                        add_debug_log(f"Напрямок pattern: {target_norm} at {target_coords}", "napryamok")
                        continue  # Skip other processing for this line

            # Look for UAV course patterns
            if 'бпла' in line_lower and ('курс' in line_lower or ' на ' in line_lower or 'над' in line_lower or 'повз' in line_lower):
                # Extract city name from patterns - handle both plain text and markdown links
                patterns = [
                    # Pattern for markdown links: БпЛА курсом на [Бровари](link)
                    r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(?:курсом?)?\s*(?:на|над)\s+\[([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]+?)\]',
                    # Pattern for plain text: БпЛА курсом на Конотоп (improved to capture multi-word cities + districts)
                    # Fixed: Added " з " and " район" to lookahead to properly capture "Миколаїв з акваторії" and "Покровський район"
                    r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]+?(?:\s+район)?)(?=\s*(?:\n|$|[,\.\!\?;]|\s+з\s+|\s+\d+[xх×]?\s*бпла|\s+[А-ЯІЇЄЁа-яіїєё]+щина:|\s+\())',
                    # PRIORITY: Pattern for "повз ... курсом на" (e.g., "БпЛА повз Юріївку курсом на Павлоград")
                    # Must be BEFORE the simple "повз" pattern to capture both cities correctly
                    # Ignored for marker creation - handled separately below to create marker at bypass city with trajectory
                ]

                # SPECIAL HANDLING: "повз ... курсом на" pattern - create marker at bypass city with trajectory to target
                povz_course_match = re.search(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+повз\s+([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]{3,50}?)\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]{3,50}?)(?=\s*(?:\n|$|[,\.\!\?;]))', line_lower, re.IGNORECASE)
                if povz_course_match:
                    count_str, bypass_city_raw, target_city_raw = povz_course_match.groups()

                    # Normalize bypass city name
                    bypass_city = bypass_city_raw.strip()
                    bypass_norm = bypass_city.lower()
                    if bypass_norm.endswith('у') and len(bypass_norm) > 3:
                        bypass_norm = bypass_norm[:-1] + 'а'
                    elif bypass_norm.endswith('ку') and len(bypass_norm) > 4:
                        bypass_norm = bypass_norm[:-2] + 'ка'
                    if bypass_norm in UA_CITY_NORMALIZE:
                        bypass_norm = UA_CITY_NORMALIZE[bypass_norm]

                    # Normalize target city name
                    target_city = target_city_raw.strip()
                    target_norm = target_city.lower()
                    if target_norm.endswith('у') and len(target_norm) > 3:
                        target_norm = target_norm[:-1] + 'а'
                    elif target_norm.endswith('ку') and len(target_norm) > 4:
                        target_norm = target_norm[:-2] + 'ка'
                    if target_norm in UA_CITY_NORMALIZE:
                        target_norm = UA_CITY_NORMALIZE[target_norm]

                    # Get coordinates for bypass city using region context
                    bypass_coords = get_city_coords_quick(bypass_norm, current_region)

                    if bypass_coords:
                        if len(bypass_coords) == 3:
                            lat, lng, approx = bypass_coords
                        else:
                            lat, lng = bypass_coords

                        uav_count = 1
                        if count_str and count_str.isdigit():
                            uav_count = int(count_str)

                        # Create marker at bypass city with trajectory info
                        threat_id = f"{mid}_povz_course_{len(threats)}"
                        threats.append({
                            'id': threat_id,
                            'place': bypass_norm.title(),
                            'lat': lat,
                            'lng': lng,
                            'threat_type': 'shahed',
                            'text': f"Повз {bypass_norm.title()} → {target_norm.title()}",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': 'shahed3.webp',
                            'source_match': 'immediate_povz_course',
                            'count': uav_count,
                            'course_source': bypass_norm,
                            'course_target': target_norm
                        })

                        add_debug_log(f"Повз курсом на: {bypass_norm} -> {target_norm} at {bypass_coords}", "povz_course")
                        continue  # Skip normal processing for this line

                # Normal patterns (after special handling)
                patterns.append(
                    # Pattern for "повз" without "курсом на" (e.g., "БпЛА повз Славутич в бік Білорусі")
                    r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(?:.*?)?повз\s+([А-ЯІЇЄЁа-яіїєёʼ\'\-\s]{3,50}?)(?=\s+(?:в\s+бік|до|на|через|$|[,\.\!\?;]))'
                )

                # Also check for bracket city pattern like "Вилково (Одещина)"
                bracket_matches = re.finditer(r'([А-ЯІЇЄЁа-яіїєё\'ʼʻ`\-\s]{3,30})\s*\(([А-ЯІЇЄЁа-яіїєё\'ʼʻ`\-\s]+щина|[А-ЯІЇЄЁа-яіїєё\'ʼʻ`\-\s]+обл\.?)\)', line_stripped, re.IGNORECASE)
                for bmatch in bracket_matches:
                    city_clean = bmatch.group(1).strip()
                    region_info = bmatch.group(2).strip()

                    city_normalized = city_clean.lower()
                    city_key = city_normalized

                    # Skip if already processed
                    if city_key in processed_cities:
                        continue
                    processed_cities.add(city_key)

                    # Try to get coordinates using region from bracket or current_region
                    # Extract oblast from bracket (e.g., "Одещина" -> "Одеська область")
                    bracket_region = None
                    region_info_lower = region_info.lower()
                    if region_info_lower in region_header_to_oblast:
                        bracket_region = region_header_to_oblast[region_info_lower]
                    elif region_info_lower.replace('щина', 'щина') in region_header_to_oblast:
                        bracket_region = region_header_to_oblast.get(region_info_lower)

                    coords = get_city_coords_quick(city_clean, bracket_region or current_region)

                    if coords:
                        if len(coords) == 3:
                            lat, lng, approx = coords
                        else:
                            lat, lng = coords

                        threat_id = f"{mid}_imm_bracket_{len(threats)}"
                        threats.append({
                            'id': threat_id,
                            'place': city_clean.title(),
                            'lat': lat,
                            'lng': lng,
                            'threat_type': 'shahed',
                            'text': f"{line_stripped} (bracket city)",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': 'shahed3.webp',
                            'source_match': 'immediate_multi_regional_bracket',
                            'count': 1
                        })

                        add_debug_log(f"Immediate Multi-regional bracket: {city_clean} -> {coords}", "multi_regional")
                    else:
                        add_debug_log(f"Immediate Multi-regional bracket: No coords for {city_clean}", "multi_regional")

                for pattern in patterns:
                    matches = re.finditer(pattern, line_stripped, re.IGNORECASE)
                    for match in matches:
                        if len(match.groups()) == 2:
                            count_str, city_raw = match.groups()
                        else:
                            count_str = None
                            city_raw = match.group(1)

                        if not city_raw:
                            continue

                        # Clean city name (remove trailing spaces)
                        city_clean = city_raw.strip()

                        # Normalize city name for coordinate lookup
                        city_normalized = city_clean.lower()

                        # Normalize for display (convert accusative to nominative)
                        city_display = city_clean
                        if city_normalized == 'велику димерку':
                            city_display = 'Велика Димерка'
                        elif city_normalized == 'велику виску':
                            city_display = 'Велика Виска'
                        elif city_normalized == 'мену':
                            city_display = 'Мена'
                        elif city_normalized == 'пісківку':
                            city_display = 'Пісківка'
                        elif city_normalized == 'києвом':
                            city_display = 'Київ'
                            city_normalized = 'київ'  # Also normalize for lookup
                        elif city_normalized.endswith('ом') and len(city_normalized) > 4:
                            # Handle other accusative masculine endings
                            city_display = city_normalized[:-2]
                            city_display = city_display.title()
                            city_normalized = city_normalized[:-2]
                        elif city_normalized.endswith('у') and len(city_normalized) > 3:
                            city_display = city_normalized[:-1] + 'а'
                            city_display = city_display.title()
                        elif city_normalized.endswith('ю') and len(city_normalized) > 3:
                            city_display = city_normalized[:-1] + 'я'
                            city_display = city_display.title()
                        elif city_normalized.endswith('ку') and len(city_normalized) > 4:
                            city_display = city_normalized[:-2] + 'ка'
                            city_display = city_display.title()
                        else:
                            city_display = city_clean.title()

                        city_key = city_normalized

                        # Skip if already processed
                        if city_key in processed_cities:
                            continue
                        processed_cities.add(city_key)

                        # Try to get coordinates using current region context
                        coords = get_city_coords_quick(city_clean, current_region)

                        if coords:
                            if len(coords) == 3:
                                lat, lng, approx = coords
                            else:
                                lat, lng = coords

                            # Extract count if present
                            uav_count_num = 1
                            if count_str and count_str.isdigit():
                                uav_count_num = int(count_str)

                            # Create multiple tracks for multiple drones
                            tracks_to_create = max(1, uav_count_num)
                            for i in range(tracks_to_create):
                                track_display_name = city_display
                                if tracks_to_create > 1:
                                    track_display_name += f" #{i+1}"

                                # Add small coordinate offsets to prevent marker overlap
                                marker_lat = lat
                                marker_lng = lng
                                if tracks_to_create > 1:
                                    # Create a chain pattern - drones one after another
                                    offset_distance = 0.03  # ~3km offset between each drone
                                    marker_lat += offset_distance * i
                                    marker_lng += offset_distance * i * 0.5

                                threat_id = f"{mid}_imm_multi_{len(threats)}"
                                threats.append({
                                    'id': threat_id,
                                    'place': track_display_name,  # Use numbered display name for multiple drones
                                    'lat': marker_lat,
                                    'lng': marker_lng,
                                    'threat_type': 'shahed',
                                    'text': f"{line_stripped} (мультирегіональне)",
                                    'date': date_str,
                                    'channel': channel,
                                    'marker_icon': 'shahed3.webp',
                                    'source_match': f'immediate_multi_regional_uav_{uav_count_num}x',
                                    'count': 1  # Each track represents 1 drone
                                })

                            add_debug_log(f"Immediate Multi-regional: {city_clean} ({uav_count_num}x) -> {tracks_to_create} tracks at {coords}", "multi_regional")
                        else:
                            add_debug_log(f"Immediate Multi-regional: No coords for {city_clean}", "multi_regional")

        # Also check for regional UAV references without specific cities
        for line in text_lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            line_lower = line_stripped.lower()

            # Look for UAV + region patterns without specific cities
            if 'бпла' in line_lower and any(region in line_lower for region in ['щини', 'щину', 'одещина', 'чернігівщина', 'дніпропетровщини']):
                # Skip if this specific line contains a city that was already processed
                line_has_processed_city = False
                for city in processed_cities:
                    if city in line_lower:
                        line_has_processed_city = True
                        break

                if line_has_processed_city:
                    continue

                # Special case: movement messages with direction in parentheses
                # Pattern: "БпЛА на півдні Чернігівщини, рухаються на південь (Київщина)"
                # Here (Київщина) indicates direction, not location
                directional_movement = re.search(r'на\s+([\w\-\s/]+?)\s+([а-яіїєґ]+щини|[а-яіїєґ]+щину|дніпропетровщини|одещини|чернігівщини).*рухаються.*\(([^)]+)\)', line_lower)
                if directional_movement:
                    direction = directional_movement.group(1).strip()
                    region_raw = directional_movement.group(2).strip()
                    target_direction = directional_movement.group(3).strip()

                    # Map region to oblast center (current location, not target)
                    region_coords = None
                    if 'дніпропетров' in region_raw:
                        region_coords = (48.45, 35.0)
                        region_name = 'Дніпропетровщини'
                    elif 'чернігів' in region_raw:
                        region_coords = (51.4982, 31.3044)
                        region_name = 'Чернігівщини'
                    elif 'одес' in region_raw:
                        region_coords = (46.5197, 30.7495)
                        region_name = 'Одещини'

                    if region_coords:
                        # Apply directional offset for current location
                        lat, lng = region_coords
                        if 'півдн' in direction or 'южн' in direction:
                            lat -= 0.5
                        elif 'північ' in direction or 'север' in direction:
                            lat += 0.5
                        elif 'захід' in direction or 'запад' in direction:
                            lng -= 0.8
                        elif 'схід' in direction or 'восток' in direction:
                            lng += 0.8

                        direction_label = direction.replace('півдн', 'південн').replace('північ', 'північн')
                        place_name = f"{region_name} ({direction_label}а частина) → {target_direction}"

                        threat_id = f"{mid}_imm_regional_movement_{len(threats)}"
                        threats.append({
                            'id': threat_id,
                            'place': place_name,
                            'lat': lat,
                            'lng': lng,
                            'threat_type': 'shahed',
                            'text': f"{line_stripped} (рух у напрямку {target_direction})",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': 'shahed3.webp',
                            'source_match': 'immediate_multi_regional_movement',
                            'count': 1,
                            'movement_target': target_direction
                        })

                        add_debug_log(f"Immediate Multi-regional movement: {place_name} -> {lat}, {lng} (target: {target_direction})", "multi_regional")
                        continue

                # Check if this is a directional reference like "на півдні Дніпропетровщини"
                region_match = re.search(r'на\s+([\w\-\s/]+?)\s+([а-яіїєґ]+щини|[а-яіїєґ]+щину|дніпропетровщини|одещини|чернігівщини)', line_lower)
                if region_match:
                    direction = region_match.group(1).strip()
                    region_raw = region_match.group(2).strip()

                    # Map region to oblast center
                    region_coords = None
                    if 'дніпропетров' in region_raw:
                        region_coords = (48.45, 35.0)
                        region_name = 'Дніпропетровщини'
                    elif 'чернігів' in region_raw:
                        region_coords = (51.4982, 31.3044)
                        region_name = 'Чернігівщини'
                    elif 'одес' in region_raw:
                        region_coords = (46.5197, 30.7495)
                        region_name = 'Одещини'

                    if region_coords:
                        # Apply directional offset
                        lat, lng = region_coords
                        if 'півдн' in direction or 'южн' in direction:
                            lat -= 0.5
                        elif 'північ' in direction or 'север' in direction:
                            lat += 0.5
                        elif 'захід' in direction or 'запад' in direction:
                            lng -= 0.8
                        elif 'схід' in direction or 'восток' in direction:
                            lng += 0.8

                        direction_label = direction.replace('півдн', 'південн').replace('північ', 'північн')
                        place_name = f"{region_name} ({direction_label}а частина)"

                        threat_id = f"{mid}_imm_regional_{len(threats)}"
                        threats.append({
                            'id': threat_id,
                            'place': place_name,
                            'lat': lat,
                            'lng': lng,
                            'threat_type': 'shahed',
                            'text': f"{line_stripped} (регіональний)",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': 'shahed3.webp',
                            'source_match': 'immediate_multi_regional_region',
                            'count': 1
                        })

                        add_debug_log(f"Immediate Multi-regional regional: {place_name} -> {lat}, {lng}", "multi_regional")

        if threats:
            add_debug_log(f"IMMEDIATE MULTI-REGIONAL RESULT: {len(threats)} threats", "multi_regional")
            return threats

    if 'повітряна тривога' in low_orig or 'тривога' in low_orig or 'тривог' in low_orig:
        # Always event-only record (list), never create map markers for air alarms or cancellations
        place = None
        low = low_orig.lower()
        # Try to extract oblast/region info for place
        for name in ['запорізька', 'одеська', 'миколаївська', 'херсонська', 'київська', 'львівська', 'харківська', 'дніпропетровська', 'чернігівська', 'сумська', 'полтавська', 'тернопільська', 'волинська', 'рівненська', 'житомирська', 'вінницька', 'закарпатська', 'івано-франківська', 'кіровоградська', 'черкаська', 'хмельницька', 'луганська', 'донецька']:
            if name in low:
                place = name.title() + ' Обл.'
                break

        # Also try to find city names
        if not place:
            for city in ['запоріжжя', 'одеса', 'миколаїв', 'херсон', 'київ', 'львів', 'харків', 'дніпро', 'чернігів', 'суми', 'полтава']:
                if city in low:
                    place = city.title()
                    break

        # Determine if this is alarm start or cancellation
        threat_type = 'alarm_cancel' if ('відбій' in low_orig or 'отбой' in low_orig) else 'alarm'
        icon = 'vidboi.png' if threat_type == 'alarm_cancel' else 'trivoga.png'

        # Clean subscription links from air alarm messages before returning
        import re as re_import
        cleaned_text = original_text
        if original_text:
            # remove lines containing subscription prompts
            cleaned = []
            for ln in original_text.splitlines():
                ln2 = ln.strip()
                if not ln2:
                    continue
                # remove any line that is just a subscribe CTA or starts with arrow+subscribe
                if re_import.search(r'(підписатись|підписатися|підписатися|подписаться|подпишись|subscribe)', ln2, re_import.IGNORECASE):
                    continue
                # remove arrow+subscribe pattern specifically
                if re_import.search(r'[➡→>]\s*підписатися', ln2, re_import.IGNORECASE):
                    continue
                cleaned.append(ln2)
            cleaned_text = '\n'.join(cleaned)

        return [{
            'id': str(mid), 'place': place, 'lat': None, 'lng': None,
            'threat_type': threat_type, 'text': cleaned_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': icon, 'list_only': True
        }]

    # Define classify function at the start so it's available throughout process_message
    def classify(th: str, city_context: str = ""):
        import re  # Import re module locally for pattern matching
        l = th.lower()

        # Add debug logging (temporarily disabled)
        # print(f"[CLASSIFY DEBUG] Input text: {th}")
        # print(f"[CLASSIFY DEBUG] Lowercase text: {l}")
        # print(f"[CLASSIFY DEBUG] City context: {city_context}")
        # print(f"[CLASSIFY DEBUG] Contains 🚀: {'🚀' in th}")
        # print(f"[CLASSIFY DEBUG] Contains 'ціль': {'ціль' in l}")
        # print(f"[CLASSIFY DEBUG] Contains 'високошвидкісн': {'високошвидкісн' in l}")
        # print(f"[CLASSIFY DEBUG] Contains 'бпла': {'бпла' in l}")

        # PRIORITY: Artillery shelling warning (обстріл / загроза обстрілу) -> use obstril.png
        # This should have priority over FPV cities when explicit shelling threat is mentioned
        if 'обстріл' in l or 'обстрел' in l or 'загроза обстрілу' in l or 'угроза обстрела' in l:
            # print(f"[CLASSIFY DEBUG] Classified as artillery")
            return 'artillery', 'obstril.png'

        # Special override for specific cities - Kherson, Nikopol, Marhanets always get FPV icon
        city_lower = city_context.lower() if city_context else ""
        fpv_cities = ['херсон', 'никополь', 'нікополь', 'марганець', 'марганец']

        # Check both city context and message text for FPV cities
        if any(fpv_city in city_lower for fpv_city in fpv_cities) or any(fpv_city in l for fpv_city in fpv_cities):
            return 'fpv', 'fpv.png'
        # Recon / розвід дрони -> use pvo icon (rozvedka2.png) per user request - PRIORITY: check BEFORE general БПЛА
        if 'розвід' in l or 'розвідуваль' in l or 'развед' in l:
            return 'rozved', 'rozvedka2.png'
        # PRIORITY: КАБы (управляемые авиационные бомбы) -> icon_missile.svg - check BEFORE пуски to avoid misclassification
        if any(k in l for k in ['каб','kab','умпк','umpk','модуль','fab','умпб','фаб','кабу']) or \
           ('авіаційн' in l and 'бомб' in l) or ('керован' in l and 'бомб' in l):
            return 'kab', 'icon_missile.svg'
        # Launch site detections for explicit "Пуск ... (РФ)" style messages
        # Examples: "Пуск Приморськ-Ахтарська (РФ)", "Пуск Халино (РФ)", "Пуск Орел-Південний (РФ)", "Пуск Курська (РФ)"
        launch_locations = [
            'приморськ-ахтарськ', 'приморськ-ахтарська', 'приморсько-ахтарськ', 'приморсько-ахтарська',
            'приморск-ахтарск', 'приморск-ахтарская', 'приморско-ахтарск', 'приморско-ахтарская',
            'халино', 'орел-південний', 'орел-южный', 'курськ', 'курська', 'курск', 'курской', 'курскую'
        ]
        if ('пуск' in l or 'пуски' in l) and (('рф' in l) or any(loc in l for loc in launch_locations)):
            return 'pusk', 'pusk.png'
        # Launch site detections for Shahed / UAV launches ("пуски" + origin phrases). User wants pusk.png marker.
        # Exclude КАБ launches - they should be classified as КАБ, not пуски
        if ('пуск' in l or 'пуски' in l) and (any(k in l for k in ['shahed','шахед','шахеді','шахедів','бпла','uav','дрон']) or ('аеродром' in l) or ('аэродром' in l)) and not any(k in l for k in ['каб','kab','умпк','fab','фаб']):
            return 'pusk', 'pusk.png'
        # Explicit launches from occupied Berdyansk airbase (Запорізька область) should also show as pusk (not avia)
        if ('пуск' in l or 'пуски' in l) and 'бердян' in l and ('авіабаз' in l or 'аеродром' in l or 'авиабаз' in l):
            return 'pusk', 'pusk.png'
        # Air alarm start
        if ('повітряна тривога' in l or 'повітряна тривога.' in l or ('тривога' in l and 'повітр' in l)) and not ('відбій' in l or 'отбой' in l):
            return 'alarm', 'trivoga.png'
        # Air alarm cancellation
        if ('відбій тривоги' in l) or ('отбой тревоги' in l):
            return 'alarm_cancel', 'vidboi.png'
        # Explosions reporting -> vibuh icon (cover broader fixation phrases)
        if ('повідомляють про вибух' in l or 'повідомлено про вибух' in l or 'зафіксовано вибух' in l or 'зафіксовано вибухи' in l
            or 'фіксація вибух' in l or 'фіксують вибух' in l or re.search(r'\b(вибух|вибухи|вибухів)\b', l)):
            return 'vibuh', 'vibuh.png'
        # Alarm cancellation (відбій тривоги / отбой тревоги)
        if ('відбій' in l and 'тривог' in l) or ('отбой' in l and 'тревог' in l):
            print("[CLASSIFY DEBUG] Classified as alarm_cancel")
            return 'alarm_cancel', 'vidboi.png'

        # PRIORITY: High-speed targets / missile threats with rocket emoji (🚀) -> icon_balistic.svg
        # This should have priority over drones to handle missile-like threats with rocket emoji
        if '🚀' in th or any(k in l for k in ['ціль','цілей','цілі','високошвидкісн','high-speed']):
            print("[CLASSIFY DEBUG] Classified as raketa (high-speed targets/rocket emoji)")
            return 'raketa', 'icon_balistic.svg'

        # PRIORITY: drones (частая путаница). Если присутствуют слова шахед/бпла/дрон -> это shahed
        if any(k in l for k in ['shahed','шахед','шахеді','шахедів','geran','герань','дрон','дрони','бпла','uav']):
            print("[CLASSIFY DEBUG] Classified as shahed (drones/UAV)")
            return 'shahed', 'shahed3.webp'
        # PRIORITY: Aircraft activity & tactical aviation (avia) -> avia.png (jets, tactical aviation, но БЕЗ КАБов)
        if any(k in l for k in ['літак','самол','avia','tactical','тактичн','fighter','истребит','jets']) or \
           ('авіаційн' in l and ('засоб' in l or 'ураж' in l)):
            return 'avia', 'avia.png'
        # Rocket / missile attacks (ракета, ракети) -> icon_balistic.svg
        if any(k in l for k in ['ракет','rocket','міжконтинент','межконтинент','балістичн','крилат','cruise']):
            return 'raketa', 'icon_balistic.svg'
        # РСЗВ (MLRS, град, ураган, смерч) -> icon_missile.svg
        if any(k in l for k in ['рсзв','mlrs','град','ураган','смерч','рсув','tор','tорнадо','торнадо']):
            return 'rszv', 'icon_missile.svg'
        # Korabel (naval/ship-related threats) -> use icon_balistic.svg as fallback
        if any(k in l for k in ['корабел','флот','корабл','ship','fleet','морськ','naval']):
            return 'raketa', 'icon_balistic.svg'
        # Artillery
        if any(k in l for k in ['арт','artillery','гармат','гаубиц','минометн','howitzer']):
            return 'artillery', 'artillery.png'
        # PVO (air defense activity) -> use vidboi.png as fallback
        if any(k in l for k in ['ппо','pvo','defense','оборон','зенітн','с-','patriot']):
            return 'vidboi', 'vidboi.png'
        # Naval mines -> use icon_balistic.svg as fallback
        if any(k in l for k in ['міна','мін ','mine','neptun','нептун','противокорабел']):
            return 'raketa', 'icon_balistic.svg'
        # FPV drones -> fpv.png
        if any(k in l for k in ['fpv','фпв','камікадз','kamikaze']):
            print("[CLASSIFY DEBUG] Classified as fpv")
            return 'fpv', 'fpv.png'

        # General fallback for unclassified threats
        print("[CLASSIFY DEBUG] Using default fallback: shahed")
        return 'shahed', 'shahed3.webp'  # default fallback

    # PRIORITY CHECK: District-level UAV messages (e.g., "вишгородський р-н київська обл.")
    # Added after classify function to ensure it's available
    lower_text = original_text.lower()
    district_pattern = re.compile(r'([а-яіїєґ\'\-\s]+ський|[а-яіїєґ\'\-\s]+цький)\s+р[-\s]*н\s+([а-яіїєґ\'\-\s]+(?:обл\.?|область|щина))', re.IGNORECASE)
    district_match = district_pattern.search(lower_text)

    if district_match and 'бпла' in lower_text:
        district_raw = district_match.group(1).strip()
        region_raw = district_match.group(2).strip()

        add_debug_log(f"DISTRICT UAV: found '{district_raw} р-н {region_raw}'", "district_uav")

        # Try to map district to city coordinates
        district_city = district_raw.replace('ський', '').replace('цький', '').strip()

        # Check if we have coordinates for this district city
        coords = CITY_COORDS.get(district_city)
        if not coords and district_city in UA_CITY_NORMALIZE:
            coords = CITY_COORDS.get(UA_CITY_NORMALIZE[district_city])

        if coords:
            lat, lng = coords
            threat_type, icon = classify(original_text, district_city)

            # Create district-level marker
            district_track = {
                'id': f"{mid}_district",
                'place': f"{district_city.title()} ({district_raw} р-н)",
                'lat': lat,
                'lng': lng,
                'threat_type': threat_type,
                'text': original_text[:500],
                'date': date_str,
                'channel': channel,
                'marker_icon': icon,
                'source_match': 'district_priority_uav',
                'count': 1
            }

            add_debug_log(f"DISTRICT UAV SUCCESS: {district_city} -> {coords}", "district_uav")
            return [district_track]
        else:
            add_debug_log(f"DISTRICT UAV: No coords for '{district_city}'", "district_uav")

    # PRIORITY CHECK: Single-region numbered UAV lists (н.п. patterns)
    # For messages like "Київщина:\n• н.п. Бровари - постійна загроза БпЛА"
    lower_text = original_text.lower()
    text_lines = original_text.split('\n')

    # Check if this is a single-region message with numbered н.п. cities
    region_lines = [line for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:']) and line.strip().endswith(':')]
    np_lines = [line for line in text_lines if ('н.п.' in line.lower() or 'н. п.' in line.lower()) and 'бпла' in line.lower()]

    if len(region_lines) == 1 and len(np_lines) >= 1:  # Single region with н.п. cities
        region_line = region_lines[0]
        region_name = region_line.replace(':', '').strip()

        add_debug_log(f"SINGLE-REGION NUMBERED: found {len(np_lines)} н.п. cities in {region_name}", "single_region_numbered")

        numbered_tracks = []
        for i, line in enumerate(np_lines):
            # Extract city name from н.п. pattern
            np_match = re.search(r'н\.?\s*п\.?\s+([а-яіїєґ\'\-\s]+)', line.lower())
            if np_match:
                city_name_raw = np_match.group(1).strip()
                # Clean up - take only the city name before any separators
                city_name = city_name_raw.split(' - ')[0].split(' –')[0].split(' ')[0].strip()

                # Try to find coordinates for this city
                coords = CITY_COORDS.get(city_name)
                if not coords and city_name in UA_CITY_NORMALIZE:
                    coords = CITY_COORDS.get(UA_CITY_NORMALIZE[city_name])

                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(line, city_name)

                    numbered_tracks.append({
                        'id': f"{mid}_np_{i+1}",
                        'place': f"{city_name.title()} ({region_name})",
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': line[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': 'single_region_numbered_np',
                        'count': 1
                    })
                    add_debug_log(f"NUMBERED UAV SUCCESS: {city_name} -> {coords}", "single_region_numbered")
                else:
                    # Fallback to region coordinates if city not found
                    region_key = region_name.lower().replace('щина', '').replace('область', '').strip()
                    region_coords = CITY_COORDS.get(region_key)
                    if region_coords:
                        lat, lng = region_coords
                        threat_type, icon = classify(line)

                        numbered_tracks.append({
                            'id': f"{mid}_np_fallback_{i+1}",
                            'place': f"{region_name} (н.п. {city_name.title()})",
                            'lat': lat,
                            'lng': lng,
                            'threat_type': threat_type,
                            'text': line[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'single_region_numbered_np_fallback',
                            'count': 1
                        })
                        add_debug_log(f"NUMBERED UAV FALLBACK: {city_name} -> {region_name} {region_coords}", "single_region_numbered")

        if numbered_tracks:
            add_debug_log(f"SINGLE-REGION NUMBERED SUCCESS: {len(numbered_tracks)} markers created", "single_region_numbered")
            return numbered_tracks

    # HIGHEST PRIORITY: Check for region-district patterns immediately
    import re as _re_priority
    region_district_pattern = _re_priority.compile(r'([а-яіїєґ]+щин[ауи]?)\s*\(\s*([а-яіїєґ\'\-\s]+)\s+р[-\s]*н\)', _re_priority.IGNORECASE)
    region_district_match = region_district_pattern.search(original_text)

    if region_district_match:
        region_raw, district_raw = region_district_match.groups()
        target_city = district_raw.strip()

        add_debug_log(f"PRIORITY REGION-DISTRICT pattern FOUND: region='{region_raw}', district='{district_raw}'", "priority_region_district")

        # Normalize city name and try to find coordinates via API
        city_norm = target_city.lower()
        # Apply UA_CITY_NORMALIZE rules if available
        if 'UA_CITY_NORMALIZE' in globals():
            city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)

        # Use API geocoding with message context
        coords_result = ensure_city_coords_with_message_context(city_norm, original_text)
        coords = (coords_result[0], coords_result[1]) if coords_result else None

        add_debug_log(f"Priority district city API lookup: '{target_city}' -> '{city_norm}' -> {coords}", "priority_region_district")

        if coords:
            lat, lng = coords
            threat_type, icon = classify(original_text)

            priority_result = [{
                'id': f"{mid}_priority_district",
                'place': target_city.title(),
                'lat': lat,
                'lng': lng,
                'threat_type': threat_type,
                'text': original_text[:500],
                'date': date_str,
                'channel': channel,
                'marker_icon': icon,
                'source_match': 'priority_region_district',
                'count': 1
            }]
            add_debug_log(f"Created PRIORITY region-district marker: {target_city.title()}", "priority_region_district")

            # Store priority result globally for combination with other results
            globals()['_current_priority_result'] = priority_result

            # Store priority result and continue with normal processing to catch other cities
            # This allows other parsers to find additional cities in the same message
        else:
            add_debug_log(f"No coordinates found for priority district city: '{target_city}' (normalized: '{city_norm}')", "priority_region_district")
            priority_result = None
    else:
        priority_result = None

    # ВСЕГДА логируем каждое входящее сообщение для отладки
    try:
        add_debug_log(f"process_message called - mid={mid}, channel={channel}, text_length={len(text or '')}", "message_processing")
        add_debug_log(f"message text preview: {(text or '')[:200]}...", "message_processing")
        # Check if this is our test message
        if 'чернігівщина' in (text or '').lower() and 'сумщина' in (text or '').lower():
            add_debug_log("MULTI-REGION MESSAGE DETECTED!", "multi_region")
            add_debug_log(f"Full text: {text}", "multi_region")
    except Exception:
        pass

    # PRIORITY: Handle emoji + city + oblast format BEFORE any other processing
    try:
        import re  # Import re module for pattern matching
        head = text.split('\n', 1)[0][:160] if text else ""

        # Handle general emoji + city + oblast format with any UAV threat (more flexible pattern)
        # NOTE: ʼ (U+02BC), ʻ (U+02BB), ` are Ukrainian apostrophe variants
        general_emoji_pattern = r'^[^\w\s]*\s*([А-ЯІЇЄЁа-яіїєё\'ʼʻ`\-\s]+)\s*\(([^)]*обл[^)]*)\)'
        general_emoji_match = re.search(general_emoji_pattern, head, re.IGNORECASE)
        add_debug_log(f"PRIORITY: Testing general emoji pattern on head: {repr(head)}", "emoji_debug")
        add_debug_log(f"PRIORITY: General emoji match result: {general_emoji_match}", "emoji_debug")

        if general_emoji_match and any(uav_word in text.lower() for uav_word in ['бпла', 'дрон', 'шахед', 'активність', 'загроза', 'тривога', 'обстріл', 'обстрел']):
            city_from_general = general_emoji_match.group(1).strip()
            oblast_from_general = general_emoji_match.group(2).strip()

            # Strip UAV-related prefixes from city name (БПЛА, дрон, шахед, etc.)
            uav_prefixes = ['бпла', 'дрон', 'дрони', 'шахед', 'шахеди', 'безпілотник', 'безпілотники', 'ворожий', 'ворожі']
            city_lower = city_from_general.lower()
            for prefix in uav_prefixes:
                if city_lower.startswith(prefix + ' '):
                    city_from_general = city_from_general[len(prefix):].strip()
                    city_lower = city_from_general.lower()
                    add_debug_log(f"PRIORITY: Stripped UAV prefix '{prefix}', city now: {repr(city_from_general)}", "emoji_debug")

            # Strip course/direction suffixes from city name
            city_from_general = re.sub(r'\s+(курсом|курс|напрям(?:ком)?|в\s+напрямку|у\s+напрямку)\s+.+$', '', city_from_general, flags=re.IGNORECASE).strip()

            add_debug_log(f"PRIORITY: Found city: {repr(city_from_general)}, oblast: {repr(oblast_from_general)}", "emoji_debug")

            if city_from_general and 2 <= len(city_from_general) <= 40:
                base = city_from_general.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                base = re.sub(r'\s+',' ', base)
                norm = UA_CITY_NORMALIZE.get(base, base)

                # Extract region name from oblast string for OpenCage
                oblast_key = oblast_from_general.lower()
                region_for_geocode = oblast_key.replace(' обл.', '').replace(' обл', '').replace('область', '').strip()
                
                # ONLY OpenCage API - no local dictionaries!
                # Build context with explicit oblast
                context_text = f"{city_from_general} ({oblast_from_general})"
                coords = ensure_city_coords_with_message_context(norm, context_text)
                add_debug_log(f"PRIORITY: OpenCage lookup: city={repr(norm)}, region={repr(region_for_geocode)}, coords={coords}", "emoji_debug")

                if coords:
                    lat, lon = coords[:2]

                    # Check for threat cancellation BEFORE creating marker
                    text_lower = text.lower()
                    if ('відбій загрози' in text_lower or
                        'відбій тривоги' in text_lower or
                        ('відбій' in text_lower and any(cancel_word in text_lower for cancel_word in ['загрози', 'тривоги']))):
                        # This is a cancellation message - create list_only entry, no map marker
                        track = {
                            'id': f"{mid}_priority_emoji_cancel_{city_from_general.replace(' ','_')}",
                            'place': city_from_general.title(),
                            'threat_type': 'alarm_cancel',
                            'text': clean_text(text)[:500],
                            'date': date_str,
                            'channel': channel,
                            'list_only': True,  # NO map marker for cancellation
                            'source_match': 'priority_emoji_cancel'
                        }
                        add_debug_log(f'PRIORITY CANCELLATION: {city_from_general} -> list_only=True (no marker)', "emoji_debug")
                        return [track]  # Early return - cancellation handled

                    # Regular threat - create map marker
                    threat_type, icon = classify(text, city_from_general)
                    track = {
                        'id': f"{mid}_priority_emoji_{city_from_general.replace(' ','_')}",
                        'place': city_from_general.title(),
                        'lat': lat, 'lng': lon,
                        'threat_type': threat_type,
                        'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'priority_emoji_threat'
                    }
                    add_debug_log(f'PRIORITY EARLY RETURN: {city_from_general} -> {coords} -> {icon}', "emoji_debug")
                    return [track]  # Early return - highest priority
                else:
                    # NO COORDS FOUND - create list_only entry for push notifications but no map marker
                    threat_type, icon = classify(text, city_from_general)
                    track = {
                        'id': f"{mid}_priority_emoji_nocoords_{city_from_general.replace(' ','_')}",
                        'place': city_from_general.title(),
                        'threat_type': threat_type,
                        'text': clean_text(text)[:500],
                        'date': date_str,
                        'channel': channel,
                        'list_only': True,  # NO map marker - coords not found
                        'source_match': 'priority_emoji_no_coords'
                    }
                    add_debug_log(f'PRIORITY NO COORDS: {city_from_general} -> list_only=True (push will be sent)', "emoji_debug")
                    return [track]
    except Exception as e:
        add_debug_log(f"PRIORITY emoji processing error: {e}", "emoji_debug")

    # PRIORITY: Handle emoji + oblast format (when only oblast is specified, place marker in regional center)
    try:
        import re  # Import re module for pattern matching
        head = text.split('\n', 1)[0][:160] if text else ""

        # Handle emoji + oblast format (e.g. "👁️ Миколаївська обл.")
        oblast_emoji_pattern = r'^[^\w\s]*\s*([А-ЯІЇЄЁа-яіїєё\'\-\s]*обл\.?)\s*\*\*'
        oblast_emoji_match = re.search(oblast_emoji_pattern, head, re.IGNORECASE)
        add_debug_log(f"PRIORITY: Testing oblast emoji pattern on head: {repr(head)}", "emoji_debug")
        add_debug_log(f"PRIORITY: Oblast emoji match result: {oblast_emoji_match}", "emoji_debug")

        if oblast_emoji_match and any(uav_word in text.lower() for uav_word in ['бпла', 'дрон', 'шахед', 'активність', 'загроза', 'тривога']):
            oblast_from_emoji = oblast_emoji_match.group(1).strip()
            add_debug_log(f"PRIORITY: Found oblast from emoji: {repr(oblast_from_emoji)}", "emoji_debug")

            # Map oblast to regional center
            regional_center = None
            coords = None

            oblast_key = oblast_from_emoji.lower()
            if 'миколаївськ' in oblast_key:
                regional_center = 'Миколаїв'
                coords = CITY_COORDS.get('миколаїв')
            elif 'дніпропетровськ' in oblast_key:
                regional_center = 'Дніпро'
                coords = CITY_COORDS.get('дніпро')
            elif 'харківськ' in oblast_key:
                regional_center = 'Харків'
                coords = CITY_COORDS.get('харків')
            elif 'сумськ' in oblast_key:
                regional_center = 'Суми'
                coords = CITY_COORDS.get('суми')
            elif 'херсонськ' in oblast_key:
                regional_center = 'Херсон'
                coords = CITY_COORDS.get('херсон')
            elif 'одеськ' in oblast_key:
                regional_center = 'Одеса'
                coords = CITY_COORDS.get('одеса')
            elif 'запорізьк' in oblast_key:
                regional_center = 'Запоріжжя'
                coords = CITY_COORDS.get('запоріжжя')
            elif 'полтавськ' in oblast_key:
                regional_center = 'Полтава'
                coords = CITY_COORDS.get('полтава')

            add_debug_log(f"PRIORITY: Oblast {oblast_from_emoji} -> regional center {regional_center} -> coords {coords}", "emoji_debug")

            if coords and regional_center:
                lat, lon = coords[:2]
                threat_type, icon = classify(text)
                track = {
                    'id': f"{mid}_priority_oblast_{regional_center.replace(' ','_')}",
                    'place': regional_center,
                    'lat': lat, 'lng': lon,
                    'threat_type': threat_type,
                    'text': text[:160], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'priority_oblast_threat'
                }
                add_debug_log(f'PRIORITY OBLAST EARLY RETURN: {oblast_from_emoji} -> {regional_center} -> {coords} -> {icon}', "emoji_debug")
                return [track]  # Early return - highest priority
    except Exception as e:
        add_debug_log(f"PRIORITY oblast processing error: {e}", "emoji_debug")

    # Continue with existing logic...

    # Strip embedded links (Markdown [text](url) or raw URLs) while keeping core message text.
    # Requested: if message contains links, remove them but keep the rest.
    try:
        import re as _re_strip  # type: ignore
        if text:
            _orig_text = text
            # Remove markdown links [ ... ](http...). Keep the visible text (group 1) only.
            text = _re_strip.sub(r"\[([^\]]*)\]\((?:https?|tg|mailto)://[^)]+\)", lambda m: (m.group(1) or '').strip(), text)
            # Remove any residual raw URLs (http/https/t.me) leaving a single space
            text = _re_strip.sub(r"https?://\S+", " ", text)
            text = _re_strip.sub(r"t\.me/\S+", " ", text)
            # Remove lone decorative symbols (✙, •, ★) that may have surrounded links
            text = _re_strip.sub(r"[✙•★]{1,}", " ", text)
            # Collapse multiple spaces and trim each line
            cleaned_lines = []
            for _ln in text.splitlines():
                _cl = ' '.join(_ln.split())
                if _cl:
                    cleaned_lines.append(_cl)
            if cleaned_lines:
                text = '\n'.join(cleaned_lines)
            else:
                # If stripping removed everything, fall back to original
                text = _orig_text
    except Exception:
        pass
    # Ensure original_text is defined early to avoid UnboundLocalError in early parsing branches
    original_text = text

    # Special handling for oblast+raion format: "чернігівська область (чернігівський район), київська область (вишгородський район)"
    import re as _re_oblast
    oblast_raion_pattern = r'([а-яіїєґ]+ська\s+область)\s*\(([^)]*?райони?[^)]*?)\)'
    oblast_raion_matches = _re_oblast.findall(oblast_raion_pattern, text.lower(), _re_oblast.IGNORECASE)

    # Also check for pattern without requiring "райони" in parentheses - some messages might have just names
    if not oblast_raion_matches:
        oblast_raion_pattern_simple = r'([а-яіїєґ]+ська\s+область)\s*\(([^)]+)\)'
        oblast_raion_matches_simple = _re_oblast.findall(oblast_raion_pattern_simple, text.lower(), _re_oblast.IGNORECASE)
        # Filter to only those that contain district-like words
        oblast_raion_matches = [(oblast, raion) for oblast, raion in oblast_raion_matches_simple
                               if any(word in raion for word in ['район', 'р-н', 'ський', 'цький'])]

    add_debug_log(f"Oblast+raion pattern check: found {len(oblast_raion_matches)} matches in text: {text[:200]}...", "oblast_raion")

    if oblast_raion_matches and any(word in text.lower() for word in ['бпла', 'загроза', 'укриття']):
        add_debug_log(f"Oblast+raion format detected: {oblast_raion_matches}", "oblast_raion")
        tracks = []

        for oblast_text, raion_text in oblast_raion_matches:
            add_debug_log(f"Processing oblast: '{oblast_text}', raion_text: '{raion_text}'", "oblast_raion")
            # Extract individual raions from the parentheses
            # Handle both single and multiple raions: "сумський, конотопський райони"
            raion_parts = _re_oblast.split(r',\s*|\s+та\s+', raion_text)
            add_debug_log(f"Split raion_parts: {raion_parts}", "oblast_raion")

            for raion_part in raion_parts:
                raion_part = raion_part.strip()
                if not raion_part:
                    continue

                add_debug_log(f"Processing raion_part: '{raion_part}'", "oblast_raion")

                # Extract raion name (remove "район"/"райони" suffix)
                raion_name = _re_oblast.sub(r'\s*(райони?|р-н\.?).*$', '', raion_part).strip()
                add_debug_log(f"After removing suffix, raion_name: '{raion_name}'", "oblast_raion")

                # Normalize raion name
                raion_normalized = _re_oblast.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_name)
                add_debug_log(f"Normalized raion: '{raion_normalized}', checking in RAION_FALLBACK", "oblast_raion")

                if raion_normalized in RAION_FALLBACK:
                    lat, lng = RAION_FALLBACK[raion_normalized]
                    add_debug_log(f"Creating oblast+raion marker: {raion_normalized} at {lat}, {lng}", "oblast_raion")

                    # Use classify function to determine correct threat type and icon
                    threat_type, icon = classify(original_text, raion_normalized)

                    tracks.append({
                        'id': f"{mid}_raion_{raion_normalized}",
                        'place': f"{raion_normalized.title()} район",
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': original_text[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': 'oblast_raion_format'
                    })
                else:
                    add_debug_log(f"Raion not found in RAION_FALLBACK: '{raion_normalized}'. Available keys: {list(RAION_FALLBACK.keys())[:10]}...", "oblast_raion")

        if tracks:
            add_debug_log(f"Returning {len(tracks)} oblast+raion markers", "oblast_raion")
            return tracks

    large_message_mode = False
    LARGE_THRESHOLD = 15000
    HARD_CUTOFF = 40000  # safety to avoid pathological regex backtracking
    parse_started_ts = time.perf_counter()
    if text and len(text) > LARGE_THRESHOLD:
        large_message_mode = True
        orig_len = len(text)
        if orig_len > HARD_CUTOFF:
            # Keep head + tail slices to retain some closing context
            head = text[:HARD_CUTOFF//2]
            tail = text[-2000:]
            text = head + "\n...TRUNCATED...\n" + tail
            log.debug(f"mid={mid} large_message_mode truncation {orig_len}->{len(text)} chars")
        else:
            log.debug(f"mid={mid} large_message_mode len={orig_len}")
        # Quick complexity metrics
        try:
            lc = text.lower()
            metrics = {
                'len': orig_len,
                'lines': text.count('\n') + 1,
                'bpla': lc.count('бпла'),
                'shahed': lc.count('шахед'),
                'course': lc.count('курс'),
                'napr': lc.count('напрям') + lc.count('напрямку')
            }
            log.debug(f"mid={mid} large_msg_metrics {metrics}")
        except Exception:
            pass
        # Pre-scan chunk optimization: if many repeated 'бпла курсом на', extract tokens fast before heavy regex blocks
        try:
            if text.lower().count('курс') > 8 and text.lower().count('бпла') > 8:
                fast_tokens = []
                for ln in text.split('\n'):
                    lnl = ln.lower()
                    if 'бпла' in lnl and 'курс' in lnl and ' на ' in lnl:
                        # light-weight extraction (avoid complex backtracking)
                        # Regex: capture token after 'курс(ом) на' up to 40 chars (letters, spaces, dashes)
                        m = re.search(r"курс(?:ом)?\s+на\s+([a-zа-яіїєґ\-\s]{3,40})", lnl, re.IGNORECASE)
                        if m:
                            tok = m.group(1).strip()
                            if tok and tok not in fast_tokens:
                                fast_tokens.append(tok)
                if fast_tokens:
                    log.debug(f"mid={mid} pre-scan collected {len(fast_tokens)} fast_tokens (will still run main parser)")
        except Exception as _e_fast:
            log.debug(f"mid={mid} pre-scan error: {_e_fast}")
    # Early benign filter: city name + emojis / hearts without any threat keywords -> ignore
    try:
        lt = (text or '').lower().strip()
        if lt:
            # threat indicator tokens (broad stems)
            threat_tokens = (
                'шахед','shahed','бпла','дрон','ракет','каб','вибух','прил','удар','загроз','тривог',
                'пуск','зліт','злет','avia','авіа','пво','обстр','mlrs','rszv','fpv','артил','зеніт','зенит'
            )
            if not any(t in lt for t in threat_tokens):
                # strip emojis & symbols leaving letters, spaces and apostrophes
                import re as _re_benign
                core = _re_benign.sub(r"[^a-zа-яіїєґ'’ʼ`\s-]","", lt)
                core = ' '.join(core.split())
                # If core matches exactly a known city (or its normalized form) and original text length small -> benign
                if 2 <= len(core) <= 30:
                    base = UA_CITY_NORMALIZE.get(core, core)
                    if base in CITY_COORDS or ('SETTLEMENTS_INDEX' in globals() and (globals().get('SETTLEMENTS_INDEX') or {}).get(base)):
                        # Ignore this message (no tracks)
                        add_debug_log(f"BENIGN FILTER blocked message mid={mid} - detected city name without threats: '{core}'", "filter")
                        return []
            # NEW suppression: reconnaissance-only notes ("дорозвідка по БпЛА") should not produce a marker
            # Pattern triggers if word 'дорозвідк' present together with UAV terms but no other threat verbs
            if 'дорозвідк' in lt and any(k in lt for k in ['бпла','shahed','шахед','дрон']):
                # Avoid suppressing if explosions or launches also present
                if not any(k in lt for k in ['вибух','удар','пуск','прил','обстріл','обстрел','зліт','злет']):
                    add_debug_log(f"RECONNAISSANCE FILTER blocked message mid={mid} - reconnaissance only", "filter")
                    return []
    except Exception:
        pass

    # SPECIAL: Handle multiple threats in one message BEFORE other parsing
    def handle_multiple_threats():
        """Check for messages with multiple different threats and process each separately"""
        all_threats = []
        text_lower = text.lower()

        # 1. Check for northeast tactical aviation threat
        if ('тактичн' in text_lower or 'авіаці' in text_lower or 'авиац' in text_lower) and (
            'північно-східн' in text_lower or 'північно східн' in text_lower or 'северо-восточ' in text_lower or 'північного-сходу' in text_lower
        ):
            lat, lng = 51.0, 36.5  # On Russian territory near Belgorod (before Ukraine border)
            all_threats.append({
                'id': f"{mid}_ne_multi", 'place': 'Північно-східний напрямок', 'lat': lat, 'lng': lng,
                'threat_type': 'avia', 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'avia.png', 'source_match': 'multiple_threats_northeast_aviation'
            })

        # 2. Check for reconnaissance UAV in Mykolaiv oblast (миколаївщини/миколаївщині)
        if ('розвід' in text_lower or 'розведуваль' in text_lower) and ('миколаївщини' in text_lower or 'миколаївщині' in text_lower or 'миколаївщина' in text_lower):
            # Use Mykolaiv city coordinates
            lat, lng = 46.9750, 31.9946
            all_threats.append({
                'id': f"{mid}_mykolaiv_recon", 'place': 'Миколаївщина', 'lat': lat, 'lng': lng,
                'threat_type': 'rozved', 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'rozvedka2.png', 'source_match': 'multiple_threats_mykolaiv_recon'
            })

        # 3. Check for general БПЛА threats in oblast format (миколаївщини/миколаївщині) without "розвід"
        elif ('бпла' in text_lower or 'дрон' in text_lower) and ('миколаївщини' in text_lower or 'миколаївщині' in text_lower or 'миколаївщина' in text_lower):
            lat, lng = 46.9750, 31.9946
            all_threats.append({
                'id': f"{mid}_mykolaiv_uav", 'place': 'Миколаївщина', 'lat': lat, 'lng': lng,
                'threat_type': 'shahed', 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'shahed3.webp', 'source_match': 'multiple_threats_mykolaiv_uav'
            })

        return all_threats

    # Check if this is a multi-threat message
    if '🛬' in text and '🛸' in text:
        multi_threats = handle_multiple_threats()
        if multi_threats:
            add_debug_log(f"MULTIPLE THREATS DETECTED: Found {len(multi_threats)} threats", "multi_threats")
            return multi_threats

    # EARLY CHECK: Multi-regional UAV messages (before other logic can interfere)
    text_lines = text.split('\n')
    region_count = sum(1 for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:', 'край:']) or (
        'щина' in line.lower() and line.lower().strip().endswith(':')
    ))
    uav_count = sum(1 for line in text_lines if 'бпла' in line.lower() and ('курс' in line.lower() or 'на ' in line.lower()))

    if region_count >= 2 and uav_count >= 3:
        add_debug_log(f"EARLY MULTI-REGIONAL UAV DETECTION: {region_count} regions, {uav_count} UAVs", "multi_regional")
        # We'll process this later when all functions are defined
        # Set a flag for now
        multi_regional_flag = True
    else:
        multi_regional_flag = False

    # ... existing parsing logic continues ...
    # At the very end of function (before return default) we'll log duration.
    # Air alarm region/raion tracking (start / cancel) before other parsing
    try:
        low_full = (text or '').lower()
        now_ep = time.time()
        lines = [l.strip() for l in (text or '').split('\n') if l.strip()][:3]
        if lines:
            header = lines[0].lower()
            header_norm = header.replace('область', 'обл.').replace('обл..','обл.')
            # Oblast alarm start: contains '<adj> обл.' and body has 'повітряна тривога'
            if ('повітр' in low_full or 'тривог' in low_full) and ' обл' in header_norm:
                m_obl = re.search(r"([а-яіїєґ\-']+?)\s+обл\.?", header_norm)
                if m_obl:
                    stem = m_obl.group(1)
                    # Match against OBLAST_CENTERS keys
                    for k in OBLAST_CENTERS.keys():
                        if k.startswith(stem):
                            is_new = k not in ACTIVE_OBLAST_ALARMS
                            rec = ACTIVE_OBLAST_ALARMS.setdefault(k, {'since': now_ep, 'last': now_ep})
                            if rec['since'] > now_ep: rec['since'] = now_ep
                            rec['last'] = now_ep
                            persist_alarm('oblast', k, rec['since'], rec['last'])
                            if is_new:
                                log_alarm_event('oblast', k, 'start', now_ep)
                            break
            # Raion alarm start: '<name> район'
            if ('повітр' in low_full or 'тривог' in low_full) and ' район' in header:
                m_r = re.search(r"([а-яіїєґ\-']+?)\s+район", header)
                if m_r:
                    rb = m_r.group(1).replace('’',"'").replace('ʼ',"'")
                    if rb in RAION_FALLBACK:
                        is_new_r = rb not in ACTIVE_RAION_ALARMS
                        rec = ACTIVE_RAION_ALARMS.setdefault(rb, {'since': now_ep, 'last': now_ep})
                        if rec['since'] > now_ep: rec['since'] = now_ep
                        rec['last'] = now_ep
                        persist_alarm('raion', rb, rec['since'], rec['last'])
                        if is_new_r:
                            log_alarm_event('raion', rb, 'start', now_ep)
        # Cancellation lines contain 'відбій тривоги' or 'отбой тревоги'
        if ('відбій' in low_full or 'отбой' in low_full) and ('тривог' in low_full or 'тревог' in low_full):
            # Precise: look for explicit oblast adjectives endings '-ська', '-цька', '-ницька', etc.
            # Pattern: відбій тривоги у / в <word...> області OR '<adj> обл.'
            m_cancel_obl = re.findall(r"(\b[а-яіїєґ\-']+?)(?:ська|цька|ницька|зька|жська)\s+обл(?:асть|\.|)", low_full)
            removed_any = False
            if m_cancel_obl:
                for stem in m_cancel_obl:
                    for k in list(ACTIVE_OBLAST_ALARMS.keys()):
                        if k.startswith(stem):
                            ACTIVE_OBLAST_ALARMS.pop(k, None); remove_alarm('oblast', k); log_alarm_event('oblast', k, 'cancel', now_ep); removed_any=True
            # Raion precise cancel: "відбій тривоги у <name> районі" (locative: -ському / -івському)
            m_cancel_r = re.findall(r"відбій[^\n]*?\b([а-яіїєґ\-']+?)(?:ському|івському|ському)\s+районі", low_full)
            if m_cancel_r:
                for stem in m_cancel_r:
                    for r in list(ACTIVE_RAION_ALARMS.keys()):
                        if r.startswith(stem):
                            ACTIVE_RAION_ALARMS.pop(r, None); remove_alarm('raion', r); log_alarm_event('raion', r, 'cancel', now_ep); removed_any=True
            # Fallback broad cancel if phrase generic and no explicit names matched
            if not removed_any and re.search(r"відбій\s+тривог|отбой\s+тревог", low_full):
                # remove all (global відбій)
                for k in list(ACTIVE_OBLAST_ALARMS.keys()):
                    ACTIVE_OBLAST_ALARMS.pop(k, None); remove_alarm('oblast', k); log_alarm_event('oblast', k, 'cancel', now_ep)
                for r in list(ACTIVE_RAION_ALARMS.keys()):
                    ACTIVE_RAION_ALARMS.pop(r, None); remove_alarm('raion', r); log_alarm_event('raion', r, 'cancel', now_ep)
        # Expire stale
        ttl_cut = now_ep - APP_ALARM_TTL_MINUTES*60
        for dct in (ACTIVE_OBLAST_ALARMS, ACTIVE_RAION_ALARMS):
            for k in list(dct.keys()):
                if dct[k]['last'] < ttl_cut:
                    level = 'oblast' if dct is ACTIVE_OBLAST_ALARMS else 'raion'
                    dct.pop(k, None)
                    remove_alarm(level, k)
                    log_alarm_event(level, k, 'expire', now_ep)
    except Exception as _e_alarm:
        log.debug(f'alarm tracking block error: {_e_alarm}')
    # Early single-city (bold/emoji tolerant) parser
    try:
        orig = text
        head = orig.split('\n',1)[0][:160]
        
        # DEBUG: Log incoming message for mapstransler parsing
        print(f"[PARSER_DEBUG] Processing message: {repr(head[:80])}...")

        # PRIORITY: Handle mapstransler_bot format: "[count]х БПЛА/КАБ/Ракета Місто (Область обл.)"
        # Examples:
        #   "2х БПЛА Барвінкове (Харківська обл.) Загроза застосування БПЛА."
        #   "БПЛА Єланець (Миколаївська обл.) Загроза застосування БПЛА."
        #   "КАБ Вовчанськ (Харківська обл.)"
        #   "Ракета Запоріжжя (Запорізька обл.)"
        #   "Димер (Київська обл.) Загроза застосування БПЛА."
        #   "БПЛА Федорівку/Піщане (Харківська обл.)" - multiple cities with /
        #   "БПЛА Вільхівку⚠ (Харківська обл.)" - emoji after city name
        # Note: [^(]* allows any chars (including emoji) between city name and (
        # THREAT_TYPES: БПЛА, КАБ, Ракета, Шахед, Дрон
        # NOTE: ʼ is U+02BC (modifier letter apostrophe), ʻ is U+02BB - both used in Ukrainian
        threat_type_pattern = r'(?:БПЛА|КАБ|Ракета|Ракети|Шахед|Дрон|Дрони)'
        mapstransler_pattern = rf'^[^\w]*(\d+)[xх×]?\s*{threat_type_pattern}\s+([А-ЯІЇЄЁа-яіїєё\'\'\ʼʻ`\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)'
        mapstransler_match = re.search(mapstransler_pattern, head, re.IGNORECASE)

        # Also try without count prefix
        if not mapstransler_match:
            mapstransler_pattern2 = rf'^[^\w]*{threat_type_pattern}\s+([А-ЯІЇЄЁа-яіїєё\'\'\ʼʻ`\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)'
            mapstransler_match2 = re.search(mapstransler_pattern2, head, re.IGNORECASE)
            if mapstransler_match2:
                city_raw = mapstransler_match2.group(1).strip()
                oblast_raw = mapstransler_match2.group(2).strip()
                uav_count = 1
            else:
                city_raw = None
                oblast_raw = None
                uav_count = 1
        else:
            uav_count = int(mapstransler_match.group(1))
            city_raw = mapstransler_match.group(2).strip()
            oblast_raw = mapstransler_match.group(3).strip()

        # Handle multiple cities separated by / (take first one)
        if city_raw and '/' in city_raw:
            cities_list = city_raw.split('/')
            city_raw = cities_list[0].strip()  # Take first city
            add_debug_log(f"Multiple cities in message, using first: '{city_raw}' from {cities_list}", "mapstransler")

        # Also try format without БПЛА prefix: "Димер (Київська обл.) Загроза..."
        if not city_raw:
            no_bpla_pattern = r'^[^\w]*([А-ЯІЇЄЁа-яіїєё][А-ЯІЇЄЁа-яіїєё\'\'\ʼʻ`\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)\s*загроза'
            no_bpla_match = re.search(no_bpla_pattern, head, re.IGNORECASE)
            if no_bpla_match:
                city_raw = no_bpla_match.group(1).strip()
                # Handle multiple cities
                if '/' in city_raw:
                    city_raw = city_raw.split('/')[0].strip()
                oblast_raw = no_bpla_match.group(2).strip()
                uav_count = 1
                print(f"[PARSER_DEBUG] no_bpla_pattern matched: city='{city_raw}', oblast='{oblast_raw}'")

        if city_raw and oblast_raw:
            print(f"[PARSER_DEBUG] mapstransler MATCHED: city='{city_raw}', oblast='{oblast_raw}', count={uav_count}")
            # Strip course/direction suffixes from city name before normalization
            city_raw = re.sub(r'\s+(курсом|курс|напрям(?:ком)?|в\s+напрямку|у\s+напрямку)\s+.+$', '', city_raw, flags=re.IGNORECASE).strip()
            # Strip "район" suffix - e.g., "Богодухів район" -> "Богодухів"
            city_raw = re.sub(r'\s+район\s*$', '', city_raw, flags=re.IGNORECASE).strip()
            print(f"[PARSER_DEBUG] After cleanup: city='{city_raw}'")
            # Normalize city name (accusative -> nominative) - COMPREHENSIVE
            city_norm = city_raw.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
            city_norm = re.sub(r'\s+',' ', city_norm).strip()

            # Store original for API search
            city_original = city_norm

            # COMPOUND NAMES: Handle "Adjective + Noun" patterns (e.g., "Малу Дівицю" -> "Мала Дівиця")
            # Split into words and normalize each
            words = city_norm.split()
            if len(words) == 2:
                adj, noun = words[0], words[1]

                # Normalize adjective (feminine accusative -> nominative)
                # -у → -а (Малу → Мала, Велику → Велика, Нову → Нова)
                if adj.endswith('у') and len(adj) > 3:
                    adj = adj[:-1] + 'а'
                # -ю → -я (Синю → Синя)
                elif adj.endswith('ю') and len(adj) > 3:
                    adj = adj[:-1] + 'я'

                # Normalize noun
                # -ку → -ка (Дівицку → Дівицка? No, Дівицю → Дівиця)
                if noun.endswith('ку') and len(noun) > 4:
                    noun = noun[:-2] + 'ка'
                elif noun.endswith('цю') and len(noun) > 3:
                    noun = noun[:-1] + 'я'  # Дівицю → Дівиця
                elif noun.endswith('ну') and len(noun) > 4:
                    noun = noun[:-2] + 'на'
                elif noun.endswith('у') and len(noun) > 3:
                    noun = noun[:-1] + 'а'
                elif noun.endswith('ю') and len(noun) > 3:
                    noun = noun[:-1] + 'я'

                city_norm = f"{adj} {noun}"
            else:
                # Single word - apply standard normalization
                # -ку → -ка (Юріївку → Юріївка, Сахновщину → Сахновщина)
                if city_norm.endswith('ку') and len(city_norm) > 4:
                    city_norm = city_norm[:-2] + 'ка'
                # -ну → -на (Сахновщину → Сахновщина)
                elif city_norm.endswith('ну') and len(city_norm) > 4:
                    city_norm = city_norm[:-2] + 'на'
                # -у → -а (Одесу → Одеса)
                elif city_norm.endswith('у') and len(city_norm) > 3:
                    city_norm = city_norm[:-1] + 'а'
                # -ю → -я (Балаклію → Балаклія)
                elif city_norm.endswith('ю') and len(city_norm) > 3:
                    city_norm = city_norm[:-1] + 'я'

            city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)

            # Extract oblast name for Photon API filtering
            oblast_lower = oblast_raw.lower()
            oblast_to_state = {
                'дніпропетровська': 'Дніпропетровська область',
                'харківська': 'Харківська область',
                'київська': 'Київська область',
                'чернігівська': 'Чернігівська область',
                'сумська': 'Сумська область',
                'полтавська': 'Полтавська область',
                'миколаївська': 'Миколаївська область',
                'одеська': 'Одеська область',
                'херсонська': 'Херсонська область',
                'запорізька': 'Запорізька область',
                'донецька': 'Донецька область',
                'луганська': 'Луганська область',
                'черкаська': 'Черкаська область',
                'вінницька': 'Вінницька область',
                'житомирська': 'Житомирська область',
                'рівненська': 'Рівненська область',
                'волинська': 'Волинська область',
                'львівська': 'Львівська область',
                'тернопільська': 'Тернопільська область',
                'хмельницька': 'Хмельницька область',
                'івано-франківська': 'Івано-Франківська область',
                'закарпатська': 'Закарпатська область',
                'чернівецька': 'Чернівецька область',
                'кіровоградська': 'Кіровоградська область',
            }

            target_state = None
            for key, state in oblast_to_state.items():
                if key in oblast_lower:
                    target_state = state
                    break

            add_debug_log(f"Mapstransler pattern: city='{city_raw}' -> norm='{city_norm}', oblast='{oblast_raw}' -> state='{target_state}', count={uav_count}", "mapstransler")

            coords = None

            # Check in-memory cache first
            cache_key = f"{city_norm}|{target_state}"
            
            # MEMORY PROTECTION: Limit cache size
            if len(_mapstransler_geocode_cache) >= _mapstransler_cache_max_size:
                # Remove ~half of the cache (oldest entries - FIFO approximation)
                keys_to_remove = list(_mapstransler_geocode_cache.keys())[:_mapstransler_cache_max_size // 2]
                for k in keys_to_remove:
                    del _mapstransler_geocode_cache[k]
            
            if cache_key in _mapstransler_geocode_cache:
                cached = _mapstransler_geocode_cache[cache_key]
                if cached:
                    coords = cached
                    add_debug_log(f"Cache HIT: {city_norm} -> ({coords[0]}, {coords[1]})", "mapstransler")
                else:
                    add_debug_log(f"Cache HIT (negative): {city_norm} not found previously", "mapstransler")

            # ONLY OpenCage API - no local dictionaries!
            if not coords and cache_key not in _mapstransler_geocode_cache and GEOCODER_AVAILABLE:
                try:
                    # Use target_state directly (with "область") for better disambiguation
                    # OpenCage understands "Дніпропетровська область" better than just "Дніпропетровська"
                    region_for_geocode = target_state if target_state else None
                    
                    opencage_coords = opencage_geocode(city_norm, region=region_for_geocode)
                    if opencage_coords:
                        coords = opencage_coords
                        _mapstransler_geocode_cache[cache_key] = coords
                        add_debug_log(f"OpenCage: '{city_norm}' with region '{region_for_geocode}' -> {coords}", "mapstransler")
                except Exception as e:
                    add_debug_log(f"OpenCage error: {e}", "mapstransler")

            # Save to cache (both positive and negative results)
            if coords:
                _mapstransler_geocode_cache[cache_key] = coords
                add_debug_log(f"Cache SAVED: {city_norm} -> ({coords[0]}, {coords[1]})", "mapstransler")
            elif cache_key not in _mapstransler_geocode_cache:
                _mapstransler_geocode_cache[cache_key] = None  # Negative cache
                add_debug_log(f"Cache SAVED (negative): {city_norm} not found", "mapstransler")

            # FALLBACK TO OBLAST CENTER if city not found
            if not coords and target_state:
                # Oblast center coordinates (approximate)
                oblast_centers = {
                    'Дніпропетровська область': (48.4647, 35.0462),
                    'Харківська область': (50.0047, 36.2314),
                    'Київська область': (50.4501, 30.5234),
                    'Чернігівська область': (51.4982, 31.2893),
                    'Сумська область': (50.9077, 34.7981),
                    'Полтавська область': (49.5883, 34.5514),
                    'Миколаївська область': (46.9750, 31.9946),
                    'Одеська область': (46.4825, 30.7233),
                    'Херсонська область': (46.6354, 32.6169),
                    'Запорізька область': (47.8388, 35.1396),
                    'Донецька область': (48.0159, 37.8029),
                    'Луганська область': (48.5740, 39.3078),
                    'Черкаська область': (49.4444, 32.0598),
                    'Вінницька область': (49.2331, 28.4682),
                    'Житомирська область': (50.2547, 28.6587),
                    'Рівненська область': (50.6199, 26.2516),
                    'Волинська область': (50.7472, 25.3254),
                    'Львівська область': (49.8397, 24.0297),
                    'Тернопільська область': (49.5535, 25.5948),
                    'Хмельницька область': (49.4229, 26.9871),
                    'Івано-Франківська область': (48.9226, 24.7111),
                    'Закарпатська область': (48.6208, 22.2879),
                    'Чернівецька область': (48.2921, 25.9358),
                    'Кіровоградська область': (48.5079, 32.2623),
                }
                fallback_coords = oblast_centers.get(target_state)
                if fallback_coords:
                    # Add small random offset so multiple fallbacks don't overlap
                    import random
                    offset_lat = random.uniform(-0.15, 0.15)
                    offset_lng = random.uniform(-0.15, 0.15)
                    coords = (fallback_coords[0] + offset_lat, fallback_coords[1] + offset_lng)
                    add_debug_log(f"FALLBACK to oblast center: {city_raw} ({target_state}) -> {coords}", "mapstransler")

            if not coords:
                add_debug_log(f"City NOT FOUND, no fallback: {city_raw} ({oblast_raw})", "mapstransler")

            if coords:
                if len(coords) == 3:
                    lat, lon = coords[0], coords[1]
                else:
                    lat, lon = coords[:2]

                threat_type, icon = classify(text)
                track = {
                    'id': f"{mid}_mapstransler_{city_norm.replace(' ','_')}",
                    'place': city_raw.title(),
                    'lat': lat, 'lng': lon,
                    'threat_type': threat_type,
                    'text': clean_text(orig)[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'mapstransler_format',
                    'count': uav_count
                }
                add_debug_log(f'Mapstransler parser SUCCESS: {city_raw} ({oblast_raw}) -> {coords}, count={uav_count}', "mapstransler")
                return [track]  # Early return
            else:
                add_debug_log(f'Mapstransler parser: No coords for {city_norm} ({oblast_raw})', "mapstransler")

        # NEW: Handle emoji-prefixed threat messages like "🛸 Звягель (Житомирська обл.) Загроза застосування БПЛА"
        # NOTE: ʼ (U+02BC), ʻ (U+02BB), ` are Ukrainian apostrophe variants
        emoji_threat_pattern = r'^[^\w\s]*\s*([А-ЯІЇЄЁа-яіїєё\'ʼʻ`\-\s]+)\s*\([^)]*обл[^)]*\)\s*загроза\s+застосування\s+бпла'
        emoji_match = re.search(emoji_threat_pattern, head, re.IGNORECASE)
        if emoji_match:
            city_from_emoji = emoji_match.group(1).strip()
            if city_from_emoji and 2 <= len(city_from_emoji) <= 40:
                base = city_from_emoji.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                base = re.sub(r'\s+',' ', base)
                norm = UA_CITY_NORMALIZE.get(base, base)
                
                # ONLY OpenCage API
                coords = None
                if GEOCODER_AVAILABLE:
                    oblast_match = re.search(r'\(([А-Яа-яЇїІіЄєҐґ\-]+)\s*обл', head, re.IGNORECASE)
                    region_for_geocode = oblast_match.group(1) if oblast_match else None
                    try:
                        coords = opencage_geocode(norm, region=region_for_geocode)
                    except Exception as e:
                        pass
                if coords:
                    lat, lon = coords[:2]
                    threat_type, icon = classify(text)
                    track = {
                        'id': f"{mid}_emoji_threat_{city_from_emoji.replace(' ','_')}",
                        'place': city_from_emoji,
                        'lat': lat, 'lng': lon,
                        'threat_type': threat_type,
                        'text': clean_text(orig)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'emoji_threat'
                    }
                    log.debug(f'Emoji threat parser: {city_from_emoji} -> {coords} -> {icon}')
                    return [track]  # Early return

        # NEW: Handle general emoji + city + oblast format with any UAV threat (more flexible pattern)
        # NOTE: ʼ (U+02BC), ʻ (U+02BB), ` are Ukrainian apostrophe variants
        general_emoji_pattern = r'^[^\w\s]*\s*([А-ЯІЇЄЁа-яіїєё\'ʼʻ`\-\s]+)\s*\([^)]*обл[^)]*\)'
        general_emoji_match = re.search(general_emoji_pattern, head, re.IGNORECASE)
        add_debug_log(f"Testing general emoji pattern on head: {repr(head)}", "emoji_debug")
        add_debug_log(f"General emoji match result: {general_emoji_match}", "emoji_debug")

        if general_emoji_match and any(uav_word in text.lower() for uav_word in ['бпла', 'дрон', 'шахед', 'активність', 'загроза']):
            city_from_general = general_emoji_match.group(1).strip()

            # Strip UAV-related prefixes from city name (БПЛА, дрон, шахед, etc.)
            uav_prefixes = ['бпла', 'дрон', 'дрони', 'шахед', 'шахеди', 'безпілотник', 'безпілотники', 'ворожий', 'ворожі']
            city_lower = city_from_general.lower()
            for prefix in uav_prefixes:
                if city_lower.startswith(prefix + ' '):
                    city_from_general = city_from_general[len(prefix):].strip()
                    city_lower = city_from_general.lower()
                    add_debug_log(f"Stripped UAV prefix '{prefix}', city now: {repr(city_from_general)}", "emoji_debug")

            add_debug_log(f"Found city from general emoji: {repr(city_from_general)}", "emoji_debug")

            if city_from_general and 2 <= len(city_from_general) <= 40:
                base = city_from_general.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                base = re.sub(r'\s+',' ', base)
                norm = UA_CITY_NORMALIZE.get(base, base)
                coords = CITY_COORDS.get(norm)
                add_debug_log(f"Looking up coordinates: base={repr(base)}, norm={repr(norm)}, coords={coords}", "emoji_debug")

                if not coords and 'SETTLEMENTS_INDEX' in globals():
                    idx_map = globals().get('SETTLEMENTS_INDEX') or {}
                    coords = idx_map.get(norm)
                
                # Try OpenCage API if still no coords
                if not coords and GEOCODER_AVAILABLE:
                    oblast_match = re.search(r'\(([А-Яа-яЇїІіЄєҐґ\-]+)\s*обл', head, re.IGNORECASE)
                    region_for_geocode = oblast_match.group(1) if oblast_match else None
                    try:
                        coords = opencage_geocode(norm, region=region_for_geocode)
                    except Exception as e:
                        pass
                
                if coords:
                    lat, lon = coords[:2]
                    threat_type, icon = classify(text)
                    track = {
                        'id': f"{mid}_general_emoji_{city_from_general.replace(' ','_')}",
                        'place': city_from_general.title(),
                        'lat': lat, 'lng': lon,
                        'threat_type': threat_type,
                        'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'general_emoji_threat'
                    }
                    add_debug_log(f'EARLY RETURN: General emoji threat parser: {city_from_general} -> {coords} -> {icon}', "emoji_debug")
                    return [track]  # Early return

        if '(' in head and ('обл' in head.lower() or 'область' in head.lower()):
            import re as _re_early
            cleaned = head.replace('**','')
            for _zw in ('\u200b','\u200c','\u200d','\ufeff','\u2060','\u00a0'):
                cleaned = cleaned.replace(_zw,' ')
            cleaned = ' '.join(cleaned.split())
            cleaned = _re_early.sub(r'^[^A-Za-zА-Яа-яЇїІіЄєҐґ]+','', cleaned)
            # NEW: if pipe '|' separates multiple city headers in one line, attempt multi-city extraction here
            if '|' in cleaned:
                parts = [p.strip() for p in cleaned.split('|') if p.strip()]
                multi_tracks = []
                for idx, part in enumerate(parts, start=1):
                    if '(' not in part:
                        continue
                    par_pos = part.find('(')
                    if par_pos <= 1:
                        continue
                    city_candidate = part[:par_pos].strip()
                    if not (2 <= len(city_candidate) <= 40):
                        continue
                    try:
                        base = city_candidate.lower().replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
                        base = _re_early.sub(r'\s+',' ', base)
                        norm = UA_CITY_NORMALIZE.get(base, base)
                        coords = CITY_COORDS.get(norm)
                        if not coords and 'SETTLEMENTS_INDEX' in globals():
                            idx_map = globals().get('SETTLEMENTS_INDEX') or {}
                            coords = idx_map.get(norm)
                        approx_flag = False
                        if not coords:
                            enriched = ensure_city_coords(norm, context=part)
                            if enriched:
                                if isinstance(enriched, tuple) and len(enriched) == 3:
                                    coords = (enriched[0], enriched[1])
                                    approx_flag = enriched[2]
                                else:
                                    coords = enriched
                        if not coords:
                            continue
                        # classification per segment
                        lseg = part.lower()
                        if any(ph in lseg for ph in ['повідомляють про вибух','повідомлено про вибух','зафіксовано вибух','зафіксовано вибухи','фіксація вибух','фіксують вибух',' вибух.',' вибухи.']):
                            threat, icon = 'vibuh','vibuh.png'
                        elif 'відбій загрози обстр' in lseg or 'відбій загрози застосування' in lseg or 'відбій загрози бпла' in lseg:
                            # treat as list-only cancellation fragment -> skip map marker for this part
                            multi_tracks.append({
                                'id': f"{mid}_p{idx}", 'text': part[:500], 'date': date_str, 'channel': channel,
                                'list_only': True, 'threat_type': 'alarm_cancel', 'place': city_candidate.title()
                            })
                            continue
                        elif 'загроза застосування бпла' in lseg or 'загроза застосування безпілот' in lseg:
                            threat, icon = 'shahed','shahed3.webp'
                        elif 'загроза обстрілу' in lseg or 'загроза обстрела' in lseg:
                            threat, icon = 'artillery','obstril.png'
                        else:
                            threat, icon = classify(part)
                        lat, lng = coords
                        track = {
                            'id': f"{mid}_p{idx}", 'place': city_candidate.title(), 'lat': lat, 'lng': lng,
                            'threat_type': threat, 'text': part[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'multi_city_pipe'
                        }
                        if approx_flag:
                            track['approx'] = True
                        multi_tracks.append(track)
                    except Exception:
                        continue
                # Return only if 2+ actual geo tracks (ignore if we only produced one, fall back to single-city logic)
                geo_count = sum(1 for t in multi_tracks if not t.get('list_only'))
                if geo_count >= 2:
                    return multi_tracks
            par = cleaned.find('(')
            if par > 1:
                city_candidate = cleaned[:par].strip()

                # CRITICAL FIX: Remove BPLA/count prefixes that should NOT be part of city name
                # Examples: "БПЛА Васильків" -> "Васильків", "2х БПЛА Ніжин" -> "Ніжин"
                city_candidate = _re_early.sub(r'^[^а-яіїєґА-ЯІЇЄҐ]*(\d+[xхX×]?\s*)?БПЛА\s+', '', city_candidate, flags=_re_early.IGNORECASE)
                city_candidate = _re_early.sub(r'^[^а-яіїєґА-ЯІЇЄҐ]*(\d+[xхX×]?\s*)?бпла\s+', '', city_candidate, flags=_re_early.IGNORECASE)
                # Also remove "біля" prefix (e.g., "біля Нового Буга" -> "Нового Буга")
                city_candidate = _re_early.sub(r'^біля\s+', '', city_candidate, flags=_re_early.IGNORECASE)
                # Remove "/груп транзитом" and similar routing noise
                city_candidate = _re_early.sub(r'^/\s*груп\s+транзитом\s+', '', city_candidate, flags=_re_early.IGNORECASE)
                city_candidate = city_candidate.strip()

                if 2 <= len(city_candidate) <= 40:
                    base = city_candidate.lower().replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
                    base = _re_early.sub(r'\s+',' ', base)
                    norm = UA_CITY_NORMALIZE.get(base, base)

                    # CRITICAL: Extract oblast from parentheses for oblast-aware lookup
                    # Format: "City (Oblast обл.)" - extract oblast to disambiguate same-name cities
                    coords = None
                    oblast_key_early = None
                    par_end = cleaned.find(')', par)
                    if par_end > par:
                        oblast_raw_early = cleaned[par+1:par_end].strip()
                        # Extract oblast key: "Миколаївська обл." -> "миколаївська"
                        oblast_lower_early = oblast_raw_early.lower()
                        if ' обл' in oblast_lower_early:
                            oblast_key_early = oblast_lower_early.split(' обл')[0].strip()
                        elif 'область' in oblast_lower_early:
                            oblast_key_early = oblast_lower_early.replace('область', '').strip()

                        # PRIORITY 0: Oblast-aware lookup in UKRAINE_SETTLEMENTS_BY_OBLAST
                        if oblast_key_early and 'UKRAINE_SETTLEMENTS_BY_OBLAST' in globals():
                            settlements_by_oblast = globals().get('UKRAINE_SETTLEMENTS_BY_OBLAST') or {}
                            lookup_key_early = (norm, oblast_key_early)
                            if lookup_key_early in settlements_by_oblast:
                                coords = settlements_by_oblast[lookup_key_early]
                                _log(f"[single_city_simple_early] OBLAST-AWARE HIT: {lookup_key_early} -> {coords}")

                    # Fallback to simple lookup if oblast-aware failed
                    if not coords:
                        coords = CITY_COORDS.get(norm)
                    if not coords and 'SETTLEMENTS_INDEX' in globals():
                        idx = globals().get('SETTLEMENTS_INDEX') or {}
                        coords = idx.get(norm)
                    approx_flag = False
                    if not coords:
                        enriched = ensure_city_coords_with_message_context(norm, orig)
                        if enriched:
                            if isinstance(enriched, tuple) and len(enriched) == 3:
                                coords = (enriched[0], enriched[1])
                                approx_flag = enriched[2]
                            else:
                                coords = enriched
                    if coords:
                        l = orig.lower()
                        if any(ph in l for ph in ['повідомляють про вибух','повідомлено про вибух','зафіксовано вибух','зафіксовано вибухи','фіксація вибух','фіксують вибух',' вибух.',' вибухи.']):
                            threat, icon = 'vibuh','vibuh.png'
                        elif 'відбій загрози обстр' in l or 'відбій загрози застосування' in l or 'відбій загрози бпла' in l:
                            # Treat city-level cancellation as list event, not a geo marker
                            return [{
                                'id': str(mid), 'text': orig[:500], 'date': date_str, 'channel': channel,
                                'list_only': True, 'threat_type': 'alarm_cancel', 'place': city_candidate.title()
                            }]
                        elif 'загроза застосування бпла' in l or 'загроза застосування безпілот' in l:
                            threat, icon = 'shahed','shahed3.webp'
                        elif 'загроза обстрілу' in l or 'загроза обстрела' in l:
                            threat, icon = 'artillery','obstril.png'
                        else:
                            threat, icon = classify(orig)
                        lat,lng = coords
                        track = {
                            'id': str(mid), 'place': city_candidate.title(), 'lat': lat, 'lng': lng,
                            'threat_type': threat, 'text': orig[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'single_city_simple_early'
                        }
                        if approx_flag:
                            track['approx'] = True
                        return [track]
    except Exception:
        pass


    # Directional multi-region (e.g. "група БпЛА на Донеччині курсом на Дніпропетровщину") -> list-only, no fixed marker
    try:
        lorig = text.lower()
        # Skip if this message has route patterns (handled by route parser above)
        if 'через' in lorig or 'повз' in lorig:
            pass
        elif (('курс' in lorig or '➡' in lorig or '→' in lorig or 'напрям' in lorig) and ('бпла' in lorig or 'дрон' in lorig or 'груп' in lorig)) or ('бпла' in lorig and 'частин' in lorig) or ('дрон' in lorig and 'частин' in lorig):
            # Special case: BPLA current location with directional info
            # e.g., "БпЛА в північно-західній частині Полтавщини, курсом на Київщину"
            # or "БпЛА в південно-східній частині Харківщини"
            import re as _re_loc

            # Look for current location patterns
            location_match = _re_loc.search(r'(?:бпла|дрон[иа]?)\s+(?:в|на|над)\s+([а-яіїєґ\-\s]+(?:частин[іа]|район[іе]|округ[уі])\s+[а-яіїєґ]+щин[иаю])', lorig)
            if location_match:
                current_location = location_match.group(1).strip()
                print(f"DEBUG: Found current BPLA location: {current_location}")

                # Extract region from current location
                region_in_location = None
                for reg_key in OBLAST_CENTERS.keys():
                    if reg_key in current_location:
                        region_in_location = reg_key
                        break

                if region_in_location:
                    # Get region center and apply directional offset
                    region_coords = OBLAST_CENTERS.get(region_in_location, (50.0, 30.0))

                    # Apply directional offset based on specified part of region
                    offset_lat, offset_lon = 0, 0
                    if 'північно-західн' in current_location:
                        offset_lat, offset_lon = 0.8, -0.8  # Northwest
                    elif 'північно-східн' in current_location:
                        offset_lat, offset_lon = 0.8, 0.8   # Northeast
                    elif 'південно-західн' in current_location:
                        offset_lat, offset_lon = -0.8, -0.8 # Southwest
                    elif 'південно-східн' in current_location:
                        offset_lat, offset_lon = -0.8, 0.8  # Southeast
                    elif 'північн' in current_location:
                        offset_lat, offset_lon = 0.8, 0     # North
                    elif 'південн' in current_location:
                        offset_lat, offset_lon = -0.8, 0    # South
                    elif 'західн' in current_location:
                        offset_lat, offset_lon = 0, -0.8    # West
                    elif 'східн' in current_location:
                        offset_lat, offset_lon = 0, 0.8     # East
                    elif 'центральн' in current_location:
                        offset_lat, offset_lon = 0, 0       # Center

                    final_lat = region_coords[0] + offset_lat
                    final_lon = region_coords[1] + offset_lon

                    # Clean up city name for display
                    region_name = region_in_location.replace('щини', 'щина').replace('щину', 'щина')
                    direction_part = ""
                    if 'північно-західн' in current_location:
                        direction_part = "Пн-Зх "
                    elif 'північно-східн' in current_location:
                        direction_part = "Пн-Сх "
                    elif 'південно-західн' in current_location:
                        direction_part = "Пд-Зх "
                    elif 'південно-східн' in current_location:
                        direction_part = "Пд-Сх "
                    elif 'північн' in current_location:
                        direction_part = "Пн "
                    elif 'південн' in current_location:
                        direction_part = "Пд "
                    elif 'західн' in current_location:
                        direction_part = "Зх "
                    elif 'східн' in current_location:
                        direction_part = "Сх "
                    elif 'центральн' in current_location:
                        direction_part = "Центр "

                    display_name = f"{direction_part}{region_name.title()}"

                    print(f"DEBUG: Location '{current_location}' in {region_in_location} -> ({final_lat}, {final_lon})")

                    return [{
                        'id': str(mid), 'text': clean_text(text)[:600], 'date': date_str, 'channel': channel,
                        'lat': final_lat, 'lon': final_lon, 'city': display_name,
                        'source_match': 'trajectory_current_location'
                    }]

            # Quick reject if explicit single settlement in parentheses (handled elsewhere)
            if '(' not in lorig:
                present_regions = []
                for reg_key in OBLAST_CENTERS.keys():
                    if reg_key in lorig:
                        present_regions.append(reg_key)
                        if len(present_regions) >= 4:
                            break
                distinct = {r.split()[0] for r in present_regions}
                # Accept patterns like "нова група ударних БпЛА на Донеччині курсом на Дніпропетровщину"
                # even if only 2 region stems present
                if len(distinct) >= 2:
                    # Check if message contains specific cities that should create markers instead
                    city_keywords = ['на кролевец', 'на конотоп', 'на чернігів', 'на вишгород', 'на петрівці', 'на велика димерка', 'на білу церкву', 'на бровари', 'на суми', 'на харків', 'на дніпро', 'на кропивницький', 'на житомир', 'на миколаївку', 'на липовець', 'на ріпки', 'на терни', 'на павлоград']
                    has_specific_cities = any(city_kw in lorig for city_kw in city_keywords)

                    # Also check for pattern "БпЛА на [city]" which should create markers
                    import re as _re_cities
                    bpla_na_pattern = _re_cities.findall(r'бпла\s+на\s+([a-zа-яіїєґʼ`\-\s]{3,20})', lorig)
                    if bpla_na_pattern:
                        has_specific_cities = True

                    if has_specific_cities:
                        # Let multi-city parser handle this instead
                        pass
                    else:
                        # Extra guard: if a well-known large city (e.g. дніпро, харків, київ) appears ONLY because it's substring of region
                        # we still treat as region directional, not city marker
                        # But if message contains multiple explicit directional part-of-region clauses ("на сході <області>" ... "на сході <області>")
                        # then we want to produce separate segment markers instead of a single list-only event.
                        import re as _re_dd
                        dir_clause_count = len(_re_dd.findall(r'на\s+(?:північ|півден|схід|заход|північно|південно)[^\.]{0,40}?(?:щина|щини|щину)', lorig))
                        if dir_clause_count < 2:
                            return [{
                                'id': str(mid), 'text': clean_text(text)[:600], 'date': date_str, 'channel': channel,
                                'list_only': True, 'source_match': 'region_direction_multi'
                            }]
    except Exception:
        pass
    # Comparative directional relative to a city ("північніше Городні", "східніше Кролевця") -> use base city location
    try:
        import re as _re_rel
        low_txt = text.lower()
        # NEW: pattern "<city> - до вас БпЛА" -> marker at city
        m_dash = _re_rel.search(r"([a-zа-яіїєґ'ʼ’`\-]{3,40})\s*[-–—]\s*до вас\s+бпла", low_txt)
        if m_dash:
            raw_city = m_dash.group(1)
            raw_city = raw_city.replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
            base = UA_CITY_NORMALIZE.get(raw_city, raw_city)
            coords = CITY_COORDS.get(base)
            if not coords and 'SETTLEMENTS_INDEX' in globals():
                coords = (globals().get('SETTLEMENTS_INDEX') or {}).get(base)
            if coords:
                lat,lng = coords
                threat, icon = 'shahed','shahed3.webp'
                return [{
                    'id': str(mid), 'place': base.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat, 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'city_dash_uav'
                }]
        # NEW: pattern "БпЛА на <city>" or "бпла на <city>" -> marker at city
        uav_city_pattern = _re_rel.compile(r"бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ\`\s/]+?)(?=\s+(?:з|на|до|від|через|повз|курсом|напрям)\s|[,\.\!\?;:\n]|$)")
        uav_cities = list(uav_city_pattern.finditer(low_txt))
        if uav_cities:
            threats = []
            for idx, match in enumerate(uav_cities):
                rc = match.group(1)
                # If the message continues with course wording immediately after this fragment,
                # treat it as a transit description (let region-course logic handle it)
                tail = low_txt[match.end():match.end()+80]
                if 'курс' in tail:
                    continue
                rc = rc.replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")

                # Handle cities separated by slash (e.g., "вишгород/петрівці")
                cities_to_process = []
                if '/' in rc:
                    cities_to_process.extend(rc.split('/'))
                else:
                    cities_to_process.append(rc)

                for city_idx, city in enumerate(cities_to_process):
                    city = city.strip()
                    if not city:
                        continue

                    base = UA_CITY_NORMALIZE.get(city, city)

                    # Special handling for Kyiv - show directional approach instead of center point
                    if base.lower() == 'київ':
                        kyiv_lat, kyiv_lng, kyiv_label, direction_info = get_kyiv_directional_coordinates(text, base)
                        threat_type, icon = classify(text)

                        # Use specialized icon for directional Kyiv threats
                        if direction_info:
                            icon = 'shahed3.webp'  # Could create special directional icon later

                        threats.append({
                            'id': f"{mid}_uav_{idx}_{city_idx}_kyiv_dir", 'place': kyiv_label, 'lat': kyiv_lat, 'lng': kyiv_lng,
                            'threat_type': threat_type, 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'uav_on_city_kyiv_directional',
                            'direction_info': direction_info
                        })
                        continue

                    coords = CITY_COORDS.get(base)
                    if not coords and 'SETTLEMENTS_INDEX' in globals():
                        coords = (globals().get('SETTLEMENTS_INDEX') or {}).get(base)
                    if coords:
                        lat,lng = coords
                        threats.append({
                            'id': f"{mid}_uav_{idx}_{city_idx}", 'place': base.title(), 'lat': lat, 'lng': lng,
                            'threat_type': 'shahed', 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'shahed3.webp', 'source_match': 'uav_on_city'
                        })
            if threats:
                return threats
        # pattern captures direction word + city morph form
        m_rel = _re_rel.search(r'(північніше|південніше|східніше|західніше)\s+([a-zа-яіїєґ\'ʼ’`\-]{3,40})', low_txt)
        if m_rel:
            raw_city = m_rel.group(2)
            # normalize apostrophes
            raw_city = raw_city.replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
            base = UA_CITY_NORMALIZE.get(raw_city, raw_city)
            coords = CITY_COORDS.get(base)
            if not coords and 'SETTLEMENTS_INDEX' in globals():
                idx = globals().get('SETTLEMENTS_INDEX') or {}
                coords = idx.get(base)
            if not coords:
                enriched = ensure_city_coords(base, context=text)
                if enriched:
                    if isinstance(enriched, tuple) and len(enriched)==3:
                        coords = (enriched[0], enriched[1])
                    else:
                        coords = enriched
            if coords:
                lat,lng = coords
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': base.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'relative_direction_city'
                }]
    except Exception:
        pass
    # Multi-segment UAV messages with pipe separator (e.g., "БпЛА курсом на Кагарлик | 2х БпЛА Білоцерківський район | 3х БпЛА Вишеньки / Українка")
    try:
        if '|' in text and 'бпла' in text.lower():
            segments = [seg.strip() for seg in text.split('|') if seg.strip()]
            if len(segments) >= 2:  # At least 2 segments
                threats = []
                import re as _re_multi

                for seg_idx, segment in enumerate(segments):
                    seg_lower = segment.lower()
                    if 'бпла' not in seg_lower:
                        continue

                    # Pattern 1: "БпЛА курсом на [city]" (with optional н.п. prefix)
                    course_match = _re_multi.search(r'бпла\s+курсом?\s+на\s+(?:н\.п\.?\s*)?([а-яіїєґ\'\-\s]+?)(?:\s*$|\s*\|)', seg_lower)
                    if course_match:
                        city_name = course_match.group(1).strip()
                        city_norm = clean_text(city_name).lower()

                        # Accusative case normalization (винительный падеж)
                        if city_norm == 'велику димерку':
                            city_norm = 'велика димерка'
                        elif city_norm == 'мену':
                            city_norm = 'мена'
                        elif city_norm == 'пісківку':
                            city_norm = 'пісківка'
                        elif city_norm == 'києвом':
                            city_norm = 'київ'
                        # General accusative case endings
                        elif city_norm.endswith('у') and len(city_norm) > 3:
                            city_norm = city_norm[:-1] + 'а'
                        elif city_norm.endswith('ю') and len(city_norm) > 3:
                            city_norm = city_norm[:-1] + 'я'
                        elif city_norm.endswith('ку') and len(city_norm) > 4:
                            city_norm = city_norm[:-2] + 'ка'

                        if city_norm in UA_CITY_NORMALIZE:
                            city_norm = UA_CITY_NORMALIZE[city_norm]

                        coords = ensure_city_coords_with_message_context(city_norm, text)

                        if coords and isinstance(coords, tuple) and len(coords) >= 2:
                            lat, lng = coords[0], coords[1]
                            threat_type, icon = classify(text)
                            # Use normalized city name for display, not the original accusative form
                            display_name = city_norm.title()
                            threats.append({
                                'id': f"{mid}_multi_{seg_idx}",
                                'place': display_name,
                                'lat': lat,
                                'lng': lng,
                                'threat_type': threat_type,
                                'text': f"Курсом на {display_name}",
                                'date': date_str,
                                'channel': channel,
                                'marker_icon': icon,
                                'source_match': 'multi_segment_course',
                                'count': 1
                            })

                    # Pattern 1.5: "БпЛА повз [city1] курсом на [city2]" - extract both cities
                    povz_match = _re_multi.search(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+повз\s+([а-яіїєґ\'\-\s]+?)\s+курсом?\s+на\s+([а-яіїєґ\'\-\s]+?)(?:\s*$|\s*\|)', seg_lower)
                    if povz_match and not course_match:  # Don't double-process if already handled by Pattern 1
                        count_str, city1_name, city2_name = povz_match.groups()
                        count = int(count_str) if count_str and count_str.isdigit() else 1

                        for city_idx, city_raw in enumerate([city1_name, city2_name]):
                            if not city_raw:
                                continue

                            city_name = city_raw.strip()
                            city_norm = clean_text(city_name).lower()

                            # Accusative case normalization for both cities
                            if city_norm == 'велику димерку':
                                city_norm = 'велика димерка'
                            elif city_norm == 'мену':
                                city_norm = 'мена'
                            elif city_norm == 'пісківку':
                                city_norm = 'пісківка'
                            elif city_norm == 'києвом':
                                city_norm = 'київ'
                            # General accusative case endings
                            elif city_norm.endswith('у') and len(city_norm) > 3:
                                city_norm = city_norm[:-1] + 'а'
                            elif city_norm.endswith('ю') and len(city_norm) > 3:
                                city_norm = city_norm[:-1] + 'я'
                            elif city_norm.endswith('ку') and len(city_norm) > 4:
                                city_norm = city_norm[:-2] + 'ка'

                            if city_norm in UA_CITY_NORMALIZE:
                                city_norm = UA_CITY_NORMALIZE[city_norm]

                            coords = ensure_city_coords(city_norm, context=text)

                            if coords and isinstance(coords, tuple) and len(coords) >= 2:
                                lat, lng = coords[0], coords[1]
                                threat_type, icon = classify(text)
                                action = "Повз" if city_idx == 0 else "Курсом на"
                                # Use normalized city name for display
                                display_name = city_norm.title()
                                threats.append({
                                    'id': f"{mid}_multi_{seg_idx}_povz_{city_idx}",
                                    'place': display_name,
                                    'lat': lat,
                                    'lng': lng,
                                    'threat_type': threat_type,
                                    'text': f"{action} {display_name} ({count}x)",
                                    'date': date_str,
                                    'channel': channel,
                                    'marker_icon': icon,
                                    'source_match': 'multi_segment_povz',
                                    'count': count
                                })

                    # Pattern 2: "[N]х БпЛА [location]" - extract cities
                    location_match = _re_multi.search(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(.+?)(?:\.|$)', seg_lower)
                    if location_match and not course_match:  # Don't double-process course segments
                        count_str = location_match.group(1) or "1"
                        location_text = location_match.group(2).strip()
                        count = int(count_str) if count_str.isdigit() else 1

                        # Split by common separators to get individual cities
                        cities = []
                        for sep in [' / ', ' та ', ' і ', ', ']:
                            if sep in location_text:
                                cities = [c.strip() for c in location_text.split(sep) if c.strip()]
                                break
                        if not cities:
                            cities = [location_text]

                        for city_idx, city in enumerate(cities):
                            city = city.strip()
                            if not city:
                                continue

                            # Handle district references (e.g., "Білоцерківський район")
                            if 'район' in city:
                                # Extract district name and try to find main city
                                district_name = city.replace('район', '').replace('ський', '').replace('цький', '').strip()

                                # Special case mappings
                                if 'білоцерків' in district_name:
                                    district_name = 'біла церква'

                                if district_name:
                                    city = district_name
                                else:
                                    continue

                            city_norm = clean_text(city).lower()
                            if city_norm in UA_CITY_NORMALIZE:
                                city_norm = UA_CITY_NORMALIZE[city_norm]

                            coords = ensure_city_coords(city_norm, context=text)

                            if coords and isinstance(coords, tuple) and len(coords) >= 2:
                                lat, lng = coords[0], coords[1]
                                threat_type, icon = classify(text)
                                threats.append({
                                    'id': f"{mid}_multi_{seg_idx}_{city_idx}",
                                    'place': city.title(),
                                    'lat': lat,
                                    'lng': lng,
                                    'threat_type': threat_type,
                                    'text': f"{count}х БпЛА на {city.title()}",
                                    'date': date_str,
                                    'channel': channel,
                                    'marker_icon': icon,
                                    'source_match': f'multi_segment_location_{count}x',
                                    'count': count
                                })

                if threats:
                    # ALSO: Extract cities from emoji structure in the same text
                    # Pattern for "| 🛸 Город (Область)"
                    emoji_pattern = r'\|\s*🛸\s*([А-ЯІЇЄЁа-яіїєё\'ʼʻ`\-\s]+?)\s*\([^)]*обл[^)]*\)'
                    emoji_matches = re.finditer(emoji_pattern, text, re.IGNORECASE)

                    for match in emoji_matches:
                        city_raw = match.group(1).strip()
                        if not city_raw or len(city_raw) < 2:
                            continue

                        city_norm = clean_text(city_raw).lower()
                        if city_norm in UA_CITY_NORMALIZE:
                            city_norm = UA_CITY_NORMALIZE[city_norm]

                        coords = ensure_city_coords(city_norm, context=text)

                        if coords:
                            lat, lng = coords[:2]
                            threat_type, icon = classify(text)

                            threat_id = f"{mid}_emoji_struct_{len(threats)}"
                            threats.append({
                                'id': threat_id,
                                'place': city_raw.title(),
                                'lat': lat,
                                'lng': lng,
                                'threat_type': threat_type,
                                'text': f"Загроза в {city_raw}",
                                'date': date_str,
                                'channel': channel,
                                'marker_icon': icon,
                                'source_match': 'emoji_structure_multi',
                                'count': 1
                            })

                            add_debug_log(f"Multi emoji structure: {city_raw} -> {coords}", "emoji_struct_multi")
                        else:
                            add_debug_log(f"Multi emoji structure: No coords for {city_raw}", "emoji_struct_multi")

                    # Check for priority result to combine
                    if '_current_priority_result' in globals() and globals()['_current_priority_result']:
                        combined_result = globals()['_current_priority_result'] + threats
                        add_debug_log(f"MULTI-SEGMENT: Combined priority result ({len(globals()['_current_priority_result'])}) with threats ({len(threats)}) = {len(combined_result)} total", "priority_combine")
                        # Clear the global priority result after use
                        globals()['_current_priority_result'] = None
                        return combined_result
                    return threats

    except Exception:
        pass

    # Course towards single city ("курс(ом) на Батурин") -> place marker at that city
    try:
        import re as _re_course
        low_txt2 = text.lower()
        m_course = _re_course.search(r"курс(?:ом)?\s+на\s+([a-zа-яіїєґ\'ʼ'`\-\s]{3,60})(?=\s*(?:$|[,\.\!\?;]|\n))", low_txt2)
        if m_course:
            raw_city = m_course.group(1).strip()
            raw_city = raw_city.replace('\u02bc',"'").replace('ʼ',"'").replace('’',"'").replace('`',"'")
            base = UA_CITY_NORMALIZE.get(raw_city, raw_city)

            # Use OpenCage geocoder
            coords = ensure_city_coords(base, context=text)

            if not coords:
                # Legacy fallback for backwards compatibility
                enriched = ensure_city_coords(base, context=text)
                if enriched:
                    if isinstance(enriched, tuple) and len(enriched)==3:
                        coords = (enriched[0], enriched[1])
                    else:
                        coords = enriched
                    if isinstance(enriched, tuple) and len(enriched)==3:
                        coords = (enriched[0], enriched[1])
                    else:
                        coords = enriched
            if coords:
                lat,lng = coords
                threat_type, icon = classify(text)

                # Extract course information for Shahed threats
                course_info = None
                if threat_type == 'shahed':
                    course_info = extract_shahed_course_info(text)

                # Extract count from text (look for pattern like "10х БпЛА")
                uav_count = 1
                import re as _re_count
                count_match = _re_count.search(r'(\d+)\s*[xх×]\s*бпла', low_txt2)
                if count_match:
                    uav_count = int(count_match.group(1))

                # Create multiple tracks for multiple drones
                tracks_to_create = max(1, uav_count)
                threat_tracks = []

                for i in range(tracks_to_create):
                    track_name = base.title()
                    if tracks_to_create > 1:
                        track_name += f" #{i+1}"

                    # Add small coordinate offsets to prevent marker overlap
                    marker_lat = lat
                    marker_lng = lng
                    if tracks_to_create > 1:
                        # Create a chain pattern - drones one after another
                        offset_distance = 0.03  # ~3km offset between each drone
                        marker_lat += offset_distance * i
                        marker_lng += offset_distance * i * 0.5

                    threat_data = {
                        'id': f"{mid}_{i+1}", 'place': track_name, 'lat': marker_lat, 'lng': marker_lng,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'course_to_city', 'count': 1
                    }

                    # Add course information if available
                    if course_info:
                        threat_data.update({
                            'course_source': course_info.get('source_city'),
                            'course_target': course_info.get('target_city'),
                            'course_direction': course_info.get('course_direction'),
                            'course_type': course_info.get('course_type')
                        })

                    threat_tracks.append(threat_data)

                return threat_tracks
    except Exception:
        pass

    # --- PRIORITY: Early explicit pattern for districts - MOVED UP TO AVOID CONFLICTS ---
    # Check before region direction processing to prevent fallback to oblast centers
    try:
        import re as _re_raion
        # Pattern 1: "<RaionName> район (<Oblast ...>)"
        m_raion_oblast = _re_raion.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\'\-]{4,})\s+район\s*\(([^)]*обл[^)]*)\)', text)
        if m_raion_oblast:
            raion_token = m_raion_oblast.group(1).strip().lower()
            # Normalize morphological endings
            raion_base = _re_raion.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_token)
            if raion_base in RAION_FALLBACK:
                lat, lng = RAION_FALLBACK[raion_base]
                threat_type, icon = classify(text)
                add_debug_log(f"PRIORITY: Early district processing - {raion_base} район -> {lat}, {lng}", "district_early")
                return [{
                    'id': str(mid), 'place': f"{raion_base.title()} район", 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500],
                    'date': date_str, 'channel': channel, 'marker_icon': icon, 'source_match': 'raion_oblast_combo_early'
                }]
            else:
                add_debug_log(f"Early district processing - {raion_base} not found in RAION_FALLBACK", "district_early")

        # Pattern 2: "<RaionName> район <OblastName>" (без дужок)
        m_raion_oblast2 = _re_raion.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\'\-]{4,})\s+район\s+([\w\']+(?:щини|щину|области|області))', text)
        if m_raion_oblast2:
            raion_token = m_raion_oblast2.group(1).strip().lower()
            # Normalize morphological endings
            raion_base = _re_raion.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_token)
            if raion_base in RAION_FALLBACK:
                lat, lng = RAION_FALLBACK[raion_base]
                threat_type, icon = classify(text)
                add_debug_log(f"PRIORITY: Early district processing (format 2) - {raion_base} район -> {lat}, {lng}", "district_early")
                return [{
                    'id': str(mid), 'place': f"{raion_base.title()} район", 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500],
                    'date': date_str, 'channel': channel, 'marker_icon': icon, 'source_match': 'raion_oblast_combo_early_v2'
                }]
            else:
                add_debug_log(f"Early district processing (format 2) - {raion_base} not found in RAION_FALLBACK", "district_early")
    except Exception as e:
        add_debug_log(f"Early district processing error: {e}", "district_early")

    # Region directional segments specifying part of oblast ("на сході Дніпропетровщини") possibly multiple in one line
    try:
        import re as _re_seg
        lower_full = text.lower()
        pattern = _re_seg.compile(r'на\s+([\w\-\s/]+?)\s+(?:частині\s+)?([a-zа-яіїєґ]+щина|[a-zа-яіїєґ]+щини|[a-zа-яіїєґ]+щину)')
        seg_matches = list(pattern.finditer(lower_full))
        seg_tracks = []
        used_spans = []
        if seg_matches:
            # Map Ukrainian directional forms to codes
            dir_map_words = {
                'північ':'n','південь':'s','схід':'e','захід':'w','сході':'e','заході':'w','півночі':'n','півдні':'s',
                'північно-схід':'ne','північно-сход':'ne','північно схід':'ne','південно-схід':'se','південно схід':'se',
                'північно-захід':'nw','північно захід':'nw','південно-захід':'sw','південно захід':'sw'
            }
            def direction_codes(raw:str):
                parts = [p.strip() for p in raw.replace('–','-').split('/') if p.strip()]
                out = []
                for p in parts:
                    # compress multiple spaces
                    p2 = ' '.join(p.split())
                    # find best match in dir_map_words by prefix
                    code=None
                    for k,v in dir_map_words.items():
                        if k in p2:
                            code=v; break
                    if not code:
                        # try simple endings
                        if p2.startswith('схід'): code='e'
                        elif p2.startswith('захід'): code='w'
                    if code and code not in out:
                        out.append(code)
                return out or ['center']
            for m in seg_matches:
                dir_raw = m.group(1).strip()
                region_raw = m.group(2).strip()
                # Normalize region key to match OBLAST_CENTERS keys
                region_key = None
                for k in OBLAST_CENTERS.keys():
                    if region_raw in k:
                        region_key = k
                        break
                if not region_key:
                    continue
                base_lat, base_lng = OBLAST_CENTERS[region_key]
                codes = direction_codes(dir_raw)
                for idx, code in enumerate(codes,1):
                    # offset placement (reuse logic similar to later region_direction block)
                    def offset(lat,lng,code):
                        lat_step = 0.55
                        lng_step = 0.85 / max(0.2, abs(math.cos(math.radians(lat))))
                        if code=='n': return lat+lat_step, lng
                        if code=='s': return lat-lat_step, lng
                        if code=='e': return lat, lng+lng_step
                        if code=='w': return lat, lng-lng_step
                        lat_diag=lat_step*0.8; lng_diag=lng_step*0.8
                        if code=='ne': return lat+lat_diag, lng+lng_diag
                        if code=='nw': return lat+lat_diag, lng-lng_diag
                        if code=='se': return lat-lat_diag, lng+lng_diag
                        if code=='sw': return lat-lat_diag, lng-lng_diag
                        return lat, lng
                    lat_o, lng_o = offset(base_lat, base_lng, code)
                    label_region = region_key.split()[0].title()
                    dir_label_map = {
                        'n':'північна частина','s':'південна частина','e':'східна частина','w':'західна частина',
                        'ne':'північно-східна частина','nw':'північно-західна частина','se':'південно-східна частина','sw':'південно-західна частина','center':'частина'
                    }
                    label = f"{label_region} ({dir_label_map.get(code,'частина')})"
                    threat_type, icon = classify(text)

                    # Skip if this segment contains "курсом на [city]" after the region match
                    # to give priority to specific city course tracking
                    segment_after = text[m.end():]
                    if _re_seg.search(r'курсом?\s+на\s+(?:н\.п\.?\s*)?[А-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,}', segment_after, _re_seg.IGNORECASE):
                        continue

                    seg_tracks.append({
                        'id': f"{mid}_rd{len(seg_tracks)+1}", 'place': label, 'lat': lat_o, 'lng': lng_o,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_direction_segment'
                    })
            if seg_tracks:
                return seg_tracks
    except Exception as e:
        try: log.debug(f'region_dir_segments error: {e}')
        except: pass
    # --- Pre-split case: several bold oblast headers inside a single line (e.g. **Полтавщина:** ... **Дніпропетровщина:** ... ) ---
    try:
        # Detect two or more bold oblast headers
        hdr_pat = re.compile(r'(\*\*[A-Za-zА-Яа-яЇїІіЄєҐґ]+щина\*\*:)')
        if text.count('**') >= 4:  # quick filter
            matches = list(hdr_pat.finditer(text))
            if len(matches) >= 2:
                # Insert newline before each header (except first) if not already line-start
                # Build new text chunk-wise
                new_parts = []
                last = 0
                for i, m in enumerate(matches):
                    start = m.start()
                    if i == 0 and start > 0 and text[start-1] != '\n':
                        # ensure header is at line start
                        new_parts.append(text[last:start])
                    elif i > 0:
                        # append text before header ensuring newline separation
                        segment = text[last:start]
                        if not segment.endswith('\n'):
                            segment += '\n'
                        new_parts.append(segment)
                    last = start
                # append remaining
                new_parts.append(text[last:])
                new_text_joined = ''.join(new_parts)
                if new_text_joined != text:
                    text = new_text_joined
    except Exception:
        pass
    # --- Спец. обработка многострочных сообщений с заголовками-областями и списком городов ---
    import unicodedata
    def normalize_city_name(name):
        # Привести к нижнему регистру, заменить все апострофы на стандартный, убрать лишние пробелы
        n = name.lower().strip()
        n = n.replace('ʼ', "'").replace('’', "'").replace('`', "'")
        n = unicodedata.normalize('NFC', n)

        # Convert mixed Latin/Cyrillic to full Cyrillic (e.g. "Kov'яги" -> "ков'яги")
        # Common Latin-Cyrillic lookalikes in Ukrainian city names
        latin_to_cyrillic = {
            'a': 'а', 'e': 'е', 'i': 'і', 'o': 'о', 'p': 'р', 'c': 'с',
            'y': 'у', 'x': 'х', 'k': 'к', 'h': 'н', 't': 'т', 'm': 'м',
            'b': 'в', 'v': 'в', 'n': 'н', 's': 'с', 'r': 'р'
        }

        # Only convert if string contains mixed Latin + Cyrillic (heuristic: has both ranges)
        has_cyrillic = any(ord(c) >= 0x0400 and ord(c) <= 0x04FF for c in n)
        has_latin = any('a' <= c <= 'z' for c in n)

        if has_cyrillic and has_latin:
            # Convert Latin lookalikes to Cyrillic
            n_converted = ''
            for c in n:
                if 'a' <= c <= 'z':
                    n_converted += latin_to_cyrillic.get(c, c)
                else:
                    n_converted += c
            n = n_converted

        return n

    def sanitize_course_destination(name: str) -> str:
        if not name:
            return ''
        cleaned = name.strip()
        cleaned = re.sub(r'[\\/|]+', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'(район|району|районі|районів|района|р-н|область|області|обл\.|громада|громаді|громади|community|district|sector|сектор|місто|місті)$', '', cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'\b(район|району|районі|района|р-н|область|області|обл\.|громада|громади|community|district|sector|сектор|місто|місті)\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(" .,'-\"")
        low = cleaned.lower()
        tokens = {t for t in re.split(r'\s+', low) if t}
        garbage_tokens = {
            'передмісті', 'передмістя', 'передмістях',
            'містом', 'місті', 'місто', 'містами',
            'чисто', 'чистий', 'чиста', 'чисті'
        }
        if not tokens or tokens.issubset(garbage_tokens):
            return ''
        if 'передміст' in low and 'чист' in low:
            return ''
        return cleaned

    def extract_course_targets(raw: str):
        if not raw:
            return []
        parts = re.split(r'\s*(?:[\\/|,;]|\s+та\s+|\s+і\s+|\s+и\s+|\s+або\s+|\s+or\s+)\s*', raw, flags=re.IGNORECASE)
        targets = []
        for part in parts:
            candidate = sanitize_course_destination(part)
            if candidate:
                targets.append(candidate)
        if targets:
            return targets
        cleaned = sanitize_course_destination(raw)
        return [cleaned] if cleaned else []
    # Если сообщение содержит несколько строк с заголовками-областями и городами
    # Предварительно уберём чисто донатные/подписи строки из многострочного блока, чтобы они не мешали
    raw_lines = text.splitlines()

    # NEW: Handle single-line messages with multiple regions like "Чернігівщина: 1 БпЛА на Козелець ... Сумщина: 3 БпЛА..."
    # First try to split by region headers in single line
    single_line_regions = ['чернігівщин', 'сумщин', 'харківщин', 'полтавщин', 'херсонщин', 'донецьк', 'луганщин']
    if len(raw_lines) == 1 and any(region in text.lower() for region in single_line_regions):
        add_debug_log(f"Single-line multi-region message detected, raw_lines count: {len(raw_lines)}", "multi_region")
        # Split by oblast headers that have colon after them
        import re as _re_split
        region_split = _re_split.split(r'([А-ЯІЇЄЁа-яіїєё]+щина):\s*', text)
        add_debug_log(f"Region split result: {region_split}", "multi_region")
        if len(region_split) > 2:  # We have actual splits
            new_lines = []
            for i in range(1, len(region_split), 2):  # Take every odd element (region name) and next even (content)
                if i+1 < len(region_split):
                    region_name = region_split[i]
                    content = region_split[i+1].strip()
                    new_lines.append(f"{region_name}:")
                    new_lines.append(content)
                    add_debug_log(f"Added region header: '{region_name}:' and content: '{content}'", "multi_region")
            if new_lines:
                raw_lines = new_lines
                add_debug_log(f"Split single line into {len(raw_lines)} lines for multi-region processing", "multi_region")
        else:
            add_debug_log("Region split failed, keeping original format", "multi_region")

    cleaned_for_multiline = []
    import re as _re_clean
    donation_keys = ['монобанк','send.monobank','patreon','donat','донат','підтримати канал','підтримати']
    for l in raw_lines:
        ls = l.strip()
        if not ls:
            continue
        # If line combines header and content ("Хмельниччина: Група КР ..." possibly with formatting ** **)
        m_comb = _re_clean.match(r'^\**([A-Za-zА-Яа-яЇїІіЄєҐґ]+щина)\**:\s*(.+)$', ls)
        if m_comb:
            header_part = m_comb.group(1) + ':'
            rest_part = m_comb.group(2).strip()
            cleaned_for_multiline.append(header_part)
            ls = rest_part  # continue processing rest_part below (could still contain links)
        low_ls = ls.lower()
        # Strip markdown links / segments that are purely donation or service references, keep threat fragment
        def _strip_bad_links(s: str):
            # Remove any [text](url) where text or url contains donation_keys
            def _repl(m):
                inner_text = m.group(1).lower()
                url = m.group(2).lower()
                if any(k in inner_text or k in url for k in donation_keys):
                    return ''
                return m.group(0)
            s2 = _re_clean.sub(r'\[([^\]]{0,60})\]\(([^) ]+?)\)', _repl, s)
            return s2
        ls_no_links = _strip_bad_links(ls)
        low_no_links = ls_no_links.lower()
        if any(k in low_no_links for k in donation_keys):
            # If after stripping links still only donation noise and no threat keywords, skip.
            if not any(t in low_no_links for t in ['бпла','курс','ракета','ракети','рупа','група','кр']):
                continue
            # Else remove the donation substrings explicitly.
            for k in donation_keys:
                low_no_links = low_no_links.replace(k,' ')
            ls_no_links = ' '.join(low_no_links.split())
        cleaned_for_multiline.append(ls_no_links.strip())
    lines = cleaned_for_multiline

    oblast_hdr = None
    multi_city_tracks = []
    processed_lines_count = 0
    add_debug_log(f"Processing {len(lines)} cleaned lines for multi-city tracks", "multi_region")

    for ln in lines:
        processed_lines_count += 1
        add_debug_log(f"Processing line {processed_lines_count}/{len(lines)}: '{ln[:80]}...'", "multi_region")

        # PRIORITY: Check for specific region-city patterns FIRST
        import re as _re_region_city
        ln_lower = ln.lower()

        # Pattern 1: "на [region] [count] шахедів на [city]"
        region_city_pattern1 = _re_region_city.compile(r'на\s+([а-яіїєґ]+щин[іау]?)\s+(\d+)\s+шахед[іїв]*\s+на\s+([а-яіїєґ\'\-\s]+)', _re_region_city.IGNORECASE)
        region_city_match1 = region_city_pattern1.search(ln_lower)

        # Pattern 2: "[region] - шахеди на [city]"
        region_city_pattern2 = _re_region_city.compile(r'([а-яіїєґ]+щин[ауи]?)\s*-\s*шахед[іїив]*\s+на\s+([а-яіїєґ\'\-\s]+)', _re_region_city.IGNORECASE)
        region_city_match2 = region_city_pattern2.search(ln_lower)

        # Pattern 3: "[region] ([city] р-н)" - for district headquarters
        region_district_pattern = _re_region_city.compile(r'([а-яіїєґ]+щин[ауи]?)\s*\(\s*([а-яіїєґ\'\-\s]+)\s+р[-\s]*н\)', _re_region_city.IGNORECASE)
        region_district_match = region_district_pattern.search(ln_lower)

        add_debug_log(f"CHECKING region-city patterns for line: '{ln_lower}'", "region_city_debug")

        region_city_match = region_city_match1 or region_city_match2

        if region_district_match:
            # Handle "чернігівщина (новгород-сіверський р-н)" format
            region_raw, district_raw = region_district_match.groups()
            target_city = district_raw.strip()

            add_debug_log(f"REGION-DISTRICT pattern FOUND: region='{region_raw}', district='{district_raw}'", "region_district")

            # Normalize city name and try to find coordinates
            city_norm = target_city.lower()
            # Apply UA_CITY_NORMALIZE rules if available
            if 'UA_CITY_NORMALIZE' in globals():
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
            coords = CITY_COORDS.get(city_norm)

            add_debug_log(f"District city lookup: '{target_city}' -> '{city_norm}' -> {coords}", "region_district")

            if coords:
                lat, lng = coords
                threat_type, icon = classify(ln)

                multi_city_tracks.append({
                    'id': f"{mid}_region_district_{len(multi_city_tracks)+1}",
                    'place': target_city.title(),
                    'lat': lat,
                    'lng': lng,
                    'threat_type': threat_type,
                    'text': ln[:500],
                    'date': date_str,
                    'channel': channel,
                    'marker_icon': icon,
                    'source_match': 'region_district',
                    'count': 1
                })
                add_debug_log(f"Created region-district marker: {target_city.title()}", "region_district")
                continue  # Skip further processing of this line
            else:
                add_debug_log(f"No coordinates found for district city: '{target_city}' (normalized: '{city_norm}')", "region_district")

        elif region_city_match:
            if region_city_match1:
                region_raw, count_str, city_raw = region_city_match1.groups()
                count = int(count_str) if count_str.isdigit() else 1
            else:  # region_city_match2
                region_raw, city_raw = region_city_match2.groups()
                count = 1  # default count for pattern 2

            target_city = city_raw.strip()

            add_debug_log(f"REGION-CITY pattern FOUND: region='{region_raw}', count={count}, city='{target_city}'", "region_city")

            # Normalize city name and try to find coordinates
            city_norm = target_city.lower()
            # Apply UA_CITY_NORMALIZE rules if available
            if 'UA_CITY_NORMALIZE' in globals():
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
            coords = CITY_COORDS.get(city_norm)

            add_debug_log(f"City lookup: '{target_city}' -> '{city_norm}' -> {coords}", "region_city")

            if coords:
                lat, lng = coords
                threat_type, icon = classify(ln)

                multi_city_tracks.append({
                    'id': f"{mid}_region_city_{len(multi_city_tracks)+1}",
                    'place': target_city.title(),
                    'lat': lat,
                    'lng': lng,
                    'threat_type': threat_type,
                    'text': ln[:500],
                    'date': date_str,
                    'channel': channel,
                    'marker_icon': icon,
                    'source_match': 'region_city_shahed',
                    'count': count
                })
                add_debug_log(f"Created region-city marker: {target_city.title()} ({count} шахедів)", "region_city")
                continue  # Skip further processing of this line
            else:
                add_debug_log(f"No coordinates found for city: '{target_city}' (normalized: '{city_norm}')", "region_city")
        else:
            add_debug_log(f"REGION-CITY pattern NOT FOUND for line: '{ln_lower}'", "region_city_debug")

        # NEW: Pattern "БпЛА на [direction] [region_genitive] курсом на [target]"
        # Example: "БпЛА на півночі Херсонщини курсом на Миколаївщину"
        regional_course_pattern = re.search(r'(бпла|безпілотник|шахед|дрон).*(на\s+(півночі|півдні|сході|заході|центрі))?\s*([а-яіїєґ]+щин[іуиа])\s*.*курсом\s+на\s+([а-яіїєґ\'\-\s]+)', ln_lower, re.IGNORECASE)
        if regional_course_pattern:
            direction_part = regional_course_pattern.group(3) if regional_course_pattern.group(2) else None
            region_genitive = regional_course_pattern.group(4)
            target_raw = regional_course_pattern.group(5).strip()

            # Normalize target (could be city or region)
            target_norm = target_raw.replace('щину', 'щина').replace('щини', 'щина').strip()

            add_debug_log(f"REGIONAL COURSE pattern: direction={direction_part}, region={region_genitive}, target={target_raw} -> {target_norm}", "regional_course")

            # Try to find coordinates for target
            target_city = normalize_city_name(target_norm)
            target_city = UA_CITY_NORMALIZE.get(target_city, target_city)
            coords = CITY_COORDS.get(target_city)
            if not coords and SETTLEMENTS_INDEX:
                coords = SETTLEMENTS_INDEX.get(target_city)

            # If target is a region (щина), use region center
            if not coords and ('щина' in target_city or 'щини' in target_city):
                # Try to get region center coordinates
                region_centers = {
                    'миколаївщина': (46.975, 31.995),
                    'херсонщина': (46.635, 32.617),
                    'чернігівщина': (51.4982, 31.2893),
                    'сумщина': (50.9077, 34.7981),
                    'полтавщина': (49.5883, 34.5514),
                    'харківщина': (49.9935, 36.2304),
                    'дніпропетровщина': (48.4647, 35.0462),
                    'запоріжжя': (47.8388, 35.1396),
                    'донеччина': (48.0159, 37.8028),
                }
                coords = region_centers.get(target_city)
                if coords:
                    add_debug_log(f"Using region center for '{target_city}': {coords}", "regional_course")

            if coords:
                lat, lng = coords
                threat_type, icon = classify(ln)

                # Extract count if present
                count_match = re.search(r'(\d+)\s*[xх×]?\s*(бпла|шахед)', ln_lower)
                count = int(count_match.group(1)) if count_match else 1

                place_label = target_norm.title()
                if direction_part:
                    place_label += f" ({direction_part})"

                multi_city_tracks.append({
                    'id': f"{mid}_regional_course_{len(multi_city_tracks)+1}",
                    'place': place_label,
                    'lat': lat,
                    'lng': lng,
                    'threat_type': threat_type,
                    'text': clean_text(ln)[:500],
                    'date': date_str,
                    'channel': channel,
                    'marker_icon': icon,
                    'source_match': 'regional_course',
                    'count': count
                })
                add_debug_log(f"Created regional course marker: {place_label} at {lat}, {lng}", "regional_course")
                continue
            else:
                add_debug_log(f"No coordinates for regional course target: '{target_raw}' (norm: '{target_city}')", "regional_course")

        # NEW: Check for regional direction patterns WITHOUT specific city (e.g. "БпЛА на сході Сумщини ➡️ курсом на південь")
        # These should create regional markers, not skip
        region_direction_pattern = re.search(r'(бпла|безпілотник|шахед|дрон).*(на\s+(півночі|півдні|сході|заході)).*([а-яіїєґ]+щин[іуиа])', ln_lower, re.IGNORECASE)
        if region_direction_pattern and not region_city_match and not regional_course_pattern:
            add_debug_log(f"REGIONAL DIRECTION pattern detected (no specific city): {ln[:100]}", "regional_direction")
            # This line should be processed by regional parser - don't add to multi_city_tracks yet
            # Instead, extract the region and direction to create a regional marker later
            # For now, just mark it for special processing

        # Check if line contains БпЛА information without specific course
        ln_lower = ln.lower()
        # Support both Cyrillic БпЛА and Latin-mixed БпЛA variants, and also Shahed
        has_uav = 'бпла' in ln_lower or 'бпла' in ln_lower or 'безпілотник' in ln_lower or 'дрон' in ln_lower or 'bpla' in ln_lower or 'шахед' in ln_lower or 'shahed' in ln_lower
        if has_uav:
            add_debug_log("Line contains UAV keywords", "multi_region")
            if not any(keyword in ln_lower for keyword in ['курс', 'на ', 'районі']):
                add_debug_log("UAV line lacks direction keywords (курс/на/районі) - general activity message", "multi_region")
        else:
            add_debug_log("Line does not contain UAV keywords", "multi_region")
        # Если строка — это заголовок области (например, "Сумщина:")
        # Заголовок области: строка, заканчивающаяся на ':' (возможен пробел перед / после) или формой '<область>:' с лишними пробелами
        # NEW: Also handle format like "**🚨 Конотопський район (Сумська обл.)**"
        import re
        oblast_hdr_match = None

        # Standard format: "Сумщина:" or "Чернігівщина:"
        if re.match(r'^[A-Za-zА-Яа-яЇїІіЄєҐґ\-ʼ`\s]+:\s*$', ln):
            oblast_hdr = ln.split(':')[0].strip().lower()
            oblast_hdr_match = True
            add_debug_log(f"Standard region header format detected: '{oblast_hdr}'", "multi_region")

        # NEW format: "**🚨 Конотопський район (Сумська обл.)**" or similar with oblast in parentheses
        elif re.search(r'\(([А-ЯІЇЄЁа-яіїєё]+ська\s+обл\.?)\)', ln):
            oblast_match = re.search(r'\(([А-ЯІЇЄЁа-яіїєё]+ська\s+обл\.?)\)', ln)
            if oblast_match:
                oblast_full = oblast_match.group(1).lower().strip()
                # Convert "сумська обл." to "сумщина"
                oblast_hdr = oblast_full.replace('ська обл.', 'щина').replace('ська обл', 'щина')
                oblast_hdr_match = True
                add_debug_log(f"Parentheses region header format detected: '{oblast_full}' -> '{oblast_hdr}'", "multi_region")

        # NEW format: "Харківщина — БпЛА на Гути" - region with dash followed by content
        elif re.search(r'^([А-ЯІЇЄЁа-яіїєё]+щина)\s*[-–—]\s*(.+)', ln):
            dash_match = re.search(r'^([А-ЯІЇЄЁа-яіїєё]+щина)\s*[-–—]\s*(.+)', ln)
            if dash_match:
                oblast_hdr = dash_match.group(1).lower().strip()
                remaining_content = dash_match.group(2).strip()
                oblast_hdr_match = True
                add_debug_log(f"Dash region header format detected: '{oblast_hdr}' with content: '{remaining_content}'", "multi_region")
                # Set the line content to just the remaining part after dash for further processing
                ln = remaining_content

        # NEW: Detect regional genitive forms like "Сумщини", "Харківщини", etc.
        elif re.search(r'\b([а-яіїєґ]+щин[иі])\b', ln_lower):
            genitive_match = re.search(r'\b([а-яіїєґ]+щин[иі])\b', ln_lower)
            if genitive_match:
                genitive_form = genitive_match.group(1)
                # Convert genitive to nominative: "сумщини" -> "сумщина"
                potential_oblast = genitive_form.replace('щини', 'щина').replace('щині', 'щина')

                # Validate that this is actually a known region, not just any word ending with щин[иі]
                known_regions = ['сумщина', 'чернігівщина', 'харківщина', 'полтавщина', 'херсонщина',
                               'донеччина', 'луганщина', 'запорожжя', 'дніпропетровщина', 'київщина',
                               'львівщина', 'івано-франківщина', 'тернопільщина', 'хмельниччина',
                               'рівненщина', 'волинщина', 'житомирщина', 'вінниччина', 'черкащина',
                               'кіровоградщина', 'миколаївщина', 'одещина']

                if potential_oblast in known_regions:
                    oblast_hdr = potential_oblast
                    oblast_hdr_match = True
                    add_debug_log(f"Genitive region format detected: '{genitive_form}' -> '{oblast_hdr}' in line: '{ln}'", "multi_region")
                    add_debug_log(f"POTENTIAL ISSUE: Oblast set to '{oblast_hdr}' from genitive pattern in: '{ln}'", "oblast_detection")
                else:
                    add_debug_log(f"Ignored potential genitive form '{genitive_form}' -> '{potential_oblast}' (not in known regions) in line: '{ln}'", "multi_region")

        if oblast_hdr_match:
            add_debug_log(f"Region header detected: '{oblast_hdr}'", "multi_region")
            if oblast_hdr.startswith('на '):  # handle 'на харківщина:' header variant
                oblast_hdr = oblast_hdr[3:].strip()
            if oblast_hdr and oblast_hdr[0] in ('е','є') and oblast_hdr.endswith('гівщина'):
                # восстановить черниговщина -> чернігівщина (fix dropped leading Ч)
                oblast_hdr = 'чернігівщина'
            # Доп. почин восстановлений первых букв для областей (потеря первой буквы)
            if oblast_hdr and oblast_hdr.endswith('ївщина') and oblast_hdr != 'київщина':
                oblast_hdr = 'київщина'
            if oblast_hdr and oblast_hdr.endswith('нниччина') and oblast_hdr != 'вінниччина':
                oblast_hdr = 'вінниччина'
            # header detected
            add_debug_log(f"Final region header: '{oblast_hdr}'", "multi_region")
            # IMPORTANT: Only continue (skip processing) if this is JUST a header, 
            # NOT a БПЛА message with oblast in parentheses like "БПЛА Семенівка (Полтавська обл.)"
            ln_lower_check = ln.lower()
            if not any(kw in ln_lower_check for kw in ['бпла', 'дрон', 'шахед', 'ракет', 'каб', 'балістик']):
                continue
            # Otherwise fall through to process this line as a threat message
        try:
            add_debug_log(f"MLINE_LINE oblast={oblast_hdr} raw='{ln}'", "multi_region")
        except Exception:
            pass

        # NEW: Check for specific direction patterns before falling back to general UAV activity
        import re
        ln_lower = ln.lower()

        # NEW: Pattern "кружляє над/над [city]"
        if 'кружляє' in ln_lower or 'кружля' in ln_lower:
            kruzhlia_match = re.search(r'кружля[єюя]\s+(?:над\s+)?([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)', ln, re.IGNORECASE)
            if kruzhlia_match:
                city_raw = kruzhlia_match.group(1).strip()
                city_norm = normalize_city_name(city_raw)
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
                coords = CITY_COORDS.get(city_norm) or (SETTLEMENTS_INDEX.get(city_norm) if SETTLEMENTS_INDEX else None)

                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(ln)
                    count_match = re.search(r'(\d+)[xх×]?\s*бпла', ln_lower)
                    count = int(count_match.group(1)) if count_match else 1

                    # Create multiple tracks if count > 1
                    for i in range(count):
                        place_label = city_norm.title()
                        if count > 1:
                            place_label += f" #{i+1} (кружляє)"
                        else:
                            place_label += " (кружляє)"

                        # Add offset for multiple drones
                        marker_lat, marker_lng = lat, lng
                        if count > 1:
                            offset_distance = 0.03
                            marker_lat += offset_distance * i
                            marker_lng += offset_distance * i * 0.5

                        multi_city_tracks.append({
                            'id': f"{mid}_kruzhlia_{len(multi_city_tracks)+1}",
                            'place': place_label,
                            'lat': marker_lat,
                            'lng': marker_lng,
                            'threat_type': threat_type,
                            'text': clean_text(ln)[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'kruzhlia_nad',
                            'count': 1
                        })
                    add_debug_log(f"Created {count} marker(s) for 'кружляє': {city_norm.title()}", "kruzhlia")
                    continue

        # NEW: Pattern "північніше/південніше/східніше/західніше [city]"
        if any(direction in ln_lower for direction in ['північніше', 'південніше', 'східніше', 'західніше']):
            direction_match = re.search(r'(північніше|південніше|східніше|західніше)\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)', ln, re.IGNORECASE)
            if direction_match:
                direction_type = direction_match.group(1).lower()
                city_raw = direction_match.group(2).strip()
                city_norm = normalize_city_name(city_raw)
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
                coords = CITY_COORDS.get(city_norm) or (SETTLEMENTS_INDEX.get(city_norm) if SETTLEMENTS_INDEX else None)

                if coords:
                    lat, lng = coords
                    # Apply directional offset based on direction type
                    offset = 0.15  # ~15km
                    if direction_type == 'північніше':
                        lat += offset
                    elif direction_type == 'південніше':
                        lat -= offset
                    elif direction_type == 'східніше':
                        lng += offset
                    elif direction_type == 'західніше':
                        lng -= offset

                    threat_type, icon = classify(ln)
                    count_match = re.search(r'(\d+)[xх×]?\s*бпла', ln_lower)
                    count = int(count_match.group(1)) if count_match else 1

                    # Create multiple tracks if count > 1
                    for i in range(count):
                        place_label = f"{direction_type.title()} {city_norm.title()}"
                        if count > 1:
                            place_label += f" #{i+1}"

                        # Add offset for multiple drones
                        marker_lat, marker_lng = lat, lng
                        if count > 1:
                            offset_distance = 0.03
                            marker_lat += offset_distance * i
                            marker_lng += offset_distance * i * 0.5

                        multi_city_tracks.append({
                            'id': f"{mid}_direction_{len(multi_city_tracks)+1}",
                            'place': place_label,
                            'lat': marker_lat,
                            'lng': marker_lng,
                            'threat_type': threat_type,
                            'text': clean_text(ln)[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': f'directional_{direction_type}',
                            'count': 1
                        })
                    add_debug_log(f"Created {count} marker(s) for '{direction_type}': {city_norm.title()}", "directional")
                    continue

        # NEW: Pattern "на/через [city]" - combined "на" and "через"
        if re.search(r'на/через\s+[А-ЯІЇЄЁа-яіїєё]', ln, re.IGNORECASE):
            na_cherez_match = re.search(r'(\d+)[xх×]?\s*бпла\s+на/через\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)', ln, re.IGNORECASE)
            if na_cherez_match:
                count = int(na_cherez_match.group(1)) if na_cherez_match.group(1) else 1
                city_raw = na_cherez_match.group(2).strip()
                city_norm = normalize_city_name(city_raw)
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
                coords = CITY_COORDS.get(city_norm) or (SETTLEMENTS_INDEX.get(city_norm) if SETTLEMENTS_INDEX else None)

                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(ln)

                    # Create multiple tracks if count > 1
                    for i in range(count):
                        place_label = city_norm.title()
                        if count > 1:
                            place_label += f" #{i+1} (на/через)"
                        else:
                            place_label += " (на/через)"

                        # Add offset for multiple drones
                        marker_lat, marker_lng = lat, lng
                        if count > 1:
                            offset_distance = 0.03
                            marker_lat += offset_distance * i
                            marker_lng += offset_distance * i * 0.5

                        multi_city_tracks.append({
                            'id': f"{mid}_na_cherez_{len(multi_city_tracks)+1}",
                            'place': place_label,
                            'lat': marker_lat,
                            'lng': marker_lng,
                            'threat_type': threat_type,
                            'text': clean_text(ln)[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'na_cherez',
                            'count': 1
                        })
                    add_debug_log(f"Created {count} marker(s) for 'на/через': {city_norm.title()}", "na_cherez")
                    continue

        # NEW: Pattern "з ТОТ в напрямку [city]" - drones from occupied territory
        if 'з тот' in ln_lower or 'з tot' in ln_lower:
            tot_match = re.search(r'(\d+)[xх×]?\s*бпла\s+з\s+тот\s+(?:в\s+напрямку|на)\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)', ln, re.IGNORECASE)
            if tot_match:
                count = int(tot_match.group(1)) if tot_match.group(1) else 1
                city_raw = tot_match.group(2).strip()
                city_norm = normalize_city_name(city_raw)
                city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
                coords = CITY_COORDS.get(city_norm) or (SETTLEMENTS_INDEX.get(city_norm) if SETTLEMENTS_INDEX else None)

                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(ln)

                    # Create multiple tracks if count > 1
                    for i in range(count):
                        place_label = city_norm.title()
                        if count > 1:
                            place_label += f" #{i+1} (з ТОТ)"
                        else:
                            place_label += " (з ТОТ)"

                        # Add offset for multiple drones
                        marker_lat, marker_lng = lat, lng
                        if count > 1:
                            offset_distance = 0.03
                            marker_lat += offset_distance * i
                            marker_lng += offset_distance * i * 0.5

                        multi_city_tracks.append({
                            'id': f"{mid}_tot_{len(multi_city_tracks)+1}",
                            'place': place_label,
                            'lat': marker_lat,
                            'lng': marker_lng,
                            'threat_type': threat_type,
                            'text': clean_text(ln)[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'z_tot',
                            'count': 1
                        })
                    add_debug_log(f"Created {count} marker(s) for 'з ТОТ': {city_norm.title()}", "z_tot")
                    continue

        # Check if line has БпЛА or starts with a number (implying drones)
        has_bpla = 'бпла' in ln_lower
        starts_with_number = re.match(r'^\d+', ln.strip())
        has_direction_pattern = any(pattern in ln_lower for pattern in ['у напрямку', 'через', 'повз'])

        if (has_bpla or starts_with_number) and has_direction_pattern:
            target_cities = []

            # Pattern 1: "у напрямку [city]"
            naprym_pattern = r'у\s+напрямку\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)'
            naprym_matches = re.findall(naprym_pattern, ln, re.IGNORECASE)
            for city_raw in naprym_matches:
                target_cities.append(('у напрямку', city_raw.strip()))

            # Pattern 2: "через [city]"
            cherez_pattern = r'через\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)'
            cherez_matches = re.findall(cherez_pattern, ln, re.IGNORECASE)
            for city_raw in cherez_matches:
                target_cities.append(('через', city_raw.strip()))

            # Pattern 3: "повз [city]"
            povz_pattern = r'повз\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*[\.\,\!\?;]|$)'
            povz_matches = re.findall(povz_pattern, ln, re.IGNORECASE)
            for city_raw in povz_matches:
                target_cities.append(('повз', city_raw.strip()))

            # Process extracted target cities
            for direction_type, city_raw in target_cities:
                city_clean = city_raw.strip()
                city_norm = city_clean.lower()

                # Apply UA_CITY_NORMALIZE rules
                if city_norm in UA_CITY_NORMALIZE:
                    city_norm = UA_CITY_NORMALIZE[city_norm]

                # Try to get coordinates
                coords = CITY_COORDS.get(city_norm)
                if not coords and SETTLEMENTS_INDEX:
                    coords = SETTLEMENTS_INDEX.get(city_norm)
                if not coords:
                    coords = SETTLEMENT_FALLBACK.get(city_norm) if 'SETTLEMENT_FALLBACK' in globals() else None

                add_debug_log(f"Direction pattern '{direction_type}' found city: '{city_raw}' -> '{city_norm}' -> coords: {coords}", "direction_processing")

                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(ln)

                    # Create label showing direction
                    place_label = city_clean.title()
                    if direction_type == 'у напрямку':
                        place_label += " (напрямок)"
                    elif direction_type == 'через':
                        place_label += " (через)"
                    elif direction_type == 'повз':
                        place_label += " (повз)"

                    multi_city_tracks.append({
                        'id': f"{mid}_direction_{len(multi_city_tracks)+1}",
                        'place': place_label,
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': clean_text(ln)[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': f'direction_{direction_type.replace(" ", "_")}',
                        'count': 1
                    })
                    add_debug_log(f"Created direction marker: {place_label} ({direction_type})", "direction_processing")
                else:
                    add_debug_log(f"No coordinates found for direction target: '{city_raw}' (normalized: '{city_norm}')", "direction_processing")

            # If we found any target cities with valid coordinates, skip general UAV processing
            if any(coords for _, coords in [(city_norm, CITY_COORDS.get(UA_CITY_NORMALIZE.get(city_raw.strip().lower(), city_raw.strip().lower()))) for _, city_raw in target_cities]):
                add_debug_log(f"Direction processing complete, skipping general UAV activity for line: '{ln}'", "direction_processing")
                continue

        # NEW: Create markers for general UAV activity messages (without specific direction)
        if 'бпла' in ln_lower or 'безпілотник' in ln_lower or 'дрон' in ln_lower:
            add_debug_log(f"UAV activity detected in line: '{ln}', oblast_hdr: '{oblast_hdr}'", "uav_processing")

            # CRITICAL: Check if message has specific directional patterns - if yes, skip general marker
            # Let the main parser handle "курсом на", "напрямок на", "у напрямку", "на [місто]" etc.
            has_directional_pattern = any(pattern in ln_lower for pattern in [
                'курсом на', 'курс на', 'напрямок на', 'напрямку на',
                'ціль на', 'у напрямку', 'у бік', 'в бік', 'через', 'повз',
                'маневрує в районі', 'в районі', 'бпла на ', 'дрон на '
            ])

            # Check for emoji arrows BUT only if there's actual text (city name) after the arrow
            if '➡' in ln and not has_directional_pattern:
                # Extract text after arrow to see if there's a city name
                arrow_match = re.search(r'➡[️\s]*(.{3,})', ln)
                if arrow_match:
                    text_after_arrow = arrow_match.group(1).strip().strip('ㅤ️ ').strip()
                    # If there's meaningful text after arrow (not just punctuation/links), treat as directional
                    if text_after_arrow and len(text_after_arrow) > 1 and not text_after_arrow.startswith(('http', '[', '**', '➡')):
                        has_directional_pattern = True

            if has_directional_pattern:
                add_debug_log(f"SKIP general UAV marker - has directional pattern: '{ln}'", "uav_processing")
                # Don't create general marker - let main parser extract specific city
                continue

            # Check if we have a region and this is a UAV message
            if oblast_hdr:
                add_debug_log(f"Processing UAV with region context: '{oblast_hdr}'", "uav_processing")
                # Find the main city of the region to place the marker
                region_cities = {
                    'сумщина': 'суми',
                    'чернігівщина': 'чернігів',
                    'херсонщина': 'херсон',
                    'харківщина': 'харків',
                    'донеччина': 'краматорськ',  # safer than донецьк
                    'луганщина': 'сєвєродонецьк',
                    'запорожжя': 'запоріжжя',
                    'дніпропетровщина': 'дніпро',
                    'полтавщина': 'полтава',
                    'київщина': 'київ',
                    'львівщина': 'львів',
                    'івано-франківщина': 'івано-франківськ',
                    'тернопільщина': 'тернопіль',
                    'хмельниччина': 'хмельницький',
                    'рівненщина': 'рівне',
                    'волинщина': 'луцьк',
                    'житомирщина': 'житомир',
                    'вінниччина': 'вінниця',
                    'черкащина': 'черкаси',
                    'кіровоградщина': 'кропивницький',
                    'миколаївщина': 'миколаїв',
                    'одещина': 'одеса'
                }

                # Special coordinates for aviation threats over regions (e.g., aircraft over Black Sea for Odesa)
                region_aviation_coords = {
                    'одещина': (46.373528, 31.284023),  # Black Sea near Odesa for aviation threats
                    'одесщина': (46.373528, 31.284023),
                }

                region_city = region_cities.get(oblast_hdr)
                if region_city:
                    # Check if message refers to entire region rather than specific city
                    # Skip marker creation for some regional threats, but create for KAB/aviation bombs
                    genitive_form = oblast_hdr.replace('щина', 'щини')  # сумщина -> сумщини
                    dative_form = oblast_hdr.replace('щина', 'щині')    # сумщина -> сумщині
                    accusative_form = oblast_hdr + 'у'                  # сумщина -> сумщину

                    is_regional_threat = any(regional_ref in ln_lower for regional_ref in [
                        f'на {oblast_hdr}', f'{accusative_form}', f'{genitive_form}', f'{dative_form}',
                        f'для {genitive_form}', f'по {dative_form}'
                    ])

                    # For KAB/aviation bombs and aviation threats, always create marker even for regional threats
                    has_kab = any(kab_word in ln_lower for kab_word in ['каб', 'авіабомб', 'авиабомб'])
                    has_aviation_threat = any(avia_word in ln_lower for avia_word in [
                        'авіаційних засобів ураження', 'авіаційних засобів', 'застосування авіації',
                        'тактична авіація', 'тактичної авіації'
                    ])

                    if is_regional_threat and not has_kab and not has_aviation_threat:
                        add_debug_log(f"Skipping regional threat marker - affects entire region: {oblast_hdr} (found: {[ref for ref in [f'на {oblast_hdr}', accusative_form, genitive_form, dative_form] if ref in ln_lower]})", "multi_region")
                        continue

                    # Check if this is an aviation threat and use special coordinates if available
                    coords = None
                    if has_aviation_threat and oblast_hdr in region_aviation_coords:
                        coords = region_aviation_coords[oblast_hdr]
                        label = f"Авіація [{oblast_hdr.title()}]"
                        add_debug_log(f"Using aviation coordinates for {oblast_hdr}: {coords}", "aviation_region")

                    # Otherwise, try to find coordinates for the region's main city
                    if not coords:
                        base_city = normalize_city_name(region_city)
                        base_city = UA_CITY_NORMALIZE.get(base_city, base_city)
                        coords = CITY_COORDS.get(base_city) or (SETTLEMENTS_INDEX.get(base_city) if SETTLEMENTS_INDEX else None)
                        label = base_city.title()
                        label += f" [{oblast_hdr.title()}]"

                    if coords:
                        lat, lng = coords

                        # Determine threat type based on message content using classify function
                        threat_type, icon = classify(ln)
                        # Keep shahed as default for UAV if classify doesn't return anything specific
                        if not threat_type:
                            threat_type = 'shahed'

                        multi_city_tracks.append({
                            'id': f"{mid}_general_uav_{len(multi_city_tracks)+1}",
                            'place': label,
                            'lat': lat,
                            'lng': lng,
                            'threat_type': threat_type,
                            'text': clean_text(ln)[:500],
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': 'general_uav_activity',
                            'count': 1
                        })
                        add_debug_log(f"Created general UAV marker: {label} ({threat_type})", "multi_region")
                        add_debug_log(f"MARKER CREATION: oblast_hdr='{oblast_hdr}', region_city='{region_city}', coords=({lat}, {lng})", "marker_creation")
                        continue  # move to next line

        # NEW: Handle UAV messages without region but with city name
        ln_lower = ln.lower()
        if (not oblast_hdr) and ('бпла' in ln_lower or 'безпілотник' in ln_lower or 'дрон' in ln_lower or 'обстріл' in ln_lower or 'вибух' in ln_lower):
            # Try to extract city name from the message
            import re
            # Pattern for messages like "❗️ Синельникове — 1х БпЛА довкола" or "💥 Херсон — обстріл"
            city_match = re.search(r'[❗️⚠️🛸💥]*\s*([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ]{2,30}(?:ське|цьке|ський|ський район|ове|еве|ине|ино|івка|івськ|ськ|град|город)?)', ln)
            if city_match:
                city_name = city_match.group(1).strip()

                # Normalize city name
                base_city = normalize_city_name(city_name)
                base_city = UA_CITY_NORMALIZE.get(base_city, base_city)
                coords = CITY_COORDS.get(base_city) or (SETTLEMENTS_INDEX.get(base_city) if SETTLEMENTS_INDEX else None)

                if coords:
                    lat, lng = coords
                    label = base_city.title()

                    # Determine threat type based on message content using classify function
                    threat_type, icon = classify(ln)
                    # Keep shahed as default for UAV if classify doesn't return anything specific
                    if not threat_type:
                        threat_type = 'shahed'
                        icon = 'shahed3.webp'

                    multi_city_tracks.append({
                        'id': f"{mid}_city_threat_{len(multi_city_tracks)+1}",
                        'place': label,
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': clean_text(ln)[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': 'city_threat_activity',
                        'count': 1
                    })
                    add_debug_log(f"Created city threat marker: {label} ({threat_type})", "multi_region")
                    continue  # move to next line

        # --- NEW: БпЛА курсом на [city] pattern (e.g., "4х БпЛА курсом на Конотоп") ---
        # ВАЖЛИВО: Підтримка багатослівних назв міст (наприклад "Жовті Води")
        uav_course_city = None
        uav_course_count = 1
        # Pattern: "Nх БпЛА курсом на [city]" or "БпЛА курсом на [city]"
        # Захоплює назву міста до кінця рядка або до розділових знаків
        m_uav_course = re.search(r'(?:^|\b)(?:([0-9]+)[xх×]?\s*)?(?:бпла|шахед(?:и|ів)?|дрон(?:и)?)\s+курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]+?)(?:\s*$|[,\.\!\?;])', ln, re.IGNORECASE)
        if m_uav_course:
            if m_uav_course.group(1):
                try:
                    uav_course_count = int(m_uav_course.group(1))
                except:
                    uav_course_count = 1
            uav_course_city = m_uav_course.group(2).strip()

            add_debug_log(f"UAV course pattern found: {uav_course_count}x БпЛА курсом на '{uav_course_city}'", "multi_region")

        if uav_course_city:
            candidate_cities = extract_course_targets(uav_course_city)
            add_debug_log(f"extract_course_targets('{uav_course_city}') returned: {candidate_cities}", "multi_region")
            per_marker_count = uav_course_count if len(candidate_cities) <= 1 else 1
            created_course_markers = False
            for dest_city in candidate_cities or [uav_course_city]:
                if not dest_city:
                    continue
                base_uav = normalize_city_name(dest_city)
                base_uav = UA_CITY_NORMALIZE.get(base_uav, base_uav)
                coords_uav = CITY_COORDS.get(base_uav) or (SETTLEMENTS_INDEX.get(base_uav) if SETTLEMENTS_INDEX else None)
                add_debug_log(f"Geocoding '{dest_city}' -> normalized: '{base_uav}' -> coords: {coords_uav}", "multi_region")

                # Try region-specific lookup if oblast_hdr is set
                if not coords_uav and oblast_hdr:
                    combo_uav = f"{base_uav} {oblast_hdr}"
                    coords_uav = CITY_COORDS.get(combo_uav) or (SETTLEMENTS_INDEX.get(combo_uav) if SETTLEMENTS_INDEX else None)
                    add_debug_log(f"Trying region combo: '{combo_uav}' -> {coords_uav}", "multi_region")

                if not coords_uav:
                    add_debug_log(f"No coords found for '{dest_city}' (normalized: '{base_uav}', oblast: '{oblast_hdr}')", "multi_region")
                    continue
                created_course_markers = True
                lat, lng = coords_uav
                label = UA_CITY_NORMALIZE.get(base_uav, base_uav).title()
                if per_marker_count > 1:
                    label += f" ({per_marker_count}x)"
                if oblast_hdr and oblast_hdr not in label.lower():
                    label += f" [{oblast_hdr.title()}]"

                multi_city_tracks.append({
                    'id': f"{mid}_mc{len(multi_city_tracks)+1}",
                    'place': label,
                    'lat': lat,
                    'lng': lng,
                    'threat_type': 'shahed',
                    'text': clean_text(ln)[:500],
                    'date': date_str,
                    'channel': channel,
                    'marker_icon': 'shahed3.webp',
                    'source_match': 'multiline_uav_course',
                    'count': per_marker_count
                })
                add_debug_log(f"Created UAV course marker: {label}", "multi_region")
            if created_course_markers:
                continue  # move to next line
            else:
                base_uav = normalize_city_name(sanitize_course_destination(uav_course_city))
                add_debug_log(f"No coordinates found for UAV course city: '{uav_course_city}' (normalized: '{base_uav}')", "multi_region")

        # Continue processing other patterns even if UAV course didn't match
        # Don't skip the line completely

        # Пытаемся найти город и количество (например, "2х БпЛА курсом на Десну")
        import re
        # --- NEW: распознавание ракетных строк внутри многострочного блока ---
        # Примеры: "1 ракета на Холми", "2 ракети на Лубни", "3 ракеты на Лубни", "ракета на <місто>"
        rocket_city = None; rocket_count = 1
        mr = re.search(r'(?:^|\b)(?:([0-9]+)\s*)?(ракета|ракети|ракет)\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{2,40})', ln, re.IGNORECASE)
        if mr:
            if mr.group(1):
                try: rocket_count = int(mr.group(1))
                except: rocket_count = 1
            rocket_city = mr.group(3)
        if rocket_city:
            base_r = normalize_city_name(rocket_city)
            base_r = UA_CITY_NORMALIZE.get(base_r, base_r)
            coords_r = CITY_COORDS.get(base_r) or (SETTLEMENTS_INDEX.get(base_r) if SETTLEMENTS_INDEX else None)
            if not coords_r and oblast_hdr:
                combo_r = f"{base_r} {oblast_hdr}"
                coords_r = CITY_COORDS.get(combo_r) or (SETTLEMENTS_INDEX.get(combo_r) if SETTLEMENTS_INDEX else None)
            if coords_r:
                lat, lng = coords_r
                label = UA_CITY_NORMALIZE.get(base_r, base_r).title()
                if rocket_count > 1:
                    label += f" ({rocket_count})"
                if oblast_hdr and oblast_hdr not in label.lower():
                    label += f" [{oblast_hdr.title()}]"
                multi_city_tracks.append({
                    'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                    'threat_type': 'rszv', 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': 'icon_missile.svg', 'source_match': 'multiline_oblast_city_rocket', 'count': rocket_count
                })
                continue  # переходим к следующей строке (не пытаемся распознать как БпЛА)
        # --- NEW: группы крылатых ракет ("Група/Групи КР курсом на <город>") ---
        kr_city = None; kr_count = 1
        # Primary straightforward pattern for "Група/Групи КР курсом на <місто>"
        mkr = re.search(r'(?:^|\b)(?:([0-9]+)[xх×]?\s*)?груп[аи]\s+кр\b.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
        if not mkr:
            # Tolerant pattern allowing missing leading "г" or space glitches / lost letters
            mkr = re.search(r'(?:^|\b)(?:([0-9]+)[xх×]?\s*)?(?:г)?руп[аи]\s*(?:к)?р\b.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
        if not mkr and 'груп' in ln.lower() and 'курс' in ln.lower() and ' на ' in ln.lower():
            # Very loose fallback if 'КР' fragment dropped; capture after last 'на'
            after = ln.rsplit('на',1)[-1].strip()
            after = re.split(r'[,.!?:;]', after)[0].strip()
            if len(after) >= 3:
                class Dummy: pass
                mkr = Dummy(); mkr.group = lambda i: None if i==1 else after
        if mkr:
            try:
                log.info(f"KR_MATCH line='{ln}' groups={mkr.groups()}")
            except Exception:
                pass
            if mkr.group(1):
                try: kr_count = int(mkr.group(1))
                except: kr_count = 1
            kr_city = mkr.group(2)
        if kr_city:
            base_k = normalize_city_name(kr_city)
            base_k = UA_CITY_NORMALIZE.get(base_k, base_k)
            coords_k = CITY_COORDS.get(base_k) or (SETTLEMENTS_INDEX.get(base_k) if SETTLEMENTS_INDEX else None)
            if not coords_k and oblast_hdr:
                combo_k = f"{base_k} {oblast_hdr}"
                coords_k = CITY_COORDS.get(combo_k) or (SETTLEMENTS_INDEX.get(combo_k) if SETTLEMENTS_INDEX else None)
            if coords_k:
                lat, lng = coords_k
                label = UA_CITY_NORMALIZE.get(base_k, base_k).title()
                if kr_count > 1:
                    label += f" ({kr_count})"
                if oblast_hdr and oblast_hdr not in label.lower():
                    label += f" [{oblast_hdr.title()}]"
                multi_city_tracks.append({
                    'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                    'threat_type': 'raketa', 'text': ln[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': 'icon_balistic.svg', 'source_match': 'multiline_oblast_city_kr_group', 'count': kr_count
                })
                continue
        # Universal KR fallback (handles degraded OCR lines like '3х рупи  курсом на рилуки')
        low_ln = ln.lower()
        if ('курс' in low_ln and ' на ' in low_ln and ('груп' in low_ln or ' кр' in low_ln)):
            # Extract count if present at start or before 'груп'
            mcnt = re.search(r'^(\d+(?:-\d+)?)[xх×]?\s*', low_ln)
            count_guess = 1
            if mcnt:
                try: count_guess = int(mcnt.group(1))
                except: pass
            # Try after last 'на '
            parts = low_ln.rsplit(' на ', 1)
            if len(parts) == 2:
                cand = parts[1]
                cand = re.split(r'[\n,.!?:;]', cand)[0].strip()
                # strip residual non-letter chars
                cand_clean = re.sub(r"[^A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]", '', cand).strip()
                if len(cand_clean) >= 3:
                    base_f = normalize_city_name(cand_clean)
                    base_f = UA_CITY_NORMALIZE.get(base_f, base_f)
                    coords_f = CITY_COORDS.get(base_f) or (SETTLEMENTS_INDEX.get(base_f) if SETTLEMENTS_INDEX else None)
                    if not coords_f and oblast_hdr:
                        combo_f = f"{base_f} {oblast_hdr}"
                        coords_f = CITY_COORDS.get(combo_f) or (SETTLEMENTS_INDEX.get(combo_f) if SETTLEMENTS_INDEX else None)
                    # Fuzzy repair: if still not found, try restoring a potentially lost first letter
                    if not coords_f:
                        for pref in ['н','к','ч','п','г','с','в','б','д','м','т','л']:
                            test_base = pref + base_f
                            coords_try = CITY_COORDS.get(test_base) or (SETTLEMENTS_INDEX.get(test_base) if SETTLEMENTS_INDEX else None)
                            if not coords_try and oblast_hdr:
                                combo_try = f"{test_base} {oblast_hdr}"
                                coords_try = CITY_COORDS.get(combo_try) or (SETTLEMENTS_INDEX.get(combo_try) if SETTLEMENTS_INDEX else None)
                            if coords_try:
                                base_f = test_base
                                coords_f = coords_try
                                try: log.info(f"KR_FUZZ_REPAIR first_letter pref='{pref}' -> {base_f}")
                                except Exception: pass
                                break
                    if coords_f:
                        lat, lng = coords_f
                        label = UA_CITY_NORMALIZE.get(base_f, base_f).title()
                        if count_guess > 1:
                            label += f" ({count_guess})"
                        if oblast_hdr and oblast_hdr not in label.lower():
                            label += f" [{oblast_hdr.title()}]"
                        multi_city_tracks.append({
                            'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                            'threat_type': 'raketa', 'text': ln[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'icon_balistic.svg', 'source_match': 'multiline_oblast_city_kr_group_fallback2', 'count': count_guess
                        })
                        continue
        # Generic course fallback (any remaining 'курс' + ' на ' line not yet matched)
        if 'курс' in low_ln and ' на ' in low_ln and not any(tag in low_ln for tag in ['бпла','shahed']) and not any(mt['id'] == f"{mid}_mc{len(multi_city_tracks)+1}" for mt in multi_city_tracks):
            parts = low_ln.rsplit(' на ',1)
            if len(parts)==2:
                cand = re.split(r'[\n,.!?:;]', parts[1])[0].strip()
                cand = re.sub(r"[^A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]", '', cand)
                if len(cand) >= 3:
                    base_g = normalize_city_name(cand)
                    base_g = UA_CITY_NORMALIZE.get(base_g, base_g)
                    coords_g = CITY_COORDS.get(base_g) or (SETTLEMENTS_INDEX.get(base_g) if SETTLEMENTS_INDEX else None)
                    if not coords_g and oblast_hdr:
                        combo_g = f"{base_g} {oblast_hdr}"
                        coords_g = CITY_COORDS.get(combo_g) or (SETTLEMENTS_INDEX.get(combo_g) if SETTLEMENTS_INDEX else None)
                    # NEW: allow oblast center lookup if destination is a region (e.g. полтавщина / полтавщину)
                    if not coords_g and base_g in OBLAST_CENTERS:
                        coords_g = OBLAST_CENTERS[base_g]
                        try: log.info(f"GENERIC_COURSE_REGION dest='{base_g}' -> oblast center")
                        except Exception: pass
                    if not coords_g:
                        for pref in ['к','с','о','л','б','в','ж','т','я','у','р','н','п','г','ч']:
                            test = pref + base_g
                            coords_try = CITY_COORDS.get(test) or (SETTLEMENTS_INDEX.get(test) if SETTLEMENTS_INDEX else None)
                            if not coords_try and oblast_hdr:
                                combo_try = f"{test} {oblast_hdr}"
                                coords_try = CITY_COORDS.get(combo_try) or (SETTLEMENTS_INDEX.get(combo_try) if SETTLEMENTS_INDEX else None)
                            if coords_try:
                                base_g = test
                                coords_g = coords_try
                                try: log.info(f"GENERIC_FUZZ_CITY pref='{pref}' -> {base_g}")
                                except Exception: pass
                                break
                    if not coords_g:
                        for pref in ['н','к','ч','п','г','с','в','б','д','м','т','л']:
                            test_base = pref + base_g
                            coords_try = CITY_COORDS.get(test_base) or (SETTLEMENTS_INDEX.get(test_base) if SETTLEMENTS_INDEX else None)
                            if not coords_try and oblast_hdr:
                                combo_try = f"{test_base} {oblast_hdr}"
                                coords_try = CITY_COORDS.get(combo_try) or (SETTLEMENTS_INDEX.get(combo_try) if SETTLEMENTS_INDEX else None)
                            if coords_try:
                                base_g = test_base
                                coords_g = coords_try
                                try: log.info(f"GENERIC_COURSE_FUZZ pref='{pref}' -> {base_g}")
                                except Exception: pass
                                break
                    if coords_g:
                        lat, lng = coords_g
                        label = UA_CITY_NORMALIZE.get(base_g, base_g).title()
                        if oblast_hdr and oblast_hdr not in label.lower():
                            label += f" [{oblast_hdr.title()}]"
                        multi_city_tracks.append({
                            'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                            'threat_type': 'raketa', 'text': ln[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'icon_balistic.svg', 'source_match': 'multiline_oblast_city_course_generic', 'count': 1
                        })
                        continue
        # Fallback KR pattern if above failed but line mentions 'КР' and 'курс'
        if 'кр' in ln.lower() and 'курс' in ln.lower() and ' на ' in f" {ln.lower()} ":
            mkr2 = re.search(r'курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
            if mkr2:
                base_k2 = normalize_city_name(mkr2.group(1))
                base_k2 = UA_CITY_NORMALIZE.get(base_k2, base_k2)
                coords_k2 = CITY_COORDS.get(base_k2) or (SETTLEMENTS_INDEX.get(base_k2) if SETTLEMENTS_INDEX else None)
                if not coords_k2 and oblast_hdr:
                    combo_k2 = f"{base_k2} {oblast_hdr}"
                    coords_k2 = CITY_COORDS.get(combo_k2) or (SETTLEMENTS_INDEX.get(combo_k2) if SETTLEMENTS_INDEX else None)
                if not coords_k2:
                    for pref in ['н','к','ч','п','г','с','в','б','д','м','т','л']:
                        test_base = pref + base_k2
                        coords_try = CITY_COORDS.get(test_base) or (SETTLEMENTS_INDEX.get(test_base) if SETTLEMENTS_INDEX else None)
                        if not coords_try and oblast_hdr:
                            combo_try = f"{test_base} {oblast_hdr}"
                            coords_try = CITY_COORDS.get(combo_try) or (SETTLEMENTS_INDEX.get(combo_try) if SETTLEMENTS_INDEX else None)
                        if coords_try:
                            base_k2 = test_base
                            coords_k2 = coords_try
                            try: log.info(f"KR_FALLBACK_FUZZ pref='{pref}' -> {base_k2}")
                            except Exception: pass
                            break
                if coords_k2:
                    lat, lng = coords_k2
                    label = UA_CITY_NORMALIZE.get(base_k2, base_k2).title()
                    if oblast_hdr and oblast_hdr not in label.lower():
                        label += f" [{oblast_hdr.title()}]"
                    multi_city_tracks.append({
                        'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                        'threat_type': 'raketa', 'text': ln[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': 'icon_balistic.svg', 'source_match': 'multiline_oblast_city_kr_group_fallback', 'count': 1
                    })
                    continue
        # Разрешаем многословные названия (до 3 слов) до конца строки / знака препинания
        m = re.search(r'(\d+)[xх×]?\s*бпла.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
        if m:
            count = int(m.group(1))
            city = m.group(2)
        else:
            # Дополнительно поддерживаем строки вида "7х БпЛА повз <місто> ..." или "БпЛА повз <місто>"
            m2 = re.search(r'бпла.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
            if m2:
                count = 1
                city = m2.group(1)
            else:
                m3 = re.search(r'(\d+)[xх×]?\s*бпла.*?повз\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
                if m3:
                    count = int(m3.group(1))
                    city = m3.group(2)
                else:
                    m4 = re.search(r'бпла.*?повз\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\!\?;]|$)', ln, re.IGNORECASE)
                    count = 1
                    city = m4.group(1) if m4 else None
        # --- NEW: Shahed lines inside multi-line block (e.g. '2 шахеди на Старий Салтів', '1 шахед на Мерефа / Борки') ---
        if not city:
            m_sha = re.search(r'^(?:([0-9]+)\s*[xх×]?\s*)?шахед(?:и|ів)?\s+на\s+(.+)$', ln.strip(), re.IGNORECASE)
            if m_sha:
                try:
                    scount = int(m_sha.group(1) or '1')
                except Exception:
                    scount = 1
                cities_part = m_sha.group(2)
                # Apply extract_course_targets to properly sanitize destinations (removes /район, etc.)
                raw_parts = extract_course_targets(cities_part)
                add_debug_log(f"Shahed pattern: '{cities_part}' -> sanitized targets: {raw_parts}", "multi_region")
                for ci in raw_parts:
                    c_raw = ci.strip().strip('.').strip()
                    if not c_raw or len(c_raw) < 2:
                        continue
                    cbase = normalize_city_name(c_raw)
                    cbase = UA_CITY_NORMALIZE.get(cbase, cbase)
                    coords_s = CITY_COORDS.get(cbase) or (SETTLEMENTS_INDEX.get(cbase) if SETTLEMENTS_INDEX else None)
                    add_debug_log(f"Shahed geocoding: '{ci}' -> normalized '{cbase}' -> coords {coords_s}", "multi_region")
                    if not coords_s and oblast_hdr:
                        combo_s = f"{cbase} {oblast_hdr}"
                        coords_s = CITY_COORDS.get(combo_s) or (SETTLEMENTS_INDEX.get(combo_s) if SETTLEMENTS_INDEX else None)
                    if not coords_s:
                        for pref in ['с','м','к','б','г','ч','н','п','т','в','л']:
                            test = pref + cbase
                            coords_try = CITY_COORDS.get(test) or (SETTLEMENTS_INDEX.get(test) if SETTLEMENTS_INDEX else None)
                            if not coords_try and oblast_hdr:
                                combo_try = f"{test} {oblast_hdr}"
                                coords_try = CITY_COORDS.get(combo_try) or (SETTLEMENTS_INDEX.get(combo_try) if SETTLEMENTS_INDEX else None)
                            if coords_try:
                                cbase = test; coords_s = coords_try; break
                    if not coords_s:
                        add_debug_log(f"No coords found for shahed dest '{ci}' (norm: '{cbase}')", "multi_region")
                        continue
                    lat, lng = coords_s
                    label = UA_CITY_NORMALIZE.get(cbase, cbase).title()
                    per_count = scount if len(raw_parts) == 1 else 1
                    if oblast_hdr and oblast_hdr not in label.lower():
                        label += f" [{oblast_hdr.title()}]"

                    # Create multiple tracks for multiple shaheds
                    tracks_to_create = max(1, per_count)
                    for i in range(tracks_to_create):
                        track_label = label
                        if tracks_to_create > 1:
                            track_label += f" #{i+1}"

                        # Add small coordinate offsets to prevent marker overlap
                        marker_lat = lat
                        marker_lng = lng
                        if tracks_to_create > 1:
                            # Create a chain pattern - drones one after another
                            offset_distance = 0.03  # ~3km offset between each drone
                            marker_lat += offset_distance * i
                            marker_lng += offset_distance * i * 0.5

                        multi_city_tracks.append({
                            'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': track_label, 'lat': marker_lat, 'lng': marker_lng,
                            'threat_type': 'shahed', 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'shahed3.webp', 'source_match': 'multiline_oblast_city_shahed', 'count': 1
                        })
                continue

        # --- NEW: Pattern "N на City1 N на City2..." (e.g. "Харківщина 1 на Вільшани 1 на Kov'яги 1 на Бірки") ---
        # Handles multiple "number + на + city" sequences in a single line WITHOUT repeating "БпЛА"
        # IMPORTANT: Pattern supports mixed Cyrillic/Latin city names (e.g. "Kov'яги")
        if re.search(r'(\d+)\s+на\s+[A-ZА-ЯІЇЄa-zа-яіїєґ\'\-]+', ln, re.IGNORECASE):
            # Find all "N на City" patterns in the line (supports mixed Cyrillic/Latin)
            multi_na_pattern = re.findall(r'(\d+)\s+на\s+([A-ZА-ЯІЇЄa-zа-яіїєґ\'\-]+(?:/[A-ZА-ЯІЇЄa-zа-яіїєґ\'\-]+)?)', ln, re.IGNORECASE)

            if len(multi_na_pattern) > 1:  # Multiple "N на City" patterns found - this is our case!
                add_debug_log(f"MULTI-NA pattern found {len(multi_na_pattern)} cities in line: '{ln}'", "multi_na")
                add_debug_log(f"MULTI-NA current region header (oblast_hdr): '{oblast_hdr}'", "multi_na")

                # Regional overrides for cities with duplicate names in different oblasts
                REGIONAL_CITY_COORDS = {
                    'харківщина': {
                        'вільшани': (50.177, 35.398),  # Вільшани, Харківська обл., Богодухівський район
                        'ковяги': (49.75, 36.12),       # Ков'яги, Харківська обл.
                        'березівка': (49.583, 36.450),  # Березівка, Харківська обл.
                    },
                    # Add more regional overrides as needed
                }

                for count_str, city_raw in multi_na_pattern:
                    count = int(count_str) if count_str.isdigit() else 1
                    city_name = city_raw.strip()

                    # Normalize city name (handle Latin/Cyrillic mix)
                    city_norm = normalize_city_name(city_name)
                    city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)

                    # TRY 1: Regional override if oblast_hdr is set (e.g. "Харківщина:")
                    coords = None
                    if oblast_hdr and oblast_hdr in REGIONAL_CITY_COORDS:
                        region_coords = REGIONAL_CITY_COORDS[oblast_hdr]
                        coords = region_coords.get(city_norm)
                        if coords:
                            add_debug_log(f"  Multi-NA city: '{city_name}' ({count}x) -> norm: '{city_norm}' -> REGIONAL OVERRIDE coords: {coords} (oblast: {oblast_hdr})", "multi_na")

                    # TRY 2: Default database lookup if no regional override
                    if not coords:
                        coords = CITY_COORDS.get(city_norm)
                        if coords:
                            add_debug_log(f"  Multi-NA city: '{city_name}' ({count}x) -> norm: '{city_norm}' -> DATABASE coords: {coords}", "multi_na")

                    # TRY 3: Settlements index fallback
                    if not coords and SETTLEMENTS_INDEX:
                        coords = SETTLEMENTS_INDEX.get(city_norm)
                        if coords:
                            add_debug_log(f"  Multi-NA city: '{city_name}' ({count}x) -> norm: '{city_norm}' -> SETTLEMENTS coords: {coords}", "multi_na")

                    if not coords:
                        add_debug_log(f"  WARNING: No coordinates for '{city_name}' (normalized: '{city_norm}', oblast: {oblast_hdr})", "multi_na")
                        continue

                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(ln)

                        # Create separate markers for each count
                        for i in range(count):
                            place_label = city_norm.title()
                            if count > 1:
                                place_label += f" #{i+1}"

                            # Add offset for multiple drones at same location
                            marker_lat, marker_lng = lat, lng
                            if count > 1:
                                offset_distance = 0.03  # ~3km offset
                                marker_lat += offset_distance * i
                                marker_lng += offset_distance * i * 0.5

                            multi_city_tracks.append({
                                'id': f"{mid}_multi_na_{len(multi_city_tracks)+1}",
                                'place': place_label,
                                'lat': marker_lat,
                                'lng': marker_lng,
                                'threat_type': threat_type,
                                'text': clean_text(ln)[:500],
                                'date': date_str,
                                'channel': channel,
                                'marker_icon': icon,
                                'source_match': 'multi_na_pattern',
                                'count': 1
                            })
                        add_debug_log(f"  Created {count} marker(s) for '{city_norm.title()}'", "multi_na")
                    else:
                        add_debug_log(f"  WARNING: No coordinates for '{city_name}' (normalized: '{city_norm}')", "multi_na")

                add_debug_log(f"Multi-NA pattern processed: {len(multi_city_tracks)} total markers created", "multi_na")
                continue  # Skip further processing of this line

        # --- NEW: Simple "X БпЛА на <city>" pattern (e.g. '1 БпЛА на Козелець', '2 БпЛА на Куликівку') ---
        # Also handle "Ціль на <city>" pattern for missile/rocket targets
        if not city:
            print(f"DEBUG: Checking simple БпЛА/Ціль pattern for line: '{ln}'")

            # Pattern 1: "Ціль на <city>" - rocket/missile target
            m_target = re.search(r'ціль\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=\s|$|[,\.\!\?;\[])', ln, re.IGNORECASE)
            if m_target:
                city = m_target.group(1).strip()
                count = 1  # Default count for target
                print(f"DEBUG: Found 'Ціль на' pattern - city: '{city}'")
            # Pattern 2: "X БпЛА на <city>"
            elif re.search(r'(\d+)\s+бпла\s+на\s+', ln, re.IGNORECASE):
                m_simple = re.search(r'(\d+)\s+бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
                if m_simple:
                    try:
                        count = int(m_simple.group(1))
                    except Exception:
                        count = 1
                    city = m_simple.group(2).strip()
                    print(f"DEBUG: Found simple БпЛА pattern - count: {count}, city: '{city}'")
            # Pattern 3: "БпЛА на <city>" without count
            elif re.search(r'бпла\s+на\s+[A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,}', ln, re.IGNORECASE):
                # Fallback for "БпЛА на <city>" without count - handle cities with parentheses like "Кривий ріг (Дніпропетровщина)"
                m_simple_no_count = re.search(r'бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,}?)(?:\s*\([^)]*\))?(?=\s*$|[,\.\!\?;])', ln, re.IGNORECASE)
                if m_simple_no_count:
                    count = 1
                    city = m_simple_no_count.group(1).strip()
                    print(f"DEBUG: Found simple БпЛА pattern (no count) - city: '{city}'")
            # Pattern 4: "БПЛА <city> (область)" WITHOUT "на" - e.g. "БПЛА Кривий Ріг (Дніпропетровська обл.)"
            elif re.search(r'бпла\s+[A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,}?\s*\(', ln, re.IGNORECASE):
                m_city_oblast = re.search(r'бпла\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,}?)\s*\([^)]*(?:обл|область|щина)[^)]*\)', ln, re.IGNORECASE)
                if m_city_oblast:
                    count = 1
                    city = m_city_oblast.group(1).strip()
                    print(f"DEBUG: Found 'БПЛА City (oblast)' pattern - city: '{city}'")

        # --- NEW: Handle "X у напрямку City1, City2" pattern (e.g. "4 у напрямку Карлівки, Полтави") ---
        if not city:
            print(f"DEBUG: Checking 'X у напрямку' pattern for line: '{ln}'")
            m_naprymku = re.search(r'(\d+)\s+у\s+напрямку\s+([А-ЯІЇЄЁа-яіїєё\'\-\s,]{5,})(?=\s*$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_naprymku:
                try:
                    count = int(m_naprymku.group(1))
                except Exception:
                    count = 1
                cities_raw = m_naprymku.group(2).strip()
                print(f"DEBUG: Found 'у напрямку' pattern - count: {count}, cities: '{cities_raw}'")

                # Split cities by comma
                cities_list = [c.strip() for c in cities_raw.split(',') if c.strip()]
                for city_name in cities_list:
                    base = normalize_city_name(city_name)
                    base = UA_CITY_NORMALIZE.get(base, base)
                    coords = CITY_COORDS.get(base)

                    # If not found, try to handle declensions (ending with -и, -ми, -у, etc)
                    if not coords and base:
                        if base.endswith('і') or base.endswith('и'):
                            base_nom = base[:-1] + 'а'  # карлівки -> карлівка
                            coords = CITY_COORDS.get(base_nom)
                        elif base.endswith('у'):
                            base_nom = base[:-1] + 'а'  # полтаву -> полтава
                            coords = CITY_COORDS.get(base_nom)
                        elif base.endswith('ми'):
                            base_nom = base[:-2] + 'а'  # київми -> києва -> doesn't work, try other variants
                            coords = CITY_COORDS.get(base_nom)

                    if coords:
                        lat, lng = coords
                        multi_city_tracks.append({
                            'id': f"{mid}_naprymku{len(multi_city_tracks)+1}", 'place': city_name.title(), 'lat': lat, 'lng': lng,
                            'threat_type': 'shahed', 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': 'shahed3.webp', 'source_match': 'naprymku_pattern', 'count': count
                        })
                        print(f"DEBUG: Added marker for '{city_name}' at {lat}, {lng}")
                if multi_city_tracks:
                    continue

        # --- NEW: Handle "X БпЛА City1 / City2" pattern (e.g. "2х БпЛА Гнідин / Бориспіль") ---
        if not city:
            print(f"DEBUG: Checking БпЛА city/city pattern for line: '{ln}'")
            m_cities = re.search(r'(\d+)х?\s+бпла\s+(?:на\s+)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)\s*/\s*([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_cities:
                try:
                    count = int(m_cities.group(1))
                except Exception:
                    count = 1
                city1 = m_cities.group(2).strip()
                city2 = m_cities.group(3).strip()
                print(f"DEBUG: Found БпЛА city/city pattern - count: {count}, cities: '{city1}' / '{city2}'")

                # Process both cities separately
                for city_name in [city1, city2]:
                    base = normalize_city_name(city_name)
                    base = UA_CITY_NORMALIZE.get(base, base)
                    coords = CITY_COORDS.get(base)
                    if coords:
                        print(f"DEBUG: Creating БпЛА track for {city_name} at {coords}")
                        multi_city_tracks.append({
                            'lat': coords[0],
                            'lon': coords[1],
                            'name': city_name,
                            'type': 'БпЛА',
                            'time': date_str,
                            'id': mid,
                            'message': text[:100] + ('...' if len(text) > 100 else ''),
                            'channel': channel
                        })
                    else:
                        print(f"DEBUG: No coordinates found for {city_name} (base: {base})")

                # Set city to processed to prevent further processing
                city = f"{city1} / {city2}"
        # --- NEW: Handle "між X та Y" pattern (e.g. "між Корюківкою та Меною") ---
        if not city:
            m_between = re.search(r'між\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)\s+та\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_between:
                city1 = m_between.group(1).strip()
                city2 = m_between.group(2).strip()
                # Try to geocode both cities and place marker at midpoint
                base1 = normalize_city_name(city1)
                base2 = normalize_city_name(city2)
                base1 = UA_CITY_NORMALIZE.get(base1, base1)
                base2 = UA_CITY_NORMALIZE.get(base2, base2)

                coords1 = CITY_COORDS.get(base1) or (SETTLEMENTS_INDEX.get(base1) if SETTLEMENTS_INDEX else None)
                coords2 = CITY_COORDS.get(base2) or (SETTLEMENTS_INDEX.get(base2) if SETTLEMENTS_INDEX else None)

                if not coords1 and oblast_hdr:
                    combo1 = f"{base1} {oblast_hdr}"
                    coords1 = CITY_COORDS.get(combo1) or (SETTLEMENTS_INDEX.get(combo1) if SETTLEMENTS_INDEX else None)
                if not coords2 and oblast_hdr:
                    combo2 = f"{base2} {oblast_hdr}"
                    coords2 = CITY_COORDS.get(combo2) or (SETTLEMENTS_INDEX.get(combo2) if SETTLEMENTS_INDEX else None)

                if coords1 and coords2:
                    # Place marker at midpoint
                    lat = (coords1[0] + coords2[0]) / 2
                    lng = (coords1[1] + coords2[1]) / 2
                    label = f"Між {base1.title()} та {base2.title()}"
                    if oblast_hdr and oblast_hdr not in label.lower():
                        label += f" [{oblast_hdr.title()}]"

                    # Extract count from beginning of line if present
                    count_match = re.search(r'^(\d+(?:-\d+)?)\s*бпла', ln, re.IGNORECASE)
                    count = int(count_match.group(1)) if count_match else 1

                    multi_city_tracks.append({
                        'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                        'threat_type': 'shahed', 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': 'shahed3.webp', 'source_match': 'multiline_oblast_city_between', 'count': count
                    })
                    continue

        # --- NEW: Handle "неподалік X" pattern (e.g. "неподалік Ічні") ---
        if not city:
            m_near = re.search(r'неподалік\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_near:
                city = m_near.group(1).strip()
                # Extract count from beginning of line if present
                count_match = re.search(r'^(\d+(?:-\d+)?)\s*бпла', ln, re.IGNORECASE)
                count = int(count_match.group(1)) if count_match else 1

        # --- NEW: Handle "в районі X" pattern (e.g. "в районі Конотопу") ---
        if not city:
            m_area = re.search(r'в\s+районі\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,30}?)(?=\s|$|[,\.\!\?;])', ln, re.IGNORECASE)
            if m_area:
                city = m_area.group(1).strip()
                # Extract count from beginning of line if present
                count_match = re.search(r'^(\d+(?:-\d+)?)\s*бпла', ln, re.IGNORECASE)
                count = int(count_match.group(1)) if count_match else 1

        if city:
            print(f"DEBUG: Processing city '{city}' with oblast_hdr '{oblast_hdr}' and count {count}")
            base = normalize_city_name(city)
            print(f"DEBUG: Normalized city name: '{base}'")
            # Простейшая нормализация винительного падежа -> именительный ("велику димерку" -> "велика димерка")
            if base.endswith('у димерку') and 'велик' in base:
                base = 'велика димерка'
            # Общая морфология: заменяем окончания "ку"->"ка", "ю"->"я" для последнего слова
            if base.endswith('ку '):
                base = base[:-3] + 'ка '
            elif base.endswith('ку'):
                base = base[:-2] + 'ка'
            if base.endswith('ю '):
                base = base[:-3] + 'я '
            elif base.endswith('ю'):
                base = base[:-1] + 'я'
            # Приводим многословные формы через UA_CITY_NORMALIZE если есть
            base = UA_CITY_NORMALIZE.get(base, base)
            if base == 'троєщину':
                base = 'троєщина'

            # Use OpenCage geocoder with region context
            coords = ensure_city_coords(base, region=oblast_hdr, context=text)

            print(f"DEBUG: Enhanced lookup for '{base}'" + (f" in {oblast_hdr}" if oblast_hdr else "") + f": {coords}")

            if not coords and oblast_hdr:
                # Legacy combo lookup as fallback
                combo = f"{base} {oblast_hdr}"
                print(f"DEBUG: Trying legacy combo lookup for '{combo}'")
                coords = CITY_COORDS.get(combo)
                if not coords and SETTLEMENTS_INDEX:
                    coords = SETTLEMENTS_INDEX.get(combo)
                print(f"DEBUG: Combo lookup result: {coords}")
            if not coords:
                print(f"DEBUG: Calling ensure_city_coords_with_message_context for '{base}' with oblast context '{oblast_hdr}'")
                # Try with full message context first to get oblast-specific coordinates
                context_message = f"{oblast_hdr} {original_text if 'original_text' in locals() else text}"
                coords = ensure_city_coords_with_message_context(base, context_message)
                if not coords:
                    print(f"DEBUG: Context-based lookup failed, trying standard ensure_city_coords for '{base}'")
                    coords = ensure_city_coords(base, context=text)
                print(f"DEBUG: ensure_city_coords result: {coords}")
            if coords:
                print(f"DEBUG: Found coords {coords} for city '{base}', creating track")
                # Handle both 2-tuple (lat, lng) and 3-tuple (lat, lng, approx_flag) returns
                if len(coords) == 3:
                    lat, lng, approx_flag = coords
                else:
                    lat, lng = coords
                    approx_flag = False
                threat_type, icon = 'shahed', 'shahed3.webp'
                label = UA_CITY_NORMALIZE.get(base, base).title()
                if oblast_hdr and oblast_hdr not in label.lower():
                    label += f" [{oblast_hdr.title()}]"

                # Create multiple tracks for multiple drones instead of one track with count
                tracks_to_create = max(1, count)
                for i in range(tracks_to_create):
                    track_label = label
                    if tracks_to_create > 1:
                        track_label += f" #{i+1}"

                    # Add small coordinate offsets to prevent marker overlap
                    marker_lat = lat
                    marker_lng = lng
                    if tracks_to_create > 1:
                        # Create a chain pattern - drones one after another
                        offset_distance = 0.03  # ~3km offset between each drone
                        marker_lat += offset_distance * i
                        marker_lng += offset_distance * i * 0.5

                    print(f"DEBUG: Creating track {i+1}/{tracks_to_create} with label '{track_label}' at {marker_lat}, {marker_lng}")
                    multi_city_tracks.append({
                        'id': f"{mid}_mc{len(multi_city_tracks)+1}", 'place': track_label, 'lat': marker_lat, 'lng': marker_lng,
                        'threat_type': threat_type, 'text': clean_text(ln)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'multiline_oblast_city', 'count': 1
                    })
            else:
                print(f"DEBUG: No coordinates found for city '{base}'")
    print(f"DEBUG: Multi-city tracks processing complete. Found {len(multi_city_tracks)} tracks")
    add_debug_log(f"Multi-region processing complete: {len(multi_city_tracks)} markers from {processed_lines_count} lines", "multi_region")

    if multi_city_tracks:
        print(f"DEBUG: Returning {len(multi_city_tracks)} multi-city tracks")
        add_debug_log(f"Returning {len(multi_city_tracks)} multi-city tracks: {[t['place'] for t in multi_city_tracks]}", "multi_region")
        # Combine with priority result if available
        if 'priority_result' in locals() and priority_result:
            combined_result = priority_result + multi_city_tracks
            add_debug_log(f"Combined priority result ({len(priority_result)}) with multi-city tracks ({len(multi_city_tracks)}) = {len(combined_result)} total", "priority_combine")
            return combined_result
        return multi_city_tracks
    else:
        # If no multi-city tracks were created, continue with main parsing logic
        # This allows regional direction messages like "БпЛА на сході Сумщини" to be processed by regional parser
        add_debug_log("No multi-city tracks created, continuing to main parser", "multi_region_fallback")
    # --- Detect and split multiple city targets in one message ---
    import re
    multi_city_tracks = []
    # 1. Patterns: 'на <город>', 'повз <город>'
    # Захватываем одно- или многословные названия после "на" / "повз" до знака препинания / конца строки
    city_patterns = re.findall(r'(?:на|повз)\s+([A-Za-zА-Яа-яЇїІіЄєҐґʼ`’\-\s]{3,40}?)(?=[,\.\n;:!\?]|$)', text.lower())
    # 2. Patterns: перечисление через запятую или слэш (например: "шишаки, глобине, ромодан" или "малин/гранітне")
    # Только если в сообщении нет явного одного города в начале
    city_enumerations = []
    for part in re.split(r'[\n\|]', text.lower()):
        # ищем перечисления через запятую
        if ',' in part:
            city_enumerations += [c.strip() for c in part.split(',') if len(c.strip()) > 2]
        # ищем перечисления через слэш
        if '/' in part:
            city_enumerations += [c.strip() for c in part.split('/') if len(c.strip()) > 2]
    # Объединяем все найденные города
    all_cities = set(city_patterns + city_enumerations)
    # Фильтруем по наличию в CITY_COORDS (или SETTLEMENTS_INDEX)
    found_cities = []
    def _resolve_city_candidate(raw: str):
        cand = raw.strip().lower()
        cand = re.sub(r'["“”«»\(\)\[\]]','', cand)

        # CRITICAL: Remove trailing geographic qualifiers (e.g., "Канів по межі з Київщиною" → "Канів")
        trailing_patterns = [
            r'\s+по\s+межі\s+з\s+.*$',
            r'\s+на\s+межі\s+з\s+.*$',
            r'\s+в\s+районі\s+.*$',
            r'\s+біля\s+кордону\s+.*$',
            r'\s+на\s+околицях\s+.*$',
            r'\s+поблизу\s+.*$',
        ]
        for pattern in trailing_patterns:
            cand = re.sub(pattern, '', cand).strip()

        cand = re.sub(r'\s+',' ', cand)
        # Пробуем от длинного к короткому (до 3 слов достаточно для наших случаев)
        words = cand.split()
        if not words:
            return None
        for ln in range(min(3, len(words)), 0, -1):
            sub = ' '.join(words[:ln])
            base = UA_CITY_NORMALIZE.get(sub, sub)
            if base in CITY_COORDS or (SETTLEMENTS_INDEX and base in SETTLEMENTS_INDEX):
                return base
            # Морфология окончания винительного/родительного последнего слова
            sub_mod = re.sub(r'у\b','а', sub)
            sub_mod = re.sub(r'ю\b','я', sub_mod)
            sub_mod = re.sub(r'ої\b','а', sub_mod)
            base2 = UA_CITY_NORMALIZE.get(sub_mod, sub_mod)
            if base2 in CITY_COORDS or (SETTLEMENTS_INDEX and base2 in SETTLEMENTS_INDEX):
                return base2
        return UA_CITY_NORMALIZE.get(cand, cand)
    for city in all_cities:
        norm = _resolve_city_candidate(city)
        if not norm:
            continue
        coords = CITY_COORDS.get(norm)
        if not coords and SETTLEMENTS_INDEX:
            coords = SETTLEMENTS_INDEX.get(norm)
        if coords:
            found_cities.append((norm, coords))
    # Если найдено 2 и более города — создаём отдельный маркер для каждого
    if len(found_cities) >= 2:
        threat_type, icon = 'shahed', 'shahed3.webp'  # можно доработать auto-classify

        # Extract course information for Shahed threats
        course_info = None
        if threat_type == 'shahed':
            course_info = extract_shahed_course_info(original_text)

        for idx, (city, (lat, lng)) in enumerate(found_cities, 1):
            track = {
                'id': f"{mid}_mc{idx}", 'place': city.title(), 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': clean_text(original_text)[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'multi_city_auto'
            }

            # Add course information if available
            if course_info:
                track.update({
                    'course_source': course_info.get('source_city'),
                    'course_target': course_info.get('target_city'),
                    'course_direction': course_info.get('course_direction'),
                    'course_type': course_info.get('course_type')
                })

            multi_city_tracks.append(track)
        if multi_city_tracks:
            return multi_city_tracks
    """Extract coordinates or try simple city geocoding (lightweight)."""
    original_text = text
    # ---------------- Global region (oblast) hint detection for universal settlement binding ----------------
    region_hint_global = None
    try:
        low_rt = original_text.lower()
        for obl_name in OBLAST_CENTERS.keys():
            if obl_name in low_rt:
                region_hint_global = obl_name  # first hit
                break
    except Exception:
        region_hint_global = None
    # Additional: detect section headers like "Сумщина:" "Полтавщина:" at line starts to set region hint
    if not region_hint_global:
        for line in original_text.split('\n'):
            l = line.strip().lower()
            if l.endswith(':'):
                base = l[:-1]
                if base in OBLAST_CENTERS:
                    region_hint_global = base
                    break

    def region_enhanced_coords(base_name: str, region_hint_override: str = None):
        """Resolve coordinates for a settlement name by weighted order:
        0) FIRST: Local oblast-aware lookup (UKRAINE_SETTLEMENTS_BY_OBLAST) - MOST RELIABLE
        1) External geocode (region-qualified, then plain)
        2) Exact local datasets (CITY_COORDS, SETTLEMENTS_INDEX)
        3) Fuzzy approximate local match (Levenshtein-like via difflib)
        """
        if not base_name:
            return None
        name_norm = UA_CITY_NORMALIZE.get(base_name, base_name).strip().lower()
        
        # --- 0. PRIORITY: Local oblast-aware lookup (handles duplicate city names!) ---
        region_for_query = region_hint_override or region_hint_global
        if region_for_query and UKRAINE_SETTLEMENTS_BY_OBLAST:
            # Normalize region name to match database format
            region_norm = region_for_query.lower().strip()
            # Map regional names to adjective forms
            region_to_adj = {
                'харківщина': 'харківська', 'сумщина': 'сумська', 'полтавщина': 'полтавська',
                'чернігівщина': 'чернігівська', 'київщина': 'київська', 'одещина': 'одеська',
                'миколаївщина': 'миколаївська', 'херсонщина': 'херсонська', 'запорізька': 'запорізька',
                'дніпропетровщина': 'дніпропетровська', 'донецька': 'донецька', 'луганська': 'луганська',
                'черкащина': 'черкаська', 'вінниччина': 'вінницька', 'житомирщина': 'житомирська',
                'рівненщина': 'рівненська', 'волинь': 'волинська', 'львівщина': 'львівська',
                'тернопільщина': 'тернопільська', 'хмельниччина': 'хмельницька',
                'івано-франківщина': 'івано-франківська', 'закарпаття': 'закарпатська',
                'чернівецька': 'чернівецька', 'кіровоградщина': 'кіровоградська',
            }
            if region_norm in region_to_adj:
                region_norm = region_to_adj[region_norm]
            
            # Try looking up (city, oblast) tuple
            lookup_key = (name_norm, region_norm)
            if lookup_key in UKRAINE_SETTLEMENTS_BY_OBLAST:
                coords = UKRAINE_SETTLEMENTS_BY_OBLAST[lookup_key]
                log.info(f"region_enhanced_coords: Found '{name_norm}' in '{region_norm}' oblast: {coords}")
                return coords
        
        # --- 1. Remote geocode ---
        if region_for_query:
            canon = REGION_GEOCODE_CANON.get(region_for_query)
            if canon:
                region_for_query = canon
        # Region-qualified
        if OPENCAGE_API_KEY and region_for_query:
            try:
                combo = f"{name_norm} {region_for_query}".replace('  ', ' ').strip()
                c = geocode_opencage(combo)
                if c and 43.0 <= c[0] <= 53.8 and 20.0 <= c[1] <= 42.0:
                    return c
            except Exception:
                pass
        # Plain name remote
        if OPENCAGE_API_KEY:
            try:
                c = geocode_opencage(name_norm)
                if c and 43.0 <= c[0] <= 53.8 and 20.0 <= c[1] <= 42.0:
                    return c
            except Exception:
                pass
        # --- 2. Exact local datasets ---
        coord = CITY_COORDS.get(name_norm)
        if not coord and SETTLEMENTS_INDEX:
            coord = SETTLEMENTS_INDEX.get(name_norm)
        # Explicit settlement fallback (manual corrections for mis-geocoded small places)
        if not coord:
            coord = SETTLEMENT_FALLBACK.get(name_norm)
        if coord:
            return coord
        # --- 3. Fuzzy approximate search (only if not found) ---
        try:
            if SETTLEMENTS_INDEX:
                import difflib
                # Choose candidate list limited for performance
                names = list(SETTLEMENTS_INDEX.keys())
                # High cutoff to avoid bad matches
                best = difflib.get_close_matches(name_norm, names, n=1, cutoff=0.86)
                if best:
                    b = best[0]
                    return SETTLEMENTS_INDEX.get(b)
        except Exception:
            pass
        return None
    # ---- Fundraising / donation solicitation handling ----
    # Previous behavior: fully suppressed entire message if donation links found (blocked napramok multi-line threat posts with footer links)
    # New behavior: If donation lines present BUT the message also contains threat indicators, strip only the donation lines and continue parsing.
    low_full = original_text.lower()
    DONATION_KEYS = [
        'монобанк','monobank','mono.bank','privat24','приват24','реквізит','реквизит','донат','donat','iban','paypal','patreon','send.monobank.ua','jar/','банка: http','карта(','карта(monobank)','карта(privat24)','підтримати канал'
    ]
    donation_present = any(k in low_full for k in DONATION_KEYS) or re.search(r'\b\d{16}\b', low_full)
    # Pure subscription / invite promo suppression (no threats, mostly t.me invite links + short call to action)
    if not any(w in low_full for w in ['бпла','дрон','шахед','shahed','ракета','каб','артил','града','смерч','ураган','mlrs','iskander','s-300','s300','border','trivoga','тривога','повітряна тривога']) and \
       low_full.count('t.me/') >= 1 and len(re.sub(r'\s+',' ', low_full)) < 260 and \
       len([ln for ln in low_full.splitlines() if ln.strip()]) <= 6:
        if all(tok not in low_full for tok in ['загроза','укритт','alert','launch','start','вильот','вихід','пуски','air','strike']):
            return None
    if donation_present:
        # Threat keyword heuristic (lightweight; don't rely on later THREAT_KEYS definition yet)
        threat_tokens = ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile','iskander','s-300','s300','каб','артил','града','смерч','ураган','mlrs']
        has_threat_word = any(tok in low_full for tok in threat_tokens)
        if has_threat_word:
            # НЕ удаляем строки с донатами если есть угрозы - просто продолжаем парсинг
            log.debug(f"mid={mid} donation_present but has_threats - continuing without stripping")
            # text остается без изменений
        else:
            return [{
                'id': str(mid), 'place': None, 'lat': None, 'lng': None,
                'threat_type': None, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'list_only': True, 'suppress': True, 'suppress_reason': 'donation_only'
            }]
    # --- Universal link stripping (any clickable invite / http) ---
    def _strip_links(s: str) -> str:
        if not s:
            return s
        # markdown links [text](url)
        # handle bold inside brackets [**Text**](url) by stripping ** first
        s = re.sub(r'\*\*','', s)
        s = re.sub(r'\[([^\]]{0,80})\]\((https?://|t\.me/)[^\)]+\)', lambda m: (m.group(1) or '').strip(), s, flags=re.IGNORECASE)
        # bare urls
        s = re.sub(r'(https?://\S+|t\.me/\S+)', '', s, flags=re.IGNORECASE)
        # collapse whitespace and drop empty lines
        cleaned = []
        for ln in s.splitlines():
            ln2 = ln.strip()
            if not ln2:
                continue
            # pure decoration (arrows, bullets) or subscribe call to action lines
            if re.fullmatch(r'[>➡→\-\s·•]*', ln2):
                continue
            # remove any line that is just a subscribe CTA or starts with arrow+subscribe
            if re.search(r'(підписатись|підписатися|підписатися|подписаться|подпишись|subscribe)', ln2, re.IGNORECASE):
                continue
            # remove arrow+subscribe pattern specifically
            if re.search(r'[➡→>]\s*підписатися', ln2, re.IGNORECASE):
                continue
            cleaned.append(ln2)
        return '\n'.join(cleaned)
    new_text = _strip_links(text)
    if new_text != text:
        text = new_text
    new_orig = _strip_links(original_text)
    if new_orig != original_text:
        original_text = new_orig
    # --- Explicit launch site detection (multi-line). Create one marker per detected launch location.
    low_work = text.lower()
    # --- Single-line explicit RF launch: "пуск <place> (рф)" ---
    if 'пуск' in low_work and 'рф' in low_work:
        try:
            m = re.search(r'пуск(?:и)?\s+([A-Za-zА-Яа-яЇїІіЄєҐґ0-9\-–—\s]{2,60})', low_work)
            if m:
                raw_place = m.group(1)
                raw_place = raw_place.split('(')[0].split(',')[0].strip()
                raw_place = raw_place.replace('–', '-').replace('—', '-')
                raw_place = raw_place.replace('ё', 'е')
                raw_place = re.sub(r'\bрф\b', '', raw_place).strip()
                raw_place = re.sub(r'\bрайон(у|а)?\b', '', raw_place).strip()
                raw_place = re.sub(r'\bр-н\b', '', raw_place).strip()
                raw_place = re.sub(r'\s+', ' ', raw_place)
                
                # Фільтр неправильних/жартівливих локацій, областей РФ та напрямків
                invalid_locations = [
                    'пусківка', 'пуськівка', 'хуйовка', 'залупинськ',
                    # Області РФ (не конкретні аеродроми)
                    'курщини', 'курщина', 'воронежу', 'воронежа', 'воронеж',
                    'бєлгородщини', 'білгородщини', 'брянщини',
                    # Напрямки (не місця)
                    'північ', 'південь', 'схід', 'захід', 
                    'північного сходу', 'північного заходу', 'південного сходу', 'південного заходу',
                    'північні', 'південні', 'східні', 'західні',
                    'та', 'і', 'або'  # Сполучники які залишаються після парсингу
                ]
                if any(inv in raw_place.lower() for inv in invalid_locations):
                    return []
                
                # Також пропускаємо якщо в назві тільки напрямки без конкретного міста
                direction_only = ['північ', 'південь', 'схід', 'захід', 'та', 'і']
                words = raw_place.lower().split()
                if all(any(d in word for d in direction_only) for word in words):
                    return []
                
                variants = {
                    raw_place,
                    raw_place.replace(' ', '-'),
                    raw_place.replace('-', ' '),
                }
                if raw_place.endswith('ова'):
                    variants.add(raw_place[:-3] + 'ово')
                if raw_place.endswith('ева'):
                    variants.add(raw_place[:-3] + 'ево')
                # Simple case normalization for RF launch sites (genitive -> nominative)
                case_variants = set()
                for v in list(variants):
                    parts = v.split()
                    if not parts:
                        continue
                    last = parts[-1]
                    candidates = set()
                    if last.endswith(('и', 'ы', 'і')) and len(last) > 2:
                        candidates.add(last[:-1] + 'а')
                    if last.endswith('ої') and len(last) > 3:
                        candidates.add(last[:-2] + 'а')
                        candidates.add(last[:-2] + 'е')
                    if last.endswith('ю') and len(last) > 2:
                        candidates.add(last[:-1] + 'а')
                    for cand in candidates:
                        new_name = ' '.join(parts[:-1] + [cand]).strip()
                        if new_name in LAUNCH_SITES:
                            case_variants.add(new_name)
                variants |= case_variants
                coord = None
                chosen = None
                for v in variants:
                    key = v.strip()
                    if key in LAUNCH_SITES:
                        coord = LAUNCH_SITES[key]
                        chosen = key
                        break
                if not coord:
                    coord = _geocode_rf_place(raw_place)
                if coord:
                    lat, lng = coord
                    return [{
                        'id': f"{mid}_pusk_rf",
                        'place': (chosen or raw_place).title(),
                        'lat': lat,
                        'lng': lng,
                        'threat_type': 'pusk',
                        'text': original_text[:500],
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': 'pusk.png',
                        'source_match': 'launch_site_rf'
                    }]
        except Exception:
            pass
    if ('пуск' in low_work or 'пуски' in low_work or '+ пуски' in low_work):
        # find quoted or dash-separated site tokens: «Name», "Name", or after 'з ' preposition
        sites_found = set()
        # Quoted tokens
        for m in re.findall(r'«([^»]{2,40})»', text):
            sites_found.add(m.strip().lower())
        for m in re.findall(r'"([^"\n]{2,40})"', text):
            sites_found.add(m.strip().lower())
        # Phrases after 'з ' (from) up to comma
        for m in re.findall(r'з\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{2,40})', low_work):
            sites_found.add(m.strip().lower())
        # tokens after 'аеродрому' or 'аэродрома' inside quotes
        for m in re.findall(r'аеродром[ау]\s+«([^»]{2,40})»', low_work):
            sites_found.add(m.strip().lower())
        for m in re.findall(r'аэродром[ау]\s+«([^»]{2,40})»', low_work):
            sites_found.add(m.strip().lower())
        tracks = []
        threat_type = 'pusk'
        icon = 'pusk.png'
        idx = 0
        for raw_site in sites_found:
            norm_key = raw_site.replace(' — ','-').replace(' – ','-').replace('—','-').replace('–','-')
            norm_key = norm_key.replace('  ',' ').strip()
            base_variants = [norm_key, norm_key.replace('полігон ','').replace('полигон ','')]
            coord = None
            chosen_name = raw_site
            for bv in base_variants:
                if bv in LAUNCH_SITES:
                    coord = LAUNCH_SITES[bv]
                    chosen_name = bv
                    break
            if not coord:
                continue
            idx += 1
            lat,lng = coord
            tracks.append({
                'id': f"{mid}_l{idx}", 'place': chosen_name.title(), 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'launch_site'
            })
        if tracks:
            return tracks
    # ---- Daily / periodic situation summary ("ситуація станом на HH:MM" + sectional bullets) ----
    # User request: do NOT create map markers for such aggregated status reports.
    # Heuristics: phrase "ситуація станом" (uk) or "ситуация на" (ru), OR presence of 2+ bullet headers like "• авіація", "• бпла", "• флот" in same message.
    bullet_headers = 0
    for hdr in ['• авіація', '• авиа', '• бпла', '• дро', '• флот', '• кораб', '• ракети', '• ракеты']:
        if hdr in low_full:
            bullet_headers += 1
    if re.search(r'ситуац[ія][яi]\s+станом', low_full) or re.search(r'ситуац[ия]\s+на\s+\d{1,2}:\d{2}', low_full) or bullet_headers >= 2:
        # User clarified: completely skip (no site display at all)
        return [{
            'id': str(mid), 'place': None, 'lat': None, 'lng': None,
            'threat_type': None, 'text': original_text[:800], 'date': date_str, 'channel': channel,
            'list_only': True, 'summary': True, 'suppress': True
        }]
    # ---- Imprecise directional-only messages (no exact city location) suppression ----
    # User request: messages that only state relative / directional movement without a clear city position
    # Examples: "групи ... рухаються північніше X у напрямку Y"; "... курс західний (місто)"; region-only with direction
    # Allow cases with explicit target form "курс на <city>" (precise intent) or patterns we already map like 'повз <city>' or multi-city slash/comma lists.
    def _has_threat_local(txt: str):
        l = txt.lower()
        return any(k in l for k in ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile'])
    lower_all = original_text.lower()
    if _has_threat_local(lower_all):
        directional_course = 'курс' in lower_all and any(w in lower_all for w in ['північ','півден','схід','захід']) and not re.search(r'курс(?:ом)?\s+на\s+[A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,}', lower_all)
        relative_dir_tokens = any(tok in lower_all for tok in ['північніше','південніше','східніше','західніше'])
        # Multi-city list heuristic (comma or slash separated multiple city tokens at start)
        multi_city_pattern = r"^[^\n]{0,120}?([A-Za-zА-Яа-яЇїІіЄєҐґ'`’ʼ\-]{3,}\s*,\s*){1,}[A-Za-zА-Яа-яЇїІіЄєҐґ'`’ʼ\-]{3,}"
        multi_city_enumeration = bool(re.match(multi_city_pattern, lower_all)) or ('/' in lower_all)
        has_pass_near = 'повз ' in lower_all
        if (directional_course or relative_dir_tokens) and not has_pass_near and not multi_city_enumeration:
            return [{
                'id': str(mid), 'place': None, 'lat': None, 'lng': None,
                'threat_type': None, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'list_only': True, 'suppress': True, 'suppress_reason': 'imprecise_direction_only'
            }]
    # Не удаляем полностью "Повітряна тривога" теперь: нужно показывать в списке событий.
    # Сохраняем текст как есть для event list.
    # Убираем markdown * _ ` и базовые эмодзи-иконки в начале строк
    text = re.sub(r'[\*`_]+', '', text)
    # Удаляем ведущие эмодзи/иконки перед словами
    text = re.sub(r'^[\W_]+', '', text)
    # Общий набор ключевых слов угроз
    THREAT_KEYS = ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile','iskander','s-300','s300','каб','артил','града','смерч','ураган','mlrs','avia','авіа','авиа','бомба','високошвидкісн']
    def has_threat(txt: str):
        l = txt.lower()
        return any(k in l for k in THREAT_KEYS)

    # PRIORITY: Structured messages with regional headers (e.g., "Область:\n city details")
    if not _disable_multiline and has_threat(original_text):
        import re as _struct_re
        # Look for pattern: "RegionName:\n threats with cities"
        region_header_pattern = r'^([А-Яа-яЇїІіЄєҐґ]+щина):\s*$'
        text_lines = original_text.split('\n')

        structured_sections = []
        current_region = None
        current_threats = []

        for line in text_lines:
            line = line.strip()
            if not line or 'підписатися' in line.lower():
                continue

            # Check if line is a region header
            region_match = _struct_re.match(region_header_pattern, line)
            if region_match:
                # Save previous section
                if current_region and current_threats:
                    structured_sections.append((current_region, current_threats))
                # Start new section
                current_region = region_match.group(1)
                current_threats = []
            elif current_region and ('шахед' in line.lower() or 'бпла' in line.lower()):
                # This is a threat line under current region
                current_threats.append(line)

        # Don't forget last section
        if current_region and current_threats:
            structured_sections.append((current_region, current_threats))

        # Process structured sections if we found any
        if len(structured_sections) >= 2:
            add_debug_log(f"STRUCTURED REGIONS: Found {len(structured_sections)} regions with threats", "structured_regions")

            all_structured_tracks = []
            for region_name, threat_lines in structured_sections:
                add_debug_log(f"Processing region {region_name} with {len(threat_lines)} threats", "structured_region_detail")

                for threat_line in threat_lines:
                    # Process each threat line with region context
                    region_context_text = f"{region_name}:\n{threat_line}"
                    line_tracks = process_message(region_context_text, f"{mid}_{region_name}_{len(all_structured_tracks)}",
                                                date_str, channel, _disable_multiline=True)
                    if line_tracks:
                        all_structured_tracks.extend(line_tracks)
                        add_debug_log(f"Region {region_name} threat '{threat_line[:50]}...' produced {len(line_tracks)} tracks", "structured_threat_result")

            if all_structured_tracks:
                add_debug_log(f"Structured processing complete: {len(all_structured_tracks)} total tracks", "structured_complete")
                return all_structured_tracks

    # NEW: Handle UAV messages with "через [city]" and "повз [city]" patterns - BEFORE trajectory_phrase
    try:
        lorig = text.lower()
        if 'бпла' in lorig and ('через' in lorig or 'повз' in lorig):
            threats = []

            # Extract cities from "через [city1], [city2]" pattern
            import re as _re_route
            route_pattern = r'через\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*\.\s+|$)'
            route_matches = _re_route.findall(route_pattern, text, re.IGNORECASE)

            for route_match in route_matches:
                # Split by comma to get individual cities
                cities_raw = [c.strip() for c in route_match.split(',') if c.strip()]

                for city_raw in cities_raw:
                    city_clean = city_raw.strip().strip('.,')
                    city_norm = clean_text(city_clean).lower()

                    # Apply normalization rules
                    if city_norm in UA_CITY_NORMALIZE:
                        city_norm = UA_CITY_NORMALIZE[city_norm]

                    # Try to get coordinates
                    coords = region_enhanced_coords(city_norm)
                    if not coords:
                        coords = ensure_city_coords(city_norm, context=text)

                    if coords:
                        # Handle different coordinate formats
                        if isinstance(coords, tuple) and len(coords) >= 2:
                            lat, lng = coords[0], coords[1]
                        else:
                            continue

                        threat_type, icon = classify(text)

                        # Extract count from text context (look for patterns like "15х БпЛА через")
                        count = 1
                        count_match = _re_route.search(rf'(\d+)[xх×]?\s*бпла.*?через.*?{re.escape(city_clean)}', text, re.IGNORECASE)
                        if count_match:
                            count = int(count_match.group(1))

                        threats.append({
                            'id': f"{mid}_route_{len(threats)}",
                            'place': city_clean.title(),
                            'lat': lat,
                            'lng': lng,
                            'threat_type': threat_type,
                            'text': f"Через {city_clean.title()} (з повідомлення про маршрут)",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': f'route_via_{count}x',
                            'count': count
                        })

                        add_debug_log(f"Route via: {city_clean} ({count}x) -> {coords}", "route_via")

            # Extract cities from "повз [city]" pattern
            past_pattern = r'повз\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*\.\s*|$)'
            past_matches = _re_route.findall(past_pattern, text, re.IGNORECASE)

            for past_match in past_matches:
                city_clean = past_match.strip().strip('.,')
                city_norm = clean_text(city_clean).lower()

                # Apply normalization rules
                if city_norm in UA_CITY_NORMALIZE:
                    city_norm = UA_CITY_NORMALIZE[city_norm]

                # Try to get coordinates
                coords = region_enhanced_coords(city_norm)
                if not coords:
                    coords = ensure_city_coords_with_message_context(city_norm, text)

                # Fallback: try accusative case normalization (e.g., "олександрію" -> "олександрія")
                if not coords and city_norm.endswith('ію'):
                    accusative_fallback = city_norm[:-2] + 'ія'
                    coords = region_enhanced_coords(accusative_fallback)
                    if not coords:
                        coords = ensure_city_coords_with_message_context(accusative_fallback, text)
                    if coords:
                        city_norm = accusative_fallback
                        city_clean = accusative_fallback.title()  # Use normalized name for display

                if coords:
                    # Handle different coordinate formats
                        if isinstance(coords, tuple) and len(coords) >= 2:
                            lat, lng = coords[0], coords[1]
                        else:
                            continue

                        threat_type, icon = classify(text)

                        # Extract count from text context (look for patterns like "4х БпЛА повз")
                        count = 1
                        count_match = _re_route.search(rf'(\d+)[xх×]?\s*бпла.*?повз.*?{re.escape(city_clean)}', text, re.IGNORECASE)
                        if count_match:
                            count = int(count_match.group(1))

                        threats.append({
                            'id': f"{mid}_past_{len(threats)}",
                            'place': city_clean.title(),
                            'lat': lat,
                            'lng': lng,
                            'threat_type': threat_type,
                            'text': f"Повз {city_clean.title()} (з повідомлення про маршрут)",
                            'date': date_str,
                            'channel': channel,
                            'marker_icon': icon,
                            'source_match': f'route_past_{count}x',
                            'count': count
                        })

                        add_debug_log(f"Route past: {city_clean} ({count}x) -> {coords}", "route_past")

            if threats:
                return threats
            else:
                pass

    except Exception:
        pass

    # --- Trajectory phrase pattern: "з дніпропетровщини через харківщину у напрямку полтавщини" ---
    # We map region stems to canonical OBLAST_CENTERS keys (simplistic stem matching).
    lower_full = text.lower()
    if has_threat(lower_full) and ' через ' in lower_full and (' у напрямку ' in lower_full or ' напрямку ' in lower_full or ' в напрямку ' in lower_full):
        # Extract sequence tokens after prepositions з/із/від -> start, через -> middle(s), напрямку -> target
        # Very heuristic; splits by key words.
        try:
            norm = re.sub(r'\s+', ' ', lower_full)
            norm = norm.replace('із ', 'з ').replace('від ', 'з ')
            if ' через ' in norm:
                front, after = norm.split(' через ', 1)
                start_token = front.split(' з ')[-1].strip()
                target_part = None; mid_part = ''
                for marker in [' у напрямку ', ' в напрямку ', ' напрямку ']:
                    if marker in after:
                        mid_part, target_part = after.split(marker, 1)
                        break
                if target_part:
                    mid_token = mid_part.strip().split('.')[0]
                    target_token = target_part.strip().split('.')[0]
                    def region_center(token: str):
                        token = token.strip()
                        for k,(lat,lng) in OBLAST_CENTERS.items():
                            if token.startswith(k.split()[0][:6]) or token in k:
                                return (k,(lat,lng))
                        return None
                    seq = []
                    for tk in [start_token, mid_token, target_token]:
                        rc = region_center(tk)
                        if rc and (not seq or seq[-1][0] != rc[0]):
                            seq.append(rc)
                    if len(seq) >= 2:
                        threat_type, icon = classify(text)
                        tracks = []
                        for idx,(name,(lat,lng)) in enumerate(seq,1):
                            base = name.split()[0].title()
                            tracks.append({
                                'id': f"{mid}_t{idx}", 'place': base, 'lat': lat, 'lng': lng,
                                'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                                'marker_icon': icon, 'source_match': 'trajectory_phrase'
                            })
                        return tracks
        except Exception:
            pass
    # direct coordinates pattern
    # --- Direction with parenthetical specific settlement e.g. "у напрямку білгород-дністровського району одещини (затока)" ---
    if has_threat(lower_full) and 'у напрямку' in lower_full and '(' in lower_full and ')' in lower_full:
        # capture last parenthetical token (short) that is a known settlement
        try:
            paren_tokens = re.findall(r'\(([a-zа-яіїєґ\-\s]{3,})\)', lower_full)
            if paren_tokens:
                candidate = paren_tokens[-1].strip().lower()
                # trim descriptors like 'смт ' , 'с.' etc
                candidate = re.sub(r'^(смт|с\.|м\.|місто|селище)\s+','', candidate)
                norm = UA_CITY_NORMALIZE.get(candidate, candidate)
                coords = CITY_COORDS.get(norm)
                if not coords and SETTLEMENTS_INDEX:
                    coords = SETTLEMENTS_INDEX.get(norm)
                if not coords:
                    coords = SETTLEMENT_FALLBACK.get(norm)
                log.debug(f"parenthetical_dir detect mid={mid} candidate={candidate} norm={norm} found={bool(coords)}")
                if coords:
                    lat,lng = coords
                    threat_type, icon = classify(text)
                    return [{
                        'id': f"{mid}_dirp", 'place': norm.title(), 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'direction_parenthetical'
                    }]
        except Exception:
            pass
    # --- Region-level shelling threat (e.g. "Харківська обл. Загроза обстрілу прикордонних територій") ---
    try:
        if re.search(r'(загроза обстрілу|угроза обстрела)', lower_full):
            # attempt to match any oblast token present
            region_hit = None
            for reg_key in OBLAST_CENTERS.keys():
                if reg_key in lower_full:
                    region_hit = reg_key
                    log.debug(f"region_shelling candidate mid={mid} match={reg_key}")
                    break
            if region_hit:
                # Only emit if we haven't already returned a more specific structure earlier (heuristic: continue)
                lat, lng = OBLAST_CENTERS[region_hit]
                threat_type, icon = classify(text)
                # Enforce obstril icon for shelling phrasing even if classify changed in future
                if re.search(r'(загроза обстрілу|угроза обстрела|обстріл|обстрел)', lower_full):
                    threat_type = 'artillery'; icon = 'obstril.png'
                border_shell = bool(re.search(r'прикордон|пригранич', lower_full))
                place_label = region_hit
                if border_shell:
                    place_label += ' (прикордоння)'
                log.debug(f"region_shelling emit mid={mid} region={region_hit} border={border_shell}")
                return [{
                    'id': f"{mid}_region_shell", 'place': place_label, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'region_shelling', 'border_shelling': border_shell
                }]
    except Exception:
        pass
    # Special handling for KAB threats with regional mentions (e.g., "Загроза КАБ для прифронтових громад Сумщини")
    kab_region_match = re.search(r'(каб|авіабомб|авиабомб|авіаційних.*бомб|керован.*бомб)[^\.]*?(сумщин[иіа]|харківщин[иіа]|чернігівщин[иіа]|полтавщин[иіа])', text.lower())
    if kab_region_match:
        region_mention = kab_region_match.group(2)
        # Convert genitive/dative to nominative
        if 'сумщин' in region_mention:
            region_key = 'сумщина'
        elif 'харківщин' in region_mention:
            region_key = 'харківщина'
        elif 'чернігівщин' in region_mention:
            region_key = 'чернігівщина'
        elif 'полтавщин' in region_mention:
            region_key = 'полтавщина'
        else:
            region_key = None

        if region_key and region_key in OBLAST_CENTERS:
            lat, lng = OBLAST_CENTERS[region_key]
            # For KAB threats, offset coordinates slightly from city center to avoid implying direct city impact
            if region_key == 'сумщина':
                lat += 0.1  # Move north of Sumy city
                lng -= 0.1  # Move west of Sumy city
            elif region_key == 'харківщина':
                lat += 0.1  # Move north of Kharkiv city
                lng -= 0.1  # Move west of Kharkiv city
            add_debug_log(f"Creating KAB regional threat marker for {region_key}: lat={lat}, lng={lng}", "kab_regional")
            return [{
                'id': f"{mid}_kab_regional", 'place': region_key.title(), 'lat': lat, 'lng': lng,
                'threat_type': 'raketa', 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'icon_balistic.svg', 'source_match': 'kab_regional_threat'
            }]

    # SPECIAL: Handle multi-regional UAV messages (like the user's example)
    def handle_multi_regional_uav():
        """Handle messages with multiple regional UAV threats listed separately"""
        threats = []
        text_lines = text.split('\n')

        # Check if this looks like a multi-regional UAV message
        region_count = 0
        uav_count = 0
        for line in text_lines:
            line_lower = line.lower().strip()
            if not line_lower:
                continue

            # Count regions mentioned
            if any(region in line_lower for region in ['щина:', 'область:', 'край:']):
                region_count += 1

            # Count UAV mentions
            if 'бпла' in line_lower and ('курс' in line_lower or 'на ' in line_lower):
                uav_count += 1

        # If we have multiple regions and multiple UAV mentions, process each line
        if region_count >= 2 and uav_count >= 3:
            add_debug_log(f"MULTI-REGIONAL UAV MESSAGE: {region_count} regions, {uav_count} UAVs", "multi_regional")

            for line in text_lines:
                line_stripped = line.strip()
                if not line_stripped or ':' in line_stripped[:20]:  # Skip region headers
                    continue

                line_lower = line_stripped.lower()

                # Look for UAV course patterns
                if 'бпла' in line_lower and ('курс' in line_lower or ' на ' in line_lower):
                    # Extract city name from patterns like "БпЛА курсом на Конотоп" or "2х БпЛА курсом на Велику Димерку"
                    patterns = [
                        r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|])',
                        r'бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|])',
                        r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|])'
                    ]

                    for pattern in patterns:
                        matches = re.finditer(pattern, line_stripped, re.IGNORECASE)
                        for match in matches:
                            if len(match.groups()) == 2:
                                count_str, city_raw = match.groups()
                            else:
                                count_str = None
                                city_raw = match.group(1)

                            if not city_raw:
                                continue

                            # Clean and normalize city name
                            city_clean = city_raw.strip()
                            city_norm = clean_text(city_clean).lower()

                            # Apply normalization rules
                            if city_norm in UA_CITY_NORMALIZE:
                                city_norm = UA_CITY_NORMALIZE[city_norm]

                            # Try to get coordinates
                            coords = region_enhanced_coords(city_norm)
                            if not coords:
                                coords = ensure_city_coords(city_norm, context=text)

                            if coords:
                                lat, lng = coords
                                threat_type, icon = classify(text)

                                # Extract count if present
                                uav_count_num = 1
                                if count_str and count_str.isdigit():
                                    uav_count_num = int(count_str)

                                threat_id = f"{mid}_multi_{len(threats)}"
                                threats.append({
                                    'id': threat_id,
                                    'place': city_clean.title(),
                                    'lat': lat,
                                    'lng': lng,
                                    'threat_type': threat_type,
                                    'text': f"{line_stripped} (з багаторегіонального повідомлення)",
                                    'date': date_str,
                                    'channel': channel,
                                    'marker_icon': icon,
                                    'source_match': f'multi_regional_uav_{uav_count_num}x',
                                    'count': uav_count_num
                                })

                                add_debug_log(f"Multi-regional UAV: {city_clean} ({uav_count_num}x) -> {coords}", "multi_regional")
                            else:
                                add_debug_log(f"Multi-regional UAV: No coords for {city_clean}", "multi_regional")

        return threats

    # SPECIAL: Handle single UAV course mentions in regular messages
    def handle_single_uav_courses():
        """Handle UAV course mentions like '4х БпЛА курсом на Добротвір' in regular alert messages"""
        threats = []

        # Look for UAV course patterns in the entire message
        patterns = [
            r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|\(])',
            r'бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|\(])',
            r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s*$|\s*[,\.\!\?\|\(])'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:
                    count_str, city_raw = match.groups()
                else:
                    count_str = None
                    city_raw = match.group(1)

                if not city_raw:
                    continue

                # Clean and normalize city name
                city_clean = city_raw.strip()
                city_norm = clean_text(city_clean).lower()

                # Apply normalization rules
                if city_norm in UA_CITY_NORMALIZE:
                    city_norm = UA_CITY_NORMALIZE[city_norm]

                # Try to get coordinates
                coords = region_enhanced_coords(city_norm)
                if not coords:
                    coords = ensure_city_coords(city_norm, context=text)

                if coords:
                    lat, lng = coords[:2]
                    threat_type, icon = classify(text)

                    # Extract count if present
                    uav_count_num = 1
                    if count_str and count_str.isdigit():
                        uav_count_num = int(count_str)

                    threat_id = f"{mid}_uav_course_{len(threats)}"
                    threats.append({
                        'id': threat_id,
                        'place': city_clean.title(),
                        'lat': lat,
                        'lng': lng,
                        'threat_type': threat_type,
                        'text': f"БпЛА курсом на {city_clean} ({uav_count_num}x)",
                        'date': date_str,
                        'channel': channel,
                        'marker_icon': icon,
                        'source_match': f'single_uav_course_{uav_count_num}x',
                        'count': uav_count_num
                    })

                    add_debug_log(f"Single UAV course: {city_clean} ({uav_count_num}x) -> {coords}", "single_uav")
                else:
                    add_debug_log(f"Single UAV course: No coords for {city_clean}", "single_uav")

        # ALSO: Extract cities from emoji structure in the same text
        # Pattern for "| 🛸 Город (Область)"
        emoji_pattern = r'\|\s*🛸\s*([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)\s*\([^)]*обл[^)]*\)'
        emoji_matches = re.finditer(emoji_pattern, text, re.IGNORECASE)

        for match in emoji_matches:
            city_raw = match.group(1).strip()
            if not city_raw or len(city_raw) < 2:
                continue

            city_norm = clean_text(city_raw).lower()
            if city_norm in UA_CITY_NORMALIZE:
                city_norm = UA_CITY_NORMALIZE[city_norm]

            coords = region_enhanced_coords(city_norm)
            if not coords:
                coords = ensure_city_coords(city_norm, context=text)

            if coords:
                lat, lng = coords[:2]
                threat_type, icon = classify(text)

                threat_id = f"{mid}_emoji_struct_{len(threats)}"
                threats.append({
                    'id': threat_id,
                    'place': city_raw.title(),
                    'lat': lat,
                    'lng': lng,
                    'threat_type': threat_type,
                    'text': f"Загроза в {city_raw}",
                    'date': date_str,
                    'channel': channel,
                    'marker_icon': icon,
                    'source_match': 'emoji_structure',
                    'count': 1
                })

                add_debug_log(f"Emoji structure: {city_raw} -> {coords}", "emoji_struct")
            else:
                add_debug_log(f"Emoji structure: No coords for {city_raw}", "emoji_struct")

        return threats

    # Check for single UAV course mentions first (before multi-regional check)
    single_uav_threats = handle_single_uav_courses()
    if single_uav_threats:
        add_debug_log(f"SINGLE UAV COURSES: Found {len(single_uav_threats)} threats", "single_uav")
        # Continue processing to also get regular location markers
        # Don't return early - we want both UAV course markers AND location markers

    # Check for multi-regional UAV messages
    if multi_regional_flag:
        multi_regional_threats = handle_multi_regional_uav()
        if multi_regional_threats:
            add_debug_log(f"MULTI-REGIONAL UAV: Found {len(multi_regional_threats)} threats", "multi_regional")
            return multi_regional_threats

    # Southeast-wide tactical aviation activity (no specific settlement): place a synthetic marker off SE border.
    se_phrase = lower if 'lower' in locals() else original_text.lower()
    if ('тактичн' in se_phrase or 'авіаці' in se_phrase or 'авиац' in se_phrase) and ('південно-східн' in se_phrase or 'південно східн' in se_phrase or 'юго-восточ' in se_phrase or 'південного-сходу' in se_phrase):
        # Approx point in Azov Sea off SE (between Mariupol & Berdyansk) to avoid implying exact impact
        lat, lng = 46.5, 37.5
        return [{
            'id': f"{mid}_se", 'place': 'Південно-східний напрямок', 'lat': lat, 'lng': lng,
            'threat_type': 'avia', 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': 'avia.png', 'source_match': 'southeast_aviation'
        }]
    # North-east tactical aviation activity - coordinates on Russian territory before Ukraine border
    # Aviation threats come FROM Russia, so marker should be in Russia
    # SKIP if this is a multi-threat message (handled separately above)
    if ('тактичн' in se_phrase or 'авіаці' in se_phrase or 'авиац' in se_phrase) and (
        'північно-східн' in se_phrase or 'північно східн' in se_phrase or 'северо-восточ' in se_phrase or 'північного-сходу' in se_phrase
    ) and not ('🛬' in original_text and '🛸' in original_text):
        # Coordinates on Russian territory (Belgorod area) - aviation source location
        lat, lng = 51.0, 36.5  # Near Belgorod, Russia (before Ukraine border)
        return [{
            'id': f"{mid}_ne", 'place': 'Північно-східний напрямок', 'lat': lat, 'lng': lng,
            'threat_type': 'avia', 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': 'avia.png', 'source_match': 'northeast_aviation'
        }]
    m = re.search(r'(\d{1,2}\.\d+),(\d{1,3}\.\d+)', text)
    if m:
        lat_val = safe_float(m.group(1))
        lng_val = safe_float(m.group(2))
        if lat_val is not None and lng_val is not None and validate_ukraine_coords(lat_val, lng_val):
            threat_type, icon = classify(text)
            return [{
                'id': str(mid), 'place': 'Unknown', 'lat': lat_val, 'lng': lng_val,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon
            }]
    # Alarm cancellation always list-only
    if re.search(r'відбій\s+тривог|отбой\s+тревог', original_text.lower()):
        return [{
            'id': str(mid), 'place': None, 'lat': None, 'lng': None,
            'threat_type': 'alarm_cancel', 'text': original_text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': 'vidboi.png', 'list_only': True
        }]
    lower = text.lower()
    # Specialized single-line pattern: direction from one oblast toward another (e.g. 'бпла ... курсом на полтавщину')
    import re as _re_one
    m_dir_oblast = _re_one.search(r'бпла[^\n]*курс(?:ом)?\s+на\s+([a-zа-яїієґ\-]+щин[ауі])', lower)
    if m_dir_oblast:
        dest = m_dir_oblast.group(1)
        # normalize accusative -> nominative
        dest_norm = dest.replace('щину','щина').replace('щини','щина')
        if dest_norm in OBLAST_CENTERS:
            dest_lat, dest_lng = OBLAST_CENTERS[dest_norm]

            def _region_key_from_stem(stem: str):
                for key in OBLAST_CENTERS.keys():
                    if stem and stem in key:
                        return key
                return None

            def _resolve_location_token(token: str):
                if not token:
                    return None
                cleaned = token.strip(" .,:;!?\n\t'`\"-»«")
                if not cleaned:
                    return None
                cleaned = ' '.join(cleaned.split())
                variants = [cleaned]
                def _add_variant(val: str):
                    v = val.strip()
                    if v and v not in variants:
                        variants.append(v)
                suffix_map = {
                    'щину': 'щина', 'щини': 'щина', 'щині': 'щина',
                    ' область': ' область', ' обл.': ' область', ' обл': ' область'
                }
                for suffix, repl in suffix_map.items():
                    if cleaned.endswith(suffix):
                        _add_variant(cleaned[:-len(suffix)] + repl)
                loc_endings = [('і','ь'),('і','а'),('і','я'),('ї','я'),('ю','я'),('у','а')]
                for ending, replacement in loc_endings:
                    if cleaned.endswith(ending):
                        _add_variant(cleaned[:-len(ending)] + replacement)
                for variant in list(variants):
                    normalized = UA_CITY_NORMALIZE.get(variant, variant)
                    if normalized in OBLAST_CENTERS:
                        plat, plng = OBLAST_CENTERS[normalized]
                        return {'label': normalized.split()[0].title(), 'lat': plat, 'lng': plng}
                    if normalized in CITY_TO_OBLAST:
                        stem = CITY_TO_OBLAST[normalized]
                        reg_key = _region_key_from_stem(stem)
                        if reg_key:
                            plat, plng = OBLAST_CENTERS[reg_key]
                            return {'label': reg_key.split()[0].title(), 'lat': plat, 'lng': plng}
                    if normalized in CITY_COORDS:
                        plat, plng = CITY_COORDS[normalized]
                        return {'label': normalized.title(), 'lat': plat, 'lng': plng}
                return None

            prefix = lower[:m_dir_oblast.start()]
            source_candidate = None
            src_pattern = _re_one.compile(r'(?:на|у|в|із|зі|з)\s+([a-zа-яїієґ\-\'ʼ`\s]{3,40})')
            for sm in src_pattern.finditer(prefix):
                resolved = _resolve_location_token(sm.group(1))
                if resolved:
                    source_candidate = resolved
            if not source_candidate:
                header_match = _re_one.match(r'^\s*([a-zа-яїієґ\-\'ʼ`\s]{3,})[:—-]', lower)
                if header_match:
                    resolved = _resolve_location_token(header_match.group(1))
                    if resolved:
                        # Skip if header is just an oblast/region marker (not a specific city)
                        # When destination is also an oblast, this indicates region-level info without specific location
                        header_text = header_match.group(1).strip()
                        header_normalized = LOCATIVE_NORMALIZE.get(header_text, header_text)
                        is_region_header = (
                            header_normalized in OBLAST_CENTERS or
                            header_normalized in CITY_TO_OBLAST or
                            'область' in header_normalized or 'обл' in header_normalized or
                            header_text.endswith(('щина', 'щині', 'щину', 'щиною'))
                        )
                        dest_is_oblast = dest_norm in OBLAST_CENTERS
                        # Only use header as source if it's a specific city OR if destination is a city (not oblast)
                        if not (is_region_header and dest_is_oblast):
                            source_candidate = resolved
            if source_candidate:
                src_lat, src_lng = source_candidate['lat'], source_candidate['lng']
                dest_label = dest_norm.split()[0].title()

                def _direction_token(dlat: float, dlng: float):
                    if abs(dlat) < 1e-6 and abs(dlng) < 1e-6:
                        return None
                    if abs(dlat) > abs(dlng) * 1.4:
                        return 'n' if dlat > 0 else 's'
                    if abs(dlng) > abs(dlat) * 1.4:
                        return 'e' if dlng > 0 else 'w'
                    if dlat >= 0 and dlng >= 0:
                        return 'ne'
                    if dlat >= 0 and dlng < 0:
                        return 'nw'
                    if dlat < 0 and dlng >= 0:
                        return 'se'
                    return 'sw'

                dir_token = _direction_token(dest_lat - src_lat, dest_lng - src_lng)
                arrow_label_map = {
                    'n': 'півночі', 's': 'півдня', 'e': 'сходу', 'w': 'заходу',
                    'ne': 'північного сходу', 'nw': 'північного заходу',
                    'se': 'південного сходу', 'sw': 'південного заходу'
                }
                course_direction_map = {
                    'n': 'північ', 's': 'південь', 'e': 'схід', 'w': 'захід',
                    'ne': 'північний схід', 'nw': 'північний захід',
                    'se': 'південний схід', 'sw': 'південний захід'
                }
                arrow_label = arrow_label_map.get(dir_token, '')
                course_direction_text = course_direction_map.get(dir_token, dest_label)

                place_name = f"{source_candidate['label']} → {dest_label}"
                if arrow_label:
                    place_name += f" ←{arrow_label}"

                trajectory = {
                    'start': [src_lat, src_lng],
                    'end': [dest_lat, dest_lng],
                    'source': source_candidate['label'],
                    'target': dest_label,
                    'kind': 'singleline_region_course'
                }

                threat_type, icon = classify(original_text)
                return [{
                    'id': f"{mid}_dir_oblast", 'place': place_name, 'lat': src_lat, 'lng': src_lng,
                    'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'singleline_region_course', 'trajectory': trajectory,
                    'course_source': source_candidate['label'], 'course_target': dest_label,
                    'course_direction': f"курс на {course_direction_text}", 'course_type': 'region_to_region'
                }]

            return [{
                'id': f"{mid}_dir_oblast", 'place': dest_norm.title(), 'lat': dest_lat, 'lng': dest_lng,
                'threat_type': 'uav', 'text': original_text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': 'shahed3.webp', 'source_match': 'singleline_oblast_course'
            }]
    # Extract drone / shahed count pattern (e.g. "7х бпла", "6x дронів", "10 х бпла") early so later branches can reuse
    drone_count = None
    m_count = re.search(r'(\b\d{1,3})\s*[xх]\s*(?:бпла|дрон|дрони|шахед|шахеди|шахедів)', lower)
    if m_count:
        try:
            drone_count = int(m_count.group(1))
        except ValueError:
            drone_count = None
    # Normalize some genitive forms ("дніпропетровської" -> base) to capture multiple oblasts in one message
    GENITIVE_NORMALIZE = {
        'дніпропетровської': 'дніпропетровська область',
        'днепропетровской': 'дніпропетровська область',
        'чернігівської': 'чернігівська обл.',
        'черниговской': 'чернігівська обл.',
        'сумської': 'сумська область',
        'сумской': 'сумська область',
        'харківської': 'харківська обл.',
        'харьковской': 'харківська обл.'
    }
    for gform, base_form in GENITIVE_NORMALIZE.items():
        if gform in lower:
            lower = lower.replace(gform, base_form)
    # Locative / prepositional oblast & region endings -> base ("дніпропетровщині" -> "дніпропетровщина")
    LOCATIVE_NORMALIZE = {
        'дніпропетровщині': 'дніпропетровщина',
        'донеччині': 'донеччина',
        'сумщині': 'сумщина',
        'харківщині': 'харківщина',
        'чернігівщині': 'чернігівщина',
        'миколаївщині': 'миколаївщина',
        'херсонщині': 'херсонщина',
        'запоріжжі': 'запоріжжя'
    }
    for lform, base_form in LOCATIVE_NORMALIZE.items():
        if lform in lower:
            lower = lower.replace(lform, base_form)
    # City genitive -> nominative (subset) for settlement detection
    CITY_GENITIVE = [
        ('харкова','харків'), ('києва','київ'), ('львова','львів'), ('одеси','одеса'), ('дніпра','дніпро')
    ]
    for gform, base in CITY_GENITIVE:
        if gform in lower:
            lower = lower.replace(gform, base)
    # Normalize some accusative oblast forms to nominative for matching
    lower = lower.replace('донеччину','донеччина').replace('сумщину','сумщина')
    text = lower  # downstream logic mostly uses lower-case comparisons
    # Санітизація дублювань типу "область області" -> залишаємо один раз
    text = re.sub(r'(область|обл\.)\s+област[іи]', r'\1', text)

    # --- Simple sanitization of formatting noise (bold asterisks, stray stars) ---
    # Keeps Ukrainian characters while removing leading/trailing markup like ** or * around segments
    if '**' in text or '*' in text:
        # remove isolated asterisks not part of words
        text = re.sub(r'\*+', '', text)

    # --- Early explicit pattern: "<RaionName> район (<Oblast ...>)" (e.g. "Запорізький район (Запорізька обл.)") ---
    # Sometimes such messages were slipping through as raw because the pre-parenthesis token ended with 'район'.
    m_raion_oblast = re.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{4,})\s+район\s*\(([^)]*обл[^)]*)\)', text)
    if m_raion_oblast:
        raion_token = m_raion_oblast.group(1).strip().lower()
        # Normalize morphological endings similar to later norm_raion logic
        raion_base = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_token)
        if raion_base in RAION_FALLBACK:
            lat, lng = RAION_FALLBACK[raion_base]
            threat_type, icon = classify(original_text if 'original_text' in locals() else text)
            # Maintain active raion alarm state
            if threat_type == 'alarm':
                RAION_ALARMS[raion_base] = {'place': f"{raion_base.title()} район", 'lat': lat, 'lng': lng, 'since': time.time()}
            elif threat_type == 'alarm_cancel':
                RAION_ALARMS.pop(raion_base, None)
            return [{
                'id': str(mid), 'place': f"{raion_base.title()} район", 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': (original_text if 'original_text' in locals() else text)[:500],
                'date': date_str, 'channel': channel, 'marker_icon': icon, 'source_match': 'raion_oblast_combo'
            }]
        else:
            log.debug(f"raion_oblast primary matched token={raion_token} base={raion_base} no coords")
    else:
        # Secondary heuristic fallback if formatting (emoji / markup) broke regex
        if 'район (' in text and ' обл' in text and has_threat(text):
            try:
                prefix = text.split('район (',1)[0]
                cand = prefix.strip().split()[-1].lower()
                cand_base = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', cand)
                if cand_base in RAION_FALLBACK:
                    lat,lng = RAION_FALLBACK[cand_base]
                    threat_type, icon = classify(original_text if 'original_text' in locals() else text)
                    log.debug(f"raion_oblast secondary emit cand={cand} base={cand_base}")
                    return [{
                        'id': str(mid), 'place': f"{cand_base.title()} район", 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': (original_text if 'original_text' in locals() else text)[:500],
                        'date': date_str, 'channel': channel, 'marker_icon': icon, 'source_match': 'raion_oblast_secondary'
                    }]
                else:
                    log.debug(f"raion_oblast secondary no coords cand={cand} base={cand_base}")
            except Exception as _e:
                log.debug(f"raion_oblast secondary error={_e}")

    # --- Russian strategic aviation suppression (uses _is_russian_strategic_aviation defined earlier) ---
    if _is_russian_strategic_aviation(text):
        return None

    if _is_general_warning_without_location(text):
        return None

    # --- Western border drone reconnaissance suppression ---
    def _is_western_border_reconnaissance(t: str) -> bool:
        """Suppress messages about drones crossing western borders (Hungary, etc.) - not related to Russian threats"""
        t_lower = t.lower()

        # Check for western border crossing indicators
        border_crossing_terms = [
            'перетнув державний кордон', 'пересек государственную границу',
            'перетнув кордон', 'пересек границу',
            'з боку угорщини', 'со стороны венгрии',
            'з території угорщини', 'с территории венгрии'
        ]
        has_border_crossing = any(term in t_lower for term in border_crossing_terms)

        # Check for western regions (primarily Zakarpattya)
        western_regions = ['закарпатт', 'закарпать', 'ужгород', 'мукачев']
        has_western_region = any(region in t_lower for region in western_regions)

        # Check for reconnaissance/monitoring context (not combat threats)
        recon_terms = ['радари зсу', 'радары всу', 'зафіксували проліт', 'зафиксировали пролет', 'стежити за обстановкою', 'следить за обстановкой']
        has_recon_context = any(term in t_lower for term in recon_terms)

        # Suppress if it's about western border reconnaissance
        if has_border_crossing and has_western_region:
            return True

        # Also suppress general monitoring messages about western regions
        if has_western_region and has_recon_context and ('дрон' in t_lower or 'бпла' in t_lower):
            return True

        return False

    if _is_western_border_reconnaissance(text):
        return None

    # --- Aggregate / statistical summary suppression ---
    def _is_aggregate_summary(t: str) -> bool:
        # Situation report override: if starts with 'обстановка' we evaluate full logic first (word 'загроза' inside shouldn't unblock)
        starts_obst = t.startswith('обстановка')
        # Do not suppress if explicit real-time warning words present (unless it's a structured situation report)
        if not starts_obst and any(w in t for w in ['загроза','перейдіть в укриття','укриття!']):
            return False
        verbs = ['збито/подавлено','збито / подавлено','збито-подавлено','збито','подавлено','знищено']
        context = ['станом на','за попередніми даними','у ніч на','повітряний напад','протиповітряною обороною','протиповітряна оборона','підрозділи реб','мобільні вогневі групи','обстановка']
        objects_re = re.compile(r'\b\d{1,3}[\-–]?(ма|)?\s*(ворожих|)\s*(бпла|shahed|дрон(?:ів|и)?|ракет|ракети)')
        verb_hit = any(v in t for v in verbs)
        ctx_hits = sum(1 for c in context if c in t)
        obj_hit = bool(objects_re.search(t))
        # Strong aggregate if all three categories present OR multiple context + objects
        if (verb_hit and obj_hit and ctx_hits >= 1) or (ctx_hits >= 2 and obj_hit):
            return True
        # Long multiline with origins list and many commas plus 'типу shahed'
        if 'типу shahed' in t and t.count('\n') >= 2 and obj_hit:
            return True
        # Situation report structure: starts with 'обстановка станом на' or begins with 'обстановка' and multiple category lines (— стратегічна авіація, — бпла, — флот)
        if starts_obst:
            dash_lines = sum(1 for line in t.split('\n') if line.strip().startswith('—'))
            if dash_lines >= 2:
                return True
        return False
    if _is_aggregate_summary(text):
        return None

    # --- Pattern: City (Oblast ...) e.g. "Павлоград (Дніпропетровська обл.)" ---
    bracket_city = re.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})\s*\(([^)]+)\)', text)
    if bracket_city:
        raw_city = bracket_city.group(1).strip().lower()
        raw_inside = bracket_city.group(2).lower()
        # Особый случай: "дніпропетровська область (павлоградський р-н)" -> ставим Павлоград
        if ('область' in raw_city or 'обл' in raw_city) and ('павлоград' in raw_inside):
            pav_key = 'павлоградський'
            if pav_key in RAION_FALLBACK:
                lat,lng = RAION_FALLBACK[pav_key]
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': 'Павлоградський район', 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'oblast_raion_combo'
                }]
        # Пропускаем случаи вида "<область> (<район ...>)" чтобы не трактовать слово 'область' как город
        if raw_city in {'область','обл','обл.'} or raw_city.endswith('область'):
            bracket_city = None
    if bracket_city and raw_city != 'район':
            norm_city = UA_CITY_NORMALIZE.get(raw_city, raw_city)
            # Initial local attempt (static minimal list)
            coords = CITY_COORDS.get(norm_city)
            # Region hint extraction
            region_hint = None
            if any(tok in raw_inside for tok in ['обл', 'область']):
                region_hint = raw_inside.strip()
            # 1) Explicit override for (city, region) if provided
            if region_hint:
                override_key = (norm_city, region_hint)
                if override_key in OBLAST_CITY_OVERRIDES:
                    coords = OBLAST_CITY_OVERRIDES[override_key]
            # 2) If we have region hint and NO coords yet, attempt region-qualified geocode first (priority to enforce oblast binding)
            region_combo_tried = False
            if not coords and region_hint and OPENCAGE_API_KEY:
                combo_query = f"{norm_city} {region_hint}".replace('  ',' ').strip()
                try:
                    refined = geocode_opencage(combo_query)
                    if refined:
                        coords = refined
                    region_combo_tried = True
                except Exception:
                    pass
            # 3) Attempt city alone geocode only if still no coords
            if not coords and OPENCAGE_API_KEY:
                try:
                    coords = geocode_opencage(norm_city)
                except Exception:
                    pass
            # 4) If region hint exists and we got coords from plain city geocode but city is potentially duplicated across oblasts,
            # try region-qualified geocode as refinement (unless already tried).
            if region_hint and OPENCAGE_API_KEY and not region_combo_tried and coords and norm_city in ['борова','миколаївка','николаевка']:
                try:
                    combo_query = f"{norm_city} {region_hint}".replace('  ',' ').strip()
                    refined2 = geocode_opencage(combo_query)
                    if refined2:
                        coords = refined2
                except Exception:
                    pass
            # Ambiguous manual mapping fallback (if still no coords or mismatch with region)
            if region_hint:
                # derive stem like 'харківськ', 'львівськ'
                rh_low = region_hint.lower()
                # choose first word containing 'харків' etc
                region_key = None
                for stem in ['харків','львів','київ','дніпропетров','полтав','сум','черніг','волин','запор','одес','микола','черка','житом','хмельниць','рівн','івано','терноп','ужгород','кропив','луган','донець','чернівц']:
                    if stem in rh_low:
                        region_key = stem
                        break
                AMBIGUOUS_CITY_REGION = {
                    ('золочів','харків'): (50.2788, 36.3644),  # Zolochiv Kharkiv oblast
                    ('золочів','львів'): (49.8078, 24.9002),   # Zolochiv Lviv oblast
                }
                if region_key:
                    key = (norm_city, region_key)
                    mapped = AMBIGUOUS_CITY_REGION.get(key)
                    if mapped:
                        coords = mapped
            if coords:
                lat,lng = coords
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': norm_city.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'bracket_city'
                }]

    # --- Multi-segment / enumerated lines (1. 2. 3.) region extraction ---
    # Разбиваем по переносам, собираем упоминания нескольких областей; создаём отдельные маркеры

    # PRIORITY: Detect trajectory patterns BEFORE multi-region processing
    # Pattern: "з [source_region] на [target_region(s)]" - trajectory, not multi-target
    trajectory_pattern = r'(\d+(?:-\d+)?)?\s*шахед[іївыиє]*\s+з\s+([а-яіїєґ]+(щин|ччин)[ауиі])\s+на\s+([а-яіїєґ/]+(щин|ччин)[ауиіу])'
    trajectory_match = re.search(trajectory_pattern, text.lower(), re.IGNORECASE)

    if trajectory_match:
        count_str = trajectory_match.group(1)
        source_region = trajectory_match.group(2)
        target_regions = trajectory_match.group(4)

        print(f"DEBUG: Trajectory detected - {count_str or ''}шахедів з {source_region} на {target_regions}")

        # For trajectory messages, we should NOT create markers in region centers
        # This represents movement through airspace, not attacks on specific locations
        # Options:
        # 1. Don't create any markers (trajectory only)
        # 2. Create trajectory line visualization
        # 3. Create border crossing markers

        # For now, suppress markers for pure trajectory messages
        print("DEBUG: Suppressing region markers for trajectory message")
        return None

    region_hits = []  # list of (display_name, (lat,lng), snippet)
    # Treat semicolons as separators like newlines for multi-segment parsing
    seg_text = text.replace(';', '\n')
    lines = [ln.strip() for ln in seg_text.split('\n') if ln.strip()]
    # Pre-flag launch site style multi-line posts to avoid RAW fallback – treat each line with a launch phrase as separate pseudo-track (no coords yet)
    launch_mode = any(ln.lower().startswith('відмічені пуски') or ln.lower().startswith('+ пуски') for ln in lines)
    for ln in lines:
        ln_low = ln.lower()
        local_regions = []
        for name, coords in OBLAST_CENTERS.items():
            if name in ln_low:
                local_regions.append((name, coords))
        # если в строке более 1— сохраняем все, иначе одну
        for (rn, rc) in local_regions:
            region_hits.append((rn.title(), rc, ln[:180]))
    # Якщо знайшли >=2 регіональних маркери в різних пунктах списку — формуємо множинні треки
    if len(region_hits) >= 2 and not launch_mode:
        # ВИДАЛЕНО перевірку course_line_present - тепер завжди дозволяємо region markers + course parsing
        if True:  # завжди виконуємо блок регіональних маркерів
            # Пропускаем если нет ни одного упоминания угрозы вообще
            if not has_threat(text):
                return None
            threat_type, icon = classify(text)
            tracks = []
            # deduplicate by name
            seen_names = set()
            # Directional offset helper
            def directional_offset(rlabel: str, lat: float, lng: float):
                base = rlabel.lower().split()[0]
                full = text  # already lower
                # detect "на схід <base>", "схід <base>", etc., but ignore origins "з південного сходу" for that base
                # We only tag if phrase contains base key AFTER direction (targeting side), not originating "з <dir> ..." alone.
                directions = [
                    ('схід', 'east', (0.0, 0.9)),
                    ('захід', 'west', (0.0, -0.9)),
                    ('північ', 'north', (0.7, 0.0)),
                    ('південь', 'south', (-0.7, 0.0))
                ]
                applied = None
                for word, code, (dlat, dlng) in directions:
                    patterns = [f"на {word} {base}", f" {word} {base}"]
                    if any(pat in full for pat in patterns) and f"з {word}" not in full:
                        applied = (code, dlat, dlng)
                        break
                if not applied:
                    return lat, lng, rlabel
                _, dlat, dlng = applied
                nlat = max(43.0, min(53.5, lat + dlat))
                nlng = max(21.0, min(41.0, lng + dlng))
                human = {'east':'схід','west':'захід','north':'північ','south':'південь'}[applied[0]]
                return nlat, nlng, f"{rlabel} ({human})"
            for idx, (rname, (lat,lng), snippet) in enumerate(region_hits, 1):
                if rname in seen_names: continue
                seen_names.add(rname)
                adj_lat, adj_lng, adj_label = directional_offset(rname, lat, lng)
                tracks.append({
                    'id': f"{mid}_{idx}", 'place': adj_label, 'lat': adj_lat, 'lng': adj_lng,
                    'threat_type': threat_type, 'text': snippet[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'region_multi'
                })
            if tracks:
                return tracks

    # --- Single border oblast KAB launch: place marker at predefined border point ---
    if len(region_hits) == 1 and 'каб' in lower and ('пуск' in lower or 'пуски' in lower):
        rname, (olat, olng), snippet = region_hits[0]
        # базовые ключи для соответствия
        key = rname.lower()
        BORDER_POINTS = {
            'донеччина': (48.20, 37.90),
            'донецька область': (48.20, 37.90),
            'сумщина': (51.30, 34.40),
            'сумська область': (51.30, 34.40),
            'чернігівщина': (51.75, 31.60),
            'чернігівська обл.': (51.75, 31.60),
            'харківщина': (50.25, 36.85),
            'харківська обл.': (50.25, 36.85),
            'луганщина': (48.90, 39.40),
            'луганська область': (48.90, 39.40),
            'запорізька обл.': (47.55, 35.60),
            'херсонська обл.': (46.65, 32.60)
        }
        # нормализация ключа (удаляем регистр / лишние пробелы)
        k_simple = key.replace('’','').replace("'",'').strip()
        # попытка прямого поиска
        coord = None
        for bk, bcoord in BORDER_POINTS.items():
            if bk in k_simple:
                coord = bcoord
                break
        if coord:
            threat_type, icon = classify(text)
            return [{
                'id': str(mid), 'place': rname + ' (кордон)', 'lat': coord[0], 'lng': coord[1],
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'border_kab'
            }]

    # --- Pattern: multiple shaheds with counts / directions / near-pass ("повз") ---
    # Handles composite direction phrases (південного сходу -> південний схід, північно-захід тощо)
    # Examples: "14 шахедів ... 3 на Покровське з півдня, 9 на Петропавлівку з південного сходу, 2 на Шахтарське з півдня"
    #           "16 шахедів ... 2 повз Терентівку на північ, 6 на Юріївку з півдня, 7 повз Межову північно-захід" etc.
    if 'шахед' in lower and ((' на ' in lower) or (' повз ' in lower)):
        segs = re.split(r'[\n,⚠;]+', lower)
        found = []
        # Direction phrases may appear after 'з', 'зі', 'із', 'на'. Capture full tail then normalize.
        pat_on = re.compile(r'(\d{1,2})\s+на\s+([a-zа-яіїєґ\-ʼ\']{3,})(?:у|а|е)?(?:\s+((?:з|зі|із|на)\s+[a-zа-яіїєґ\-\s]+))?')
        pat_povz = re.compile(r'(\d{1,2})\s+повз\s+([a-zа-яіїєґ\-ʼ\']{3,})(?:у|а|е)?(?:\s+(?:на\s+)?([a-zа-яіїєґ\-\s]+))?')
        def normalize_direction(raw_dir: str) -> str:
            if not raw_dir:
                return ''
            d = raw_dir.lower().strip()
            # remove leading prepositions
            d = re.sub(r'^(з|зі|із|на|від)\s+', '', d)
            d = d.replace('–','-')
            # unify hyphen variants to space-separated tokens
            d = d.replace('-', ' ')
            d = re.sub(r'\s+', ' ', d).strip()
            # morphological endings -> base cardinal forms
            repl = [
                (r'південного сходу', 'південний схід'),
                (r'північного сходу', 'північний схід'),
                (r'південного заходу', 'південний захід'),
                (r'північного заходу', 'північний захід'),
                (r'півдня', 'південь'),
                (r'півночі', 'північ'),
                (r'сходу', 'схід'),
                (r'заходу', 'захід')
            ]
            for pat, rep in repl:
                d = re.sub(pat, rep, d)
            # collapse duplicate words
            parts = []
            seen = set()
            for tok in d.split():
                if tok in seen:
                    continue
                seen.add(tok)
                parts.append(tok)
            return ' '.join(parts)
        for seg in segs:
            # Strip common trailing separators (colon, semicolon, space, slash, backslash)
            s = seg.strip(':; /\\')
            if not s or s.isdigit():
                continue
            matches = []
            matches.extend(list(pat_on.finditer(s)))
            matches.extend(list(pat_povz.finditer(s)))
            for m in matches:
                cnt = int(m.group(1))
                place_token = (m.group(2) or '').strip("-'ʼ")
                raw_dir = ''
                # pat_on group(3); pat_povz group(3)
                if len(m.groups()) >= 3:
                    raw_dir = (m.group(3) or '').strip()
                direction = normalize_direction(raw_dir)
                place_token = place_token.replace('ʼ',"'")
                variants = {place_token}
                # heuristic nominative recovery
                if place_token.endswith('ку'): variants.add(place_token[:-2]+'ка')
                if place_token.endswith('ву'): variants.add(place_token[:-2]+'ва')
                if place_token.endswith('ову'): variants.add(place_token[:-3]+'ова')
                if place_token.endswith('ю'):
                    variants.add(place_token[:-1]+'я'); variants.add(place_token[:-1]+'а')
                if place_token.endswith('у'): variants.add(place_token[:-1]+'а')
                if place_token.endswith('ому'):
                    variants.add(place_token[:-3]+'е'); variants.add(place_token[:-3])
                matched_coord = None; matched_name = None
                for var in variants:
                    if var in CITY_COORDS:
                        matched_coord = CITY_COORDS[var]; matched_name = var; break
                if matched_coord:
                    plat, plng = matched_coord
                    found.append((matched_name, plat, plng, cnt, direction, s[:160]))
        if found:
            threat_type, icon = classify(text)
            tracks = []
            for idx,(p, plat, plng, cnt, direction, snippet) in enumerate(found,1):
                base_label = f"{p.title()} ({cnt})"
                if direction:
                    base_label += f" ←{direction}"
                tracks.append({
                    'id': f"{mid}_s{idx}", 'place': base_label, 'lat': plat, 'lng': plng,
                    'threat_type': threat_type, 'text': snippet[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'multi_shah_ed', 'count': cnt
                })
            if found and not tracks:
                log.debug(f"multi_shah_ed matched segments but no tracks mid={mid} raw={found}")
            if tracks:
                log.debug(f"multi_shah_ed tracks mid={mid} -> {[t['place'] for t in tracks]}")
                return tracks

    # --- Per-line UAV course / area city targeting ("БпЛА курсом на <місто>", "8х БпЛА в районі <міста>", "БпЛА на <місто>") ---
    # Triggered when region multi list suppressed earlier due to presence of course lines or simple "на" pattern.
    if 'бпла' in lower and ('курс' in lower or 'в районі' in lower or 'в напрямку' in lower or 'в бік' in lower or 'від' in lower or 'околиц' in lower or 'сектор' in lower or 'бпла на ' in lower or (re.search(r'\d+\s*[xх×]?\s*бпла\s+на\s+', lower))):
        add_debug_log(f"UAV course parser triggered for message length: {len(text)} chars", "uav_course")

        # --- EARLY CHECK: Black Sea aquatory (e.g. "курсом на Миколаїв з акваторії Чорного моря" or "15 шахедів з моря на Ізмаїл") ---
        # Must check BEFORE "курсом на" parser to prevent placing marker on target city
        is_black_sea = (('акватор' in lower or 'акваторії' in lower) and ('чорного моря' in lower or 'чорне море' in lower or 'чорному морі' in lower)) or \
                       ('з моря' in lower and ('курс' in lower or 'на ' in lower)) or \
                       ('з чорного моря' in lower)

        if is_black_sea:
            # Extract target region/direction if mentioned
            m_target = re.search(r'курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower)
            m_direction = re.search(r'на\s+(північ|південь|схід|захід|північний\s+схід|північний\s+захід|південний\s+схід|південний\s+захід)', lower)
            m_region = re.search(r'(одещин|одеськ|миколаїв|херсон)', lower)

            target_info = None
            sea_lat, sea_lng = 45.3, 30.7  # Default: northern Black Sea central coords

            # Adjust position based on direction/region
            if m_direction:
                direction = m_direction.group(1)
                if 'південь' in direction:
                    sea_lat = 45.0  # Further south
                elif 'північ' in direction:
                    sea_lat = 45.6  # Further north
                if 'схід' in direction:
                    sea_lng = 31.2  # Further east
                elif 'захід' in direction:
                    sea_lng = 30.2  # Further west

            if m_region:
                region_name = m_region.group(1)
                if 'одещин' in region_name or 'одеськ' in region_name:
                    # South of Odesa region - in the sea 50km offshore
                    sea_lat, sea_lng = 45.7, 30.7
                    target_info = 'Одещини'
                elif 'миколаїв' in region_name:
                    sea_lat, sea_lng = 45.9, 31.4
                    target_info = 'Миколаївщини'
                elif 'херсон' in region_name:
                    sea_lat, sea_lng = 45.7, 32.5
                    target_info = 'Херсонщини'

            if m_target:
                tc = m_target.group(1).lower()
                tc = UA_CITY_NORMALIZE.get(tc, tc)
                target_info = tc.title()

            threat_type, icon = classify(text)
            place_label = 'Акваторія Чорного моря'
            if target_info:
                place_label += f' (на {target_info})'

            # Try to find target city coordinates for trajectory
            target_coords = None
            if m_target:
                tc_normalized = m_target.group(1).lower()
                tc_normalized = UA_CITY_NORMALIZE.get(tc_normalized, tc_normalized)
                if tc_normalized in CITY_COORDS:
                    target_coords = CITY_COORDS[tc_normalized]

            result = {
                'id': str(mid), 'place': place_label, 'lat': sea_lat, 'lng': sea_lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'black_sea_course'
            }

            # Add trajectory data if we have target coordinates
            if target_coords:
                result['trajectory'] = {
                    'start': [sea_lat, sea_lng],
                    'end': list(target_coords),
                    'target': target_info
                }

            return [result]

        original_text_norm = re.sub(r'(?i)(\b[А-Яа-яЇїІіЄєҐґ\-]{3,}(?:щина|область|обл\.)):(?!\s*\n)', r'\1:\n', original_text)
        lines_with_region = []
        current_region_hdr = None
        for raw_ln in original_text_norm.splitlines():
            ln_stripped = raw_ln.strip()
            if not ln_stripped:
                continue
            low_ln = ln_stripped.lower()
            # Allow region header if line ends with ':' even if preceded by emoji or bullets
            if low_ln.endswith(':'):
                # remove leading emojis/symbols
                cleaned_hdr = re.sub(r'^[^a-zа-яіїєґ]+','', low_ln[:-1])
                base_hdr = cleaned_hdr.strip()
                log.debug(f"mid={mid} region_header_check: '{low_ln}' -> cleaned: '{base_hdr}' -> found: {base_hdr in OBLAST_CENTERS}")
                if base_hdr in OBLAST_CENTERS:
                    current_region_hdr = base_hdr
                    log.debug(f"mid={mid} region_header_set: '{base_hdr}'")
                continue
            # split by semicolons; also break on pattern like " 2х БпЛА курсом" inside the same segment later
            subparts = [p.strip() for p in re.split(r'[;]+', ln_stripped) if p.strip()]
            for part in subparts:
                lines_with_region.append((part, current_region_hdr))
        # Further split segments that contain multiple "БпЛА курс" phrases glued together
        multi_start_re = re.compile(r'(?:\d+\s*[xх×]?\s*)?бпла\s*курс', re.IGNORECASE)
        expanded = []
        for part, region_hdr in lines_with_region:
            low_part = part.lower()
            starts = [m.start() for m in multi_start_re.finditer(low_part)]
            if len(starts) <= 1:
                expanded.append((part, region_hdr))
                continue
            for idx, s in enumerate(starts):
                seg_start = s
                seg_end = starts[idx+1] if idx+1 < len(starts) else len(low_part)
                segment = part[seg_start:seg_end].strip()
                if segment:
                    expanded.append((segment, region_hdr))
        if expanded:
            lines_with_region = expanded
        course_tracks = []
        pat_count_course = re.compile(r'^(\d+(?:-\d+)?)\s*[xх×]?\s*бпла(?:\s+пролетіли)?.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-’ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_course = re.compile(r'бпла(?:\s+пролетіли)?.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-’ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_area = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(?:.*?\s+)?в\s+районі\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,60}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)  # Fixed: added н.п. support
        pat_napramku = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+[➡️⬆️⬇️⬅️↗️↘️↙️↖️]*\s*(?:в|у)\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_sektor = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+в\s+секторі\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_simple_na = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_complex_napramku = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на/через\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)\s+в\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_napramku_ta = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(?:в|у)\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)\s+та\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_okolytsi = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на\s+околицях\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_vid_do = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+від\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)\s+до\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        pat_vik = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+[➡️⬆️⬇️⬅️↗️↘️↙️↖️]*\s*(?:в|у)\s+бік\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
        if re.search(r'бпла.*?курс(?:ом)?\s+на\s+кіпт[ії]', lower):
            coords = SETTLEMENT_FALLBACK.get('кіпті')
            if coords:
                lat, lng = coords
                threat_type, icon = classify(original_text)
                return [{
                    'id': f"{mid}_kipti_course", 'place': 'Кіпті', 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'course_kipti'
                }]
        def norm_city_token(tok: str) -> str:
            t = tok.lower().strip(" .,'’ʼ`-:")
            t = t.replace("'", "'")  # Normalize curly quotes
            if t.endswith('ку'): t = t[:-2] + 'ка'
            elif t.endswith('ву'): t = t[:-2] + 'ва'
            elif t.endswith('ову'): t = t[:-3] + 'ова'
            elif t.endswith('ю'): t = t[:-1] + 'я'
            elif t.endswith('у'): t = t[:-1] + 'а'
            if t.startswith('нову '):
                t = 'нова ' + t[5:]
            t = t.replace('водолагу','водолога')
            return t

        # Pattern to extract oblast from parentheses like "(Полтавська обл.)" or "(Харківська область)"
        pat_oblast_in_parens = re.compile(r'\(([А-Яа-яЇїІіЄєҐґ\-]+)\s*обл\.?\)?', re.IGNORECASE)

        for ln, region_hdr in lines_with_region:
            ln_low = ln.lower()
            if 'бпла' not in ln_low:
                continue

            # PRIORITY: Extract oblast from parentheses in the line itself (e.g., "Семенівку (Полтавська обл.)")
            # This overrides the region header from channel
            line_oblast_match = pat_oblast_in_parens.search(ln)
            if line_oblast_match:
                oblast_name = line_oblast_match.group(1).lower()
                # Map to standard oblast name
                oblast_map = {
                    'полтавськ': 'полтавщина', 'полтавська': 'полтавщина',
                    'харківськ': 'харківщина', 'харківська': 'харківщина',
                    'чернігівськ': 'чернігівщина', 'чернігівська': 'чернігівщина',
                    'сумськ': 'сумщина', 'сумська': 'сумщина',
                    'київськ': 'київщина', 'київська': 'київщина',
                    'одеськ': 'одещина', 'одеська': 'одещина',
                    'миколаївськ': 'миколаївщина', 'миколаївська': 'миколаївщина',
                    'херсонськ': 'херсонщина', 'херсонська': 'херсонщина',
                    'запорізьк': 'запорізька', 'запорізька': 'запорізька',
                    'дніпропетровськ': 'дніпропетровщина', 'дніпропетровська': 'дніпропетровщина',
                    'донецьк': 'донецька', 'донецька': 'донецька',
                    'луганськ': 'луганська', 'луганська': 'луганська',
                    'черкаськ': 'черкащина', 'черкаська': 'черкащина',
                    'житомирськ': 'житомирщина', 'житомирська': 'житомирщина',
                    'вінницьк': 'вінниччина', 'вінницька': 'вінниччина',
                    'рівненськ': 'рівненщина', 'рівненська': 'рівненщина',
                    'волинськ': 'волинь', 'волинська': 'волинь',
                    'львівськ': 'львівщина', 'львівська': 'львівщина',
                    'тернопільськ': 'тернопільщина', 'тернопільська': 'тернопільщина',
                    'хмельницьк': 'хмельниччина', 'хмельницька': 'хмельниччина',
                    'івано-франківськ': 'івано-франківщина', 'івано-франківська': 'івано-франківщина',
                    'закарпатськ': 'закарпаття', 'закарпатська': 'закарпаття',
                    'чернівецьк': 'чернівецька', 'чернівецька': 'чернівецька',
                    'кіровоградськ': 'кіровоградщина', 'кіровоградська': 'кіровоградщина',
                }
                for key, val in oblast_map.items():
                    if oblast_name.startswith(key):
                        region_hdr = val
                        log.info(f"mid={mid} OVERRIDE region_hdr from line: '{oblast_name}' -> '{region_hdr}'")
                        break

            add_debug_log(f"Processing UAV line: '{ln[:100]}...' (region: {region_hdr})", "uav_course")

            # PRIORITY: Handle "БпЛА із/з [source] ➡️ у напрямку [target]" - marker at SOURCE, not target
            # Example: "🛵 БпЛА із Чернігівщини ➡️ у напрямку Києва" -> marker at Чернігівщина
            m_iz_napramku = re.search(r'бпла\s+(?:із|з)\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)\s*[➡️⬆️⬇️⬅️↗️↘️↙️↖️]*\s*(?:в|у)\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', ln_low, re.IGNORECASE)
            if m_iz_napramku:
                source_region = m_iz_napramku.group(1).strip()
                target_name = m_iz_napramku.group(2).strip()
                add_debug_log(f"Found 'із X у напрямку Y' pattern: source={source_region}, target={target_name}", "uav_course")
                
                # Get source coordinates (this is where UAV currently is!)
                source_norm = norm_city_token(source_region)
                coords = CITY_COORDS.get(source_norm) or OBLAST_CENTERS.get(source_norm) or (SETTLEMENTS_INDEX.get(source_norm) if SETTLEMENTS_INDEX else None)
                if not coords:
                    # Try as oblast
                    for obl_key, obl_coords in OBLAST_CENTERS.items():
                        if source_norm in obl_key or obl_key in source_norm:
                            coords = obl_coords
                            break
                
                if coords:
                    lat, lng = coords
                    threat_type, icon = classify(text)
                    label = f"{source_norm.title()} → {target_name.title()}"
                    
                    # Get target coordinates for trajectory
                    target_norm = norm_city_token(target_name)
                    target_coords = CITY_COORDS.get(target_norm) or OBLAST_CENTERS.get(target_norm) or (SETTLEMENTS_INDEX.get(target_norm) if SETTLEMENTS_INDEX else None)
                    if not target_coords:
                        target_coords = UKRAINE_ALL_SETTLEMENTS.get(target_norm)
                    
                    trajectory_data = None
                    if target_coords:
                        target_lat, target_lng = target_coords if len(target_coords) == 2 else (target_coords[0], target_coords[1])
                        trajectory_data = {
                            'start': [lat, lng],
                            'end': [target_lat, target_lng],
                            'target': target_name.title()
                        }
                    
                    course_tracks.append({
                        'id': f"{mid}_iz_napramku_{source_norm}", 'place': label, 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'uav_iz_napramku', 'count': 1,
                        'trajectory': trajectory_data
                    })
                    add_debug_log(f"Created marker at SOURCE: {source_norm} ({lat}, {lng}) with trajectory to {target_name}", "uav_course")
                    continue
                else:
                    add_debug_log(f"Could not find coords for source '{source_norm}'", "uav_course")

            # PRIORITY: Handle "БПЛА [city] курсом на [target]" - marker at CITY (current location), not target
            # Example: "БПЛА Славутич курсом на Київщина" -> marker at Славутич
            m_city_kursom = re.search(r'бпла\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`]{3,30})\s+курсом\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', ln_low, re.IGNORECASE)
            if m_city_kursom:
                current_city = m_city_kursom.group(1).strip()
                target_name = m_city_kursom.group(2).strip()
                add_debug_log(f"Found 'БПЛА [city] курсом на [target]' pattern: city={current_city}, target={target_name}", "uav_course")
                
                # Get current city coordinates (this is where UAV is NOW!)
                city_norm = norm_city_token(current_city)
                coords = CITY_COORDS.get(city_norm) or (SETTLEMENTS_INDEX.get(city_norm) if SETTLEMENTS_INDEX else None)
                if not coords:
                    coords = UKRAINE_ALL_SETTLEMENTS.get(city_norm)
                if not coords:
                    # Try region-aware lookup
                    if region_hdr:
                        oblast_key = region_hdr.replace('щина', 'ська').replace('ь', 'ська')
                        for obl in ['ська', 'ка', 'а', '']:
                            test_key = (city_norm, oblast_key.rstrip('а') + obl if obl else oblast_key)
                            if test_key in UKRAINE_SETTLEMENTS_BY_OBLAST:
                                coords = UKRAINE_SETTLEMENTS_BY_OBLAST[test_key]
                                break
                
                if coords:
                    lat, lng = coords if len(coords) == 2 else (coords[0], coords[1])
                    threat_type, icon = classify(text)
                    label = f"{city_norm.title()} → {target_name.title()}"
                    
                    # Get target coordinates for trajectory
                    target_norm = norm_city_token(target_name)
                    target_coords = CITY_COORDS.get(target_norm) or OBLAST_CENTERS.get(target_norm) or (SETTLEMENTS_INDEX.get(target_norm) if SETTLEMENTS_INDEX else None)
                    if not target_coords:
                        target_coords = UKRAINE_ALL_SETTLEMENTS.get(target_norm)
                    
                    trajectory_data = None
                    if target_coords:
                        target_lat, target_lng = target_coords if len(target_coords) == 2 else (target_coords[0], target_coords[1])
                        trajectory_data = {
                            'start': [lat, lng],
                            'end': [target_lat, target_lng],
                            'target': target_name.title()
                        }
                    
                    course_tracks.append({
                        'id': f"{mid}_city_kursom_{city_norm}", 'place': label, 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'uav_city_kursom', 'count': 1,
                        'trajectory': trajectory_data
                    })
                    add_debug_log(f"Created marker at CITY: {city_norm} ({lat}, {lng}) with trajectory to {target_name}", "uav_course")
                    continue
                else:
                    add_debug_log(f"Could not find coords for city '{city_norm}'", "uav_course")

            # Check for complex pattern "на/через X в напрямку Y" first
            m_complex = pat_complex_napramku.search(ln_low)
            if m_complex:
                count = int(m_complex.group(1)) if m_complex.group(1) else 1
                city1 = m_complex.group(2)  # через це місто
                city2 = m_complex.group(3)  # в напрямку цього міста

                # Process both cities
                for city_raw in [city1, city2]:
                    multi_norm = _resolve_city_candidate(city_raw)
                    base = norm_city_token(multi_norm)
                    
                    # PRIORITY: Try region-specific lookup first if region is known
                    coords = None
                    if region_hdr:
                        region_key = f"{base}_{region_hdr}"
                        coords = CITY_COORDS.get(region_key)
                    
                    # Fallback to base lookup
                    if not coords:
                        coords = CITY_COORDS.get(base) or (SETTLEMENTS_INDEX.get(base) if SETTLEMENTS_INDEX else None)
                    if not coords:
                        try:
                            coords = region_enhanced_coords(base, region_hint_override=region_hdr)
                        except Exception:
                            coords = None
                    # Try OpenCage API if still no coordinates
                    if not coords and GEOCODER_AVAILABLE:
                        try:
                            coords = opencage_geocode(base, region=region_hdr)
                        except Exception:
                            pass
                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(text)
                        for i in range(1, count+1):
                            label = base.title()
                            if count > 1:
                                label += f" ({i}/{count})"
                            if region_hdr and region_hdr not in label.lower():
                                label += f" [{region_hdr.title()}]"
                            course_tracks.append({
                                'id': f"{mid}_complex_{base}_{i}", 'place': label, 'lat': lat, 'lng': lng,
                                'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                                'marker_icon': icon, 'source_match': 'uav_complex', 'count': 1
                            })
                continue  # Skip to next line

            # Check for "від X до Y" pattern (trajectory)
            m_vid_do = pat_vid_do.search(ln_low)
            if m_vid_do:
                count = int(m_vid_do.group(1)) if m_vid_do.group(1) else 1
                city1 = m_vid_do.group(2)  # від цього міста
                city2 = m_vid_do.group(3)  # до цього міста

                # Process both cities
                for city_raw in [city1, city2]:
                    multi_norm = _resolve_city_candidate(city_raw)
                    base = norm_city_token(multi_norm)
                    
                    # PRIORITY: Try region-specific lookup first if region is known
                    coords = None
                    if region_hdr:
                        region_key = f"{base}_{region_hdr}"
                        coords = CITY_COORDS.get(region_key)
                    
                    # Fallback to base lookup
                    if not coords:
                        coords = CITY_COORDS.get(base) or (SETTLEMENTS_INDEX.get(base) if SETTLEMENTS_INDEX else None)
                    if not coords:
                        try:
                            coords = region_enhanced_coords(base, region_hint_override=region_hdr)
                        except Exception:
                            coords = None
                    if not coords and GEOCODER_AVAILABLE:
                        try:
                            coords = opencage_geocode(base, region=region_hdr)
                        except Exception:
                            pass
                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(text)
                        for i in range(1, count+1):
                            label = base.title()
                            if count > 1:
                                label += f" ({i}/{count})"
                            if region_hdr and region_hdr not in label.lower():
                                label += f" [{region_hdr.title()}]"
                            course_tracks.append({
                                'id': f"{mid}_viddo_{base}_{i}", 'place': label, 'lat': lat, 'lng': lng,
                                'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                                'marker_icon': icon, 'source_match': 'uav_vid_do', 'count': 1
                            })
                continue

            # Check for "в напрямку X та Y" pattern (multiple cities)
            m_ta = pat_napramku_ta.search(ln_low)
            if m_ta:
                count = int(m_ta.group(1)) if m_ta.group(1) else 1
                city1 = m_ta.group(2)
                city2 = m_ta.group(3)

                # Process both cities
                for city_raw in [city1, city2]:
                    multi_norm = _resolve_city_candidate(city_raw)
                    base = norm_city_token(multi_norm)
                    
                    # PRIORITY: Try region-specific lookup first if region is known
                    coords = None
                    if region_hdr:
                        region_key = f"{base}_{region_hdr}"
                        coords = CITY_COORDS.get(region_key)
                    
                    # Fallback to base lookup
                    if not coords:
                        coords = CITY_COORDS.get(base) or (SETTLEMENTS_INDEX.get(base) if SETTLEMENTS_INDEX else None)
                    if not coords:
                        try:
                            coords = region_enhanced_coords(base, region_hint_override=region_hdr)
                        except Exception:
                            coords = None
                    if not coords and GEOCODER_AVAILABLE:
                        try:
                            coords = opencage_geocode(base, region=region_hdr)
                        except Exception:
                            pass
                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(text)
                        for i in range(1, count+1):
                            label = base.title()
                            if count > 1:
                                label += f" ({i}/{count})"
                            if region_hdr and region_hdr not in label.lower():
                                label += f" [{region_hdr.title()}]"
                            course_tracks.append({
                                'id': f"{mid}_ta_{base}_{i}", 'place': label, 'lat': lat, 'lng': lng,
                                'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                                'marker_icon': icon, 'source_match': 'uav_ta', 'count': 1
                            })
                continue

            count = None; city = None; approx_flag = False
            m1 = pat_count_course.search(ln_low)
            if m1:
                count = int(m1.group(1)); city = m1.group(2)
            else:
                m2 = pat_area.search(ln_low)
                if m2:
                    if m2.group(1):
                        count = int(m2.group(1))
                    city = m2.group(2)
                else:
                    m3 = pat_napramku.search(ln_low)
                    if m3:
                        if m3.group(1):
                            count = int(m3.group(1))
                        city = m3.group(2)
                    else:
                        m3_sektor = pat_sektor.search(ln_low)
                        if m3_sektor:
                            if m3_sektor.group(1):
                                count = int(m3_sektor.group(1))
                            city = m3_sektor.group(2)
                        else:
                            m4 = pat_course.search(ln_low)
                            if m4:
                                city = m4.group(1)
                            else:
                                m5 = pat_okolytsi.search(ln_low)
                                if m5:
                                    if m5.group(1):
                                        count = int(m5.group(1))
                                    city = m5.group(2)
                                else:
                                    m6 = pat_simple_na.search(ln_low)
                                    if m6:
                                        if m6.group(1):
                                            count = int(m6.group(1))
                                        city = m6.group(2)
                                    else:
                                        m7 = pat_vik.search(ln_low)
                                        if m7:
                                            if m7.group(1):
                                                count = int(m7.group(1))
                                            city = m7.group(2)
            if not city:
                add_debug_log("No city found in UAV line", "uav_course")
                continue
            add_debug_log(f"Found city '{city}' in UAV line", "uav_course")
            multi_norm = _resolve_city_candidate(city)
            base = norm_city_token(multi_norm)
            add_debug_log(f"City normalized to '{base}'", "uav_course")

            # FILTER: Skip oblast/region names (e.g., "БпЛА на Дніпропетровщині" should be regional threat, not city marker)
            oblast_suffixes = ['щина', 'щині', 'область', 'обл']
            if any(base.endswith(suffix) for suffix in oblast_suffixes):
                add_debug_log(f"Skipping oblast name '{base}' - this is a regional threat, not a city target", "uav_course")
                continue

            # PRIORITY: Try region-specific variant first
            coords = None
            if region_hdr:
                # Try variant with region suffix (underscore format used by Nominatim cache)
                region_key = f"{base}_{region_hdr}"
                coords = CITY_COORDS.get(region_key)
                if coords:
                    add_debug_log(f"Found region-specific coordinates for '{region_key}': {coords}", "uav_course")
                else:
                    # Also try old format for backwards compatibility
                    region_variant = f"{base}({region_hdr})"
                    coords = CITY_COORDS.get(region_variant)
                    if coords:
                        add_debug_log(f"Found region-specific coordinates (old format) for '{region_variant}': {coords}", "uav_course")

            # Fallback to base name without region
            if not coords:
                coords = CITY_COORDS.get(base) or (SETTLEMENTS_INDEX.get(base) if SETTLEMENTS_INDEX else None)
                add_debug_log(f"Coordinates lookup for '{base}': {coords}", "uav_course")
            if not coords:
                try:
                    coords = region_enhanced_coords(base, region_hint_override=region_hdr)
                except Exception:
                    coords = None
            # Try OpenCage API if still no coordinates
            if not coords and GEOCODER_AVAILABLE:
                try:
                    coords = opencage_geocode(base, region=region_hdr)
                except Exception:
                    pass
            if not coords:
                # Fallback: if we have a region header, place placeholder near its oblast center with slight jitter
                if region_hdr and region_hdr in OBLAST_CENTERS:
                    rlat, rlng = OBLAST_CENTERS[region_hdr]
                    # deterministic jitter based on hash of city token
                    h = abs(hash(base)) % 1000 / 1000.0
                    lat = max(43.0, min(53.5, rlat + (h - 0.5) * 0.4))
                    lng = max(21.0, min(41.0, rlng + (h - 0.5) * 0.6))
                    coords = (lat, lng)
                    approx_flag = True
                else:
                    # skip THIS city but continue processing other cities
                    add_debug_log(f"Skipping unrecognized city '{base}' - no coordinates and no region context", "uav_course")
                    continue
            # Cache with region key if region is known
            cache_key = f"{base}_{region_hdr}" if region_hdr else base
            if cache_key not in CITY_COORDS:
                CITY_COORDS[cache_key] = coords
            lat, lng = coords
            threat_type, icon = classify(text)
            # Generate individual markers per drone for progressive map loading
            total = count or 1
            for i in range(1, total+1):
                label = base.title()
                if total > 1:
                    label += f" ({i}/{total})"
                if region_hdr and region_hdr not in label.lower():
                    label += f" [{region_hdr.title()}]"
                if approx_flag:
                    label += ' ~'
                course_tracks.append({
                    'id': f"{mid}_c{len(course_tracks)+1}", 'place': label, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'course_city_unit', 'count': 1
                })
                add_debug_log(f"Created course track for '{label}' at {lat}, {lng}", "uav_course")
        add_debug_log(f"Total course tracks generated: {len(course_tracks)}", "uav_course")
        log.debug(f"mid={mid} course_tracks_generated: {len(course_tracks)} tracks")
        if course_tracks:
            return course_tracks
        # Salvage fallback: large multi-line message with many 'бпла курсом' but parser produced nothing
        try:
            ll_full = text.lower()
            if course_tracks == [] and ll_full.count('бпла') >= 5 and ll_full.count('курс') >= 5:
                pat_salv = re.compile(r'(?:\d+\s*[xх×]?\s*)?бпла[^\n]{0,60}?курс(?:ом)?\s+на\s+([a-zа-яіїєґ\-ʼ"“”\'`\s]{3,40})', re.IGNORECASE)
                raw_hits = [m.group(1).strip() for m in pat_salv.finditer(ll_full)]
                uniq = []
                for h in raw_hits:
                    if h and h not in uniq:
                        uniq.append(h)
                salvage_tracks = []
                for idx, token in enumerate(uniq, 1):
                    base_tok = _resolve_city_candidate(token)
                    base_tok = norm_city_token(base_tok)
                    coords = CITY_COORDS.get(base_tok) or (SETTLEMENTS_INDEX.get(base_tok) if SETTLEMENTS_INDEX else None)
                    if not coords:
                        continue
                    lat, lng = coords
                    threat_type, icon = classify(text)
                    salvage_tracks.append({
                        'id': f"{mid}_sf{idx}", 'place': base_tok.title(), 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': token[:120], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'salvage_course_multi'
                    })
                if salvage_tracks:
                    log.debug(f"salvage_course_multi generated {len(salvage_tracks)} tracks mid={mid}")
                    return salvage_tracks
        except Exception as _e_salv:
            log.debug(f'salvage fallback error mid={mid}: {_e_salv}')

    # --- Generic multi-line UAV near-pass counts (e.g. "5х бпла повз Барвінкове") ---
    if 'бпла' in lower and 'повз' in lower and re.search(r'\d+[xх]\s*бпла', lower):
        lines_near = [ln.strip() for ln in lower.split('\n') if ln.strip()]
        near_tracks = []
        pat_near = re.compile(r'(\d+)[xх]\s*бпла[^\n]*?повз\s+([a-zа-яіїєґ\-ʼ\']{3,})')
        for ln in lines_near:
            m = pat_near.search(ln)
            if not m:
                continue
            cnt = int(m.group(1))
            place = (m.group(2) or '').strip("-'ʼ")
            variants = {place}
            if place.endswith('е'): variants.add(place[:-1])
            if place.endswith('ю'):
                variants.add(place[:-1]+'я'); variants.add(place[:-1]+'а')
            if place.endswith('у'):
                variants.add(place[:-1]+'а')
            if place.endswith('ому'):
                variants.add(place[:-3])
            if place.endswith('ове'):
                variants.add(place[:-2]+'’я')  # crude alt
            matched=None; mname=None
            for v in variants:
                if v in CITY_COORDS:
                    matched=CITY_COORDS[v]; mname=v; break
            if not matched and SETTLEMENTS_INDEX:
                for v in variants:
                    if v in SETTLEMENTS_INDEX:
                        matched=SETTLEMENTS_INDEX[v]; mname=v; break
            if not matched:
                # OpenCage fallback
                try:
                    for v in variants:
                        oc = region_enhanced_coords(v)
                        if oc:
                            matched=oc; mname=v; break
                except Exception:
                    matched=None
            if matched:
                if mname not in CITY_COORDS:
                    CITY_COORDS[mname]=matched
                lat,lng = matched
                threat_type, icon = classify(text)
                near_tracks.append({
                    'id': f"{mid}_n{len(near_tracks)+1}", 'place': f"{mname.title()} ({cnt})", 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': ln[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'uav_near_pass', 'count': cnt
                })
        if near_tracks:
            return near_tracks

    # --- Late parenthetical specific settlement fallback (e.g. direction to oblast but (затока)) ---
    if has_threat(original_text.lower()) and '(' in original_text and ')' in original_text:
        p_tokens = re.findall(r'\(([A-Za-zА-Яа-яЇїІіЄєҐґ\-\s]{3,})\)', original_text.lower())
        if p_tokens:
            cand = p_tokens[-1].strip()
            cand = re.sub(r'^(смт|с\.|м\.|місто|селище)\s+','', cand)
            base_cand = UA_CITY_NORMALIZE.get(cand, cand)
            coords = CITY_COORDS.get(base_cand) or SETTLEMENTS_INDEX.get(base_cand)
            log.debug(f"late_parenthetical mid={mid} cand={cand} base={base_cand} found={bool(coords)}")
            if coords:
                lat,lng = coords
                threat_type, icon = classify(original_text)
                return [{
                    'id': str(mid), 'place': base_cand.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': original_text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'late_parenthetical'
                }]

    # --- Settlement matching using external dataset (if provided) (single first match) ---
    if not region_hits:
        # 1) Multi-list form: "Новгород-сіверський, Шостка, Короп, Кролевець - уважно по БПЛА"
        # support both hyphen - and en dash – between list and tail
        dash_idx = None
        for dch in [' - ', ' – ', '- ', '– ']:
            if dch in lower:
                dash_idx = lower.index(dch)
                break
        if ('уважно' in lower or 'по бпла' in lower or 'бпла' in lower) and (',' in lower) and dash_idx is not None:
            left = lower[:dash_idx]
            right = lower[dash_idx+1:]
            if any(k in right for k in ['бпла','дрон','шахед','uav']):
                raw_places = [p.strip() for p in left.split(',') if p.strip()]
                tracks = []
                threat_type, icon = classify(text)
                seen = set()
                for idx, rp in enumerate(raw_places,1):
                    key = rp.replace('й,','й').strip()
                    coords = region_enhanced_coords(key)
                    if coords and key not in seen:
                        seen.add(key)
                        lat,lng = coords
                        tracks.append({
                            'id': f"{mid}_m{idx}", 'place': key.title(), 'lat': lat, 'lng': lng,
                            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'multi_settlement'
                        })
                if tracks:
                    return tracks
        # 2) Single settlement search (fallback) with word-boundary and specificity prioritization
        if SETTLEMENTS_INDEX:
            cand_hits = []
            text_len = len(lower)
            for name in SETTLEMENTS_ORDERED:
                start = 0
                while True:
                    idx = lower.find(name, start)
                    if idx == -1:
                        break
                    before_ok = (idx == 0) or not lower[idx-1].isalnum()
                    after_idx = idx + len(name)
                    after_ok = (after_idx == text_len) or not lower[after_idx].isalnum()
                    if before_ok and after_ok:
                        cand_hits.append(name)
                        break  # only need first occurrence
                    start = idx + 1
            if cand_hits:
                # Prefer longer names; deprioritize generic oblast centers when more specific present
                def score(n: str):
                    base_penalty = -5 if n in ['суми'] and len(cand_hits) > 1 else 0
                    return (len(n) + base_penalty)
                cand_hits.sort(key=score, reverse=True)
                chosen = cand_hits[0]
                lat, lng = SETTLEMENTS_INDEX[chosen]
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': chosen.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon,
                    'source_match': 'settlement'
                }]

    # --- Raion (district) detection ---
    # Ищем конструкции вида "Покровський район", а также множественные "Конотопський та Сумський районы".
    def norm_raion(token: str):
        t = token.lower().strip('- ')
        # унификация дефисов
        t = t.replace('–','-')
        # морфологические окончания -> базовая форма -ський
        t = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$','ський', t)
        return t
    raion_matches = []
    # множественное 'райони'
    plural_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё,\-\s]{4,}?)райони', re.IGNORECASE)
    for pm in plural_pattern.finditer(text):
        segment = pm.group(1)
        # разделяем по 'та' или запятым
        parts = re.split(r'\s+та\s+|,', segment)
        for p in parts:
            cand = p.strip()
            if not cand:
                continue
            # берём последнее слово (Конотопський)
            last = cand.split()[-1]
            base = norm_raion(last)
            if base in RAION_FALLBACK:
                raion_matches.append((base, RAION_FALLBACK[base]))
    # одиночное 'район' (любой падеж: район, району, районом, района)
    raion_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё\-]{4,})\s+район(?:у|ом|а)?', re.IGNORECASE)
    for m_r in raion_pattern.finditer(text):
        base = norm_raion(m_r.group(1))
        if base in RAION_FALLBACK:
            raion_matches.append((base, RAION_FALLBACK[base]))
    # Аббревиатура "р-н" (у т.ч. варианты "р-н.", "рн", "р-н," )
    raion_abbrev_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё\-]{4,})\s+р\s*[-–]?\s*н\.?', re.IGNORECASE)
    for m_ra in raion_abbrev_pattern.finditer(text):
        base = norm_raion(m_ra.group(1))
        if base in RAION_FALLBACK:
            raion_matches.append((base, RAION_FALLBACK[base]))
    if raion_matches:
        threat_type, icon = classify(text)
        tracks = []
        seen = set()
        for idx,(name,(lat,lng)) in enumerate(raion_matches,1):
            # For some districts, show the main city name instead of district name
            district_to_city_mapping = {
                'павлоградський': 'Павлоград',
                'білоцерківський': 'Біла Церква',
                'кременчуцький': 'Кременчук',
                'миколаївський': 'Миколаїв',
                'дніпровський': 'Дніпро'
            }

            if name.lower() in district_to_city_mapping:
                title = district_to_city_mapping[name.lower()]
            else:
                title = f"{name.title()} район"
            if title in seen: continue
            seen.add(title)
            # Maintain alarm overlay state
            if threat_type == 'alarm':
                RAION_ALARMS[name] = {'place': title, 'lat': lat, 'lng': lng, 'since': time.time()}
            elif threat_type == 'alarm_cancel':
                RAION_ALARMS.pop(name, None)
            tracks.append({
                'id': f"{mid}_d{idx}", 'place': title, 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'raion'
            })
        if tracks:
            log.debug(f"RAION_MATCH mid={mid} -> {[t['place'] for t in tracks]}")
            return tracks

    # --- Hromada detection (e.g., "Хотінська територіальна громада") ---
    hromada_pattern = re.compile(r'([А-ЯA-ZЇІЄҐЁа-яa-zїієґё\-]{4,})\s+територіал(?:ьна|ьної)?\s+громада', re.IGNORECASE)
    hromada_matches = []
    for m_h in hromada_pattern.finditer(text):
        token = m_h.group(1).lower()
        # normalize adjective endings to 'ська'
        base = re.sub(r'(ської|ской|ська|ской)$', 'ська', token)
        if base in HROMADA_FALLBACK:
            hromada_matches.append((base, HROMADA_FALLBACK[base]))
    if hromada_matches:
        threat_type, icon = classify(text)
        tracks = []
        seen = set()
        for idx,(name,(lat,lng)) in enumerate(hromada_matches,1):
            title = f"{name.title()} територіальна громада"
            if title in seen: continue
            seen.add(title)
            tracks.append({
                'id': f"{mid}_h{idx}", 'place': title, 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'source_match': 'hromada'
            })
        if tracks:
            return tracks

    # --- Slash separated settlements PRIORITY (moved earlier so it can't be overridden by region logic) ---
    lower_full_for_slash = text.lower()
    if '/' in lower_full_for_slash and ('бпла' in lower_full_for_slash or 'дрон' in lower_full_for_slash) and any(x in lower_full_for_slash for x in ['х бпла','x бпла',' бпла']):
        # take portion before first dash (— or -) which usually separates counts/other text
        left_part = re.split(r'[—-]', lower_full_for_slash, 1)[0]
        # Remove trailing count token like "5х бпла" from left part to isolate pure settlements
        left_part = re.sub(r'\b\d+[xх]\s*бпла.*$', '', left_part).strip()
        parts = [p.strip() for p in re.split(r'/|\\', left_part) if p.strip()]
        found = []
        # Derive a region stem from any well-known city token to bias geocoding of other parts
        inferred_region = None
        for p in parts:
            base_inf = UA_CITY_NORMALIZE.get(p, p)
            if base_inf in CITY_TO_OBLAST:
                inferred_region = CITY_TO_OBLAST[base_inf]
                break
        for p in parts:
            base = UA_CITY_NORMALIZE.get(p, p)
            coords = CITY_COORDS.get(base)
            if not coords and SETTLEMENTS_INDEX:
                coords = SETTLEMENTS_INDEX.get(base)
            if not coords:
                # If we have inferred region stem, attempt region-qualified geocode first
                if inferred_region and OPENCAGE_API_KEY:
                    oblast_variants = [
                        f"{base} {inferred_region}щина",
                        f"{base} {inferred_region}ська область",
                        f"{base} {inferred_region}ская область"
                    ]
                    for q in oblast_variants:
                        try:
                            coords = geocode_opencage(q)
                            if coords:
                                break
                        except Exception:
                            pass
                if not coords:
                    try:
                        coords = region_enhanced_coords(base)
                    except Exception:
                        coords = None
            if coords:
                found.append((base.title(), coords))
        if found:
            threat_type, icon = classify(text)
            tracks = []
            for idx,(nm,(lat,lng)) in enumerate(found,1):
                if 'курс захід' in lower_full_for_slash:
                    lng -= 0.4
                tracks.append({
                    'id': f"{mid}_s{idx}", 'place': nm, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'slash_combo', 'count': drone_count
                })
            if tracks:
                try:
                    log.debug(f"SLASH_COMBO mid={mid} parts={parts} tracks={[(t['place'], t['lat'], t['lng']) for t in tracks]}")
                except Exception:
                    pass
            if tracks:
                return tracks

    # --- Black Sea aquatory: place marker in sea, not on target city (e.g. "в акваторії чорного моря, курсом на одесу" or "з моря на Ізмаїл") ---
    lower_sea = text.lower()
    is_black_sea = (('акватор' in lower_sea or 'акваторії' in lower_sea) and ('чорного моря' in lower_sea or 'чорне море' in lower_sea or 'чорному морі' in lower_sea)) or \
                   ('з моря' in lower_sea and ('курс' in lower_sea or 'на ' in lower_sea)) or \
                   ('з чорного моря' in lower_sea)

    if is_black_sea:
        # Extract target region/direction if mentioned
        m_target = re.search(r'курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower_sea)
        m_direction = re.search(r'на\s+(північ|південь|схід|захід|північний\s+схід|північний\s+захід|південний\s+схід|південний\s+захід)', lower_sea)
        m_region = re.search(r'(одещин|одеськ|миколаїв|херсон)', lower_sea)

        target_info = None
        sea_lat, sea_lng = 45.3, 30.7  # Default: northern Black Sea central coords

        # Adjust position based on direction/region
        if m_direction:
            direction = m_direction.group(1)
            if 'південь' in direction:
                sea_lat = 45.0  # Further south
            elif 'північ' in direction:
                sea_lat = 45.6  # Further north
            if 'схід' in direction:
                sea_lng = 31.2  # Further east
            elif 'захід' in direction:
                sea_lng = 30.2  # Further west

        if m_region:
            region_name = m_region.group(1)
            if 'одещин' in region_name or 'одеськ' in region_name:
                # South of Odesa region - in the sea 50km offshore
                sea_lat, sea_lng = 45.7, 30.7
                target_info = 'Одещини'
            elif 'миколаїв' in region_name:
                sea_lat, sea_lng = 45.9, 31.4
                target_info = 'Миколаївщини'
            elif 'херсон' in region_name:
                sea_lat, sea_lng = 45.7, 32.5
                target_info = 'Херсонщини'

        if m_target:
            tc = m_target.group(1).lower()
            tc = UA_CITY_NORMALIZE.get(tc, tc)
            target_info = tc.title()

        threat_type, icon = classify(text)
        place_label = 'Акваторія Чорного моря'
        if target_info:
            place_label += f' (на {target_info})'

        # Try to find target city coordinates for trajectory
        target_coords = None
        if m_target:
            tc_normalized = m_target.group(1).lower()
            tc_normalized = UA_CITY_NORMALIZE.get(tc_normalized, tc_normalized)
            if tc_normalized in CITY_COORDS:
                target_coords = CITY_COORDS[tc_normalized]

        result = {
            'id': str(mid), 'place': place_label, 'lat': sea_lat, 'lng': sea_lng,
            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': icon, 'source_match': 'black_sea_course'
        }

        # Add trajectory data if we have target coordinates
        if target_coords:
            result['trajectory'] = {
                'start': [sea_lat, sea_lng],
                'end': list(target_coords),
                'target': target_info
            }

        return [result]

    # --- Bilhorod-Dnistrovskyi coastal UAV patrol ("вздовж узбережжя Білгород-Дністровського району") ---
    if (('узбереж' in lower_sea or 'вздовж узбереж' in lower_sea) and
        ('білгород-дністровського' in lower_sea or 'белгород-днестровского' in lower_sea) and
        ('бпла' in lower_sea or 'дрон' in lower_sea)):
        # Base approximate city coordinate; push 0.22° south into sea
        city_lat, city_lng = 46.186, 30.345
        lat = city_lat - 0.22
        lng = city_lng
        threat_type, icon = classify(text)
        return [{
            'id': str(mid), 'place': 'Узбережжя Білгород-Дністровського р-ну', 'lat': lat, 'lng': lng,
            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
            'marker_icon': icon, 'source_match': 'bilhorod_dnistrovskyi_coast'
        }]

    # --- "повз <city>" (passing near) with optional direction target "у напрямку <city>" ---
    lower_pass = text.lower()
    pass_near_detected = False
    if 'повз ' in lower_pass and ('бпла' in lower_pass or 'дрон' in lower_pass):
        pass_match = re.search(r"повз\s+([A-Za-zА-Яа-яЇїІіЄєҐґ'’ʼ`\-]{3,})", lower_pass)
        dir_match = re.search(r"напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ'’ʼ`\-]{3,})(?:\s+([A-Za-zА-Яа-яЇїІіЄєҐґ'’ʼ`\-]{3,}))?", lower_pass)
        places = []
        def norm_c(s: str):
            if not s: return None
            s = s.strip().lower().strip(".,:;()!?")
            s = UA_CITY_NORMALIZE.get(s, s)
            # Morphological heuristics: convert common Ukrainian/Russian case endings to nominative
            candidates = [s]
            if s.endswith('у') and len(s) > 4:
                candidates.append(s[:-1] + 'а')
            if s.endswith('ю') and len(s) > 4:
                candidates.append(s[:-1] + 'я')
            if s.endswith('и') and len(s) > 4:
                candidates.append(s[:-1] + 'а')
            if s.endswith('ої') and len(s) > 5:
                candidates.append(s[:-2] + 'а')
            if s.endswith('оїї') and len(s) > 6:
                candidates.append(s[:-3] + 'а')
            for cand in candidates:
                if region_enhanced_coords(cand):
                    return cand
            return s
        if pass_match:
            c1 = norm_c(pass_match.group(1))
            if c1:
                coords1 = region_enhanced_coords(c1)
                if coords1:
                    places.append((c1.title(), coords1, 'pass_near'))
        if dir_match:
            c2_first = norm_c(dir_match.group(1))
            c2_second_raw = dir_match.group(2)
            full_phrase = None
            if c2_first and c2_second_raw:
                c2_second = norm_c(c2_second_raw)
                cand_phrase = f"{c2_first} {c2_second}".strip()
                if cand_phrase in CITY_COORDS or (SETTLEMENTS_INDEX and cand_phrase in SETTLEMENTS_INDEX):
                    full_phrase = cand_phrase
            c2_key = full_phrase or c2_first
            if c2_key and c2_key != (places[0][0].lower() if places else None):
                coords2 = region_enhanced_coords(c2_key)
                if coords2:
                    places.append((c2_key.title(), coords2, 'direction_target'))
        if places:
            threat_type, icon = classify(text)
            out_tracks = []
            for idx,(nm,(lat,lng),tag) in enumerate(places,1):
                out_tracks.append({
                    'id': f"{mid}_pv{idx}", 'place': nm, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str,
                    'channel': channel, 'marker_icon': icon, 'source_match': tag, 'count': drone_count
                })
            if out_tracks:
                pass_near_detected = True
                return out_tracks

    # --- Pattern: "рухалися на <city1>, змінили курс на <city2>" ---
    lower_course_change = text.lower()
    if 'змінили курс на' in lower_course_change and ('рухал' in lower_course_change or 'рухались' in lower_course_change or 'рухалися' in lower_course_change):
        m_to = re.search(r'змінили\s+курс\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower_course_change)
        m_from = re.search(r'рухал(?:ися|ись|и|ась)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', lower_course_change)
        places = []
        def norm_simple(s):
            if not s: return None
            s = s.strip().lower().strip(".,:;()!")
            return UA_CITY_NORMALIZE.get(s, s)
        if m_from:
            c_from = norm_simple(m_from.group(1))
            coords_from = region_enhanced_coords(c_from)
            if coords_from:
                places.append((c_from.title(), coords_from, 'course_from'))
        if m_to:
            c_to = norm_simple(m_to.group(1))
            coords_to = region_enhanced_coords(c_to)
            if coords_to:
                # avoid duplicate if same
                if not any(p[0].lower()==c_to for p in places):
                    places.append((c_to.title(), coords_to, 'course_changed_to'))
        if places:
            threat_type, icon = classify(text)
            out = []
            for idx,(name,(lat,lng),tag) in enumerate(places,1):
                out.append({
                    'id': f"{mid}_cc{idx}", 'place': name, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': tag
                })
            if out:
                return out

    # --- Relative direction near a city: "північніше кам'янського у напрямку кременчука" ---
    rel_dir_lower = text.lower()
    if any(k in rel_dir_lower for k in ['північніше','південніше','східніше','західніше']) and ('бпла' in rel_dir_lower or 'дрон' in rel_dir_lower):
        # Allow letters plus apostrophes/hyphen
        m_rel = re.search(r"(північніше|південніше|східніше|західніше)\s+([A-Za-zА-Яа-яЇїІіЄєҐґ'`’ʼ\-]{4,})", rel_dir_lower)
        target_dir = re.search(r'напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})', rel_dir_lower)
        if m_rel:
            dir_word = m_rel.group(1)
            raw_city = m_rel.group(2).strip(".,:;()!?")
            def norm_rel_city(s):
                s = s.lower()
                # нормализация окончаний родительного падежа '-ського' -> 'ське'
                if s.endswith('ського'):
                    s = s[:-6] + 'ське'
                if s.endswith('ого') and len(s) > 5:
                    s = s[:-3] + 'о'
                return UA_CITY_NORMALIZE.get(s, s)
            base_city = norm_rel_city(raw_city)
            coords_base = region_enhanced_coords(base_city)
            coords_target = None
            target_name = None
            if target_dir:
                tn = target_dir.group(1).lower().strip('.:,;()!?')
                tn = UA_CITY_NORMALIZE.get(tn, tn)
                coords_target = region_enhanced_coords(tn)
                target_name = tn
            if coords_base:
                lat_b, lng_b = coords_base
                # offset ~0.35 deg lat/long depending on direction
                lat_off, lng_off = 0,0
                if 'північ' in dir_word: lat_off = 0.35
                elif 'півден' in dir_word: lat_off = -0.35
                elif 'східн' in dir_word: lng_off = 0.55
                elif 'західн' in dir_word: lng_off = -0.55
                rel_lat, rel_lng = lat_b + lat_off, lng_b + lng_off
                threat_type, icon = classify(text)
                tracks = [{
                    'id': f"{mid}_rel1", 'place': base_city.title(), 'lat': rel_lat, 'lng': rel_lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'relative_dir'
                }]
                if coords_target:
                    tracks.append({
                        'id': f"{mid}_rel2", 'place': target_name.title(), 'lat': coords_target[0], 'lng': coords_target[1],
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'direction_target'
                    })
                return tracks

    # --- Parenthetical course city e.g. "курс західний (кременчук)" ---
    if 'курс' in lower and '(' in lower and ')' in lower and ('бпла' in lower or 'дрон' in lower):
        m_par = re.search(r'курс[^()]{0,30}\(([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})\)', lower)
        if m_par:
            pc = m_par.group(1).lower()
            pc = UA_CITY_NORMALIZE.get(pc, pc)
            coords = region_enhanced_coords(pc)
            if coords:
                threat_type, icon = classify(text)
                return [{
                    'id': f"{mid}_pc", 'place': pc.title(), 'lat': coords[0], 'lng': coords[1],
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'course_parenthetical'
                }]

    # --- Comma separated settlements followed by threat keyword (e.g. "Обухівка, Курилівка, Петриківка увага БПЛА") ---
    lower_commas = text.lower()
    if 'бпла' in lower_commas and ',' in lower_commas:
        # Identify first threat keyword position
        threat_kw_idx = None
        for kw in ['увага','проліт','пролёт','уважно','уважно.','уважно,']:
            pos = lower_commas.find(kw)
            if pos != -1:
                threat_kw_idx = pos
                break
        if threat_kw_idx is not None:
            left_seg = lower_commas[:threat_kw_idx]
            # quick guard to ensure segment not too long
            if 3 <= len(left_seg) <= 180:
                cand_parts = [p.strip() for p in left_seg.split(',') if p.strip()]
                found = []
                for cand in cand_parts:
                    # normalize basic endings (remove trailing punctuation)
                    base = cand.strip(" .!?:;()[]'`’ʼ")
                    if len(base) < 3:
                        continue
                    norm = UA_CITY_NORMALIZE.get(base, base)
                    coords = region_enhanced_coords(norm)
                    if coords:
                        found.append((norm.title(), coords))
                if found:
                    threat_type, icon = classify(text)
                    tracks = []
                    seenp = set()
                    for idx,(nm,(lat,lng)) in enumerate(found,1):
                        if nm in seenp: continue
                        seenp.add(nm)
                        tracks.append({
                            'id': f"{mid}_m{idx}", 'place': nm, 'lat': lat, 'lng': lng,
                            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'multi_settlement_comma', 'count': drone_count
                        })
                    if tracks:
                        return tracks

    # --- PRIORITY: Direction patterns (у напрямку, через, повз) - BEFORE region boundary logic ---
    try:
        import re as _re_direction

        if has_threat(text) and any(pattern in text.lower() for pattern in ['у напрямку', 'через', 'повз']):
            direction_targets = []

            # Pattern 1: "у напрямку [city], [oblast]"
            naprym_pattern = r'у\s+напрямку\s+([А-Яа-яЇїІіЄєҐґ\'\-\s]+?)(?:\s*,\s*([А-Яа-яЇїІіЄєҐґ\'\-\s]*області?))?(?:[\.\,\!\?;]|$)'
            naprym_matches = _re_direction.findall(naprym_pattern, text, _re_direction.IGNORECASE)
            for city_raw, oblast_raw in naprym_matches:
                direction_targets.append(('у напрямку', city_raw.strip(), oblast_raw.strip() if oblast_raw else ''))

            # Process direction targets
            for direction_type, city_raw, oblast_raw in direction_targets:
                if direction_type == 'у напрямку':
                    city_norm = city_raw.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                    city_norm = re.sub(r'\s+',' ', city_norm).strip()

                    # Try exact lookup
                    coords = CITY_COORDS.get(city_norm)
                    if not coords:
                        # Try normalized lookup
                        city_base = UA_CITY_NORMALIZE.get(city_norm, city_norm)
                        coords = CITY_COORDS.get(city_base)

                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(text)

                        # Extract drone count
                        import re as _re_count
                        count_match = _re_count.search(r'(\d+)\s*[хx]?\s*(?:бпла|дрон|шахед)', text.lower())
                        drone_count = int(count_match.group(1)) if count_match else 1

                        add_debug_log(f"PRIORITY: Direction target found - {city_norm} -> {coords}", "direction_priority")
                        return [{
                            'id': str(mid), 'place': city_raw.title(), 'lat': lat, 'lng': lng,
                            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'direction_target_priority', 'count': drone_count
                        }]
                    else:
                        add_debug_log(f"PRIORITY: Direction target not found - {city_norm}", "direction_priority")
    except Exception as e:
        add_debug_log(f"Direction priority processing error: {e}", "direction_priority")

    # PRIORITY: Various Shahed patterns - Process before region boundary logic
    try:
        import re as _re_shahed
        all_shahed_tracks = []

        # Pattern 1: "N шахедів біля [city]" or "N шахедів біля [city1]/[city2]"
        bilya_pattern = r'(\d+)\s+шахед[а-яіїєёыийї]*\s+біля\s+([А-Яа-яЏїІіЄєҐґ\'\-\s\/]+?)(?:\s+та\s+район)?(?:\s+на\s+[А-Яа-яЇїІіЄєҐґ\'\-\s]+)?(?:[\.\,\!\?;]|$)'
        bilya_matches = _re_shahed.findall(bilya_pattern, text, _re_shahed.IGNORECASE)

        # Pattern 2: "N шахед на [city]"
        na_pattern = r'(\d+)\s+шахед[а-яіїєёыийї]*\s+на\s+([А-Яа-яЇїІіЄєҐґ\'\-\s]+?)(?:[\.\,\!\?;]|$)'
        na_matches = _re_shahed.findall(na_pattern, text, _re_shahed.IGNORECASE)

        # Pattern 3: "N шахедів з боку [city]"
        z_boku_pattern = r'(\d+)\s+шахед[а-яіїєёыийї]*\s+з\s+боку\s+([А-Яа-яЇїІіЄєҐґ\'\-\s]+?)(?:[\.\,\!\?;]|$)'
        z_boku_matches = _re_shahed.findall(z_boku_pattern, text, _re_shahed.IGNORECASE)

        # Pattern 4: "N шахедів через [city1]/[city2]" - multiple cities
        cherez_multi_pattern = r'(\d+)\s+шахед[а-яіїєёыийї]*\s+через\s+([А-Яа-яЇїІіЄєҐґ\'\-\s\/]+?)(?:\s+район)?(?:\s+на\s+[А-Яа-яЇїІіЄєҐґ\'\-\s]+)?(?:[\.\,\!\?;]|$)'
        cherez_matches = _re_shahed.findall(cherez_multi_pattern, text, _re_shahed.IGNORECASE)

        all_patterns = [
            (bilya_matches, 'bilya'),
            (na_matches, 'na'),
            (z_boku_matches, 'z_boku'),
            (cherez_matches, 'cherez')
        ]

        for matches, pattern_type in all_patterns:
            for count_str, city_raw in matches:
                # Handle multiple cities separated by /
                cities = [c.strip() for c in city_raw.split('/')]

                for city_part in cities:
                    city_norm = city_part.lower().replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
                    city_norm = re.sub(r'\s+',' ', city_norm).strip()

                    # Special handling for "[city] на [region]" patterns
                    region_match = re.match(r'^(.+?)\s+на\s+([а-яіїє]+щині?|[а-яіїє]+ській?\s+обл?\.?|[а-яіїє]+ській?\s+області?)$', city_norm)
                    if region_match:
                        city_norm = region_match.group(1).strip()
                        region_hint = region_match.group(2).strip()
                        # Use full message context for resolution
                        coords = ensure_city_coords_with_message_context(city_norm, text)
                        if coords:
                            lat, lng, approx = coords
                            add_debug_log(f"SHAHED: Regional pattern found - {city_norm} на {region_hint} -> ({lat}, {lng})", "shahed_regional")

                            result_entry = {
                                'id': f"{mid}_sha_{len(threats)+1}",
                                'place': f"{city_part.title()}",
                                'lat': lat, 'lng': lng,
                                'type': 'shahed', 'count': int(count_str),
                                'timestamp': date_str, 'channel': channel
                            }
                            threats.append(result_entry)
                            continue  # Skip regular processing for this city

                    # Apply normalization rules for accusative/genitive cases
                    original_norm = city_norm
                    if city_norm in UA_CITY_NORMALIZE:
                        city_norm = UA_CITY_NORMALIZE[city_norm]

                    # Try accusative endings for cities like "миколаєва" -> "миколаїв", "полтави" -> "полтава"
                    if not (city_norm in CITY_COORDS or region_enhanced_coords(city_norm)):
                        # Try various ending transformations
                        variants = [city_norm]
                        if city_norm.endswith('а'):
                            variants.extend([city_norm[:-1] + 'ів', city_norm[:-1] + 'і'])
                        elif city_norm.endswith('и'):
                            variants.extend([city_norm[:-1] + 'а', city_norm[:-1] + 'я'])
                        elif city_norm.endswith('у'):
                            variants.extend([city_norm[:-1] + 'п', city_norm[:-1] + 'к'])

                        for variant in variants:
                            if variant in CITY_COORDS or region_enhanced_coords(variant):
                                city_norm = variant
                                break

                    # Try to get coordinates
                    coords = region_enhanced_coords(city_norm)
                    if not coords:
                        context_result = ensure_city_coords_with_message_context(city_norm, text)
                        if context_result:
                            coords = context_result[:2]  # Take only lat, lng

                    if coords:
                        lat, lng = coords
                        threat_type, icon = classify(text)
                        count = int(count_str) if count_str.isdigit() else 1

                        # Create multiple tracks for multiple drones
                        tracks_to_create = max(1, count)
                        for i in range(tracks_to_create):
                            track_label = city_part.title()
                            if tracks_to_create > 1:
                                track_label += f" #{i+1}"

                            # Add small coordinate offsets to prevent marker overlap
                            marker_lat = lat
                            marker_lng = lng
                            if tracks_to_create > 1:
                                # Create a chain pattern - drones one after another
                                offset_distance = 0.03  # ~3km offset between each drone
                                marker_lat += offset_distance * i
                                marker_lng += offset_distance * i * 0.5

                            all_shahed_tracks.append({
                                'id': f"{mid}_{pattern_type}_{len(all_shahed_tracks)}",
                                'place': track_label,
                                'lat': marker_lat,
                                'lng': marker_lng,
                                'threat_type': threat_type,
                                'text': text[:500],
                                'date': date_str,
                                'channel': channel,
                                'marker_icon': icon,
                                'source_match': f'{pattern_type}_shahed_priority',
                                'count': 1
                            })
                        add_debug_log(f"SHAHED {pattern_type.upper()}: {city_norm} ({count}x) -> {coords}", f"shahed_{pattern_type}")

        if all_shahed_tracks:
            return all_shahed_tracks
    except Exception as e:
        add_debug_log(f"Shahed patterns processing error: {e}", "shahed_priority")

    # Region boundary logic (fallback single or midpoint for exactly two)
    matched_regions = []
    for name, coords in OBLAST_CENTERS.items():
        if name in lower:
            matched_regions.append((name, coords))
    if matched_regions:
        # НОВОЕ: Проверка контекстного геокодинга перед региональными маркерами
        if CONTEXT_GEOCODER_AVAILABLE:
            context_result = get_coordinates_context_aware(text)
            if context_result:
                lat, lng, target_city = context_result
                threat_type, icon = classify(text)

                print(f"DEBUG Context-aware geocoding: Found primary target '{target_city}' at ({lat}, {lng})")

                return [{
                    'id': str(mid), 'place': target_city.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'context_aware_geocoding', 'count': 1
                }]

        # Если только области упомянуты и нет ключей угроз, пропускаем.
        # Дополнительная защита: иногда в messages.json могли сохраниться старые записи без угроз.
        if not has_threat(text):
            # чистый список областей? (только названия + двоеточия/пробелы/переводы строк)
            stripped = re.sub(r'[\s:]+', ' ', text.lower()).strip()
            only_regions = all(rn in OBLAST_CENTERS for rn in stripped.split() if rn)
            if only_regions or len(text) < 120:
                return None
        # --- Направления внутри области (північно-західний / південно-західний и т.п.) ---
        def detect_direction(lower_txt: str):
            # Support full adjectives with endings (-ний / -ня / -ньому) by searching stems
            if 'північно-захід' in lower_txt or 'північно-західн' in lower_txt: return 'nw'
            if 'південно-захід' in lower_txt or 'південно-західн' in lower_txt: return 'sw'
            if 'північно-схід' in lower_txt or 'північно-східн' in lower_txt: return 'ne'
            if 'південно-схід' in lower_txt or 'південно-східн' in lower_txt: return 'se'
            # Single directions (allow stems 'північн', 'південн')
            if re.search(r'\bпівніч(?!о-с)(?:н\w*)?\b', lower_txt): return 'n'
            if re.search(r'\bпівденн?\w*\b', lower_txt): return 's'
            if re.search(r'\bсхідн?\w*\b', lower_txt): return 'e'
            if re.search(r'\bзахідн?\w*\b', lower_txt): return 'w'
            return None
        direction_code = None
    if len(matched_regions) == 1 and not raion_matches and not pass_near_detected:
            direction_code = detect_direction(lower)
            # If message also contains course info referencing cities/slash – skip region-level marker to allow city parsing later
            course_words = (' курс ' in lower or lower.startswith('курс '))
            # Treat city present only if it appears as a standalone word (to avoid 'дніпро' inside 'дніпропетровщини')
            has_city_token = False
            try:
                import re as _re_ct
                for c_name in CITY_COORDS.keys():
                    if _re_ct.search(r'\b'+_re_ct.escape(c_name)+r'\b', lower):
                        has_city_token = True; break
            except Exception:
                has_city_token = any(c in lower for c in CITY_COORDS.keys())
            has_slash_combo = '/' in lower
            if direction_code and not (course_words and (has_city_token or has_slash_combo)):
                # ---- Special: sector course pattern inside region directional message ----
                # e.g. "курс(ом) в бік сектору перещепине - губиниха"
                sector_match = re.search(r'курс(?:ом)?\s+в\s+бік\s+сектору\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})(?:\s*[-–]\s*([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,}))?', lower)
                if sector_match:
                    c1 = sector_match.group(1)
                    c2 = sector_match.group(2)
                    def norm_city(n):
                        if not n: return None
                        n = n.strip().lower()
                        n = re.sub(r'["`ʼ’\'.,:;()]+', '', n)
                        return UA_CITY_NORMALIZE.get(n, n)
                    c1n = norm_city(c1)
                    c2n = norm_city(c2) if c2 else None
                    coords1 = CITY_COORDS.get(c1n) or (SETTLEMENTS_INDEX.get(c1n) if SETTLEMENTS_INDEX else None)
                    coords2 = CITY_COORDS.get(c2n) or (SETTLEMENTS_INDEX.get(c2n) if (c2n and SETTLEMENTS_INDEX) else None)
                    if coords1 or coords2:
                        if coords1 and coords2:
                            lat_o = (coords1[0]+coords2[0])/2
                            lng_o = (coords1[1]+coords2[1])/2
                            place_label = f"{c1n.title()} - {c2n.title()} (сектор)"
                        else:
                            (lat_o,lng_o) = coords1 or coords2
                            place_label = (c1n or c2n).title()
                        threat_type, icon = classify(text)
                        return [{
                            'id': str(mid), 'place': place_label, 'lat': lat_o, 'lng': lng_o,
                            'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                            'marker_icon': icon, 'source_match': 'course_sector', 'count': drone_count
                        }]
                (reg_name, (base_lat, base_lng)) = matched_regions[0]

                # Define offset function for coordinate calculations
                def offset(lat, lng, code):
                    # Уменьшенные дельты для более точного позиционирования в пределах области
                    # (широта ~111 км, долгота * cos(lat))
                    import math
                    lat_step = 0.35  # Примерно 35-40 км вместо 60 км
                    lng_step = 0.55 / max(0.2, abs(math.cos(math.radians(lat))))  # Примерно 35-40 км
                    if code == 'n': return lat+lat_step, lng
                    if code == 's': return lat-lat_step, lng
                    if code == 'e': return lat, lng+lng_step
                    if code == 'w': return lat, lng-lng_step
                    # диагонали немного меньше по каждой оси
                    lat_diag = lat_step * 0.8
                    lng_diag = lng_step * 0.8
                    if code == 'ne': return lat+lat_diag, lng+lng_diag
                    if code == 'nw': return lat+lat_diag, lng-lng_diag
                    if code == 'se': return lat-lat_diag, lng+lng_diag
                    if code == 'sw': return lat-lat_diag, lng-lng_diag
                    return lat, lng

                # SPECIAL: Handle messages with start position + course direction
                # e.g. "на півночі тернопільщини ➡️ курсом на південно-західний напрямок"
                start_direction = None
                course_direction = None

                # Detect start position (на півночі/півдні/сході/заході)
                if re.search(r'\bна\s+півночі\b', lower) or re.search(r'\bпівнічн\w+\s+частин\w*\b', lower):
                    start_direction = 'n'
                elif re.search(r'\bна\s+півдні\b', lower) or re.search(r'\bпівденн\w+\s+частин\w*\b', lower):
                    start_direction = 's'
                elif re.search(r'\bна\s+сході\b', lower) or re.search(r'\bсхідн\w+\s+частин\w*\b', lower):
                    start_direction = 'e'
                elif re.search(r'\bна\s+заході\b', lower) or re.search(r'\bзахідн\w+\s+частин\w*\b', lower):
                    start_direction = 'w'

                # Detect course direction (курсом на направление)
                # Support patterns: "курсом на", "рух на", "продовжує рух на", "прямують на", "в напрямку"
                has_direction_keyword = ('курс' in lower and 'напрямок' in lower) or ('➡' in lower or '→' in lower) or \
                                       ('рух' in lower and 'на' in lower) or ('прямують' in lower and 'на' in lower) or \
                                       ('продовжує' in lower and ('рух' in lower or 'на' in lower)) or \
                                       ('в' in lower and ('напрямку' in lower or 'напрямок' in lower or 'напрям' in lower))

                if has_direction_keyword:
                    if 'північно-західн' in lower or 'північно-захід' in lower:
                        course_direction = 'nw'
                    elif 'південно-західн' in lower or 'південно-захід' in lower:
                        course_direction = 'sw'
                    elif 'північно-східн' in lower or 'північно-схід' in lower:
                        course_direction = 'ne'
                    elif 'південно-східн' in lower or 'південно-схід' in lower:
                        course_direction = 'se'
                    # Single directions in course - support "курсом на", "рух на", "в [напрямок] напрямку"
                    elif re.search(r'(курс\w*|рух|прямують|продовжує)\s+(на\s+)?північ', lower) or re.search(r'в\s+північн\w*\s+напрям', lower):
                        course_direction = 'n'
                    elif re.search(r'(курс\w*|рух|прямують|продовжує)\s+(на\s+)?південь|півд', lower) or re.search(r'в\s+півден\w*\s+напрям', lower):
                        course_direction = 's'
                    elif re.search(r'(курс\w*|рух|прямують|продовжує)\s+(на\s+)?схід', lower) or re.search(r'в\s+східн\w*\s+напрям', lower):
                        course_direction = 'e'
                    elif re.search(r'(курс\w*|рух|прямують|продовжує)\s+(на\s+)?захід', lower) or re.search(r'в\s+захід\w*\s+напрям', lower):
                        course_direction = 'w'

                # If we have both start position and course direction, apply them sequentially
                if start_direction and course_direction:
                    # First offset: move to start position within region
                    lat_start, lng_start = offset(base_lat, base_lng, start_direction)
                    # Second offset: apply course direction from start position
                    lat_final, lng_final = offset(lat_start, lng_start, course_direction)

                    # Create descriptive label with arrow for trajectory visualization
                    start_labels = {'n':'півночі', 's':'півдні', 'e':'сході', 'w':'заході'}
                    course_labels = {
                        'n':'північ', 's':'південь', 'e':'схід', 'w':'захід',
                        'ne':'північний схід', 'nw':'північний захід',
                        'se':'південний схід', 'sw':'південний захід'
                    }
                    # Direction labels for arrow (Ukrainian names compatible with frontend)
                    arrow_labels = {
                        'n':'північ', 's':'півдня', 'e':'сходу', 'w':'заходу',
                        'ne':'північного сходу', 'nw':'північного заходу',
                        'se':'південного сходу', 'sw':'південного заходу'
                    }
                    start_label = start_labels.get(start_direction, 'області')
                    course_label = course_labels.get(course_direction, 'напрямок')
                    arrow_label = arrow_labels.get(course_direction, '')
                    base_disp = reg_name.split()[0].title()

                    # Add arrow to place name for trajectory visualization in frontend
                    place_name = f"{base_disp} (з {start_label})"
                    if arrow_label:
                        place_name += f" ←{arrow_label}"

                    trajectory = {
                        'start': [lat_start, lng_start],
                        'end': [lat_final, lng_final],
                        'source': base_disp,
                        'target': course_label,
                        'kind': 'region_start_course'
                    }

                    threat_type, icon = classify(text)
                    return [{
                        'id': str(mid), 'place': place_name,
                        'lat': lat_final, 'lng': lng_final,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_start_course', 'count': drone_count,
                        'trajectory': trajectory,
                        'course_direction': f"курс на {course_label}",
                        'course_source': base_disp,
                        'course_target': course_label,
                        'course_type': 'region_start_course'
                    }]

                # If only course_direction (no start position), use it as the direction
                if course_direction and not start_direction:
                    direction_code = course_direction

                # смещение ~50-70 км в сторону указанного направления (fallback for single direction)
                lat_o, lng_o = offset(base_lat, base_lng, direction_code)
                threat_type, icon = classify(text)
                dir_label_map = {
                    'n':'північна частина', 's':'південна частина', 'e':'східна частина', 'w':'західна частина',
                    'ne':'північно-східна частина', 'nw':'північно-західна частина',
                    'se':'південно-східна частина', 'sw':'південно-західна частина'
                }
                # Direction labels for arrow (Ukrainian names compatible with frontend)
                arrow_labels = {
                    'n':'північ', 's':'півдня', 'e':'сходу', 'w':'заходу',
                    'ne':'північного сходу', 'nw':'північного заходу',
                    'se':'південного сходу', 'sw':'південного заходу'
                }
                dir_phrase = dir_label_map.get(direction_code, 'частина')
                arrow_label = arrow_labels.get(direction_code, '')
                base_disp = reg_name.split()[0].title()

                # Add arrow to place name for trajectory visualization
                place_name = f"{base_disp} ({dir_phrase})"
                if arrow_label:
                    place_name += f" ←{arrow_label}"

                return [{
                    'id': str(mid), 'place': place_name, 'lat': lat_o, 'lng': lng_o,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'region_direction', 'count': drone_count
                }]
            # если нет направления — продолжаем анализ (ищем конкретные цели типа "курс на <місто>")
    # Midpoint for explicit course between two regions (e.g. "... на запоріжжі курсом на дніпропетровщину")
    if len(matched_regions) == 2 and ('курс' in lower or '➡' in lower or '→' in lower) and (' на ' in lower):
            # ensure we really reference both regions in a course sense: one mentioned before 'курс' and the other after 'курс' / arrow
            parts_course = re.split(r'курс|➡|→', lower, 1)
            if len(parts_course) == 2:
                before, after_part = parts_course
                r1, r2 = matched_regions[0], matched_regions[1]
                bnames = [r1[0].split()[0].lower(), r2[0].split()[0].lower()]
                # If both region stems appear across the split segments, build midpoint
                cond_split = (any(n[:5] in before for n in bnames) and any(n[:5] in after_part for n in bnames))
                # Fallback heuristic: pattern 'на <region1>' earlier then arrow/"курс" then 'на <region2>'
                if not cond_split:
                    # Extract simple region stems from OBLAST_CENTERS keys
                    stems = ['запоріж','запор', 'дніпропетров','дніпропет']
                    if any(st in lower for st in stems):
                        if re.search(r'на\s+запоріж', lower) and re.search(r'на\s+дніпропетров', lower):
                            cond_split = True
                if cond_split:
                    (n1,(a1,b1)), (n2,(a2,b2)) = matched_regions

                    def region_variants(name: str):
                        base = name.split()[0].lower()
                        variants = {base}
                        cleaned = base.replace('область', '').replace('області', '').strip()
                        if cleaned:
                            variants.add(cleaned)
                        if cleaned.endswith('ська'):
                            stem = cleaned[:-4]
                            variants.update({stem + 'щина', stem + 'щини', stem + 'щин', stem})
                        elif cleaned.endswith('ської'):
                            stem = cleaned[:-5]
                            variants.update({stem + 'щина', stem + 'щини', stem + 'щин', stem})
                        return [v for v in variants if v]

                    def segment_has(segment: str, name: str) -> bool:
                        for variant in region_variants(name):
                            if variant in segment:
                                return True
                        return False

                    def region_position(full_text: str, name: str) -> int:
                        positions = []
                        for variant in region_variants(name):
                            idx = full_text.find(variant)
                            if idx != -1:
                                positions.append(idx)
                        return min(positions) if positions else 10**6

                    # Determine source and target based on message structure
                    source_entry = matched_regions[0]
                    target_entry = matched_regions[1]
                    before_region = next((entry for entry in matched_regions if segment_has(before, entry[0])), None)
                    after_region = next((entry for entry in matched_regions if segment_has(after_part, entry[0])), None)

                    if before_region and after_region and before_region != after_region:
                        source_entry = before_region
                        target_entry = after_region
                    elif before_region and not after_region:
                        source_entry = before_region
                        target_entry = next(entry for entry in matched_regions if entry != source_entry)
                    elif after_region and not before_region:
                        target_entry = after_region
                        source_entry = next(entry for entry in matched_regions if entry != target_entry)
                    else:
                        # fallback to textual order
                        ordered = sorted(matched_regions, key=lambda entry: region_position(lower, entry[0]))
                        if len(ordered) == 2 and ordered[0] != ordered[1]:
                            source_entry, target_entry = ordered[0], ordered[1]

                    (source_name, (src_lat, src_lng)) = source_entry
                    (target_name, (tgt_lat, tgt_lng)) = target_entry

                    source_region = source_name.split()[0].title()
                    target_region = target_name.split()[0].title()

                    def offset(lat, lng, code):
                        import math
                        lat_step = 0.35
                        lng_step = 0.55 / max(0.2, abs(math.cos(math.radians(lat))))
                        if code == 'n': return lat+lat_step, lng
                        if code == 's': return lat-lat_step, lng
                        if code == 'e': return lat, lng+lng_step
                        if code == 'w': return lat, lng-lng_step
                        lat_diag = lat_step * 0.8
                        lng_diag = lng_step * 0.8
                        if code == 'ne': return lat+lat_diag, lng+lng_diag
                        if code == 'nw': return lat+lat_diag, lng-lng_diag
                        if code == 'se': return lat-lat_diag, lng+lng_diag
                        if code == 'sw': return lat-lat_diag, lng-lng_diag
                        return lat, lng

                    def detect_region_direction(text_block: str, region_label: str):
                        base = region_label.split()[0].lower()
                        region_variants = [base]
                        if base.endswith('ська'):
                            region_variants.append(base[:-4] + 'щині')
                            region_variants.append(base[:-4] + 'щини')
                            region_variants.append(base[:-4] + 'щина')
                        tokens = {
                            'північ': 'n',
                            'півден': 's',
                            'схід': 'e',
                            'захід': 'w'
                        }
                        for variant in region_variants:
                            for needle, code in tokens.items():
                                pattern = rf'(?:на|у|в)\s+{needle}\w*\s+(?:частин\w*\s+)?{variant}'
                                if re.search(pattern, text_block):
                                    return code
                        return None

                    source_lat_adj, source_lng_adj = src_lat, src_lng
                    source_direction_hint = detect_region_direction(lower, source_name)
                    if source_direction_hint:
                        source_lat_adj, source_lng_adj = offset(source_lat_adj, source_lng_adj, source_direction_hint)

                    # Calculate direction from source to target for arrow labels
                    dlat = tgt_lat - src_lat
                    dlng = tgt_lng - src_lng

                    def direction_token(dy: float, dx: float):
                        if abs(dy) < 1e-6 and abs(dx) < 1e-6:
                            return None
                        if abs(dy) > abs(dx) * 1.4:
                            return 'n' if dy > 0 else 's'
                        if abs(dx) > abs(dy) * 1.4:
                            return 'e' if dx > 0 else 'w'
                        if dy >= 0 and dx >= 0:
                            return 'ne'
                        if dy >= 0 and dx < 0:
                            return 'nw'
                        if dy < 0 and dx >= 0:
                            return 'se'
                        return 'sw'

                    dir_token = direction_token(dlat, dlng)
                    arrow_label_map = {
                        'n': 'півночі', 's': 'півдня', 'e': 'сходу', 'w': 'заходу',
                        'ne': 'північного сходу', 'nw': 'північного заходу',
                        'se': 'південного сходу', 'sw': 'південного заходу'
                    }
                    course_label_map = {
                        'n': 'північ', 's': 'південь', 'e': 'схід', 'w': 'захід',
                        'ne': "північний схід", 'nw': "північний захід",
                        'se': "південний схід", 'sw': "південний захід"
                    }
                    arrow_direction = arrow_label_map.get(dir_token, '')
                    course_direction_text = course_label_map.get(dir_token)

                    # Position marker at the (optionally offset) source to avoid teleporting to the target city
                    lat = source_lat_adj
                    lng = source_lng_adj

                    # Create place name with arrow for trajectory visualization
                    place_name = f"{source_region} → {target_region}"
                    if arrow_direction:
                        place_name += f" ←{arrow_direction}"

                    trajectory = {
                        'start': [lat, lng],
                        'end': [tgt_lat, tgt_lng],
                        'target': target_region,
                        'source': source_region,
                        'kind': 'region_course'
                    }

                    threat_type, icon = classify(text)
                    result = {
                        'id': str(mid), 'place': place_name, 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_course_trajectory', 'count': drone_count,
                        'trajectory': trajectory,
                        'course_source': source_region,
                        'course_target': target_region,
                        'course_type': 'region_to_region'
                    }
                    if course_direction_text:
                        result['course_direction'] = f"курс на {course_direction_text}"
                    else:
                        result['course_direction'] = f"курс на {target_region}"
                    return [result]

    if len(matched_regions) == 2 and any(w in lower for w in ['межі','межу','межа','между','границі','граница']):
            (n1,(a1,b1)), (n2,(a2,b2)) = matched_regions
            lat = (a1+a2)/2; lng = (b1+b2)/2
            threat_type, icon = classify(text)
            return [{
                'id': str(mid), 'place': f"Межа {n1.split()[0].title()}/{n2.split()[0].title()}" , 'lat': lat, 'lng': lng,
                'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                'marker_icon': icon, 'count': drone_count
            }]
    else:
            # If message contains explicit course targets (parsed later), don't emit plain region markers
            course_target_hint = False
            for ln in text.split('\n'):
                ll = ln.lower()
                if 'бпла' in ll and 'курс' in ll and re.search(r'курс(?:ом)?\s+(?:на|в|у)\s+[A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,}', ll):
                    course_target_hint = True
                    break
            if not course_target_hint:
                threat_type, icon = classify(text)

                # Extract course information for Shahed threats
                course_info = None
                if threat_type == 'shahed':
                    course_info = extract_shahed_course_info(original_text or text)

                tracks = []
                seen = set()
                for idx,(n1,(lat,lng)) in enumerate(matched_regions,1):
                    base = n1.split()[0].title()
                    if base in seen: continue
                    seen.add(base)

                    track = {
                        'id': f"{mid}_r{idx}", 'place': base, 'lat': lat, 'lng': lng,
                        'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': icon, 'source_match': 'region_multi_simple', 'count': drone_count
                    }

                    # Add course information if available
                    if course_info:
                        track.update({
                            'course_source': course_info.get('source_city'),
                            'course_target': course_info.get('target_city'),
                            'course_direction': course_info.get('course_direction'),
                            'course_type': course_info.get('course_type')
                        })

                    tracks.append(track)
                if tracks:
                    return tracks
    # City fallback scan (ensure whole-word style match to avoid false hits inside oblast words, e.g. 'дніпро' in 'дніпропетровщина')
    for city in UA_CITIES:
        if re.search(r'(?<![a-zа-яїієґ])' + re.escape(city) + r'(?![a-zа-яїієґ])', lower):
            norm = UA_CITY_NORMALIZE.get(city, city)
            # City fallback: attempt region-qualified first
            coords = None
            if region_hint_global and OPENCAGE_API_KEY:
                coords = geocode_opencage(f"{norm} {region_hint_global}")
            if not coords:
                coords = region_enhanced_coords(norm)
            # If областной контекст уже определён (matched_regions) ограничим города той же области
            if matched_regions:
                # берем первый stem области
                stem = None
                for (rn, _c) in matched_regions:
                    for s in ['харків','львів','київ','дніпропетров','полтав','сум','черніг','волин','запор','одес','микола','черка','житом','хмельниць','рівн','івано','терноп','ужгород','кропив','луган','донець','чернівц']:
                        if s in rn:
                            stem = s; break
                    if stem: break
                if stem and norm in CITY_TO_OBLAST and CITY_TO_OBLAST[norm] != stem:
                    continue
            if coords:
                lat, lng = coords
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': norm.title(), 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'count': drone_count
                }]
            # if city found but no coords even in fallback, continue scanning others (no break)
    # --- Slash separated settlements with drone count (e.g. "дніпро / самар — 6х бпла ... курс західний") ---
    if '/' in lower and ('бпла' in lower or 'дрон' in lower) and any(x in lower for x in ['х бпла','x бпла',' бпла']):
        left_part = lower.split('—')[0].split('-',1)[0]
        parts = [p.strip() for p in re.split(r'/|\\', left_part) if p.strip()]
        found = []
        for p in parts:
            if p in CITY_COORDS:
                found.append((p.title(), CITY_COORDS[p]))
        if found:
            threat_type, icon = classify(text)
            tracks = []
            for idx,(nm,(lat,lng)) in enumerate(found,1):
                # If course west mentioned, offset west a bit
                if 'курс захід' in lower or 'курс запад' in lower:
                    lng -= 0.4
                tracks.append({
                    'id': f"{mid}_s{idx}", 'place': nm, 'lat': lat, 'lng': lng,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'slash_combo'
                })
            if tracks:
                return tracks
    # --- Single city with westward course ("курс західний") adjust marker to west to avoid mistaken northern region offsets ---
    if 'курс захід' in lower and 'бпла' in lower:
        for c in CITY_COORDS.keys():
            if c in lower:
                lat,lng = CITY_COORDS[c]
                threat_type, icon = classify(text)
                return [{
                    'id': str(mid), 'place': c.title(), 'lat': lat, 'lng': lng - 0.4,
                    'threat_type': threat_type, 'text': text[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'course_west'
                }]
    # --- Drone course target parsing (e.g. "БпЛА курсом на Ніжин") ---
    def _normalize_course_city(w: str):
        # Preserve internal single space for multi-word (e.g. "липова долина") before stripping punctuation
        w = re.sub(r'\s+', ' ', w.strip().lower())
        # Remove punctuation but keep spaces and hyphen
        w = re.sub(r'["`ʼ’\'.,:;()]+', '', w)
        # Allow letters, spaces, hyphen
        w = re.sub(r'[^a-zа-яїієґё\- ]', '', w)
        # Accusative to nominative heuristic for each word (handles phrases like 'велику багачку', 'липову долину')
        parts = [p for p in w.split(' ') if p]
        norm_parts = []
        for p in parts:
            base = p
            # Common feminine accusative endings -> nominative
            if len(base) > 4 and base.endswith(('у','ю')):
                base = base[:-1] + 'а'
            # Handle '-у/ю' endings for multi-word second element 'долину' -> 'долина'
            if len(base) > 5 and base.endswith('ину'):
                base = base[:-2] + 'на'
            # Special handling for oblast names ending in 'щину' -> 'щина'
            if len(base) > 6 and base.endswith('щину'):
                base = base[:-1] + 'а'
            norm_parts.append(base)
        w = ' '.join(norm_parts)
        # Apply explicit manual normalization map last (covers irregular)
        if w in UA_CITY_NORMALIZE:
            w = UA_CITY_NORMALIZE[w]
        return w
    course_matches = []
    # Ищем каждую строку с шаблоном
    for line in text.split('\n'):
        line_low = line.lower()
        if 'бпла' in line_low and 'курс' in line_low and (' на ' in line_low or ' в ' in line_low or ' у ' in line_low):
            # Capture one or two words as target, allowing hyphens and apostrophes
            m = re.search(r'курс(?:ом)?\s+(?:на|в|у)\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,}(?:\s+[A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})?)', line, flags=re.IGNORECASE)
            if m:
                raw_city = m.group(1)
                norm_city = _normalize_course_city(raw_city)
                if norm_city:
                    # If the captured target looks like an oblast (region) name (e.g. 'дніпропетровщина', 'черкаська область'),
                    # we intentionally SKIP adding a precise course target marker to avoid falsely placing it at the oblast's capital city.
                    # User requirement: phrases like 'курс(ом) на Дніпропетровщину' must NOT create a marker right in 'Дніпро'.
                    # Check both nominative and accusative forms (щина/щину)
                    if re.search(r'(щина|щину|область)$', norm_city) or re.search(r'(щина|щину|область)$', raw_city.lower()):
                        log.debug(f'skip course_target oblast_only={norm_city} raw={raw_city} mid={mid}')
                        continue
                    coords = region_enhanced_coords(norm_city)
                    if not coords:
                        log.debug(f'course_target_lookup miss city={norm_city} mid={mid} line={line.strip()[:120]!r} region_hint={region_hint_global}')
                        coords = ensure_city_coords(norm_city, context=text)
                        # Try context-based lookup if standard lookup fails
                        if not coords:
                            context_result = ensure_city_coords_with_message_context(norm_city, text)
                            if context_result:
                                coords = context_result[:2]  # Take only lat, lng
                    # Oblast stem disambiguation: if global hint exists and known expected stem differs, re-query with region-qualified geocode
                    if coords and region_hint_global and norm_city in CITY_TO_OBLAST:
                        expected_stem = CITY_TO_OBLAST[norm_city]
                        if expected_stem != region_hint_global[:len(expected_stem)]:
                            # attempt region-qualified geocode with expected stem to refine
                            if OPENCAGE_API_KEY:
                                try:
                                    region_phrase = None
                                    # derive full oblast phrase from stem heuristically (simple mapping subset)
                                    stem_map = {
                                        'сум': 'сумська область', 'полтав': 'полтавська область', 'дніпропетров': 'дніпропетровська область',
                                        'харків': 'харківська область'
                                    }
                                    region_phrase = stem_map.get(expected_stem)
                                    if region_phrase:
                                        refined = geocode_opencage(f"{norm_city} {region_phrase}")
                                        if refined:
                                            coords = refined
                                except Exception:
                                    pass
                    if coords:
                        log.debug(f'course_target_match city={norm_city} coords={coords} region_hint={region_hint_global} mid={mid}')
                    # If still no coords AND we have a region hint + OpenCage, try region-qualified query directly for multi-word ambiguous city
                    if not coords and region_hint_global and OPENCAGE_API_KEY:
                        try:
                            refined2 = geocode_opencage(f"{norm_city} {region_hint_global}")
                            if refined2:
                                coords = refined2
                        except Exception:
                            pass
                    if coords:
                        # Extract line-specific drone count if present (e.g. "4х БпЛА")
                        line_count = None
                        m_lc = re.search(r'(\b\d{1,3})\s*[xх]\s*бпла', line_low)
                        if m_lc:
                            try:
                                line_count = int(m_lc.group(1))
                            except Exception:
                                line_count = None
                        # Ensure coords is a tuple of exactly 2 elements (lat, lng)
                        if len(coords) >= 2:
                            coords = coords[:2]
                        course_matches.append((norm_city.title(), coords, line[:200], line_count))
    if course_matches:
        threat_type, icon = classify(text)
        tracks = []
        seen_places = set()
        for idx,(name,(lat,lng),snippet,line_count) in enumerate(course_matches,1):
            if name in seen_places: continue
            seen_places.add(name)

            # Extract Shahed course information if this is a Shahed threat
            course_info = None
            if threat_type == 'shahed':
                course_info = extract_shahed_course_info(original_text or text)

            # Determine how many tracks to create
            count = line_count if line_count else drone_count
            tracks_to_create = max(1, count if count else 1)

            # Create multiple tracks for multiple drones
            for i in range(tracks_to_create):
                track_name = name
                if tracks_to_create > 1:
                    track_name += f" #{i+1}"

                # Add small coordinate offsets to prevent marker overlap
                marker_lat = lat
                marker_lng = lng
                if tracks_to_create > 1:
                    # Create a chain pattern - drones one after another
                    offset_distance = 0.03  # ~3km offset between each drone
                    marker_lat += offset_distance * i
                    marker_lng += offset_distance * i * 0.5

                track = {
                    'id': f"{mid}_c{idx}_{i+1}", 'place': track_name, 'lat': marker_lat, 'lng': marker_lng,
                    'threat_type': threat_type, 'text': snippet[:500], 'date': date_str, 'channel': channel,
                    'marker_icon': icon, 'source_match': 'course_target', 'count': 1
                }

                # Add course information if available
                if course_info:
                    track.update({
                        'course_source': course_info.get('source_city'),
                        'course_target': course_info.get('target_city'),
                        'course_direction': course_info.get('course_direction'),
                        'course_type': course_info.get('course_type')
                    })

                tracks.append(track)
        if tracks:
            return tracks

    # Логируем длинные сообщения, которые не сгенерировали треков
    try:
        if text and len(text) > 1000:
            print(f"DEBUG: LONG MESSAGE NO TRACKS - mid={mid}, length={len(text)}, preview: {text[:200]}...")
            # Проверим наличие ключевых слов
            lower_check = text.lower()
            keywords = {'бпла': lower_check.count('бпла'), 'шахед': lower_check.count('шахед'),
                       'курс': lower_check.count('курс'), 'район': lower_check.count('район')}
            print(f"DEBUG: Long message keywords: {keywords}")
    except Exception:
        pass

    # Final check: if we found single UAV threats earlier but no other tracks, return the UAV threats
    if 'single_uav_threats' in locals() and single_uav_threats:
        add_debug_log(f"FINAL: Returning single UAV threats only: {len(single_uav_threats)}", "final_single_uav")
        return single_uav_threats

    return None

async def fetch_loop():
    log.info('fetch_loop() started')
    if not client:
        log.warning('Telegram client not configured; skipping fetch loop.')
        return
    log.info('fetch_loop: client exists, proceeding')
    async def ensure_connected():
        log.info('ensure_connected() called')
        if client.is_connected():
            log.info('Client already connected')
            auth_status = await client.is_user_authorized()
            log.info(f'Authorization status: {auth_status}')
            return auth_status
        try:
            log.info('Connecting client...')
            await client.connect()
            log.info('Client connected successfully')
            # If bot token provided and not authorized yet, try bot login
            if BOT_TOKEN and not await client.is_user_authorized():
                try:
                    log.info('Trying bot token login...')
                    await client.start(bot_token=BOT_TOKEN)
                except Exception as be:
                    log.error(f'Bot start failed: {be}')
            auth_status = await client.is_user_authorized()
            log.info(f'Final authorization status: {auth_status}')
            if not auth_status:
                log.error('Not authorized. Use /auth/start & /auth/complete to login or set TELEGRAM_SESSION.')
                return False
            return True
        except AuthKeyDuplicatedError:
            log.error('AuthKeyDuplicatedError: duplicate session. Provide new TELEGRAM_SESSION or re-auth.')
            return False
        except AuthKeyUnregisteredError:
            log.error('AuthKeyUnregisteredError: Session invalid/expired. Re-auth needed.')
            return False
        except FloodWaitError as fe:
            wait = int(getattr(fe, 'seconds', 60))
            log.warning(f'FloodWait: sleeping {wait}s before reconnect.')
            await asyncio.sleep(wait)
            return False
        except Exception as e:
            log.warning(f'ensure_connected error: {e}')
            return False

    if not await ensure_connected():
        AUTH_STATUS.update({'authorized': False, 'reason': 'not_authorized_initial'})
        await asyncio.sleep(180)
        return
    else:
        AUTH_STATUS.update({'authorized': True, 'reason': 'ok'})
    tz = pytz.timezone('Europe/Kyiv')
    # Load existing messages and create ID set (convert to strings for comparison)
    all_data = load_messages()
    processed = {str(m.get('id')) for m in all_data if m.get('id')}
    # -------- Initial backfill (last BACKFILL_MINUTES, default 50) --------
    try:
        backfill_minutes = int(os.getenv('BACKFILL_MINUTES', '50'))
    except ValueError:
        backfill_minutes = 50
    # SPEED FIX: Limit backfill messages per channel (was 400, now 100)
    try:
        backfill_limit = int(os.getenv('BACKFILL_LIMIT', '100'))
    except ValueError:
        backfill_limit = 100
    backfill_cutoff = datetime.now(tz) - timedelta(minutes=backfill_minutes)
    if backfill_minutes > 0:
        log.info(f'Starting FAST backfill for last {backfill_minutes} minutes (limit {backfill_limit} per channel, NO geocoding)...')
        # Track backfill progress
        BACKFILL_STATUS['in_progress'] = True
        BACKFILL_STATUS['started_at'] = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        BACKFILL_STATUS['channels_total'] = len([c for c in CHANNELS if c.strip()])
        BACKFILL_STATUS['channels_done'] = 0
        BACKFILL_STATUS['messages_processed'] = 0

        total_backfilled = 0
        for ch in CHANNELS:
            ch_strip = ch.strip()
            if not ch_strip:
                continue
            BACKFILL_STATUS['current_channel'] = ch_strip
            print(f"DEBUG: Processing backfill for channel: {ch_strip}")
            fetched = 0
            try:
                if not await ensure_connected():
                    log.warning('Disconnected during backfill; aborting backfill early.')
                    break
                async for msg in client.iter_messages(ch_strip, limit=backfill_limit):  # SPEED FIX: reduced from 400
                    if not msg.text:
                        continue
                    dt = msg.date.astimezone(tz)
                    if dt < backfill_cutoff:
                        break  # older than needed
                    msg_id_str = str(msg.id)
                    if msg_id_str in processed:
                        continue
                    # Check for ballistic threat messages (backfill - don't add to chat)
                    update_ballistic_state(msg.text, is_realtime=False)

                    # SPEED FIX: Skip heavy geocoding during backfill - store raw, process later
                    # This makes backfill instant instead of 30+ minutes
                    all_data.append({
                        'id': msg_id_str,
                        'place': None,
                        'lat': None,
                        'lng': None,
                        'threat_type': 'shahed',  # default, will be updated on reparse
                        'text': msg.text[:500],
                        'date': dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'channel': ch_strip,
                        'pending_geo': True  # Flag for lazy geocoding in /data
                    })
                    processed.add(msg_id_str)
                    fetched += 1
                    BACKFILL_STATUS['messages_processed'] += 1
                if fetched:
                    total_backfilled += fetched
                    log.info(f'Backfilled {fetched} raw messages from {ch_strip}')
                BACKFILL_STATUS['channels_done'] += 1
            except Exception as e:
                log.warning(f'Backfill error {ch_strip}: {e}')
                BACKFILL_STATUS['channels_done'] += 1
    if backfill_minutes > 0:
        # Mark backfill complete
        BACKFILL_STATUS['in_progress'] = False
        BACKFILL_STATUS['current_channel'] = None
        if total_backfilled:
            save_messages(all_data)
            log.info(f'Backfill saved: {total_backfilled} raw messages (geocoding deferred to /data)')
        log.info('Backfill completed.')
    while True:
        new_tracks = []
        for ch in CHANNELS:
            ch = ch.strip()
            if not ch:
                continue
            if ch in INVALID_CHANNELS:
                log.debug(f'Skip invalid channel {ch}')
                continue
            msgs_seen = 0
            msgs_recent_window = 0
            geo_added = 0
            try:
                if not await ensure_connected():
                    # If session invalid we stop loop gracefully
                    if not client.is_connected():
                        log.error('Stopping live loop due to lost/invalid session.')
                        AUTH_STATUS.update({'authorized': False, 'reason': 'lost_session'})
                        return
                log.debug(f'Polling channel {ch} (last processed count={len(processed)})')
                async for msg in client.iter_messages(ch, limit=20):
                    msgs_seen += 1
                    if not msg.text:
                        continue
                    msg_id_str = str(msg.id)
                    if msg_id_str in processed:
                        continue
                    dt = msg.date.astimezone(tz)
                    if dt < datetime.now(tz) - timedelta(minutes=30):
                        # Older than live window
                        continue
                    msgs_recent_window += 1
                    # Check for ballistic threat messages (realtime - add to chat)
                    update_ballistic_state(msg.text, is_realtime=True)
                    # Add other important messages to chat
                    add_telegram_message_to_chat(msg.text, is_realtime=True)
                    tracks = process_message(msg.text, msg.id, dt.strftime('%Y-%m-%d %H:%M:%S'), ch)
                    
                    # DEBUG: Log what process_message returned
                    print(f"[FETCH_DEBUG] msg.id={msg.id}, tracks={len(tracks) if tracks else 0}, has_coords={bool(tracks and tracks[0].get('lat'))}", flush=True)
                    if tracks:
                        print(f"[FETCH_DEBUG] First track: place={tracks[0].get('place')}, lat={tracks[0].get('lat')}, lng={tracks[0].get('lng')}", flush=True)

                    # Send push notification for threat messages (КАБи, ракети, БПЛА)
                    msg_lower = msg.text.lower()
                    if any(kw in msg_lower for kw in ['каб', 'ракет', 'балістичн', 'бпла', 'дрон', 'шахед', 'вибух']):
                        # Extract location from message (usually first part before threat description)
                        location = ''
                        if '(' in msg.text and ')' in msg.text:
                            # Format: "Харків (Харківська обл.) Загроза..."
                            location = msg.text.split(')')[0] + ')'
                        elif tracks and tracks[0].get('place'):
                            location = tracks[0]['place']
                        
                        # DEBUG: Log location extraction
                        print(f"[PUSH_DEBUG] msg_id={msg.id}, location='{location}', has_tracks={bool(tracks)}", flush=True)

                        if location:
                            # Pass FULL message text - function will extract threat part
                            send_telegram_threat_notification(msg.text, location, str(msg.id))
                        else:
                            # No location found - still try to send with raw text as fallback
                            print(f"[PUSH_DEBUG] No location found, trying with first 50 chars of msg", flush=True)
                            # Try to extract any region-like word from text
                            import re
                            oblast_match = re.search(r'([А-Яа-яІіЇїЄє]+(?:ська|ський)\s*обл)', msg.text, re.IGNORECASE)
                            if oblast_match:
                                location = oblast_match.group(1)
                                print(f"[PUSH_DEBUG] Found oblast in text: '{location}'", flush=True)
                                send_telegram_threat_notification(msg.text, location, str(msg.id))
                            else:
                                print(f"[PUSH_DEBUG] Could not extract location, skipping push for msg {msg.id}", flush=True)

                    if tracks:
                        merged_any = False
                        appended = []
                        for t in tracks:
                            merged, ref = maybe_merge_track(all_data, t)
                            print(f"[FETCH_DEBUG] Track {t.get('place')}: merged={merged}", flush=True)
                            if merged:
                                merged_any = True
                            else:
                                new_tracks.append(t)
                                appended.append(t)
                        geo_added += 1
                        processed.add(msg_id_str)
                        print(f"[FETCH_DEBUG] Result: merged_any={merged_any}, appended={len(appended)}, new_tracks_total={len(new_tracks)}", flush=True)
                        if merged_any and not appended:
                            log.info(f'Merged live track(s) {ch} #{msg.id} (no new marker).')
                        else:
                            log.info(f'Added track from {ch} #{msg.id} (+{len(appended)} new, merged={merged_any})')
                    else:
                        # Store raw if enabled to allow later reprocessing / debugging (e.g., napramok multi-line posts)
                        if ALWAYS_STORE_RAW:
                            all_data.append({
                                'id': msg_id_str, 'place': None, 'lat': None, 'lng': None,
                                'threat_type': None, 'text': msg.text[:800], 'date': dt.strftime('%Y-%m-%d %H:%M:%S'),
                                'channel': ch, 'pending_geo': True
                            })
                            processed.add(msg_id_str)
                        log.debug(f'Live skip (no geo): {ch} #{msg.id} {msg.text[:80]!r}')
            except AuthKeyDuplicatedError:
                log.error('AuthKeyDuplicatedError during live fetch. Ending loop until session replaced.')
                AUTH_STATUS.update({'authorized': False, 'reason': 'authkey_duplicated'})
                return
            except FloodWaitError as fe:
                wait = int(getattr(fe, 'seconds', 60))
                log.warning(f'FloodWait while reading {ch}: sleep {wait}s')
                await asyncio.sleep(wait)
            # Generic RPC errors will be caught by broad Exception if specific class not available
            except Exception as e:
                msg = str(e)
                log.warning(f'Error reading {ch}: {msg}')
                # Auto-mark invalid entity errors to skip future attempts this runtime
                markers = ['Cannot find any entity', 'CHANNEL_PRIVATE', 'USERNAME_NOT_OCCUPIED', 'TOPIC_DELETED']
                if any(mk in msg for mk in markers):
                    INVALID_CHANNELS.add(ch)
                    log.warning(f'Marking channel {ch} as invalid; will skip further reads this session.')
            finally:
                # Post-channel diagnostics to help debug silent channels like 'napramok'
                log.debug(
                    f'Channel diag {ch}: iter_messages_seen={msgs_seen}, recent_window={msgs_recent_window}, geo_added={geo_added}, invalid={ch in INVALID_CHANNELS}'
                )
                if msgs_seen == 0:
                    log.warning(f'Channel {ch} returned no messages this cycle (possible resolution/access issue).')
                elif msgs_recent_window == 0:
                    log.debug(f'Channel {ch} had messages but none within last 30m window.')
                elif geo_added == 0:
                    log.debug(f'Channel {ch} had {msgs_recent_window} recent messages but none produced geo tracks.')
        if new_tracks:
            # RACE CONDITION FIX: Reload all_data from disk before extending
            # This preserves updates made by /data endpoint's update_message()
            all_data = load_messages()
            processed = {m.get('id') for m in all_data}
            # Only add tracks that aren't already in the data (check by id)
            existing_ids = {m.get('id') for m in all_data}
            truly_new = [t for t in new_tracks if t.get('id') not in existing_ids]
            if truly_new:
                all_data.extend(truly_new)
                save_messages(all_data)
                try:
                    broadcast_new(truly_new)
                except Exception as e:
                    log.debug(f'SSE broadcast failed: {e}')
        # Note: removed periodic save_messages when no new tracks to avoid overwriting /data updates
        await asyncio.sleep(45)  # Check every 45 seconds (CPU optimized)

