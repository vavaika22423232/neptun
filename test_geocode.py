#!/usr/bin/env python3
from opencage_geocoder import geocode

tests = [
    ('Семенівка', 'полтавщина'),
    ('Хорол', 'полтавщина'),
    ('Синельникове', 'дніпропетровщина'),
    ('Запоріжжя', 'запорізька'),
    ('Кривий Ріг', 'дніпропетровщина'),
    ('Богодухів', 'харківщина'),
    ('Павлоград', 'дніпропетровщина'),
    ('Марганець', 'дніпропетровщина'),
    ('Гути', 'харківщина'),
    ('Чаплине', 'дніпропетровщина'),
    ('Межова', 'дніпропетровщина'),
]

print("=" * 60)
print("TEST GEOCODING")
print("=" * 60)

for city, region in tests:
    coords = geocode(city, region)
    if coords:
        print(f"OK: {city} ({region}) => {coords[0]:.4f}, {coords[1]:.4f}")
    else:
        print(f"FAIL: {city} ({region}) => None")
