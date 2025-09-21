#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test second trajectory message
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_trajectory_2():
    """Test trajectory with 'шахеди' plural."""
    message = "2 шахеди з донеччини на харківщину"
    
    print("🛸 TRAJECTORY MESSAGE TEST 2")
    print("==================================================")
    print(f"Message: '{message}'")
    
    result = process_message(message, 'test_traj_2', '2024-12-21', 'test_channel')
    markers = result if result else []
    
    print(f"\n📍 Results:")
    print(f"Number of markers: {len(markers)}")
    
    if markers:
        for i, marker in enumerate(markers, 1):
            place = marker.get('place', 'N/A')
            source = marker.get('source_match', 'N/A')
            print(f"  {i}. {place} (source: {source})")
    else:
        print("  No markers created")
    
    print(f"\n🔍 Analysis:")
    print(f"This is a TRAJECTORY message: 'з донеччини на харківщину'")
    print(f"Should NOT create markers in city centers")

if __name__ == "__main__":
    test_trajectory_2()
