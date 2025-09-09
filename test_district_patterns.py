#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def test_district_patterns():
    text = "вишгородський р-н київська обл.- загроза застосування ворогом ударних бпла. | 1 БпЛА на Київщину вектором на водосховище"
    
    print("=== Тестування district patterns ===")
    print(f"Текст: {text}")
    print()
    
    # Існуючий pattern з app.py
    existing_pattern = r'([а-яіїєґ]+щин[ауи]?)\s*\(\s*([а-яіїєґ\'\-\s]+)\s+р[-\s]*н\)'
    print(f"Існуючий pattern: {existing_pattern}")
    match = re.search(existing_pattern, text, re.IGNORECASE)
    print(f"Match: {bool(match)}")
    if match:
        print(f"  Groups: {match.groups()}")
    print()
    
    # Новий pattern для формату "район область"
    new_pattern = r'([а-яіїєґ\'\-\s]+)\s+р[-\s]*н\s+([а-яіїєґ]+щин[ауи]?|київська|харківська|одеська)'
    print(f"Новий pattern (район область): {new_pattern}")
    match2 = re.search(new_pattern, text, re.IGNORECASE)
    print(f"Match: {bool(match2)}")
    if match2:
        district, region = match2.groups()
        print(f"  District: '{district.strip()}'")
        print(f"  Region: '{region.strip()}'")
    print()
    
    # Ще один варіант
    alt_pattern = r'([а-яіїєґ\'\-\s]+ський)\s+р[-\s]*н\s+([а-яіїєґ\'\-\s]+(?:обл\.?|область|щина))'
    print(f"Alt pattern: {alt_pattern}")
    match3 = re.search(alt_pattern, text, re.IGNORECASE)
    print(f"Match: {bool(match3)}")
    if match3:
        district, region = match3.groups()
        print(f"  District: '{district.strip()}'")
        print(f"  Region: '{region.strip()}'")

if __name__ == "__main__":
    test_district_patterns()
