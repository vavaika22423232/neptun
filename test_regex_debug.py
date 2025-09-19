#!/usr/bin/env python3

import sys
import os
import re
sys.path.append(os.path.dirname(__file__))

from app import RAION_FALLBACK

def test_regex_match():
    """Test the regex pattern that should catch Куп'янський район"""
    
    test_message = """🛸 Куп'янський район (Харківська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""
    
    print("=== Testing Regex Pattern ===")
    print(f"Message: {test_message}")
    print()
    
    # Test the exact regex from the code (FIXED VERSION)
    pattern = r'([A-Za-zА-Яа-яЇїІіЄєҐґ\'\-]{4,})\s+район\s*\(([^)]*обл[^)]*)\)'
    match = re.search(pattern, test_message)
    
    if match:
        print("✅ Regex MATCHED!")
        print(f"Group 1 (raion_token): '{match.group(1)}'")
        print(f"Group 2 (oblast): '{match.group(2)}'")
        
        raion_token = match.group(1).strip().lower()
        print(f"Raion token lowercase: '{raion_token}'")
        
        # Test normalization
        raion_base = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_token)
        print(f"Normalized raion_base: '{raion_base}'")
        
        # Check if in RAION_FALLBACK
        if raion_base in RAION_FALLBACK:
            coords = RAION_FALLBACK[raion_base]
            print(f"✅ Found in RAION_FALLBACK: {coords}")
        else:
            print(f"❌ NOT found in RAION_FALLBACK")
            print(f"Available keys with 'куп': {[k for k in RAION_FALLBACK.keys() if 'куп' in k]}")
            
    else:
        print("❌ Regex DID NOT MATCH")
        print("Testing individual components...")
        
        # Test if the first part matches
        part1_pattern = r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{4,})\s+район'
        part1_match = re.search(part1_pattern, test_message)
        if part1_match:
            print(f"✅ First part matches: '{part1_match.group(1)}'")
        else:
            print("❌ First part doesn't match")
        
        # Test if parentheses part matches
        part2_pattern = r'\(([^)]*обл[^)]*)\)'
        part2_match = re.search(part2_pattern, test_message)
        if part2_match:
            print(f"✅ Second part matches: '{part2_match.group(1)}'")
        else:
            print("❌ Second part doesn't match")

if __name__ == "__main__":
    test_regex_match()
