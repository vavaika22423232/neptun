#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для ручной синхронизации messages.json на сервер
"""

import requests
import json
import os
from datetime import datetime

def upload_messages_to_server():
    """Загружает локальный messages.json на сервер"""
    
    # Читаем локальный файл
    local_file = "messages.json"
    if not os.path.exists(local_file):
        print("❌ Локальный файл messages.json не найден")
        return False
    
    with open(local_file, 'r', encoding='utf-8') as f:
        messages = json.load(f)
    
    print(f"📄 Локальный файл содержит {len(messages)} сообщений")
    
    # Показываем последние сообщения
    if messages:
        print("\n📋 Последние сообщения:")
        for msg in messages[-3:]:
            print(f"  • {msg.get('place', 'N/A')} - {msg.get('date', 'N/A')} - {msg.get('threat_type', 'N/A')}")
    
    # Здесь должна быть логика загрузки на сервер
    # Поскольку у нас нет FTP или SSH доступа, создадим файл для ручной загрузки
    
    # Создаем копию для загрузки
    server_copy = "messages_for_server.json"
    with open(server_copy, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Создан файл {server_copy} для ручной загрузки на сервер")
    print("📁 Загрузите этот файл на сервер как messages.json")
    
    return True

def check_server_data():
    """Проверяет данные на сервере"""
    server_url = "http://195.226.192.65"
    
    try:
        # Проверяем основные эндпоинты
        endpoints = [
            "/data?timeRange=40",
            "/messages.json",
            "/api/messages"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{server_url}{endpoint}", timeout=10)
                print(f"🔗 {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            print(f"   📊 Найдено {len(data)} элементов")
                        elif isinstance(data, dict):
                            if 'tracks' in data:
                                print(f"   📊 Треков: {len(data.get('tracks', []))}")
                            else:
                                print(f"   📊 Ключи: {list(data.keys())}")
                    except:
                        print(f"   📄 Размер ответа: {len(response.text)} символов")
                else:
                    print(f"   ❌ Ошибка: {response.text[:100]}")
            except Exception as e:
                print(f"   ❌ Ошибка подключения: {e}")
        
    except Exception as e:
        print(f"❌ Ошибка проверки сервера: {e}")

if __name__ == "__main__":
    print("🚀 NEPTUN - Синхронизация данных")
    print("=" * 50)
    
    print("\n1️⃣ Проверка локальных данных...")
    upload_messages_to_server()
    
    print("\n2️⃣ Проверка данных на сервере...")
    check_server_data()
    
    print("\n" + "=" * 50)
    print("📋 Рекомендации:")
    print("1. Загрузите messages_for_server.json на сервер как messages.json")
    print("2. Убедитесь, что на сервере запущен daemon для получения новых сообщений")
    print("3. Проверьте права доступа к файлу messages.json на сервере")
