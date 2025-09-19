#!/usr/bin/env python3
"""Test Власівка geographic resolution"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import ensure_city_coords_with_message_context, NAME_REGION_MAP, CITY_COORDS

def test_vlasivka_resolution():
    """Test that Власівка resolves correctly"""
    
    message = "БпЛА курсом на Власівку"
    
    print("Testing Власівка resolution...")
    print(f"Message: {message}")
    
    # Check if Власівка is in NAME_REGION_MAP
    city_lower = "власівка"
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
        
        # Check if it's showing Kyiv coordinates (50.4501, 30.5234)
        if abs(lat - 50.4501) < 0.01 and abs(lon - 30.5234) < 0.01:
            print("❌ Coordinates are in Kyiv center - probably using oblast fallback!")
            return False
        else:
            print(f"✅ Coordinates are NOT in Kyiv center: ({lat}, {lon})")
            return True
    else:
        print("❌ No coordinates found")
        return False

def search_vlasivka_variants():
    """Search for Власівка variants in the coordinate databases"""
    
    print("\n=== Searching for Власівка variants ===")
    
    variants = [
        'власівка', 'власовка', 'власівку', 'власовку', 
        'власівці', 'власовці', 'власівкою', 'власовкою'
    ]
    
    found_any = False
    for variant in variants:
        if variant in CITY_COORDS:
            coords = CITY_COORDS[variant]
            print(f"✅ Found '{variant}': {coords}")
            found_any = True
        elif variant in NAME_REGION_MAP:
            region = NAME_REGION_MAP[variant]
            print(f"📍 Found '{variant}' in NAME_REGION_MAP → {region}")
            found_any = True
    
    if not found_any:
        print("❌ No variants of Власівка found in coordinate databases")
    
    return found_any

if __name__ == "__main__":
    print("=== Testing Власівка Geographic Resolution ===\n")
    
    success = test_vlasivka_resolution()
    search_vlasivka_variants()
    
    print("\n=== Summary ===")
    if success:
        print("✅ Власівка resolution is working correctly!")
    else:
        print("❌ Власівка resolution needs fixing - likely missing coordinates")
