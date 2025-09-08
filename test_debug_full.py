#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_debug_full():
    # Оригінальне повідомлення
    original = """🛵 Інформація щодо руху ворожих ударних БпЛА:
1. БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина);
2. БпЛА на сході Чернігівщини курсом на н.п.Батурин.
3. БпЛА на південному заході Дніпропетровщини, курс - południowy-західний/південно-східний."""
    
    print("=== Дебаг повного повідомлення ===")
    print(f"Текст:\n{original}\n")
    print("="*50)
    
    # Викликати process_message з дебагом
    tracks = process_message(original, "debug_test", "2024-01-01 12:00:00", "test_channel")
    
    print("="*50)
    if tracks:
        print(f"✅ Отримано маркерів: {len(tracks)}")
        for j, track in enumerate(tracks, 1):
            place = track.get('place', track.get('name', 'Unknown'))
            lat = track.get('lat')
            lon = track.get('lon', track.get('lng'))
            source = track.get('source_match', 'unknown')
            print(f"  {j}. {place} ({lat}, {lon}) ({source})")
    else:
        print("❌ Маркери не створені")
    
    print("\n=== Перевірка окремих рядків ===")
    lines = [
        "1. БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина)",
        "2. БпЛА на сході Чернігівщини курсом на н.п.Батурин",
        "3. БпЛА на південному заході Дніпропетровщини, курс - південно-західний/південно-східний"
    ]
    
    for i, line in enumerate(lines, 1):
        print(f"\nРядок {i}: {line}")
        line_tracks = process_message(line, f"line_{i}", "2024-01-01 12:00:00", "test_channel")
        if line_tracks:
            for track in line_tracks:
                place = track.get('place', track.get('name', 'Unknown'))
                source = track.get('source_match', 'unknown')
                print(f"  -> {place} ({source})")
        else:
            print("  -> Немає маркерів")

if __name__ == "__main__":
    test_debug_full()
