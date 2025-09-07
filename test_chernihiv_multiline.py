#!/usr/bin/env python3
"""
Test parsing multi-line regional UAV message
"""

import sys
import os
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_chernihiv_multiline():
    """Test the specific message pattern reported by user"""
    
    # User's message
    test_message = """Чернігівщина:
3 БпЛА в районі Ніжина
1 БпЛА на Березну"""
    
    print("="*60)
    print("TESTING CHERNIHIV MULTILINE MESSAGE")
    print("="*60)
    print(f"Message: {repr(test_message)}")
    print()
    
    # Parse the message
    markers = process_message(
        text=test_message,
        mid=999999,
        date_str="07.09.2025 12:00",
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
        print(f"  Text: {marker.get('text')}")
        print(f"  Count: {marker.get('count', 1)}")
        print(f"  Source match: {marker.get('source_match')}")
        print()
    
    # Expected: should find 2 markers (one for Ніжин with count 3, one for Березна with count 1)
    expected_places = ['Ніжин', 'Березна']
    expected_counts = [3, 1]
    
    if len(markers) != 2:
        print(f"❌ FAILED: Expected 2 markers, got {len(markers)}")
        return False
    
    found_places = [m.get('place') for m in markers]
    found_counts = [m.get('count', 1) for m in markers]
    
    print("Expected places:", expected_places)
    print("Found places:", found_places)
    print("Expected counts:", expected_counts)
    print("Found counts:", found_counts)
    
    success = True
    
    for place in expected_places:
        if place not in found_places:
            print(f"❌ FAILED: Missing place {place}")
            success = False
    
    if success:
        print("✅ SUCCESS: All expected places found")
    
    return success

if __name__ == "__main__":
    test_chernihiv_multiline()
