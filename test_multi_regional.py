#!/usr/bin/env python3
"""
Тест для мультирегиональных UAV сообщений
"""

import sys
import re

# Добавляем основной модуль
sys.path.insert(0, '.')

from app import process_message

def test_multi_regional_uav():
    """Тест сообщения с множественными регионами и БпЛА"""
    
    test_message = """**Сумщина:**
5х БпЛА курсом на Конотоп
**Чернігівщина:**
БпЛА курсом на Батурин
БпЛА курсом на Новгород-Сіверський
БпЛА курсом на Мену
БпЛА курсом на Сновськ
БпЛА курсом на Бахмач
2х БпЛА курсом на Гончарівське
**Київщина:**
БпЛА курсом на Пісківку
БпЛА курсом на Бориспіль
2х БпЛА курсом на Велику Димерку
БпЛА курсом на Димер
**Запорізька область:**
7х БпЛА курсом на Запоріжжя
**Миколаївщина:**
2х БпЛА курсом на Миколаїв
Напрямок ракет
Підтримати канал | Сумщина — 6 БпЛА на Конотоп"""

    print("🔍 Тестування мультирегіонального UAV сообщения...")
    print("=" * 60)
    
    try:
        result = process_message(test_message, "test_123", "2024-01-01 10:00:00", "test_channel")
        
        if result:
            print(f"✅ Результат: {len(result)} загроз знайдено")
            print("\n📍 Створені маркери:")
            for i, threat in enumerate(result, 1):
                place = threat.get('place', 'Unknown')
                lat = threat.get('lat', 0)
                lng = threat.get('lng', 0)
                source = threat.get('source_match', 'unknown')
                count = threat.get('count', 1)
                print(f"  {i}. {place} ({count}x) - {lat:.4f}, {lng:.4f} [{source}]")
                
            # Проверяем ожидаемые города
            expected_cities = [
                'Конотоп', 'Батурин', 'Новгород-Сіверський', 'Мена', 'Сновськ', 
                'Бахмач', 'Гончарівське', 'Пісківка', 'Бориспіль', 'Велика Димерка',
                'Димер', 'Запоріжжя', 'Миколаїв'
            ]
            
            found_places = [threat.get('place', '') for threat in result]
            missing_cities = [city for city in expected_cities if not any(city.lower() in place.lower() for place in found_places)]
            
            if missing_cities:
                print(f"\n⚠️  Не знайдено: {missing_cities}")
            else:
                print(f"\n🎯 Усі очікувані міста знайдено!")
                
        else:
            print("❌ Нічого не знайдено")
            
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_regional_uav()
