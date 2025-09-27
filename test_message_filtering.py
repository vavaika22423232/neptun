#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест фильтрации сообщений без конкретных локаций
"""

import sys
sys.path.append('.')

try:
    from app import process_message
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def test_message_filtering():
    """Тестируем фильтрацию различных типов сообщений"""
    
    test_cases = [
        {
            'name': 'Передислокация Ту-160 (должно фильтроваться)',
            'message': '🪿Передислокація Ту-160 з Українки на "Енгельс-2" ✙[ Напрямок ракет ](https://t.me/napramok)✙ ✙[Підтримати канал](https://send.monobank.ua/5Pwr3r52mg)✙ **Відмічено Ту-160 в Саратовській області, ймовірно переліт на аеродром Енгельс-2 з аеродрома Українка.**',
            'should_filter': True
        },
        {
            'name': 'Общее предупреждение о ночной опасности (должно фильтроваться)',
            'message': 'протягом ночі уважним бути києву, київщина і західна україна. український ппошник',
            'should_filter': True
        },
        {
            'name': 'Конкретная угроза с координатами (НЕ должно фильтроваться)',
            'message': 'БпЛА на Суми, курс на Полтаву',
            'should_filter': False
        },
        {
            'name': 'Обстрел конкретного города (НЕ должно фильтроваться)', 
            'message': 'Обстріл Харкова, підтверджено вибухи',
            'should_filter': False
        }
    ]
    
    print("=== ТЕСТ ФИЛЬТРАЦИИ СООБЩЕНИЙ ===\n")
    
    for i, case in enumerate(test_cases):
        print(f"ТЕСТ {i+1}: {case['name']}")
        print(f"Сообщение: {case['message'][:100]}{'...' if len(case['message']) > 100 else ''}")
        
        try:
            result = process_message(case['message'], f"filter_test_{i}", "2025-09-27 12:00:00", "test")
            
            if result is None:
                print(f"Результат: ОТФИЛЬТРОВАНО (None)")
                filtered = True
            elif isinstance(result, list) and len(result) == 0:
                print(f"Результат: ОТФИЛЬТРОВАНО (пустой список)")
                filtered = True
            else:
                print(f"Результат: НЕ ОТФИЛЬТРОВАНО ({len(result)} меток)")
                filtered = False
            
            # Проверяем правильность фильтрации
            if case['should_filter'] and filtered:
                print("✅ ПРАВИЛЬНО: Сообщение отфильтровано как ожидалось")
            elif not case['should_filter'] and not filtered:
                print("✅ ПРАВИЛЬНО: Сообщение не отфильтровано, созданы метки")
            elif case['should_filter'] and not filtered:
                print("❌ ОШИБКА: Сообщение должно было быть отфильтровано, но создались метки")
            else:
                print("❌ ОШИБКА: Сообщение не должно было фильтроваться, но было отфильтровано")
                
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            
        print("-" * 60)
        print()

if __name__ == "__main__":
    test_message_filtering()
