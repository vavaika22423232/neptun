#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест различных сценариев с несколькими городами
"""

import sys
sys.path.append('.')

try:
    from app import process_message, SPACY_AVAILABLE
    print(f"SpaCy available: {SPACY_AVAILABLE}")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def test_various_multi_city_scenarios():
    test_cases = [
        {
            'name': 'Підготовка до пусків БПЛА (оригинальный случай)',
            'message': 'Підготовка до пусків БПЛА з Шаталово, Орла, Брянська, Міллерево',
            'expected_type': 'pusk'
        },
        {
            'name': 'Обстріл кількох міст',
            'message': 'Обстріл з території Білгорода, Орла, підтвердження вибухів',
            'expected_type': 'artillery'
        },
        {
            'name': 'Рух Шахедів через кілька міст',
            'message': 'Шахеди через Суми, Полтаву, курс на Дніпро',
            'expected_type': 'shahed'
        }
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\n=== ТЕСТ {i+1}: {case['name']} ===")
        print(f"Сообщение: {case['message']}")
        
        try:
            results = process_message(case['message'], f"test_{i}", "2025-09-27 12:00:00", "test")
            
            print(f"Результат: {len(results)} меток")
            
            if results:
                for j, result in enumerate(results):
                    print(f"  {j+1}. Город: {result.get('place', 'Не указан')}")
                    print(f"     Координаты: {result.get('lat', 'N/A')}, {result.get('lng', 'N/A')}")
                    print(f"     Тип угрозы: {result.get('threat_type', 'N/A')}")
                    
                    # Проверяем тип угрозы
                    if result.get('threat_type') == case['expected_type']:
                        print(f"     ✅ Тип угрозы правильный: {case['expected_type']}")
                    else:
                        print(f"     ❌ Ожидался {case['expected_type']}, получен {result.get('threat_type')}")
            else:
                print("  ❌ Метки не созданы")
                
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_various_multi_city_scenarios()
