"""
Data module for Neptune Ukraine monitoring system.

Contains static data like settlements, coordinates, etc.
"""

from data.geodata import (
    CITY_COORDS,
    UKRAINE_ALL_SETTLEMENTS,
    UKRAINE_SETTLEMENTS_BY_OBLAST,
    REGIONAL_CITY_COORDS,
    get_coords,
    get_regional_cities,
    load_settlements,
    stats as geodata_stats,
)

__all__ = [
    'CITY_COORDS',
    'UKRAINE_ALL_SETTLEMENTS', 
    'UKRAINE_SETTLEMENTS_BY_OBLAST',
    'REGIONAL_CITY_COORDS',
    'get_coords',
    'get_regional_cities',
    'load_settlements',
    'geodata_stats',
]
