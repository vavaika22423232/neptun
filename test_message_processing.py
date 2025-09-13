#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест для проверки того, что сообщения из Одесской области больше не отображаются неправильно
"""

import sys
import os

# Добавляем текущую папку в sys.path чтобы импортировать app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import find_city_from_general, ensure_city_coords

    def test_message_processing():
        print("=== Тест обработки сообщений из Одесской области ===\n")
        
        test_messages = [
            "🛸 Сергіївка (Одеська обл.) Загроза БпЛА!",
            "🛸 Тузли (Одеська обл.) Загроза БпЛА!",
            "💥 Сергіївка (Одеська обл.) Загроза обстрілу!",
        ]
        
        for msg in test_messages:
            print(f"Сообщение: {msg}")
            
            # Извлекаем город
            city = find_city_from_general(msg)
            if city:
                print(f"  Найден город: '{city}'")
                
                # Получаем координаты
                coords_result = ensure_city_coords(city)
                if coords_result:
                    lat, lon, is_approx = coords_result
                    print(f"  Координаты: ({lat}, {lon})")
                    print(f"  Точность: {'приблизительные (oblast fallback)' if is_approx else 'точные'}")
                    
                    # Проверяем, что не Луцьк и не Николаев
                    if abs(lat - 50.7472) < 0.001 and abs(lon - 25.3254) < 0.001:
                        print("  ❌ ОШИБКА: Определено как Луцьк!")
                    elif abs(lat - 46.9750) < 0.001 and abs(lon - 31.9946) < 0.001:
                        print("  ❌ ОШИБКА: Определено как Николаев!")
                    else:
                        print("  ✅ Правильно: не путается с другими городами")
                else:
                    print(f"  ❌ Координаты не найдены для города '{city}'")
            else:
                print(f"  ❌ Город не определен из сообщения")
            
            print()

    if __name__ == "__main__":
        test_message_processing()
        
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
