#!/usr/bin/env python3
"""Test full Устинівка message processing"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_full_ustynivka_message():
    """Test the exact message from user"""
    
    message = "БпЛА курсом на Устинівку"
    
    print("Testing full Устинівка message...")
    print(f"Message: {message}")
    
    try:
        result = process_message(message, "test_id", "2024-01-01", "test_channel")
        print(f"Found {len(result)} markers")
        
        ustynivka_found = False
        for marker in result:
            if isinstance(marker, dict) and 'lat' in marker and 'lng' in marker:
                lat, lon = marker['lat'], marker['lng']
                print(f"Marker: ({lat}, {lon})")
                
                # Check if it's Устинівка coordinates (50.7481, 29.0028)
                if abs(lat - 50.7481) < 0.01 and abs(lon - 29.0028) < 0.01:
                    print("✅ Found Устинівка marker with correct coordinates!")
                    ustynivka_found = True
                elif abs(lat - 50.2547) < 0.01 and abs(lon - 28.6587) < 0.01:
                    print("❌ Found Zhytomyr center coordinates - still wrong!")
                else:
                    print(f"❓ Found marker at ({lat}, {lon}) - unknown location")
        
        return ustynivka_found
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Testing Full Устинівка Message ===\n")
    
    success = test_full_ustynivka_message()
    
    print("\n=== Summary ===")
    if success:
        print("✅ Устинівка message processing is working correctly!")
    else:
        print("❌ Устинівка message processing still has issues")
