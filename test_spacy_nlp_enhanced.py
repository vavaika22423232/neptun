#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test enhanced SpaCy NLP functionality 
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import spacy_enhanced_geocoding, SPACY_AVAILABLE

def test_spacy_nlp_analysis():
    """Test SpaCy with proper NLP entity recognition"""
    
    if not SPACY_AVAILABLE:
        print("❌ SpaCy not available - skipping tests")
        return
        
    print("🔍 Testing Enhanced SpaCy NLP Analysis")
    print("=" * 50)
    
    test_cases = [
        {
            'text': 'БпЛА курсом на Олександрію',
            'expected_city': 'олександрія',
            'description': 'City after directional phrase'
        },
        {
            'text': 'Удар по Кривому Рогу',
            'expected_city': 'кривий ріг',
            'description': 'Multi-word city name'
        },
        {
            'text': 'Обстріл Зарічного на Дніпропетровщині',
            'expected_city': 'зарічне',
            'expected_region': 'дніпропетровщина',
            'description': 'City with regional context'
        },
        {
            'text': 'Атака дронів на Миколаївку в Сумській області',
            'expected_city': 'миколаївка', 
            'expected_region': 'сумщина',
            'description': 'City with explicit regional specification'
        },
        {
            'text': 'Шахеди летять через Полтаву у напрямку Київа',
            'expected_cities': ['полтава', 'київ'],
            'description': 'Multiple cities with direction'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['description']}")
        print(f"Input: '{test_case['text']}'")
        
        results = spacy_enhanced_geocoding(test_case['text'])
        
        print(f"SpaCy NLP Results: {len(results)} entities found")
        for result in results:
            print(f"  - {result['name']} -> {result['normalized']} ({result['source']}, conf: {result['confidence']:.1f})")
            if result['coords']:
                print(f"    Coordinates: {result['coords']}")
            if result['region']:
                print(f"    Region: {result['region']}")
            if result['case']:
                print(f"    Grammatical case: {result['case']}")
        
        # Validation
        if 'expected_city' in test_case:
            found = any(r['normalized'] == test_case['expected_city'] for r in results)
            print(f"  ✅ Expected city '{test_case['expected_city']}' found" if found else f"  ❌ Expected city '{test_case['expected_city']}' NOT found")
        
        if 'expected_cities' in test_case:
            for expected_city in test_case['expected_cities']:
                found = any(r['normalized'] == expected_city for r in results)
                print(f"  ✅ Expected city '{expected_city}' found" if found else f"  ❌ Expected city '{expected_city}' NOT found")
                
        if 'expected_region' in test_case:
            found = any(r['region'] == test_case['expected_region'] for r in results)
            print(f"  ✅ Expected region '{test_case['expected_region']}' detected" if found else f"  ❌ Expected region '{test_case['expected_region']}' NOT detected")

def test_spacy_nlp_vs_regex():
    """Compare SpaCy NLP vs regex-based approach"""
    
    if not SPACY_AVAILABLE:
        print("❌ SpaCy not available - skipping comparison")
        return
        
    print("\n🔄 SpaCy NLP vs Regex Comparison")
    print("=" * 40)
    
    challenging_cases = [
        'Ракетний удар по Кропивницькому',  # SpaCy should recognize proper noun
        'БпЛА пролетіли над Житомиром',      # Morphological analysis 
        'Вибухи в Ужгороді',                 # Case analysis (locative)
        'На Запоріжжі зафіксовано атаку',    # Regional vs city disambiguation
        'Дрони атакували Першотравенськ'     # Complex compound name
    ]
    
    for text in challenging_cases:
        print(f"\n📝 Text: '{text}'")
        
        spacy_results = spacy_enhanced_geocoding(text)
        print(f"SpaCy NLP found {len(spacy_results)} entities:")
        for result in spacy_results:
            print(f"  - {result['name']} -> {result['normalized']} (source: {result['source']}, case: {result.get('case', 'N/A')})")
            if result['coords']:
                lat, lng = result['coords']
                print(f"    📍 Coordinates: ({lat:.4f}, {lng:.4f})")

if __name__ == "__main__":
    test_spacy_nlp_analysis()
    test_spacy_nlp_vs_regex()
