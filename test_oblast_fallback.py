#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест для проверки улучшенного fallback механизма - 
когда город не найден, должны использоваться координаты области из сообщения
"""

import sys
import os

# Добавляем текущую папку в sys.path чтобы импортировать app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import ensure_city_coords_with_message_context, process_message, OBLAST_CENTERS
    
    def test_oblast_fallback():
        print("=== Тест fallback к координатам области ===\n")
        
        print("1. Проверка функции ensure_city_coords_with_message_context:")
        
        test_cases = [
            {
                'city': 'невідомемісто',
                'message': '🛸 Невідомемісто (Херсонська обл.) Загроза БпЛА!',
                'expected_oblast': 'херсонська обл.',
                'expected_coords': (46.6354, 32.6169),
                'description': 'Неизвестный город в Херсонской области'
            },
            {
                'city': 'якесьселище',
                'message': '💥 Якесьселище (Дніпропетровська область) Загроза обстрілу!',
                'expected_oblast': 'дніпропетровська область',
                'expected_coords': (48.4500, 34.9830),
                'description': 'Неизвестное село в Днепропетровской области'
            },
            {
                'city': 'тестовечорнобаївка',
                'message': '🛸 Тестовечорнобаївка (Львівська обл.) Загроза БпЛА!',
                'expected_oblast': 'львівська обл.',
                'expected_coords': (49.8397, 24.0297),
                'description': 'Тестовый город во Львовской области'
            }
        ]
        
        for test in test_cases:
            print(f"  Тест: {test['description']}")
            print(f"    Сообщение: {test['message']}")
            
            coords = ensure_city_coords_with_message_context(test['city'], test['message'])
            
            if coords:
                lat, lon, is_approx = coords
                print(f"    Результат: ({lat}, {lon}), приблизительно: {is_approx}")
                
                # Проверяем, что используются координаты области
                expected_lat, expected_lon = test['expected_coords']
                if abs(lat - expected_lat) < 0.1 and abs(lon - expected_lon) < 0.1:
                    print(f"    ✅ ПРАВИЛЬНО: Использованы координаты {test['expected_oblast']}")
                else:
                    print(f"    ❌ НЕПРАВИЛЬНО: Ожидались координаты ({expected_lat}, {expected_lon})")
                    
                if is_approx:
                    print(f"    ✅ Корректно помечено как приблизительное (область)")
                else:
                    print(f"    ⚠️ Должно быть помечено как приблизительное")
            else:
                print(f"    ❌ Координаты не найдены")
            print()
        
        print("2. Проверка полной обработки сообщений:")
        
        message_tests = [
            {
                'message': '🛸 Невідомеселище (Одеська обл.) Загроза БпЛА!',
                'expected_oblast_coords': (46.4825, 30.7233),  # Одесская область
                'description': 'Неизвестное село в Одесской области'
            }
        ]
        
        for test in message_tests:
            print(f"  Тест: {test['description']}")
            print(f"    Сообщение: {test['message']}")
            
            try:
                result = process_message(test['message'], "test_1", "2025-09-13", "test_channel")
                
                if result and len(result) > 0:
                    message_data = result[0]
                    place = message_data.get('place', 'не найдено')
                    lat = message_data.get('lat', None)
                    lng = message_data.get('lng', None)
                    
                    print(f"    Результат: место={place}, координаты=({lat}, {lng})")
                    
                    if lat and lng:
                        expected_lat, expected_lon = test['expected_oblast_coords']
                        if abs(lat - expected_lat) < 0.1 and abs(lng - expected_lon) < 0.1:
                            print(f"    ✅ ОТЛИЧНО: Использованы координаты области!")
                        else:
                            print(f"    ❌ Координаты не соответствуют ожидаемым ({expected_lat}, {expected_lon})")
                else:
                    print(f"    ❌ Сообщение не обработано")
            except Exception as e:
                print(f"    ❌ ОШИБКА: {e}")
            print()
        
        print("3. Справка - доступные области в OBLAST_CENTERS:")
        oblast_keys = sorted(list(OBLAST_CENTERS.keys())[:10])  # Показываем первые 10 для примера
        for key in oblast_keys:
            lat, lon = OBLAST_CENTERS[key]
            print(f"    '{key}': ({lat}, {lon})")
        print(f"    ... и еще {len(OBLAST_CENTERS) - 10} областей")

    if __name__ == "__main__":
        test_oblast_fallback()

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
