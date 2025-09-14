#!/usr/bin/env python3
import sys
sys.path.append('.')
from app import process_message

def test_simple_kyiv():
    print("🔍 Тестируем простые угрозы Киева...")
    
    # Тестовые сообщения
    test_cases = [
        '🟥 КИЇВ',
        '🟥 Повітряна тривога в Києві',
        'БпЛА на Київ',
        'КИЇВ - до вас БпЛА'
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
            else:
                print(f"  ❌ Угрозы не найдены")
                print(f"      Result: {result}")
                
        except Exception as e:
            print(f"  💥 Ошибка: {e}")

if __name__ == "__main__":
    test_simple_kyiv()
