#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

def test_trajectory_regex():
    """Test trajectory regex patterns."""
    text = "2 шахеди з донеччини на харківщину"
    
    patterns = [
        # Current pattern
        r'\b(\d+)?\s*шахед[іївыиє]*\s+з\s+([а-яіїєґ]+щин[ауиі])\s+на\s+([а-яіїєґ/]+щин[ауиі])',
        # Without word boundary
        r'(\d+)?\s*шахед[іївыиє]*\s+з\s+([а-яіїєґ]+щин[ауиі])\s+на\s+([а-яіїєґ/]+щин[ауиі])',
        # With 'и' explicitly
        r'(\d+)?\s*шахеди\s+з\s+([а-яіїєґ]+щин[ауиі])\s+на\s+([а-яіїєґ/]+щин[ауиі])',
        # Flexible pattern
        r'(\d+)?\s*шахед\w*\s+з\s+([а-яіїєґ]+щин[ауиі])\s+на\s+([а-яіїєґ/]+щин[ауиі])',
    ]
    
    print(f"Testing text: '{text}'")
    print(f"Text chars: {[c for c in text]}")
    
    for i, pattern in enumerate(patterns, 1):
        print(f"\n--- Pattern {i} ---")
        print(f"Pattern: {pattern}")
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            print(f"✅ MATCH: {match.groups()}")
        else:
            print("❌ No match")

if __name__ == "__main__":
    test_trajectory_regex()
