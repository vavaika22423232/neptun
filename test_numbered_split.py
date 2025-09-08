#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_numbered_split():
    # Оригінальне повідомлення
    original = """🛵 Інформація щодо руху ворожих ударних БпЛА:
1. БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина);
2. БпЛА на сході Чернігівщини курсом на н.п.Батурин.
3. БпЛА на південному заході Дніпропетровщини, курс - південно-західний/південно-східний."""
    
    # Різні варіанти розбиття
    test_variants = [
        ("Оригінал", original),
        ("Рядок 1", "1. БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина)"),
        ("Рядок 2", "2. БпЛА на сході Чернігівщини курсом на н.п.Батурин"),
        ("Рядок 3", "3. БпЛА на південному заході Дніпропетровщини, курс - південно-західний/південно-східний"),
        ("Без номерів", "БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина)"),
        ("Без номерів 2", "БпЛА на сході Чернігівщини курсом на н.п.Батурин"),
    ]
    
    print("=== Тестування нумерованого розбиття ===")
    
    for name, message in test_variants:
        print(f"\n--- {name}: ---")
        print(f"Текст: '{message[:100]}{'...' if len(message) > 100 else ''}'")
        
        # Викликати process_message
        tracks = process_message(message, f"test_{name}", "2024-01-01 12:00:00", "test_channel")
        
        if tracks:
            print(f"✅ Маркерів: {len(tracks)}")
            for j, track in enumerate(tracks, 1):
                place = track.get('place', track.get('name', 'Unknown'))
                lat = track.get('lat')
                lon = track.get('lon', track.get('lng'))
                source = track.get('source_match', 'unknown')
                print(f"  {j}. {place} ({lat}, {lon}) ({source})")
        else:
            print("❌ Маркери не створені")

if __name__ == "__main__":
    test_numbered_split()
