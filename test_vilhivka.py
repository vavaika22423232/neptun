#!/usr/bin/env python3
import re

head = 'БПЛА Вільхівка (Харківська обл.)'

# Pattern from app.py
mapstransler_pattern2 = r'^[^\w]*БПЛА\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s]+?)\s*\(([^)]+обл[^)]*)\)'
match = re.search(mapstransler_pattern2, head, re.IGNORECASE)
if match:
    city_raw = match.group(1).strip()
    oblast_raw = match.group(2).strip()
    print(f'City: {city_raw}')
    print(f'Oblast: {oblast_raw}')
    
    # Normalize city
    city_norm = city_raw.lower()
    print(f'City norm: {city_norm}')
    
    # Extract oblast key
    oblast_lower = oblast_raw.lower()
    if 'харківська' in oblast_lower:
        oblast_key = 'харківська'
        print(f'Oblast key: {oblast_key}')
    
    # Check in UKRAINE_SETTLEMENTS_BY_OBLAST
    from ukraine_all_settlements import UKRAINE_SETTLEMENTS_BY_OBLAST
    key = (city_norm, oblast_key)
    print(f'Lookup key: {key}')
    print(f'Result: {UKRAINE_SETTLEMENTS_BY_OBLAST.get(key)}')
else:
    print('No match!')
