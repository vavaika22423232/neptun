#!/usr/bin/env python3
import sys
sys.path.append('.')
import app

# Test cases for district threats
test_cases = [
    {
        'name': 'Сумський район КАБ',
        'message': '💣 Сумський район (Сумська обл.)\nЗагроза застосування КАБів. Негайно прямуйте в укриття!',
        'expected_place': 'Сумський район'
    },
    {
        'name': 'Конотопський район БПЛА', 
        'message': '🛸 Конотопський район (Сумська обл.)\nКурс БПЛА. Прямуйте в укриття!',
        'expected_place': 'Конотопський район'
    },
    {
        'name': 'Суми город (для сравнения)',
        'message': '💣 Суми (Сумська обл.)\nЗагроза застосування КАБів.',
        'expected_place': 'Суми'
    }
]

def test_district_processing():
    for test in test_cases:
        print(f"\n=== {test['name'].upper()} ===")
        print(f"Сообщение: {test['message']}")
        
        result = app.process_message(test['message'], f"test_{test['name']}", "2025-01-01 12:00:00", "test_channel")
        
        if result and len(result) > 0:
            place = result[0].get('place', '')
            coords = (result[0].get('lat'), result[0].get('lng'))
            threat_type = result[0].get('threat_type', '')
            
            print(f"Место: {place}")
            print(f"Координаты: {coords}")
            print(f"Тип угрозы: {threat_type}")
            
            # Check if district coordinates are different from city center
            if 'район' in test['expected_place'].lower():
                sumy_coords = (50.9077, 34.7981)  # City center coordinates
                if coords != sumy_coords:
                    print("✅ SUCCESS: District coordinates differ from city center!")
                else:
                    print("❌ FAILED: District coordinates same as city center!")
            else:
                print("ℹ️  City center test (reference)")
        else:
            print("❌ FAILED: No result returned!")

if __name__ == "__main__":
    test_district_processing()
