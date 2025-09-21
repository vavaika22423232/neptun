#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

def test_step_by_step():
    """Test trajectory step by step."""
    text = "2 шахеди з донеччини на харківщину"
    
    print(f"Original: '{text}'")
    print(f"Length: {len(text)}")
    
    # Test each part
    parts = [
        ("Number", r"(\d+)"),
        ("Space", r"\s+"),
        ("Shahed word", r"шахеди"),
        ("Space z", r"\s+з\s+"),
        ("Region 1", r"донеччини"),
        ("Space na", r"\s+на\s+"),
        ("Region 2", r"харківщину"),
    ]
    
    for name, pattern in parts:
        match = re.search(pattern, text, re.IGNORECASE)
        print(f"{name}: {pattern} -> {'✅' if match else '❌'}")
        if match:
            print(f"  Match: '{match.group()}'")
    
    # Test combined patterns
    print("\n--- COMBINED TESTS ---")
    
    simple_patterns = [
        r"шахеди з",
        r"з донеччини",
        r"на харківщину",
        r"шахеди з донеччини",
        r"з донеччини на харківщину",
        r"шахеди з донеччини на харківщину",
        r"2 шахеди з донеччини на харківщину",
    ]
    
    for pattern in simple_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        print(f"'{pattern}' -> {'✅' if match else '❌'}")

if __name__ == "__main__":
    test_step_by_step()
