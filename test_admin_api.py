#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест админ панели с Ukraine Alert API интеграцией
"""

import requests
import time

def test_admin_api_integration():
    """Тестируем интеграцию API в админ панели"""
    print("🛠️ Тест Ukraine Alert API в админ панели")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # 1. Проверяем админ панель доступна
    try:
        response = requests.get(f"{base_url}/admin")
        if response.status_code == 200:
            print("✅ Админ панель доступна")
            
            # Проверяем наличие новых кнопок в HTML
            if "🇺🇦 API:" in response.text:
                print("✅ Кнопка управления API найдена в HTML")
            else:
                print("❌ Кнопка управления API не найдена")
                
            if "testAPIConnection" in response.text:
                print("✅ Функция тестирования API найдена")
            else:
                print("❌ Функция тестирования API не найдена")
                
        else:
            print(f"❌ Админ панель недоступна: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Сервер не запущен")
        return False
    
    # 2. Проверяем API эндпоинт
    try:
        response = requests.get(f"{base_url}/api_alerts")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API эндпоинт работает")
            print(f"   📊 Всего тревог: {data.get('total_api_alerts', 0)}")
            print(f"   🗺️ С координатами: {data.get('mapped_alerts', 0)}")
            print(f"   📍 Маркеров: {len(data.get('markers', []))}")
        else:
            print(f"❌ API эндпоинт недоступен: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка API эндпоинта: {e}")
    
    # 3. Проверяем комбинированные данные
    try:
        # Симулируем запрос как из админ панели
        telegram_response = requests.get(f"{base_url}/data")
        api_response = requests.get(f"{base_url}/api_alerts")
        
        if telegram_response.status_code == 200 and api_response.status_code == 200:
            telegram_data = telegram_response.json()
            api_data = api_response.json()
            
            telegram_tracks = len(telegram_data.get('tracks', []))
            api_markers = len(api_data.get('markers', []))
            total = telegram_tracks + api_markers
            
            print(f"✅ Комбинированные данные:")
            print(f"   📱 Telegram треки: {telegram_tracks}")
            print(f"   🇺🇦 API маркеры: {api_markers}")
            print(f"   🎯 Итого: {total}")
            
        else:
            print("❌ Не удалось получить комбинированные данные")
            
    except Exception as e:
        print(f"❌ Ошибка комбинированных данных: {e}")
    
    print("\n🎯 Инструкции для админа:")
    print("1. Откройте админ панель: http://localhost:5000/admin")
    print("2. Найдите кнопки '🇺🇦 API: OFF' и '🔗 Test API'")
    print("3. Нажмите '🔗 Test API' для проверки подключения")
    print("4. Нажмите '🇺🇦 API: OFF' чтобы включить (станет '🇺🇦 API: ON')")
    print("5. Нажмите '🔄 Refresh' чтобы увидеть API маркеры на карте")
    
    return True

if __name__ == "__main__":
    test_admin_api_integration()
