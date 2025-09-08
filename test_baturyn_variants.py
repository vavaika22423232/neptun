#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Baturyn city detection variants
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_baturyn_variants():
    print("=== Тестування варіантів Батурин ===")
    
    variants = [
        "БпЛА курсом на батурин",
        "БпЛА курсом на н.п.батурин", 
        "БпЛА курсом на н.п.Батурин",
        "БпЛА на сході Чернігівщини курсом на н.п.Батурин",
        "БпЛА курсом на Батурин",
        "БпЛА на батурин"
    ]
    
    for i, variant in enumerate(variants, 1):
        print(f"\n--- Варіант {i}: ---")
        print(f"Текст: '{variant}'")
        
        result = process_message(variant, f"test_baturyn_{i}", "2025-09-09 12:00:00", "test_channel")
        
        if result and isinstance(result, list):
            print(f"✅ Маркерів: {len(result)}")
            for j, marker in enumerate(result, 1):
                place = marker.get('place', 'N/A')
                coords = (marker.get('lat'), marker.get('lng'))
                source = marker.get('source_match', 'N/A')
                print(f"  {j}. {place} {coords} ({source})")
                if 'батурин' in place.lower():
                    print(f"     ✅ ПРАВИЛЬНО: Знайдено Батурин")
                else:
                    print(f"     ❌ ПОМИЛКА: Не знайдено Батурин")
        else:
            print("❌ Маркери не створені")

if __name__ == "__main__":
    test_baturyn_variants()
