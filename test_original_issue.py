#!/usr/bin/env python3
import sys
sys.path.append('.')
import app

# Test the original user message
original_message = """💣 Сумський район (Сумська обл.)
Загроза застосування КАБів. Негайно прямуйте в укриття!"""

print("=== ORIGINAL USER MESSAGE TEST ===")
print(f"Message: {original_message}")

result = app.process_message(original_message, "user_test", "2025-01-01 12:00:00", "test_channel")

if result and len(result) > 0:
    place = result[0].get('place', '')
    coords = (result[0].get('lat'), result[0].get('lng'))
    threat_type = result[0].get('threat_type', '')
    icon = result[0].get('marker_icon', '')
    
    print(f"Место: {place}")
    print(f"Координаты: {coords}")
    print(f"Тип угрозы: {threat_type}")
    print(f"Иконка: {icon}")
    
    # Check if coordinates are correct for district (not city center)
    sumy_city_coords = (50.9077, 34.7981)
    if coords != sumy_city_coords:
        print("✅ SUCCESS: Marker is NOT in Sumy city center!")
        print(f"✅ District coordinates: {coords}")
        print(f"ℹ️  City center would be: {sumy_city_coords}")
    else:
        print("❌ FAILED: Marker is still in Sumy city center!")
else:
    print("❌ FAILED: No result returned!")

print("\n=== VERIFICATION ===")
print("Before fix: Marker was in Sumy city center (50.9077, 34.7981)")
print("After fix: Marker should be in district area (different coordinates)")
print("This ensures КАБ threats to district are shown in district area, not city center.")
