#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test additional Zhytomyr Oblast cities to ensure they don't fallback to Zhytomyr city
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_zhytomyr_oblast_cities():
    print("=== Тестування міст Житомирської області ===")
    
    test_cities = [
        ("Коростень", "🛸 Коростень (Житомирська обл.)\nЗагроза застосування БПЛА"),
        ("Бердичів", "🛸 Бердичів (Житомирська обл.)\nЗагроза застосування БПЛА"),
        ("Новоград-Волинський", "🛸 Новоград-Волинський (Житомирська обл.)\nЗагроза застосування БПЛА"),
        ("Малин", "🛸 Малин (Житомирська обл.)\nЗагроза застосування БПЛА"),
        ("Звягель", "🛸 Звягель (Житомирська обл.)\nЗагроза застосування БПЛА")
    ]
    
    for city_name, test_message in test_cities:
        print(f"\n📍 Тестування {city_name}:")
        print(f"Повідомлення: {test_message}")
        
        result = process_message(test_message, f"test_{city_name}", "2025-09-08 12:00:00", "test_channel")
        
        if result and isinstance(result, list) and len(result) > 0:
            marker = result[0]
            place = marker.get('place', '')
            coordinates = (marker.get('lat'), marker.get('lng'))
            
            if place.lower() == city_name.lower():
                print(f"  ✅ ПРАВИЛЬНО: Маркер для {place}")
                print(f"     Координати: {coordinates}")
            elif 'житомир' in place.lower() and place.lower() != city_name.lower():
                print(f"  ❌ ПОМИЛКА: Fallback до Житомира замість {city_name}")
                print(f"     Отримано: {place} з координатами {coordinates}")
            else:
                print(f"  ✅ ПРАВИЛЬНО: Маркер для {place}")
                print(f"     Координати: {coordinates}")
        else:
            print(f"  ❌ ПОМИЛКА: Маркер не створено для {city_name}")
    
    print(f"\n{'='*60}")
    print("Тестування завершено!")

if __name__ == "__main__":
    test_zhytomyr_oblast_cities()
