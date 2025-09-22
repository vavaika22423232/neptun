#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test comprehensive plugin normalization fixes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import spacy_enhanced_geocoding, SPACY_AVAILABLE

def test_plugin_normalization():
    """Test plugin normalization for multiple problematic cities"""
    
    print("🔧 Testing Plugin Normalization Fixes")
    print("=" * 50)
    
    test_cases = [
        {
            'message': '1 БпЛА на Чкаловське',
            'expected_city': 'чкаловське',
            'expected_region': 'Харківська область',
            'coordinates_range': [(49.7, 49.8), (36.9, 37.0)],
            'description': 'Чкаловське should be in Kharkiv oblast'
        },
        {
            'message': 'БпЛА курсом на Покровськ',
            'expected_city': 'покровськ',
            'expected_region': 'Донецька область',
            'coordinates_range': [(48.1, 48.3), (37.6, 37.8)],
            'description': 'Pokrovsk lemmatization test'
        },
        {
            'message': 'Удар по Краматорську',
            'expected_city': 'краматорськ',
            'expected_region': 'Донецька область',
            'coordinates_range': [(48.7, 48.8), (37.5, 37.6)],
            'description': 'Kramatorsk lemmatization test'
        },
        {
            'message': 'Атака на Слов\'янськ',
            'expected_city': 'слов\'янськ',
            'expected_region': 'Донецька область',
            'coordinates_range': [(48.8, 48.9), (37.6, 37.7)],
            'description': 'Slovyansk with apostrophe'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['description']}")
        print(f"Input: '{test_case['message']}'")
        
        if SPACY_AVAILABLE:
            results = spacy_enhanced_geocoding(test_case['message'])
            
            # Find the target city in results
            target_result = None
            for result in results:
                if (result['normalized'] == test_case['expected_city'] or 
                    result['name'].lower() == test_case['expected_city']):
                    target_result = result
                    break
            
            if target_result:
                print(f"✅ Found: {target_result['name']} -> {target_result['normalized']}")
                
                if target_result['coords']:
                    lat, lng = target_result['coords']
                    print(f"📍 Coordinates: ({lat:.6f}, {lng:.6f})")
                    
                    # Check if coordinates are in expected range
                    lat_range, lng_range = test_case['coordinates_range']
                    if (lat_range[0] <= lat <= lat_range[1] and 
                        lng_range[0] <= lng <= lng_range[1]):
                        print(f"✅ Coordinates in expected range for {test_case['expected_region']}")
                    else:
                        print(f"❌ Coordinates outside expected range for {test_case['expected_region']}")
                else:
                    print("❌ No coordinates found")
                    
                print(f"🎯 Confidence: {target_result['confidence']:.1f}, Source: {target_result['source']}")
                if target_result['case']:
                    print(f"📝 Grammatical case: {target_result['case']}")
            else:
                print(f"❌ Expected city '{test_case['expected_city']}' not found")
                print(f"Found results: {[r['normalized'] for r in results if r['coords']]}")
        else:
            print("⚠️ SpaCy not available - skipping test")

def test_edge_cases():
    """Test edge cases and potential conflicts"""
    
    print(f"\n🎯 Testing Edge Cases")
    print("=" * 30)
    
    edge_cases = [
        'БпЛА над Новоукраїнськом',  # Should normalize correctly
        'Вибух у Першотравенську',   # Complex compound name
        'Ракети в Новомосковську',   # Another complex name
    ]
    
    for case in edge_cases:
        print(f"\n📝 Text: '{case}'")
        if SPACY_AVAILABLE:
            results = spacy_enhanced_geocoding(case)
            for result in results:
                if result['coords']:
                    lat, lng = result['coords']
                    print(f"  - {result['name']} -> {result['normalized']} ({lat:.4f}, {lng:.4f})")

if __name__ == "__main__":
    test_plugin_normalization()
    test_edge_cases()
