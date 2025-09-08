#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug regex pattern for region-city Shahed messages
"""

import re

def test_regex_pattern():
    print("=== Тестування regex паттерну для регіон-місто ===")
    
    test_messages = [
        "на одещині 10 шахедів на вилкове",
        "на дніпропетровщина 1 шахед на чаплине",
        "на харківщині 5 шахедів на куп'янськ",
        "на сумщині 3 шахеди на охтирку"
    ]
    
    # Паттерн з коду
    pattern = re.compile(r'на\s+([а-яіїєґ]+щин[іау]?)\s+(\d+)\s+шахед[іїв]*\s+на\s+([а-яіїєґ\'\-\s]+)', re.IGNORECASE)
    
    for message in test_messages:
        print(f"\n📍 Тестування: '{message}'")
        match = pattern.search(message.lower())
        
        if match:
            region, count, city = match.groups()
            print(f"  ✅ ЗНАЙДЕНО: регіон='{region}', кількість='{count}', місто='{city}'")
        else:
            print(f"  ❌ НЕ ЗНАЙДЕНО")
            
            # Спробуємо покроково
            parts = message.lower().split()
            print(f"     Частини: {parts}")
            
            # Перевіримо кожну частину окремо
            if 'на' in parts:
                print(f"     'на' знайдено")
            
            region_candidates = [part for part in parts if 'щин' in part]
            print(f"     Кандидати регіону: {region_candidates}")
            
            numbers = [part for part in parts if part.isdigit()]
            print(f"     Числа: {numbers}")
            
            shahed_candidates = [part for part in parts if 'шахед' in part]
            print(f"     Шахед кандидати: {shahed_candidates}")

if __name__ == "__main__":
    test_regex_pattern()
