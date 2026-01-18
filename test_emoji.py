#!/usr/bin/env python3
import re

# Test with emoji after city name
head = 'БПЛА Вільхівку⚠ (Харківська обл.)'
print(f'Input: {head}')

# Current pattern (FAILS)
pattern_old = r'^[^\w]*БПЛА\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+?)\s*\(([^)]+обл[^)]*)\)'
match_old = re.search(pattern_old, head, re.IGNORECASE)
print(f'Old pattern match: {match_old}')

# New pattern with emoji support
pattern_new = r'^[^\w]*БПЛА\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+?)[⚠️🔴⛔❗‼️⚡🚨]*\s*\(([^)]+обл[^)]*)\)'
match_new = re.search(pattern_new, head, re.IGNORECASE)
if match_new:
    print(f'New pattern: city="{match_new.group(1)}", oblast="{match_new.group(2)}"')
else:
    print('New pattern: NO MATCH')

# Even more permissive - any non-cyrillic chars before (
pattern_v3 = r'^[^\w]*БПЛА\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)'
match_v3 = re.search(pattern_v3, head, re.IGNORECASE)
if match_v3:
    city = match_v3.group(1).strip()
    oblast = match_v3.group(2).strip()
    print(f'V3 pattern: city="{city}", oblast="{oblast}"')
    
    # Normalize
    city_norm = city.lower()
    if city_norm.endswith('ку'):
        city_norm = city_norm[:-2] + 'ка'
    elif city_norm.endswith('у'):
        city_norm = city_norm[:-1] + 'а'
    print(f'Normalized: "{city_norm}"')
    
    # Check
    from ukraine_all_settlements import UKRAINE_SETTLEMENTS_BY_OBLAST
    key = (city_norm, 'харківська')
    print(f'Lookup {key}: {UKRAINE_SETTLEMENTS_BY_OBLAST.get(key)}')
