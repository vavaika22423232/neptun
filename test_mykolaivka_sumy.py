#!/usr/bin/env python3
"""
Тест для проверки правильного определения Миколаївки на Сумщині
"""

import sys
sys.path.insert(0, '.')

from app import process_message

def test_mykolaivka_sumy():
    """Тестирует правильное определение Миколаївки в Сумской области"""
    
    # Тестовое сообщение с шахедом на Миколаївку на Сумщині
    test_message = "1 шахед на Миколаївку на Сумщині"
    
    result = process_message(test_message, "test_001", "2024-01-01 12:00:00", "test_channel")
    
    print(f"Результат обработки сообщения: '{test_message}'")
    print(f"Количество результатов: {len(result)}")
    
    if result:
        for i, threat in enumerate(result):
            print(f"\nУгроза {i+1}:")
            print(f"  Место: {threat.get('place', 'Неизвестно')}")
            print(f"  Координаты: ({threat.get('lat', 'Н/Д')}, {threat.get('lng', 'Н/Д')})")
            print(f"  Тип: {threat.get('type', 'Неизвестно')}")
            print(f"  Количество: {threat.get('count', 'Н/Д')}")
            
            # Проверяем, что координаты соответствуют Сумской области
            lat = threat.get('lat')
            lng = threat.get('lng')
            
            if lat and lng:
                # Координаты Миколаївки в Сумской области: (51.5667, 34.1333)
                # Допустимое отклонение для проверки
                expected_lat = 51.5667
                expected_lng = 34.1333
                tolerance = 0.1
                
                if (abs(lat - expected_lat) < tolerance and 
                    abs(lng - expected_lng) < tolerance):
                    print(f"  ✅ Правильные координаты для Сумской области!")
                else:
                    print(f"  ❌ Неправильные координаты! Ожидались: ({expected_lat}, {expected_lng})")
                    print(f"     Возможно, показывается Миколаївка в Миколаївській області: (47.0667, 31.8333)")
    else:
        print("Не найдено угроз в сообщении")

if __name__ == "__main__":
    test_mykolaivka_sumy()
