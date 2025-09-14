#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест для проверки, почему КАБы показывают shahed.png вместо avia.png
"""

import sys
import os

# Добавляем текущую папку в sys.path чтобы импортировать app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import process_message
    
    def test_kab_issue():
        print("=== Тест обработки КАБов ===\n")
        
        test_messages = [
            {
                'message': '💣 Хотінь (Сумська обл.) Загроза застосування КАБів. Негайно прямуйте в укриття!',
                'expected_icon': 'avia.png',
                'expected_category': 'avia',
                'description': 'КАБы (управляемые авиационные бомбы)'
            },
            {
                'message': '🛸 Тестове місто (Сумська обл.) Загроза БпЛА!',
                'expected_icon': 'shahed.png', 
                'expected_category': 'shahed',
                'description': 'БпЛА (для сравнения)'
            },
            {
                'message': '✈️ Тестове місто (Сумська обл.) Загроза тактичної авіації!',
                'expected_icon': 'avia.png',
                'expected_category': 'avia', 
                'description': 'Тактическая авиация'
            }
        ]
        
        for test in test_messages:
            print(f"Тест: {test['description']}")
            print(f"Сообщение: {test['message']}")
            
            try:
                result = process_message(test['message'], "test_1", "2025-09-13", "test_channel")
                
                if result and len(result) > 0:
                    message_data = result[0]
                    threat_type = message_data.get('threat_type', 'не найдено')
                    marker_icon = message_data.get('marker_icon', 'не найдено')
                    place = message_data.get('place', 'не найдено')
                    
                    print(f"  Результат:")
                    print(f"    Место: {place}")
                    print(f"    Категория: {threat_type}")
                    print(f"    Иконка: {marker_icon}")
                    print(f"    Ожидается: {test['expected_category']}/{test['expected_icon']}")
                    
                    if threat_type == test['expected_category'] and marker_icon == test['expected_icon']:
                        print(f"  ✅ ПРАВИЛЬНО")
                    else:
                        print(f"  ❌ НЕПРАВИЛЬНО")
                        
                        # Анализ текста сообщения
                        msg_lower = test['message'].lower()
                        print(f"  Анализ текста:")
                        
                        # Проверяем, что попадает под дроны
                        drone_keywords = ['shahed','шахед','шахеді','шахедів','geran','герань','дрон','дрони','бпла','uav']
                        found_drone = [kw for kw in drone_keywords if kw in msg_lower]
                        if found_drone:
                            print(f"    ❌ Найдены ключевые слова дронов: {found_drone}")
                        
                        # Проверяем КАБы
                        kab_keywords = ['каб','kab','умпк','umpk','модуль','fab','умпб','фаб','кабу']
                        found_kab = [kw for kw in kab_keywords if kw in msg_lower]
                        if found_kab:
                            print(f"    ✅ Найдены ключевые слова КАБов: {found_kab}")
                        
                        # Проверяем авиацию
                        avia_keywords = ['літак','самол','avia','tactical','тактичн','fighter','истребит','jets']
                        found_avia = [kw for kw in avia_keywords if kw in msg_lower]
                        if found_avia:
                            print(f"    ✅ Найдены ключевые слова авиации: {found_avia}")
                            
                else:
                    print(f"  ❌ Сообщение не обработано")
                    
            except Exception as e:
                print(f"  ❌ ОШИБКА: {e}")
            
            print()

    if __name__ == "__main__":
        test_kab_issue()

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
