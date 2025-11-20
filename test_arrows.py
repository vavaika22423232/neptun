#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

pat_vik = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+[➡️⬆️⬇️⬅️↗️↘️↙️↖️]*\s*(?:в|у)\s+бік\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)
pat_napramku = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+[➡️⬆️⬇️⬅️↗️↘️↙️↖️]*\s*(?:в|у)\s+напрямку\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)

tests = [
    'БпЛА ➡️ у бік Канева.',
    'БпЛА ➡️ у напрямку Павлограда',
    'Дніпропетровщина: БпЛА ➡️ у напрямку Павлограда.',
    'Черкащина: БпЛА ➡️ у бік Канева.',
]

for t in tests:
    print(f'\nTest: "{t}"')
    m1 = pat_vik.search(t)
    m2 = pat_napramku.search(t)
    if m1:
        print(f'  ✓ у бік: "{m1.group(2)}"')
    if m2:
        print(f'  ✓ у напрямку: "{m2.group(2)}"')
    if not m1 and not m2:
        print('  ✗ No match')
