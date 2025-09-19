#!/usr/bin/env python3
"""Test Переяслав geographic resolution"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import ensure_city_coords_with_message_context, NAME_REGION_MAP, CITY_COORDS

def test_pereyaslav_resolution():
    """Test that Переяслав resolves correctly"""
    
    message = "БпЛА курсом на Переяслав | 1 шахед на переяслав | 🛸 Переяслав (Київська обл.)"
    
    print("Testing Переяслав resolution...")
    print(f"Message: {message}")
    
    # Check if Переяслав is in NAME_REGION_MAP
    city_lower = "переяслав"
    if city_lower in NAME_REGION_MAP:
        region = NAME_REGION_MAP[city_lower]
        print(f"NAME_REGION_MAP['{city_lower}'] = '{region}'")
    else:
        print(f"'{city_lower}' not found in NAME_REGION_MAP")
    
    # Check CITY_COORDS
    if city_lower in CITY_COORDS:
        coords = CITY_COORDS[city_lower]
        print(f"CITY_COORDS['{city_lower}'] = {coords}")
    else:
        print(f"'{city_lower}' not found in CITY_COORDS")
    
    # Test coordinate resolution
    coords = ensure_city_coords_with_message_context(city_lower, message)
    print(f"Resolved coordinates: {coords}")
    
    if coords:
        lat, lon = coords[0], coords[1]
        print(f"Coordinates: ({lat}, {lon})")
        
        # Переяслав should be around (50.077, 31.461) - southeast of Kyiv
        # Kyiv is around (50.4501, 30.5234)
        # If it's showing Kyiv coordinates, that's wrong
        
        if abs(lat - 50.4501) < 0.1 and abs(lon - 30.5234) < 0.1:
            print("❌ Coordinates are in Kyiv center - WRONG!")
            return False
        elif abs(lat - 50.077) < 0.1 and abs(lon - 31.461) < 0.1:
            print("✅ Coordinates are in Переяслав - CORRECT!")
            return True
        else:
            print(f"❓ Coordinates are somewhere else: ({lat}, {lon})")
            # Check if it's at least in the right general area
            if 49.8 < lat < 50.3 and 31.0 < lon < 32.0:
                print("✅ Coordinates are in Переяслав area")
                return True
            else:
                print("❌ Coordinates are not in Переяслав area")
                return False
    else:
        print("❌ No coordinates found")
        return False

if __name__ == "__main__":
    print("=== Testing Переяслав Geographic Resolution ===\n")
    
    success = test_pereyaslav_resolution()
    
    print("\n=== Summary ===")
    if success:
        print("✅ Переяслав resolution is working correctly!")
    else:
        print("❌ Переяслав resolution needs fixing")
