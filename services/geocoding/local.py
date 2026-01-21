"""
Local geocoder using pre-loaded coordinate dictionaries.

Найшвидший geocoder - не робить HTTP запитів.
Використовує CITY_COORDS та UKRAINE_ALL_SETTLEMENTS.

СТРУКТУРА ДАНИХ:
- CITY_COORDS: {city_name: (lat, lon)} - 120 основних міст
- UKRAINE_ALL_SETTLEMENTS: {normalized_name: (lat, lon)} - 24862 населених пунктів
- UKRAINE_SETTLEMENTS_BY_OBLAST: {(name, oblast): (lat, lon)} - 35019 записів з областю
"""
import logging
from typing import Dict, List, Optional, Tuple

from .base import GeocoderInterface, GeocodingResult
from .normalizer import get_name_variants, normalize_city, normalize_oblast

log = logging.getLogger(__name__)


class LocalGeocoder(GeocoderInterface):
    """
    Geocoder using local coordinate dictionaries.

    Переваги:
    - Миттєвий (без мережевих запитів)
    - Працює офлайн
    - Не має rate limits
    - 26000+ населених пунктів

    Пошук:
    1. Точний збіг в основних містах
    2. Варіанти назв (відмінки)
    3. По області (якщо вказано) - шукає в settlements_by_oblast
    4. Всі населені пункти (settlements)
    """

    def __init__(
        self,
        city_coords: Optional[Dict] = None,
        settlements: Optional[Dict] = None,
        settlements_by_oblast: Optional[Dict] = None,
    ):
        """
        Args:
            city_coords: Main city coordinates {name: (lat, lon)} or {name: [lat, lon]}
            settlements: All settlements {normalized_name: (lat, lon)}
            settlements_by_oblast: {(settlement_name, oblast_name): (lat, lon)}
                                   OR {oblast: {name: (lat, lon)}}
        """
        # Normalize city_coords
        self._city_coords: Dict[str, Tuple[float, float]] = {}
        for name, coords in (city_coords or {}).items():
            normalized = normalize_city(name)
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                self._city_coords[normalized] = (float(coords[0]), float(coords[1]))
        
        # Settlements by normalized name
        self._settlements: Dict[str, Tuple[float, float]] = {}
        for name, coords in (settlements or {}).items():
            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                self._settlements[name] = (float(coords[0]), float(coords[1]))
        
        # Process settlements_by_oblast
        # Format can be:
        # A) {(settlement, oblast): coords} - tuple keys
        # B) {oblast: {settlement: coords}} - nested dict
        self._settlements_by_name_oblast: Dict[Tuple[str, str], Tuple[float, float]] = {}
        self._oblasts_for_settlement: Dict[str, List[str]] = {}
        
        if settlements_by_oblast:
            # Check format by first key
            first_key = next(iter(settlements_by_oblast.keys()), None)
            
            if isinstance(first_key, tuple):
                # Format A: {(settlement, oblast): coords}
                for (settlement, oblast), coords in settlements_by_oblast.items():
                    if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                        key = (settlement.lower(), oblast.lower())
                        self._settlements_by_name_oblast[key] = (float(coords[0]), float(coords[1]))
                        
                        # Build reverse index
                        if settlement.lower() not in self._oblasts_for_settlement:
                            self._oblasts_for_settlement[settlement.lower()] = []
                        if oblast.lower() not in self._oblasts_for_settlement[settlement.lower()]:
                            self._oblasts_for_settlement[settlement.lower()].append(oblast.lower())
            
            elif isinstance(first_key, str):
                # Format B: {oblast: {settlement: coords}}
                for oblast, setts in settlements_by_oblast.items():
                    if isinstance(setts, dict):
                        oblast_lower = oblast.lower()
                        for settlement, coords in setts.items():
                            if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                                key = (settlement.lower(), oblast_lower)
                                self._settlements_by_name_oblast[key] = (float(coords[0]), float(coords[1]))
                                
                                if settlement.lower() not in self._oblasts_for_settlement:
                                    self._oblasts_for_settlement[settlement.lower()] = []
                                if oblast_lower not in self._oblasts_for_settlement[settlement.lower()]:
                                    self._oblasts_for_settlement[settlement.lower()].append(oblast_lower)
        
        log.info(f"LocalGeocoder initialized: {len(self._city_coords)} cities, "
                 f"{len(self._settlements)} settlements, "
                 f"{len(self._settlements_by_name_oblast)} oblast-entries")

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
        2. Variants in city_coords
        3. Oblast-specific settlements (if region provided)
        4. All settlements with variants
        """
        if not query:
            return None

        normalized = normalize_city(query)
        if not normalized:
            return None
        
        # Normalize region
        normalized_region = normalize_oblast(region) if region else None

        # 1. Exact match in main cities
        if normalized in self._city_coords:
            coords = self._city_coords[normalized]
            return GeocodingResult(
                coordinates=coords,
                place_name=query,
                source=self.name,
                confidence=1.0,
            )

        # 2. Try variants in city_coords
        variants = get_name_variants(normalized)
        for variant in variants[1:]:  # Skip first (already tried)
            if variant in self._city_coords:
                coords = self._city_coords[variant]
                return GeocodingResult(
                    coordinates=coords,
                    place_name=query,
                    source=self.name,
                    confidence=0.95,
                )

        # 3. Oblast-specific search (most accurate for small villages)
        if normalized_region and self._settlements_by_name_oblast:
            result = self._search_in_oblast(normalized, variants, normalized_region, query)
            if result:
                return result

        # 4. All settlements (exact)
        if self._settlements:
            if normalized in self._settlements:
                coords = self._settlements[normalized]
                return GeocodingResult(
                    coordinates=coords,
                    place_name=query,
                    source=self.name,
                    confidence=0.85,
                )

            # 5. Variants in settlements
            for variant in variants[1:]:
                if variant in self._settlements:
                    coords = self._settlements[variant]
                    return GeocodingResult(
                        coordinates=coords,
                        place_name=query,
                        source=self.name,
                        confidence=0.8,
                    )

        return None

    def _search_in_oblast(
        self,
        normalized: str,
        variants: List[str],
        oblast: str,
        original_query: str,
    ) -> Optional[GeocodingResult]:
        """Search in specific oblast's settlements using tuple keys."""
        # Direct key lookup (most common)
        key = (normalized, oblast)
        if key in self._settlements_by_name_oblast:
            coords = self._settlements_by_name_oblast[key]
            return GeocodingResult(
                coordinates=coords,
                place_name=original_query,
                source=self.name,
                confidence=0.95,
            )
        
        # Try variants
        for variant in variants:
            key = (variant, oblast)
            if key in self._settlements_by_name_oblast:
                coords = self._settlements_by_name_oblast[key]
                return GeocodingResult(
                    coordinates=coords,
                    place_name=original_query,
                    source=self.name,
                    confidence=0.9,
                )
        
        # Try partial oblast match (e.g., "харківська" vs "харківська область")
        for variant in [normalized] + variants:
            for (name, obl), coords in self._settlements_by_name_oblast.items():
                if name == variant and (oblast in obl or obl in oblast):
                    return GeocodingResult(
                        coordinates=coords,
                        place_name=original_query,
                        source=self.name,
                        confidence=0.88,
                    )
        
        return None

    def get_oblasts_for_settlement(self, settlement: str) -> List[str]:
        """Get list of oblasts where settlement exists (for disambiguation)."""
        normalized = normalize_city(settlement)
        return self._oblasts_for_settlement.get(normalized, [])

    def stats(self) -> dict:
        """Get geocoder statistics."""
        return {
            'name': self.name,
            'city_coords': len(self._city_coords),
            'settlements': len(self._settlements),
            'oblast_entries': len(self._settlements_by_name_oblast),
            'unique_settlements_with_oblast': len(self._oblasts_for_settlement),
        }

    def add_city(self, name: str, coords: tuple, region: Optional[str] = None):
        """Add or update city coordinates."""
        normalized = normalize_city(name)
        self._city_coords[normalized] = coords
        
        if region:
            normalized_region = normalize_oblast(region)
            if normalized_region:
                key = (normalized, normalized_region)
                self._settlements_by_name_oblast[key] = coords
