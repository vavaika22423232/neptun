#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test the multi-UAV message with numbered list
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_numbered_uav_message():
    print("=== Тестування нумерованого UAV повідомлення ===")
    
    test_message = """🛵 Інформація щодо руху ворожих ударних БпЛА:
1. БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина);
2. БпЛА на сході Чернігівщини курсом на н.п.Батурин.
3. БпЛА на південному заході Дніпропетровщини, курс - південно-західний/південно-східний."""
    
    print(f"Повідомлення:")
    print(test_message)
    print()
    
    result = process_message(test_message, "test_numbered_uav", "2025-09-09 12:00:00", "test_channel")
    
    if result and isinstance(result, list):
        print(f"✅ Маркерів: {len(result)}")
        for i, marker in enumerate(result, 1):
            place = marker.get('place', 'N/A')
            coords = (marker.get('lat'), marker.get('lng'))
            source = marker.get('source_match', 'N/A')
            icon = marker.get('marker_icon', 'N/A')
            text = marker.get('text', 'N/A')[:100]
            
            print(f"  {i}. Місце: {place}")
            print(f"     Координати: {coords}")
            print(f"     Джерело: {source}")
            print(f"     Іконка: {icon}")
            print(f"     Текст: {text}...")
            print()
    else:
        print("❌ Маркери не створені")
    
    print("=" * 60)
    print("📊 АНАЛІЗ:")
    print("Очікується 3 маркери:")
    print("1. Вилково (Одещина)")
    print("2. Батурин (Чернігівщина)")  
    print("3. Центр Дніпропетровщини (через відсутність конкретного міста)")

if __name__ == "__main__":
    test_numbered_uav_message()
