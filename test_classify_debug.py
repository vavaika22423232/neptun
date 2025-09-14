#!/usr/bin/env python3
import sys
sys.path.append('.')
from app import process_message

def test_classify_function():
    print("🔍 Тестируем функцию classify...")
    
    # Импортируем функцию classify из модуля app
    import app
    
    test_message = "🚀Дніпропетровська область (Синельниківський р-н) - загроза застосування авіаційних засобів ураження!"
    
    print(f"📝 Тестовое сообщение:")
    print(f"{repr(test_message)}")
    print()
    
    # Попробуем найти и вызвать функцию classify
    # Ищем определение функции в process_message
    print("🔍 Проверяем содержимое сообщения:")
    l = test_message.lower()
    print(f"   Содержит 🚀: {'🚀' in test_message}")
    print(f"   Содержит 'авіаційн': {'авіаційн' in l}")
    print(f"   Содержит 'засоб': {'засоб' in l}")
    print(f"   Содержит 'ураж': {'ураж' in l}")
    print(f"   Содержит 'бпла': {'бпла' in l}")
    print(f"   Содержит 'дрон': {'дрон' in l}")
    print(f"   Содержит 'шахед': {'шахед' in l}")
    
    print(f"\n🔍 Логика классификации:")
    print(f"   1. Проверка на БПЛА/дроны: {any(k in l for k in ['shahed','шахед','шахеді','шахедів','geran','герань','дрон','дрони','бпла','uav'])}")
    print(f"   2. Проверка на авиацию: {('авіаційн' in l and ('засоб' in l or 'ураж' in l))}")
    print(f"   3. Проверка на ракеты (🚀): {'🚀' in test_message}")
    
    # Попробуем вручную обработать это сообщение с отладкой
    print(f"\n🔍 Полная обработка сообщения:")
    result = process_message(test_message, "test_mid", "2024-09-14", "test_channel")
    
    if result and len(result) > 0:
        threat = result[0]
        threat_type = threat.get('threat_type', 'N/A')
        icon = threat.get('marker_icon', 'N/A')
        source = threat.get('source_match', 'N/A')
        
        print(f"   Результат классификации:")
        print(f"   - Тип угрозы: {threat_type}")
        print(f"   - Иконка: {icon}")
        print(f"   - Источник: {source}")

if __name__ == "__main__":
    test_classify_function()
