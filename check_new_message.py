#!/usr/bin/env python3
"""Check coordinates for cities in the new napramok message."""

import sys
sys.path.insert(0, '.')

# Import coordinate data
try:
    from app import CITY_COORDS, UA_CITY_NORMALIZE
    print("Successfully imported coordinate data")
except Exception as e:
    print(f"Failed to import: {e}")
    sys.exit(1)

# Cities from the new message
cities_from_message = [
    'недригайлів', 'липову долину', 'конотоп',
    'прилуки', 'корюківку', 'ніжин', 'десну', 'кіпті', 'ічню', 'гончарівське',
    'гадяч', 'кременчук', 'миргород',
    'цвіткове',
    'страхолісся', 'білу церкву', 'київ', 'бровари', 'бишів',
    'коростень', 'чоповичі', 'звягель', 'радомишль',
    'сахновщину',
    'камʼянське', 'солоне',
    'кропивницький', 'піщаний брід', 'бобринець', 'петрове',
    'тендрівську косу'
]

print(f"Checking {len(cities_from_message)} cities from new message...")
print("=" * 60)

found = 0
missing = []

for city in cities_from_message:
    # Try direct lookup
    if city in CITY_COORDS:
        print(f"✅ {city} - direct match")
        found += 1
        continue
    
    # Try normalized lookup
    normalized = UA_CITY_NORMALIZE.get(city, city)
    if normalized in CITY_COORDS:
        print(f"✅ {city} → {normalized} - normalized match")
        found += 1
        continue
    
    # Not found
    print(f"❌ {city} - NOT FOUND")
    missing.append(city)

print("=" * 60)
print(f"SUMMARY:")
print(f"Found: {found}/{len(cities_from_message)}")
print(f"Missing: {len(missing)}")

if missing:
    print(f"\nMissing cities: {missing}")
else:
    print(f"\n🎉 ALL CITIES HAVE COORDINATES!")
