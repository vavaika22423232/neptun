#!/usr/bin/env python3
"""
Debug route parser execution
"""

# Import from app.py
import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import process_message, clean_text, UA_CITY_NORMALIZE

def test_route_parser_execution():
    """Test if route parser is being executed"""
    
    test_message = """Кіровоградщина: Група 15х БпЛА через Компаніївка, Новоукраїнка. Курс Північно-Західний у напрямку Черкащини. Група 4х БпЛА повз Олександрію."""
    
    print("="*60)
    print("TESTING ROUTE PARSER EXECUTION")
    print("="*60)
    print(f"Message: {repr(test_message)}")
    print()
    
    # Test basic conditions
    lorig = test_message.lower()
    print("Basic conditions check:")
    print(f"  'бпла' in text: {'бпла' in lorig}")
    print(f"  'через' in text: {'через' in lorig}")
    print(f"  'повз' in text: {'повз' in lorig}")
    print(f"  Route condition: {'бпла' in lorig and ('через' in lorig or 'повз' in lorig)}")
    print()
    
    # Test regex patterns directly
    import re
    import re as _re_route
    route_pattern = r'через\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*\.\s+|$)'
    route_matches = _re_route.findall(route_pattern, test_message, re.IGNORECASE)
    print(f"Route pattern matches: {route_matches}")
    
    past_pattern = r'повз\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*\.\s*|$)'
    past_matches = _re_route.findall(past_pattern, test_message, re.IGNORECASE)
    print(f"Past pattern matches: {past_matches}")
    print()
    
    # Test city normalization
    if route_matches:
        for route_match in route_matches:
            print(f"Processing route match: '{route_match}'")
            cities_raw = [c.strip() for c in route_match.split(',') if c.strip()]
            print(f"  Raw cities: {cities_raw}")
            
            for city_raw in cities_raw:
                city_clean = city_raw.strip().strip('.,')
                city_norm = clean_text(city_clean).lower()
                print(f"    '{city_raw}' -> clean: '{city_clean}' -> norm: '{city_norm}'")
                
                if city_norm in UA_CITY_NORMALIZE:
                    city_norm = UA_CITY_NORMALIZE[city_norm]
                    print(f"      Normalized to: '{city_norm}'")

if __name__ == "__main__":
    test_route_parser_execution()
