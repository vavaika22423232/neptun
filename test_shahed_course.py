#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Shahed course extraction functionality
"""

import sys
import os

# Add the current directory to Python path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import extract_shahed_course_info, process_message

def test_shahed_course_extraction():
    """Test the extract_shahed_course_info function with various patterns"""
    
    test_cases = [
        {
            'text': 'БпЛА курсом з Дніпропетровщини на Полтавщину',
            'expected_source': 'дніпропетровщина',
            'expected_target': 'полтавщина',
            'expected_type': 'full_course'
        },
        {
            'text': '5х БпЛА курсом на Кременчук з півночі',
            'expected_target': 'кременчук',
            'expected_direction': 'з півночі',
            'expected_type': 'target_with_direction'
        },
        {
            'text': 'Шахеди курсом на південно-західний напрямок',
            'expected_direction': 'південно-західний напрямок',
            'expected_type': 'directional'
        },
        {
            'text': 'БпЛА з Херсонщини у напрямку Миколаїв',
            'expected_source': 'херсонщина',
            'expected_target': 'миколаїв',
            'expected_type': 'full_course'
        },
        {
            'text': '3х БпЛА курс східний (Харків)',
            'expected_target': 'харків',
            'expected_direction': 'східний',
            'expected_type': 'target_with_direction'
        }
    ]
    
    print("🧪 Testing Shahed course extraction...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['text']}")
        result = extract_shahed_course_info(test_case['text'])
        
        print(f"  Result: {result}")
        
        # Check expected values
        if 'expected_source' in test_case:
            expected = test_case['expected_source']
            actual = result.get('source_city', '') if result else ''
            actual = actual.lower() if actual else ''
            status = "✅" if expected in actual else "❌"
            print(f"  Source: {status} Expected '{expected}', got '{actual}'")
        
        if 'expected_target' in test_case:
            expected = test_case['expected_target']
            actual = result.get('target_city', '') if result else ''
            actual = actual.lower() if actual else ''
            status = "✅" if expected in actual else "❌"
            print(f"  Target: {status} Expected '{expected}', got '{actual}'")
        
        if 'expected_direction' in test_case:
            expected = test_case['expected_direction']
            actual = result.get('course_direction', '') if result else ''
            actual = actual.lower() if actual else ''
            status = "✅" if expected in actual else "❌"
            print(f"  Direction: {status} Expected '{expected}', got '{actual}'")
        
        if 'expected_type' in test_case:
            expected = test_case['expected_type']
            actual = result.get('course_type', '') if result else ''
            status = "✅" if expected == actual else "❌"
            print(f"  Type: {status} Expected '{expected}', got '{actual}'")
        
        print()

def test_process_message_with_course():
    """Test process_message integration with course extraction"""
    
    test_messages = [
        {
            'text': 'БпЛА курсом на Кременчук з Дніпропетровщини',
            'mid': 'test_001',
            'date_str': '2024-01-01 12:00:00',
            'channel': 'test_channel'
        },
        {
            'text': '🚁 Дніпропетровська область (Синельниківський р-н) - загроза застосування авіаційних засобів ураження!',
            'mid': 'test_002', 
            'date_str': '2024-01-01 12:00:00',
            'channel': 'test_channel'
        }
    ]
    
    print("🧪 Testing process_message with course extraction...\n")
    
    for i, test_msg in enumerate(test_messages, 1):
        print(f"Test {i}: {test_msg['text'][:50]}...")
        
        result = process_message(
            test_msg['text'],
            test_msg['mid'], 
            test_msg['date_str'],
            test_msg['channel']
        )
        
        print(f"  Result type: {type(result)}")
        
        if result and isinstance(result, list) and len(result) > 0:
            threat = result[0]
            print(f"  Threat type: {threat.get('threat_type')}")
            print(f"  Place: {threat.get('place')}")
            
            # Check for course information
            course_fields = ['course_source', 'course_target', 'course_direction', 'course_type']
            course_info = {field: threat.get(field) for field in course_fields if threat.get(field)}
            
            if course_info:
                print(f"  Course info: ✅ {course_info}")
            else:
                print(f"  Course info: ❌ None found")
        else:
            print(f"  No threats found")
        
        print()

if __name__ == '__main__':
    test_shahed_course_extraction()
    test_process_message_with_course()
    print("✅ Course extraction testing completed!")
