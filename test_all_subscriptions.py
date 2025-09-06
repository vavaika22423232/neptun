#!/usr/bin/env python3
import sys
sys.path.append('.')
import app

# Test 1: Air alarm with subscription
test_message_1 = """🚨Повітряна тривога

В зв'язку з активністю ворожої авіації, повітряна тривога оголошена в наступних областях:

🔺Харківська область
🔺Полтавська область


➡Підписатися
@ukraine_in_alarm_official_bot"""

# Test 2: Regular threat with subscription
test_message_2 = """🛸 БПЛА курс Дніпропетровська область

Курс: Дніпро
Напрямок: зх-сх

➡Підписатися
@ukraine_alerts"""

# Test 3: Multiple threats with subscription
test_message_3 = """🛬🛸 Тактична авіація + БПЛА

Запорізька область - загроза КАБ
Одеська область - курс БПЛА

➡Підписатися на канал"""

def test_subscription_removal():
    tests = [
        ("Air alarm", test_message_1),
        ("Regular БПЛА", test_message_2), 
        ("Multiple threats", test_message_3)
    ]
    
    for test_name, msg in tests:
        print(f"\n=== {test_name.upper()} TEST ===")
        print("ORIGINAL:")
        print(msg)
        
        result = app.process_message(msg, f"test_{test_name}", "2025-01-01 12:00:00", "test_channel")
        
        print("\nPROCESSED:")
        if result and len(result) > 0:
            clean_text = result[0].get('text', '')
            print(clean_text)
            
            # Check if subscription was removed
            if '➡' in clean_text or 'підписатися' in clean_text.lower() or 'підписатися' in clean_text.lower():
                print("❌ FAILED: Subscription text still present!")
            else:
                print("✅ SUCCESS: Subscription text removed!")
        else:
            print("❌ FAILED: No result returned!")

if __name__ == "__main__":
    test_subscription_removal()
