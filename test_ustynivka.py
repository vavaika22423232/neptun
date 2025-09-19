#!/usr/bin/env python3
"""Test Устинівка geographic resolution"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import ensure_city_coords_with_message_context, NAME_REGION_MAP, CITY_COORDS

def test_ustynivka_resolution():
    """Test that Устинівка resolves correctly"""
    
    message = "БпЛА курсом на Устинівку"
    
    print("Testing Устинівка resolution...")
    print(f"Message: {message}")
    
    # Check if Устинівка is in NAME_REGION_MAP
    city_lower = "устинівка"
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
        
        # Check if it's showing Zhytomyr coordinates (50.2649, 28.6767)
        if abs(lat - 50.2649) < 0.01 and abs(lon - 28.6767) < 0.01:
            print("❌ Coordinates are in Zhytomyr center - probably using oblast fallback!")
            return False
        else:
            print(f"✅ Coordinates are NOT in Zhytomyr center: ({lat}, {lon})")
            return True
    else:
        print("❌ No coordinates found")
        return False

def search_ustynivka_variants():
    """Search for Устинівка variants in the coordinate databases"""
    
    print("\n=== Searching for Устинівка variants ===")
    
    variants = [
        'устинівка', 'устиновка', 'устинівку', 'устиновку', 
        'устинівці', 'устиновці', 'устинівкою', 'устиновкою'
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
        print("❌ No variants of Устинівка found in coordinate databases")
    
    return found_any

if __name__ == "__main__":
    print("=== Testing Устинівка Geographic Resolution ===\n")
    
    success = test_ustynivka_resolution()
    search_ustynivka_variants()
    
    print("\n=== Summary ===")
    if success:
        print("✅ Устинівка resolution is working correctly!")
    else:
        print("❌ Устинівка resolution needs fixing - likely missing coordinates")
