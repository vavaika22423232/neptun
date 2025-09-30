#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест работы с Ukraine Alert API с разными форматами токена
"""

import requests
import json
import base64

# Наш токен содержит двоеточие, возможно это username:password
API_TOKEN = "57fe8a39:7698ad50f0f15d502b280a83019bab25"
BASE_URL = "https://api.ukrainealarm.com"

def test_basic_auth():
    """Тестируем Basic Authentication"""
    print("🔐 Тестирование Basic Authentication...")
    
    # Разделяем токен на username:password
    if ':' in API_TOKEN:
        username, password = API_TOKEN.split(':', 1)
        print(f"   Username: {username}")
        print(f"   Password: {password[:8]}...")
        
        # Создаем Basic Auth заголовок
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
        
        # Тестируем эндпоинты
        endpoints = ["/api/v3/alerts", "/api/v3/regions", "/api/v3/alerts/status"]
        
        for endpoint in endpoints:
            try:
                url = f"{BASE_URL}{endpoint}"
                response = requests.get(url, headers=headers, timeout=10)
                
                print(f"  {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"    ✅ Данные получены!")
                        
                        if endpoint == "/api/v3/alerts" and data:
                            print(f"    📊 Тревог: {len(data)}")
                            if data:
                                print("    📋 Пример тревоги:")
                                example = data[0]
                                print(f"    {json.dumps(example, indent=6, ensure_ascii=False)[:500]}...")
                                
                        elif endpoint == "/api/v3/regions" and data:
                            if "states" in data:
                                print(f"    🏘️ Регионов: {len(data['states'])}")
                                
                    except json.JSONDecodeError as e:
                        print(f"    ❌ JSON ошибка: {e}")
                        
                elif response.status_code == 401:
                    print(f"    ❌ Неавторизован")
                elif response.status_code == 403:
                    print(f"    ❌ Доступ запрещен")
                else:
                    print(f"    ⚠️ Код: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"  {endpoint}: Ошибка - {e}")
                
def test_header_variations():
    """Тестируем различные варианты заголовков"""
    print("\n🔧 Тестирование вариантов заголовков...")
    
    variations = [
        {"Authorization": API_TOKEN},
        {"Authorization": f"Token {API_TOKEN}"},  
        {"X-Authorization": API_TOKEN},
        {"Api-Key": API_TOKEN},
        {"X-Api-Key": API_TOKEN},
    ]
    
    test_endpoint = "/api/v3/alerts"
    
    for i, headers in enumerate(variations):
        try:
            url = f"{BASE_URL}{test_endpoint}"
            response = requests.get(url, headers=headers, timeout=5)
            print(f"  Вариант {i+1} {headers}: {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            print(f"  Вариант {i+1}: Ошибка - {e}")

if __name__ == "__main__":
    test_basic_auth()
    test_header_variations()
