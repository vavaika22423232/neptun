"""
Photon geocoder (komoot.io).

HTTP geocoder з використанням безкоштовного Photon API.
Хороша альтернатива Nominatim без rate limits.
"""
import time
import logging
from typing import Optional, Tuple
import requests

from services.geocoding.base import GeocoderInterface, GeocodingResult

log = logging.getLogger(__name__)


class PhotonGeocoder(GeocoderInterface):
    """
    Geocoder using Photon API (photon.komoot.io).
    
    Переваги:
    - Безкоштовний
    - Без суворих rate limits
    - Швидший за Nominatim
    - Гарна підтримка України
    
    Недоліки:
    - Менш точний ніж Nominatim
    - Може бути недоступний
    """
    
    DEFAULT_URL = 'https://photon.komoot.io/api/'
    DEFAULT_TIMEOUT = 5.0
    
    # Ukraine bounding box for filtering
    UKRAINE_BBOX = {
        'lat_min': 44.0,
        'lat_max': 52.5,
        'lng_min': 22.0,
        'lng_max': 40.5,
    }
    
    def __init__(
        self,
        url: str = DEFAULT_URL,
        timeout: float = DEFAULT_TIMEOUT,
        enabled: bool = True,
    ):
        self._url = url.rstrip('/')
        self._timeout = timeout
        self._enabled = enabled
        
        # Stats
        self._requests = 0
        self._hits = 0
        self._errors = 0
        self._last_request_time: Optional[float] = None
    
    @property
    def name(self) -> str:
        return 'photon'
    
    @property
    def priority(self) -> int:
        return 50  # Medium priority (after local, before Nominatim)
    
    def is_available(self) -> bool:
        return self._enabled
    
    def geocode(
        self,
        query: str,
        region: Optional[str] = None,
    ) -> Optional[GeocodingResult]:
        """
        Geocode a location name.
        
        Args:
            query: Location name to geocode
            region: Optional region context (oblast)
            
        Returns:
            GeocodingResult or None if not found
        """
        if not self._enabled:
            return None
        
        if not query or len(query) < 2:
            return None
        
        self._requests += 1
        self._last_request_time = time.time()
        
        try:
            # Build query with region context
            search_query = query
            if region:
                # Add region for better accuracy
                search_query = f"{query}, {region}"
            
            # Add Ukraine context
            search_query = f"{search_query}, Ukraine"
            
            params = {
                'q': search_query,
                'limit': 5,
                'lang': 'uk',  # Ukrainian language
            }
            
            response = requests.get(
                self._url,
                params=params,
                timeout=self._timeout,
                headers={'User-Agent': 'NeptunApp/2.0'},
            )
            
            if not response.ok:
                log.warning(f"Photon returned {response.status_code}")
                self._errors += 1
                return None
            
            data = response.json()
            features = data.get('features', [])
            
            if not features:
                return None
            
            # Find best match within Ukraine
            for feature in features:
                coords = feature.get('geometry', {}).get('coordinates', [])
                if len(coords) < 2:
                    continue
                
                lng, lat = coords[0], coords[1]
                
                # Verify within Ukraine bounds
                if not self._is_in_ukraine(lat, lng):
                    continue
                
                # Extract place name
                props = feature.get('properties', {})
                place_name = (
                    props.get('name') or 
                    props.get('city') or 
                    props.get('locality') or
                    query
                )
                
                self._hits += 1
                
                return GeocodingResult(
                    coordinates=(lat, lng),
                    place_name=place_name,
                    source=self.name,
                    confidence=0.7,
                    raw_response=props,
                )
            
            return None
            
        except requests.Timeout:
            log.warning(f"Photon timeout for: {query}")
            self._errors += 1
            return None
        except requests.RequestException as e:
            log.warning(f"Photon request error: {e}")
            self._errors += 1
            return None
        except Exception as e:
            log.error(f"Photon error: {e}")
            self._errors += 1
            return None
    
    def _is_in_ukraine(self, lat: float, lng: float) -> bool:
        """Check if coordinates are within Ukraine."""
        return (
            self.UKRAINE_BBOX['lat_min'] <= lat <= self.UKRAINE_BBOX['lat_max'] and
            self.UKRAINE_BBOX['lng_min'] <= lng <= self.UKRAINE_BBOX['lng_max']
        )
    
    def stats(self) -> dict:
        """Get geocoder statistics."""
        return {
            'name': self.name,
            'enabled': self._enabled,
            'requests': self._requests,
            'hits': self._hits,
            'errors': self._errors,
            'hit_rate': round(self._hits / max(1, self._requests) * 100, 1),
            'last_request': self._last_request_time,
        }
