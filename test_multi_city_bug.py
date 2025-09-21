#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for multi-city message processing
"""

import sys
sys.path.append('/Users/vladimirmalik/Desktop/render2')

def test_multi_city_message():
    from app import process_message, spacy_enhanced_geocoding, SPACY_AVAILABLE
    
    # The problematic message
    test_message = """🛸 Білозерка (Херсонська обл.)
Загроза застосування БПЛА. Перейдіть в укриття! | 🛸 Суми (Сумська обл.)
Загроза застосування БПЛА. Перейдіть в укриття!"""
    
    print("🔍 MULTI-CITY MESSAGE TEST")
    print("=" * 50)
    print(f"SpaCy Available: {SPACY_AVAILABLE}")
    print(f"Message: {repr(test_message)}")
    
    # Test SpaCy detection first
    if SPACY_AVAILABLE:
        print("\n🧠 SpaCy Analysis:")
        spacy_results = spacy_enhanced_geocoding(test_message)
        for i, result in enumerate(spacy_results, 1):
            print(f"  {i}. {result['name']} -> {result['normalized']}")
            print(f"     Coords: {result['coords']}")
            print(f"     Region: {result.get('region', 'None')}")
            print(f"     Confidence: {result['confidence']}")
            print()
    
    # Test full message processing
    print("📍 Process Message Results:")
    try:
        results = process_message(test_message, "test_multi", "2025-09-21 12:00:00", "test")
        
        print(f"Number of markers created: {len(results) if results else 0}")
        
        if results:
            for i, marker in enumerate(results, 1):
                print(f"  Marker {i}:")
                print(f"    Place: {marker['place']}")
                print(f"    Coords: ({marker['lat']}, {marker['lng']})")
                print(f"    Source: {marker.get('source_match', 'unknown')}")
                print()
        else:
            print("  ❌ No markers created!")
            
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_city_message()
