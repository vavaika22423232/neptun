#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test the exact user message that was problematic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_exact_user_message():
    print("=== Тестування точного повідомлення користувача ===")
    
    # Точне повідомлення від користувача
    exact_message = """🛵 Ворожі ударні БпЛА на сході Богодухівського району (Харківщина), курс - східний/південний.
🛵 БпЛА на заході від Харкова, курс - південно-східний.
🛵 Ворожі ударні БпЛА на півночі та північному сході Чернігівщини, курс - південно-західний."""
    
    print(f"Повідомлення:\n{exact_message}")
    print("\n" + "="*60)
    
    result = process_message(exact_message, "exact_test", "2025-09-08 12:00:00", "test_channel")
    
    if result and isinstance(result, list):
        print(f"\n✅ Результат: {len(result)} маркерів створено")
        
        regions_found = {}
        for i, marker in enumerate(result, 1):
            place = marker.get('place', 'N/A')
            coords = (marker.get('lat'), marker.get('lng'))
            source = marker.get('source_match', 'N/A')
            
            print(f"\nМаркер {i}:")
            print(f"  📍 Місце: {place}")
            print(f"  🗺️  Координати: {coords}")
            print(f"  🔍 Джерело: {source}")
            
            # Класифікація за регіонами
            place_lower = place.lower()
            if 'харків' in place_lower or 'богодухів' in place_lower:
                regions_found['Харківщина'] = place
            elif 'чернігів' in place_lower:
                regions_found['Чернігівщина'] = place
        
        print(f"\n" + "="*60)
        print("📊 ПІДСУМОК ПО РЕГІОНАХ:")
        
        expected_regions = ['Харківщина', 'Чернігівщина']
        all_found = True
        
        for region in expected_regions:
            if region in regions_found:
                print(f"  ✅ {region}: {regions_found[region]}")
            else:
                print(f"  ❌ {region}: НЕ ЗНАЙДЕНО")
                all_found = False
        
        if all_found:
            print(f"\n🎉 УСПІХ: Всі регіони знайдені! Проблему вирішено.")
        else:
            print(f"\n⚠️  ПРОБЛЕМА: Не всі регіони знайдені.")
            
        if len(result) >= 2:
            print(f"🎯 МАРКЕРІВ: {len(result)} (мінімум 2 очікувалося)")
        else:
            print(f"⚠️  МАРКЕРІВ: {len(result)} (очікувалося мінімум 2)")
            
    else:
        print("❌ ПОМИЛКА: Маркери не створені")

if __name__ == "__main__":
    test_exact_user_message()
