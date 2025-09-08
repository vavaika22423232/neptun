#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug complex message processing step by step
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def test_full_complex_message():
    print("=== Тестування повного складного повідомлення з DEBUG ===")
    
    test_message = """чернігівщина (новгород-сіверський р-н) та одещина - загроза застосування ворогом ударних бпла. | одещина - шахеди на вилково
ㅤ | група 8х бпла у напрямку ізмаїльського району одещини, вилкове."""
    
    print(f"Повідомлення:")
    print(repr(test_message))
    print()
    
    result = process_message(test_message, "test_full_debug", "2025-09-08 12:00:00", "test_channel")
    
    if result and isinstance(result, list):
        print(f"✅ Маркерів: {len(result)}")
        for i, marker in enumerate(result, 1):
            place = marker.get('place', 'N/A')
            coords = (marker.get('lat'), marker.get('lng'))
            source = marker.get('source_match', 'N/A')
            icon = marker.get('marker_icon', 'N/A')
            
            print(f"  {i}. Місце: {place}")
            print(f"     Координати: {coords}")
            print(f"     Джерело: {source}")
            print(f"     Іконка: {icon}")
    else:
        print("❌ Маркери не створені")

if __name__ == "__main__":
    test_full_complex_message()
