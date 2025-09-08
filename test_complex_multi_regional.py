#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test complex multi-regional message with pipes and different cities
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_complex_multi_regional():
    print("=== Тестування складного багаторегіонального повідомлення ===")
    
    # Точне повідомлення від користувача
    test_message = """чернігівщина (новгород-сіверський р-н) та одещина - загроза застосування ворогом ударних бпла. | одещина - шахеди на вилково
ㅤ | група 8х бпла у напрямку ізмаїльського району одещини, вилкове."""
    
    print(f"Повідомлення:\n{test_message}")
    print("\n" + "="*70)
    
    # Розберемо повідомлення на частини
    lines = test_message.strip().split('\n')
    print(f"\nРядки повідомлення:")
    for i, line in enumerate(lines, 1):
        print(f"  {i}: '{line}'")
    
    # Очікувані мітки
    expected_cities = [
        "Новгород-Сіверський (Чернігівщина)",
        "Вилкове (Одещина)", 
        "Ізмаїл (Одещина)"  # можливо
    ]
    
    print(f"\nОчікувані мітки: {expected_cities}")
    
    # Тестуємо обробку
    result = process_message(test_message, "test_complex", "2025-09-08 12:00:00", "test_channel")
    
    if result and isinstance(result, list):
        print(f"\n✅ Результат: {len(result)} маркерів створено")
        
        regions_found = {}
        cities_found = []
        
        for i, marker in enumerate(result, 1):
            place = marker.get('place', 'N/A')
            coords = (marker.get('lat'), marker.get('lng'))
            icon = marker.get('marker_icon', 'N/A')
            source = marker.get('source_match', 'N/A')
            threat_type = marker.get('threat_type', 'N/A')
            
            print(f"\nМаркер {i}:")
            print(f"  📍 Місце: {place}")
            print(f"  🗺️  Координати: {coords}")
            print(f"  🔶 Іконка: {icon}")
            print(f"  🔍 Джерело: {source}")
            print(f"  ⚠️  Тип: {threat_type}")
            
            cities_found.append(place)
            
            # Класифікація за регіонами
            place_lower = place.lower()
            if 'новгород' in place_lower or 'чернігів' in place_lower:
                regions_found['Чернігівщина'] = place
            elif 'вилкове' in place_lower or 'вилково' in place_lower or 'одес' in place_lower or 'ізмаїл' in place_lower:
                regions_found['Одещина'] = place
        
        print(f"\n" + "="*70)
        print("📊 АНАЛІЗ РЕЗУЛЬТАТІВ:")
        
        expected_regions = ['Чернігівщина', 'Одещина']
        
        for region in expected_regions:
            if region in regions_found:
                print(f"  ✅ {region}: {regions_found[region]}")
            else:
                print(f"  ❌ {region}: НЕ ЗНАЙДЕНО")
        
        print(f"\n🎯 Знайдені міста: {cities_found}")
        
        # Перевірка основної проблеми
        if len(result) == 1 and any('одес' in city.lower() for city in cities_found):
            print(f"\n⚠️  ПРОБЛЕМА: Створена тільки мітка в Одесі замість конкретних міст")
            print(f"   Очікувалося: Вилкове, можливо Новгород-Сіверський")
            print(f"   Отримано: {cities_found[0]}")
        elif len(result) >= 2:
            print(f"\n🎉 ДОБРЕ: Створено {len(result)} міток для різних міст")
        else:
            print(f"\n⚠️  РЕЗУЛЬТАТ: {len(result)} міток")
            
    else:
        print("❌ ПОМИЛКА: Маркери не створені")

if __name__ == "__main__":
    test_complex_multi_regional()
