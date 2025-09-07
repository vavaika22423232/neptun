#!/usr/bin/env python3
"""
Test parsing Kaharlik UAV message
"""

import sys
import os
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_kaharlik_uav():
    """Test the specific Kaharlik UAV message"""
    
    test_message = """БпЛА курсом на Кагарлик | 2х БпЛА Білоцерківський район. | 3х БпЛА Вишеньки / Українка."""
    
    print("="*60)
    print("TESTING KAHARLIK UAV MESSAGE")
    print("="*60)
    print(f"Message: {repr(test_message)}")
    print()
    
    # Parse the message
    markers = process_message(
        text=test_message,
        mid=777777,
        date_str="2025-09-08 12:00:00",
        channel="test_channel"
    )
    
    print(f"Number of markers found: {len(markers)}")
    print()
    
    for i, marker in enumerate(markers, 1):
        print(f"Marker {i}:")
        print(f"  ID: {marker.get('id', 'N/A')}")
        print(f"  Place: {marker.get('place', 'N/A')}")
        print(f"  Coordinates: ({marker.get('lat', 'N/A')}, {marker.get('lng', 'N/A')})")
        print(f"  Threat type: {marker.get('threat_type', 'N/A')}")
        print(f"  Text: {marker.get('text', 'N/A')[:100]}...")
        print(f"  Count: {marker.get('count', 'N/A')}")
        print(f"  Source match: {marker.get('source_match', 'N/A')}")
        print(f"  List only: {marker.get('list_only', False)}")
        print()
    
    # Check expected places
    expected_places = ['Кагарлик', 'Білоцерківський', 'Вишеньки', 'Українка']
    found_places = [marker.get('place', '') for marker in markers if marker.get('place')]
    
    print(f"Expected places: {expected_places}")
    print(f"Found places: {found_places}")
    
    for place in expected_places:
        if any(place in found_place for found_place in found_places):
            print(f"✅ FOUND: {place}")
        else:
            print(f"❌ MISSING: {place}")
    
    print()
    if all(any(place in found_place for found_place in found_places) for place in expected_places):
        print("✅ SUCCESS: All expected places found")
    else:
        print("❌ FAILED: Some places missing")

if __name__ == "__main__":
    test_kaharlik_uav()
