#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import CITY_COORDS

# Основные города Винницкой области для проверки
vinnytsia_cities = [
    # Обласний центр
    'вінниця',
    
    # Міста обласного значення
    'козятин',
    'хмільник', 
    'ладижин',
    'могилів-подільський',
    
    # Важливі райцентри
    'бар',
    'гайсин',
    'жмеринка',
    'іллінці',
    'калинівка',
    'крижопіль',
    'липовець',
    'літин',
    'муровані курилівці',
    'немирів',
    'оратів',
    'піщанка',
    'погребище',
    'теплик',
    'томашпіль',
    'тростянець',
    'тульчин',
    'тиврів',
    'чечельник',
    'шаргород',
    'ямпіль',
    
    # Селища міського типу
    'браїлів',
    'вапнярка',
    'гнівань',
    'дашів',
    'деражня',
    'джулинка',
    'мурафа',
    'охматів',
    'печера',
    'станіславчик',
    'стрижавка',
    'чорний острів',
]

print("=== ПРОВЕРКА ГОРОДОВ ВИННИЦКОЙ ОБЛАСТИ ===")
print(f"Всего городов для проверки: {len(vinnytsia_cities)}")
print()

found_cities = []
missing_cities = []

for city in vinnytsia_cities:
    normalized_city = city.lower().strip()
    if normalized_city in CITY_COORDS:
        coords = CITY_COORDS[normalized_city]
        found_cities.append((city, coords))
        print(f"✅ {city:25}: {coords}")
    else:
        missing_cities.append(city)
        print(f"❌ {city:25}: НЕ НАЙДЕН")

print()
print("=== РЕЗУЛЬТАТЫ ===")
print(f"Найдено: {len(found_cities)}")
print(f"Отсутствует: {len(missing_cities)}")

if missing_cities:
    print()
    print("ОТСУТСТВУЮЩИЕ ГОРОДА:")
    for city in missing_cities:
        print(f"  - {city}")
else:
    print("🎉 ВСЕ ГОРОДА ВИННИЦКОЙ ОБЛАСТИ НАЙДЕНЫ В БАЗЕ ДАННЫХ!")

print()
print("=== ПРОВЕРКА ФОРМ СКЛОНЕНИЯ ===")
# Проверим несколько форм склонения
declension_test = [
    ('вінниці', 'вінниця'),
    ('козятині', 'козятин'),
    ('гайсині', 'гайсин'),
    ('жмеринці', 'жмеринка'),
    ('тульчині', 'тульчин'),
    ('шаргороді', 'шаргород'),
]

for declined_form, base_form in declension_test:
    if declined_form in CITY_COORDS:
        coords = CITY_COORDS[declined_form]
        print(f"✅ {declined_form} (от {base_form}): {coords}")
    else:
        print(f"❌ {declined_form} (от {base_form}): не найдено")

print()
print("=== СТАТИСТИКА ===")
total_vinnytsia = len([k for k in CITY_COORDS.keys() if any(city in k for city in ['вінниц', 'козятин', 'хмільник', 'ладижин', 'гайсин', 'жмеринк', 'тульчин', 'шаргород', 'ямпіль', 'бар', 'теплик'])])
print(f"Всего записей связанных с Винницкой областью в базе: {total_vinnytsia}")
