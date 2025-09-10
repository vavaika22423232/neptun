#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест нормализации винительного падежа для Соснівку
"""

test_city = "соснівку"

print(f"Тестируем: '{test_city}'")

# Проверяем правила
if test_city.endswith('ку') and len(test_city) > 4:
    normalized = test_city[:-2] + 'ка'
    print(f"  Нормализация 'ку' -> 'ка': {test_city} -> {normalized}")
elif test_city.endswith('у') and len(test_city) > 3:
    normalized = test_city[:-1] + 'а'
    print(f"  Нормализация 'у' -> 'а': {test_city} -> {normalized}")
else:
    print(f"  Правила не применились")

# Проверяем длину
print(f"  Длина: {len(test_city)}")
print(f"  Заканчивается на 'ку': {test_city.endswith('ку')}")
print(f"  Длина > 4: {len(test_city) > 4}")

# Ручная проверка
if test_city == 'соснівку':
    print("  ✅ Правило должно сработать: соснівку -> соснівка")
