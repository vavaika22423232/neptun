#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for multi-shahed message processing bug
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_multi_shahed():
    """Test the specific multi-shahed message that's only showing one marker."""
    print("🔍 MULTI-SHAHED MESSAGE TEST")
    print("=" * 50)
    
    message = """На Харківщині:
1 шахед на Савинці
1 шахед на Гусарівку
1 шахед на Протопопівку"""
    
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
            
        # Expected: 3 markers (Савинці, Гусарівка, Протопопівка)
        expected_cities = ['савинці', 'гусарівка', 'протопопівка']
        if markers:
            found_cities = [marker.get('place', '').lower() for marker in markers]
            # Нормализуем найденные города (убираем винительный падеж)
            normalized_found = []
            for city in found_cities:
                if city.endswith('ку'):
                    normalized_found.append(city[:-2] + 'ка')  # гусарівку -> гусарівка
                elif city.endswith('цях'):
                    normalized_found.append(city[:-2] + 'ці')  # shouldn't happen but just in case
                else:
                    normalized_found.append(city)
            
            print(f"\n🔍 Analysis:")
            print(f"Expected cities: {expected_cities}")
            print(f"Found cities: {found_cities}")
            print(f"Normalized found: {normalized_found}")
            
            missing_cities = [city for city in expected_cities if city not in normalized_found]
            
            if missing_cities:
                print(f"❌ Missing cities: {missing_cities}")
            else:
                print(f"✅ All expected cities found!")
        else:
            print(f"\n🔍 Analysis:")
            print(f"Expected cities: {expected_cities}")
            print(f"Found cities: []")
            print(f"❌ Missing cities: {expected_cities}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_shahed()
