#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Гути location issue
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message, CITY_COORDS, SETTLEMENTS_INDEX, UA_CITY_NORMALIZE

def debug_guti_location():
    """Debug why Гути shows in wrong oblast"""
    
    test_text = "Харківщина — БпЛА на Гути"
    
    print("🔍 Debugging Гути location issue...\n")
    print(f"Input text: {test_text}")
    
    # Check if Гути is in city databases
    city_variants = ['гути', 'guti']
    
    print(f"\n📍 Checking city databases:")
    for variant in city_variants:
        if variant in CITY_COORDS:
            coords = CITY_COORDS[variant]
            print(f"  CITY_COORDS['{variant}'] = {coords}")
        else:
            print(f"  CITY_COORDS['{variant}'] = Not found")
    
    # Check settlements index if available
    if 'SETTLEMENTS_INDEX' in globals() and SETTLEMENTS_INDEX:
        for variant in city_variants:
            if variant in SETTLEMENTS_INDEX:
                coords = SETTLEMENTS_INDEX[variant]
                print(f"  SETTLEMENTS_INDEX['{variant}'] = {coords}")
            else:
                print(f"  SETTLEMENTS_INDEX['{variant}'] = Not found")
    
    # Check normalization
    print(f"\n🔄 Checking UA_CITY_NORMALIZE:")
    for variant in city_variants:
        if variant in UA_CITY_NORMALIZE:
            normalized = UA_CITY_NORMALIZE[variant]
            print(f"  '{variant}' -> '{normalized}'")
        else:
            print(f"  '{variant}' -> No normalization")
    
    # Test full message processing
    print(f"\n🧪 Testing message processing:")
    result = process_message(test_text, 'debug_guti', '2024-01-01 12:00:00', 'debug_channel')
    
    if result and isinstance(result, list) and len(result) > 0:
        threat = result[0]
        print(f"✅ Threat created:")
        print(f"  Place: {threat.get('place')}")
        print(f"  Coordinates: ({threat.get('lat')}, {threat.get('lng')})")
        print(f"  Source match: {threat.get('source_match')}")
        print(f"  Threat type: {threat.get('threat_type')}")
        
        # Determine which oblast these coordinates are in
        lat, lng = threat.get('lat'), threat.get('lng')
        if lat and lng:
            print(f"\n🗺️ Geographic analysis:")
            print(f"  Coordinates: {lat:.4f}°N, {lng:.4f}°E")
            
            # Known oblast boundaries (approximate)
            oblast_bounds = {
                'харківська': {'lat_range': (49.0, 50.5), 'lng_range': (35.5, 38.5)},
                'вінницька': {'lat_range': (48.5, 49.8), 'lng_range': (27.5, 30.0)},
                'полтавська': {'lat_range': (49.0, 50.5), 'lng_range': (32.0, 35.5)}
            }
            
            for oblast, bounds in oblast_bounds.items():
                lat_in = bounds['lat_range'][0] <= lat <= bounds['lat_range'][1]
                lng_in = bounds['lng_range'][0] <= lng <= bounds['lng_range'][1]
                if lat_in and lng_in:
                    print(f"  ✅ Located in: {oblast.title()} область")
                else:
                    print(f"  ❌ Not in: {oblast.title()} область")
    else:
        print(f"❌ No threat created")

if __name__ == '__main__':
    debug_guti_location()
