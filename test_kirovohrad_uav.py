#!/usr/bin/env python3
"""
Test parsing Kirovohrad UAV message
"""

import sys
import os
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_kirovohrad_uav():
    """Test the specific Kirovohrad UAV message"""
    
    test_message = """Кіровоградщина: Група 15х БпЛА через Компаніївка, Новоукраїнка. Курс Північно-Західний у напрямку Черкащини. Група 4х БпЛА повз Олександрію."""
    
    print("="*60)
    print("TESTING KIROVOHRAD UAV MESSAGE")
    print("="*60)
    print(f"Message: {repr(test_message)}")
    print()
    
    # Parse the message
    markers = process_message(
        text=test_message,
        mid=888888,
        date_str="07.09.2025 12:30",
        channel="test"
    )
    
    print(f"Number of markers found: {len(markers)}")
    print()
    
    for i, marker in enumerate(markers, 1):
        print(f"Marker {i}:")
        print(f"  ID: {marker.get('id')}")
        print(f"  Place: {marker.get('place')}")
        print(f"  Coordinates: ({marker.get('lat')}, {marker.get('lng')})")
        print(f"  Threat type: {marker.get('threat_type')}")
        print(f"  Text: {marker.get('text', '')[:100]}...")
        print(f"  Count: {marker.get('count', 1)}")
        print(f"  Source match: {marker.get('source_match')}")
        print(f"  List only: {marker.get('list_only', False)}")
        print()
    
    # Expected cities: Компаніївка, Новоукраїнка, Олександрія
    expected_places = ['Компаніївка', 'Новоукраїнка', 'Олександрія']
    
    if len(markers) == 0:
        print("❌ FAILED: No markers found - this explains why it shows in event list only")
        return False
    
    found_places = [m.get('place') for m in markers if not m.get('list_only')]
    
    print("Expected places:", expected_places)
    print("Found places:", found_places)
    
    success = True
    
    for place in expected_places:
        if place not in found_places:
            print(f"❌ MISSING: {place}")
            success = False
        else:
            print(f"✅ FOUND: {place}")
    
    if success:
        print("✅ SUCCESS: All expected places found")
    else:
        print("❌ FAILED: Some places missing")
    
    return success

if __name__ == "__main__":
    test_kirovohrad_uav()
