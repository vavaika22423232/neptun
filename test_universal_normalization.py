#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test universal Ukrainian toponym normalization
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import normalize_ukrainian_toponym, spacy_enhanced_geocoding, SPACY_AVAILABLE

def test_universal_normalization():
    """Test the universal normalization logic"""
    
    print("🧠 Testing Universal Ukrainian Toponym Normalization")
    print("=" * 60)
    
    test_cases = [
        # Adjective → City patterns
        ('чкаловський', 'Чкаловське', 'Acc', 'чкаловське'),
        ('покровський', 'Покровськ', 'Nom', 'покровськ'),
        ('краматорський', 'Краматорську', 'Loc', 'краматорськ'),
        ('слов\'янський', 'Слов\'янськ', 'Acc', 'слов\'янськ'),
        ('новоукраїнський', 'Новоукраїнськ', 'Nom', 'новоукраїнськ'),
        
        # Case-specific fixes
        ('зарічний', 'Зарічного', 'Gen', 'зарічне'),
        ('новоукраїнськом', 'Новоукраїнськом', 'Ins', 'новоукраїнськ'),
        
        # Feminine places
        ('савинка', 'Савинці', 'Nom', 'савинці'),
        ('миколаївка', 'Миколаївку', 'Acc', 'миколаївка'),
        
        # Should remain unchanged
        ('київ', 'Київ', 'Nom', 'київ'),
        ('харків', 'Харків', 'Nom', 'харків'),
        ('полтава', 'Полтаву', 'Acc', 'полтава'),
    ]
    
    print("🔍 Direct normalization function tests:")
    for lemma, original, case, expected in test_cases:
        result = normalize_ukrainian_toponym(lemma, original, case)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{lemma}' (from '{original}', {case}) → '{result}' (expected: '{expected}')")
    
    print(f"\n🎯 Testing with actual SpaCy processing:")
    
    spacy_test_messages = [
        '1 БпЛА на Чкаловське',
        'БпЛА курсом на Покровськ', 
        'Удар по Краматорську',
        'Атака на Слов\'янськ',
        'Обстріл Зарічного',
        'БпЛА над Новоукраїнськом',
        'Вибухи в Миколаївці',
    ]
    
    if SPACY_AVAILABLE:
        for message in spacy_test_messages:
            print(f"\n📝 Message: '{message}'")
            results = spacy_enhanced_geocoding(message)
            
            for result in results:
                if result['coords']:
                    lat, lng = result['coords']
                    print(f"  ✅ {result['name']} → {result['normalized']} ({lat:.4f}, {lng:.4f})")
                    print(f"     Source: {result['source']}, Case: {result.get('case', 'N/A')}")
    else:
        print("⚠️ SpaCy not available - skipping integration tests")

def test_pattern_coverage():
    """Test how many different patterns the universal logic covers"""
    
    print(f"\n📊 Pattern Coverage Analysis")
    print("=" * 40)
    
    # Test various Ukrainian city name patterns
    pattern_examples = [
        # -ський pattern cities
        'донецький', 'луганський', 'харківський', 'київський',
        # -цький pattern cities  
        'вінницький', 'хмельницький', 'житомирський',
        # Complex compounds
        'кам\'янський', 'олександрівський', 'петропавлівський',
        # Instrumental cases
        'покровськом', 'краматорськом', 'костянтинівськом',
        # Genitive cases
        'бахмутський', 'артемівський', 'горлівський',
    ]
    
    print("🔍 Testing pattern recognition:")
    for test_name in pattern_examples:
        result = normalize_ukrainian_toponym(test_name, test_name.title(), 'Test')
        if result != test_name:
            print(f"  🔄 '{test_name}' → '{result}'")
        else:
            print(f"  ➖ '{test_name}' → unchanged")

if __name__ == "__main__":
    test_universal_normalization()
    test_pattern_coverage()
