#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестируем исправленную функцию detect_direction
"""

test_message = "бпла на півночі тернопільщини ➡️ курсом на південно-західний напрямок."

print("Тестируем функцию detect_direction...")

def detect_direction(lower_txt: str):
    # Support full adjectives with endings (-ний / -ня / -ньому) by searching stems
    if 'північно-захід' in lower_txt or 'північно-західн' in lower_txt: return 'nw'
    if 'південно-захід' in lower_txt or 'південно-західн' in lower_txt: return 'sw'
    if 'північно-схід' in lower_txt or 'північно-східн' in lower_txt: return 'ne'
    if 'південно-схід' in lower_txt or 'південно-східн' in lower_txt: return 'se'
    # Single directions (allow stems 'північн', 'південн')
    import re
    if re.search(r'\bпівніч(?!о-с)(?:н\w*)?\b', lower_txt): return 'n'
    if re.search(r'\bпівденн?\w*\b', lower_txt): return 's'
    if re.search(r'\bсхідн?\w*\b', lower_txt): return 'e'
    if re.search(r'\bзахідн?\w*\b', lower_txt): return 'w'
    return None

direction = detect_direction(test_message.lower())
print(f"Сообщение: {test_message}")
print(f"Определенное направление: {direction}")

# Проверяем отдельные части
print("\nПроверяем части:")
print(f"'південно-західн' in text: {'південно-західн' in test_message.lower()}")
print(f"'північ' in text: {'північ' in test_message.lower()}")

# Ожидаем: должно определить 'sw' из-за "південно-західний напрямок"
# Но проблема в том, что "півночі" тоже присутствует и может быть найдено как 'n'
