#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест для проверки, что Нікополь (украинский вариант) корректно показывает obstril.png для обстрелов
"""

import sys
import os

# Добавляем текущую папку в sys.path чтобы импортировать app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import process_message
    
    def test_nikopol_processing():
        print("=== Тест обработки сообщений с Нікополь ===\n")
        
        test_messages = [
            {
                'text': '💥 Нікополь (Дніпропетровська обл.) Загроза обстрілу! Перейдіть в укриття!',
                'description': 'Нікополь (украинский) + обстрел → должен быть obstril.png'
            },
            {
                'text': '🛸 Нікополь (Дніпропетровська обл.) Загроза БпЛА!',
                'description': 'Нікополь (украинский) + БпЛА → должен быть fpv.png'
            },
            {
                'text': '💥 Никополь (Дніпропетровська обл.) Загроза обстрілу!',
                'description': 'Никополь (русский) + обстрел → должен быть obstril.png'
            }
        ]
        
        for i, test in enumerate(test_messages, 1):
            print(f"Тест {i}: {test['description']}")
            print(f"Сообщение: {test['text']}")
            
            try:
                result = process_message(test['text'], f"test_{i}", "2025-09-13", "test_channel")
                
                if result and len(result) > 0:
                    message_data = result[0]
                    marker_icon = message_data.get('marker_icon', 'не найдено')
                    threat_type = message_data.get('threat_type', 'не найдено')
                    place = message_data.get('place', 'не найдено')
                    
                    print(f"  Результат:")
                    print(f"    Место: {place}")
                    print(f"    Тип угрозы: {threat_type}")
                    print(f"    Иконка: {marker_icon}")
                    
                    # Проверяем результат
                    if 'обстріл' in test['text'].lower() or 'обстрел' in test['text'].lower():
                        if marker_icon == 'obstril.png':
                            print(f"  ✅ ПРАВИЛЬНО: obstril.png для обстрела")
                        else:
                            print(f"  ❌ НЕПРАВИЛЬНО: ожидался obstril.png, получен {marker_icon}")
                    elif 'бпла' in test['text'].lower():
                        if marker_icon == 'fpv.png':
                            print(f"  ✅ ПРАВИЛЬНО: fpv.png для FPV города")
                        else:
                            print(f"  ❌ НЕПРАВИЛЬНО: ожидался fpv.png для FPV города, получен {marker_icon}")
                else:
                    print(f"  ❌ Сообщение не обработано")
                    
            except Exception as e:
                print(f"  ❌ ОШИБКА: {e}")
            
            print()

    if __name__ == "__main__":
        test_nikopol_processing()

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
