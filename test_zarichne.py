#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Zarichne geocoding issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message, spacy_enhanced_geocoding

def test_zarichne():
    """Test Zarichne geocoding."""
    message = "БпЛА курсом на Зарічне"
    
    print("🔍 TESTING ZARICHNE GEOCODING")
    print("=" * 40)
    print(f"Message: '{message}'")
    
    # Test SpaCy first
    print(f"\n🧠 SpaCy results:")
    spacy_result = spacy_enhanced_geocoding(message)
    if spacy_result:
        for i, city in enumerate(spacy_result, 1):
            coords = city.get('coords', 'No coords')
            source = city.get('source', 'Unknown')
            print(f"  {i}. {city['name']} -> {coords} (source: {source})")
    else:
        print("  No SpaCy results")
    
    # Test full processing
    print(f"\n📍 Full processing results:")
    result = process_message(message, 'test_zarichne', '2024-12-21', 'test_channel')
    markers = result if result else []
    
    print(f"Number of markers: {len(markers)}")
    for i, marker in enumerate(markers, 1):
        place = marker.get('place', 'N/A')
        lat = marker.get('lat', 'N/A')
        lng = marker.get('lng', 'N/A')
        source = marker.get('source_match', 'N/A')
        print(f"  {i}. {place} at ({lat}, {lng}) - source: {source}")

if __name__ == "__main__":
    test_zarichne()
