#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

# Тестовое сообщение из вашего примера
test_message = """Загроза застосування БПЛА. Перейдіть в укриття! | 🛸 Львів (Львівська обл.)
Загроза застосування БПЛА. Перейдіть в укриття! | 4х БпЛА курсом на Добротвір (мультирегіональне) | 🛸 Буськ (Львівська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""

print("=== АНАЛИЗ ПРОБЛЕМНОГО СООБЩЕНИЯ ===")
print("Текст сообщения:")
print(test_message)
print()

# Анализируем структуру сообщения
lines = test_message.split('\n')
print("=== СТРУКТУРА СООБЩЕНИЯ ПО СТРОКАМ ===")
for i, line in enumerate(lines, 1):
    print(f"Строка {i}: {line}")
    
    # Анализируем каждую строку
    line_lower = line.lower()
    if 'бпла' in line_lower or 'бплa' in line_lower:
        print(f"  → Содержит упоминание БПЛА")
    if 'курс' in line_lower:
        print(f"  → Содержит слово 'курс'")
    if 'львів' in line_lower:
        print(f"  → Содержит упоминание Львова")
    if 'добротвір' in line_lower:
        print(f"  → Содержит упоминание Добротвора")
    if 'мультирегіональне' in line_lower:
        print(f"  → Помечено как мультирегиональное")
    print()

print("=== АНАЛИЗ ПАТТЕРНОВ ПАРСИНГА ===")

# Проверим паттерны для multi-regional UAV
import re

# Паттерны из кода
patterns = [
    r'(\d+)?[xх]?\s*бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|$|[,\.\!\?])',
    r'бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|$|[,\.\!\?])',
    r'(\d+)?[xх]?\s*бпла\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|$|[,\.\!\?])'
]

print("Поиск совпадений по паттернам:")
for i, pattern in enumerate(patterns, 1):
    print(f"\nПаттерн {i}: {pattern}")
    
    matches = re.finditer(pattern, test_message, re.IGNORECASE)
    found_matches = list(matches)
    
    if found_matches:
        for match in found_matches:
            if len(match.groups()) == 2:
                count_str, city_raw = match.groups()
            else:
                count_str = None
                city_raw = match.group(1)
            
            print(f"  ✅ Найдено: количество='{count_str}', город='{city_raw}'")
    else:
        print(f"  ❌ Совпадений не найдено")

print()
print("=== ПРОВЕРКА УСЛОВИЙ MULTI-REGIONAL ===")

# Проверка условий для multi-regional парсинга
region_count = 0
uav_count = 0

for line in lines:
    line_lower = line.lower().strip()
    if not line_lower:
        continue
        
    # Считаем регионы
    if any(region in line_lower for region in ['щина:', 'область:', 'край:', 'обл.)']):
        region_count += 1
        print(f"Найден регион: {line}")
    
    # Считаем UAV
    if 'бпла' in line_lower and ('курс' in line_lower or 'на ' in line_lower):
        uav_count += 1
        print(f"Найден UAV: {line}")

print(f"\nРегионов: {region_count}")
print(f"UAV упоминаний: {uav_count}")

if region_count >= 2 and uav_count >= 3:
    print("✅ Соответствует критериям multi-regional")
else:
    print("❌ НЕ соответствует критериям multi-regional")
    print("Причина: нужно минимум 2 региона и 3 UAV упоминания")

print()
print("=== ДИАГНОЗ ПРОБЛЕМЫ ===")
print("Возможные причины, почему Добротвір не создает отдельную метку:")
print("1. Сообщение не соответствует критериям multi-regional парсинга")
print("2. Паттерн '4х БпЛА курсом на Добротвір' не распознается из-за контекста")
print("3. Система обрабатывает это как обычное региональное сообщение")
print("4. Приоритет отдается геолокации Львів из структуры сообщения")
