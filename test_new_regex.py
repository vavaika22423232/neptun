#!/usr/bin/env python3

import re

def test_new_regex():
    """Test the new regex pattern for district processing"""
    
    test_message = """11 шахедів через Очаків на Березівський район Одещини"""
    
    print("=== Testing New District Pattern ===")
    print(f"Message: {test_message}")
    print()
    
    # Test new pattern
    pattern = r'([A-Za-zА-Яа-яЇїІіЄєҐґ\'\-]{4,})\s+район\s+([\w\']+(?:щини|щину|области|області))'
    match = re.search(pattern, test_message)
    
    if match:
        print("✅ New pattern MATCHED!")
        print(f"Group 1 (raion_token): '{match.group(1)}'")
        print(f"Group 2 (oblast): '{match.group(2)}'")
        
        raion_token = match.group(1).strip().lower()
        print(f"Raion token lowercase: '{raion_token}'")
        
        # Test normalization
        raion_base = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_token)
        print(f"Normalized raion_base: '{raion_base}'")
    else:
        print("❌ New pattern DID NOT MATCH")
        
        # Test simpler version
        simple_pattern = r'([A-Za-zА-Яа-яЇїІіЄєҐґ\'\-]{4,})\s+район\s+(\w+щини)'
        simple_match = re.search(simple_pattern, test_message)
        
        if simple_match:
            print("✅ Simpler pattern matched!")
            print(f"Group 1: '{simple_match.group(1)}'")
            print(f"Group 2: '{simple_match.group(2)}'")
        else:
            print("❌ Even simpler pattern failed")

if __name__ == "__main__":
    test_new_regex()
