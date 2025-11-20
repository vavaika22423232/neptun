#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# Test patterns
pat_vik = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+(?:в|у)\s+бік\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)

test_cases = [
    'БпЛА ➡️ у бік Канева.',
    'БпЛА у бік Павлограда.',
    'БпЛА в бік Дніпра',
    '2 БпЛА в бік Харкова'
]

print("Testing 'у бік' pattern:")
for test in test_cases:
    print(f'\nTest: "{test}"')
    m = pat_vik.search(test.lower())
    if m:
        count = m.group(1)
        city = m.group(2)
        print(f'  ✓ Match! Count: {count or "1"}, City: "{city}"')
    else:
        print(f'  ✗ No match')

# Test directional pattern detection
print("\n\nTesting directional pattern detection:")
test_lines = [
    'Дніпропетровщина: БпЛА ➡️ у напрямку Павлограда',
    'Черкащина: БпЛА ➡️ у бік Канева',
    'БпЛА на Канів по межі з Київщиною',
]

for ln in test_lines:
    ln_lower = ln.lower()
    has_directional = any(pattern in ln_lower for pattern in [
        'курсом на', 'курс на', 'напрямок на', 'напрямку на', 
        'ціль на', 'у напрямку', 'у бік', 'в бік', 'через', 'повз',
        'маневрує в районі', 'в районі', 'бпла на ', 'дрон на '
    ]) or '➡' in ln
    
    print(f'\nLine: "{ln}"')
    print(f'  Has directional pattern: {has_directional}')
