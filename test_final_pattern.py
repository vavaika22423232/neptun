#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

def test_final_pattern():
    """Test final corrected trajectory pattern."""
    text = "2 шахеди з донеччини на харківщину"
    
    # Current pattern from app.py
    pattern = r'(\d+)?\s*шахед[іївыиє]*\s+з\s+([а-яіїєґ]+щин[ауиі])\s+на\s+([а-яіїєґ/]+щин[ауиіу])'
    
    print(f"Testing: '{text}'")
    print(f"Pattern: {pattern}")
    
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        print(f"✅ MATCH: {match.groups()}")
    else:
        print("❌ No match")
        
        # Debug each character class
        print("\n--- DEBUG ---")
        issues = [
            ("шахед[іївыиє]*", "шахеди"),
            ("[а-яіїєґ]+щин[ауиі]", "донеччини"),
            ("[а-яіїєґ/]+щин[ауиіу]", "харківщину"),
        ]
        
        for pattern_part, test_word in issues:
            test_match = re.search(pattern_part, test_word, re.IGNORECASE)
            print(f"'{pattern_part}' vs '{test_word}' -> {'✅' if test_match else '❌'}")

if __name__ == "__main__":
    test_final_pattern()
