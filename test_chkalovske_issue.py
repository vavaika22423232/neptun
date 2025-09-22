#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Чкаловське geocoding issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import (
    CITY_COORDS, 
    ensure_city_coords_with_message_context,
    spacy_enhanced_geocoding,
    SPACY_AVAILABLE,
    get_coordinates_enhanced
)

def test_chkalovske_issue():
    """Test why Чкаловське shows in wrong region"""
    
    print("🔍 Testing Чкаловське Geocoding Issue")
    print("=" * 50)
    
    test_message = "1 БпЛА на Чкаловське"
    city_name = "чкаловське"
    
    print(f"Input message: '{test_message}'")
    print(f"Target city: '{city_name}'")
    print()
    
    # 1. Check direct lookup in CITY_COORDS
    print("1️⃣ Direct CITY_COORDS lookup:")
    direct_coords = CITY_COORDS.get(city_name)
    print(f"   Direct: {direct_coords}")
    
    # Check variants
    variants = [
        "чкаловське",
        "чкаловське харківська",
        "чкаловське харківської",
        "чкаловське донецька", 
        "чкаловське донецької",
        "чкаловське (харківська)",
        "чкаловське (донецька)"
    ]
    
    print("\n🔍 Checking all variants:")
    for variant in variants:
        coords = CITY_COORDS.get(variant)
        if coords:
            print(f"   ✅ '{variant}' -> {coords}")
        else:
            print(f"   ❌ '{variant}' -> Not found")
    
    # 2. Test SpaCy enhanced geocoding
    print(f"\n2️⃣ SpaCy Enhanced Geocoding (available: {SPACY_AVAILABLE}):")
    if SPACY_AVAILABLE:
        spacy_results = spacy_enhanced_geocoding(test_message)
        print(f"   Found {len(spacy_results)} results:")
        for result in spacy_results:
            print(f"   - {result['name']} -> {result['normalized']} -> {result['coords']}")
            if result['region']:
                print(f"     Region: {result['region']}")
    else:
        print("   SpaCy not available")
    
    # 3. Test enhanced coordinate lookup
    print(f"\n3️⃣ Enhanced Coordinate Lookup:")
    enhanced_coords = get_coordinates_enhanced(city_name, context=test_message)
    print(f"   Enhanced: {enhanced_coords}")
    
    # 4. Test with regional context
    print(f"\n4️⃣ With Regional Context:")
    for region in ["харківська", "донецька"]:
        coords = get_coordinates_enhanced(city_name, region, test_message)
        print(f"   With {region}: {coords}")
    
    # 5. Test message context function
    print(f"\n5️⃣ Message Context Function:")
    context_coords = ensure_city_coords_with_message_context(city_name, test_message)
    print(f"   Context result: {context_coords}")

def check_chkalovske_in_database():
    """Check all Чкаловське entries in database"""
    
    print("\n📊 All Чкаловське entries in database:")
    print("=" * 40)
    
    found_entries = []
    for key, coords in CITY_COORDS.items():
        if "чкаловськ" in key.lower():
            found_entries.append((key, coords))
    
    if found_entries:
        for key, coords in found_entries:
            lat, lng = coords
            # Determine region by coordinates
            if 49.0 <= lat <= 50.5 and 35.5 <= lng <= 37.5:
                region = "Харківська область"
            elif 47.0 <= lat <= 49.0 and 36.5 <= lng <= 39.0:
                region = "Донецька область"
            else:
                region = "Unknown region"
            
            print(f"   ✅ '{key}' -> {coords} ({region})")
    else:
        print("   ❌ No Чкаловське entries found")

if __name__ == "__main__":
    test_chkalovske_issue()
    check_chkalovske_in_database()
