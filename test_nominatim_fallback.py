#!/usr/bin/env python3
"""
Test: Nominatim fallback for unknown cities
Testing if system uses Nominatim API when city is not in local database
"""

import sys
import os

# Add the parent directory to the path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and parsing functions
from app import process_message

def test_unknown_city():
    print("🔍 TESTING UNKNOWN CITY WITH NOMINATIM FALLBACK")
    print("="*50)
    
    # Test with a small Ukrainian village that's likely not in our local database
    message = "БпЛА курсом на Березівку"
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
        
        if lat and lng:
            print(f"    ✅ SUCCESS: Found coordinates via enhanced lookup (likely Nominatim)")
        else:
            print(f"    ❌ FAILED: No coordinates found")

def test_known_city_vs_nominatim():
    print("\n🔍 TESTING NOMINATIM VS LOCAL DATABASE ACCURACY")
    print("="*50)
    
    # Test with Zarichne - should use military priority, not Nominatim
    message = "БпЛА курсом на Зарічне"
    print(f"Message: '{message}'")
    
    threats = process_message(message, 124, "2024-01-01 12:00:00", "test_channel")
    
    print(f"\n📍 Processing results:")
    for i, threat in enumerate(threats):
        place = threat.get('place', 'N/A')
        lat, lng = threat.get('lat', 'N/A'), threat.get('lng', 'N/A')
        source = threat.get('source_match', 'N/A')
        print(f"  {i+1}. {place} at ({lat}, {lng}) - source: {source}")
        
        # Check if coordinates are correct (Dnipropetrovska)
        if lat and lng:
            if abs(float(lat) - 48.15) < 0.1 and abs(float(lng) - 35.2) < 0.3:
                print(f"    ✅ CORRECT: Using military prioritized Dnipropetrovska coordinates!")
            elif abs(float(lat) - 48.046119) < 0.1 and abs(float(lng) - 36.0988602) < 0.1:
                print(f"    ⚠️  NOMINATIM: Using Nominatim Dnipropetrovska coordinates (also correct)")
            else:
                print(f"    ❓ OTHER: Using different coordinates")

if __name__ == "__main__":
    test_unknown_city()
    test_known_city_vs_nominatim()
