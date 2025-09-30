#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Детальный тест Ukraine Alert API для понимания формата данных
"""

import requests
import json

# Тестируем разные варианты авторизации
API_TOKEN = "57fe8a39:7698ad50f0f15d502b280a83019bab25"
BASE_URL = "https://api.ukrainealarm.com"

def test_auth_methods():
    """Тестируем разные методы авторизации"""
    
    endpoints = [
        "/api/v3/alerts/status",
        "/api/v3/regions", 
        "/api/v3/alerts"
    ]
    
    auth_methods = [
        {"Authorization": API_TOKEN},
        {"Authorization": f"Bearer {API_TOKEN}"},
        {"Authorization": f"Token {API_TOKEN}"},
        {"Token": API_TOKEN},
        {"X-API-Key": API_TOKEN},
    ]
    
    print("🔍 Тестирование методов авторизации...")
    
    for i, headers in enumerate(auth_methods):
        print(f"\n--- Метод {i+1}: {headers} ---")
        
        for endpoint in endpoints:
            try:
                url = f"{BASE_URL}{endpoint}"
                response = requests.get(url, headers=headers, timeout=5)
                
                print(f"  {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            print(f"    ✅ Список из {len(data)} элементов")
                        elif isinstance(data, dict):
                            print(f"    ✅ Объект с ключами: {list(data.keys())}")
                            
                        # Показать пример данных для успешных запросов
                        if endpoint == "/api/v3/alerts" and data:
                            print("    📋 Пример тревоги:")
                            example = data[0] if isinstance(data, list) else data
                            print(f"    {json.dumps(example, indent=6, ensure_ascii=False)}")
                            
                    except json.JSONDecodeError:
                        print(f"    ✅ Ответ получен, но не JSON")
                        
                elif response.status_code == 401:
                    print(f"    ❌ Неавторизован")
                else:
                    print(f"    ⚠️ Код ошибки: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"  {endpoint}: Ошибка - {e}")

def test_public_endpoints():
    """Тестируем публичные эндпоинты без авторизации"""
    print("\n🌐 Тестирование публичных эндпоинтов...")
    
    public_endpoints = [
        "/api/v3/regions",
        "/api/v3/alerts/status"
    ]
    
    for endpoint in public_endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            
            print(f"  {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"    ✅ Данные получены")
                    
                    if endpoint == "/api/v3/regions" and data:
                        print("    📍 Пример региона:")
                        if "states" in data and data["states"]:
                            example = data["states"][0]
                            print(f"    {json.dumps(example, indent=6, ensure_ascii=False)}")
                    
                except json.JSONDecodeError:
                    print(f"    ❌ Ответ не является JSON")
                    
        except requests.exceptions.RequestException as e:
            print(f"  {endpoint}: Ошибка - {e}")

if __name__ == "__main__":
    test_auth_methods()
    test_public_endpoints()
