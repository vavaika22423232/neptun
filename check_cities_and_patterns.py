#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка наличия городов в базе данных координат
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import CITY_COORDS, UA_CITY_NORMALIZE, ensure_city_coords

cities_to_check = ['соснівка', 'дубляни', 'львів', 'буськ']

print("=== ПРОВЕРКА ГОРОДОВ В БАЗЕ ДАННЫХ ===")

for city in cities_to_check:
    print(f"\n🔍 Проверяем: {city}")
    
    # Прямой поиск
    if city in CITY_COORDS:
        coords = CITY_COORDS[city]
        print(f"  ✅ Найден напрямую: {coords}")
        continue
    
    # Поиск через нормализацию
    if city in UA_CITY_NORMALIZE:
        normalized = UA_CITY_NORMALIZE[city]
        print(f"  🔄 Нормализация: {city} -> {normalized}")
        if normalized in CITY_COORDS:
            coords = CITY_COORDS[normalized]
            print(f"  ✅ Найден после нормализации: {coords}")
            continue
    
    # Поиск через ensure_city_coords
    coords = ensure_city_coords(city)
    if coords:
        print(f"  ✅ Найден через ensure_city_coords: {coords}")
    else:
        print(f"  ❌ НЕ НАЙДЕН нигде!")
        
        # Попробуем найти похожие
        print(f"  🔍 Ищем похожие названия...")
        similar = [k for k in CITY_COORDS.keys() if city[:4] in k or k[:4] in city]
        if similar:
            print(f"    Похожие: {similar[:5]}")
        else:
            print(f"    Похожих не найдено")

print("\n" + "="*50)
print("=== ПРОВЕРКА ПАТТЕРНОВ ===")

test_segments = [
    "2х БпЛА курсом на Соснівку",
    "2х БпЛА повз Дубляни курсом на Львів", 
    "БпЛА курсом на Буськ"
]

import re

for segment in test_segments:
    print(f"\n📝 Сегмент: '{segment}'")
    
    # Паттерн 1: "БпЛА курсом на [city]"
    pattern1 = r'бпла\s+курсом?\s+на\s+(?:н\.п\.?\s*)?([а-яіїєґ\'\-\s]+?)(?:\s|$)'
    match1 = re.search(pattern1, segment.lower())
    if match1:
        city = match1.group(1).strip()
        print(f"  ✅ Паттерн 1 нашел: '{city}'")
    else:
        print(f"  ❌ Паттерн 1 не сработал")
    
    # Паттерн 2: "[N]х БпЛА [location]"
    pattern2 = r'(\d+)?[xх]?\s*бпла\s+(.+?)(?:\.|$)'
    match2 = re.search(pattern2, segment.lower())
    if match2:
        location = match2.group(2).strip()
        print(f"  ✅ Паттерн 2 нашел: '{location}'")
    else:
        print(f"  ❌ Паттерн 2 не сработал")
