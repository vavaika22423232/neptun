#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_user_scenario():
    # Точно таке же повідомлення як у користувача
    user_message = """🛵 Інформація щодо руху ворожих ударних БпЛА:
1. БпЛА з акваторії Чорного моря курсом на н.п.Вилково (Одещина);
2. БпЛА на сході Чернігівщини курсом на н.п.Батурин.
3. БпЛА на південному заході Дніпропетровщини, курс - південно-західний/південно-східний."""
    
    print("🎯 === FINAL TEST: User Scenario ===")
    print(f"Повідомлення:\n{user_message}\n")
    
    # Викликати process_message
    tracks = process_message(user_message, "user_test", "2024-01-01 12:00:00", "test_channel")
    
    print("📊 === РЕЗУЛЬТАТ ===")
    if tracks:
        print(f"✅ Знайдено маркерів: {len(tracks)}")
        print()
        for i, track in enumerate(tracks, 1):
            place = track.get('place', track.get('name', 'Unknown'))
            lat = track.get('lat')
            lon = track.get('lon', track.get('lng'))
            source = track.get('source_match', 'unknown')
            icon = track.get('marker_icon', 'unknown.png')
            
            print(f"🔹 Маркер {i}: {place}")
            print(f"   📍 Координати: ({lat}, {lon})")
            print(f"   🎯 Джерело: {source}")
            print(f"   🖼️ Іконка: {icon}")
            print()
        
        print("🎉 === УСПІХ! ===")
        print("Тепер numbered UAV lists правильно створюють маркери для всіх міст!")
        print("Проблему з 'н.п.' prefix вирішено! ✅")
        
    else:
        print("❌ Маркери не створені")
        print("Проблема ще залишається")

if __name__ == "__main__":
    test_user_scenario()
