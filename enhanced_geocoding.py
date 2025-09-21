#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced geocoding with SpaCy integration for app.py
"""

# Try to import SpaCy components
try:
    from spacy_integration import SpacyCityExtractor
    SPACY_ENHANCED = True
except ImportError:
    SPACY_ENHANCED = False

def enhance_city_extraction_with_spacy(message_text: str, existing_city_coords: dict, 
                                     existing_normalizer: dict) -> list:
    """
    Enhanced city extraction using SpaCy when available, with fallback to existing logic
    
    Args:
        message_text: Original message text  
        existing_city_coords: Your CITY_COORDS dict
        existing_normalizer: Your UA_CITY_NORMALIZE dict
        
    Returns:
        List of dicts with enhanced city information:
        {
            'name': str,           # Original city name from message
            'normalized': str,     # Normalized city name for lookup
            'coords': tuple,       # (lat, lng) coordinates if found
            'region': str,         # Detected region if any
            'confidence': float,   # Confidence score 0.0-1.0
            'source': str         # Detection method used
        }
    """
    results = []
    
    if SPACY_ENHANCED:
        try:
            extractor = SpacyCityExtractor()
            cities_info, regions = extractor.extract_cities_and_regions(message_text)
            
            for city_info in cities_info:
                # Normalize city name using SpaCy
                normalized_name = extractor.normalize_city_name(city_info)
                
                # Try existing normalization as fallback
                if normalized_name in existing_normalizer:
                    normalized_name = existing_normalizer[normalized_name]
                
                # Look up coordinates
                coords = existing_city_coords.get(normalized_name)
                detected_region = regions[0] if regions else None
                
                # Try with region context if no direct match
                if not coords and detected_region:
                    region_key = f"{normalized_name} {detected_region}"
                    coords = existing_city_coords.get(region_key)
                
                result = {
                    'name': city_info['name'],
                    'normalized': normalized_name,
                    'coords': coords,
                    'region': detected_region,
                    'confidence': city_info['confidence'],
                    'source': f"spacy_{city_info['source']}"
                }
                results.append(result)
                
        except Exception as e:
            print(f"SpaCy processing error: {e}, falling back to regex")
            return _fallback_city_extraction(message_text, existing_city_coords, existing_normalizer)
    else:
        return _fallback_city_extraction(message_text, existing_city_coords, existing_normalizer)
    
    return results

def _fallback_city_extraction(message_text: str, existing_city_coords: dict, 
                             existing_normalizer: dict) -> list:
    """Fallback extraction using existing regex patterns"""
    import re
    
    results = []
    
    # Your existing city extraction patterns
    city_patterns = [
        r'(?:на|повз|через)\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,30}?)(?=\s|$|[,\.\!\?;])',
        r'у\s+напрямку\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,30}?)(?=\s|$|[,\.\!\?;])',
        r'між\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,30}?)\s+та\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,30}?)(?=\s|$|[,\.\!\?;])'
    ]
    
    for pattern in city_patterns:
        matches = re.findall(pattern, message_text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):  # Multiple groups (e.g., "між X та Y")
                for city_name in match:
                    if city_name.strip():
                        _process_fallback_city(city_name.strip(), results, existing_city_coords, existing_normalizer)
            else:
                _process_fallback_city(match.strip(), results, existing_city_coords, existing_normalizer)
    
    return results

def _process_fallback_city(city_name: str, results: list, existing_city_coords: dict, existing_normalizer: dict):
    """Process a single city from fallback extraction"""
    normalized = city_name.lower()
    
    # Apply existing normalization
    if normalized in existing_normalizer:
        normalized = existing_normalizer[normalized]
    
    # Look up coordinates
    coords = existing_city_coords.get(normalized)
    
    result = {
        'name': city_name,
        'normalized': normalized,
        'coords': coords,
        'region': None,
        'confidence': 0.5,
        'source': 'regex_fallback'
    }
    results.append(result)

# Test function
def test_enhanced_extraction():
    """Test the enhanced extraction with sample data"""
    
    # Sample data (subset of your actual data)
    test_city_coords = {
        'миколаївка': (51.5667, 34.1333),  # Sumy Oblast
        'миколаїв': (46.9659, 31.9974),    # Mykolaiv Oblast  
        'миколаївка сумщина': (51.5667, 34.1333),
        'харків': (49.9935, 36.2304),
        'полтава': (49.5885, 34.5514)
    }
    
    test_normalizer = {
        'миколаївку': 'миколаївка',
        'полтаву': 'полтава'
    }
    
    test_messages = [
        "1 шахед на Миколаївку на Сумщині",
        "БпЛА курсом на Харків через Полтаву",
        "2х БпЛА повз Конотоп у напрямку Глухова"
    ]
    
    print("=== Enhanced City Extraction Test ===\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"Тест {i}: {message}")
        results = enhance_city_extraction_with_spacy(message, test_city_coords, test_normalizer)
        
        for result in results:
            print(f"  Місто: {result['name']} -> {result['normalized']}")
            print(f"    Координати: {result['coords']}")
            print(f"    Регіон: {result['region']}")
            print(f"    Джерело: {result['source']} (впевненість: {result['confidence']})")
            print()
        
        print("-" * 60)

if __name__ == "__main__":
    test_enhanced_extraction()
