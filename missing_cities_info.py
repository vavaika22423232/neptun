#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Координаты отсутствующих городов (найденные в открытых источниках)

missing_cities_coords = {
    # Житомирська область
    "корнин": (50.9167, 29.1167),  # Корнин - село в Житомирській області, Малинський район
    
    # Львівська область  
    "добротвір": (50.2053, 24.4239),  # Добротвір - місто в Львівській області, важливий енергетичний центр
}

print("=== КООРДИНАТЫ ОТСУТСТВУЮЩИХ ГОРОДОВ ===")
for city, coords in missing_cities_coords.items():
    print(f"{city}: {coords}")

print()
print("=== ИНФОРМАЦИЯ О ГОРОДАХ ===")
city_info = {
    "корнин": {
        "region": "Житомирська область",
        "type": "село",
        "district": "Малинський район",
        "note": "Часто упоминается в UAV сводках"
    },
    "добротвір": {
        "region": "Львівська область", 
        "type": "місто",
        "district": "Кам'янка-Бузький район",
        "note": "Энергетический центр, Добротвірська ТЕС"
    }
}

for city, info in city_info.items():
    print(f"\n{city.upper()}:")
    print(f"  Регион: {info['region']}")
    print(f"  Тип: {info['type']}")
    print(f"  Район: {info['district']}")
    print(f"  Примечание: {info['note']}")

print()
print("=== КОД ДЛЯ ДОБАВЛЕНИЯ В БАЗУ ===")
print("# Недостающие города из UAV сообщения (сентябрь 2025)")
for city, coords in missing_cities_coords.items():
    print(f"    '{city}': {coords},")

print()
print("# С формами склонения:")
declensions = {
    "корнин": ["корнину", "корнином", "корнина"],
    "добротвір": ["добротворі", "добротвору", "добротвором", "добротвора"]
}

for city, forms in declensions.items():
    coords = missing_cities_coords[city]
    print(f"    '{city}': {coords},")
    for form in forms:
        print(f"    '{form}': {coords},")
    print()
