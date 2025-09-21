#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

def test_correct_pattern():
    """Test correct trajectory pattern building."""
    text = "2 шахеди з донеччини на харківщину"
    
    print(f"Testing: '{text}'")
    
    # Build pattern step by step
    patterns = [
        # Basic
        r"2 шахеди з донеччини на харківщину",
        # With groups
        r"(2) (шахеди) з (донеччини) на (харківщину)",
        # With optional number
        r"(\d+)?\s*шахеди з донеччини на харківщину",
        # With region pattern
        r"(\d+)?\s*шахеди з ([а-яіїєґ]+щини) на ([а-яіїєґ]+щину)",
        # Final pattern
        r"(\d+)?\s*шахеди\s+з\s+([а-яіїєґ]+щини)\s+на\s+([а-яіїєґ]+щину)",
    ]
    
    for i, pattern in enumerate(patterns, 1):
        print(f"\n--- Pattern {i} ---")
        print(f"Pattern: {pattern}")
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            print(f"✅ MATCH: {match.groups()}")
        else:
            print("❌ No match")
    
    # The issue might be the ending pattern
    print(f"\n--- ENDING ANALYSIS ---")
    endings = ["щину", "щини", "щин[ауиі]"]
    for ending in endings:
        pattern = r"харків" + ending
        match = re.search(pattern, text, re.IGNORECASE)
        print(f"'{pattern}' on 'харківщину' -> {'✅' if match else '❌'}")

if __name__ == "__main__":
    test_correct_pattern()
