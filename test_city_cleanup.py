#!/usr/bin/env python3

import re


def test_resolve(raw):
    cand = raw.strip().lower()
    cand = re.sub(r'["""«»\(\)\[\]]','', cand)

    trailing_patterns = [
        r'\s+по\s+межі\s+з\s+.*$',
        r'\s+на\s+межі\s+з\s+.*$',
        r'\s+в\s+районі\s+.*$',
        r'\s+біля\s+кордону\s+.*$',
        r'\s+на\s+околицях\s+.*$',
        r'\s+поблизу\s+.*$',
    ]
    for pattern in trailing_patterns:
        cand = re.sub(pattern, '', cand).strip()

    cand = re.sub(r'\s+',' ', cand)
    return cand

# Test extraction
pat_simple_na = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)

test_cases = [
    'БпЛА на Канів по межі з Київщиною',
    'БпЛА на Канів',
    'БпЛА курсом на Канів по межі з Київщиною'
]

for test_text in test_cases:
    print(f'\nTest: "{test_text}"')
    m = pat_simple_na.search(test_text.lower())
    if m:
        city_raw = m.group(2)
        print(f'  Extracted: "{city_raw}"')
        cleaned = test_resolve(city_raw)
        print(f'  Cleaned: "{cleaned}"')
    else:
        print('  No match')
