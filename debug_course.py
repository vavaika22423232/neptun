#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug course extraction integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message, extract_shahed_course_info

def debug_course_integration():
    """Debug why course info is not being added to threats"""
    
    test_text = "БпЛА курсом на Кременчук з Дніпропетровщини"
    
    print("🔍 Debugging course integration...\n")
    print(f"Input text: {test_text}")
    
    # Test course extraction directly
    course_info = extract_shahed_course_info(test_text)
    print(f"Course extraction result: {course_info}")
    
    # Test full message processing
    result = process_message(test_text, 'debug_001', '2024-01-01 12:00:00', 'debug_channel')
    
    if result and isinstance(result, list) and len(result) > 0:
        threat = result[0]
        print(f"\nThreat created:")
        print(f"  Type: {threat.get('threat_type')}")
        print(f"  Place: {threat.get('place')}")
        print(f"  Source match: {threat.get('source_match')}")
        
        # Check all keys to see if course info was added
        course_keys = [k for k in threat.keys() if 'course' in k]
        if course_keys:
            print(f"  Course keys found: {course_keys}")
            for key in course_keys:
                print(f"    {key}: {threat.get(key)}")
        else:
            print(f"  ❌ No course keys found in threat")
            print(f"  All keys: {list(threat.keys())}")
    else:
        print(f"❌ No threats created")

if __name__ == '__main__':
    debug_course_integration()
