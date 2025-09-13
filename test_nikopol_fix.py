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
    from app import classify
    
    def test_nikopol_obstril():
        print("=== Тест Нікополь (украинский) для obstril.png ===\n")
        
        test_cases = [
            {
                'message': '💥 Нікополь (Дніпропетровська обл.) Загроза обстрілу! Перейдіть в укриття!',
                'city_context': 'нікополь',
                'expected_category': 'obstril',
                'expected_icon': 'obstril.png',
                'description': 'Нікополь (украинский) + обстрел'
            },
            {
                'message': '💥 Никополь (Дніпропетровська обл.) Загроза обстрілу! Перейдіть в укриття!',
                'city_context': 'никополь',
                'expected_category': 'obstril',
                'expected_icon': 'obstril.png', 
                'description': 'Никополь (русский) + обстрел'
            },
            {
                'message': '🛸 Нікополь (Дніпропетровська обл.) Загроза БпЛА!',
                'city_context': 'нікополь',
                'expected_category': 'fpv',
                'expected_icon': 'fpv.png',
                'description': 'Нікополь (украинский) + БпЛА (должен быть FPV)'
            },
            {
                'message': '💥 Марганець (Дніпропетровська обл.) Загроза обстрілу!',
                'city_context': 'марганець',
                'expected_category': 'obstril', 
                'expected_icon': 'obstril.png',
                'description': 'Для сравнения - Марганець + обстрел'
            }
        ]
        
        for test in test_cases:
            print(f"Тест: {test['description']}")
            print(f"Сообщение: {test['message']}")
            print(f"Контекст города: '{test['city_context']}'")
            
            try:
                category, icon = classify(test['message'], test['city_context'])
                
                print(f"  Результат: category='{category}', icon='{icon}'")
                print(f"  Ожидается: category='{test['expected_category']}', icon='{test['expected_icon']}'")
                
                if category == test['expected_category'] and icon == test['expected_icon']:
                    print(f"  ✅ ПРАВИЛЬНО")
                else:
                    print(f"  ❌ НЕПРАВИЛЬНО")
                    
            except Exception as e:
                print(f"  ❌ ОШИБКА: {e}")
            
            print()

    if __name__ == "__main__":
        test_nikopol_obstril()

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
