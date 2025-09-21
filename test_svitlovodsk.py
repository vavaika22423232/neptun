#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for Svitlovodsk message processing bug
"""

from app import process_message, CITY_COORDS, ensure_city_coords_with_message_context, ensure_city_coords

def test_svitlovodsk_message():
    """Test the specific Svitlovodsk message that's showing wrong location."""
    
    message = """🛸 Світловодськ (Кіровоградська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""
    
    print("🔍 SVITLOVODSK MESSAGE TEST")
    print("=" * 50)
    print(f"Message: '{message}'")
    
    # Test individual geocoding functions
    print(f"\n📍 Testing geocoding functions:")
    
    # Test ensure_city_coords
    coords1 = ensure_city_coords("світловодськ")
    print(f"ensure_city_coords('світловодськ'): {coords1}")
    
    # Test with message context
    coords2 = ensure_city_coords_with_message_context("світловодськ", message)
    print(f"ensure_city_coords_with_message_context('світловодськ', message): {coords2}")
    
    # Check CITY_COORDS directly
    variants = [
        'світловодськ',
        'світловодськ кіровоградська',
        'світловодськ кіровоградська область',
        'світловодськ (кіровоградська)',
        'світловодськ кіровоградська обл.',
    ]
    
    print(f"\n🔍 Checking CITY_COORDS variants:")
    for variant in variants:
        coords = CITY_COORDS.get(variant)
        print(f"  '{variant}': {coords}")
    
    # Test full message processing
    print(f"\n📍 Process Message Results:")
    try:
        markers = process_message(message, "test_123", "2025-09-21 17:00", "test_channel")
        print(f"Number of markers created: {len(markers) if markers else 0}")
        if markers:
            for i, marker in enumerate(markers, 1):
                print(f"  Marker {i}:")
                print(f"    Place: {marker.get('place', 'N/A')}")
                print(f"    Coords: ({marker.get('lat', 'N/A')}, {marker.get('lng', marker.get('lon', 'N/A'))})")
                print(f"    Source: {marker.get('source_match', 'N/A')}")
        else:
            print("  No markers created")
    except Exception as e:
        print(f"  Error processing message: {e}")

if __name__ == "__main__":
    test_svitlovodsk_message()
