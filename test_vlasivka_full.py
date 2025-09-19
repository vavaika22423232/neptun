#!/usr/bin/env python3
"""Test full Власівка message processing"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_full_vlasivka_message():
    """Test the exact message from user"""
    
    message = "БпЛА курсом на Власівку"
    
    print("Testing full Власівка message...")
    print(f"Message: {message}")
    
    try:
        result = process_message(message, "test_id", "2024-01-01", "test_channel")
        print(f"Found {len(result)} markers")
        
        vlasivka_found = False
        for marker in result:
            if isinstance(marker, dict) and 'lat' in marker and 'lng' in marker:
                lat, lon = marker['lat'], marker['lng']
                print(f"Marker: ({lat}, {lon})")
                
                # Check if it's Власівка coordinates (50.3706, 31.2381)
                if abs(lat - 50.3706) < 0.01 and abs(lon - 31.2381) < 0.01:
                    print("✅ Found Власівка marker with correct coordinates!")
                    vlasivka_found = True
                elif abs(lat - 50.4501) < 0.01 and abs(lon - 30.5234) < 0.01:
                    print("❌ Found Kyiv center coordinates - still wrong!")
                else:
                    print(f"❓ Found marker at ({lat}, {lon}) - unknown location")
        
        return vlasivka_found
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Testing Full Власівка Message ===\n")
    
    success = test_full_vlasivka_message()
    
    print("\n=== Summary ===")
    if success:
        print("✅ Власівка message processing is working correctly!")
    else:
        print("❌ Власівка message processing still has issues")
