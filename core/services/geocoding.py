"""
Neptun Alarm - Geocoding Service
Multi-provider geocoding with caching
"""
import json
import time
import logging
import requests
from typing import Optional, Tuple, Dict
from pathlib import Path

from core.config import OPENCAGE_API_KEY, OPENCAGE_TTL

log = logging.getLogger(__name__)

# Cache file
GEOCODE_CACHE_FILE = Path("geocode_cache.json")

# In-memory cache
_geocode_cache: Dict[str, dict] = {}


def _load_cache():
    """Load geocode cache from file"""
    global _geocode_cache
    try:
        if GEOCODE_CACHE_FILE.exists():
            _geocode_cache = json.loads(GEOCODE_CACHE_FILE.read_text())
    except Exception as e:
        log.warning(f"Failed to load geocode cache: {e}")
        _geocode_cache = {}


def _save_cache():
    """Save geocode cache to file"""
    try:
        GEOCODE_CACHE_FILE.write_text(json.dumps(_geocode_cache, ensure_ascii=False, indent=2))
    except Exception as e:
        log.warning(f"Failed to save geocode cache: {e}")


def _get_from_cache(key: str) -> Optional[Tuple[float, float]]:
    """Get coordinates from cache if not expired"""
    if key in _geocode_cache:
        entry = _geocode_cache[key]
        if time.time() - entry.get('ts', 0) < OPENCAGE_TTL:
            coords = entry.get('coords')
            if coords:
                return tuple(coords)
    return None


def _set_cache(key: str, coords: Optional[Tuple[float, float]]):
    """Store coordinates in cache"""
    _geocode_cache[key] = {
        'ts': int(time.time()),
        'coords': list(coords) if coords else None
    }
    _save_cache()


def geocode_opencage(place: str, region: str = None) -> Optional[Tuple[float, float]]:
    """
    Geocode place using OpenCage API
    
    Args:
        place: Place name to geocode
        region: Optional region hint for better accuracy
        
    Returns:
        Tuple of (lat, lng) or None
    """
    if not OPENCAGE_API_KEY:
        return None
    
    # Build cache key
    cache_key = f"{place.lower()}|{region or ''}"
    
    # Check cache
    cached = _get_from_cache(cache_key)
    if cached:
        return cached
    
    # Build query
    query = place
    if region:
        query = f"{place}, {region}, Ukraine"
    else:
        query = f"{place}, Ukraine"
    
    try:
        resp = requests.get(
            'https://api.opencagedata.com/geocode/v1/json',
            params={
                'q': query,
                'key': OPENCAGE_API_KEY,
                'language': 'uk',
                'limit': 1,
                'countrycode': 'ua',
                'no_annotations': 1
            },
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('results'):
                geo = data['results'][0]['geometry']
                coords = (geo['lat'], geo['lng'])
                _set_cache(cache_key, coords)
                return coords
        
        # Cache negative result
        _set_cache(cache_key, None)
        return None
        
    except Exception as e:
        log.warning(f"OpenCage geocoding error for '{place}': {e}")
        return None


def geocode_nominatim(place: str, region: str = None) -> Optional[Tuple[float, float]]:
    """
    Geocode place using Nominatim (OpenStreetMap)
    Free but rate-limited
    """
    cache_key = f"nom:{place.lower()}|{region or ''}"
    
    cached = _get_from_cache(cache_key)
    if cached:
        return cached
    
    query = place
    if region:
        query = f"{place}, {region}"
    
    try:
        resp = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={
                'q': f"{query}, Ukraine",
                'format': 'json',
                'limit': 1,
                'countrycodes': 'ua',
                'accept-language': 'uk'
            },
            headers={
                'User-Agent': 'NeptunAlarm/2.0 (https://neptun.in.ua)'
            },
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                coords = (float(data[0]['lat']), float(data[0]['lon']))
                _set_cache(cache_key, coords)
                return coords
        
        _set_cache(cache_key, None)
        return None
        
    except Exception as e:
        log.warning(f"Nominatim geocoding error for '{place}': {e}")
        return None


def geocode(place: str, region: str = None) -> Optional[Tuple[float, float]]:
    """
    Smart geocoding - tries multiple providers
    
    Priority:
    1. Cache
    2. OpenCage (if API key available)
    3. Nominatim (free fallback)
    """
    if not place:
        return None
    
    # Try OpenCage first (better for Ukraine)
    if OPENCAGE_API_KEY:
        result = geocode_opencage(place, region)
        if result:
            return result
    
    # Fallback to Nominatim
    result = geocode_nominatim(place, region)
    if result:
        return result
    
    return None


def reverse_geocode(lat: float, lng: float) -> Optional[str]:
    """
    Reverse geocode - get place name from coordinates
    """
    cache_key = f"rev:{lat:.4f},{lng:.4f}"
    
    if cache_key in _geocode_cache:
        entry = _geocode_cache[cache_key]
        if time.time() - entry.get('ts', 0) < OPENCAGE_TTL:
            return entry.get('name')
    
    try:
        resp = requests.get(
            'https://nominatim.openstreetmap.org/reverse',
            params={
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'accept-language': 'uk'
            },
            headers={
                'User-Agent': 'NeptunAlarm/2.0 (https://neptun.in.ua)'
            },
            timeout=5
        )
        
        if resp.status_code == 200:
            data = resp.json()
            name = data.get('display_name', '').split(',')[0]
            _geocode_cache[cache_key] = {'ts': int(time.time()), 'name': name}
            _save_cache()
            return name
            
    except Exception as e:
        log.warning(f"Reverse geocoding error: {e}")
    
    return None


# Load cache on module import
_load_cache()
