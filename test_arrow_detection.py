#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# Test arrow detection with city names
test_cases = [
    ('Дніпропетровщина: БпЛА ➡️', False, 'No city after arrow'),
    ('Дніпропетровщина: БпЛА ➡️ у напрямку Павлограда', True, 'City after arrow'),
    ('Черкащина: БпЛА ➡️ у бік Канева', True, 'City after arrow'),
    ('БпЛА ➡️ [link](http://...)', False, 'Only link after arrow'),
    ('БпЛА ➡️ ㅤ', False, 'Only whitespace emoji after arrow'),
]

print("Testing arrow + city detection:\n")
for ln, expected, description in test_cases:
    ln_lower = ln.lower()
    
    # Check basic directional patterns
    has_directional_pattern = any(pattern in ln_lower for pattern in [
        'курсом на', 'курс на', 'напрямок на', 'напрямку на', 
        'ціль на', 'у напрямку', 'у бік', 'в бік', 'через', 'повз',
        'маневрує в районі', 'в районі', 'бпла на ', 'дрон на '
    ])
    
    # Check for emoji arrows BUT only if there's actual text (city name) after the arrow
    if '➡' in ln and not has_directional_pattern:
        # Extract text after arrow to see if there's a city name
        arrow_match = re.search(r'➡[️\s]*(.{3,})', ln)
        if arrow_match:
            text_after_arrow = arrow_match.group(1).strip().strip('ㅤ️ ').strip()
            # If there's meaningful text after arrow (not just punctuation/links), treat as directional
            if text_after_arrow and len(text_after_arrow) > 1 and not text_after_arrow.startswith(('http', '[', '**', '➡')):
                has_directional_pattern = True
    
    result = '✓' if has_directional_pattern == expected else '✗'
    print(f'{result} "{ln}"')
    print(f'   Expected: {expected}, Got: {has_directional_pattern} ({description})\n')
