#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to extract all Volyn settlements from city_ukraine.json and add them to app.py
"""

import json
import re

# Read city_ukraine.json
with open('city_ukraine.json', 'r', encoding='utf-8') as f:
    cities_data = json.load(f)

# Extract all Volyn settlements
volyn_settlements = []
for entry in cities_data:
    if entry.get('region') == 'ВОЛИНСЬКА ОБЛАСТЬ':
        name = entry.get('object_name', '').lower()
        if name:
            volyn_settlements.append(name)

# Remove duplicates and sort
volyn_settlements = sorted(set(volyn_settlements))

print(f"Found {len(volyn_settlements)} unique Volyn settlements:")
print("\nFirst 20 settlements:")
for i, settlement in enumerate(volyn_settlements[:20]):
    print(f"{i+1:2d}. {settlement}")

if len(volyn_settlements) > 20:
    print(f"\n... and {len(volyn_settlements) - 20} more settlements")

# Generate the dictionary entries for app.py
print("\n" + "="*60)
print("VOLYN_CITY_COORDS entries to add to app.py:")
print("="*60)

print("VOLYN_CITY_COORDS = {")
for settlement in volyn_settlements:
    # For now, use placeholder coordinates - these would need to be looked up
    print(f"    '{settlement}': (50.7472, 25.3254),  # TODO: Get actual coordinates")
print("}")

print("\nfor _volyn_name, _volyn_coords in VOLYN_CITY_COORDS.items():")
print("    CITY_COORDS.setdefault(_volyn_name, _volyn_coords)")

# Count by object category
category_counts = {}
for entry in cities_data:
    if entry.get('region') == 'ВОЛИНСЬКА ОБЛАСТЬ':
        category = entry.get('object_category', 'Unknown')
        category_counts[category] = category_counts.get(category, 0) + 1

print(f"\nSettlement types in Volyn Oblast:")
for category, count in sorted(category_counts.items()):
    print(f"  {category}: {count}")

print(f"\nTotal Volyn settlements: {sum(category_counts.values())}")
