"""
UkraineAlarm API client.

HTTP клієнт для ukrainealarm.com API з:
- Retry logic
- Response caching
- ETag support
"""
import time
import json
import hashlib
import logging
import threading
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """Cached API response."""
    data: Any
    timestamp: float
    etag: Optional[str] = None
    
    def is_fresh(self, ttl: float) -> bool:
        return time.time() - self.timestamp < ttl
    
    def is_stale(self, max_age: float) -> bool:
        return time.time() - self.timestamp > max_age


@dataclass
class AlarmRegion:
    """Single alarm region."""
    region_id: str
    region_name: str
    region_type: str  # State, District, Community
    active_alerts: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def has_alarm(self) -> bool:
        return len(self.active_alerts) > 0
    
    @property
    def alert_types(self) -> List[str]:
        return [alert.get('type', 'unknown') for alert in self.active_alerts]
    
    @property
    def is_oblast(self) -> bool:
        return self.region_type == 'State'
    
    @property
    def is_district(self) -> bool:
        return self.region_type == 'District'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'regionId': self.region_id,
            'regionName': self.region_name,
            'regionType': self.region_type,
            'activeAlerts': self.active_alerts,
        }


class AlarmClient:
    """
    HTTP client for ukrainealarm.com API.
    
    Features:
    - Automatic retries with backoff
    - Response caching with TTL
    - ETag support for bandwidth optimization
    - Thread-safe operations
    """
    
    DEFAULT_BASE_URL = 'https://api.ukrainealarm.com/api/v3'
    DEFAULT_TIMEOUT = 10
    DEFAULT_CACHE_TTL = 30  # seconds
    DEFAULT_STALE_TTL = 300  # 5 minutes - use stale data if API fails
    
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        cache_ttl: float = DEFAULT_CACHE_TTL,
        stale_ttl: float = DEFAULT_STALE_TTL,
        max_retries: int = 3,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip('/')
        self._timeout = timeout
        self._cache_ttl = cache_ttl
        self._stale_ttl = stale_ttl
        self._max_retries = max_retries
        
        # Caches
        self._alerts_cache: Optional[CachedResponse] = None
        self._regions_cache: Optional[CachedResponse] = None
        
        self._lock = threading.Lock()
        
        # Stats
        self._request_count = 0
        self._cache_hits = 0
        self._errors = 0
    
    def get_alerts(self, force_refresh: bool = False) -> Tuple[List[AlarmRegion], bool]:
        """
        Get all active alerts.
        
        Args:
            force_refresh: Bypass cache
            
        Returns:
            Tuple of (list of AlarmRegion, is_from_cache)
        """
        with self._lock:
            # Check cache
            if not force_refresh and self._alerts_cache:
                if self._alerts_cache.is_fresh(self._cache_ttl):
                    self._cache_hits += 1
                    return self._parse_alerts(self._alerts_cache.data), True
            
            # Fetch from API
            data = self._fetch_with_retry('/alerts')
            
            if data is not None:
                self._alerts_cache = CachedResponse(
                    data=data,
                    timestamp=time.time(),
                    etag=self._compute_etag(data),
                )
                return self._parse_alerts(data), False
            
            # API failed - try stale cache
            if self._alerts_cache and not self._alerts_cache.is_stale(self._stale_ttl):
                log.warning("Using stale cache after API failure")
                return self._parse_alerts(self._alerts_cache.data), True
            
            # No cache available
            return [], False
    
    def get_alerts_raw(self, force_refresh: bool = False) -> Tuple[List[Dict], Optional[str]]:
        """
        Get raw alerts data (for API proxy).
        
        Returns:
            Tuple of (raw data, etag)
        """
        with self._lock:
            # Check cache
            if not force_refresh and self._alerts_cache:
                if self._alerts_cache.is_fresh(self._cache_ttl):
                    self._cache_hits += 1
                    return self._alerts_cache.data, self._alerts_cache.etag
            
            # Fetch from API
            data = self._fetch_with_retry('/alerts')
            
            if data is not None:
                etag = self._compute_etag(data)
                self._alerts_cache = CachedResponse(
                    data=data,
                    timestamp=time.time(),
                    etag=etag,
                )
                return data, etag
            
            # API failed - try stale cache
            if self._alerts_cache and not self._alerts_cache.is_stale(self._stale_ttl):
                return self._alerts_cache.data, self._alerts_cache.etag
            
            return [], None
    
    def get_active_regions(self) -> List[AlarmRegion]:
        """Get only regions with active alarms."""
        regions, _ = self.get_alerts()
        return [r for r in regions if r.has_alarm]
    
    def get_active_oblasts(self) -> List[AlarmRegion]:
        """Get oblasts (states) with active alarms."""
        return [r for r in self.get_active_regions() if r.is_oblast]
    
    def get_active_districts(self) -> List[AlarmRegion]:
        """Get districts with active alarms."""
        return [r for r in self.get_active_regions() if r.is_district]
    
    def check_etag(self, client_etag: str) -> bool:
        """Check if client's ETag matches current data."""
        if self._alerts_cache and self._alerts_cache.etag:
            return client_etag == self._alerts_cache.etag
        return False
    
    def stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            'requests': self._request_count,
            'cache_hits': self._cache_hits,
            'errors': self._errors,
            'cache_age': time.time() - self._alerts_cache.timestamp if self._alerts_cache else None,
        }
    
    def _fetch_with_retry(self, endpoint: str) -> Optional[Any]:
        """Fetch from API with retries."""
        import requests
        
        url = f"{self._base_url}{endpoint}"
        headers = {'Authorization': self._api_key}
        
        for attempt in range(self._max_retries):
            try:
                self._request_count += 1
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self._timeout,
                )
                
                if response.ok:
                    return response.json()
                else:
                    log.warning(f"API attempt {attempt+1}/{self._max_retries} failed: HTTP {response.status_code}")
                    
            except Exception as e:
                log.warning(f"API attempt {attempt+1}/{self._max_retries} error: {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < self._max_retries - 1:
                time.sleep(2 ** attempt)
        
        self._errors += 1
        return None
    
    def _parse_alerts(self, data: List[Dict]) -> List[AlarmRegion]:
        """Parse raw API data into AlarmRegion objects."""
        regions = []
        for item in data:
            region = AlarmRegion(
                region_id=item.get('regionId', ''),
                region_name=item.get('regionName', ''),
                region_type=item.get('regionType', ''),
                active_alerts=item.get('activeAlerts', []),
            )
            regions.append(region)
        return regions
    
    def _compute_etag(self, data: Any) -> str:
        """Compute ETag from data."""
        content = json.dumps(data, sort_keys=True)
        hash_value = hashlib.md5(content.encode()).hexdigest()[:16]
        return f'"{hash_value}"'
