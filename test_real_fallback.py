#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест с реальным примером неизвестного города
"""

import sys
import os

# Добавляем текущую папку в sys.path чтобы импортировать app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import process_message
    
    def test_real_case():
        print("=== Тест реального случая ===\n")
        
        # Создаем тестовое сообщение с неизвестным городом
        message = "🛸 Якийсьневідомийгород (Херсонська обл.) Загроза застосування БПЛА. Перейдіть в укриття!"
        
        print(f"Тестовое сообщение: {message}")
        print()
        
        result = process_message(message, "test_real", "2025-09-13", "test_channel")
        
        if result and len(result) > 0:
            message_data = result[0]
            place = message_data.get('place', 'не найдено')
            lat = message_data.get('lat', None)
            lng = message_data.get('lng', None)
            marker_icon = message_data.get('marker_icon', 'не найдено')
            
            print(f"Результат обработки:")
            print(f"  Место: {place}")
            print(f"  Координаты: ({lat}, {lng})")
            print(f"  Иконка: {marker_icon}")
            print()
            
            # Проверяем координаты Херсонской области
            kherson_oblast_coords = (46.6354, 32.6169)  # Херсонська обл.
            kharkiv_coords = (49.9935, 36.2304)  # Харьков для сравнения
            
            if lat and lng:
                if abs(lat - kherson_oblast_coords[0]) < 0.1 and abs(lng - kherson_oblast_coords[1]) < 0.1:
                    print("✅ ОТЛИЧНО: Метка размещена в Херсонской области!")
                    print(f"   Правильные координаты области: {kherson_oblast_coords}")
                elif abs(lat - kharkiv_coords[0]) < 0.1 and abs(lng - kharkiv_coords[1]) < 0.1:
                    print("❌ ОШИБКА: Метка по-прежнему размещается в Харькове!")
                    print(f"   Неправильные координаты: {kharkiv_coords}")
                else:
                    print(f"⚠️ Метка размещена в других координатах: ({lat}, {lng})")
                
                print()
                print("Сравнение координат:")
                print(f"  Херсонская область: {kherson_oblast_coords}")
                print(f"  Харьков: {kharkiv_coords}")
                print(f"  Фактические: ({lat}, {lng})")
                
        else:
            print("❌ Сообщение не обработано")

    if __name__ == "__main__":
        test_real_case()

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
