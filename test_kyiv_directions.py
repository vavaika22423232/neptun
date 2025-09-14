#!/usr/bin/env python3
import sys
sys.path.append('.')
from app import process_message

def test_kyiv_directional_logic():
    print("🔍 Тестируем улучшенную логику Киева...")
    
    # Тестовые сообщения с разными направлениями для Киева
    test_cases = [
        {
            'name': 'Курс из Чернигова на Киев',
            'message': '🔴 БпЛА курсом з Чернігова на Київ'
        },
        {
            'name': 'БпЛА на Киев с севера',
            'message': '🟥 БпЛА на Київ з північного напрямку'
        },
        {
            'name': 'Обычная угроза Киева',
            'message': '🟥 Тривога у Києві'
        },
        {
            'name': 'БпЛА курсом на Киев',
            'message': '🔴 БпЛА курсом на Київ'
        },
        {
            'name': 'БпЛА курс Житомир-Киев',
            'message': '🔴 2х БпЛА курс Житомир - Київ'
        }
    ]
    
    for test in test_cases:
        print(f"\n📋 Тест: {test['name']}")
        print(f"📝 Сообщение: {repr(test['message'])}")
        
        try:
            result = process_message(test['message'], "test_mid", "2024-09-14", "test_channel")
            
            if result and 'threats' in result:
                for threat in result['threats']:
                    city = threat.get('place', 'N/A')
                    coords = (threat.get('lat', 0), threat.get('lng', 0))
                    icon = threat.get('marker_icon', 'N/A')
                    source = threat.get('source_match', 'N/A')
                    direction = threat.get('direction_info', 'N/A')
                    
                    print(f"  ✅ Угроза: {city}")
                    print(f"      📍 Координаты: {coords}")
                    print(f"      🎯 Иконка: {icon}")
                    print(f"      🔗 Источник: {source}")
                    if direction != 'N/A':
                        print(f"      🧭 Направление: {direction}")
            else:
                print(f"  ❌ Угрозы не найдены или сообщение отфильтровано")
                
        except Exception as e:
            print(f"  💥 Ошибка: {e}")

if __name__ == "__main__":
    test_kyiv_directional_logic()
