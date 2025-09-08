#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Ovurch BPLA message parsing to ensure it creates marker in Ovurch, not Zhytomyr
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_ovruch_message():
    print("=== Тестування повідомлення про Овруч ===")
    
    # Тестове повідомлення про Овруч (Житомирська обл.)
    test_message = "🛸 Овруч (Житомирська обл.)\nЗагроза застосування БПЛА. Перейдіть в укриття!"
    
    print(f"Вхідне повідомлення:\n{test_message}")
    print("\n" + "="*50)
    
    result = process_message(test_message, "test_123", "2025-09-08 12:00:00", "test_channel")
    
    print(f"\nРезультат парсингу:")
    print(f"- Тип результату: {type(result)}")
    print(f"- Результат: {result}")
    
    if result and isinstance(result, list):
        print(f"- Кількість маркерів: {len(result)}")
        
        for i, marker in enumerate(result, 1):
            print(f"\nМаркер {i}:")
            print(f"  - Місце: {marker.get('place', 'N/A')}")
            print(f"  - Координати: ({marker.get('lat', 'N/A')}, {marker.get('lng', 'N/A')})")
            print(f"  - Тип загрози: {marker.get('threat_type', 'N/A')}")
            print(f"  - Іконка: {marker.get('marker_icon', 'N/A')}")
            print(f"  - Джерело: {marker.get('source_match', 'N/A')}")
                
            # Перевіримо, що це саме Овруч, а не Житомир
            place_name = marker.get('place', '').lower()
            if 'овруч' in place_name:
                print(f"  ✅ ПРАВИЛЬНО: Маркер створено для Овруча")
                # Перевіримо координати Овруча
                if marker.get('lat') == 51.3244 and marker.get('lng') == 28.8006:
                    print(f"  ✅ КООРДИНАТИ: Правильні координати Овруча")
                else:
                    print(f"  ⚠️  КООРДИНАТИ: Неочікувані координати")
            elif 'житомир' in place_name:
                print(f"  ❌ ПОМИЛКА: Маркер створено для Житомира замість Овруча")
            else:
                print(f"  ⚠️  УВАГА: Неочікуване місто: {place_name}")
    else:
        print("❌ ПОМИЛКА: Маркери не створені або неправильний формат")
    
    print("\n" + "="*50)
    return result

if __name__ == "__main__":
    test_ovruch_message()
