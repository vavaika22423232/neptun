#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test with debug output to see what parsers are triggered
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_with_debug():
    print("=== Тестування з debug логами ===")
    
    test_message = """чернігівщина (новгород-сіверський р-н) та одещина - загроза застосування ворогом ударних бпла. | одещина - шахеди на вилково
ㅤ | група 8х бпла у напрямку ізмаїльського району одещини, вилкове."""
    
    print(f"Повідомлення:")
    print(repr(test_message))
    print()
    
    # Check shahed count for early multi-line processing
    text_lines = test_message.split('\n')
    shahed_region_lines = [line for line in text_lines if 
                          ('шахед' in line.lower() or 'shahed' in line.lower()) and 
                          ('щина' in line.lower() or 'щину' in line.lower() or 'щині' in line.lower())]
    
    print(f"Shahed+region лінії: {len(shahed_region_lines)}")
    for i, line in enumerate(shahed_region_lines, 1):
        print(f"  {i}: {repr(line)}")
    
    print(f"\nТест region-district pattern:")
    import re
    region_district_pattern = re.compile(r'([а-яіїєґ]+щин[ауи]?)\s*\(\s*([а-яіїєґ\'\-\s]+)\s+р[-\s]*н\)', re.IGNORECASE)
    region_district_match = region_district_pattern.search(test_message)
    
    if region_district_match:
        print(f"✅ Pattern знайдений: {region_district_match.groups()}")
    else:
        print(f"❌ Pattern НЕ знайдений")

if __name__ == "__main__":
    test_with_debug()
