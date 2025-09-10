#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест нового проблемного сообщения с множественными UAV курсами
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message, logging
import datetime

# Новое проблемное сообщение
TEST_MESSAGE = "2х БпЛА курсом на Соснівку | 2х БпЛА повз Дубляни курсом на Львів | БпЛА курсом на Буськ"

print("=== ТЕСТ НОВОГО ПРОБЛЕМНОГО СООБЩЕНИЯ ===")
print("Сообщение:")
print(TEST_MESSAGE)
print("\n" + "="*50)

print("=== АНАЛИЗ СТРУКТУРЫ ===")
parts = TEST_MESSAGE.split('|')
print(f"Количество частей (разделенных '|'): {len(parts)}")
for i, part in enumerate(parts, 1):
    part = part.strip()
    print(f"  Часть {i}: '{part}'")
    if 'бпла' in part.lower():
        print(f"    ✅ Содержит БПЛА")
    if 'курс' in part.lower():
        print(f"    ✅ Содержит курс")
    if 'на ' in part.lower():
        print(f"    ✅ Содержит 'на'")

print("\n" + "="*50)

try:
    result = process_message(TEST_MESSAGE, "test_multi_uav", datetime.datetime.now().isoformat(), "test_channel")
    
    print(f"\n=== РЕЗУЛЬТАТ ОБРАБОТКИ ===")
    print(f"Количество меток: {len(result) if result else 0}")
    
    if result and isinstance(result, list):
        for i, track in enumerate(result, 1):
            place = track.get('place', 'Unknown')
            lat = track.get('lat', 'N/A')
            lng = track.get('lng', 'N/A')
            source = track.get('source_match', 'Unknown source')
            text = track.get('text', 'No text')
            print(f"  {i}. {place} ({lat}, {lng})")
            print(f"     Источник: {source}")
            print(f"     Текст: {text}")
            
        # Проверяем наличие ожидаемых городов
        places = [track.get('place', '') for track in result]
        expected_places = ['Соснівка', 'Дубляни', 'Львів', 'Буськ']
        
        print(f"\n=== ПРОВЕРКА ОЖИДАЕМЫХ ГОРОДОВ ===")
        for place in expected_places:
            if place in places:
                print(f"✅ {place} найден")
            else:
                print(f"❌ {place} НЕ найден")
                
        found_count = sum(1 for place in expected_places if place in places)
        print(f"\nНайдено {found_count} из {len(expected_places)} ожидаемых городов")
        
        if len(result) == 1:
            print("⚠️ ПРОБЛЕМА: Только одна метка вместо нескольких!")
        else:
            print("✅ Создано несколько меток")
            
    else:
        print("❌ Нет результатов")
        
except Exception as e:
    print(f"❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("=== ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ===")
print("Должно быть создано 4 метки:")
print("1. Соснівка - из '2х БпЛА курсом на Соснівку'")
print("2. Дубляни - из '2х БпЛА повз Дубляни'") 
print("3. Львів - из 'курсом на Львів'")
print("4. Буськ - из 'БпЛА курсом на Буськ'")
print("Но получаем только одну метку во Львове")
