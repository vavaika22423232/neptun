#!/usr/bin/env python3
import re
import requests
from app import process_message

# Тестируем фильтрацию "Підтримати канал"
test_message = """
🟥 КРИВИЙ РІГ
🟨 Попередження про можливу активність БпЛА в області

Підтримати канал: https://send.monobank.ua/jar/5mLLhfgKiX
"""

print("Тестируем сообщение с 'Підтримати канал':")
print(f"Исходный текст:\n{repr(test_message)}")
print("\nОбрабатываем сообщение...")

result = process_message(test_message.strip(), "test_mid", "2024-09-14", "test_channel")
print(f"\nРезультат: {result}")

if result is None:
    print("✓ Сообщение правильно отфильтровано как donation")
elif 'threats' in result and result['threats']:
    print("✓ Угрозы извлечены:")
    for threat in result['threats']:
        print(f"  - {threat['city']}: {threat['type']} ({threat.get('icon', 'N/A')})")
else:
    print("! Неожиданный результат")
