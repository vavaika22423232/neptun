#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест для проверки, что КАБы показывают raketa.png (не avia.png и не shahed.png)
"""

import sys
import os

# Добавляем текущую папку в sys.path чтобы импортировать app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import process_message
    
    def test_kab_messages():
        print("=== Тест КАБов (должны показывать raketa.png) ===\n")
        
        test_messages = [
            {
                'message': '💣 Хотінь (Сумська обл.) Загроза застосування КАБів. Негайно прямуйте в укриття!',
                'expected_icon': 'raketa.png',
                'expected_threat': 'raketa',
                'description': 'Точное сообщение пользователя - КАБы'
            },
            {
                'message': '💣 Київ Загроза КАБ!',
                'expected_icon': 'raketa.png',
                'expected_threat': 'raketa',
                'description': 'КАБ (краткая форма)'
            },
            {
                'message': '💣 Харків Керовані авіаційні бомби!',
                'expected_icon': 'raketa.png',
                'expected_threat': 'raketa',
                'description': 'Керовані авіаційні бомби'
            },
            {
                'message': '✈️ Харків Літаки в повітрі!',
                'expected_icon': 'avia.png',
                'expected_threat': 'avia',
                'description': 'Для сравнения - авиация (не КАБы)'
            },
            {
                'message': '🛸 Одеса БпЛА!',
                'expected_icon': 'shahed.png',
                'expected_threat': 'shahed',
                'description': 'Для сравнения - дроны (не КАБы)'
            }
        ]
        
        for i, test in enumerate(test_messages, 1):
            print(f"Тест {i}: {test['description']}")
            print(f"  Сообщение: {test['message']}")
            
            try:
                result = process_message(test['message'], f"test_{i}", "2025-09-13", "test_channel")
                
                if result and len(result) > 0:
                    message_data = result[0]
                    place = message_data.get('place', 'не найдено')
                    threat_type = message_data.get('threat_type', 'не найдено')
                    marker_icon = message_data.get('marker_icon', 'не найдено')
                    
                    print(f"  Результат:")
                    print(f"    Место: {place}")
                    print(f"    Тип угрозы: {threat_type}")
                    print(f"    Иконка: {marker_icon}")
                    
                    # Проверяем результат
                    if marker_icon == test['expected_icon'] and threat_type == test['expected_threat']:
                        print(f"    ✅ ПРАВИЛЬНО: {test['expected_icon']}")
                    else:
                        print(f"    ❌ НЕПРАВИЛЬНО: ожидался {test['expected_icon']}, получен {marker_icon}")
                        
                else:
                    print(f"    ❌ Сообщение не обработано")
                    
            except Exception as e:
                print(f"    ❌ ОШИБКА: {e}")
            
            print()

    if __name__ == "__main__":
        test_kab_messages()

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
