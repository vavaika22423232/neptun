#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test multi-regional Shahed message to check why only Dnipro marker is created
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_multi_regional_shahed():
    print("=== Тестування багаторегіонального повідомлення про Шахеди ===")
    
    # Точне повідомлення від користувача
    test_message = """на одещині 10 шахедів на вилкове
на дніпропетровщина 1 шахед на чаплине"""
    
    print(f"Повідомлення:\n{test_message}")
    print("\n" + "="*60)
    
    # Тестуємо кожен рядок окремо
    lines = test_message.strip().split('\n')
    print("\n=== ОКРЕМІ ТЕСТИ ===")
    
    for i, line in enumerate(lines, 1):
        print(f"\n📍 Рядок {i}: {line}")
        result = process_message(line.strip(), f"test_line_{i}", "2025-09-08 12:00:00", "test_channel")
        
        if result and isinstance(result, list):
            print(f"  - Кількість маркерів: {len(result)}")
            for j, marker in enumerate(result, 1):
                place = marker.get('place', 'N/A')
                coords = (marker.get('lat'), marker.get('lng'))
                icon = marker.get('marker_icon', 'N/A')
                source = marker.get('source_match', 'N/A')
                print(f"    Маркер {j}: {place} {coords} ({icon}, {source})")
        else:
            print(f"  ❌ Маркери не створені")
    
    # Тестуємо об'єднане повідомлення
    print(f"\n=== ОБ'ЄДНАНИЙ ТЕСТ ===")
    result = process_message(test_message, "test_combined", "2025-09-08 12:00:00", "test_channel")
    
    if result and isinstance(result, list):
        print(f"\n  - Загальна кількість маркерів: {len(result)}")
        
        regions_found = {}
        for i, marker in enumerate(result, 1):
            place = marker.get('place', 'N/A')
            coords = (marker.get('lat'), marker.get('lng'))
            icon = marker.get('marker_icon', 'N/A')
            source = marker.get('source_match', 'N/A')
            
            print(f"    Маркер {i}: {place} {coords} ({icon}, {source})")
            
            # Класифікація за регіонами
            place_lower = place.lower()
            if 'вилкове' in place_lower or 'одес' in place_lower:
                regions_found['Одещина'] = place
            elif 'чаплине' in place_lower or 'дніпро' in place_lower:
                regions_found['Дніпропетровщина'] = place
                
        print(f"\n  📊 Аналіз по регіонах:")
        expected_regions = ['Одещина', 'Дніпропетровщина'] 
        
        for region in expected_regions:
            if region in regions_found:
                print(f"    ✅ {region}: {regions_found[region]}")
            else:
                print(f"    ❌ {region}: НЕ ЗНАЙДЕНО")
                
        if len(regions_found) < 2:
            print(f"\n  ⚠️  ПРОБЛЕМА: Очікувалося 2 регіони, знайдено {len(regions_found)}")
            
        # Перевірка координат
        if len(result) == 1 and result[0].get('place') == 'Дніпро':
            print(f"\n  ❌ ОСНОВНА ПРОБЛЕМА: Створена тільки мітка в Дніпро замість Вилкове та Чаплине")
            
    else:
        print(f"  ❌ Маркери не створені")

if __name__ == "__main__":
    test_multi_regional_shahed()
