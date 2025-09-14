#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест точного сообщения пользователя
"""

import sys
import os

# Добавляем текущую папку в sys.path чтобы импортировать app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import process_message
    
    def test_exact_user_message():
        print("=== Тест точного сообщения пользователя ===\n")
        
        # Точное сообщение от пользователя
        message = "💣 Хотінь (Сумська обл.) Загроза застосування КАБів. Негайно прямуйте в укриття!"
        
        print(f"Тестируемое сообщение:")
        print(f"{message}")
        print()
        
        result = process_message(message, "user_test", "2025-09-14", "test_channel")
        
        if result and len(result) > 0:
            message_data = result[0]
            threat_type = message_data.get('threat_type', 'не найдено')
            marker_icon = message_data.get('marker_icon', 'не найдено')
            place = message_data.get('place', 'не найдено')
            lat = message_data.get('lat', None)
            lng = message_data.get('lng', None)
            
            print(f"Результат обработки:")
            print(f"  Место: {place}")
            print(f"  Координаты: ({lat}, {lng})")
            print(f"  Категория угрозы: {threat_type}")
            print(f"  Иконка маркера: {marker_icon}")
            print()
            
            # Анализ
            if marker_icon == 'shahed.png':
                print("❌ ПРОБЛЕМА: Показывает shahed.png (дроны)")
                print("   КАБы должны показывать avia.png (авиация)")
            elif marker_icon == 'avia.png':
                print("✅ ПРАВИЛЬНО: Показывает avia.png (авиация)")
            else:
                print(f"⚠️ Неожиданная иконка: {marker_icon}")
            
            print()
            print("Анализ содержимого сообщения:")
            msg_lower = message.lower()
            
            # Проверка на КАБы
            if 'каб' in msg_lower:
                print("✅ Содержит 'каб' - должно обрабатываться как авиация")
            
            # Проверка на дроны
            drone_words = ['бпла', 'дрон', 'шахед', 'shahed']
            found_drones = [word for word in drone_words if word in msg_lower]
            if found_drones:
                print(f"❌ Также содержит слова дронов: {found_drones}")
            else:
                print("✅ Не содержит слов дронов")
                
        else:
            print("❌ Сообщение не обработано")

    if __name__ == "__main__":
        test_exact_user_message()

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
