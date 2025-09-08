#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import re

def test_immediate_patterns():
    # Тестуємо лінії окремо з immediate multi-regional patterns
    lines = [
        "1. БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина);",
        "2. БпЛА на сході Чернігівщини курсом на н.п.Батурин.",
        "3. БпЛА на південному заході Дніпропетровщини, курс - південно-західний/південно-східний."
    ]
    
    # Updated patterns from app.py (fixed for "БпЛА ... курсом на")
    patterns = [
        # Pattern for markdown links: БпЛА курсом на [Бровари](link)
        r'(\d+)?[xх]?\s*бпла\s+(?:курсом?)?\s*(?:на|над)\s+\[([А-ЯІЇЄЁа-яіїєё\'\-\s]+?)\]',
        # Pattern for plain text: БпЛА курсом на Конотоп (with optional н.п. prefix and flexible БпЛА...курсом)
        r'(\d+)?[xх]?\s*бпла\s+.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([А-ЯІЇЄЁа-яіїєё\'\-\s]{3,50}?)(?=\s*(?:\n|$|[,\.\!\?;]))'
    ]
    
    # Also test bracket patterns
    bracket_patterns = [
        r'([А-Яа-яЇїІіЄєҐґ\'\-\s]{2,30}?)\s*\(([А-Яа-яЇїІіЄєҐґ\'\-\s]+(?:щина|ська\s+область))\)',
    ]
    
    print("=== Тестування immediate multi-regional patterns ===")
    
    for i, line in enumerate(lines, 1):
        print(f"\n--- Рядок {i}: ---")
        print(f"Текст: '{line}'")
        
        # Test course patterns
        print("Course patterns:")
        for j, pattern in enumerate(patterns, 1):
            matches = list(re.finditer(pattern, line, re.IGNORECASE))
            if matches:
                for match in matches:
                    groups = match.groups()
                    if len(groups) == 2:
                        count_str, city_raw = groups
                        print(f"  Pattern {j}: ✅ count='{count_str}' city='{city_raw}'")
                    else:
                        print(f"  Pattern {j}: ✅ city='{groups[0] if groups else 'none'}'")
            else:
                print(f"  Pattern {j}: ❌ no match")
        
        # Test bracket patterns
        print("Bracket patterns:")
        for j, pattern in enumerate(bracket_patterns, 1):
            matches = list(re.finditer(pattern, line, re.IGNORECASE))
            if matches:
                for match in matches:
                    city_raw, region_raw = match.groups()
                    print(f"  Bracket {j}: ✅ city='{city_raw}' region='{region_raw}'")
            else:
                print(f"  Bracket {j}: ❌ no match")

if __name__ == "__main__":
    test_immediate_patterns()
