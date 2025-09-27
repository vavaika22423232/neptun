#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_kab_classification():
    print("=== ТЕСТ КЛАССИФИКАЦИИ КАБов ===")
    
    kab_messages = [
        "Пуски КАБ по Харкову",
        "Удары КАБ-1500 по городу", 
        "Применение УМПК против гражданских объектов",
        "ФАБ-500 с УМПК на Сумы",
        "Керованая авіаційна бомба по району",
        "Авіаційні бомби КАБ-250"
    ]
    
    for i, message in enumerate(kab_messages, 1):
        print(f"\nТЕСТ {i}: {message}")
        
        try:
            result = process_message(message, f"kab_test_{i}", "2025-09-27 12:00:00", "test")
            
            if result and len(result) > 0:
                marker = result[0]
                threat_type = marker.get('threat_type', 'Unknown')
                icon = marker.get('marker_icon', 'Unknown')
                
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
    test_kab_classification()
