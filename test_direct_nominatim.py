#!/usr/bin/env python3
"""
Test: Really unknown city to trigger Nominatim
Testing with a rare Ukrainian settlement
"""

import sys
import os

# Add the parent directory to the path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and parsing functions
from app import get_coordinates_enhanced

def test_direct_nominatim():
    print("🔍 TESTING DIRECT NOMINATIM LOOKUP")
    print("="*40)
    
    # Test with a rare settlement that's unlikely to be in local database
    test_cities = [
        ("Верхньоднагачівка", None),  # Rare village in Dnipropetrovska oblast
        ("Новопетрівка", "Херсонська область"),  # Common name, need region
        ("Світловодськ", None),  # This should be in database
        ("УстиновкаТест", None),  # This definitely doesn't exist
    ]
    
    for city, region in test_cities:
        print(f"\nTesting: {city}" + (f" ({region})" if region else ""))
        coords = get_coordinates_enhanced(city, region=region)
        if coords:
            print(f"  ✅ Found: {coords}")
        else:
            print(f"  ❌ Not found")

if __name__ == "__main__":
    test_direct_nominatim()
