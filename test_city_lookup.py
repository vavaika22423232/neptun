#!/usr/bin/env python3
"""
Test script for specific city coordinate lookup
"""

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import CITY_COORDS, UA_CITY_NORMALIZE

def test_city_lookup():
    """Test coordinate lookup for problematic cities"""
    
    test_cities = [
        "Доброслав",
        "доброслав",
        "Березнегувате", 
        "березнегувате",
        "Очаків",
        "очаків", 
        "Велику Виску",
        "велику виску",
        "Велика Виска",
        "велика виска"
    ]
    
    print("Testing city coordinate lookup:")
    for city in test_cities:
        coords = CITY_COORDS.get(city.lower())
        normalized = UA_CITY_NORMALIZE.get(city.lower())
        
        print(f"City: '{city}'")
        print(f"  Direct lookup: {bool(coords)}")
        print(f"  Normalized: {normalized}")
        if normalized:
            norm_coords = CITY_COORDS.get(normalized.lower())
            print(f"  Normalized coords: {bool(norm_coords)}")
        print()

if __name__ == "__main__":
    test_city_lookup()
