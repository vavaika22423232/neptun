#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

from app import CITY_COORDS

print("=== ФИНАЛЬНАЯ ПРОВЕРКА ВИННИЦКОЙ ОБЛАСТИ ===")
print()

# Группы городов Винницкой области
city_groups = {
    'Обласний центр': ['вінниця'],
    
    'Міста обласного значення': [
        'козятин', 'хмільник', 'ладижин', 'могилів-подільський'
    ],
    
    'Райцентри': [
        'бар', 'гайсин', 'жмеринка', 'іллінці', 'калинівка', 'крижопіль',
        'липовець', 'літин', 'муровані курилівці', 'немирів', 'оратів',
        'піщанка', 'погребище', 'теплик', 'томашпіль', 'тульчин', 'тиврів',
        'чечельник', 'шаргород'
    ],
    
    'Селища міського типу': [
        'браїлів', 'вапнярка', 'гнівань', 'дашів', 'деражня', 'джулинка',
        'мурафа', 'охматів', 'печера', 'станіславчик', 'стрижавка', 'чорний острів'
    ],
    
    'Спецификації (для избежания конфликтов)': [
        'тростянець вінницька', 'ямпіль вінницька'
    ]
}

total_cities = 0
total_found = 0

for group_name, cities in city_groups.items():
    print(f"📍 {group_name.upper()}")
    group_found = 0
    
    for city in cities:
        total_cities += 1
        if city in CITY_COORDS:
            coords = CITY_COORDS[city]
            print(f"  ✅ {city:25}: {coords}")
            total_found += 1
            group_found += 1
        else:
            print(f"  ❌ {city:25}: НЕ НАЙДЕН")
    
    print(f"     Найдено в группе: {group_found}/{len(cities)}")
    print()

print("=== ОБЩИЙ РЕЗУЛЬТАТ ===")
print(f"Всего проверено городов: {total_cities}")
print(f"Найдено в базе данных: {total_found}")
print(f"Процент покрытия: {(total_found/total_cities)*100:.1f}%")

if total_found == total_cities:
    print("🎉 ИДЕАЛЬНОЕ ПОКРЫТИЕ ВИННИЦКОЙ ОБЛАСТИ!")
    print()
    print("Теперь система может:")
    print("  • Точно геолоцировать все основные города области")
    print("  • Различать города с одинаковыми названиями в разных областях") 
    print("  • Обрабатывать различные формы склонения украинских названий")
    print("  • Предоставлять высокоточную географическую информацию для UAV угроз")
else:
    missing_count = total_cities - total_found
    print(f"❌ Отсутствует {missing_count} городов")

print()
print("=== ПРОВЕРКА ФОРМ СКЛОНЕНИЯ ===")
declension_samples = [
    ('вінниці', 'вінниця'), ('козятині', 'козятин'), ('гайсині', 'гайсин'),
    ('тульчині', 'тульчин'), ('шаргороді', 'шаргород'), ('ямполі вінницька', 'ямпіль вінницька')
]

for declined, base in declension_samples:
    if declined in CITY_COORDS:
        print(f"  ✅ {declined} ← {base}")
    else:
        print(f"  ❌ {declined} ← {base}")

print()
print("=== ГЕОГРАФИЯ ===")
# Анализ географического распределения
all_vinnytsia = [(city, coords) for city, coords in CITY_COORDS.items() 
                 if any(keyword in city for keyword in ['вінниц', 'козятин', 'хмільник', 'ладижин', 
                                                       'гайсин', 'жмеринк', 'тульчин', 'шаргород', 
                                                       'браїлів', 'немир', 'оратів', 'літин']) 
                 and 27.5 <= coords[1] <= 30.0 and 48.0 <= coords[0] <= 50.2]

print(f"Городов в географических границах Винницкой области: {len(all_vinnytsia)}")

if all_vinnytsia:
    lats = [coords[0] for _, coords in all_vinnytsia]
    lngs = [coords[1] for _, coords in all_vinnytsia]
    print(f"Широта: {min(lats):.3f} - {max(lats):.3f}")
    print(f"Долгота: {min(lngs):.3f} - {max(lngs):.3f}")
