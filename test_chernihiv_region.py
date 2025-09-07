#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест для повідомлення про Чернігівщину з напрямком
"""

def test_chernihiv_message():
    import sys
    sys.path.append('.')
    import app
    
    # Тестове повідомлення
    test_text = "декілька груп ворожих бпла на чернігівщина у південно-західному напрямку."
    
    print("Тестуємо повідомлення:", test_text)
    print("=" * 60)
    
    # Тестуємо парсинг
    try:
        events = app.process_message(test_text, "test_id", "2025-09-07 14:02:37", "kpszsu")
        
        if events:
            print(f"Знайдено {len(events)} подій:")
            for i, event in enumerate(events, 1):
                print(f"  Подія {i}:")
                print(f"    Тип: {event.get('threat_type', 'невідомо')}")
                print(f"    Координати: {event.get('lat', 'N/A')}, {event.get('lng', 'N/A')}")
                print(f"    Локація: {event.get('location', 'невідомо')}")
                print(f"    Регіон: {event.get('region', 'невідомо')}")
                print(f"    Опис: {event.get('description', 'невідомо')}")
                print()
        else:
            print("❌ Подій не знайдено")
            
        # Перевіряємо розпізнавання регіону окремо
        print("Тест розпізнавання регіону:")
        if 'чернігівщин' in test_text.lower():
            print("✅ 'чернігівщин' знайдено в тексті")
        else:
            print("❌ 'чернігівщин' не знайдено в тексті")
            
        if 'південно-західн' in test_text.lower():
            print("✅ 'південно-západн' знайдено в тексті")
        else:
            print("❌ 'південно-західн' не знайдено в тексті")
    
    except Exception as e:
        print(f"Помилка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_chernihiv_message()
