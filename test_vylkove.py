#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_vylkove():
    # Тест Вилково окремо
    test_messages = [
        "БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина)",
        "БпЛА курсом на н.п.Вилково (Одещина)",
        "БпЛА курсом на Вилково (Одещина)",
        "БпЛА курсом на Вилково",
        "БпЛА курсом на н.п.Вилково"
    ]
    
    print("=== Тестування Вилково ===")
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Варіант {i}: ---")
        print(f"Текст: '{message}'")
        
        # Викликати process_message
        tracks = process_message(message, f"test_{i}", "2024-01-01 12:00:00", "test_channel")
        
        if tracks:
            print(f"✅ Маркерів: {len(tracks)}")
            for j, track in enumerate(tracks, 1):
                place = track.get('place', track.get('name', 'Unknown'))
                lat = track.get('lat')
                lon = track.get('lon', track.get('lng'))
                source = track.get('source_match', 'unknown')
                print(f"  {j}. {place} ({lat}, {lon}) ({source})")
                if 'вилков' in place.lower():
                    print(f"     ✅ ПРАВИЛЬНО: Знайдено Вилково")
                else:
                    print(f"     ❌ ПОМИЛКА: Не знайдено Вилково, знайдено {place}")
        else:
            print("❌ Маркери не створені")

if __name__ == "__main__":
    test_vylkove()
