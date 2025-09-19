#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_single_drone_message():
    """Test processing of a single drone message to see where it's handled."""
    
    text = "7х БпЛА курсом на Смілу"
    
    print("=== Отладка обработки одного сообщения ===")
    print(f"Текст: {text}")
    
    result = process_message(text, "test_single", "2025-09-19 23:15:00", "test_channel")
    
    print(f"\nРезультат: {result}")
    
    if isinstance(result, list) and result:
        for i, item in enumerate(result):
            print(f"Трек {i+1}:")
            print(f"  id: {item.get('id')}")
            print(f"  place: {item.get('place')}")
            print(f"  count: {item.get('count')}")
            print(f"  source_match: {item.get('source_match')}")
            print(f"  lat/lng: {item.get('lat')}, {item.get('lng')}")
            print()

if __name__ == "__main__":
    test_single_drone_message()
