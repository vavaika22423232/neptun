#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест обработки второй строки отдельно для проверки Буська
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message, logging
import datetime

# Вторая строка из проблемного сообщения
TEST_LINE2 = "Загроза застосування БПЛА. Перейдіть в укриття! | 4х БпЛА курсом на Добротвір (мультирегіональне) | 🛸 Буськ (Львівська обл.)"

print("=== ТЕСТ ОБРАБОТКИ ВТОРОЙ СТРОКИ ===")
print("Строка:")
print(TEST_LINE2)
print("\n" + "="*50)

try:
    result = process_message(TEST_LINE2, "test_line2", datetime.datetime.now().isoformat(), "test_channel")
    
    print(f"\n=== РЕЗУЛЬТАТ ОБРАБОТКИ ВТОРОЙ СТРОКИ ===")
    print(f"Количество меток: {len(result) if result else 0}")
    
    if result and isinstance(result, list):
        for i, track in enumerate(result, 1):
            place = track.get('place', 'Unknown')
            lat = track.get('lat', 'N/A')
            lng = track.get('lng', 'N/A')
            source = track.get('source_match', 'Unknown source')
            print(f"  {i}. {place} ({lat}, {lng}) - {source}")
            
        # Проверяем наличие ожидаемых городов
        places = [track.get('place', '') for track in result]
        expected = ['Добротвір', 'Буськ']
        
        print(f"\n=== ОЖИДАЕМЫЕ ГОРОДА ===")
        for place in expected:
            if place in places:
                print(f"✅ {place} найден")
            else:
                print(f"❌ {place} НЕ найден")
    else:
        print("❌ Нет результатов")
        
except Exception as e:
    print(f"❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("=== АНАЛИЗ ===")
print("Ожидаем найти в этой строке:")
print("1. Добротвір - из курса '4х БпЛА курсом на Добротвір'")
print("2. Буськ - из структуры '| 🛸 Буськ (Львівська обл.)'")
