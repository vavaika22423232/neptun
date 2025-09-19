#!/usr/bin/env python3
"""
Test script to verify oblast-specific city coordinate resolution
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_oblast_specific_cities():
    """Test that cities with oblast context are resolved to correct coordinates"""
    
    test_cases = [
        {
            'text': '🛸 Срібне (Чернігівська обл.) Загроза застосування БПЛА. Перейдіть в укриття! | 2х БпЛА курсом на Срібне | 2 шахеди на срібне',
            'expected_city': 'Срібне',
            'expected_oblast': 'Чернігівська',
            'expected_lat_range': (51.0, 51.3),  # Should be in Chernihiv oblast, not Donetsk
            'description': 'Срібне should resolve to Chernihiv oblast'
        },
        {
            'text': '🛸 Златопіль (Харківська обл.) Загроза застосування БПЛА. Перейдіть в укриття! | БпЛА курсом на Златопіль | 1 шахед на Златопіль',
            'expected_city': 'Златопіль',
            'expected_oblast': 'Харківська',
            'expected_lat_range': (49.5, 50.5),  # Should be in Kharkiv oblast, not Donetsk
            'description': 'Златопіль should resolve to Kharkiv oblast'
        }
    ]
    
    print("=== Testing Oblast-Specific City Resolution ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['description']}")
        print(f"Text: {test_case['text'][:100]}...")
        
        # Process the message
        result = process_message(
            text=test_case['text'],
            mid=f"test_oblast_{i}",
            date_str="2025-09-19 12:00:00",
            channel="test_channel"
        )
        
        if not result:
            print("❌ No result returned")
            continue
            
        if not isinstance(result, list):
            print("❌ Result is not a list")
            continue
            
        if len(result) == 0:
            print("❌ No tracks returned")
            continue
        
        # Check all tracks for correct coordinates
        correct_tracks = 0
        total_tracks = len(result)
        
        for track in result:
            lat = track.get('lat')
            lng = track.get('lng')
            place = track.get('place', '')
            
            if lat is None or lng is None:
                print(f"❌ Track missing coordinates: {place}")
                continue
                
            lat_min, lat_max = test_case['expected_lat_range']
            
            if lat_min <= lat <= lat_max:
                correct_tracks += 1
                print(f"✅ Correct coordinates for {place}: ({lat:.4f}, {lng:.4f})")
            else:
                print(f"❌ Wrong coordinates for {place}: ({lat:.4f}, {lng:.4f}) - should be in range {test_case['expected_lat_range']}")
        
        if correct_tracks == total_tracks:
            print(f"✅ All {total_tracks} tracks have correct oblast coordinates")
        else:
            print(f"❌ Only {correct_tracks}/{total_tracks} tracks have correct coordinates")
            
        print("-" * 70)

if __name__ == "__main__":
    test_oblast_specific_cities()
