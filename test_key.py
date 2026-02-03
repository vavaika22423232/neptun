#!/usr/bin/env python3
from opencage_geocoder import _normalize_key, geocode

# Test what key is generated
print("=== KEY GENERATION TEST ===")
tests = [
    ('межова', 'Дніпропетровська область'),
    ('межова', 'дніпропетровська'),
    ('межова', 'дніпропетровщина'),
]

for city, region in tests:
    key = _normalize_key(city, region)
    print(f"city={city!r}, region={region!r} => key={key!r}")

print("\n=== GEOCODE TEST ===")
# Now test actual geocode with the region format from app.py
result = geocode('межова', 'Дніпропетровська область')
print(f"geocode('межова', 'Дніпропетровська область') => {result}")

result2 = geocode('межова', 'дніпропетровська')
print(f"geocode('межова', 'дніпропетровська') => {result2}")
