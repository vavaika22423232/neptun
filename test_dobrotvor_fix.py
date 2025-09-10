#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправления проблемы с Добротвором - полная обработка сообщения
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message, logging
import datetime

# Проблемное сообщение
TEST_MESSAGE = """Загроза застосування БПЛА. Перейдіть в укриття! | 🛸 Львів (Львівська обл.)
Загроза застосування БПЛА. Перейдіть в укриття! | 4х БпЛА курсом на Добротвір (мультирегіональне) | 🛸 Буськ (Львівська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""

print("=== ТЕСТ ПОЛНОЙ ОБРАБОТКИ СООБЩЕНИЯ ===")
print("Сообщение:")
print(TEST_MESSAGE)
print("\n" + "="*50)

try:
    # Обрабатываем сообщение
    print("=== ПЕРЕД ОБРАБОТКОЙ ===")
    print("Проверяем структуру сообщения:")
    lines = TEST_MESSAGE.split('\n')
    for i, line in enumerate(lines, 1):
        print(f"  Строка {i}: '{line}'")
        if '🛸' in line:
            print(f"    ✅ Содержит 🛸")
        if 'бпла' in line.lower():
            print(f"    ✅ Содержит БПЛА")
        if '🛸' in line and 'бпла' in line.lower():
            print(f"    ✅ UAV line!")
    
    result = process_message(TEST_MESSAGE, "test_id", datetime.datetime.now().isoformat(), "test_channel")
    
    print(f"\n=== РЕЗУЛЬТАТ ОБРАБОТКИ ===")
    print(f"Результат: {result}")
    print(f"Тип: {type(result)}")
    
    if result and isinstance(result, list):
        print(f"Количество меток: {len(result)}")
        
        if len(result) >= 2:
            print("🎉 ПРОБЛЕМА ЧАСТИЧНО РЕШЕНА! Создано больше одной метки")
        else:
            print("⚠️ Все еще только одна метка")
        
        print("\nВсе метки:")
        for i, track in enumerate(result, 1):
            place = track.get('place', 'Unknown')
            lat = track.get('lat', 'N/A')
            lng = track.get('lng', 'N/A')
            source = track.get('source_match', 'Unknown source')
            threat_type = track.get('threat_type', 'Unknown')
            print(f"  {i}. {place} ({lat}, {lng})")
            print(f"     Источник: {source}, Тип: {threat_type}")
            
        # Проверяем наличие ожидаемых городов
        places = [track.get('place', '') for track in result]
        expected_places = ['Львів', 'Добротвір', 'Буськ']
        
        print(f"\n=== ПРОВЕРКА ОЖИДАЕМЫХ ГОРОДОВ ===")
        for place in expected_places:
            if place in places:
                print(f"✅ {place} найден")
            else:
                print(f"❌ {place} НЕ найден")
                
        found_count = sum(1 for place in expected_places if place in places)
        print(f"\nНайдено {found_count} из {len(expected_places)} ожидаемых городов")
        
except Exception as e:
    print(f"❌ ОШИБКА ПРИ ОБРАБОТКЕ: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("=== АНАЛИЗ ===")
print("До исправления: только метка Львова")
print("После исправления: метки Львова, Буська И Добротвора")
print("Ожидаемый результат: 3 метки вместо 1")
