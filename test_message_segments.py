#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug complex multi-regional message by testing individual segments
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_message_segments():
    print("=== Тестування окремих сегментів складного повідомлення ===")
    
    # Розділимо повідомлення на логічні частини
    segments = [
        "чернігівщина (новгород-сіверський р-н) та одещина - загроза застосування ворогом ударних бпла.",
        "одещина - шахеди на вилково",
        "група 8х бпла у напрямку ізмаїльського району одещини, вилкове.",
        # Додаткові тести
        "чернігівщина (новгород-сіверський р-н) - бпла",
        "новгород-сіверський р-н - бпла"
    ]
    
    for i, segment in enumerate(segments, 1):
        print(f"\n📍 Сегмент {i}: '{segment}'")
        
        result = process_message(segment, f"test_segment_{i}", "2025-09-08 12:00:00", "test_channel")
        
        if result and isinstance(result, list):
            print(f"  ✅ Маркерів: {len(result)}")
            for j, marker in enumerate(result, 1):
                place = marker.get('place', 'N/A')
                coords = (marker.get('lat'), marker.get('lng'))
                source = marker.get('source_match', 'N/A')
                print(f"    {j}. {place} {coords} ({source})")
        else:
            print(f"  ❌ Маркери не створені")
    
    # Тест pipe-separated обробки
    print(f"\n" + "="*60)
    print("📍 Тест pipe-separated повідомлення:")
    
    pipe_message = "одещина - шахеди на вилково | група 8х бпла у напрямку ізмаїльського району одещини, вилкове."
    print(f"Повідомлення: {pipe_message}")
    
    result = process_message(pipe_message, "test_pipe", "2025-09-08 12:00:00", "test_channel")
    
    if result and isinstance(result, list):
        print(f"  ✅ Маркерів: {len(result)}")
        for j, marker in enumerate(result, 1):
            place = marker.get('place', 'N/A')
            coords = (marker.get('lat'), marker.get('lng'))
            source = marker.get('source_match', 'N/A')
            print(f"    {j}. {place} {coords} ({source})")
    else:
        print(f"  ❌ Маркери не створені")

if __name__ == "__main__":
    test_message_segments()
