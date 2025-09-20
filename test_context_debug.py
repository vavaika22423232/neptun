#!/usr/bin/env python3
"""
Тест для отладки парсинга Миколаївки на Сумщині
"""

import sys
sys.path.insert(0, '.')

from app import ensure_city_coords_with_message_context

def test_context_resolution():
    """Тестирует работу контекстного разрешения городов"""
    
    # Тестовые варианты
    test_cases = [
        ("миколаївка", "1 шахед на Миколаївку на Сумщині"),
        ("миколаївку", "1 шахед на Миколаївку на Сумщині"),
        ("миколаївка", "Миколаївка сумщина"),
        ("миколаївка", "Миколаївка Сумська область"),
    ]
    
    for city_name, message_text in test_cases:
        print(f"\nТестируем: город='{city_name}', сообщение='{message_text}'")
        result = ensure_city_coords_with_message_context(city_name, message_text)
        
        if result:
            lat, lng, approx = result
            print(f"Результат: ({lat}, {lng}), приблизительно: {approx}")
            
            # Проверяем правильность
            expected_lat = 51.5667
            expected_lng = 34.1333
            tolerance = 0.1
            
            if (abs(lat - expected_lat) < tolerance and 
                abs(lng - expected_lng) < tolerance):
                print("✅ Правильные координаты!")
            else:
                print("❌ Неправильные координаты!")
        else:
            print("Результат: None")

if __name__ == "__main__":
    test_context_resolution()
