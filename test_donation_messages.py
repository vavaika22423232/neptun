#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_donation_messages():
    print("=== ТЕСТ СООБЩЕНИЙ О ДОНАТАХ ===")
    
    donation_messages = [
        "За 10 хвилин на жаль лише 3 донати😞\nОлена, Тарас, Наталія дуже вдячний вам за підтримку❤️",
        "Дякую за донат! Віталій з Києва підтримав канал",
        "Сергій, дуже вдячний за підтримку!",
        "Отримав донати від Марії та Олександра, дякую!",
        "Вдячний вам за підтримку у важкі часи"
    ]
    
    for i, message in enumerate(donation_messages, 1):
        print(f"\nТЕСТ {i}: {message[:40]}...")
        
        try:
            result = process_message(message, f"donation_test_{i}", "2025-09-27 12:00:00", "test")
            
            if result is None or result == []:
                print("✅ ПРАВИЛЬНО: Сообщение отфильтровано")
            else:
                print(f"❌ НЕПРАВИЛЬНО: Создано {len(result)} меток")
                for j, marker in enumerate(result, 1):
                    name = marker.get('place', 'Unknown')
                    print(f"  {j}: {name}")
                    
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_donation_messages()
