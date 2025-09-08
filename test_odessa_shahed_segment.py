#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test the specific segment that should create Vylkove marker
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_odessa_shahed_segment():
    print("=== Тестування сегменту 'одещина - шахеди на вилково' ===")
    
    test_message = "одещина - шахеди на вилково"
    print(f"Повідомлення: '{test_message}'")
    
    result = process_message(test_message, "test_odessa_shahed", "2025-09-08 12:00:00", "test_channel")
    
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
            
            if place.lower() == 'вилково' or place.lower() == 'вилкове':
                print(f"     ✅ ПРАВИЛЬНО: Створено маркер для Вилкове")
            elif 'одес' in place.lower():
                print(f"     ❌ ПОМИЛКА: Створено маркер для Одещини замість Вилкове")
            else:
                print(f"     ⚠️  ІНШЕ: {place}")
    else:
        print("❌ Маркери не створені")
    
    # Тестуємо також варіант "вилкове" замість "вилково"
    print(f"\n=== Тестування з 'вилкове' ===")
    test_message2 = "одещина - шахеди на вилкове"
    print(f"Повідомлення: '{test_message2}'")
    
    result2 = process_message(test_message2, "test_odessa_shahed2", "2025-09-08 12:00:00", "test_channel")
    
    if result2 and isinstance(result2, list):
        print(f"✅ Маркерів: {len(result2)}")
        for i, marker in enumerate(result2, 1):
            place = marker.get('place', 'N/A')
            coords = (marker.get('lat'), marker.get('lng'))
            source = marker.get('source_match', 'N/A')
            print(f"  {i}. {place} {coords} ({source})")
    else:
        print("❌ Маркери не створені")

if __name__ == "__main__":
    test_odessa_shahed_segment()
