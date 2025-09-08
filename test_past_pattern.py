#!/usr/bin/env python3
"""
Test past pattern specifically
"""

import re

def test_past_pattern():
    """Test past pattern matching"""
    
    test_message = """Кіровоградщина: Група 15х БпЛА через Компаніївка, Новоукраїнка. Курс Північно-Західний у напрямку Черкащини. Група 4х БпЛА повз Олександрію."""
    
    print("="*60)
    print("TESTING PAST PATTERN")
    print("="*60)
    print(f"Message: {test_message}")
    print()
    
    past_pattern = r'повз\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+?)(?:\s*\.\s*|$)'
    past_matches = re.findall(past_pattern, test_message, re.IGNORECASE)
    print(f"Past pattern: {past_pattern}")
    print(f"Past matches: {past_matches}")
    
    # Also test without the end anchor
    past_pattern2 = r'повз\s+([А-ЯІЇЄЁа-яіїєё\s\',\-]+)'
    past_matches2 = re.findall(past_pattern2, test_message, re.IGNORECASE)
    print(f"Past pattern2 (simpler): {past_pattern2}")
    print(f"Past matches2: {past_matches2}")

if __name__ == "__main__":
    test_past_pattern()
