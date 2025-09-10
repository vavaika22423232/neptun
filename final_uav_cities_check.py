#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import CITY_COORDS

# Города из UAV сообщения
uav_cities = [
    # Житомирщина
    ("ружин", "Житомирщина"),
    ("бердичів", "Житомирщина"), 
    ("чоповичі", "Житомирщина"),
    ("головине", "Житомирщина"),
    ("малин", "Житомирщина"),
    ("олевськ", "Житомирщина"),
    
    # Рівненщина
    ("рівне", "Рівненщина"),
    ("березне", "Рівненщина"),
    ("костопіль", "Рівненщина"),
    ("зарічне", "Рівненщина"),  # ДОБАВЛЕН
    
    # Волинь
    ("сенкевичівка", "Волинь"),  # ДОБАВЛЕН
    ("луцьк", "Волинь"),
    ("володимир", "Волинь"),
    ("голоби", "Волинь"),        # ДОБАВЛЕН
    ("камінь-каширський", "Волинь")
]

print("=== ФИНАЛЬНАЯ ПРОВЕРКА КООРДИНАТ UAV ГОРОДОВ ===")
print(f"Всего городов: {len(uav_cities)}")
print()

all_found = True
newly_added = []

for city, region in uav_cities:
    normalized_city = city.lower().strip()
    if normalized_city in CITY_COORDS:
        coords = CITY_COORDS[normalized_city]
        status = "✅"
        
        # Проверяем, добавлен ли город недавно
        if city in ["зарічне", "сенкевичівка", "голоби"]:
            newly_added.append((city, coords))
            status = "🆕"
        
        print(f"{status} {city:20} ({region:15}): {coords}")
    else:
        print(f"❌ {city:20} ({region:15}): НЕ НАЙДЕН")
        all_found = False

print()
print("=== РЕЗУЛЬТАТЫ ===")
if all_found:
    print("🎉 ВСЕ ГОРОДА НАЙДЕНЫ В БАЗЕ ДАННЫХ!")
    print(f"Добавлено новых городов: {len(newly_added)}")
    
    if newly_added:
        print()
        print("НЕДАВНО ДОБАВЛЕННЫЕ ГОРОДА:")
        for city, coords in newly_added:
            print(f"  🆕 {city}: {coords}")
        
        print()
        print("Эти города теперь будут правильно обрабатываться в UAV сообщениях!")
        print("Система создаст отдельные маркеры для каждого города вместо региональных fallback.")
        
else:
    print("❌ НЕКОТОРЫЕ ГОРОДА ВСЕ ЕЩЕ ОТСУТСТВУЮТ")

print()
print("=== АНАЛИЗ ПОКРЫТИЯ ПО РЕГИОНАМ ===")
regions = {}
for city, region in uav_cities:
    if region not in regions:
        regions[region] = {'total': 0, 'found': 0}
    regions[region]['total'] += 1
    if city.lower() in CITY_COORDS:
        regions[region]['found'] += 1

for region, stats in regions.items():
    percentage = (stats['found'] / stats['total']) * 100
    print(f"{region:15}: {stats['found']}/{stats['total']} ({percentage:.1f}%)")
