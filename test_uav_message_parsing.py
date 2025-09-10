#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

# Импортируем функции из app.py
from app import clean_text, ensure_city_coords, region_enhanced_coords, classify, UA_CITY_NORMALIZE
import re

# Тестовое сообщение UAV
test_message = """Житомирщина:
БпЛА курсом на Ружин
БпЛА курсом на Бердичів
БпЛА курсом на Чоповичі
БпЛА курсом на Головине
БпЛА курсом на Малин
2х БпЛА курсом на Олевськ

Рівненщина:
БпЛА курсом на Рівне
2х БпЛА курсом на Березне 
БпЛА курсом на Костопіль 
БпЛА курсом на Зарічне

Волинь:
БпЛА курсом на Сенкевичівку
БпЛА курсом на Луцьк
БпЛА курсом на Володимир 
БпЛА курсом на Голоби
2х БпЛА курсом на Камінь-Каширський

✙ Напрямок ракет ✙
✙Підтримати канал✙"""

def test_multi_regional_uav(text):
    """Тестирование алгоритма multi-regional UAV парсинга"""
    threats = []
    text_lines = text.split('\n')
    
    # Проверяем, что это выглядит как multi-regional UAV сообщение
    region_count = 0
    uav_count = 0
    for line in text_lines:
        line_lower = line.lower().strip()
        if not line_lower:
            continue
            
        # Считаем регионы
        if any(region in line_lower for region in ['щина:', 'область:', 'край:']):
            region_count += 1
        
        # Считаем упоминания UAV
        if 'бпла' in line_lower and ('курс' in line_lower or 'на ' in line_lower):
            uav_count += 1
    
    print(f"Регионов: {region_count}, UAV упоминаний: {uav_count}")
    
    # Если у нас несколько регионов и несколько UAV, обрабатываем каждую строку
    if region_count >= 2 and uav_count >= 3:
        print("✅ Сообщение подходит под формат multi-regional UAV")
        
        for line_num, line in enumerate(text_lines, 1):
            line_stripped = line.strip()
            if not line_stripped or ':' in line_stripped[:20]:  # Пропускаем заголовки регионов
                continue
            
            line_lower = line_stripped.lower()
            
            # Ищем паттерны UAV курса
            if 'бпла' in line_lower and ('курс' in line_lower or ' на ' in line_lower):
                patterns = [
                    r'(\d+)?[xх]?\s*бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|$|[,\.\!\?])',
                    r'бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|$|[,\.\!\?])',
                    r'(\d+)?[xх]?\s*бпла\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|$|[,\.\!\?])'
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, line_stripped, re.IGNORECASE)
                    for match in matches:
                        if len(match.groups()) == 2:
                            count_str, city_raw = match.groups()
                        else:
                            count_str = None
                            city_raw = match.group(1)
                        
                        if not city_raw:
                            continue
                            
                        # Очищаем и нормализуем название города
                        city_clean = city_raw.strip()
                        city_norm = clean_text(city_clean).lower()
                        
                        # Применяем правила нормализации
                        if city_norm in UA_CITY_NORMALIZE:
                            city_norm = UA_CITY_NORMALIZE[city_norm]
                        
                        # Пытаемся получить координаты
                        coords = region_enhanced_coords(city_norm)
                        if not coords:
                            coords = ensure_city_coords(city_norm)
                        
                        if coords:
                            lat, lng = coords[:2]  # Возможно, функция возвращает больше 2 элементов
                            
                            # Извлекаем количество если есть
                            uav_count_num = 1
                            if count_str and count_str.isdigit():
                                uav_count_num = int(count_str)
                            
                            threats.append({
                                'line': line_num,
                                'city': city_clean.title(),
                                'lat': lat,
                                'lng': lng,
                                'count': uav_count_num,
                                'original_line': line_stripped
                            })
                            
                            print(f"  ✅ Строка {line_num}: {city_clean} ({uav_count_num}x) -> ({lat}, {lng})")
                        else:
                            print(f"  ❌ Строка {line_num}: Координаты не найдены для {city_clean}")
    else:
        print("❌ Сообщение НЕ подходит под формат multi-regional UAV")
    
    return threats

print("=== ТЕСТИРОВАНИЕ ПАРСИНГА UAV СООБЩЕНИЯ ===")
print("Тестируем алгоритм парсинга multi-regional UAV")
print()

# Тестируем парсинг
result = test_multi_regional_uav(test_message)

print()
print("=== РЕЗУЛЬТАТ ПАРСИНГА ===")
print(f"Найдено угроз: {len(result)}")

if result:
    print()
    print("ДОБАВЛЕННЫЕ ГОРОДА В РЕЗУЛЬТАТЕ:")
    added_cities = ['зарічне', 'сенкевичівка', 'голоби']
    found_added = []
    
    for threat in result:
        city_name = threat['city']
        if city_name.lower() in added_cities:
            found_added.append(city_name.lower())
            print(f"  ✅ {city_name}: ({threat['lat']}, {threat['lng']})")
    
    print()
    if len(found_added) == 3:
        print("🎉 ВСЕ 3 ДОБАВЛЕННЫХ ГОРОДА УСПЕШНО ОБНАРУЖЕНЫ В ПАРСИНГЕ!")
    else:
        missing = set(added_cities) - set(found_added)
        print(f"❌ Отсутствуют в результате: {missing}")
else:
    print("❌ Парсинг не вернул результат")
