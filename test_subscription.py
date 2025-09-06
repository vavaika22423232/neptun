#!/usr/bin/env python3
import app

test_message = """🚨Повітряна тривога

В зв'язку з активністю ворожої авіації, повітряна тривога оголошена в наступних областях:

🔺Харківська область
🔺Полтавська область


➡Підписатися
@ukraine_in_alarm_official_bot"""

print("=== ORIGINAL MESSAGE ===")
print(repr(test_message))
print("\n=== PROCESSED RESULT ===")
result = app.process_message(test_message, "test_id", "2025-01-01 12:00:00", "test_channel")
print(repr(result))

print("\n=== TEXT IN RESULT ===")
if result and len(result) > 0:
    print(f"Text: {repr(result[0].get('text', ''))}")
