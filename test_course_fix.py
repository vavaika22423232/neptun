#!/usr/bin/env python3
"""
Test: Course fix to use SpaCy for course_to_city processing
Testing if the course_to_city function uses the new SpaCy intelligence
"""

import sys
import os

# Add the parent directory to the path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and parsing functions
from app import process_message

def test_zarichne_course_spacy():
    print("=== Testing Зарічне Course Fix ===")
    
    message = "БпЛА курсом на Зарічне"
    print(f"Input: {message}")
    
    # Call the main parsing function
    threats = process_message(message, 123, "2024-01-01 12:00:00", "test_channel")
    
    print(f"\nResults: {len(threats)} threats found")
    for i, threat in enumerate(threats):
        print(f"  Threat {i+1}:")
        print(f"    Place: {threat.get('place', 'N/A')}")
        print(f"    Coordinates: ({threat.get('lat', 'N/A')}, {threat.get('lng', 'N/A')})")
        print(f"    Source: {threat.get('source_match', 'N/A')}")
        print(f"    Text: {threat.get('text', 'N/A')[:100]}...")
        
        # Check if coordinates are correct (Dnipropetrovska)
        lat, lng = threat.get('lat'), threat.get('lng')
        if lat and lng:
            if abs(lat - 48.15) < 0.1 and abs(lng - 35.2) < 0.3:
                print(f"    ✅ CORRECT: Dnipropetrovska coordinates!")
            elif abs(lat - 51.2167) < 0.1 and abs(lng - 26.0833) < 0.1:
                print(f"    ❌ WRONG: Still using Rivne coordinates")
            else:
                print(f"    ❓ UNKNOWN: Coordinates don't match either location")

if __name__ == "__main__":
    test_zarichne_course_spacy()
