#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re

# Добавляем путь к корню проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем функцию обработки сообщений из app.py
from app import process_message

def test_current_message():
    """Тест для сообщения из вопроса пользователя"""
    
    message = """Вінниччина: 
БпЛА на Липовець 

Чернігівщина: 
БпЛА на на Ріпки 

Сумщина:
БпЛА на Терни 

Дніпропетровщина:  
2 БпЛА на Павлоград
ㅤ 
➡Підписатися"""
    
    print("Тестируем сообщение:")
    print(repr(message))
    print("\n" + "="*50)
    
    # Вызываем функцию обработки сообщения
    threats = process_message(message, '12345', '2025-09-30 12:00:00', 'test_channel')
    
    print(f"Найдено угроз: {len(threats)}")
    print("\nДетали угроз:")
    
    for i, threat in enumerate(threats, 1):
        print(f"\n--- Угроза {i} ---")
        for key, value in threat.items():
            print(f"{key}: {value}")
    
    # Проверим, есть ли конкретные города
    if threats:
        threat = threats[0]
        if threat.get('list_only') == True:
            print("\n🚨 ПРОБЛЕМА: Сообщение помечено как list_only=True")
            print("Это означает, что оно будет показано только в списке событий, а не как метки на карте")
            print(f"source_match: {threat.get('source_match')}")
        else:
            print("\n✅ Сообщение должно создать метки на карте")
    
    return threats

if __name__ == "__main__":
    test_current_message()
