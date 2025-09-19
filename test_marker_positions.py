#!/usr/bin/env python3
"""
Test script to verify that multiple drone markers are positioned with proper offsets
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_multiple_drone_positions():
    """Test that multiple drones create separate markers with different coordinates"""
    
    test_cases = [
        {
            'text': '7х БпЛА курсом на Смілу',
            'expected_count': 7,
            'description': '7 drones to Smila'
        },
        {
            'text': '3х БпЛА курсом на Кагарлик',
            'expected_count': 3,
            'description': '3 drones to Kagarlyk'
        },
        {
            'text': '5 шахедів на Київ',
            'expected_count': 5,
            'description': '5 Shaheds to Kyiv'
        }
    ]
    
    print("=== Testing Multiple Drone Marker Positions ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['description']}")
        print(f"Text: {test_case['text']}")
        
        # Process the message
        result = process_message(
            text=test_case['text'],
            mid=f"test_{i}",
            date_str="2025-09-19 12:00:00",
            channel="test_channel"
        )
        
        if not result:
            print("❌ No result returned")
            continue
            
        if not isinstance(result, list):
            print("❌ Result is not a list")
            continue
            
        actual_count = len(result)
        expected_count = test_case['expected_count']
        
        print(f"Expected markers: {expected_count}")
        print(f"Actual markers: {actual_count}")
        
        if actual_count == expected_count:
            print("✅ Correct number of markers created")
            
            # Check that coordinates are different for multiple markers
            if actual_count > 1:
                coordinates = [(track['lat'], track['lng']) for track in result]
                unique_coordinates = set(coordinates)
                
                if len(unique_coordinates) == actual_count:
                    print("✅ All markers have unique coordinates")
                    
                    # Print coordinate details
                    for j, track in enumerate(result):
                        print(f"  Marker {j+1}: {track['place']} at ({track['lat']:.6f}, {track['lng']:.6f})")
                        
                else:
                    print(f"❌ Some markers have identical coordinates")
                    print(f"  Unique positions: {len(unique_coordinates)} out of {actual_count}")
            else:
                print("ℹ️  Single marker, no overlap check needed")
                track = result[0]
                print(f"  Marker: {track['place']} at ({track['lat']:.6f}, {track['lng']:.6f})")
        else:
            print("❌ Incorrect number of markers")
            
        print("-" * 50)

if __name__ == "__main__":
    test_multiple_drone_positions()
