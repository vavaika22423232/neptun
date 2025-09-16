#!/usr/bin/env python3
"""
Comprehensive test for multi-line threat message processing
"""

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import process_message

def test_various_multi_line_patterns():
    """Test different types of multi-line threat messages"""
    
    test_cases = [
        {
            "name": "Mixed БпЛА and Shahed threats",
            "message": """10х БпЛА курсом на Доброслав
8 шахедів на Березнегувате  
4 шахеди на Очаків
5 шахедів на Велику Виску""",
            "expected_count": 4
        },
        {
            "name": "Only Shahed threats",
            "message": """3 шахеди на Київ
6 шахедів на Харків
2 шахеди на Одесу""",
            "expected_count": 3
        },
        {
            "name": "Only БпЛА threats",
            "message": """5х БпЛА курсом на Суми
3х БпЛА курсом на Полтаву""",
            "expected_count": 2
        },
        {
            "name": "Single threat (should not trigger multi-line)",
            "message": """10х БпЛА курсом на Доброслав""",
            "expected_count": 1
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"Test {i+1}: {test_case['name']}")
        print(f"{'='*60}")
        print(f"Input:\n{test_case['message']}")
        print("-" * 50)
        
        # Process the message
        result = process_message(test_case['message'], f"test_{i+1}", "2024-01-15 10:30", "test_channel")
        
        if isinstance(result, list):
            actual_count = len(result)
            expected_count = test_case['expected_count']
            
            status = "✅ PASS" if actual_count == expected_count else "❌ FAIL"
            print(f"Result: {status} - Expected {expected_count}, got {actual_count} tracks")
            
            for j, track in enumerate(result):
                print(f"  Track {j+1}:")
                print(f"    - Place: {track.get('place', 'N/A')}")
                print(f"    - Type: {track.get('threat_type', 'N/A')}")
                print(f"    - Count: {track.get('count', 'N/A')}")
                print(f"    - Source: {track.get('source_match', 'N/A')}")
        else:
            print(f"❌ FAIL - Unexpected result type: {type(result)}")

def test_edge_cases():
    """Test edge cases for multi-line processing"""
    
    print(f"\n{'='*60}")
    print("Edge Cases Test")
    print(f"{'='*60}")
    
    # Test with empty lines
    test_message = """10х БпЛА курсом на Доброслав

8 шахедів на Березнегувате  

4 шахеди на Очаків"""
    
    print(f"Test: Message with empty lines")
    print(f"Input:\n{repr(test_message)}")
    
    result = process_message(test_message, "edge_test", "2024-01-15 10:30", "test_channel")
    
    if isinstance(result, list):
        print(f"Result: {len(result)} tracks (expected 3)")
        for j, track in enumerate(result):
            print(f"  Track {j+1}: {track.get('place', 'N/A')}")
    else:
        print(f"Unexpected result: {result}")

if __name__ == "__main__":
    test_various_multi_line_patterns()
    test_edge_cases()
