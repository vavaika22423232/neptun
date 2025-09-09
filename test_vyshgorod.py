#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_vyshgorod_message():
    # Повідомлення користувача
    message = "вишгородський р-н київська обл.- загроза застосування ворогом ударних бпла. | 1 БпЛА на Київщину вектором на водосховище"
    
    print("=== Тестування Вишгородського району ===")
    print(f"Повідомлення:\n{message}\n")
    
    # Викликати process_message
    tracks = process_message(message, "vyshgorod_test", "2024-01-01 12:00:00", "test_channel")
    
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
            text = track.get('text', '')[:100] + ('...' if len(track.get('text', '')) > 100 else '')
            
            print(f"🔹 Маркер {i}: {place}")
            print(f"   📍 Координати: ({lat}, {lon})")
            print(f"   🎯 Джерело: {source}")
            print(f"   🖼️ Іконка: {icon}")
            print(f"   📝 Текст: {text}")
            print()
            
            # Перевірити чи це Київ
            if lat and lon:
                kyiv_lat, kyiv_lon = 50.4501, 30.5234  # Координати Києва
                if abs(lat - kyiv_lat) < 0.1 and abs(lon - kyiv_lon) < 0.1:
                    print(f"   ⚠️  ПРОБЛЕМА: Маркер в Києві замість Вишгородського району!")
                elif 'вишгород' in place.lower():
                    print(f"   ✅ ПРАВИЛЬНО: Маркер у Вишгороді")
                else:
                    print(f"   ❓ Невідоме місце: {place}")
        
    else:
        print("❌ Маркери не створені")

if __name__ == "__main__":
    test_vyshgorod_message()
