#!/usr/bin/env python3

import re

def test_detailed_regex():
    """Detailed test to understand why regex is not capturing full word"""
    
    test_message = """🛸 Куп'янський район (Харківська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""
    
    print("=== Detailed Regex Analysis ===")
    print(f"Message: {test_message}")
    print()
    
    # Test character by character
    word = "Куп'янський"
    print(f"Testing word: '{word}'")
    for i, char in enumerate(word):
        print(f"  {i}: '{char}' (ord: {ord(char)})")
    print()
    
    # Test different regex patterns
    patterns = [
        r'([A-Za-zА-Яа-яЏїІіЄєҐґ\'\-]{4,})\s+район',  # Updated pattern
        r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{4,})\s+район',   # Original pattern
        r'([^🛸\s]+)\s+район',                        # Simpler pattern
        r'(\S+)\s+район',                             # Even simpler
        r'(.*?)\s+район',                             # Greedy
    ]
    
    for i, pattern in enumerate(patterns):
        print(f"Pattern {i+1}: {pattern}")
        match = re.search(pattern, test_message)
        if match:
            print(f"  ✅ Match: '{match.group(1)}'")
        else:
            print(f"  ❌ No match")
        print()
    
    # Check if there's something invisible in the string
    print("Hex dump of first line:")
    first_line = test_message.split('\n')[0]
    print(' '.join(f'{ord(c):02x}' for c in first_line))
    print()
    
    # Try to find the exact word boundaries
    print("All matches for word boundaries:")
    word_pattern = r'\b(\w+)\b'
    for match in re.finditer(word_pattern, test_message):
        print(f"  Word: '{match.group(1)}'")

if __name__ == "__main__":
    test_detailed_regex()
