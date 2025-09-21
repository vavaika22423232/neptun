#!/usr/bin/env python3
"""
Final test: Context-aware geocoding comprehensive validation
Testing various problematic scenarios with context understanding
"""

import sys
import os

# Add the parent directory to the path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and parsing functions
from app import process_message

def test_context_scenarios():
    print("🎯 COMPREHENSIVE CONTEXT-AWARE GEOCODING TEST")
    print("="*60)
    
    test_cases = [
        {
            'message': 'чернігівщина - нові шахеди над семенівкою',
            'expected_city': 'семенівка',
            'expected_coords': (50.6633, 32.3933),
            'description': 'Regional context + target city'
        },
        {
            'message': 'харківщина - БпЛА курсом на балаклію',
            'expected_city': 'балаклія',
            'expected_coords': None,  # Will check if found
            'description': 'Regional context + course to city'
        },
        {
            'message': 'донецька область - ракети на покровськ',
            'expected_city': 'покровськ',
            'expected_coords': None,
            'description': 'Oblast context + missile target'
        },
        {
            'message': 'полтавщина - шахеди у кременчуці',
            'expected_city': 'кременчук',
            'expected_coords': None,
            'description': 'Regional context + city with preposition "у"'
        },
        {
            'message': 'БпЛА курсом на зарічне',
            'expected_city': 'зарічне',
            'expected_coords': (48.15, 35.2),  # Should use military priority
            'description': 'Military context priority test'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['description']}")
        print(f"Message: '{test_case['message']}'")
        
        threats = process_message(test_case['message'], 100 + i, "2024-01-01 12:00:00", "test_channel")
        
        if threats and len(threats) > 0:
            threat = threats[0]  # Take first threat
            place = threat.get('place', 'N/A').lower()
            lat, lng = threat.get('lat', 'N/A'), threat.get('lng', 'N/A')
            source = threat.get('source_match', 'N/A')
            
            print(f"Result: {threat.get('place', 'N/A')} at ({lat}, {lng}) - source: {source}")
            
            # Check if result matches expected
            expected_city = test_case['expected_city'].lower()
            expected_coords = test_case['expected_coords']
            
            city_match = expected_city in place
            coords_match = True
            
            if expected_coords and lat and lng:
                coords_match = (abs(float(lat) - expected_coords[0]) < 0.1 and 
                              abs(float(lng) - expected_coords[1]) < 0.1)
            
            if city_match and coords_match:
                print(f"✅ SUCCESS: Correctly identified {expected_city}")
                if source == 'context_aware_geocoding':
                    print("🧠 Used context-aware intelligence!")
            elif city_match:
                print(f"✅ PARTIAL: Found correct city but coordinates may differ")
            else:
                print(f"❌ FAILED: Expected {expected_city}, got {place}")
        else:
            print(f"❌ FAILED: No threats found")
        
        print("-" * 50)

if __name__ == "__main__":
    test_context_scenarios()
