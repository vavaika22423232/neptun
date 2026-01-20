"""
Geocoding cache with negative caching.

Кешує як успішні, так і невдалі результати geocoding.
Негативний кеш запобігає повторним запитам до зовнішніх API
для локацій які вже відомо що не знайдуться.
"""
import time
import json
import os
import threading
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

from .base import GeocodingResult


@dataclass
class CacheEntry:
    """Single cache entry."""
    coordinates: Optional[Tuple[float, float]]
    source: str
    place_name: Optional[str]
    confidence: float
    cached_at: float
    expires_at: float
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    @property
    def is_negative(self) -> bool:
        """True if this is a cached 'not found' result."""
        return self.coordinates is None
    
    def to_result(self) -> Optional[GeocodingResult]:
        """Convert to GeocodingResult."""
        if self.is_negative:
            return None
        return GeocodingResult(
            coordinates=self.coordinates,
            place_name=self.place_name,
            source=f"{self.source}+cache",
            confidence=self.confidence,
        )


class GeocodeCache:
    """
    Two-level geocoding cache:
    1. In-memory for fast access
    2. File-based for persistence across restarts
    
    Features:
    - TTL for both positive and negative results
    - Different TTL for local vs external results
    - Automatic cleanup of expired entries
    - Thread-safe operations
    """
    
    def __init__(
        self,
        cache_file: str = 'geocode_cache.json',
        negative_cache_file: str = 'negative_geocode_cache.json',
        positive_ttl: float = 86400 * 30,  # 30 days
        negative_ttl: float = 86400 * 3,   # 3 days
        max_negative_entries: int = 500,
    ):
        self._cache_file = cache_file
        self._negative_cache_file = negative_cache_file
        self._positive_ttl = positive_ttl
        self._negative_ttl = negative_ttl
        self._max_negative = max_negative_entries
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # Load from files
        self._load_from_files()
    
    def get(self, query: str, region: Optional[str] = None) -> Optional[GeocodingResult]:
        """
        Get cached result for query.
        
        Returns:
            GeocodingResult or None if not cached/expired
        """
        key = self._make_key(query, region)
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                return None
            
            if entry.is_expired:
                del self._cache[key]
                return None
            
            return entry.to_result()
    
    def put(
        self,
        query: str,
        result: GeocodingResult,
        region: Optional[str] = None,
    ) -> None:
        """Cache a successful geocoding result."""
        key = self._make_key(query, region)
        now = time.time()
        
        entry = CacheEntry(
            coordinates=result.coordinates,
            source=result.source,
            place_name=result.place_name,
            confidence=result.confidence,
            cached_at=now,
            expires_at=now + self._positive_ttl,
        )
        
        with self._lock:
            self._cache[key] = entry
    
    def add_negative(self, query: str, region: Optional[str] = None) -> None:
        """Add query to negative cache (known not found)."""
        key = self._make_key(query, region)
        now = time.time()
        
        entry = CacheEntry(
            coordinates=None,
            source='negative',
            place_name=None,
            confidence=0.0,
            cached_at=now,
            expires_at=now + self._negative_ttl,
        )
        
        with self._lock:
            self._cache[key] = entry
            self._enforce_limits()
    
    def is_negative_cached(self, query: str, region: Optional[str] = None) -> bool:
        """
        Check if query is in negative cache.
        
        Use this to skip geocoding for known-bad queries.
        """
        key = self._make_key(query, region)
        
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                del self._cache[key]
                return False
            return entry.is_negative
    
    def invalidate(self, query: str, region: Optional[str] = None) -> bool:
        """Remove entry from cache. Returns True if entry existed."""
        key = self._make_key(query, region)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if v.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)
    
    def save(self) -> None:
        """Persist cache to files."""
        with self._lock:
            # Separate positive and negative
            positive = {}
            negative = {}
            
            for key, entry in self._cache.items():
                if entry.is_expired:
                    continue
                    
                data = {
                    'coords': entry.coordinates,
                    'source': entry.source,
                    'place_name': entry.place_name,
                    'confidence': entry.confidence,
                    'cached_at': entry.cached_at,
                    'expires_at': entry.expires_at,
                }
                
                if entry.is_negative:
                    negative[key] = data
                else:
                    positive[key] = data
            
            # Save positive cache
            try:
                with open(self._cache_file, 'w', encoding='utf-8') as f:
                    json.dump(positive, f, ensure_ascii=False)
            except Exception:
                pass
            
            # Save negative cache
            try:
                with open(self._negative_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(negative, f, ensure_ascii=False)
            except Exception:
                pass
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = len(self._cache)
            positive = sum(1 for e in self._cache.values() if not e.is_negative)
            negative = total - positive
            expired = sum(1 for e in self._cache.values() if e.is_expired)
            
            return {
                'total': total,
                'positive': positive,
                'negative': negative,
                'expired': expired,
            }
    
    def _make_key(self, query: str, region: Optional[str]) -> str:
        """Create cache key from query and region."""
        normalized = query.lower().strip()
        if region:
            return f"{normalized}|{region.lower().strip()}"
        return normalized
    
    def _enforce_limits(self) -> None:
        """Remove oldest negative entries if over limit."""
        negative_entries = [
            (k, v) for k, v in self._cache.items()
            if v.is_negative
        ]
        
        if len(negative_entries) > self._max_negative:
            # Sort by cached_at (oldest first)
            negative_entries.sort(key=lambda x: x[1].cached_at)
            
            # Remove oldest
            to_remove = len(negative_entries) - self._max_negative
            for key, _ in negative_entries[:to_remove]:
                del self._cache[key]
    
    def _load_from_files(self) -> None:
        """Load cache from files on startup."""
        now = time.time()
        
        # Load positive cache
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, entry_data in data.items():
                        if entry_data.get('expires_at', 0) > now:
                            self._cache[key] = CacheEntry(
                                coordinates=tuple(entry_data['coords']) if entry_data.get('coords') else None,
                                source=entry_data.get('source', 'cache'),
                                place_name=entry_data.get('place_name'),
                                confidence=entry_data.get('confidence', 1.0),
                                cached_at=entry_data.get('cached_at', now),
                                expires_at=entry_data.get('expires_at', now + self._positive_ttl),
                            )
            except Exception:
                pass
        
        # Load negative cache
        if os.path.exists(self._negative_cache_file):
            try:
                with open(self._negative_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, entry_data in data.items():
                        if entry_data.get('expires_at', 0) > now:
                            self._cache[key] = CacheEntry(
                                coordinates=None,
                                source=entry_data.get('source', 'negative_cache'),
                                place_name=None,
                                confidence=0.0,
                                cached_at=entry_data.get('cached_at', now),
                                expires_at=entry_data.get('expires_at', now + self._negative_ttl),
                            )
            except Exception:
                pass
