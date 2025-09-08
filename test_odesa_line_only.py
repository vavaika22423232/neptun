#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test specifically the first line that's not working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_odesa_line_only():
    print("=== Тестування тільки рядка про Одещину ===")
    
    # Тільки перший рядок
    test_message = "на одещині 10 шахедів на вилкове"
    
    print(f"Повідомлення: '{test_message}'")
    print(f"Довжина: {len(test_message)}")
    print(f"Lower: '{test_message.lower()}'")
    
    result = process_message(test_message, "test_odesa_only", "2025-09-08 12:00:00", "test_channel")
    
    print(f"\nРезультат:")
    print(f"  Тип: {type(result)}")
    print(f"  Значення: {result}")
    
    if result and isinstance(result, list) and len(result) > 0:
        marker = result[0]
        print(f"\nМаркер:")
        print(f"  - Місце: {marker.get('place', 'N/A')}")
        print(f"  - Координати: ({marker.get('lat')}, {marker.get('lng')})")
        print(f"  - Іконка: {marker.get('marker_icon', 'N/A')}")
        print(f"  - Джерело: {marker.get('source_match', 'N/A')}")
        
        if marker.get('place', '').lower() == 'вилкове':
            print("  ✅ ПРАВИЛЬНО: Створений маркер для Вилкове")
        else:
            print(f"  ❌ ПОМИЛКА: Очікувалося Вилкове, отримано {marker.get('place')}")
    else:
        print("  ❌ МАРКЕР НЕ СТВОРЕНО")
        
        # Перевіримо чи є Вилкове в базі
        from app import CITY_COORDS, normalize_city_name, UA_CITY_NORMALIZE
        
        target_city = "вилкове"
        city_norm = normalize_city_name(target_city)
        city_norm = UA_CITY_NORMALIZE.get(city_norm, city_norm)
        coords = CITY_COORDS.get(city_norm)
        
        print(f"\n  🔍 ДЕБАГ:")
        print(f"    Ціль: '{target_city}'")
        print(f"    Нормалізоване: '{city_norm}'")
        print(f"    Координати: {coords}")
        
        if coords:
            print("    ✅ Вилкове є в базі координат")
        else:
            print("    ❌ Вилкове відсутнє в базі координат")

if __name__ == "__main__":
    test_odesa_line_only()
