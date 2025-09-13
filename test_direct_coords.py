#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простая проверка координат через прямую работу с CITY_COORDS
"""

import sys
import os

# Добавляем текущую папку в sys.path чтобы импортировать app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import CITY_COORDS, ensure_city_coords

    def test_direct_lookup():
        print("=== Прямая проверка координат в базе ===\n")
        
        test_cities = ['сергіївка', 'тузли', 'луцьк', 'миколаїв']
        
        for city in test_cities:
            if city in CITY_COORDS:
                lat, lon = CITY_COORDS[city]
                print(f"✅ {city}: ({lat}, {lon})")
            else:
                print(f"❌ {city}: не найдено в CITY_COORDS")
        
        print("\n=== Проверка через ensure_city_coords ===\n")
        
        for city in test_cities:
            result = ensure_city_coords(city)
            if result:
                lat, lon, is_approx = result
                print(f"✅ {city}: ({lat}, {lon}) - {'приблизительно' if is_approx else 'точно'}")
            else:
                print(f"❌ {city}: не найдено")
        
        print("\n=== Проверка проблемных случаев ===\n")
        
        # Проверим, что Сергіївка не равна Луцьку
        serg_coords = ensure_city_coords('сергіївка')
        lutsk_coords = ensure_city_coords('луцьк')
        
        if serg_coords and lutsk_coords:
            if serg_coords[:2] == lutsk_coords[:2]:
                print("❌ ОШИБКА: Сергіївка имеет те же координаты что и Луцьк!")
            else:
                print("✅ ОК: Сергіївка и Луцьк имеют разные координаты")
        
        # Проверим, что Тузли не равны Николаеву
        tuzly_coords = ensure_city_coords('тузли')
        mykolaiv_coords = ensure_city_coords('миколаїв')
        
        if tuzly_coords and mykolaiv_coords:
            if tuzly_coords[:2] == mykolaiv_coords[:2]:
                print("❌ ОШИБКА: Тузли имеют те же координаты что и Николаев!")
            else:
                print("✅ ОК: Тузли и Николаев имеют разные координаты")

    if __name__ == "__main__":
        test_direct_lookup()
        
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что app.py находится в той же папке")
