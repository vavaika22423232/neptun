"""
Geocoding interface - base class for all geocoders.

Визначає контракт який мають імплементувати всі geocoder'и.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class GeocodingResult:
    """Result from geocoding operation."""
    coordinates: tuple[float, float]  # (lat, lng)
    place_name: Optional[str] = None
    source: str = 'unknown'
    confidence: float = 1.0
    raw_response: Optional[Any] = None


class GeocoderInterface(ABC):
    """
    Base interface for geocoding services.

    All geocoders must implement this interface.
    """

    @abstractmethod
    def geocode(
        self,
        query: str,
        region: Optional[str] = None,
    ) -> Optional[GeocodingResult]:
        """
        Convert location name to coordinates.

        Args:
            query: Location name to geocode
            region: Optional region hint for disambiguation

        Returns:
            GeocodingResult or None if not found
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this geocoder."""
        pass

    @property
    def priority(self) -> int:
        """
        Priority for geocoder chain (lower = tried first).
        Default is 50.
        """
        return 50

    @property
    def is_available(self) -> bool:
        """Check if geocoder is currently available."""
        return True

    def stats(self) -> dict:
        """Get geocoder statistics."""
        return {'name': self.name}
