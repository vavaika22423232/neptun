#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import CITY_COORDS, UA_CITY_NORMALIZE

def test_vyshgorod_coords():
    print("=== Перевірка координат Вишгорода ===")
    
    # Варіанти назв
    variants = [
        'вишгород',
        'вишгородський',
        'вишгородський р-н',
        'вишгородський район',
        'vyshgorod',
        'вишгор'
    ]
    
    for variant in variants:
        print(f"\nВаріант: '{variant}'")
        
        # Пряма перевірка в CITY_COORDS
        coords = CITY_COORDS.get(variant)
        print(f"  CITY_COORDS['{variant}']: {coords}")
        
        # Перевірка в UA_CITY_NORMALIZE
        normalized = UA_CITY_NORMALIZE.get(variant)
        print(f"  UA_CITY_NORMALIZE['{variant}']: {normalized}")
        if normalized:
            norm_coords = CITY_COORDS.get(normalized)
            print(f"  CITY_COORDS['{normalized}']: {norm_coords}")
    
    # Пошук часткових збігів
    print(f"\n=== Пошук часткових збігів ===")
    vysh_cities = [k for k in CITY_COORDS.keys() if 'вишгор' in k.lower()]
    print(f"Міста з 'вишгор': {vysh_cities[:10]}")  # Перші 10
    
    if vysh_cities:
        for city in vysh_cities[:5]:  # Перші 5
            coords = CITY_COORDS[city]
            print(f"  {city}: {coords}")

if __name__ == "__main__":
    test_vyshgorod_coords()
