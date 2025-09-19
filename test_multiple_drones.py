#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_multiple_drones_display():
    """Test that multiple drones create multiple separate markers."""
    
    text = """7х БпЛА курсом на Смілу
3х БпЛА курсом на Полтаву
БпЛА курсом на Харків"""

    print("=== Тест множественных дронов ===")
    print(f"Текст сообщения:\n{text}\n")
    
    result = process_message(text, "test_multiple_drones", "2025-09-19 23:10:00", "test_channel")
    
    print(f"Результат обработки: {type(result)}")
    
    if isinstance(result, list):
        print(f"Количество меток: {len(result)}")
        
        # Группируем по городам
        cities = {}
        for item in result:
            place = item.get('place', '')
            # Извлекаем базовое название города (без #1, #2 и т.д.)
            base_city = place.split(' #')[0] if ' #' in place else place
            
            if base_city not in cities:
                cities[base_city] = []
            cities[base_city].append(item)
        
        print("\n=== Метки по городам ===")
        for city, items in cities.items():
            print(f"\n{city}: {len(items)} меток")
            for i, item in enumerate(items, 1):
                place_name = item.get('place', 'неизвестно')
                lat = item.get('lat', 'нет')
                lng = item.get('lng', 'нет')
                count = item.get('count', 1)
                print(f"  {i}. {place_name}: ({lat}, {lng}) count={count}")
        
        # Проверим ожидаемые результаты
        expected = {
            'Сміла': 7,    # 7х БпЛА
            'Полтава': 3,  # 3х БпЛА  
            'Харків': 1    # БпЛА (без числа)
        }
        
        print(f"\n=== Проверка результатов ===")
        total_expected = sum(expected.values())
        print(f"Ожидалось меток: {total_expected}")
        print(f"Получено меток: {len(result)}")
        
        all_correct = True
        for city, expected_count in expected.items():
            actual_count = len(cities.get(city, []))
            status = "✅" if actual_count == expected_count else "❌"
            print(f"{status} {city}: {actual_count}/{expected_count} меток")
            if actual_count != expected_count:
                all_correct = False
        
        if all_correct and len(result) == total_expected:
            print(f"\n🎉 УСПЕХ! Все метки созданы правильно!")
        else:
            print(f"\n⚠️  Есть расхождения в количестве меток")
            
    else:
        print("Ошибка: результат не является списком")
        print(f"Результат: {result}")

if __name__ == "__main__":
    test_multiple_drones_display()
