"""
Local geocoder using pre-loaded coordinate dictionaries.

Найшвидший geocoder - не робить HTTP запитів.
Використовує CITY_COORDS та UKRAINE_ALL_SETTLEMENTS.
"""
import re
from typing import Optional

from .base import GeocoderInterface, GeocodingResult


class LocalGeocoder(GeocoderInterface):
    """
    Geocoder using local coordinate dictionaries.

    Переваги:
    - Миттєвий (без мережевих запитів)
    - Працює офлайн
    - Не має rate limits

    Недоліки:
    - Обмежена база даних
    - Потрібно оновлювати вручну
    """

    def __init__(
        self,
        city_coords: dict[str, tuple[float, float]],
        settlements: Optional[dict[str, tuple[float, float]]] = None,
        settlements_by_oblast: Optional[dict[str, dict[str, tuple[float, float]]]] = None,
    ):
        """
        Args:
            city_coords: Main city coordinates {normalized_name: (lat, lon)}
            settlements: All settlements {normalized_name: (lat, lon)}
            settlements_by_oblast: Oblast-aware settlements {oblast: {name: (lat, lon)}}
        """
        self._city_coords = city_coords or {}
        self._settlements = settlements or {}
        self._settlements_by_oblast = settlements_by_oblast or {}

    @property
    def name(self) -> str:
        return "local"

    @property
    def priority(self) -> int:
        return 10  # Highest priority (try first)

    def geocode(
        self,
        query: str,
        region: Optional[str] = None,
    ) -> Optional[GeocodingResult]:
        """
        Find coordinates for location name.

        Search order:
        1. Exact match in city_coords
        2. Normalized match in city_coords
        3. Oblast-specific settlements (if region provided)
        4. All settlements
        """
        if not query:
            return None

        normalized = self._normalize(query)

        # 1. Exact match in main cities
        if normalized in self._city_coords:
            coords = self._city_coords[normalized]
            return GeocodingResult(
                coordinates=coords,
                place_name=query,
                source=self.name,
                confidence=1.0,
            )

        # 2. Try variations
        for variant in self._get_variants(normalized):
            if variant in self._city_coords:
                coords = self._city_coords[variant]
                return GeocodingResult(
                    coordinates=coords,
                    place_name=query,
                    source=self.name,
                    confidence=0.9,
                )

        # 3. Oblast-specific search
        if region and self._settlements_by_oblast:
            region_key = self._normalize_region(region)
            if region_key in self._settlements_by_oblast:
                oblast_settlements = self._settlements_by_oblast[region_key]
                if normalized in oblast_settlements:
                    coords = oblast_settlements[normalized]
                    return GeocodingResult(
                        coordinates=coords,
                        place_name=f"{query}, {region}",
                        source=self.name,
                        confidence=0.95,
                    )

                # Try variants in oblast
                for variant in self._get_variants(normalized):
                    if variant in oblast_settlements:
                        coords = oblast_settlements[variant]
                        return GeocodingResult(
                            coordinates=coords,
                            place_name=f"{query}, {region}",
                            source=self.name,
                            confidence=0.85,
                        )

        # 4. All settlements search
        if self._settlements:
            if normalized in self._settlements:
                coords = self._settlements[normalized]
                return GeocodingResult(
                    coordinates=coords,
                    place_name=query,
                    source=self.name,
                    confidence=0.8,
                )

            for variant in self._get_variants(normalized):
                if variant in self._settlements:
                    coords = self._settlements[variant]
                    return GeocodingResult(
                        coordinates=coords,
                        place_name=query,
                        source=self.name,
                        confidence=0.7,
                    )

        return None

    def _normalize(self, name: str) -> str:
        """Normalize location name for matching."""
        if not name:
            return ""

        # Lowercase
        result = name.lower().strip()

        # Remove common prefixes/suffixes
        prefixes_to_remove = [
            'м.', 'м ', 'с.', 'с ', 'смт.', 'смт ',
            'село ', 'місто ', 'селище ',
        ]
        for prefix in prefixes_to_remove:
            if result.startswith(prefix):
                result = result[len(prefix):].strip()

        # Remove directional suffixes like "курсом на ..."
        result = re.sub(r'\s+курсом?\s+на\s+.*$', '', result)
        result = re.sub(r'\s+напрям(?:ок|ку)?\s+на\s+.*$', '', result)

        # Remove region suffixes
        result = re.sub(r'\s*\(.*область.*\)$', '', result)
        result = re.sub(r'\s*,\s*.*область.*$', '', result)

        # Normalize apostrophes and quotes
        result = result.replace("'", "'").replace("`", "'").replace("ʼ", "'")

        # Remove extra whitespace
        result = ' '.join(result.split())

        return result

    def _normalize_region(self, region: str) -> str:
        """Normalize region name for dict lookup."""
        if not region:
            return ""

        result = region.lower().strip()

        # Remove 'область', 'ська' endings
        result = re.sub(r'\s*область\s*$', '', result)
        result = re.sub(r'ська\s*$', '', result)
        result = re.sub(r'ький\s*$', '', result)

        return result.strip()

    def _get_variants(self, normalized: str) -> list:
        """Generate name variants for fuzzy matching."""
        variants = []

        # Without common suffixes
        for suffix in ['ка', 'ки', 'ку', 'ці', 'ий', 'а', 'і', 'у']:
            if normalized.endswith(suffix) and len(normalized) > len(suffix) + 2:
                variants.append(normalized[:-len(suffix)])

        # With common suffixes if not present
        if not normalized.endswith(('ка', 'ки', 'ський', 'ське')):
            variants.extend([
                normalized + 'ка',
                normalized + 'ки',
            ])

        return variants

    def stats(self) -> dict[str, int]:
        """Get statistics about loaded data."""
        return {
            'city_coords': len(self._city_coords),
            'settlements': len(self._settlements),
            'oblasts_with_settlements': len(self._settlements_by_oblast),
        }
