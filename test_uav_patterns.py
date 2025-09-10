#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import CITY_COORDS
import re

# Тестовое сообщение из вашего примера
test_message = """Загроза застосування БПЛА. Перейдіть в укриття! | 🛸 Львів (Львівська обл.)
Загроза застосування БПЛА. Перейдіть в укриття! | 4х БпЛА курсом на Добротвір (мультирегіональне) | 🛸 Буськ (Львівська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""

print("=== ТЕСТИРОВАНИЕ ПАТТЕРНОВ UAV КУРСОВ ===")
print("Сообщение:")
print(test_message)
print()

# Тестируем паттерны UAV курсов
patterns = [
    r'(\d+)?[xх]?\s*бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|[,\.\!\?\|\(])',
    r'бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|[,\.\!\?\|\(])',
    r'(\d+)?[xх]?\s*бпла\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|[,\.\!\?\|\(])'
]

print("=== РЕЗУЛЬТАТ ПОИСКА ПАТТЕРНОВ ===")
found_courses = []

for i, pattern in enumerate(patterns, 1):
    print(f"\nПаттерн {i}: {pattern}")
    
    matches = re.finditer(pattern, test_message, re.IGNORECASE)
    matches_list = list(matches)
    
    if matches_list:
        for match in matches_list:
            if len(match.groups()) == 2:
                count_str, city_raw = match.groups()
            else:
                count_str = None
                city_raw = match.group(1)
            
            # Очищаем название города
            city_clean = city_raw.strip()
            city_norm = city_clean.lower()
            
            # Проверяем координаты
            if city_norm in CITY_COORDS:
                coords = CITY_COORDS[city_norm]
                count = int(count_str) if count_str and count_str.isdigit() else 1
                
                found_courses.append({
                    'city': city_clean,
                    'coords': coords,
                    'count': count,
                    'pattern': i
                })
                
                print(f"  ✅ Найдено: {city_clean} ({count}x) -> {coords}")
            else:
                print(f"  ❌ Найдено '{city_clean}', но координаты отсутствуют")
    else:
        print(f"  ❌ Совпадений не найдено")

print(f"\n=== ИТОГО НАЙДЕНО UAV КУРСОВ: {len(found_courses)} ===")

if found_courses:
    print("\nВсе найденные UAV курсы:")
    for course in found_courses:
        print(f"  • {course['city']}: {course['coords']} ({course['count']}x БпЛА)")
    
    # Проверяем Добротвір
    dobrotvor_courses = [c for c in found_courses if 'добротвір' in c['city'].lower()]
    
    print(f"\n=== ПРОВЕРКА ДОБРОТВОРА ===")
    if dobrotvor_courses:
        for course in dobrotvor_courses:
            print(f"✅ Добротвір найден: {course['coords']} ({course['count']}x БпЛА)")
        print("\n🎉 ПРОБЛЕМА РЕШЕНА!")
        print("Система теперь должна создать отдельную метку для Добротвора")
        print("в дополнение к меткам Львова и Буська из структуры сообщения")
    else:
        print("❌ Добротвір не найден в UAV курсах")
        
else:
    print("❌ UAV курсы не найдены")

print("\n=== ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ===")
print("После исправления система должна создавать:")
print("1. Основные метки из структуры сообщения (Львов, Буськ)")
print("2. Дополнительные метки UAV курсов (Добротвір)")
print("3. Всего меток: больше 1 (вместо только Львова)")

# Проверяем, что Добротвір есть в базе
print(f"\n=== ПРОВЕРКА БАЗЫ ДАННЫХ ===")
if 'добротвір' in CITY_COORDS:
    coords = CITY_COORDS['добротвір']
    print(f"✅ Добротвір в базе данных: {coords}")
else:
    print("❌ Добротвір отсутствует в базе данных")
