#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def test_regional_processing():
    line = "3. БпЛА на південному заході Дніпропетровщини, курс - південно-західний/південно-східний."
    
    print("=== Тестування регіональної обробки ===")
    print(f"Рядок: '{line}'")
    
    line_lower = line.lower()
    print(f"Нижній регістр: '{line_lower}'")
    
    # Test conditions
    has_bpla = 'бпла' in line_lower
    has_region = any(region in line_lower for region in ['щини', 'щину', 'одещина', 'чернігівщина', 'дніпропетровщини'])
    
    print(f"Має 'бпла': {has_bpla}")
    print(f"Має регіон: {has_region}")
    print(f"Регіони в рядку: {[region for region in ['щини', 'щину', 'одещина', 'чернігівщина', 'дніпропетровщини'] if region in line_lower]}")
    
    # Test regex pattern
    region_match = re.search(r'на\s+([\w\-\s/]+?)\s+([а-яіїєґ]+щини|[а-яіїєґ]+щину|дніпропетровщини|одещини|чернігівщини)', line_lower)
    
    print(f"Regex match: {bool(region_match)}")
    if region_match:
        direction = region_match.group(1).strip()
        region_raw = region_match.group(2).strip()
        print(f"  Direction: '{direction}'")
        print(f"  Region: '{region_raw}'")
    else:
        print("  Regex не знайшов match")
        
        # Test alternative patterns
        print("\nТестування альтернативних patterns:")
        
        # Pattern 1: більш гнучкий
        alt1 = re.search(r'на\s+([^,]+?)\s+(дніпропетровщини|одещини|чернігівщини)', line_lower)
        print(f"Alt1: {bool(alt1)}")
        if alt1:
            print(f"  Direction: '{alt1.group(1).strip()}'")
            print(f"  Region: '{alt1.group(2).strip()}'")
        
        # Pattern 2: шукаємо "дніпропетровщини" напряму
        alt2 = re.search(r'дніпропетровщини', line_lower)
        print(f"Alt2 (direct region): {bool(alt2)}")
        
        # Pattern 3: весь текст
        alt3 = re.search(r'на\s+(південному\s+заході)\s+(дніпропетровщини)', line_lower)
        print(f"Alt3 (specific): {bool(alt3)}")
        if alt3:
            print(f"  Direction: '{alt3.group(1).strip()}'")
            print(f"  Region: '{alt3.group(2).strip()}'")

if __name__ == "__main__":
    test_regional_processing()
