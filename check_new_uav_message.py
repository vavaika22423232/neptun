#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import CITY_COORDS

# Города из UAV сообщения по регионам
uav_message_cities = [
    # Житомирщина
    ("житомир", "Житомирщина"),
    ("корнин", "Житомирщина"), 
    ("коростишів", "Житомирщина"),
    ("малин", "Житомирщина"),
    ("коростень", "Житомирщина"),
    ("звягель", "Житомирщина"),
    
    # Рівненщина
    ("клевань", "Рівненщина"),
    ("рівне", "Рівненщина"),
    ("костопіль", "Рівненщина"),
    ("зарічне", "Рівненщина"),
    
    # Хмельниччина
    ("нетішин", "Хмельниччина"),
    
    # Волинь
    ("голоби", "Волинь"),
    
    # Львівщина
    ("добротвір", "Львівщина"),
    ("броди", "Львівщина"),
]

print("=== ПРОВЕРКА ГОРОДОВ ИЗ UAV СООБЩЕНИЯ ===")
print(f"Всего городов для проверки: {len(uav_message_cities)}")
print()

all_found = True
missing_cities = []
found_cities = []

# Проверяем каждый регион отдельно
regions = {}
for city, region in uav_message_cities:
    if region not in regions:
        regions[region] = []
    regions[region].append(city)

for region, cities in regions.items():
    print(f"📍 {region.upper()}")
    region_found = 0
    
    for city in cities:
        normalized_city = city.lower().strip()
        if normalized_city in CITY_COORDS:
            coords = CITY_COORDS[normalized_city]
            found_cities.append((city, region, coords))
            print(f"  ✅ {city:20}: {coords}")
            region_found += 1
        else:
            missing_cities.append((city, region))
            print(f"  ❌ {city:20}: НЕ НАЙДЕН")
            all_found = False
    
    print(f"     Найдено в регионе: {region_found}/{len(cities)}")
    print()

print("=== ОБЩИЕ РЕЗУЛЬТАТЫ ===")
print(f"Найдено: {len(found_cities)}")
print(f"Отсутствует: {len(missing_cities)}")

if missing_cities:
    print()
    print("ОТСУТСТВУЮЩИЕ ГОРОДА:")
    for city, region in missing_cities:
        print(f"  ❌ {city} ({region})")
        
    print()
    print("=== ПОИСК ПОХОЖИХ НАЗВАНИЙ ===")
    for city, region in missing_cities:
        print(f"\nПоиск для '{city}' ({region}):")
        similar = []
        
        # Поиск точных и частичных совпадений
        for db_city in CITY_COORDS.keys():
            if city.lower() in db_city.lower() or db_city.lower() in city.lower():
                similar.append((db_city, CITY_COORDS[db_city]))
        
        if similar:
            for similar_city, coords in similar[:5]:  # Показываем первые 5 совпадений
                print(f"  → {similar_city}: {coords}")
        else:
            print(f"  Точных совпадений не найдено")
            
else:
    print("🎉 ВСЕ ГОРОДА НАЙДЕНЫ В БАЗЕ ДАННЫХ!")

print()
print("=== ПОКРЫТИЕ ПО РЕГИОНАМ ===")
for region, cities in regions.items():
    found_in_region = len([c for c in cities if c.lower() in CITY_COORDS])
    percentage = (found_in_region / len(cities)) * 100
    print(f"{region:15}: {found_in_region}/{len(cities)} ({percentage:.1f}%)")

if missing_cities:
    print()
    print("=== РЕКОМЕНДАЦИИ ===")
    print("Необходимо добавить координаты для отсутствующих городов")
    print("для обеспечения точной геолокации UAV угроз.")
    
print()
print("=== НОВЫЕ ГОРОДА В ЭТОМ СООБЩЕНИИ ===")
# Проверяем города, которых не было в предыдущих проверках
previous_cities = [
    'ружин', 'бердичів', 'чоповичі', 'головине', 'олевськ',  # из предыдущего сообщения
    'березне', 'сенкевичівка', 'луцьк', 'володимир', 'камінь-каширський'
]

new_cities = []
for city, region in uav_message_cities:
    if city not in previous_cities:
        new_cities.append((city, region))

if new_cities:
    print("Новые города в этом сообщении:")
    for city, region in new_cities:
        status = "✅" if city.lower() in CITY_COORDS else "❌"
        print(f"  {status} {city} ({region})")
else:
    print("Все города уже проверялись ранее")
