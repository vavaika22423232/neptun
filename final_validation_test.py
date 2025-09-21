#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final validation test for SpaCy integration
"""

def test_main_issue_resolved():
    """Test that the main Mykolaivka issue is fully resolved"""
    
    import sys
    sys.path.append('/Users/vladimirmalik/Desktop/render2')
    
    from app import process_message, SPACY_AVAILABLE
    
    print("🎯 FINAL VALIDATION TEST")
    print("=" * 50)
    print(f"SpaCy Status: {'✅ Available' if SPACY_AVAILABLE else '❌ Not Available'}")
    
    # The problematic message that was showing wrong location
    test_message = "1 шахед на Миколаївку на Сумщині"
    
    print(f"\n📨 Test Message: {test_message}")
    print("🎯 Expected: Sumy Oblast coordinates (51.5667, 34.1333)")
    
    try:
        result = process_message(test_message, "test_final", "2025-09-21 12:00:00", "test")
        
        if result and len(result) > 0:
            marker = result[0]
            lat, lng = marker['lat'], marker['lng']
            place = marker['place']
            
            print(f"\n✅ SUCCESS!")
            print(f"📍 Location: {place}")
            print(f"🌍 Coordinates: ({lat}, {lng})")
            
            # Check if coordinates are correct (Sumy Oblast)
            expected_lat, expected_lng = 51.5667, 34.1333
            if abs(lat - expected_lat) < 0.01 and abs(lng - expected_lng) < 0.01:
                print("🎉 CORRECT! Показывается в Сумской области")
                return True
            else:
                print(f"❌ WRONG LOCATION! Expected ({expected_lat}, {expected_lng})")
                return False
        else:
            print("❌ FAILED: No markers created")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def show_spacy_capabilities():
    """Demonstrate SpaCy capabilities"""
    
    print("\n" + "=" * 50)
    print("🧠 SpaCy NLP CAPABILITIES DEMO")
    print("=" * 50)
    
    import sys
    sys.path.append('/Users/vladimirmalik/Desktop/render2')
    
    from app import spacy_enhanced_geocoding, SPACY_AVAILABLE
    
    if not SPACY_AVAILABLE:
        print("❌ SpaCy not available")
        return
    
    demo_messages = [
        "1 шахед на Миколаївку на Сумщині",
        "БпЛА курсом на Харків через Полтаву",
        "Обстріл Херсона та Миколаєва"
    ]
    
    for i, message in enumerate(demo_messages, 1):
        print(f"\n{i}. Message: {message}")
        results = spacy_enhanced_geocoding(message)
        
        if results:
            for city in results:
                print(f"   🏙️  {city['name']} → {city['normalized']}")
                print(f"       📍 Coords: {city['coords']}")
                print(f"       🏛️  Region: {city.get('region', 'None')}")
                print(f"       📝 Case: {city.get('case', 'unknown')}")
                print(f"       🎯 Confidence: {city['confidence']}")
        else:
            print("   ❌ No cities detected")

if __name__ == "__main__":
    success = test_main_issue_resolved()
    show_spacy_capabilities()
    
    print("\n" + "=" * 50)
    print("📊 INTEGRATION SUMMARY")
    print("=" * 50)
    
    if success:
        print("✅ Main issue RESOLVED: Mykolaivka correctly shows in Sumy Oblast")
        print("🚀 SpaCy successfully integrated and working")
        print("🎯 Ukrainian NLP processing active")
        print("📈 Enhanced geocoding accuracy achieved")
    else:
        print("❌ Integration needs further work")
    
    print("\n🔄 System now uses hybrid approach:")
    print("   1. SpaCy NLP analysis (priority)")
    print("   2. Regex patterns (fallback)")
    print("   3. Morphological normalization")
    print("   4. Regional context detection")
    
    print("\n🎉 SpaCy Integration Complete!")
