#!/usr/bin/env python3
"""
Test parsing Pavlohrad district UAV message
"""

import sys
import os
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_pavlohrad_uav():
    """Test the specific Pavlohrad district UAV message"""
    
    test_message = """8х БпЛА Павлоградський район."""
    
    print("="*60)
    print("TESTING PAVLOHRAD DISTRICT UAV MESSAGE")
    print("="*60)
    print(f"Message: {repr(test_message)}")
    print()
    
    # Parse the message
    markers = process_message(
        text=test_message,
        mid=666666,
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
    
    # Check coordinates
    if markers:
        marker = markers[0]
        lat = marker.get('lat')
        lng = marker.get('lng')
        print(f"Current coordinates: {lat}, {lng}")
        print()
        print("Reference coordinates:")
        print("- Павлоград: приблизно 48.515, 35.866")
        print("- Дніпро: приблизно 48.4647, 35.0462")
        print()
        
        if lat and lng:
            if abs(lat - 48.4647) < 0.1 and abs(lng - 35.0462) < 0.1:
                print("❌ PROBLEM: Marker is indeed positioned near Dnipro!")
            elif abs(lat - 48.515) < 0.1 and abs(lng - 35.866) < 0.1:
                print("✅ CORRECT: Marker is positioned near Pavlohrad")
            else:
                print(f"? UNKNOWN: Marker position {lat}, {lng} doesn't match expected locations")

if __name__ == "__main__":
    test_pavlohrad_uav()
