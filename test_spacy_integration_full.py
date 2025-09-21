#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test SpaCy integration in app.py
"""

# Test with our problematic message
def test_spacy_mykolaivka():
    """Test the specific Mykolaivka issue"""
    
    # Import the functions from app.py
    import sys
    import os
    sys.path.append('/Users/vladimirmalik/Desktop/render2')
    
    from app import process_message, SPACY_AVAILABLE
    
    print(f"SpaCy available: {SPACY_AVAILABLE}")
    
    test_message = "1 шахед на Миколаївку на Сумщині"
    mid = "test_123"
    date_str = "2025-09-21 12:00:00"
    channel = "test_channel"
    
    print(f"\nTesting message: {test_message}")
    
    try:
        result = process_message(test_message, mid, date_str, channel)
        
        if result:
            print(f"✅ SUCCESS: Found {len(result)} markers")
            for marker in result:
                print(f"  📍 {marker['place']} at ({marker['lat']}, {marker['lng']})")
                print(f"      Source: {marker.get('source_match', 'unknown')}")
                if 'confidence' in marker:
                    print(f"      Confidence: {marker['confidence']}")
                print()
        else:
            print("❌ FAILED: No markers found")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_other_messages():
    """Test other message types"""
    
    import sys
    sys.path.append('/Users/vladimirmalik/Desktop/render2')
    from app import process_message
    
    test_cases = [
        "БпЛА курсом на Харків через Полтаву",
        "2х БпЛА повз Конотоп у напрямку Глухова", 
        "Чернігівщина: 3 шахеди на Новгород-Сіверський",
        "Обстріл Херсона та Миколаєва"
    ]
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n=== Test {i}: {message} ===")
        try:
            result = process_message(message, f"test_{i}", "2025-09-21 12:00:00", "test")
            if result:
                print(f"✅ Found {len(result)} markers:")
                for marker in result:
                    print(f"  📍 {marker['place']} ({marker.get('source_match', 'unknown')})")
            else:
                print("❌ No markers found")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=== SpaCy Integration Test ===")
    test_spacy_mykolaivka()
    test_other_messages()
