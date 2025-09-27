#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_simple_kab():
    print("=== ПРОСТОЙ ТЕСТ КАБ ===")
    
    # Импортируем функцию classify из app.py для прямого тестирования
    from app import process_message
    
    # Найдем функцию classify внутри process_message
    import inspect
    source = inspect.getsource(process_message)
    
    # Прямое тестирование classify
    test_texts = [
        "КАБ по городу",
        "УМПК на позиции", 
        "ФАБ-500",
        "Пуски КАБ"
    ]
    
    print("Тестируем прямую классификацию:")
    for text in test_texts:
        print(f"\nТекст: {text}")
        
        # Пробуем вызвать process_message с отладочной информацией
        try:
            result = process_message(text, "test", "2025-09-27 12:00:00", "test")
            
            if result and len(result) > 0:
                threat_type = result[0].get('threat_type', 'unknown')
                icon = result[0].get('marker_icon', 'unknown')
                print(f"Результат: {threat_type} -> {icon}")
            else:
                print("Результат: отфильтровано или не обработано")
                
        except Exception as e:
            print(f"Ошибка: {e}")

if __name__ == "__main__":
    test_simple_kab()
