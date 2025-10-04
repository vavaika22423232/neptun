#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

# Test the actual API endpoint
test_message = """Сумщина:
БпЛА курсом на Липову Долину 

Чернігівщина:
2х БпЛА курсом на Сосницю
БпЛА курсом на Батурин
2х БпЛА курсом на Борзну 
БпЛА курсом на Ічню
БпЛА курсом на Парафіївку
БпЛА курсом на Козелець
БпЛА курсом на Ягідне 
БпЛА курсом на Куликівку

Харківщина:
БпЛА курсом на Балаклію
6х БпЛА курсом на Нову Водолагу 
3х БпЛА курсом на Бірки 
2х БпЛА курсом на Донець
3х БпЛА курсом на Златопіль
2х БпЛА курсом на Сахновщину 
БпЛА курсом на Орільку
БпЛА курсом на Зачепилівку
БпЛА курсом на Слобожанське 
БпЛА курсом на Берестин
БпЛА курсом на Савинці 
БпЛА курсом на Краснокутськ
БпЛА курсом на Чугуїв 
БпЛА курсом на Андріївку

Полтавщина:
БпЛА курсом на Великі Сорочинці 
БпЛА курсом на Миргород 
БпЛА курсом на Полтаву 
БпЛА курсом на Карлівку
БпЛА курсом на Машівку
БпЛА курсом на Нові Санжари 
БпЛА курсом на Решетилівку 
БпЛА курсом на Глобине
БпЛА курсом на Котельву 

Дніпропетровщина:
БпЛА курсом на Софіївку
БпЛА курсом на Томаківку
БпЛА курсом на Петриківку
2х БпЛА курсом на Юріївку
БпЛА курсом на Магдалинівку 
БпЛА курсом на Царичанку 
2х БпЛА курсом на Верхньодніпровськ 
Розвідувальний БпЛА в районі Славгорода

Донеччина:
БпЛА курсом на Білозерське
ㅤ 
➡Підписатися"""

print("=== ТЕСТ API ЭНДПОИНТА ===")

try:
    # Test locally first
    url = "http://localhost:5000/api/test_process_message"
    
    data = {
        "text": test_message,
        "date": "2025-10-04T12:00:00Z",
        "channel": "test_channel"
    }
    
    print(f"Отправляю запрос на {url}")
    print(f"Длина сообщения: {len(test_message)} символов")
    print()
    
    response = requests.post(url, json=data, timeout=30)
    
    print(f"Статус ответа: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Количество найденных меток: {len(result.get('markers', []))}")
        
        if result.get('markers'):
            print("\nНайденные метки:")
            for i, marker in enumerate(result['markers'][:10], 1):  # Первые 10
                print(f"  {i}. {marker.get('place', 'Неизвестно')} - {marker.get('source_match', 'N/A')}")
            
            if len(result['markers']) > 10:
                print(f"  ... и еще {len(result['markers']) - 10} меток")
        else:
            print("❌ Метки не найдены!")
            
        # Show debug logs if available
        if result.get('debug_logs'):
            print(f"\nОтладочные логи ({len(result['debug_logs'])}):")
            for log in result['debug_logs'][-10:]:  # Последние 10
                print(f"  [{log.get('category', 'general')}] {log.get('message', '')}")
                
    else:
        print(f"Ошибка: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Не удается подключиться к локальному серверу")
    print("Убедитесь, что сервер запущен командой: python3 app.py")
except Exception as e:
    print(f"Ошибка: {e}")
