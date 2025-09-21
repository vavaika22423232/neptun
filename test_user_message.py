#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test exact user message
"""

from app import process_message

def test_user_message():
    """Test the exact user message."""
    
    message = """🛸 Світловодськ (Кіровоградська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""
    
    print("🔍 USER MESSAGE TEST")
    print("=" * 50)
    print(f"Message: '{message}'")
    
    # Test message processing
    markers = process_message(message, "user_123", "2025-09-21 23:25", "test_channel")
    
    print(f"\n📍 Results:")
    print(f"Number of markers: {len(markers) if markers else 0}")
    
    if markers:
        for i, marker in enumerate(markers, 1):
            place = marker.get('place', 'N/A')
            lat = marker.get('lat', 'N/A')
            lng = marker.get('lng', marker.get('lon', 'N/A'))
            source = marker.get('source_match', 'N/A')
            threat = marker.get('threat_type', 'N/A')
            
            print(f"  Marker {i}: {place}")
            print(f"    Coordinates: ({lat}, {lng})")
            print(f"    Threat Type: {threat}")
            print(f"    Source: {source}")
            
            # Verify coordinates are for Svitlovodsk, not Kropyvnytskyi
            if lat == 49.0556 and lng == 33.2433:
                print(f"    ✅ CORRECT: Світловодськ coordinates")
            elif lat == 48.5079 and lng == 32.2623:
                print(f"    ❌ WRONG: Кропивницький coordinates (fallback)")
            else:
                print(f"    ⚠️  UNKNOWN coordinates")
    else:
        print("  No markers created")

if __name__ == "__main__":
    test_user_message()
