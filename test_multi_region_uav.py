#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test multi-region UAV messages to check why only Chernihiv marker is created
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_multi_region_uav():
    print("=== Тестування багаторегіональних повідомлень БПЛА ===")
    
    # Повідомлення з 3 різних регіонів
    test_messages = [
        "🛵 Ворожі ударні БпЛА на сході Богодухівського району (Харківщина), курс - східний/південний.",
        "🛵 БпЛА на заході від Харкова, курс - південно-східний.", 
        "🛵 Ворожі ударні БпЛА на півночі та північному сході Чернігівщини, курс - південно-західний."
    ]
    
    # Тестуємо кожне повідомлення окремо
    print("\n=== ОКРЕМІ ТЕСТИ ===")
    for i, message in enumerate(test_messages, 1):
        print(f"\n📍 Тест {i}:")
        print(f"Повідомлення: {message}")
        
        result = process_message(message, f"test_{i}", "2025-09-08 12:00:00", "test_channel")
        
        if result and isinstance(result, list):
            print(f"  - Кількість маркерів: {len(result)}")
            for j, marker in enumerate(result, 1):
                place = marker.get('place', 'N/A')
                coords = (marker.get('lat'), marker.get('lng'))
                print(f"    Маркер {j}: {place} {coords}")
        else:
            print(f"  ❌ Маркери не створені")
    
    # Тестуємо об'єднане повідомлення (як приходить від користувача)
    print(f"\n=== ОБ'ЄДНАНИЙ ТЕСТ ===")
    combined_message = "\n".join(test_messages)
    print(f"Об'єднане повідомлення:\n{combined_message}")
    
    result = process_message(combined_message, "test_combined", "2025-09-08 12:00:00", "test_channel")
    
    if result and isinstance(result, list):
        print(f"\n  - Загальна кількість маркерів: {len(result)}")
        for i, marker in enumerate(result, 1):
            place = marker.get('place', 'N/A')
            coords = (marker.get('lat'), marker.get('lng'))
            source = marker.get('source_match', 'N/A')
            print(f"    Маркер {i}: {place} {coords} (джерело: {source})")
            
        # Аналіз по регіонах
        regions_found = {}
        for marker in result:
            place = marker.get('place', '')
            if 'харків' in place.lower() or 'богодухів' in place.lower():
                regions_found['Харківщина'] = place
            elif 'чернігів' in place.lower() or 'чернігівщина' in place.lower():
                regions_found['Чернігівщина'] = place
                
        print(f"\n  📊 Аналіз по регіонах:")
        expected_regions = ['Харківщина', 'Чернігівщина']
        for region in expected_regions:
            if region in regions_found:
                print(f"    ✅ {region}: {regions_found[region]}")
            else:
                print(f"    ❌ {region}: НЕ ЗНАЙДЕНО")
                
        if len(regions_found) < 2:
            print(f"\n  ⚠️  ПРОБЛЕМА: Очікувалося мінімум 2 регіони, знайдено {len(regions_found)}")
    else:
        print(f"  ❌ Маркери не створені")

if __name__ == "__main__":
    test_multi_region_uav()
