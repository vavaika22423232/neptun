#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import process_message, CITY_COORDS
import math

def test_voznesensk_message():
    """Test Voznesensk direction message processing"""
    
    test_message = """11х бпла вздовж одещини у напрямку вознесенська, миколаївської області."""
    
    print("=== Testing Voznesensk Direction Message ===")
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
        print("Should create marker in Вознесенськ (Миколаївська обл.), NOT in Одеса")
        print()
        
        # Check for Voznesensk
        voznesensk_variants = []
        for city_name, coords in CITY_COORDS.items():
            if 'вознесенськ' in city_name.lower() or 'вознесенск' in city_name.lower():
                voznesensk_variants.append((city_name, coords))
        
        if voznesensk_variants:
            print("Found Voznesensk variants in CITY_COORDS:")
            for name, coords in voznesensk_variants:
                print(f"  '{name}': {coords}")
        else:
            print("❌ NO Voznesensk variants found in CITY_COORDS")
        
        # Check CITY_COORDS for Odesa
        if 'одеса' in CITY_COORDS:
            odesa_coords = CITY_COORDS['одеса']
            print(f"Одеса coordinates: {odesa_coords}")
        
        # Calculate distances if we have results
        if result and voznesensk_variants:
            marker = result[0]
            marker_lat, marker_lng = marker['lat'], marker['lng']
            
            # Distance to Voznesensk
            voz_name, (voz_lat, voz_lng) = voznesensk_variants[0]
            voz_distance = math.sqrt((marker_lat - voz_lat)**2 + (marker_lng - voz_lng)**2)
            print(f"Distance to {voz_name}: {voz_distance:.4f}")
            
            # Distance to Odesa
            if 'одеса' in CITY_COORDS:
                odesa_lat, odesa_lng = CITY_COORDS['одеса']
                odesa_distance = math.sqrt((marker_lat - odesa_lat)**2 + (marker_lng - odesa_lng)**2)
                print(f"Distance to Одеса: {odesa_distance:.4f}")
                
                if voz_distance < odesa_distance:
                    print("✅ SUCCESS: Marker placed closer to Voznesensk than to Odesa")
                else:
                    print("❌ FAILURE: Marker placed closer to Odesa than to Voznesensk")
    else:
        print("❌ No markers found!")

def test_direction_pattern():
    """Test if direction pattern is detected"""
    
    test_message = """11х бпла вздовж одещини у напрямку вознесенська, миколаївської області."""
    
    print("\n=== Testing Direction Pattern ===")
    
    import re
    
    # Test direction patterns
    patterns = [
        r'у\s+напрям[кт]у\s+([А-Яа-яЇїІіЄєҐґ\'\-\s]+?)(?:,\s*([^,]+області))?',
        r'напрям[кт]у\s+([А-Яа-яЇїІіЄєҐґ\'\-\s]+?)(?:,\s*([^,]+області))?',
        r'у\s+напрям[кт]у\s+([^,\.\n]{3,40})'
    ]
    
    for i, pattern in enumerate(patterns):
        print(f"Pattern {i+1}: {pattern}")
        match = re.search(pattern, test_message, re.IGNORECASE)
        if match:
            print(f"  ✅ Match: '{match.group(1)}'")
            if len(match.groups()) > 1 and match.group(2):
                print(f"  Oblast: '{match.group(2)}'")
        else:
            print(f"  ❌ No match")
        print()

if __name__ == "__main__":
    test_voznesensk_message()
    test_direction_pattern()
