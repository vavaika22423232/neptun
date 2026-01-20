#!/usr/bin/env python3
"""Isolated test for trajectory parsing fixes"""
import re

# Mini version of OBLAST_CENTERS for testing
OBLAST_CENTERS = {
    'вінницька область': (49.2331, 28.4682),
    'вінниччина': (49.2331, 28.4682),
    'вінничина': (49.2331, 28.4682),
    'миколаївська область': (46.9750, 31.9946),
    'миколаївщина': (46.9750, 31.9946),
    'київська область': (50.4501, 30.5234),
    'київщина': (50.4501, 30.5234),
    'полтавська область': (49.5883, 34.5514),
    'полтавщина': (49.5883, 34.5514),
    'одеська область': (46.4825, 30.7233),
    'одещина': (46.4825, 30.7233),
}

CITY_COORDS = {
    'миколаїв': (46.9750, 31.9946),
    'київ': (50.4501, 30.5234),
    'одеса': (46.4825, 30.7233),
    'полтава': (49.5883, 34.5514),
    'вінниця': (49.2331, 28.4682),
}

def _get_region_center(region_name):
    """Get center coordinates for a region (oblast)"""
    region_lower = region_name.lower().strip()
    # Check in OBLAST_CENTERS directly
    if region_lower in OBLAST_CENTERS:
        return OBLAST_CENTERS[region_lower]

    # Normalize instrumental case "над вінницькою областю" → "вінницька область"
    # Pattern: Xькою областю → Xька область
    instrumental_match = re.match(r'^(.+?)(ькою|ською|цькою)\s*(областю|обл\.?)$', region_lower)
    if instrumental_match:
        base = instrumental_match.group(1)
        # Convert back to nominative: ькою→ька, ською→ська, цькою→цька
        suffix_map = {'ькою': 'ька', 'ською': 'ська', 'цькою': 'цька'}
        new_suffix = suffix_map.get(instrumental_match.group(2), 'ька')
        normalized = f"{base}{new_suffix} область"
        if normalized in OBLAST_CENTERS:
            return OBLAST_CENTERS[normalized]
        # Try without ' область'
        normalized_short = f"{base}{new_suffix}"
        if normalized_short in OBLAST_CENTERS:
            return OBLAST_CENTERS[normalized_short]

    # Try removing common endings and searching again
    base_region = region_lower
    for ending in ['щині', 'щину', 'щини', 'щина', 'ччині', 'ччину', 'ччини', 'ччина']:
        if region_lower.endswith(ending):
            base_region = region_lower[:-len(ending)]
            break

    # Try to find with base + common endings
    for ending in ['щина', 'щини', 'ччина', 'ччини']:
        test_key = base_region + ending
        if test_key in OBLAST_CENTERS:
            return OBLAST_CENTERS[test_key]

    # Try partial match
    for key, coords in OBLAST_CENTERS.items():
        if base_region in key or key.startswith(base_region):
            return coords

    return None


def _get_city_coords(city_name):
    """Get coordinates for a city"""
    city_lower = city_name.lower().strip()
    # Remove prefixes like "м.", "н.п.", "с."
    city_lower = re.sub(r'^(м\.|м\s|н\.п\.|н\.п\s|с\.|с\s|сел\.|смт\.?|смт\s)', '', city_lower).strip()

    # Check in CITY_COORDS
    if city_lower in CITY_COORDS:
        return CITY_COORDS[city_lower]

    # Try variations without endings
    endings = ['а', 'у', 'ом', 'і', 'ів', 'ами', 'е', 'ої', 'ою']
    for ending in endings:
        if city_lower.endswith(ending) and len(city_lower) > len(ending) + 2:
            base = city_lower[:-len(ending)]
            if base in CITY_COORDS:
                return CITY_COORDS[base]

    # Handle Ukrainian vowel alternation in genitive: миколаєва → миколаїв
    # Pattern: base + 'єва' (genitive) → base + 'їв' (nominative)
    if city_lower.endswith('єва'):
        base = city_lower[:-3] + 'їв'  # миколаєва → миколаїв
        if base in CITY_COORDS:
            return CITY_COORDS[base]

    # Also try simple base search for partial matches
    for key, coords in CITY_COORDS.items():
        if city_lower.startswith(key) or key.startswith(city_lower.rstrip('аеоуіїю')):
            return coords

    return None


if __name__ == '__main__':
    print("=== Тест _get_region_center ===")
    tests = [
        ('вінницькою областю', 'Should find Вінницька'),
        ('миколаївською областю', 'Should find Миколаївська'),
        ('київською областю', 'Should find Київська'),
        ('вінницька область', 'Direct match'),
        ('вінниччина', 'Direct -щина form'),
    ]
    for t, desc in tests:
        result = _get_region_center(t)
        status = '✓' if result else '✗'
        print(f"  {status} '{t}' -> {result}  ({desc})")

    print("\n=== Тест _get_city_coords ===")
    city_tests = [
        ('миколаєва', 'Genitive єва→їв'),
        ('миколаїв', 'Direct match'),
        ('київ', 'Direct match'),
        ('києва', 'Genitive а→None'),
        ('одеси', 'Genitive и→а'),
    ]
    for t, desc in city_tests:
        result = _get_city_coords(t)
        status = '✓' if result else '✗'
        print(f"  {status} '{t}' -> {result}  ({desc})")
