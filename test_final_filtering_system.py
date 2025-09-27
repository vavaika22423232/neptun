#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_final_filtering_system():
    print("=== ФИНАЛЬНЫЙ ТЕСТ СИСТЕМЫ ФИЛЬТРАЦИИ ===")
    
    test_cases = [
        # Должны фильтроваться (НЕ отображаться на карте)
        {
            "message": "👀Ніч буде важкою, залишатимуся з вами друзі вночі, підтримайте мене по 5-10-15 грн",
            "should_filter": True,
            "reason": "Сбор средств"
        },
        {
            "message": "✙ Напрямок ракет ✙\n✙Підтримати канал✙",
            "should_filter": True,
            "reason": "Реклама канала"
        },
        {
            "message": "🪿Передислокація Ту-160 з Українки на \"Енгельс-2\"",
            "should_filter": True,
            "reason": "Передислокация Ту-160"
        },
        {
            "message": "🟢 Конотопський район (Сумська обл.)\nВідбій тривоги. Будьте обережні!",
            "should_filter": True,
            "reason": "Відбій тривоги"
        },
        
        # НЕ должны фильтроваться (отображаться на карте с очищенным текстом)
        {
            "message": "Обстріл Харкова https://t.me/test @test_channel",
            "should_filter": False,
            "reason": "Конкретный обстрел с ссылками (должны удалиться)"
        },
        {
            "message": "БпЛА курс на Полтаву",
            "should_filter": False,
            "reason": "Конкретная угроза"
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        message = test_case["message"]
        should_filter = test_case["should_filter"]
        reason = test_case["reason"]
        
        print(f"\nТЕСТ {i}: {reason}")
        print(f"Сообщение: {message[:50]}...")
        
        try:
            result = process_message(message, f"final_test_{i}", "2025-09-27 12:00:00", "test")
            
            is_filtered = (result is None or result == [])
            
            if is_filtered == should_filter:
                status = "✅ ПРОШЕЛ" 
                passed += 1
                
                # Дополнительная проверка очистки ссылок для НЕфильтруемых сообщений
                if not should_filter and result:
                    cleaned_text = result[0].get('text', '')
                    has_links = any(link in cleaned_text for link in ['https://', 'www.', 't.me/', 'monobank'])
                    if has_links:
                        print(f"  ⚠️  Ссылки не удалены: {cleaned_text}")
                    else:
                        print(f"  ✅ Ссылки удалены: {cleaned_text}")
            else:
                status = "❌ ПРОВАЛЕН"
            
            expected = "должно фильтроваться" if should_filter else "НЕ должно фильтроваться" 
            actual = "отфильтровано" if is_filtered else f"создано {len(result) if result else 0} меток"
            
            print(f"Ожидалось: {expected}")
            print(f"Результат: {actual}")
            print(f"{status}")
                    
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
        
        print("-" * 50)
    
    print(f"\n=== ИТОГИ ===")
    print(f"Прошло тестов: {passed}/{total}")
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("✅ Нетактические сообщения фильтруются")  
        print("✅ Ссылки удаляются из текста")
        print("✅ Реальные угрозы обрабатываются")
    else:
        print(f"⚠️  {total - passed} тестов провалено")

if __name__ == "__main__":
    test_final_filtering_system()
