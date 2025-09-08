#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test individual lines from numbered UAV message
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_individual_lines():
    print("=== Тестування окремих ліній ===")
    
    lines = [
        "🛵 Інформація щодо руху ворожих ударних БпЛА:",
        "1. БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина);",
        "2. БпЛА на сході Чернігівщини курсом на н.п.Батурин.",
        "3. БпЛА на південному заході Дніпропетровщини, курс - південно-західний/південно-східний."
    ]
    
    for i, line in enumerate(lines, 1):
        print(f"\n--- Лінія {i}: ---")
        print(f"Текст: '{line}'")
        
        result = process_message(line, f"test_line_{i}", "2025-09-09 12:00:00", "test_channel")
        
        if result and isinstance(result, list):
            print(f"✅ Маркерів: {len(result)}")
            for j, marker in enumerate(result, 1):
                place = marker.get('place', 'N/A')
                coords = (marker.get('lat'), marker.get('lng'))
                source = marker.get('source_match', 'N/A')
                print(f"  {j}. {place} {coords} ({source})")
        else:
            print("❌ Маркери не створені")

if __name__ == "__main__":
    test_individual_lines()
