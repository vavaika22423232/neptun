#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recommended SpaCy integration strategy for app.py

STRATEGY: Hybrid approach with graceful fallback
- Use SpaCy for complex cases where current regex fails
- Keep existing regex for simple, fast cases  
- Add SpaCy as optional enhancement, not replacement
"""

def should_use_spacy_enhancement(message_text: str) -> bool:
    """
    Determine if message needs SpaCy processing based on complexity
    
    Use SpaCy for:
    - Messages with ambiguous city names (like "Миколаївка")
    - Complex regional contexts  
    - Multiple cities in different cases
    - Failed geocoding from existing methods
    
    Keep regex for:
    - Simple, clear patterns already working well
    - High-frequency, performance-critical processing
    """
    
    # Indicators that SpaCy enhancement would be beneficial
    spacy_indicators = [
        # Ambiguous city names that exist in multiple regions
        'миколаївк',  # Can be Sumy or Mykolaiv oblast
        'олександрі',  # Multiple Oleksandrivkas exist  
        'петрівк',     # Multiple Petrivkas exist
        
        # Complex regional context
        'на сумщині', 'на харківщині', 'на чернігівщині',
        
        # Multiple cities in one message with different cases
        len([m for m in ['на ', 'повз ', 'через ', 'у напрямку '] 
             if m in message_text.lower()]) >= 2,
        
        # Genitive/accusative forms that might be misrecognized
        any(ending in message_text.lower() for ending in ['ку ', 'ву ', 'ова ', 'ева ', 'ські ', 'цькі ']),
    ]
    
    return any(spacy_indicators)

def enhanced_geocoding_strategy(message_text: str, existing_city_coords: dict, 
                              existing_normalizer: dict) -> dict:
    """
    Smart geocoding strategy combining regex speed with SpaCy accuracy
    
    Returns:
        {
            'method_used': str,
            'processing_time_ms': float,
            'cities_found': list,
            'confidence': float
        }
    """
    import time
    
    start_time = time.time()
    
    # Try existing regex method first (fast path)
    existing_results = try_existing_geocoding(message_text, existing_city_coords, existing_normalizer)
    
    # If existing method failed or low confidence, try SpaCy
    if (not existing_results or 
        should_use_spacy_enhancement(message_text) or
        any(r.get('coords') is None for r in existing_results)):
        
        try:
            from enhanced_geocoding import enhance_city_extraction_with_spacy
            spacy_results = enhance_city_extraction_with_spacy(
                message_text, existing_city_coords, existing_normalizer
            )
            
            # Choose best results
            if spacy_results and any(r.get('coords') for r in spacy_results):
                processing_time = (time.time() - start_time) * 1000
                return {
                    'method_used': 'spacy_enhanced',
                    'processing_time_ms': processing_time,
                    'cities_found': spacy_results,
                    'confidence': max(r.get('confidence', 0) for r in spacy_results)
                }
        except ImportError:
            # SpaCy not available, fall back
            pass
    
    # Return existing results
    processing_time = (time.time() - start_time) * 1000
    return {
        'method_used': 'existing_regex',
        'processing_time_ms': processing_time, 
        'cities_found': existing_results,
        'confidence': 0.7  # Default confidence for regex
    }

def try_existing_geocoding(message_text: str, existing_city_coords: dict, 
                          existing_normalizer: dict) -> list:
    """Simulate your existing geocoding logic"""
    # This would be replaced with your actual existing logic
    import re
    
    results = []
    
    # Simple simulation of existing patterns
    patterns = [
        r'на\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,20})',
        r'повз\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,20})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, message_text, re.IGNORECASE)
        for match in matches:
            city_name = match.strip()
            normalized = city_name.lower()
            
            if normalized in existing_normalizer:
                normalized = existing_normalizer[normalized]
            
            coords = existing_city_coords.get(normalized)
            
            results.append({
                'name': city_name,
                'normalized': normalized,
                'coords': coords,
                'region': None,
                'confidence': 0.7,
                'source': 'existing_regex'
            })
    
    return results

# Performance comparison test
def performance_comparison_test():
    """Compare performance of different approaches"""
    import time
    
    test_messages = [
        "1 шахед на Миколаївку на Сумщині",  # Complex case needing SpaCy
        "БпЛА курсом на Харків",              # Simple case, regex sufficient
        "2х БпЛА повз Конотоп у напрямку Глухова", # Multiple cities
        "Обстріл Херсона",                   # Very simple
        "Чернігівщина: 3 шахеди на Новгород-Сіверський" # Regional context
    ]
    
    # Sample coordinates
    coords_dict = {
        'миколаївка': (51.5667, 34.1333),
        'харків': (49.9935, 36.2304),
        'конотоп': (51.2294, 33.2007),
        'херсон': (46.6354, 32.6169)
    }
    
    normalizer_dict = {
        'миколаївку': 'миколаївка',
        'херсона': 'херсон'
    }
    
    print("=== Performance Comparison ===\n")
    
    total_regex_time = 0
    total_spacy_time = 0
    
    for message in test_messages:
        print(f"Message: {message}")
        
        # Test regex approach
        start = time.time()
        regex_results = try_existing_geocoding(message, coords_dict, normalizer_dict)
        regex_time = (time.time() - start) * 1000
        total_regex_time += regex_time
        
        # Test enhanced approach  
        start = time.time()
        enhanced_result = enhanced_geocoding_strategy(message, coords_dict, normalizer_dict)
        enhanced_time = enhanced_result['processing_time_ms']
        total_spacy_time += enhanced_time
        
        print(f"  Regex: {regex_time:.2f}ms, found {len(regex_results)} cities")
        print(f"  Enhanced: {enhanced_time:.2f}ms, method: {enhanced_result['method_used']}, found {len(enhanced_result['cities_found'])} cities")
        print()
    
    print(f"Total processing time:")
    print(f"  Regex only: {total_regex_time:.2f}ms")
    print(f"  Enhanced strategy: {total_spacy_time:.2f}ms")
    print(f"  Overhead: {total_spacy_time - total_regex_time:.2f}ms ({((total_spacy_time/total_regex_time - 1)*100):.1f}%)")

if __name__ == "__main__":
    performance_comparison_test()
