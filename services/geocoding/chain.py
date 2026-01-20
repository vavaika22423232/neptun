"""
Geocoder chain - tries multiple geocoders in order.

Chain of Responsibility pattern для fallback logic.
"""
import logging
from typing import Optional

from .base import GeocoderInterface, GeocodingResult
from .cache import GeocodeCache

log = logging.getLogger(__name__)


class GeocoderChain(GeocoderInterface):
    """
    Tries multiple geocoders in priority order until one succeeds.

    Usage:
        chain = GeocoderChain(
            geocoders=[
                LocalGeocoder(city_coords),
                PhotonGeocoder(),
            ],
            cache=GeocodeCache()
        )

        result = chain.geocode("Київ")
    """

    def __init__(
        self,
        geocoders: list[GeocoderInterface],
        cache: Optional[GeocodeCache] = None,
    ):
        """
        Args:
            geocoders: List of geocoder instances to try
            cache: Optional geocode cache for results
        """
        # Sort by priority (lower = first)
        self._geocoders = sorted(geocoders, key=lambda g: g.priority)
        self._cache = cache

        # Stats
        self._total_requests = 0
        self._cache_hits = 0
        self._geocoder_hits = {g.name: 0 for g in geocoders}
        self._failures = 0

    @property
    def name(self) -> str:
        return "chain"

    @property
    def priority(self) -> int:
        return 0  # Chain is always top priority

    def geocode(
        self,
        query: str,
        region: Optional[str] = None,
    ) -> Optional[GeocodingResult]:
        """
        Try each geocoder until one succeeds.

        Args:
            query: Location name to geocode
            region: Optional region hint

        Returns:
            GeocodingResult or None if all failed
        """
        if not query or not query.strip():
            return None

        query = query.strip()
        self._total_requests += 1

        # Check cache first
        if self._cache:
            cached = self._cache.get(query, region)
            if cached:
                self._cache_hits += 1
                return cached

            # Check negative cache
            if self._cache.is_negative_cached(query):
                return None

        # Try each geocoder
        for geocoder in self._geocoders:
            if not geocoder.is_available:
                log.debug(f"Geocoder {geocoder.name} not available, skipping")
                continue

            try:
                result = geocoder.geocode(query, region)

                if result is not None:
                    log.debug(
                        f"Geocoded '{query}' via {geocoder.name}: "
                        f"{result.coordinates}"
                    )

                    # Cache result
                    if self._cache:
                        self._cache.put(query, result, region)

                    # Update stats
                    if geocoder.name in self._geocoder_hits:
                        self._geocoder_hits[geocoder.name] += 1

                    return result

            except Exception as e:
                log.warning(
                    f"Geocoder {geocoder.name} failed for '{query}': {e}"
                )
                continue

        # All geocoders failed
        log.debug(f"All geocoders failed for '{query}'")
        self._failures += 1

        # Add to negative cache
        if self._cache:
            self._cache.add_negative(query)

        return None

    def geocode_simple(
        self,
        query: str,
        region: Optional[str] = None,
    ) -> Optional[tuple[float, float]]:
        """
        Simple interface returning just coordinates.

        For backwards compatibility with existing code.
        """
        result = self.geocode(query, region)
        if result:
            return result.coordinates
        return None

    @property
    def available_geocoders(self) -> list[str]:
        """Get names of currently available geocoders."""
        return [g.name for g in self._geocoders if g.is_available]

    def stats(self) -> dict:
        """Get chain statistics."""
        return {
            'name': self.name,
            'total_requests': self._total_requests,
            'cache_hits': self._cache_hits,
            'failures': self._failures,
            'geocoder_hits': self._geocoder_hits,
            'available_geocoders': self.available_geocoders,
            'cache_stats': self._cache.stats() if self._cache else None,
        }
