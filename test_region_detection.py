#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Test region detection specifically

test_message = """Сумщина:
БпЛА курсом на Липову Долину 

Чернігівщина:
2х БпЛА курсом на Сосницю

Харківщина:
БпЛА курсом на Балаклію

Полтавщина:
БпЛА курсом на Великі Сорочинці 

Дніпропетровщина:
БпЛА курсом на Софіївку

Донеччина:
БпЛА курсом на Білозерське"""

print("=== ДЕТАЛЬНАЯ ПРОВЕРКА ОБНАРУЖЕНИЯ РЕГИОНОВ ===")

text_lines = test_message.split('\n')
print(f"Всего строк: {len(text_lines)}")
print()

print("Проверяем каждую строку:")
region_count = 0
for i, line in enumerate(text_lines, 1):
    line_stripped = line.strip()
    line_lower = line.lower().strip()
    
    # Проверяем все условия отдельно
    condition1 = any(region in line_lower for region in ['щина:', 'ччина:', 'щина]', 'ччина]', 'область:', 'край:'])
    condition2 = ('щина' in line_lower or 'ччина' in line_lower) and line_lower.endswith(':')
    
    is_region = condition1 or condition2
    
    if line_stripped:  # Показываем только непустые строки
        print(f"  {i:2d}. '{line_stripped}'")
        print(f"      lower: '{line_lower}'")
        print(f"      contains ['щина:', 'щина]', 'область:', 'край:']: {condition1}")
        print(f"      ends with ':' and contains 'щина': {condition2}")
        print(f"      IS REGION: {is_region}")
        if is_region:
            region_count += 1
        print()

print(f"ИТОГО НАЙДЕНО РЕГИОНОВ: {region_count}")
