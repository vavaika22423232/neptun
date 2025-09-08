#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test processing of individual segments from complex message
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_segment_1():
    print("=== Тестування сегменту 1 ===")
    
    test_message = "чернігівщина (новгород-сіверський р-н) та одещина - загроза застосування ворогом ударних бпла. | одещина - шахеди на вилково"
    print(f"Повідомлення: '{test_message}'")
    
    result = process_message(test_message, "test_segment1", "2025-09-08 12:00:00", "test_channel")
    
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

def test_segment_2():
    print("\n=== Тестування сегменту 2 ===")
    
    test_message = "ㅤ | група 8х бпла у напрямку ізмаїльського району одещини, вилкове."
    print(f"Повідомлення: '{test_message}'")
    
    result = process_message(test_message, "test_segment2", "2025-09-08 12:00:00", "test_channel")
    
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

def test_novgorod_simple():
    print("\n=== Тестування простого Новгород-Сіверський ===")
    
    test_message = "чернігівщина - бпла новгород-сіверський"
    print(f"Повідомлення: '{test_message}'")
    
    result = process_message(test_message, "test_novgorod", "2025-09-08 12:00:00", "test_channel")
    
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
    test_segment_1()
    test_segment_2()
    test_novgorod_simple()
