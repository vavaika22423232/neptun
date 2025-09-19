#!/usr/bin/env python3
"""Test full Переяслав message processing"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_full_pereyaslav_message():
    """Test the exact message from user"""
    
    message = """БпЛА курсом на Переяслав | 1 шахед на переяслав | 🛸 Переяслав (Київська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""
    
    print("Testing full Переяслав message...")
    print(f"Message: {message}")
    
    try:
        result = process_message(message, "test_id", "2024-01-01", "test_channel")
        print(f"Found {len(result)} markers")
        
        pereyaslav_found = False
        for marker in result:
            if isinstance(marker, dict) and 'lat' in marker and 'lng' in marker:
                lat, lon = marker['lat'], marker['lng']
                print(f"Marker: ({lat}, {lon})")
                
                # Check if it's Переяслав coordinates (50.0769, 31.461)
                if abs(lat - 50.0769) < 0.01 and abs(lon - 31.461) < 0.01:
                    print("✅ Found Переяслав marker with correct coordinates!")
                    pereyaslav_found = True
                elif abs(lat - 50.4501) < 0.01 and abs(lon - 30.5234) < 0.01:
                    print("❌ Found Kyiv center coordinates - still wrong!")
                else:
                    print(f"❓ Found marker at ({lat}, {lon}) - unknown location")
        
        return pereyaslav_found
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Testing Full Переяслав Message ===\n")
    
    success = test_full_pereyaslav_message()
    
    print("\n=== Summary ===")
    if success:
        print("✅ Переяслав message processing is working correctly!")
    else:
        print("❌ Переяслав message processing still has issues")
