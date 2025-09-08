#!/usr/bin/env python3
"""
Debug route parsing patterns
"""

import re

def test_route_patterns():
    """Test route parsing patterns"""
    
    test_message = """Кіровоградщина: Група 15х БпЛА через Компаніївка, Новоукраїнка. Курс Північно-Західний у напрямку Черкащини. Група 4х БпЛА повз Олександрію."""
    
    print("="*60)
    print("TESTING ROUTE PATTERNS")
    print("="*60)
    print(f"Message: {repr(test_message)}")
    print()
    
    lorig = test_message.lower()
    print("Basic checks:")
    print(f"  'бпла' in text: {'бпла' in lorig}")
    print(f"  'через' in text: {'через' in lorig}")
    print(f"  'повз' in text: {'повз' in lorig}")
    print()
    
    # Test route pattern
    route_pattern = r'через\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*[\.\,\!\?]|\s+курс|\s+у\s+напрям|\s+напрям|$)'
    print(f"Route pattern: {route_pattern}")
    
    route_matches = re.findall(route_pattern, test_message, re.IGNORECASE)
    print(f"Route matches: {route_matches}")
    
    for i, route_match in enumerate(route_matches):
        print(f"  Route match {i}: '{route_match}'")
        
        # Split by comma to get individual cities
        cities_raw = [c.strip() for c in route_match.split(',') if c.strip()]
        print(f"    Cities: {cities_raw}")
    
    print()
    
    # Test past pattern
    past_pattern = r'повз\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*[\.\,\!\?]|$)'
    print(f"Past pattern: {past_pattern}")
    
    past_matches = re.findall(past_pattern, test_message, re.IGNORECASE)
    print(f"Past matches: {past_matches}")
    
    for i, past_match in enumerate(past_matches):
        print(f"  Past match {i}: '{past_match}'")

if __name__ == "__main__":
    test_route_patterns()
