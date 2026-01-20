"""
OpenCage geocoder.

Платний geocoder з високою точністю.
Використовується як fallback коли Photon не знаходить.
"""
import time
import logging
from typing import Optional
import requests

from services.geocoding.base import GeocoderInterface, GeocodingResult

log = logging.getLogger(__name__)


class OpenCageGeocoder(GeocoderInterface):
    """
    Geocoder using OpenCage API.
    
    Переваги:
    - Висока точність
    - Гарна документація
    - Стабільний API
    
    Недоліки:
    - Платний (є безкоштовний тариф з лімітами)
    - 2500 запитів/день на безкоштовному тарифі
    """
    
    DEFAULT_URL = 'https://api.opencagedata.com/geocode/v1/json'
    DEFAULT_TIMEOUT = 5.0
    
    def __init__(
        self,
        api_key: str,
        url: str = DEFAULT_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self._api_key = api_key
        self._url = url
        self._timeout = timeout
        
        # Stats
        self._requests = 0
        self._hits = 0
        self._errors = 0
    
    @property
    def name(self) -> str:
        return 'opencage'
    
    @property
    def priority(self) -> int:
        return 30  # Lower priority (use sparingly due to limits)
    
    def is_available(self) -> bool:
        return bool(self._api_key)
    
    def geocode(
        self,
        query: str,
        region: Optional[str] = None,
    ) -> Optional[GeocodingResult]:
        """Geocode using OpenCage."""
        if not self._api_key:
            return None
        
        if not query or len(query) < 2:
            return None
        
        self._requests += 1
        
        try:
            # Build query
            search_query = query
            if region:
                search_query = f"{query}, {region}"
            search_query = f"{search_query}, Ukraine"
            
            params = {
                'q': search_query,
                'key': self._api_key,
                'limit': 3,
                'countrycode': 'ua',
                'language': 'uk',
                'no_annotations': 1,
            }
            
            response = requests.get(
                self._url,
                params=params,
                timeout=self._timeout,
            )
            
            if not response.ok:
                self._errors += 1
                return None
            
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                return None
            
            # Take first result
            result = results[0]
            geometry = result.get('geometry', {})
            
            lat = geometry.get('lat')
            lng = geometry.get('lng')
            
            if lat is None or lng is None:
                return None
            
            self._hits += 1
            
            return GeocodingResult(
                coordinates=(lat, lng),
                place_name=result.get('formatted', query),
                source=self.name,
                confidence=result.get('confidence', 0) / 10,  # OpenCage uses 1-10 scale
                raw_response=result,
            )
            
        except Exception as e:
            log.warning(f"OpenCage error: {e}")
            self._errors += 1
            return None
    
    def stats(self) -> dict:
        return {
            'name': self.name,
            'configured': bool(self._api_key),
            'requests': self._requests,
            'hits': self._hits,
            'errors': self._errors,
        }
