#!/usr/bin/env python3
"""Test fix for Кривий Ріг geographic resolution"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import ensure_city_coords_with_message_context, NAME_REGION_MAP

def test_kryvyi_rih_resolution():
    """Test that Кривий Ріг resolves to Dnipropetrovsk oblast, not Zakarpattia"""
    
    # Test message
    message = "БпЛА курсом на Кривий Ріг"
    
    print("Testing Кривий Ріг resolution...")
    print(f"Message: {message}")
    
    # Check NAME_REGION_MAP doesn't contain problematic entry
    if 'кривий' in NAME_REGION_MAP:
        print(f"❌ Error: 'кривий' still in NAME_REGION_MAP: {NAME_REGION_MAP['кривий']}")
    else:
        print("✅ 'кривий' removed from NAME_REGION_MAP")
    
    # Get coordinates
    coords = ensure_city_coords_with_message_context("кривий ріг", message)
    
    print(f"Resolved coordinates: {coords}")
    
    if coords:
        lat, lon = coords[0], coords[1]  # Handle tuple with 3 values
        # Кривий Ріг should be around (47.9105, 33.3918) in Dnipropetrovsk
        # NOT around (48.6208, 22.2879) which is Ужгород in Zakarpattia
        
        if 47.5 < lat < 48.5 and 33.0 < lon < 34.0:
            print("✅ Coordinates are in Dnipropetrovsk oblast region")
            return True
        elif 48.5 < lat < 49.0 and 22.0 < lon < 23.0:
            print("❌ Coordinates are in Zakarpattia oblast (Ужгород) - WRONG!")
            return False
        else:
            print(f"❓ Coordinates ({lat}, {lon}) are in unknown region")
            return False
    else:
        print("❌ No coordinates found")
        return False

def test_full_message():
    """Test full message processing"""
    message = "БпЛА курсом на Кривий Ріг"
    
    print(f"\nTesting full message: {message}")
    
    # Import main process function
    from app import process_message
    
    try:
        result = process_message(message, "test_id", "2024-01-01", "test_channel")
        print(f"Result type: {type(result)}")
        
        if result and len(result) > 0:
            print(f"Found {len(result)} markers")
            
            # Look for markers in Dnipropetrovsk region 
            found_correct = False
            for marker in result:
                if isinstance(marker, dict) and 'lat' in marker and 'lng' in marker:
                    lat, lon = marker['lat'], marker['lng']
                    print(f"Marker coordinates: ({lat}, {lon})")
                    
                    if 47.5 < lat < 48.5 and 33.0 < lon < 34.0:
                        print("✅ Found marker in correct Dnipropetrovsk region")
                        found_correct = True
                        break
            
            return found_correct
        else:
            print("❌ Message processing returned no results")
            return False
            
    except Exception as e:
        print(f"❌ Error in message processing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Testing Кривий Ріг Geographic Fix ===\n")
    
    success1 = test_kryvyi_rih_resolution()
    success2 = test_full_message()
    
    print("\n=== Summary ===")
    if success1 and success2:
        print("✅ All tests passed - Кривий Ріг fix is working!")
    else:
        print("❌ Some tests failed - need more fixes")
