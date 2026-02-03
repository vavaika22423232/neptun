#!/usr/bin/env python3
"""Test the unified geocoder (Visicom -> OpenCage fallback)"""

import os
import sys

# Test imports
print("=== TESTING GEOCODER IMPORTS ===")

try:
    from visicom_geocoder import visicom_geocode
    print("✓ Visicom geocoder imported")
    VISICOM_OK = True
except ImportError as e:
    print(f"✗ Visicom geocoder: {e}")
    VISICOM_OK = False

try:
    from opencage_geocoder import geocode as opencage_geocode_raw
    print("✓ OpenCage geocoder imported")
    OPENCAGE_OK = True
except ImportError as e:
    print(f"✗ OpenCage geocoder: {e}")
    OPENCAGE_OK = False

print()

# Unified geocoder function
def unified_geocode(city, region=None):
    """Tries Visicom first, falls back to OpenCage"""
    if VISICOM_OK:
        result = visicom_geocode(city, region)
        if result:
            return ('visicom', result)
    
    if OPENCAGE_OK:
        result = opencage_geocode_raw(city, region)
        if result:
            return ('opencage', result)
    
    return None

# Test cities
print("=== TESTING UNIFIED GEOCODER ===\n")

cities = [
    ('Межову', 'Дніпропетровська обл.'),
    ('Чаплине', 'Дніпропетровська обл.'),
    ('Семенівка', 'Полтавська обл.'),
    ('Хорол', 'Полтавська обл.'),
    ('Богодухів', 'Харківська обл.'),
    ('Гути', 'Харківська обл.'),
    ('Павлоград', 'Дніпропетровська обл.'),
    ('Синельникове', 'Дніпропетровська обл.'),
    ('Запоріжжя', 'Запорізька обл.'),
    ('Херсон', 'Херсонська обл.'),
    ('Дніпровське', 'Миколаївська обл.'),
    ('Дмитрівка', 'Дніпропетровська обл.'),
]

found = 0
for city, region in cities:
    result = unified_geocode(city, region)
    if result:
        source, coords = result
        print(f"✓ {city} ({region}) => {coords} [{source}]")
        found += 1
    else:
        print(f"✗ {city} ({region}) => NOT FOUND")

print(f"\n=== RESULT: {found}/{len(cities)} cities found ===")
