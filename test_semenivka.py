#!/usr/bin/env python3
"""
Test: Семенівка геокодинг проблема
Testing why "чернігівщина - нові шахеди над семенівкою" creates marker over Chernihiv instead of Semenivka
"""

import sys
import os

# Add the parent directory to the path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and parsing functions
from app import process_message

def test_semenivka_geocoding():
    print("🔍 TESTING SEMENIVKA GEOCODING")
    print("="*40)
    
    message = "чернігівщина - нові шахеди над семенівкою"
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
        
        # Check if coordinates are correct
        if lat and lng:
            # Semenivka (Chernihiv region) coordinates should be around (50.6633, 32.3933)
            if abs(float(lat) - 50.6633) < 0.1 and abs(float(lng) - 32.3933) < 0.1:
                print(f"    ✅ CORRECT: Semenivka coordinates!")
            # Chernihiv city coordinates are around (51.4982, 31.2893)
            elif abs(float(lat) - 51.4982) < 0.1 and abs(float(lng) - 31.2893) < 0.1:
                print(f"    ❌ WRONG: Using Chernihiv city coordinates instead of Semenivka")
            else:
                print(f"    ❓ UNKNOWN: Coordinates don't match Semenivka or Chernihiv")

def test_context_understanding():
    print("\n🔍 TESTING CONTEXT UNDERSTANDING")
    print("="*40)
    
    test_messages = [
        "чернігівщина - нові шахеди над семенівкою",
        "шахеди над семенівкою чернігівської області", 
        "БпЛА курсом на семенівку",
        "семенівка чернігівщина"
    ]
    
    for msg in test_messages:
        print(f"\nTesting: '{msg}'")
        threats = process_message(msg, 124, "2024-01-01 12:00:00", "test_channel")
        
        for threat in threats:
            place = threat.get('place', 'N/A')
            lat, lng = threat.get('lat', 'N/A'), threat.get('lng', 'N/A')
            source = threat.get('source_match', 'N/A')
            print(f"  → {place} ({lat}, {lng}) - {source}")

if __name__ == "__main__":
    test_semenivka_geocoding()
    test_context_understanding()
