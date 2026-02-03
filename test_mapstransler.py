#!/usr/bin/env python3
"""Test mapstransler pattern matching"""
import re

# Test messages
test_msgs = [
    'БПЛА Глобине (Полтавська обл.)',
    'БПЛА Просяна (Дніпропетровська обл.)',
    'БПЛА Умань (Черкаська обл.)',
    'БПЛА Вінниця (Вінницька обл.)',
    '2х БПЛА Барвінкове (Харківська обл.)',
    'КАБ Вовчанськ (Харківська обл.)',
]

threat_type_pattern = r'(?:БПЛА|КАБ|Ракета|Ракети|Шахед|Дрон|Дрони)'

# Pattern 1: with count
p1 = rf'^[^\w]*(\d+)[xх×]?\s*{threat_type_pattern}\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)'

# Pattern 2: without count  
p2 = rf'^[^\w]*{threat_type_pattern}\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)'

print('=== Testing mapstransler patterns ===\n')
for msg in test_msgs:
    print(f"Message: '{msg}'")
    print(f"  First 5 chars hex: {[hex(ord(c)) for c in msg[:5]]}")
    
    m1 = re.search(p1, msg, re.IGNORECASE)
    m2 = re.search(p2, msg, re.IGNORECASE)
    
    if m1:
        print(f"  Pattern1 MATCH: count={m1.group(1)}, city='{m1.group(2).strip()}', oblast='{m1.group(3)}'")
    elif m2:
        print(f"  Pattern2 MATCH: city='{m2.group(1).strip()}', oblast='{m2.group(2)}'")
    else:
        print("  NO MATCH!")
        
        # Try without ^ anchor
        p2_no_anchor = rf'{threat_type_pattern}\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)'
        m3 = re.search(p2_no_anchor, msg, re.IGNORECASE)
        if m3:
            print(f"  WITHOUT ^ anchor: city='{m3.group(1).strip()}', oblast='{m3.group(2)}'")
    print()
