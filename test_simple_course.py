#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# Test the current pattern
text = "БпЛА курсом на н.п.батурин"
current_pattern = re.compile(r'бпла.*?курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
new_pattern = re.compile(r'бпла.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)

print("Тестування парсера курсу:")
print(f"Текст: '{text}'")
print()

current_match = current_pattern.search(text)
print(f"Поточний pattern: {'✅' if current_match else '❌'}")
if current_match:
    print(f"  Знайдено: '{current_match.group(1)}'")

new_match = new_pattern.search(text)
print(f"Новий pattern: {'✅' if new_match else '❌'}")
if new_match:
    print(f"  Знайдено: '{new_match.group(1)}'")
