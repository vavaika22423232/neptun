#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_alert_messages():
    print("=== ТЕСТ СООБЩЕНИЙ О ТРЕВОГАХ ===")
    
    test_messages = [
        "🟢 Конотопський район (Сумська обл.)\nВідбій тривоги. Будьте обережні!",
        "🟢 Роменський район (Сумська обл.)\nВідбій тривоги. Будьте обережні!",
        "🚨 Шосткинський район (Сумська обл.)\nПовітряна тривога. Прямуйте в укриття!"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nТЕСТ {i}: {message[:50]}...")
        print(f"Полное сообщение: {message}")
        
        try:
            result = process_message(message, f"alert_test_{i}", "2025-09-27 12:00:00", "test")
            
            if result is None or result == []:
                print("✅ ОТФИЛЬТРОВАНО - правильно, не должно быть на карте")
            else:
                print(f"❌ НЕ ОТФИЛЬТРОВАНО - создано {len(result)} меток")
                for j, marker in enumerate(result, 1):
                    name = marker.get('name', 'Unknown')
                    coords = marker.get('coordinates', 'No coords')
                    print(f"  {j}: {name} - {coords}")
                    
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print("-" * 60)

if __name__ == "__main__":
    test_alert_messages()
