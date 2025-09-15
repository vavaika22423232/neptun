#!/usr/bin/env python3
"""
Test script for multi-line threat message processing with detailed debugging
"""

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import process_message, add_debug_log
import re

def test_threat_line_detection():
    """Test the threat line detection logic"""
    
    test_lines = [
        "10х БпЛА курсом на Доброслав",
        "8 шахедів на Березнегувате",  
        "4 шахеди на Очаків",
        "5 шахедів на Велику Виску"
    ]
    
    print("Testing individual threat line detection:")
    for i, line in enumerate(test_lines):
        print(f"\nLine {i+1}: {line}")
        line_lower = line.lower()
        
        # Test each pattern
        pattern1 = re.search(r'\d+\s*[xх×]\s*бпла.*?(курс|на)\s+([а-яіїєё\'\-\s]+)', line_lower)
        pattern2 = re.search(r'\d+\s+шахед[а-яіїєёыийї]*\s+на\s+([а-яіїєё\'\-\s]+)', line_lower)
        pattern3 = re.search(r'\d+\s+ударн.*?бпла.*?на\s+([а-яіїєё\'\-\s]+)', line_lower)
        pattern4 = re.search(r'\d+\s+бпла.*?на\s+([а-яіїєё\'\-\s]+)', line_lower)
        pattern5 = re.search(r'бпла.*?курс.*?на\s+([а-яіїєё\'\-\s]+)', line_lower)
        
        print(f"  Pattern 1 (N x БпЛА курс): {bool(pattern1)}")
        print(f"  Pattern 2 (N шахед на): {bool(pattern2)}")
        print(f"  Pattern 3 (N ударн БпЛА): {bool(pattern3)}")
        print(f"  Pattern 4 (N БпЛА на): {bool(pattern4)}")
        print(f"  Pattern 5 (БпЛА курс): {bool(pattern5)}")
        
        has_threat = pattern1 or pattern2 or pattern3 or pattern4 or pattern5
        print(f"  Should be detected: {has_threat}")

def test_multi_line_threats():
    """Test the multi-line threat processing logic"""
    
    # Test message similar to user's example
    test_message = """10х БпЛА курсом на Доброслав
8 шахедів на Березнегувате  
4 шахеди на Очаків
5 шахедів на Велику Виску"""
    
    print("\n" + "="*60)
    print("Testing multi-line threat message:")
    print(f"Input: {test_message}")
    print("-" * 50)
    
    # Process the message
    result = process_message(test_message, "test_123", "2024-01-15 10:30", "test_channel")
    
    print(f"Result type: {type(result)}")
    if isinstance(result, list):
        print(f"Number of tracks: {len(result)}")
        for i, track in enumerate(result):
            print(f"Track {i+1}:")
            print(f"  - ID: {track.get('id', 'N/A')}")
            print(f"  - Place: {track.get('place', 'N/A')}")
            print(f"  - Type: {track.get('threat_type', 'N/A')}")
            print(f"  - Count: {track.get('count', 'N/A')}")
            print(f"  - Source: {track.get('source_match', 'N/A')}")
    else:
        print(f"Unexpected result: {result}")

if __name__ == "__main__":
    test_threat_line_detection()
    test_multi_line_threats()
