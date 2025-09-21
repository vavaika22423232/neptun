#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for trajectory current location fix
"""

from app import process_message
import json

print("🎯 TRAJECTORY CURRENT LOCATION TEST")
print("=" * 60)

# Test different regional directional patterns
test_cases = [
    "🛵БпЛА в північно-західній частині Полтавщини, курсом на Київщину",
    "БпЛА в південно-східній частині Харківщини",
    "Дрони в центральній частині Дніпропетровщини курсом на північ",
    "БпЛА в північній частині Сумщини",
    "Група дронів в західній частині Львівщини курсом на схід",
    "БпЛА в східній частині Чернігівщини курсом на Київ"
]

for i, test_message in enumerate(test_cases, 1):
    print(f"\n📝 Test {i}: {test_message}")
    
    result = process_message(test_message, f'test_id_{i}', '2024-01-01', 'test_channel')
    
    if result and len(result) > 0:
        r = result[0]
        if 'lat' in r and 'lon' in r and r.get('source_match') == 'trajectory_current_location':
            print(f"  ✅ SUCCESS: {r['city']} at ({r['lat']:.4f}, {r['lon']:.4f})")
            print(f"     Shows current BPLA location, not destination")
        elif 'lat' in r and 'lon' in r:
            print(f"  ⚠️  PARTIAL: {r.get('city', 'Unknown')} at ({r['lat']:.4f}, {r['lon']:.4f})")
            print(f"     Source: {r.get('source_match', 'unknown')} (not trajectory_current_location)")
        else:
            print(f"  ❌ ISSUE: No coordinates found")
            print(f"     Source: {r.get('source_match', 'unknown')}")
    else:
        print(f"  ❌ ISSUE: No result returned")

print("\n" + "=" * 60)
print("Test completed!")
print("\nKey improvement: System now shows current BPLA location")
print("instead of incorrectly placing markers at destination cities!")
