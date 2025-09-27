#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_non_threat_messages():
    print("=== ТЕСТ НЕТАКТИЧЕСКИХ СООБЩЕНИЙ ===")
    
    non_threat_messages = [
        # Сбор средств
        "👀Ніч буде важкою, залишатимуся з вами друзі вночі, моніторитиму заради вашої безпеки, підтримайте мене по 5-10-15 грн на каву та енергетики",
        
        # Информационные без угрозы
        "Здійснив посадку на аеродром \"Енгельс-2\"",
        
        # Реклама канала
        "✙ Напрямок ракет ✙\n✙Підтримати канал✙",
        
        # Передислокация
        "🪿Передислокація Ту-160 з Українки на \"Енгельс-2\"",
        
        # Общая информация
        "Наразі це єдина фактична активність бортів. В разі додаткової інформації - буду оновлювати"
    ]
    
    for i, message in enumerate(non_threat_messages, 1):
        print(f"\nТЕСТ {i}: {message[:50]}...")
        print(f"Полное сообщение: {message}")
        
        try:
            result = process_message(message, f"non_threat_test_{i}", "2025-09-27 12:00:00", "test")
            
            if result is None or result == []:
                print("✅ ПРАВИЛЬНО: Сообщение отфильтровано")
            else:
                print(f"❌ НЕПРАВИЛЬНО: Создано {len(result)} меток")
                for j, marker in enumerate(result, 1):
                    name = marker.get('place', 'Unknown')
                    coords = f"({marker.get('lat', 'N/A')}, {marker.get('lng', 'N/A')})"
                    print(f"  {j}: {name} - {coords}")
                    
        except Exception as e:
            print(f"Ошибка: {e}")
        
        print("-" * 60)

if __name__ == "__main__":
    test_non_threat_messages()
