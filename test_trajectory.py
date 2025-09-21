#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for trajectory message processing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_trajectory():
    """Test the trajectory message that creates wrong markers."""
    print("🛸 TRAJECTORY MESSAGE TEST")
    print("=" * 50)
    
    message = "6 шахедів з полтавщини на київщину/черкащину"
    
    print(f"Message: '{message}'")
    
    try:
        result = process_message(message, 'test_123', '2024-12-21', 'test_channel')
        
        # Extract markers
        markers = result
        
        print(f"\n📍 Results:")
        print(f"Number of markers: {len(markers) if markers else 0}")
        
        if markers:
            for i, marker in enumerate(markers, 1):
                place = marker.get('place', 'N/A')
                lat = marker.get('lat', 'N/A')
                lng = marker.get('lng', marker.get('lon', 'N/A'))
                source = marker.get('source_match', 'N/A')
                threat = marker.get('threat_type', 'N/A')
                
                print(f"  Marker {i}: {place}")
                print(f"    Coordinates: ({lat}, {lng})")
                print(f"    Threat Type: {threat}")
                print(f"    Source: {source}")
        else:
            print("  No markers created")
            
        print(f"\n🔍 Analysis:")
        print(f"This is a TRAJECTORY message: 'з полтавщини на київщину/черкащину'")
        print(f"Should NOT create markers in city centers, but rather:")
        print(f"- Show trajectory path, OR")
        print(f"- Create markers at border areas, OR") 
        print(f"- Not create markers at all for regional trajectories")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_trajectory()
