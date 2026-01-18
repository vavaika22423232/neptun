"""
Nominatim Geocoding Integration for Ukrainian Cities
Provides fallback geocoding for cities not in the local database

Enhanced version 2.0:
- Fuzzy matching for typos
- Multiple search strategies
- OSM/Nominatim structured search
- Better rate limiting with exponential backoff
- Geographic validation
"""

import requests
import time
import logging
import re
from typing import Optional, Tuple, List, Dict
from difflib import SequenceMatcher

log = logging.getLogger(__name__)

# Try to import persistent cache
try:
    from nominatim_cache import get_from_cache, add_to_cache
    PERSISTENT_CACHE = True
except ImportError:
    PERSISTENT_CACHE = False
    def get_from_cache(city, region=None): return None
    def add_to_cache(city, coords, region=None): pass

# Nominatim API endpoint (using OpenStreetMap's public instance)
NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_ENDPOINT = "https://nominatim.openstreetmap.org/reverse"

# Rate limiting with exponential backoff
last_request_time = 0
MIN_REQUEST_INTERVAL = 1.1  # seconds (slightly more than 1 for safety)
_consecutive_failures = 0
_backoff_until = 0

# User agent as required by Nominatim policy
USER_AGENT = "UkraineAlertMap/2.0 (alert mapping service; contact@neptun.app)"

# In-memory cache to avoid repeated requests during session
_cache = {}
_negative_cache = {}  # Cache for failed lookups to avoid repeating them

# Ukraine bounding box for validation
UKRAINE_BOUNDS = {
    'min_lat': 44.0,
    'max_lat': 52.5,
    'min_lng': 22.0,
    'max_lng': 41.0
}

# Common Ukrainian word patterns to clean from search
CLEAN_PATTERNS = [
    r'\bсмт\b', r'\bс\.\s*', r'\bм\.\s*', r'\bн\.п\.\s*',
    r'\bселище\b', r'\bмісто\b', r'\bсело\b', r'\bхутір\b',
    r'\bрайон[уі]?\b', r'\bобласт[ьі]\b', r'\bрн\b'
]

# Extended region mapping with all variants
REGION_MAP = {
    # Colloquial names
    'київщина': 'Київська область',
    'харківщина': 'Харківська область',
    'одещина': 'Одеська область',
    'дніпропетровщина': 'Дніпропетровська область',
    'львівщина': 'Львівська область',
    'запоріжжя': 'Запорізька область',
    'донеччина': 'Донецька область',
    'луганщина': 'Луганська область',
    'миколаївщина': 'Миколаївська область',
    'черкащина': 'Черкаська область',
    'чернігівщина': 'Чернігівська область',
    'сумщина': 'Сумська область',
    'полтавщина': 'Полтавська область',
    'житомирщина': 'Житомирська область',
    'вінниччина': 'Вінницька область',
    'хмельниччина': 'Хмельницька область',
    'рівненщина': 'Рівненська область',
    'волинь': 'Волинська область',
    'закарпаття': 'Закарпатська область',
    'івано-франківщина': 'Івано-Франківська область',
    'тернопільщина': 'Тернопільська область',
    'херсонщина': 'Херсонська область',
    'кіровоградщина': 'Кіровоградська область',
    'буковина': 'Чернівецька область',
    
    # Short adjective forms
    'київська': 'Київська область',
    'харківська': 'Харківська область',
    'одеська': 'Одеська область',
    'дніпропетровська': 'Дніпропетровська область',
    'львівська': 'Львівська область',
    'запорізька': 'Запорізька область',
    'донецька': 'Донецька область',
    'луганська': 'Луганська область',
    'миколаївська': 'Миколаївська область',
    'черкаська': 'Черкаська область',
    'чернігівська': 'Чернігівська область',
    'сумська': 'Сумська область',
    'полтавська': 'Полтавська область',
    'житомирська': 'Житомирська область',
    'вінницька': 'Вінницька область',
    'хмельницька': 'Хмельницька область',
    'рівненська': 'Рівненська область',
    'волинська': 'Волинська область',
    'закарпатська': 'Закарпатська область',
    'івано-франківська': 'Івано-Франківська область',
    'тернопільська': 'Тернопільська область',
    'херсонська': 'Херсонська область',
    'кіровоградська': 'Кіровоградська область',
    'чернівецька': 'Чернівецька область',
}

# OSM admin level 4 region names (English)
OSM_REGION_NAMES = {
    'київська': "Kyiv Oblast",
    'харківська': "Kharkiv Oblast",
    'одеська': "Odesa Oblast",
    'дніпропетровська': "Dnipropetrovsk Oblast",
    'львівська': "Lviv Oblast",
    'запорізька': "Zaporizhzhia Oblast",
    'донецька': "Donetsk Oblast",
    'луганська': "Luhansk Oblast",
    'миколаївська': "Mykolaiv Oblast",
    'черкаська': "Cherkasy Oblast",
    'чернігівська': "Chernihiv Oblast",
    'сумська': "Sumy Oblast",
    'полтавська': "Poltava Oblast",
    'житомирська': "Zhytomyr Oblast",
    'вінницька': "Vinnytsia Oblast",
    'хмельницька': "Khmelnytskyi Oblast",
    'рівненська': "Rivne Oblast",
    'волинська': "Volyn Oblast",
    'закарпатська': "Zakarpattia Oblast",
    'івано-франківська': "Ivano-Frankivsk Oblast",
    'тернопільська': "Ternopil Oblast",
    'херсонська': "Kherson Oblast",
    'кіровоградська': "Kirovohrad Oblast",
    'чернівецька': "Chernivtsi Oblast",
}


def normalize_region(region: str) -> Optional[str]:
    """Normalize region name to full Ukrainian oblast name"""
    if not region:
        return None
    
    region_lower = region.lower().strip()
    
    # Direct lookup
    if region_lower in REGION_MAP:
        return REGION_MAP[region_lower]
    
    # Try to extract oblast name from various formats
    for key, value in REGION_MAP.items():
        if key in region_lower:
            return value
    
    # If already looks like full oblast name
    if 'область' in region_lower:
        return region.title()
    
    return region


def clean_city_name(city: str) -> str:
    """Clean city name for search"""
    if not city:
        return ''
    
    cleaned = city.lower().strip()
    
    # Remove common prefixes/suffixes
    for pattern in CLEAN_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Remove multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def is_within_ukraine(lat: float, lng: float) -> bool:
    """Check if coordinates are within Ukraine bounds"""
    return (UKRAINE_BOUNDS['min_lat'] <= lat <= UKRAINE_BOUNDS['max_lat'] and
            UKRAINE_BOUNDS['min_lng'] <= lng <= UKRAINE_BOUNDS['max_lng'])


def fuzzy_match_score(s1: str, s2: str) -> float:
    """Calculate fuzzy match score between two strings"""
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def _apply_rate_limiting():
    """Apply rate limiting with exponential backoff"""
    global last_request_time, _consecutive_failures, _backoff_until
    
    current_time = time.time()
    
    # Check if we're in backoff period
    if current_time < _backoff_until:
        wait_time = _backoff_until - current_time
        log.debug(f"In backoff period, waiting {wait_time:.1f}s")
        time.sleep(wait_time)
    
    # Regular rate limiting
    time_since_last = current_time - last_request_time
    if time_since_last < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - time_since_last)
    
    last_request_time = time.time()


def _handle_request_failure():
    """Handle request failure with exponential backoff"""
    global _consecutive_failures, _backoff_until
    
    _consecutive_failures += 1
    backoff_time = min(60, 2 ** _consecutive_failures)  # Max 60 seconds
    _backoff_until = time.time() + backoff_time
    log.warning(f"Nominatim failure #{_consecutive_failures}, backing off for {backoff_time}s")


def _handle_request_success():
    """Reset failure counter on success"""
    global _consecutive_failures, _backoff_until
    _consecutive_failures = 0
    _backoff_until = 0


def get_coordinates_nominatim(city_name: str, region: Optional[str] = None) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a Ukrainian city using Nominatim API
    
    Enhanced with:
    - Multiple search strategies
    - Fuzzy matching
    - Negative caching
    - Exponential backoff
    
    Args:
        city_name: Name of the city/settlement
        region: Optional region/oblast name for better accuracy
        
    Returns:
        Tuple of (latitude, longitude) or None if not found
    """
    global last_request_time
    
    if not city_name:
        return None
    
    # Clean and normalize input
    city_clean = clean_city_name(city_name)
    if not city_clean:
        return None
    
    region_full = normalize_region(region)
    
    # Check in-memory cache first
    cache_key = f"{city_clean}_{region_full or ''}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    # Check negative cache
    if cache_key in _negative_cache:
        age = time.time() - _negative_cache[cache_key]
        if age < 3600:  # Negative cache for 1 hour
            log.debug(f"Negative cache hit for {city_name}")
            return None
    
    # Check persistent cache
    if PERSISTENT_CACHE:
        cached_coords = get_from_cache(city_clean, region_full)
        if cached_coords:
            _cache[cache_key] = cached_coords
            log.debug(f"Found in persistent cache: {city_name} -> {cached_coords}")
            return cached_coords
    
    # Try multiple search strategies
    strategies = _build_search_strategies(city_clean, region_full)
    
    for strategy_name, params in strategies:
        coords = _execute_nominatim_search(params, strategy_name, city_name)
        if coords:
            # Cache successful result
            _cache[cache_key] = coords
            if PERSISTENT_CACHE:
                try:
                    add_to_cache(city_clean, coords, region_full)
                except Exception as e:
                    log.warning(f"Failed to save to persistent cache: {e}")
            return coords
    
    # Cache negative result
    _negative_cache[cache_key] = time.time()
    log.debug(f"All strategies failed for {city_name}")
    return None


def _build_search_strategies(city: str, region: str = None) -> List[Tuple[str, Dict]]:
    """Build list of search strategies to try"""
    strategies = []
    
    # Strategy 1: Structured search with region (most accurate)
    if region:
        osm_region = None
        region_lower = region.lower().replace(' область', '')
        if region_lower in OSM_REGION_NAMES:
            osm_region = OSM_REGION_NAMES[region_lower]
        
        strategies.append(('structured_with_osm_region', {
            'city': city,
            'state': osm_region or region,
            'country': 'Ukraine',
            'format': 'json',
            'limit': 3,
            'addressdetails': 1
        }))
        
        # Also try with Ukrainian region name
        strategies.append(('structured_with_ua_region', {
            'city': city,
            'state': region,
            'country': 'Ukraine',
            'format': 'json',
            'limit': 3,
            'addressdetails': 1
        }))
    
    # Strategy 2: Free-form query with region
    if region:
        query = f"{city}, {region}, Ukraine"
        strategies.append(('freeform_with_region', {
            'q': query,
            'format': 'json',
            'limit': 3,
            'countrycodes': 'ua',
            'addressdetails': 1
        }))
    
    # Strategy 3: Free-form query without region
    strategies.append(('freeform_simple', {
        'q': f"{city}, Ukraine",
        'format': 'json',
        'limit': 5,
        'countrycodes': 'ua',
        'addressdetails': 1
    }))
    
    # Strategy 4: Just the city name (for unique names)
    strategies.append(('city_only', {
        'q': city,
        'format': 'json',
        'limit': 5,
        'countrycodes': 'ua',
        'addressdetails': 1
    }))
    
    return strategies


def _execute_nominatim_search(params: Dict, strategy_name: str, original_city: str) -> Optional[Tuple[float, float]]:
    """Execute a single Nominatim search"""
    
    _apply_rate_limiting()
    
    try:
        headers = {'User-Agent': USER_AGENT}
        
        # Use structured search if 'city' in params, otherwise free-form
        if 'city' in params:
            endpoint = NOMINATIM_ENDPOINT
            params_final = {k: v for k, v in params.items() if v is not None}
        else:
            endpoint = NOMINATIM_ENDPOINT
            params_final = params
        
        log.debug(f"Nominatim {strategy_name}: {params_final}")
        
        response = requests.get(
            endpoint,
            params=params_final,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 429:
            _handle_request_failure()
            log.warning("Nominatim rate limited (429)")
            return None
        
        if response.status_code != 200:
            log.warning(f"Nominatim returned status {response.status_code}")
            return None
        
        _handle_request_success()
        
        results = response.json()
        if not results:
            return None
        
        # Find best matching result
        best_result = _find_best_result(results, original_city)
        if best_result:
            lat = float(best_result['lat'])
            lon = float(best_result['lon'])
            
            if is_within_ukraine(lat, lon):
                log.info(f"Nominatim {strategy_name} found: {original_city} -> ({lat}, {lon})")
                return (lat, lon)
            else:
                log.warning(f"Result outside Ukraine bounds for {original_city}: ({lat}, {lon})")
        
        return None
        
    except requests.Timeout:
        log.warning(f"Nominatim timeout for {original_city}")
        _handle_request_failure()
        return None
    except requests.RequestException as e:
        log.error(f"Nominatim request failed: {e}")
        _handle_request_failure()
        return None
    except Exception as e:
        log.error(f"Nominatim error: {e}")
        return None


def _find_best_result(results: List[Dict], original_city: str) -> Optional[Dict]:
    """Find best matching result from Nominatim response"""
    if not results:
        return None
    
    # Score each result
    scored_results = []
    for r in results:
        score = 0
        
        # Check display name for city match
        display_name = r.get('display_name', '').lower()
        city_lower = original_city.lower()
        
        # Direct match in display name
        if city_lower in display_name:
            score += 10
        
        # Fuzzy match
        fuzzy = fuzzy_match_score(city_lower, display_name.split(',')[0])
        score += fuzzy * 5
        
        # Prefer place types that indicate settlements
        place_type = r.get('type', '').lower()
        settlement_types = ['city', 'town', 'village', 'hamlet', 'suburb', 'locality']
        if place_type in settlement_types:
            score += 5
        
        # Check OSM class
        osm_class = r.get('class', '').lower()
        if osm_class == 'place':
            score += 3
        
        # Check importance (0-1 scale from Nominatim)
        importance = float(r.get('importance', 0))
        score += importance * 2
        
        scored_results.append((score, r))
    
    # Sort by score descending
    scored_results.sort(key=lambda x: x[0], reverse=True)
    
    # Return best result if score is reasonable
    if scored_results and scored_results[0][0] > 3:
        return scored_results[0][1]
    
    # Fallback to first result
    return results[0] if results else None


def reverse_geocode(lat: float, lng: float) -> Optional[Dict]:
    """
    Reverse geocode coordinates to get location name.
    
    Returns dict with:
    - city: settlement name
    - region: oblast name
    - display_name: full address string
    """
    if not is_within_ukraine(lat, lng):
        return None
    
    _apply_rate_limiting()
    
    try:
        params = {
            'lat': lat,
            'lon': lng,
            'format': 'json',
            'addressdetails': 1,
            'zoom': 14  # City/village level
        }
        
        headers = {'User-Agent': USER_AGENT}
        
        response = requests.get(
            NOMINATIM_REVERSE_ENDPOINT,
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            return None
        
        _handle_request_success()
        
        result = response.json()
        address = result.get('address', {})
        
        # Extract city (try multiple fields)
        city = (address.get('city') or 
                address.get('town') or 
                address.get('village') or 
                address.get('hamlet') or
                address.get('locality'))
        
        # Extract region
        region = address.get('state')
        
        return {
            'city': city,
            'region': region,
            'display_name': result.get('display_name'),
            'lat': lat,
            'lng': lng
        }
        
    except Exception as e:
        log.error(f"Reverse geocode error: {e}")
        return None


def clear_cache():
    """Clear all geocoding caches"""
    global _cache, _negative_cache
    _cache = {}
    _negative_cache = {}
    log.info("Nominatim caches cleared")


def get_cache_stats() -> Dict:
    """Get cache statistics"""
    return {
        'positive_cache_size': len(_cache),
        'negative_cache_size': len(_negative_cache),
        'consecutive_failures': _consecutive_failures,
        'in_backoff': time.time() < _backoff_until
    }

