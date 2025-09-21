#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alternative: Enhanced existing geocoding without SpaCy dependency
Lightweight solution for the Mykolaivka problem
"""

def improved_city_normalization():
    """
    Enhanced UA_CITY_NORMALIZE with accusative case support
    """
    
    # Add accusative->nominative mappings to existing UA_CITY_NORMALIZE
    enhanced_normalize = {
        # Existing mappings...
        
        # Add accusative case normalization (винительный падеж)
        'миколаївку': 'миколаївка',
        'олександрівку': 'олександрівка', 
        'петрівку': 'петрівка',
        'новгород-сіверський': 'новгород-сіверський',
        'полтаву': 'полтава',
        'харкова': 'харків',
        'херсона': 'херсон',
        'кременчуку': 'кременчук',
        
        # Add instrumental case (орудний відмінок)
        'харковом': 'харків',
        'полтавою': 'полтава',
        
        # Add genitive case (родовий відмінок)  
        'харкова': 'харків',
        'полтави': 'полтава',
        'миколаєва': 'миколаїв',
        
        # Add locative case (місцевий відмінок)
        'харкові': 'харків',
        'полтаві': 'полтава',
        'миколаєві': 'миколаїв',
    }
    
    return enhanced_normalize

def enhanced_regional_context_processing():
    """
    Improved regional context detection for existing app.py logic
    """
    
    # Enhanced regional patterns to add to existing code
    enhanced_regional_patterns = {
        # Priority patterns for region+city combinations
        'priority_regional_patterns': [
            # Pattern: "X шахед на [city] на [region]" 
            r'(\d+)\s*шахед[іїв]*\s+на\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,30}?)\s+на\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,20}?щин[іауи])',
            
            # Pattern: "[region] - шахеди на [city]"
            r'([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,20}?щин[іауи]?)\s*[-–—]\s*шахед[іїив]*\s+на\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,30}?)',
            
            # Pattern: "[region] ([city] р-н)" - district headquarters  
            r'([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,20}?щин[іауи]?)\s*\(\s*([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,30}?)\s+р[-\s]*н\)',
        ],
        
        # Regional normalization
        'region_normalize': {
            'сумщині': 'сумщина',
            'сумщину': 'сумщина', 
            'сумщини': 'сумщина',
            'чернігівщині': 'чернігівщина',
            'чернігівщину': 'чернігівщина',
            'чернігівщини': 'чернігівщина',
            'харківщині': 'харківщина',
            'харківщину': 'харківщина',
            'харківщини': 'харківщина',
        }
    }
    
    return enhanced_regional_patterns

def lightweight_ambiguous_city_resolver(city_name: str, region_context: str = None, 
                                       message_text: str = None) -> str:
    """
    Lightweight resolver for ambiguous city names without SpaCy
    
    Args:
        city_name: Normalized city name 
        region_context: Detected region if any
        message_text: Full message for additional context
        
    Returns:
        Best city key for CITY_COORDS lookup
    """
    
    # Known ambiguous cities with their regional variants
    ambiguous_cities = {
        'миколаївка': {
            'сумщина': 'миколаївка сумщина',      # Sumy Oblast coordinates
            'миколаївщина': 'миколаївка',          # Mykolaiv Oblast coordinates  
            'default': 'миколаївка'                # Default to more common one
        },
        'олександрівка': {
            'київщина': 'олександрівка київщина',
            'кіровоградщина': 'олександрівка кіровоградщина',
            'default': 'олександрівка'
        },
        'петрівка': {
            'полтавщина': 'петрівка полтавщина',
            'харківщина': 'петрівка харківщина', 
            'default': 'петрівка'
        }
    }
    
    if city_name in ambiguous_cities:
        city_variants = ambiguous_cities[city_name]
        
        # If we have regional context, use it
        if region_context and region_context in city_variants:
            return city_variants[region_context]
        
        # Try to detect region from message text
        if message_text:
            message_lower = message_text.lower()
            for region in city_variants:
                if region != 'default' and region in message_lower:
                    return city_variants[region]
        
        # Fall back to default
        return city_variants['default']
    
    # For non-ambiguous cities, add region context if available
    if region_context:
        return f"{city_name} {region_context}"
    
    return city_name

# Example integration with existing app.py
def demo_lightweight_solution():
    """Demo how to integrate lightweight solution"""
    
    test_message = "1 шахед на Миколаївку на Сумщині"
    
    # Step 1: Enhanced normalization
    enhanced_normalize = improved_city_normalization()
    
    # Step 2: Extract with enhanced regional patterns
    import re
    
    # Use enhanced regional pattern
    pattern = r'(\d+)\s*шахед[іїв]*\s+на\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,30}?)\s+на\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,20}?щин[іауи])'
    match = re.search(pattern, test_message, re.IGNORECASE)
    
    if match:
        count = int(match.group(1))
        city_raw = match.group(2).strip()
        region_raw = match.group(3).strip()
        
        # Step 3: Normalize city and region
        city_normalized = enhanced_normalize.get(city_raw.lower(), city_raw.lower())
        region_normalized = region_raw.lower().replace('щині', 'щина').replace('щину', 'щина')
        
        # Step 4: Resolve ambiguous city
        city_key = lightweight_ambiguous_city_resolver(
            city_normalized, region_normalized, test_message
        )
        
        print(f"Message: {test_message}")
        print(f"Extracted: count={count}, city='{city_raw}', region='{region_raw}'")
        print(f"Normalized: city='{city_normalized}', region='{region_normalized}'") 
        print(f"Final city key: '{city_key}'")
        
        # This would now correctly resolve to 'миколаївка сумщина'
        # instead of ambiguous 'миколаївка'
        
        return city_key

if __name__ == "__main__":
    result = demo_lightweight_solution()
    print(f"\nResult: {result}")
    print("✅ Problem solved without SpaCy dependency!")
