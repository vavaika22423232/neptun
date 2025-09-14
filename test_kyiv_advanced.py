#!/usr/bin/env python3
import sys
sys.path.append('.')
from app import process_message

def test_kyiv_with_directions():
    print("🔍 Тестируем направления для Киева...")
    
    # Тестовые сообщения с направлениями
    test_cases = [
        'БпЛА на Київ з півночі',
        'БпЛА на Київ з півдня', 
        'БпЛА на Київ зі сходу',
        'БпЛА на Київ із заходу',
        'Чернігів - БпЛА на Київ',
        'з Житомира БпЛА на Київ',
        '🔴 БпЛА курсом з Чернігова на Київ',
        '🔴 БпЛА курсом з Житомира на Київ',
    ]
    
    for msg in test_cases:
        print(f"\n📝 Тест: {repr(msg)}")
        
        try:
            result = process_message(msg, "test_mid", "2024-09-14", "test_channel")
            
            if result and 'threats' in result and result['threats']:
                for threat in result['threats']:
                    city = threat.get('place', 'N/A')
                    coords = (threat.get('lat', 0), threat.get('lng', 0))
                    source = threat.get('source_match', 'N/A')
                    direction = threat.get('direction_info')
                    
                    print(f"  ✅ Угроза: {city}")
                    print(f"      📍 Координаты: {coords}")
                    print(f"      🔗 Источник: {source}")
                    if direction:
                        print(f"      🧭 Направление: {direction}")
                    
                    # Проверяем, если это Киев и координаты не стандартные
                    kyiv_center = (50.4501, 30.5234)
                    if 'київ' in city.lower() and coords != kyiv_center:
                        print(f"      🎯 ОТЛИЧНО! Координаты смещены от центра Киева")
                        print(f"      🔄 Смещение: lat {coords[0] - kyiv_center[0]:.4f}, lng {coords[1] - kyiv_center[1]:.4f}")
            else:
                print(f"  ❌ Угрозы не найдены")
                print(f"      Result: {result}")
                
        except Exception as e:
            print(f"  💥 Ошибка: {e}")

if __name__ == "__main__":
    test_kyiv_with_directions()
