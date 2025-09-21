#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Oleksandria vs Kropyvnytskyi issue
"""

from app import process_message
import json

print("🎯 OLEKSANDRIA VS KROPYVNYTSKYI TEST")
print("=" * 60)

# Test the exact user message
original_message = "на кіровоградщині 1 шахед на олександрію"
print(f"Original message: {original_message}")
print("-" * 50)

result = process_message(original_message, 'test_id', '2024-01-01', 'test_channel')

if result and len(result) > 0:
    for i, r in enumerate(result):
        if 'lat' in r and 'lon' in r:
            lat, lon = r['lat'], r['lon']
            place = r.get('place', 'Unknown')
            source = r.get('source_match', 'unknown')
            
            print(f"Marker {i+1}:")
            print(f"  Place: {place}")
            print(f"  Coordinates: ({lat:.6f}, {lon:.6f})")
            print(f"  Source: {source}")
            
            # Analysis
            oleksandria_coords = (48.8033, 33.1147)
            kropyvnytskyi_coords = (48.5079, 32.2623)
            
            distance_to_oleksandria = ((lat - oleksandria_coords[0])**2 + (lon - oleksandria_coords[1])**2)**0.5
            distance_to_kropyvnytskyi = ((lat - kropyvnytskyi_coords[0])**2 + (lon - kropyvnytskyi_coords[1])**2)**0.5
            
            if distance_to_oleksandria < 0.1:
                print("  ✅ This is OLEKSANDRIA (CORRECT)")
            elif distance_to_kropyvnytskyi < 0.1:
                print("  ❌ This is KROPYVNYTSKYI (WRONG)")
            else:
                print(f"  ❓ Unknown location")
                print(f"     Distance to Oleksandria: {distance_to_oleksandria:.4f}")
                print(f"     Distance to Kropyvnytskyi: {distance_to_kropyvnytskyi:.4f}")
            print()
else:
    print("❌ No markers found!")

print("=" * 60)
print("Expected: Marker should be in Oleksandria, not Kropyvnytskyi")
print("Oleksandria coordinates: (48.8033, 33.1147)")
print("Kropyvnytskyi coordinates: (48.5079, 32.2623)")
