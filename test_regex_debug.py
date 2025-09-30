#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Детальный тест для проблемы с БпЛА на юге Чернигивщины
"""

import re

def test_regex_patterns():
    """Тестирует регулярные выражения"""
    
    test_message = "БпЛА на півдні Чернігівщини, рухаються на південь (Київщина)"
    line_lower = test_message.lower()
    
    print(f"Тестовое сообщение: {test_message}")
    print(f"Lowercase: {line_lower}")
    print("="*50)
    
    # Тестируем новый паттерн для движения
    directional_movement = re.search(r'на\s+([\w\-\s/]+?)\s+([а-яіїєґ]+щини|[а-яіїєґ]+щину|дніпропетровщини|одещини|чернігівщини).*рухаються.*\(([^)]+)\)', line_lower)
    
    if directional_movement:
        print("✅ Новый паттерн для движения сработал!")
        print(f"  Направление: '{directional_movement.group(1)}'")
        print(f"  Регион: '{directional_movement.group(2)}'")
        print(f"  Цель движения: '{directional_movement.group(3)}'")
    else:
        print("❌ Новый паттерн для движения НЕ сработал")
    
    print()
    
    # Тестируем старый паттерн
    region_match = re.search(r'на\s+([\w\-\s/]+?)\s+([а-яіїєґ]+щини|[а-яіїєґ]+щину|дніпропетровщини|одещини|чернігівщини)', line_lower)
    
    if region_match:
        print("✅ Старый региональный паттерн сработал!")
        print(f"  Направление: '{region_match.group(1)}'")
        print(f"  Регион: '{region_match.group(2)}'")
    else:
        print("❌ Старый региональный паттерн НЕ сработал")
    
    print()
    
    # Тестируем паттерн bracket city
    bracket_city = re.search(r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{3,})\s*\(([^)]+)\)', test_message)
    
    if bracket_city:
        print("⚠️  Bracket city паттерн сработал!")
        print(f"  Город: '{bracket_city.group(1)}'")
        print(f"  В скобках: '{bracket_city.group(2)}'")
        print("  Это может перехватывать наше сообщение!")
    else:
        print("✅ Bracket city паттерн НЕ сработал")
    
    print()
    
    # Проверим условие для многострочного анализа
    multi_line_conditions = [
        'шахед' in line_lower,
        'камикадзе' in line_lower,
        'дрон' in line_lower,
        'бпла' in line_lower,
        'ракет' in line_lower,
        'кр х' in line_lower,
        any(region in line_lower for region in ['щина)', 'щини', 'щину', 'одещина', 'чернігівщина', 'дніпропетровщина', 'харківщина', 'київщина'])
    ]
    
    print("При проверке условий для многострочного анализа:")
    for i, condition in enumerate(multi_line_conditions, 1):
        print(f"  Условие {i}: {condition}")
    
    if any(multi_line_conditions):
        print("✅ Сообщение должно попадать в многострочный анализ")
    else:
        print("❌ Сообщение НЕ попадает в многострочный анализ")

if __name__ == "__main__":
    test_regex_patterns()
