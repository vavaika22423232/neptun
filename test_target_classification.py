#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test various target/missile messages to ensure proper raketa.png classification
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_various_target_messages():
    print("=== Тестування різних повідомлень про цілі/ракети ===")
    
    test_cases = [
        ("Емоджі ракета + ціль", "**🚀 Дніпро (Дніпропетровська обл.)** Загроза застосування високошвидкісних цілей."),
        ("Проста ціль", "ціль на дніпро/область"),
        ("Множина цілей", "високошвидкісні цілі на київ"),
        ("Ракета", "ракета на харків"),
        ("БпЛА (для порівняння)", "🛸 БпЛА на суми"),
        ("Шахед (для порівняння)", "шахеди на полтаву"),
    ]
    
    expected_results = {
        "Емоджі ракета + ціль": "raketa.png",
        "Проста ціль": "raketa.png", 
        "Множина цілей": "raketa.png",
        "Ракета": "raketa.png",
        "БпЛА (для порівняння)": "shahed.png",
        "Шахед (для порівняння)": "shahed.png",
    }
    
    results = {}
    
    for test_name, message in test_cases:
        print(f"\n📍 {test_name}:")
        print(f"   Повідомлення: {message}")
        
        result = process_message(message, f"test_{test_name.replace(' ', '_')}", "2025-09-08 12:00:00", "test_channel")
        
        if result and isinstance(result, list) and len(result) > 0:
            marker = result[0]
            icon = marker.get('marker_icon', 'N/A')
            place = marker.get('place', 'N/A')
            threat_type = marker.get('threat_type', 'N/A')
            
            results[test_name] = icon
            expected = expected_results[test_name]
            
            if icon == expected:
                print(f"   ✅ ПРАВИЛЬНО: {place} → {icon} (тип: {threat_type})")
            else:
                print(f"   ❌ ПОМИЛКА: {place} → {icon}, очікувалося {expected} (тип: {threat_type})")
        else:
            print(f"   ❌ Маркер не створено")
            results[test_name] = "NO_MARKER"
    
    # Підсумок
    print(f"\n{'='*60}")
    print("📊 ПІДСУМОК ТЕСТУВАННЯ:")
    
    correct = 0
    total = len(test_cases)
    
    for test_name, expected in expected_results.items():
        actual = results.get(test_name, "NO_RESULT")
        if actual == expected:
            print(f"  ✅ {test_name}: {actual}")
            correct += 1
        else:
            print(f"  ❌ {test_name}: {actual} (очікувалося {expected})")
    
    print(f"\n🎯 Результат: {correct}/{total} тестів пройшли успішно")
    
    if correct == total:
        print("🎉 ВСІ ТЕСТИ ПРОЙШЛИ! Класифікація працює правильно.")
    else:
        print("⚠️  Деякі тести не пройшли. Потрібні додаткові виправлення.")

if __name__ == "__main__":
    test_various_target_messages()
