"""
Smart geocoder with context awareness and fallback chain.

Найкращий geocoder для українських військових повідомлень.
Використовує контекст повідомлення для disambiguації.
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .base import GeocoderInterface, GeocodingResult
from .normalizer import (
    extract_location_from_text,
    get_name_variants,
    is_direction_word,
    normalize_city,
    normalize_oblast,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SmartGeocodingResult(GeocodingResult):
    """Extended result with additional context."""
    oblast: Optional[str] = None
    district: Optional[str] = None
    location_type: str = 'unknown'  # city, village, district, oblast
    variants_tried: int = 0


@dataclass
class GeocodingStats:
    """Statistics for geocoding operations."""
    total_queries: int = 0
    cache_hits: int = 0
    local_hits: int = 0
    api_hits: int = 0
    failures: int = 0
    avg_response_time_ms: float = 0.0
    
    _response_times: list = field(default_factory=list, repr=False)
    
    def record_query(self, source: str, time_ms: float):
        self.total_queries += 1
        if source == 'cache':
            self.cache_hits += 1
        elif source == 'local':
            self.local_hits += 1
        elif source in ('nominatim', 'photon', 'opencage'):
            self.api_hits += 1
        elif source == 'failure':
            self.failures += 1
        
        self._response_times.append(time_ms)
        # Keep only last 1000
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]
        
        if self._response_times:
            self.avg_response_time_ms = sum(self._response_times) / len(self._response_times)
    
    def to_dict(self) -> dict:
        return {
            'total_queries': self.total_queries,
            'cache_hits': self.cache_hits,
            'local_hits': self.local_hits,
            'api_hits': self.api_hits,
            'failures': self.failures,
            'cache_rate': f"{(self.cache_hits / self.total_queries * 100):.1f}%" if self.total_queries > 0 else "0%",
            'success_rate': f"{((self.total_queries - self.failures) / self.total_queries * 100):.1f}%" if self.total_queries > 0 else "0%",
            'avg_response_time_ms': round(self.avg_response_time_ms, 2),
        }


class SmartGeocoder(GeocoderInterface):
    """
    Context-aware geocoder optimized for Ukrainian military messages.
    
    Features:
    - Message context analysis for disambiguation
    - Oblast/district hints from message
    - Multiple variant generation
    - Fallback chain with priorities
    - Comprehensive caching
    - Learning from corrections
    
    Strategy order:
    1. Learning cache (corrected geocodes)
    2. Response cache (recent successful results)
    3. Local database (CITY_COORDS, UKRAINE_ALL_SETTLEMENTS)
    4. External APIs (Nominatim, Photon, OpenCage)
    """
    
    # Known ambiguous cities that exist in multiple oblasts
    AMBIGUOUS_CITIES = {
        'олександрівка': ['дніпропетровська', 'донецька', 'кіровоградська', 'миколаївська', 'одеська'],
        'новоселівка': ['донецька', 'харківська', 'запорізька', 'дніпропетровська'],
        'степанівка': ['запорізька', 'миколаївська', 'одеська', 'херсонська'],
        'михайлівка': ['запорізька', 'дніпропетровська', 'донецька', 'одеська'],
        'петрівка': ['донецька', 'запорізька', 'кіровоградська', 'миколаївська'],
        'іванівка': ['херсонська', 'одеська', 'миколаївська', 'кіровоградська'],
        'тернівка': ['дніпропетровська', 'донецька', 'запорізька'],
        'зелене': ['донецька', 'запорізька', 'херсонська'],
        'кам\'янка': ['черкаська', 'дніпропетровська', 'запорізька'],
        'вільне': ['донецька', 'запорізька', 'луганська'],
        'мирне': ['донецька', 'запорізька', 'херсонська'],
        'червоне': ['одеська', 'миколаївська', 'запорізька'],
        'шевченко': ['донецька', 'дніпропетровська', 'запорізька'],
        'водяне': ['донецька', 'запорізька'],
        'піски': ['донецька', 'полтавська'],
    }
    
    def __init__(
        self,
        local_geocoder: Optional[GeocoderInterface] = None,
        api_geocoders: Optional[list[GeocoderInterface]] = None,
        cache: Optional[Any] = None,  # GeocodeCache
        learning_file: Optional[str] = None,
    ):
        """
        Args:
            local_geocoder: Fast local geocoder (CITY_COORDS, settlements)
            api_geocoders: List of external API geocoders
            cache: Response cache
            learning_file: Path to learning corrections file
        """
        self._local = local_geocoder
        self._apis = api_geocoders or []
        self._cache = cache
        self._learning_file = learning_file
        
        # Learning cache - loaded from file
        self._learning: dict[str, dict] = {}
        self._learning_dirty = False
        
        # Negative cache - locations that failed geocoding
        self._negative_cache: set[str] = set()
        
        # Stats
        self._stats = GeocodingStats()
        
        # Load learning data
        self._load_learning()
    
    @property
    def name(self) -> str:
        return "smart"
    
    @property
    def priority(self) -> int:
        return 1  # Highest priority
    
    def geocode(
        self,
        query: str,
        region: Optional[str] = None,
    ) -> Optional[GeocodingResult]:
        """
        Basic geocode without message context.
        """
        return self.geocode_with_context(query, region=region)
    
    def geocode_with_context(
        self,
        query: str,
        region: Optional[str] = None,
        message_text: Optional[str] = None,
        source_region: Optional[str] = None,
    ) -> Optional[SmartGeocodingResult]:
        """
        Smart geocoding with full message context.
        
        Args:
            query: Location name to geocode
            region: Explicit region hint
            message_text: Full message text for context extraction
            source_region: Region where threat originated
            
        Returns:
            SmartGeocodingResult or None
        """
        start_time = time.time()
        
        if not query:
            return None
        
        # Check if it's a direction word, not a location
        if is_direction_word(query):
            log.debug(f"Skipping direction word: {query}")
            return None
        
        # Normalize
        normalized = normalize_city(query)
        if not normalized:
            return None
        
        # Normalize region if provided
        normalized_region = normalize_oblast(region) if region else None
        
        # Try to extract region from message if not provided
        if not normalized_region and message_text:
            normalized_region = self._extract_region_from_message(message_text)
        
        # Use source region as fallback for disambiguation
        if not normalized_region and source_region:
            normalized_region = normalize_oblast(source_region)
        
        # Check negative cache first
        cache_key = f"{normalized}|{normalized_region or ''}"
        if cache_key in self._negative_cache:
            log.debug(f"Negative cache hit: {normalized}")
            return None
        
        # Strategy 1: Learning cache
        result = self._try_learning_cache(normalized, normalized_region)
        if result:
            self._record_success('cache', start_time)
            return result
        
        # Strategy 2: Response cache
        if self._cache:
            cached = self._cache.get(normalized, normalized_region)
            if cached:
                self._record_success('cache', start_time)
                return SmartGeocodingResult(
                    coordinates=cached.coordinates,
                    place_name=cached.place_name,
                    source='cache',
                    confidence=cached.confidence,
                    oblast=normalized_region,
                )
        
        # Strategy 3: Local geocoder with variants
        result = self._try_local_with_variants(normalized, normalized_region)
        if result:
            self._record_success('local', start_time)
            self._update_cache(normalized, normalized_region, result)
            return result
        
        # Strategy 4: Disambiguation for known ambiguous cities
        if normalized in self.AMBIGUOUS_CITIES:
            result = self._disambiguate(normalized, normalized_region, message_text)
            if result:
                self._record_success('local', start_time)
                self._update_cache(normalized, normalized_region, result)
                return result
        
        # Strategy 5: External APIs
        for api in self._apis:
            if not api.is_available:
                continue
            
            try:
                # Build query with region hint
                api_query = f"{query}, {region}" if region else query
                api_query += ", Україна"
                
                api_result = api.geocode(api_query, normalized_region)
                if api_result:
                    # Validate coordinates are in Ukraine
                    if self._validate_ukraine_coords(api_result.coordinates):
                        self._record_success(api.name, start_time)
                        smart_result = SmartGeocodingResult(
                            coordinates=api_result.coordinates,
                            place_name=api_result.place_name or query,
                            source=api.name,
                            confidence=api_result.confidence,
                            oblast=normalized_region,
                        )
                        self._update_cache(normalized, normalized_region, smart_result)
                        return smart_result
            except Exception as e:
                log.warning(f"API {api.name} failed for {query}: {e}")
        
        # All strategies failed
        self._record_success('failure', start_time)
        self._negative_cache.add(cache_key)
        
        # Limit negative cache size
        if len(self._negative_cache) > 5000:
            # Remove oldest entries (convert to list, slice, back to set)
            self._negative_cache = set(list(self._negative_cache)[-4000:])
        
        return None
    
    def _try_learning_cache(
        self,
        normalized: str,
        region: Optional[str],
    ) -> Optional[SmartGeocodingResult]:
        """Try learning cache with region-aware lookup."""
        # Try with region
        if region:
            key = f"{normalized}_{region}"
            if key in self._learning:
                entry = self._learning[key]
                return SmartGeocodingResult(
                    coordinates=(entry['lat'], entry['lng']),
                    place_name=entry.get('place', normalized),
                    source='learning',
                    confidence=0.99,
                    oblast=region,
                )
        
        # Try without region
        if normalized in self._learning:
            entry = self._learning[normalized]
            return SmartGeocodingResult(
                coordinates=(entry['lat'], entry['lng']),
                place_name=entry.get('place', normalized),
                source='learning',
                confidence=0.95,
                oblast=entry.get('oblast'),
            )
        
        return None
    
    def _try_local_with_variants(
        self,
        normalized: str,
        region: Optional[str],
    ) -> Optional[SmartGeocodingResult]:
        """Try local geocoder with name variants."""
        if not self._local:
            return None
        
        variants = get_name_variants(normalized)
        variants_tried = 0
        
        for variant in variants:
            variants_tried += 1
            result = self._local.geocode(variant, region)
            if result:
                return SmartGeocodingResult(
                    coordinates=result.coordinates,
                    place_name=result.place_name,
                    source='local',
                    confidence=result.confidence,
                    oblast=region,
                    variants_tried=variants_tried,
                )
        
        return None
    
    def _disambiguate(
        self,
        normalized: str,
        region: Optional[str],
        message_text: Optional[str],
    ) -> Optional[SmartGeocodingResult]:
        """Disambiguate city that exists in multiple oblasts."""
        possible_oblasts = self.AMBIGUOUS_CITIES.get(normalized, [])
        
        if not possible_oblasts:
            return None
        
        # If region is provided and matches, use it
        if region and region in possible_oblasts:
            return self._try_local_with_variants(normalized, region)
        
        # Try to infer from message context
        if message_text:
            text_lower = message_text.lower()
            for oblast in possible_oblasts:
                # Check if oblast name appears in message
                oblast_patterns = [
                    oblast,
                    oblast.replace('ська', 'щина'),
                    oblast.replace('ська', 'ської'),
                ]
                for pattern in oblast_patterns:
                    if pattern in text_lower:
                        return self._try_local_with_variants(normalized, oblast)
        
        # Default: use first oblast (usually most common)
        return self._try_local_with_variants(normalized, possible_oblasts[0])
    
    def _extract_region_from_message(self, text: str) -> Optional[str]:
        """Extract oblast from message text."""
        locations = extract_location_from_text(text)
        
        for loc in locations:
            if loc.get('type') == 'oblast':
                return loc.get('normalized') or normalize_oblast(loc['name'])
        
        return None
    
    def _validate_ukraine_coords(self, coords: tuple[float, float]) -> bool:
        """Validate coordinates are within Ukraine bounds."""
        lat, lng = coords
        # Ukraine approximate bounds
        return (44.0 <= lat <= 52.5) and (22.0 <= lng <= 40.5)
    
    def _update_cache(
        self,
        normalized: str,
        region: Optional[str],
        result: SmartGeocodingResult,
    ):
        """Update response cache."""
        if self._cache:
            self._cache.set(normalized, region, result)
    
    def _record_success(self, source: str, start_time: float):
        """Record successful geocoding."""
        elapsed_ms = (time.time() - start_time) * 1000
        self._stats.record_query(source, elapsed_ms)
    
    def learn_correction(
        self,
        query: str,
        correct_coords: tuple[float, float],
        oblast: Optional[str] = None,
        source: str = 'manual',
    ):
        """
        Learn a geocoding correction.
        
        Args:
            query: Original query
            correct_coords: Correct coordinates
            oblast: Oblast if known
            source: Source of correction
        """
        normalized = normalize_city(query)
        normalized_oblast = normalize_oblast(oblast) if oblast else None
        
        key = f"{normalized}_{normalized_oblast}" if normalized_oblast else normalized
        
        self._learning[key] = {
            'lat': correct_coords[0],
            'lng': correct_coords[1],
            'place': query,
            'oblast': normalized_oblast,
            'source': source,
            'timestamp': time.time(),
        }
        
        self._learning_dirty = True
        
        # Also add without region for fallback
        if normalized_oblast and normalized not in self._learning:
            self._learning[normalized] = self._learning[key].copy()
        
        # Remove from negative cache
        cache_key = f"{normalized}|{normalized_oblast or ''}"
        self._negative_cache.discard(cache_key)
        
        # Save periodically
        if len(self._learning) % 10 == 0:
            self._save_learning()
    
    def _load_learning(self):
        """Load learning corrections from file."""
        if not self._learning_file:
            return
        
        try:
            import json
            import os
            
            if os.path.exists(self._learning_file):
                with open(self._learning_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._learning = data.get('corrections', {})
                    log.info(f"Loaded {len(self._learning)} learned geocodes")
        except Exception as e:
            log.warning(f"Failed to load learning data: {e}")
    
    def _save_learning(self):
        """Save learning corrections to file."""
        if not self._learning_file or not self._learning_dirty:
            return
        
        try:
            import json
            
            with open(self._learning_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'corrections': self._learning,
                    'saved_at': time.time(),
                }, f, ensure_ascii=False, indent=2)
            
            self._learning_dirty = False
            log.debug(f"Saved {len(self._learning)} learned geocodes")
        except Exception as e:
            log.warning(f"Failed to save learning data: {e}")
    
    def stats(self) -> dict:
        """Get geocoding statistics."""
        return {
            'name': self.name,
            'learning_entries': len(self._learning),
            'negative_cache_size': len(self._negative_cache),
            **self._stats.to_dict(),
        }
    
    def clear_negative_cache(self):
        """Clear negative cache (for retry)."""
        self._negative_cache.clear()


def create_smart_geocoder(
    city_coords: dict,
    settlements: dict = None,
    settlements_by_oblast: dict = None,
    api_geocoders: list = None,
    cache = None,
    learning_file: str = None,
) -> SmartGeocoder:
    """
    Factory function to create configured SmartGeocoder.
    
    Args:
        city_coords: Main city coordinates dict
        settlements: All settlements dict
        settlements_by_oblast: Oblast-aware settlements
        api_geocoders: List of API geocoders
        cache: Response cache
        learning_file: Path for learning corrections
        
    Returns:
        Configured SmartGeocoder
    """
    from .local import LocalGeocoder
    
    local = LocalGeocoder(
        city_coords=city_coords,
        settlements=settlements,
        settlements_by_oblast=settlements_by_oblast,
    )
    
    return SmartGeocoder(
        local_geocoder=local,
        api_geocoders=api_geocoders or [],
        cache=cache,
        learning_file=learning_file,
    )
