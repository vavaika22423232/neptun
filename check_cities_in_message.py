#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import CITY_COORDS

# Города из сообщения
message_cities = [
    # Житомирщина
    "ружин",
    "бердичів", 
    "чоповичі",
    "головине",
    "малин",
    "олевськ",
    
    # Рівненщина
    "рівне",
    "березне",
    "костопіль",
    "зарічне",
    
    # Волинь
    "сенкевичівка", 
    "луцьк",
    "володимир",
    "голоби",
    "камінь-каширський"
]

print("=== Проверка городов из сообщения ===")
print(f"Всего городов для проверки: {len(message_cities)}")
print()

missing_cities = []
found_cities = []

for city in message_cities:
    normalized_city = city.lower().strip()
    if normalized_city in CITY_COORDS:
        coords = CITY_COORDS[normalized_city]
        found_cities.append((city, coords))
        print(f"✅ {city}: {coords}")
    else:
        missing_cities.append(city)
        print(f"❌ {city}: НЕ НАЙДЕН")

print()
print("=== РЕЗУЛЬТАТЫ ===")
print(f"Найдено: {len(found_cities)}")
print(f"Отсутствует: {len(missing_cities)}")

if missing_cities:
    print()
    print("ОТСУТСТВУЮЩИЕ ГОРОДА:")
    for city in missing_cities:
        print(f"  - {city}")
        
    print()
    print("=== Поиск альтернативных названий ===")
    for city in missing_cities:
        # Поиск похожих названий в базе
        similar = []
        for db_city in CITY_COORDS.keys():
            if city.lower() in db_city.lower() or db_city.lower() in city.lower():
                similar.append(db_city)
        
        if similar:
            print(f"{city} - возможные варианты: {similar}")
        else:
            print(f"{city} - точных совпадений не найдено")

else:
    print("🎉 ВСЕ ГОРОДА НАЙДЕНЫ В БАЗЕ ДАННЫХ!")
