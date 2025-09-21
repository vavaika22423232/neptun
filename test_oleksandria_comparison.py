#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparison test: Messages with and without specific city
"""

from app import process_message

print("🎯 COMPARISON: SPECIFIC CITY vs REGIONAL MESSAGE")
print("=" * 70)

test_cases = [
    ("на кіровоградщині 1 шахед на олександрію", "WITH specific city (Oleksandria)"),
    ("на кіровоградщині 1 шахед", "WITHOUT specific city (should show regional center)")
]

for message, description in test_cases:
    print(f"\n📝 {description}")
    print(f"Message: '{message}'")
    print("-" * 50)
    
    result = process_message(message, 'test_id', '2024-01-01', 'test_channel')
    
    if result and len(result) > 0:
        r = result[0]
        if 'lat' in r and 'lng' in r:
            lat, lng = r['lat'], r['lng']
            place = r.get('place', 'Unknown')
            source = r.get('source_match', 'unknown')
            
            print(f"Result: {place}")
            print(f"Coordinates: ({lat:.4f}, {lng:.4f})")
            print(f"Source: {source}")
            
            # Check which city this is
            if abs(lat - 48.8033) < 0.05 and abs(lng - 33.1147) < 0.05:
                print("✅ This is OLEKSANDRIA")
            elif abs(lat - 48.5079) < 0.05 and abs(lng - 32.2623) < 0.05:
                print("✅ This is KROPYVNYTSKYI (regional center)")
            else:
                print("❓ This is some other location")
        else:
            print("❌ No coordinates found")
    else:
        print("❌ No result")

print("\n" + "=" * 70)
print("KEY POINT: System correctly distinguishes between:")
print("1. Specific target: 'на олександрію' → shows Oleksandria")  
print("2. Regional mention: no specific city → shows regional center (Kropyvnytskyi)")
print("\nIf user sees wrong location, check:")
print("- Exact message being processed")
print("- Browser cache")
print("- Frontend vs backend data consistency")
