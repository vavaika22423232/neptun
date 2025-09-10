#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Поиск координат для отсутствующих городов
missing_cities_info = {
    "зарічне": {
        "region": "Рівненська область",
        "description": "селище міського типу в Рівненській області"
    },
    "сенкевичівка": {
        "region": "Волинська область", 
        "description": "село в Волинській області"
    },
    "голоби": {
        "region": "Волинська область",
        "description": "село в Волинській області"
    }
}

print("=== ОТСУТСТВУЮЩИЕ ГОРОДА ===")
for city, info in missing_cities_info.items():
    print(f"{city}: {info['description']}")
    print(f"  Регион: {info['region']}")
    print()

# Проверим, есть ли эти города в других регионах
import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import CITY_COORDS

print("=== ПОИСК ПОХОЖИХ НАЗВАНИЙ В БАЗЕ ===")
for city in missing_cities_info.keys():
    print(f"\nПоиск для '{city}':")
    found_similar = []
    
    for db_city in CITY_COORDS.keys():
        if city in db_city or db_city in city:
            found_similar.append((db_city, CITY_COORDS[db_city]))
    
    if found_similar:
        for similar_city, coords in found_similar:
            print(f"  - {similar_city}: {coords}")
    else:
        print(f"  Похожих названий не найдено")

print("\n=== НУЖНО ДОБАВИТЬ КООРДИНАТЫ ===")
print("Для точной работы системы нужно добавить координаты этих 3 городов.")
