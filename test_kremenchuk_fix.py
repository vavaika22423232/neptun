#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Kremenchuk morphological normalization fix
"""

from context_aware_geocoder import ContextAwareGeocoder, get_context_aware_geocoding
from app import get_coordinates_context_aware

print("🎯 KREMENCHUK MORPHOLOGICAL NORMALIZATION TEST")
print("=" * 60)

# Test different morphological forms of Kremenchuk
test_cases = [
    "полтавщина - шахеди атакували кременчуці",
    "кременчуці під атакою",
    "БпЛА курсом на кременчук",
    "шахеди над кременчук",
    "у кременчуці"
]

geocoder = ContextAwareGeocoder()

for i, test_text in enumerate(test_cases, 1):
    print(f"\n📝 Test {i}: {test_text}")
    
    # Test context analysis
    result = geocoder.analyze_message_context(test_text)
    print(f"Context analysis:")
    print(f"  Primary targets: {result['primary_targets']}")
    print(f"  Regional context: {result['regional_context']}")
    
    # Test normalization directly
    if 'кременчуці' in test_text:
        normalized = geocoder._normalize_city_form('кременчуці')
        print(f"  Direct normalization: кременчуці → {normalized}")
    
    # Test full geocoding
    coords = get_coordinates_context_aware(test_text)
    if coords:
        print(f"  Final coordinates: {coords}")
        if 'кременчук' in str(coords).lower():
            print("  ✅ SUCCESS: Found Kremenchuk coordinates")
        else:
            print("  ❌ ISSUE: No Kremenchuk coordinates found")
    else:
        print("  ❌ ISSUE: No coordinates found")

print("\n🎯 FINAL TEST: Context-aware geocoding function")
test_text = "полтавщина - шахеди атакували кременчуці"
context_results = get_context_aware_geocoding(test_text)
print(f"Context-aware results for '{test_text}':")
for city, region, confidence in context_results:
    print(f"  {city} (region: {region}, confidence: {confidence})")
    if city.lower() == 'кременчук':
        print("  ✅ SUCCESS: Context-aware geocoding found Kremenchuk!")

print("\n" + "=" * 60)
print("Test completed!")
