#!/usr/bin/env python3
import re

head = 'БПЛА Федорівку/Піщане (Харківська обл.)'

# Pattern from app.py
mapstransler_pattern2 = r'^[^\w]*БПЛА\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s]+?)\s*\(([^)]+обл[^)]*)\)'
match = re.search(mapstransler_pattern2, head, re.IGNORECASE)
if match:
    city_raw = match.group(1).strip()
    oblast_raw = match.group(2).strip()
    print(f'City: "{city_raw}"')
    print(f'Oblast: "{oblast_raw}"')
else:
    print('Pattern 1: No match!')

# Try with slash in pattern
mapstransler_pattern3 = r'^[^\w]*БПЛА\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+?)\s*\(([^)]+обл[^)]*)\)'
match2 = re.search(mapstransler_pattern3, head, re.IGNORECASE)
if match2:
    city_raw = match2.group(1).strip()
    oblast_raw = match2.group(2).strip()
    print(f'Pattern with /: City: "{city_raw}"')
    print(f'Pattern with /: Oblast: "{oblast_raw}"')

    # Split by slash and take first
    cities = city_raw.split('/')
    print(f'Cities: {cities}')
    first_city = cities[0].strip().lower()
    print(f'First city: "{first_city}"')

    # Normalize accusative -> nominative
    if first_city.endswith('ку'):
        first_city = first_city[:-2] + 'ка'
    elif first_city.endswith('у'):
        first_city = first_city[:-1] + 'а'
    print(f'Normalized: "{first_city}"')

    # Check in dictionary
    from ukraine_all_settlements import UKRAINE_SETTLEMENTS_BY_OBLAST
    key = (first_city, 'харківська')
    print(f'Lookup: {key} -> {UKRAINE_SETTLEMENTS_BY_OBLAST.get(key)}')
else:
    print('Pattern 2: No match!')
