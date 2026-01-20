#!/usr/bin/env python3
import re

test_msgs = [
    'БПЛА Славутич курсом на Київщина',
    'БПЛА Борисполь курсом на Київ',
    'БпЛА Ніжин курсом на Чернігів',
    'БПЛА Суми курсом на захід',
    'бпла славутич курсом на київщина.',
    'БПЛА Прилуки курсом на Київщина!',
]

pat = r"бпла\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`]{3,30})\s+курсом\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)"

print("Testing pattern for 'БПЛА [city] курсом на [target]':\n")

for msg in test_msgs:
    m = re.search(pat, msg.lower(), re.IGNORECASE)
    if m:
        print(f'✅ "{msg}"')
        print(f'   CITY (marker location): {m.group(1)}')
        print(f'   TARGET (destination): {m.group(2)}')
    else:
        print(f'❌ "{msg}" - NO MATCH')
    print()
