#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Dnipro high-speed targets message to ensure it uses raketa.png not shahed.png
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_dnipro_targets_message():
    print("=== Тестування повідомлення про високошвидкісні цілі ===")
    
    # Тестове повідомлення про Дніпро з високошвидкісними цілями
    test_message = "**🚀 Дніпро (Дніпропетровська обл.)** Загроза застосування високошвидкісних цілей. Негайно прямуйте в укриття!"
    
    print(f"Вхідне повідомлення:\n{test_message}")
    print("\n" + "="*50)
    
    result = process_message(test_message, "test_dnipro", "2025-09-08 12:00:00", "test_channel")
    
    print(f"\nРезультат парсингу:")
    print(f"- Тип результату: {type(result)}")
    
    if result and isinstance(result, list) and len(result) > 0:
        print(f"- Кількість маркерів: {len(result)}")
        
        marker = result[0]
        place = marker.get('place', 'N/A')
        coordinates = (marker.get('lat'), marker.get('lng'))
        threat_type = marker.get('threat_type', 'N/A')
        icon = marker.get('marker_icon', 'N/A')
        source = marker.get('source_match', 'N/A')
        
        print(f"\nМаркер:")
        print(f"  - Місце: {place}")
        print(f"  - Координати: {coordinates}")
        print(f"  - Тип загрози: {threat_type}")
        print(f"  - Іконка: {icon}")
        print(f"  - Джерело: {source}")
        
        # Перевірка правильності
        if place.lower() == 'дніпро':
            print(f"  ✅ МІСЦЕ: Правильно розпізнано Дніпро")
        else:
            print(f"  ❌ МІСЦЕ: Очікувався Дніпро, отримано {place}")
            
        if icon == 'raketa.png':
            print(f"  ✅ ІКОНКА: Правильно визначено raketa.png для високошвидкісних цілей")
        elif icon == 'shahed.png':
            print(f"  ❌ ІКОНКА: ПОМИЛКА! Високошвидкісні цілі повинні мати raketa.png, а не shahed.png")
        else:
            print(f"  ⚠️  ІКОНКА: Неочікувана іконка {icon}")
            
        if threat_type == 'raketa':
            print(f"  ✅ ТИП: Правильно класифіковано як ракетна загроза")
        else:
            print(f"  ⚠️  ТИП: Тип загрози {threat_type}")
            
    else:
        print("❌ ПОМИЛКА: Маркер не створено")
    
    print("\n" + "="*50)
    
    # Додатковий тест - фраза "ціль на дніпро/область"
    print("\n=== Додатковий тест: 'ціль на дніпро/область' ===")
    test_message2 = "ціль на дніпро/область"
    
    print(f"Повідомлення: {test_message2}")
    result2 = process_message(test_message2, "test_target", "2025-09-08 12:00:00", "test_channel")
    
    if result2 and isinstance(result2, list) and len(result2) > 0:
        marker2 = result2[0]
        place2 = marker2.get('place', 'N/A')
        icon2 = marker2.get('marker_icon', 'N/A')
        
        print(f"  - Місце: {place2}")
        print(f"  - Іконка: {icon2}")
        
        if icon2 == 'raketa.png':
            print(f"  ✅ Правильно: 'ціль' → raketa.png")
        else:
            print(f"  ❌ Помилка: 'ціль' повинна бути raketa.png, а не {icon2}")
    else:
        print("  ❌ Маркер не створено для 'ціль на дніпро/область'")
    
    print("\n" + "="*50)
    return result

if __name__ == "__main__":
    test_dnipro_targets_message()
