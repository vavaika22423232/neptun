# Core Data package
from core.data.regions import (
    OBLAST_PCODE, OBLAST_CENTERS, CITY_TO_OBLAST,
    UA_CITY_NORMALIZE, REGION_ALIASES,
    normalize_region_name, get_oblast_center, match_region
)

__all__ = [
    'OBLAST_PCODE', 'OBLAST_CENTERS', 'CITY_TO_OBLAST',
    'UA_CITY_NORMALIZE', 'REGION_ALIASES',
    'normalize_region_name', 'get_oblast_center', 'match_region'
]
