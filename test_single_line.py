#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import process_message

def test_single_line():
    print("=== Testing Single Line ===")
    
    message = "10 шахедів біля Вознесенська та район"
    print(f"Message: {message}")
    print()
    
    markers = process_message(message, mid=12345, date_str='2025-09-17', channel='test')
    
    print(f"Found {len(markers)} markers:")
    for i, marker in enumerate(markers, 1):
        print(f"{i}. {marker['place']} at ({marker['lat']}, {marker['lng']}) - {marker['source_match']}")
        print(f"   Text: {marker['text'][:100]}...")
        print(f"   Threat type: {marker['threat_type']}")
        print()

if __name__ == "__main__":
    test_single_line()
