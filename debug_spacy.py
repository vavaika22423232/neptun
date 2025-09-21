#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug SpaCy processing specifically
"""

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

def debug_spacy_processing():
    """Debug SpaCy processing step by step"""
    
    from app import spacy_enhanced_geocoding, SPACY_AVAILABLE, CITY_COORDS
    
    print(f"SpaCy available: {SPACY_AVAILABLE}")
    
    test_message = "1 шахед на Миколаївку на Сумщині"
    
    print(f"\nDebugging message: {test_message}")
    
    if SPACY_AVAILABLE:
        results = spacy_enhanced_geocoding(test_message)
        
        print(f"\nSpaCy results: {len(results)} cities found")
        for i, result in enumerate(results, 1):
            print(f"  {i}. Name: '{result['name']}'")
            print(f"     Normalized: '{result['normalized']}'")
            print(f"     Coords: {result['coords']}")
            print(f"     Region: {result['region']}")
            print(f"     Case: {result.get('case', 'unknown')}")
            print(f"     Source: {result['source']}")
            print(f"     Confidence: {result['confidence']}")
            
            # Check if this normalized name exists in CITY_COORDS
            if result['normalized'] in CITY_COORDS:
                print(f"     ✅ Found in CITY_COORDS: {CITY_COORDS[result['normalized']]}")
            else:
                print(f"     ❌ NOT found in CITY_COORDS")
                
                # Try with region
                if result['region']:
                    region_key = f"{result['normalized']} {result['region']}"
                    if region_key in CITY_COORDS:
                        print(f"     ✅ Found with region '{region_key}': {CITY_COORDS[region_key]}")
                    else:
                        print(f"     ❌ NOT found with region key '{region_key}'")
            print()

def test_city_coords_lookup():
    """Test direct lookup in CITY_COORDS"""
    
    from app import CITY_COORDS, UA_CITY_NORMALIZE
    
    test_cities = [
        'миколаївка',
        'миколаївку', 
        'миколаївка сумщина',
        'миколаївку сумщина'
    ]
    
    print("=== Direct CITY_COORDS lookup ===")
    for city in test_cities:
        coords = CITY_COORDS.get(city)
        print(f"'{city}' -> {coords}")
    
    print("\n=== UA_CITY_NORMALIZE lookup ===")
    for city in test_cities:
        normalized = UA_CITY_NORMALIZE.get(city, city)
        print(f"'{city}' -> '{normalized}'")
        coords = CITY_COORDS.get(normalized)
        print(f"  Coords: {coords}")

if __name__ == "__main__":
    debug_spacy_processing()
    test_city_coords_lookup()
