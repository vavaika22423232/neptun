#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to extract all Volyn settlements with coordinates from city_ukraine.json
and generate VOLYN_CITY_COORDS for app.py
"""

import json
import re

# Read city_ukraine.json
with open('city_ukraine.json', 'r', encoding='utf-8') as f:
    cities_data = json.load(f)

# Extract all Volyn settlements with coordinates
volyn_settlements = {}
for entry in cities_data:
    if entry.get('region') == 'ВОЛИНСЬКА ОБЛАСТЬ':
        name = entry.get('object_name', '').lower()
        # For now, we'll use the oblast center coordinates as placeholder
        # In a real implementation, you'd need to get actual coordinates for each settlement
        lat = 50.7472  # Lutsk coordinates as placeholder
        lon = 25.3254  # Lutsk coordinates as placeholder
        
        if name and name not in volyn_settlements:
            volyn_settlements[name] = (lat, lon)

# Sort settlements alphabetically
volyn_settlements = dict(sorted(volyn_settlements.items()))

print(f"Found {len(volyn_settlements)} unique Volyn settlements")

# Generate the VOLYN_CITY_COORDS section for app.py
print("\n# Volyn Oblast settlements (added automatically)")
print("VOLYN_CITY_COORDS = {")

for name, (lat, lon) in volyn_settlements.items():
    print(f"    '{name}': ({lat:.4f}, {lon:.4f}),")

print("}")
print()
print("for _volyn_name, _volyn_coords in VOLYN_CITY_COORDS.items():")
print("    CITY_COORDS.setdefault(_volyn_name, _volyn_coords)")

# Count by object category
category_counts = {}
major_cities = []
for entry in cities_data:
    if entry.get('region') == 'ВОЛИНСЬКА ОБЛАСТЬ':
        category = entry.get('object_category', 'Unknown')
        category_counts[category] = category_counts.get(category, 0) + 1
        
        if category == 'Місто':
            major_cities.append(entry.get('object_name', '').lower())

print(f"\nMajor cities in Volyn Oblast ({len(major_cities)}):")
for city in sorted(major_cities):
    print(f"  - {city}")

print(f"\nSettlement breakdown:")
for category, count in sorted(category_counts.items()):
    print(f"  {category}: {count}")

print(f"\nTotal Volyn settlements: {sum(category_counts.values())}")

# Write to a file for easy insertion into app.py
with open('volyn_city_coords.py', 'w', encoding='utf-8') as f:
    f.write("# Volyn Oblast settlements (auto-generated)\n")
    f.write("VOLYN_CITY_COORDS = {\n")
    for name, (lat, lon) in volyn_settlements.items():
        f.write(f"    '{name}': ({lat:.4f}, {lon:.4f}),\n")
    f.write("}\n\n")
    f.write("for _volyn_name, _volyn_coords in VOLYN_CITY_COORDS.items():\n")
    f.write("    CITY_COORDS.setdefault(_volyn_name, _volyn_coords)\n")

print(f"\nGenerated volyn_city_coords.py with all {len(volyn_settlements)} settlements")
