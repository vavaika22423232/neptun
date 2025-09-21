#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test various message types to ensure trajectory fix doesn't break other patterns
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_various_patterns():
    """Test multiple message types."""
    print("🧪 COMPREHENSIVE MESSAGE TESTS")
    print("=" * 60)
    
    test_cases = [
        # Trajectory messages (should create NO markers)
        ("6 шахедів з полтавщини на київщину/черкащину", "❌ Trajectory - no markers"),
        ("2 шахеди з донеччини на харківщину", "❌ Trajectory - no markers"),
        
        # Regular multi-city messages (should create markers)
        ("На Харківщині: 1 шахед на Савинці, 1 шахед на Гусарівку", "✅ Multi-city - create markers"),
        ("Сумщина: шахед на Конотоп", "✅ Single city - create marker"),
        
        # Mixed patterns
        ("Полтавщина, Київщина - шахеди", "✅ Multi-region threat - create markers"),
    ]
    
    for i, (message, expected) in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {expected} ---")
        print(f"Message: '{message}'")
        
        try:
            result = process_message(message, f'test_{i}', '2024-12-21', 'test_channel')
            markers = result
            
            marker_count = len(markers) if markers else 0
            print(f"Result: {marker_count} markers created")
            
            if markers:
                for j, marker in enumerate(markers, 1):
                    place = marker.get('place', 'N/A')
                    source = marker.get('source_match', 'N/A')
                    print(f"  {j}. {place} (source: {source})")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_various_patterns()
