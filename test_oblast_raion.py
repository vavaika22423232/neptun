#!/usr/bin/env python3
"""
Test script for oblast+raion parsing logic
"""

import re
import time

# Mock the RAION_FALLBACK dictionary with our test data
RAION_FALLBACK = {
    'конотопський': (51.2375, 33.2020),
    'сумський': (50.9077, 34.7981),
    'чернігівський': (51.4982, 31.2893),
    'вишгородський': (50.5850, 30.4915),
}

def test_oblast_raion_parsing():
    test_text = "Загроза застосування БПЛА. Перейдіть в укриття! | чернігівська область (чернігівський район), київська область (вишгородський район), сумська область (сумський, конотопський райони) - загроза ударних бпла!"
    
    print(f"Testing text: {test_text}")
    print()
    
    # Test our regex pattern
    oblast_raion_pattern = r'([а-яіїєґ]+ська\s+область)\s*\(([^)]*?райони?[^)]*?)\)'
    oblast_raion_matches = re.findall(oblast_raion_pattern, test_text.lower(), re.IGNORECASE)
    
    print(f"Pattern 1 matches: {oblast_raion_matches}")
    
    # Also check for pattern without requiring "райони" in parentheses
    if not oblast_raion_matches:
        oblast_raion_pattern_simple = r'([а-яіїєґ]+ська\s+область)\s*\(([^)]+)\)'
        oblast_raion_matches_simple = re.findall(oblast_raion_pattern_simple, test_text.lower(), re.IGNORECASE)
        # Filter to only those that contain district-like words
        oblast_raion_matches = [(oblast, raion) for oblast, raion in oblast_raion_matches_simple 
                               if any(word in raion for word in ['район', 'р-н', 'ський', 'цький'])]
        print(f"Pattern 2 matches: {oblast_raion_matches}")
    
    # Check if we have threat words
    has_threat = any(word in test_text.lower() for word in ['бпла', 'загроза', 'укриття'])
    print(f"Has threat words: {has_threat}")
    print()
    
    if oblast_raion_matches and has_threat:
        tracks = []
        
        for oblast_text, raion_text in oblast_raion_matches:
            print(f"Processing oblast: '{oblast_text}', raion_text: '{raion_text}'")
            
            # Extract individual raions from the parentheses
            raion_parts = re.split(r',\s*|\s+та\s+', raion_text)
            print(f"Split raion_parts: {raion_parts}")
            
            for raion_part in raion_parts:
                raion_part = raion_part.strip()
                if not raion_part:
                    continue
                    
                print(f"  Processing raion_part: '{raion_part}'")
                    
                # Extract raion name (remove "район"/"райони" suffix)
                raion_name = re.sub(r'\s*(райони?|р-н\.?).*$', '', raion_part).strip()
                print(f"  After removing suffix, raion_name: '{raion_name}'")
                
                # Normalize raion name
                raion_normalized = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_name)
                print(f"  Normalized raion: '{raion_normalized}'")
                
                if raion_normalized in RAION_FALLBACK:
                    lat, lng = RAION_FALLBACK[raion_normalized]
                    print(f"  ✅ Found coordinates: {lat}, {lng}")
                    
                    tracks.append({
                        'id': f"test_raion_{raion_normalized}",
                        'place': f"{raion_normalized.title()} район",
                        'lat': lat,
                        'lng': lng,
                        'threat_type': 'shahed',
                        'marker_icon': 'shahed.png',
                        'source_match': 'oblast_raion_format'
                    })
                else:
                    print(f"  ❌ Raion not found in RAION_FALLBACK: '{raion_normalized}'")
                    print(f"     Available keys: {list(RAION_FALLBACK.keys())}")
                print()
        
        print(f"Final result: {len(tracks)} tracks created")
        for track in tracks:
            print(f"  - {track['place']} at {track['lat']}, {track['lng']}")
    else:
        print("No matches or no threat words found")

if __name__ == "__main__":
    test_oblast_raion_parsing()
