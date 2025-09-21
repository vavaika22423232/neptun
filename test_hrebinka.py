#!/usr/bin/env python3
"""
Test: Гребінка геокодинг проблема
Testing why "🛸 Гребінка (Полтавська обл.)" creates marker in Poltava instead of Hrebinka
"""

import sys
import os

# Add the parent directory to the path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and parsing functions
from app import process_message

def test_hrebinka_geocoding():
    print("🔍 TESTING HREBINKA GEOCODING")
    print("="*40)
    
    message = "🛸 Гребінка (Полтавська обл.)\nЗагроза застосування БПЛА. Перейдіть в укриття!"
    print(f"Message: '{message}'")
    
    # Call the main parsing function
    threats = process_message(message, 123, "2024-01-01 12:00:00", "test_channel")
    
    print(f"\n📍 Processing results:")
    print(f"Number of markers: {len(threats)}")
    for i, threat in enumerate(threats):
        place = threat.get('place', 'N/A')
        lat, lng = threat.get('lat', 'N/A'), threat.get('lng', 'N/A')
        source = threat.get('source_match', 'N/A')
        print(f"  {i+1}. {place} at ({lat}, {lng}) - source: {source}")
        
        # Check if coordinates are correct for Hrebinka
        if lat and lng:
            # Hrebinka coordinates should be around (50.1058, 32.4464)
            if abs(float(lat) - 50.1058) < 0.1 and abs(float(lng) - 32.4464) < 0.1:
                print(f"    ✅ CORRECT: Hrebinka coordinates!")
            # Poltava coordinates are around (49.5937, 34.5407)
            elif abs(float(lat) - 49.5937) < 0.1 and abs(float(lng) - 34.5407) < 0.1:
                print(f"    ❌ WRONG: Using Poltava coordinates instead of Hrebinka")
            else:
                print(f"    ❓ UNKNOWN: Coordinates don't match Hrebinka or Poltava")

if __name__ == "__main__":
    test_hrebinka_geocoding()
