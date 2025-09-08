#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test what remains after district pattern removal
"""

import re

def test_pattern_removal():
    original_text = """чернігівщина (новгород-сіверський р-н) та одещина - загроза застосування ворогом ударних бпла. | одещина - шахеди на вилково
ㅤ | група 8х бпла у напрямку ізмаїльського району одещини, вилкове."""
    
    print("Оригінальний текст:")
    print(repr(original_text))
    
    # Test our pattern
    region_district_pattern = re.compile(r'([а-яіїєґ]+щин[ауи]?)\s*\(\s*([а-яіїєґ\'\-\s]+)\s+р[-\s]*н\)', re.IGNORECASE)
    match = region_district_pattern.search(original_text.lower())
    
    if match:
        print(f"\nЗнайдений pattern: {match.groups()}")
        
        # Remove the pattern
        remaining_text = region_district_pattern.sub('', original_text)
        print(f"\nЗалишається після видалення pattern:")
        print(repr(remaining_text))
        
        # Clean up the remaining text
        remaining_cleaned = remaining_text.strip()
        print(f"\nОчищений залишок:")
        print(repr(remaining_cleaned))
    else:
        print("\nPattern не знайдений")

if __name__ == "__main__":
    test_pattern_removal()
