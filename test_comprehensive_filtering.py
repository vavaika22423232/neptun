#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_comprehensive_filtering():
    print("=== КОМПЛЕКСНЫЙ ТЕСТ ФИЛЬТРАЦИИ ===")
    
    test_cases = [
        # Должны фильтроваться (НЕ отображаться на карте)
        {
            "message": "🪿Передислокація Ту-160 з Українки на \"Енгельс-2\"",
            "should_filter": True,
            "reason": "Передислокация Ту-160"
        },
        {
            "message": "протягом ночі уважним бути києву, київщина і західна україна. український ппошник",
            "should_filter": True,
            "reason": "Общее предупреждение"
        },
        {
            "message": "🟢 Конотопський район (Сумська обл.)\nВідбій тривоги. Будьте обережні!",
            "should_filter": True,
            "reason": "Відбій тривоги"
        },
        {
            "message": "🚨 Шосткинський район (Сумська обл.)\nПовітряна тривога. Прямуйте в укриття!",
            "should_filter": True,
            "reason": "Повітряна тривога"
        },
        
        # НЕ должны фильтроваться (отображаться на карте)
        {
            "message": "БпЛА на Суми, курс на Полтаву",
            "should_filter": False,
            "reason": "Конкретная угроза с координатами"
        },
        {
            "message": "Обстріл Харкова, підтверджено вибухи",
            "should_filter": False,
            "reason": "Конкретный обстрел"
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        message = test_case["message"]
        should_filter = test_case["should_filter"]
        reason = test_case["reason"]
        
        print(f"\nТЕСТ {i}: {reason}")
        print(f"Сообщение: {message[:60]}...")
        
        try:
            result = process_message(message, f"test_{i}", "2025-09-27 12:00:00", "test")
            
            is_filtered = (result is None or result == [])
            
            if is_filtered == should_filter:
                status = "✅ ПРОШЕЛ" 
                passed += 1
            else:
                status = "❌ ПРОВАЛЕН"
            
            expected = "должно фильтроваться" if should_filter else "НЕ должно фильтроваться"
            actual = "отфильтровано" if is_filtered else f"создано {len(result) if result else 0} меток"
            
            print(f"Ожидалось: {expected}")
            print(f"Результат: {actual}")
            print(f"{status}")
                    
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
        
        print("-" * 60)
    
    print(f"\n=== ИТОГИ ===")
    print(f"Прошло тестов: {passed}/{total}")
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    else:
        print(f"⚠️  {total - passed} тестов провалено")

if __name__ == "__main__":
    test_comprehensive_filtering()
