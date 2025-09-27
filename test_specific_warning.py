#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест конкретного сообщения о ночном предупреждении
"""

import sys
sys.path.append('.')

try:
    from app import process_message
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def test_specific_warning():
    # Точное сообщение из примера пользователя
    message = "протягом ночі уважним бути києву, київщина і західна україна. український ппошник"
    
    print("=== ТЕСТ КОНКРЕТНОГО ПРЕДУПРЕЖДЕНИЯ ===")
    print(f"Сообщение: {message}")
    print(f"Длина: {len(message)} символов")
    print()
    
    # Анализируем содержимое
    lower = message.lower()
    
    print("Анализ содержимого:")
    print(f"- Содержит 'протягом ночі уважним бути': {'протягом ночі уважним бути' in lower}")
    print(f"- Содержит 'києву, київщина і західна україна': {'києву, київщина і західна україна' in lower}")
    print(f"- Длина < 50: {len(message.strip()) < 50}")
    print()
    
    # Тестируем процессинг  
    try:
        result = process_message(message, "specific_test", "2025-09-27 12:00:00", "test")
        
        if result is None or (isinstance(result, list) and len(result) == 0):
            print("✅ ОТФИЛЬТROVANO")
        else:
            print(f"❌ НЕ ОТФИЛЬТРОВАНО - создано {len(result)} меток")
            for i, marker in enumerate(result):
                print(f"  {i+1}: {marker.get('place', 'N/A')} - {marker.get('lat')}, {marker.get('lng')}")
                
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_specific_warning()
