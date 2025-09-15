#!/usr/bin/env python3
"""
Test script for multi-line threat message processing
"""

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import process_message

def test_multi_line_threats():
    """Test the multi-line threat processing logic"""
    
    # Test message similar to user's example
    test_message = """10х БпЛА курсом на Доброслав
8 шахедів на Березнегувате  
4 шахеди на Очаків
5 шахедів на Велику Виску"""
    
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
    test_multi_line_threats()
