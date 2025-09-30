#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест для проблемы с БпЛА на юге Чернигивщины
"""

def test_chernigiv_direction_issue():
    """
    Тестирует сообщение: "БпЛА на півдні Чернігівщини, рухаються на південь (Київщина)"
    Проблема: отображается в самом Киеве вместо Чернигивщины
    """
    
    test_message = "БпЛА на півдні Чернігівщини, рухаються на південь (Київщина)"
    
    print(f"Тестовое сообщение: {test_message}")
    print("="*50)
    
    # Симулируем обработку
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from app import process_message
        
        # Тестируем извлечение маркеров
        result = process_message(test_message, "test_mid", "2025-09-29", "test_channel")
        markers = result if isinstance(result, list) else []
        
        print(f"Найдено маркеров: {len(markers)}")
        
        for i, marker in enumerate(markers, 1):
            print(f"\nМаркер {i}:")
            print(f"  Место: {marker.get('place', 'N/A')}")
            print(f"  Координаты: {marker.get('lat', 'N/A')}, {marker.get('lng', 'N/A')}")
            print(f"  Тип угрозы: {marker.get('threat_type', 'N/A')}")
            print(f"  Источник: {marker.get('source_match', 'N/A')}")
            print(f"  Текст: {marker.get('text', 'N/A')}")
            
        # Проверяем, есть ли маркер в Киеве
        kiev_coords = (50.4501, 30.5234)  # Примерные координаты Киева
        chernigiv_coords = (51.4982, 31.2893)  # Примерные координаты Чернигова
        
        for marker in markers:
            lat = marker.get('lat')
            lng = marker.get('lng')
            
            if lat and lng:
                # Проверяем расстояние до Киева
                kiev_distance = ((lat - kiev_coords[0])**2 + (lng - kiev_coords[1])**2)**0.5
                chernigiv_distance = ((lat - chernigiv_coords[0])**2 + (lng - chernigiv_coords[1])**2)**0.5
                
                print(f"\n  Расстояние до Киева: {kiev_distance:.4f}")
                print(f"  Расстояние до Чернигова: {chernigiv_distance:.4f}")
                
                if kiev_distance < 0.1:
                    print("  ❌ ПРОБЛЕМА: Маркер в Киеве!")
                elif chernigiv_distance < 0.5:
                    print("  ✅ ОК: Маркер в районе Чернигова")
                else:
                    print("  ⚠️  Маркер в другом месте")
        
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
    except Exception as e:
        print(f"Ошибка выполнения: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chernigiv_direction_issue()
