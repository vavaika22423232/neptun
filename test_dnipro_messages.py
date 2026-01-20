#!/usr/bin/env python3

import re

# Patterns from app.py
pat_count_course = re.compile(
    r'(\d+)х?\s+бпла(?:\s+пролетіли)?\s+(?:[а-яґєії\s]+\s+)?курсом\s+на\s+([а-яґєії]+)',
    re.IGNORECASE | re.UNICODE
)

pat_course = re.compile(
    r'бпла(?:\s+пролетіли)?\s+(?:[а-яґєії\s]+\s+)?курсом\s+на\s+([а-яґєії]+)',
    re.IGNORECASE | re.UNICODE
)

pat_area = re.compile(
    r'(?:(\d+)х?\s+)?бпла\s+в\s+районі\s+([а-яґєії]+)',
    re.IGNORECASE | re.UNICODE
)

pat_napramku = re.compile(
    r'(?:(\d+)х?\s+)?бпла\s+в\s+напрямку\s+([а-яґєії]+)',
    re.IGNORECASE | re.UNICODE
)

pat_simple_na = re.compile(
    r'(?:(\d+)х?\s+)?бпла\s+на\s+([а-яґєії]+)',
    re.IGNORECASE | re.UNICODE
)

pat_vik = re.compile(
    r'(?:(\d+)х?\s+)?бпла\s+в\s+бік\s+([а-яґєії]+)(?=\s+з\s+|[,\.\n;:!\?]|$)',
    re.IGNORECASE | re.UNICODE
)

pat_complex_napramku = re.compile(
    r'(?:(\d+)х?\s+)?бпла\s+(?:на|через)\s+([а-яґєії]+)\s+в\s+напрямку\s+([а-яґєії]+)',
    re.IGNORECASE | re.UNICODE
)

pat_vid_do = re.compile(
    r'(?:(\d+)х?\s+)?бпла\s+від\s+([а-яґєії]+)\s+до\s+([а-яґєії]+)',
    re.IGNORECASE | re.UNICODE
)

pat_okolytsi = re.compile(
    r'(?:(\d+)х?\s+)?бпла\s+на\s+околицях\s+([а-яґєії]+)',
    re.IGNORECASE | re.UNICODE
)

pat_napramku_ta = re.compile(
    r'(?:(\d+)х?\s+)?бпла\s+в\s+напрямку\s+([а-яґєії]+)\s+та\s+([а-яґєії]+)',
    re.IGNORECASE | re.UNICODE
)

# Pattern for "в секторі"
pat_sektor = re.compile(
    r'(?:(\d+)х?\s+)?бпла\s+в\s+секторі\s+([а-яґєії]+)',
    re.IGNORECASE | re.UNICODE
)

messages = [
    "3х БпЛА курсом на Васильківку | дніпропетровщина:",
    "БпЛА курсом на Петропавлівку",
    "4х бпла в секторі павлоград.",
]

print("=" * 70)
print("TESTING DNIPRO AREA MESSAGES")
print("=" * 70)

for msg in messages:
    print(f"\n📝 Message: {msg}")
    print(f"   Lower: {msg.lower()}")

    # Check each pattern
    m1 = pat_count_course.search(msg.lower())
    if m1:
        print(f"   ✓ pat_count_course: count={m1.group(1)}, city='{m1.group(2)}'")

    m2 = pat_course.search(msg.lower())
    if m2:
        print(f"   ✓ pat_course: city='{m2.group(1)}'")

    m3 = pat_area.search(msg.lower())
    if m3:
        print(f"   ✓ pat_area: count={m3.group(1)}, city='{m3.group(2)}'")

    m4 = pat_napramku.search(msg.lower())
    if m4:
        print(f"   ✓ pat_napramku: count={m4.group(1)}, city='{m4.group(2)}'")

    m5 = pat_sektor.search(msg.lower())
    if m5:
        print(f"   ✓ pat_sektor: count={m5.group(1)}, city='{m5.group(2)}'")

    m6 = pat_simple_na.search(msg.lower())
    if m6:
        print(f"   ✓ pat_simple_na: count={m6.group(1)}, city='{m6.group(2)}'")

    if not any([m1, m2, m3, m4, m5, m6]):
        print("   ✗ No pattern matched")

print("\n" + "=" * 70)
