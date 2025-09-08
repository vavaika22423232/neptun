#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test processing of remaining text after district pattern removal
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_remaining_text():
    print("=== Тестування залишкового тексту ===")
    
    remaining_text = "та одещина - загроза застосування ворогом ударних бпла. | одещина - шахеди на вилково\nㅤ | група 8х бпла у напрямку ізмаїльського району одещини, вилкове."
    
    print(f"Залишковий текст:")
    print(repr(remaining_text))
    print()
    
    result = process_message(remaining_text, "test_remaining", "2025-09-08 12:00:00", "test_channel")
    
    if result and isinstance(result, list):
        print(f"✅ Маркерів: {len(result)}")
        for i, marker in enumerate(result, 1):
            place = marker.get('place', 'N/A')
            coords = (marker.get('lat'), marker.get('lng'))
            source = marker.get('source_match', 'N/A')
            icon = marker.get('marker_icon', 'N/A')
            
            print(f"  {i}. Місце: {place}")
            print(f"     Координати: {coords}")
            print(f"     Джерело: {source}")
            print(f"     Іконка: {icon}")
    else:
        print("❌ Маркери не створені")

if __name__ == "__main__":
    test_remaining_text()
