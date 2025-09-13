#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест для проверки, что Чорнобаївка (Херсонська обл.) больше не отображается в Харькове
"""

import sys
import os

# Добавляем текущую папку в sys.path чтобы импортировать app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import ensure_city_coords, process_message
    
    def test_chornobaivka():
        print("=== Тест Чорнобаївка (Херсонська обл.) ===\n")
        
        # Тест координат
        print("1. Проверка координат Чорнобаївки:")
        coords = ensure_city_coords('чорнобаївка')
        if coords:
            lat, lon, is_approx = coords
            print(f"   Координаты: ({lat}, {lon})")
            print(f"   Точность: {'приблизительные' if is_approx else 'точные'}")
            
            # Проверяем, что это не Харьков
            if abs(lat - 49.9935) < 0.001 and abs(lon - 36.2304) < 0.001:
                print(f"   ❌ ОШИБКА: Отображается как Харьков!")
            else:
                print(f"   ✅ ОК: Не путается с Харьковом")
                
            # Проверяем, что это действительно Херсонская область
            if abs(lat - 46.6964) < 0.001 and abs(lon - 32.5469) < 0.001:
                print(f"   ✅ ОТЛИЧНО: Правильные координаты Чорнобаївки")
            else:
                print(f"   ⚠️ Координаты отличаются от ожидаемых (46.6964, 32.5469)")
        else:
            print(f"   ❌ Координаты не найдены")
            
        print()
        
        # Тест сообщения
        print("2. Тест обработки сообщения:")
        message = "🛸 Чорнобаївка (Херсонська обл.) Загроза застосування БПЛА. Перейдіть в укриття!"
        print(f"   Сообщение: {message}")
        
        try:
            result = process_message(message, "test_1", "2025-09-13", "test_channel")
            
            if result and len(result) > 0:
                message_data = result[0]
                place = message_data.get('place', 'не найдено')
                lat = message_data.get('lat', None)
                lng = message_data.get('lng', None)
                marker_icon = message_data.get('marker_icon', 'не найдено')
                
                print(f"   Место: {place}")
                print(f"   Координаты: ({lat}, {lng})" if lat and lng else "   Координаты: не найдены")
                print(f"   Иконка: {marker_icon}")
                
                # Проверяем результат
                if lat and lng:
                    if abs(lat - 49.9935) < 0.1 and abs(lng - 36.2304) < 0.1:
                        print(f"   ❌ ОШИБКА: Все еще отображается в районе Харькова!")
                    elif abs(lat - 46.6964) < 0.1 and abs(lng - 32.5469) < 0.1:
                        print(f"   ✅ ОТЛИЧНО: Правильное местоположение в Херсонской области!")
                    else:
                        print(f"   ⚠️ Координаты: широта {lat}, долгота {lng}")
            else:
                print(f"   ❌ Сообщение не обработано")
                
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}")
            
        print()
        
        # Сравнительный тест - Харьков
        print("3. Для сравнения - координаты Харькова:")
        kharkiv_coords = ensure_city_coords('харків')
        if kharkiv_coords:
            lat, lon, is_approx = kharkiv_coords
            print(f"   Харьков: ({lat}, {lon})")
        
        # Сравнительный тест - Херсон
        print("4. Для сравнения - координаты Херсона:")
        kherson_coords = ensure_city_coords('херсон')
        if kherson_coords:
            lat, lon, is_approx = kherson_coords
            print(f"   Херсон: ({lat}, {lon})")

    if __name__ == "__main__":
        test_chornobaivka()

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
