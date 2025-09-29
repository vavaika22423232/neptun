#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message
import json

# Тестовые сообщения о тревогах из сообщения пользователя
alarm_messages = [
    "**🚨 Вінницький район (Вінницька обл.)** Повітряна тривога. Прямуйте в укриття!",
    "**🟢 Житомирська обл.** Відбій тривоги. Будьте обережні!",
    "**🚨 Харківський район (Харківська обл.)** Повітряна тривога. Прямуйте в укриття!",
    "**🚨 Звенигородський район (Черкаська обл.)** Повітряна тривога. Прямуйте в укриття!",
    "**🚨 Уманський район (Черкаська обл.)** Повітряна тривога. Прямуйте в укриття!",
    "**🟢 Хмільницький район (Вінницька обл.)** Відбій тривоги. Будьте обережні!",
    "**🚨 Богодухівський район (Харківська обл.)** Повітряна тривога. Прямуйте в укриття!",
    "**🚨 Дніпровський район (Дніпропетровська обл.)** Повітряна тривога. Прямуйте в укриття!"
]

def test_alarm_messages():
    print("=== Тестирование сообщений о тревогах ===\n")
    
    should_be_events = 0  # Количество сообщений которые должны быть событиями
    actual_filtered = 0   # Количество отфильтрованных сообщений
    created_markers = 0   # Количество созданных меток
    
    for i, message in enumerate(alarm_messages, 1):
        print(f"Сообщение {i}: {message[:60]}...")
        
        # Определяем что это тревога или отбой
        if "Повітряна тривога" in message or "🚨" in message:
            message_type = "🚨 ТРЕВОГА"
            should_be_events += 1
        elif "Відбій тривоги" in message or "🟢" in message:
            message_type = "🟢 ОТБОЙ"
            should_be_events += 1
        else:
            message_type = "❓ ДРУГОЕ"
        
        try:
            mid = f"alarm_test_{i}"
            date_str = "2025-09-29 20:00:00"
            channel = "UkraineAlarmSignal"
            
            result = process_message(message, mid, date_str, channel)
            
            if result is None or (isinstance(result, list) and len(result) == 0):
                print(f"   ✅ {message_type} - Отфильтровано (должно быть событием)")
                actual_filtered += 1
            elif isinstance(result, list) and len(result) > 0:
                print(f"   ❌ {message_type} - Создает {len(result)} меток (НЕ должно!)")
                created_markers += len(result)
                for marker in result:
                    place = marker.get('place', 'Unknown')
                    print(f"      📍 {place}")
            else:
                print(f"   ❓ {message_type} - Неожиданный результат: {type(result)}")
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        print()
    
    print("=== ИТОГИ ===")
    print(f"Всего сообщений о тревогах: {len(alarm_messages)}")
    print(f"Должно быть событий: {should_be_events}")
    print(f"Отфильтровано: {actual_filtered}")
    print(f"Создано меток: {created_markers}")
    
    if actual_filtered == should_be_events and created_markers == 0:
        print("🎉 ВСЕ СООБЩЕНИЯ О ТРЕВОГАХ ПРАВИЛЬНО ФИЛЬТРУЮТСЯ!")
    else:
        print("⚠️  Некоторые сообщения о тревогах создают метки вместо событий")

if __name__ == "__main__":
    test_alarm_messages()
