#!/usr/bin/env python3
"""Check which cities from the message are missing coordinates."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import CITY_COORDS, UA_CITY_NORMALIZE, ensure_city_coords

# Cities from the new message
cities = [
    'суми', 'недригайлів', 'конотоп', 'терни', 'ромни', 'путивль', 'глухів',
    'чернігів', 'корюківку', 'ніжин', 'бахмач', 'десну', 'носівку', 'козелець', 'славутич',
    'карлівку', 'миргород',
    'черкаси',
    'страхолісся', 'велику димерку', 'бишів', 'кагарлик',
    'білокоровичі',
    'зміїв', 'краснопалівку', 'ізюм', 'лозову',
    'божедрівку', 'пʼятихатки', 'кринички', 'межову',
    'петрове',
    'запоріжжя',
    'брилівку'
]

print("Checking coordinates for cities from the message...")
print("=" * 60)

missing = []
found = []

for city in cities:
    # Normalize like parser does
    normalized = city.lower()
    if normalized.endswith('у'):
        normalized = normalized[:-1] + 'а'
    if normalized.endswith('ку'):
        normalized = normalized[:-2] + 'ка'
    
    # Check in normalization table
    final_name = UA_CITY_NORMALIZE.get(normalized, normalized)
    
    # Check coordinates
    coords = CITY_COORDS.get(final_name)
    
    if coords:
        found.append((city, final_name, coords))
        print(f"✅ {city} -> {final_name}: {coords}")
    else:
        missing.append((city, final_name))
        print(f"❌ {city} -> {final_name}: NO COORDINATES")

print(f"\n📊 Summary:")
print(f"Found: {len(found)}")
print(f"Missing: {len(missing)}")

if missing:
    print(f"\n🔧 Need to add coordinates for:")
    for orig, norm in missing:
        print(f"   {norm} (from {orig})")
        
print(f"\n🧪 Testing ensure_city_coords for missing cities...")
for orig, norm in missing[:3]:  # Test first 3 missing
    try:
        coords = ensure_city_coords(norm)
        if coords:
            print(f"📍 ensure_city_coords found {norm}: {coords}")
        else:
            print(f"❌ ensure_city_coords failed for {norm}")
    except Exception as e:
        print(f"💥 ensure_city_coords error for {norm}: {e}")
