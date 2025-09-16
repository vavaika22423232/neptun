#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import CITY_COORDS, UA_CITY_NORMALIZE

def check_city_coords():
    print("=== Checking City Coordinates ===")
    
    test_cities = [
        'ніжин', 'ніжина', 'ніжину',  # разные падежи
        'слатине', 'слатина',
        'диканька', 'диканьку'
    ]
    
    for city in test_cities:
        print(f"'{city}':")
        
        # Прямой поиск
        direct_coords = CITY_COORDS.get(city)
        print(f"  Direct lookup: {direct_coords}")
        
        # Поиск через нормализацию
        norm_city = UA_CITY_NORMALIZE.get(city, city)
        norm_coords = CITY_COORDS.get(norm_city)
        print(f"  Normalized '{norm_city}': {norm_coords}")
        
        print()

if __name__ == "__main__":
    check_city_coords()
