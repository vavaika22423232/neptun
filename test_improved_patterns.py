#!/usr/bin/env python3
"""
Test improved route patterns
"""

import re

def test_improved_patterns():
    """Test improved route parsing patterns"""
    
    test_message = """Кіровоградщина: Група 15х БпЛА через Компаніївка, Новоукраїнка. Курс Північно-Західний у напрямку Черкащини. Група 4х БпЛА повз Олександрію."""
    
    print("="*60)
    print("TESTING IMPROVED ROUTE PATTERNS")
    print("="*60)
    print(f"Message: {repr(test_message)}")
    print()
    
    # Improved route pattern - captures everything until period or "курс"
    route_pattern = r'через\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*\.\s+|$)'
    print(f"Improved route pattern: {route_pattern}")
    
    route_matches = re.findall(route_pattern, test_message, re.IGNORECASE)
    print(f"Route matches: {route_matches}")
    
    for i, route_match in enumerate(route_matches):
        print(f"  Route match {i}: '{route_match}'")
        
        # Split by comma to get individual cities
        cities_raw = [c.strip() for c in route_match.split(',') if c.strip()]
        print(f"    Cities: {cities_raw}")
    
    print()
    
    # Test alternative - looking for word boundaries
    route_pattern2 = r'через\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?=\s*\.\s+курс|\s*\.\s*$)'
    print(f"Alternative pattern with lookahead: {route_pattern2}")
    
    route_matches2 = re.findall(route_pattern2, test_message, re.IGNORECASE)
    print(f"Route matches2: {route_matches2}")
    
    print()
    
    # Test for past pattern  
    past_pattern = r'повз\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*\.\s*|$)'
    print(f"Past pattern: {past_pattern}")
    
    past_matches = re.findall(past_pattern, test_message, re.IGNORECASE)
    print(f"Past matches: {past_matches}")

if __name__ == "__main__":
    test_improved_patterns()
