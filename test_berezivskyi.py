#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import process_message, CITY_COORDS, RAION_FALLBACK
import math

def test_berezivskyi_message():
    """Test Berezivskyi district message processing"""
    
    test_message = """11 шахедів через Очаків на Березівський район Одещини
ㅤ
➡Підписатися"""
    
    print("=== Testing Berezivskyi District Message ===")
    print(f"Message: {test_message}")
    print()
    
    # Process the message
    result = process_message(test_message, 123, "test_channel", "test_channel")
    
    if result:
        print(f"Found {len(result)} markers:")
        for i, marker in enumerate(result):
            print(f"{i+1}. {marker['place']} at ({marker['lat']}, {marker['lng']}) - {marker['source_match']}")
            print(f"   Text: {marker['text'][:100]}...")
            print(f"   Threat type: {marker['threat_type']}")
            print()
        
        # Check coordinates
        print("=== Expected Results ===")
        print("Should create marker in Березівський район (Одещина), NOT in Одеса center")
        print()
        
        # Check RAION_FALLBACK for Berezivskyi
        berezivskyi_variants = []
        for key in RAION_FALLBACK.keys():
            if 'березів' in key or 'bereziv' in key:
                berezivskyi_variants.append((key, RAION_FALLBACK[key]))
        
        if berezivskyi_variants:
            print("Found Berezivskyi variants in RAION_FALLBACK:")
            for name, coords in berezivskyi_variants:
                print(f"  '{name}': {coords}")
        else:
            print("❌ NO Berezivskyi variants found in RAION_FALLBACK")
        
        # Check CITY_COORDS for Odesa
        if 'одеса' in CITY_COORDS:
            odesa_coords = CITY_COORDS['одеса']
            print(f"Одеса center coordinates: {odesa_coords}")
        
        # Calculate distances if we have results
        if result:
            marker = result[0]
            marker_lat, marker_lng = marker['lat'], marker['lng']
            
            if 'одеса' in CITY_COORDS:
                odesa_lat, odesa_lng = CITY_COORDS['одеса']
                odesa_distance = math.sqrt((marker_lat - odesa_lat)**2 + (marker_lng - odesa_lng)**2)
                print(f"Distance to Одеса center: {odesa_distance:.4f}")
                
                if odesa_distance < 0.5:
                    print("❌ FAILURE: Marker placed too close to Odesa center (should be in district)")
                else:
                    print("✅ SUCCESS: Marker placed away from Odesa center")
    else:
        print("❌ No markers found!")

def check_raion_processing():
    """Check if the district pattern should be caught"""
    
    test_message = """11 шахедів через Очаків на Березівський район Одещини"""
    
    print("\n=== Testing District Pattern Matching ===")
    
    import re
    
    # Test the district regex pattern
    pattern = r'([A-Za-zА-Яа-яЇїІіЄєҐґ\'\-]{4,})\s+район\s*\(([^)]*обл[^)]*)\)'
    match = re.search(pattern, test_message)
    
    if match:
        print(f"✅ District pattern matched: '{match.group(1)}' район in '{match.group(2)}'")
    else:
        print("❌ District pattern did not match")
        
        # Try simpler pattern without parentheses
        simple_pattern = r'([A-Za-zА-Яа-яЇїІіЄєҐґ\'\-]{4,})\s+район'
        simple_match = re.search(simple_pattern, test_message)
        
        if simple_match:
            print(f"✅ Simple district pattern matched: '{simple_match.group(1)}' район")
            raion_name = simple_match.group(1).lower()
            print(f"Raion name: '{raion_name}'")
            
            # Check normalization
            raion_base = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_name)
            print(f"Normalized: '{raion_base}'")
            
            if raion_base in RAION_FALLBACK:
                print(f"✅ Found in RAION_FALLBACK: {RAION_FALLBACK[raion_base]}")
            else:
                print(f"❌ Not found in RAION_FALLBACK")
                # Show similar keys
                similar = [k for k in RAION_FALLBACK.keys() if 'березів' in k]
                print(f"Similar keys: {similar}")
        else:
            print("❌ Even simple district pattern did not match")

if __name__ == "__main__":
    test_berezivskyi_message()
    check_raion_processing()
