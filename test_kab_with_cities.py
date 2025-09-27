#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_kab_with_cities():
    print("=== ТЕСТ КАБ С ГОРОДАМИ ===")
    
    kab_messages = [
        "КАБ по Харкову",
        "УМПК удар по Сумы", 
        "ФАБ-500 на Полтаву",
        "Пуски КАБ по Днепру"
    ]
    
    for i, message in enumerate(kab_messages, 1):
        print(f"\nТЕСТ {i}: {message}")
        
        try:
            result = process_message(message, f"kab_city_test_{i}", "2025-09-27 12:00:00", "test")
            
            if result and len(result) > 0:
                marker = result[0]
                threat_type = marker.get('threat_type', 'Unknown')
                icon = marker.get('marker_icon', 'Unknown')
                place = marker.get('place', 'Unknown')
                
                print(f"Место: {place}")
                print(f"Тип угрозы: {threat_type}")
                print(f"Иконка: {icon}")
                
                if threat_type == 'kab' and icon == 'rszv.png':
                    print("✅ ПРАВИЛЬНО: КАБ классифицирован с иконкой rszv.png")
                else:
                    print(f"❌ НЕПРАВИЛЬНО: Ожидался kab/rszv.png, получен {threat_type}/{icon}")
            else:
                print("❌ ОТФИЛЬТРОВАНО или ошибка обработки")
                
        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    test_kab_with_cities()
