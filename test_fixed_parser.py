#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

# Тестовое сообщение из вашего примера
test_message = """Загроза застосування БПЛА. Перейдіть в укриття! | 🛸 Львів (Львівська обл.)
Загроза застосування БПЛА. Перейдіть в укриття! | 4х БпЛА курсом на Добротвір (мультирегіональне) | 🛸 Буськ (Львівська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""

print("=== ТЕСТИРОВАНИЕ ИСПРАВЛЕННОГО ПАРСЕРА ===")
print("Сообщение:")
print(test_message)
print()

# Импортируем необходимые функции (не основную функцию, а вспомогательные)
from app import CITY_COORDS, clean_text, ensure_city_coords, region_enhanced_coords, classify, UA_CITY_NORMALIZE
import re

# Симулируем обработку single UAV courses
def test_single_uav_courses(text):
    """Тестируем обработку одиночных UAV курсов"""
    threats = []
    
    # Look for UAV course patterns in the entire message
    patterns = [
        r'(\d+)?[xх]?\s*бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|[,\.\!\?\|\(])',
        r'бпла\s+курсом?\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|[,\.\!\?\|\(])',
        r'(\d+)?[xх]?\s*бпла\s+на\s+([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)(?:\s|[,\.\!\?\|\(])'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) == 2:
                count_str, city_raw = match.groups()
            else:
                count_str = None
                city_raw = match.group(1)
            
            if not city_raw:
                continue
                
            # Clean and normalize city name
            city_clean = city_raw.strip()
            city_norm = clean_text(city_clean).lower()
            
            # Apply normalization rules
            if city_norm in UA_CITY_NORMALIZE:
                city_norm = UA_CITY_NORMALIZE[city_norm]
            
            # Try to get coordinates
            coords = region_enhanced_coords(city_norm)
            if not coords:
                coords = ensure_city_coords(city_norm)
            
            if coords:
                lat, lng = coords[:2]
                
                # Extract count if present
                uav_count_num = 1
                if count_str and count_str.isdigit():
                    uav_count_num = int(count_str)
                
                threat = {
                    'place': city_clean.title(),
                    'lat': lat,
                    'lng': lng,
                    'text': f"БпЛА курсом на {city_clean} ({uav_count_num}x)",
                    'count': uav_count_num
                }
                threats.append(threat)
                
                print(f"✅ Найден UAV курс: {city_clean} ({uav_count_num}x) -> ({lat}, {lng})")
            else:
                print(f"❌ UAV курс: Координаты не найдены для {city_clean}")
    
    return threats

# Тестируем
print("=== РЕЗУЛЬТАТ ОБРАБОТКИ SINGLE UAV COURSES ===")
uav_threats = test_single_uav_courses(test_message)

if uav_threats:
    print(f"\nНайдено UAV угроз: {len(uav_threats)}")
    for threat in uav_threats:
        print(f"  • {threat['place']}: ({threat['lat']}, {threat['lng']}) - {threat['count']}x БпЛА")
    
    print("\n=== ПРОВЕРКА ДОБРОТВОРА ===")
    dobrotvor_found = any('добротвір' in threat['place'].lower() for threat in uav_threats)
    if dobrotvor_found:
        print("✅ Добротвір найден и будет создана отдельная метка!")
    else:
        print("❌ Добротвір не найден")
        
    print("\n=== ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ===")
    print("Система должна создать:")
    print("1. Метку для Львова (из структуры сообщения)")
    print("2. Метку для Буська (из структуры сообщения)")  
    print("3. Метку для Добротвора (из UAV курса)")
    print("Итого: 3 метки вместо 1")
    
else:
    print("❌ UAV угрозы не найдены")
    print("Проверьте паттерны и координаты Добротвора")
