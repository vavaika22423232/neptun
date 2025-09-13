#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест для проверки, что координаты городов Одесской области определяются правильно
"""

import sys
import os

# Добавляем текущую папку в sys.path чтобы импортировать app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import ensure_city_coords
    
    def test_coords():
        print("=== Тест исправления координат одесских городов ===\n")
        
        test_cases = [
            ("Сергіївка (Одеська обл.)", "сергіївка", (46.0006, 29.9578)),
            ("Тузли (Одеська обл.)", "тузли", (45.8650, 30.0975)),
            ("Для сравнения - Луцьк", "луцьк", (50.7472, 25.3254)),
            ("Для сравнения - Миколаїв", "миколаїв", (46.9750, 31.9946)),
        ]
        
        for city_desc, city_key, expected_coords in test_cases:
            try:
                result = ensure_city_coords(city_key)
                if result:
                    lat, lon, is_approx = result
                    print(f"✅ {city_desc}:")
                    print(f"   Ключ: '{city_key}'")
                    print(f"   Ожидаемые координаты: {expected_coords}")
                    print(f"   Фактические координаты: ({lat}, {lon})")
                    print(f"   Точность: {'приблизительные (oblast fallback)' if is_approx else 'точные'}")
                    
                    if abs(lat - expected_coords[0]) < 0.001 and abs(lon - expected_coords[1]) < 0.001:
                        print(f"   ✅ ПРАВИЛЬНО")
                    else:
                        print(f"   ❌ НЕПРАВИЛЬНО")
                    print()
                else:
                    print(f"❌ {city_desc}: координаты не найдены для ключа '{city_key}'")
                    print()
            except Exception as e:
                print(f"❌ Ошибка для {city_desc}: {e}")
                print()

    if __name__ == "__main__":
        test_coords()

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
