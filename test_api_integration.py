#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест интеграции Ukraine Alert API с нашим приложением
"""

import requests
import json
import time

def test_api_endpoint():
    """Тестируем новый эндпоинт /api_alerts"""
    print("🧪 Тестирование эндпоинта /api_alerts...")
    
    try:
        # Предполагаем, что сервер запущен локально
        response = requests.get("http://localhost:5000/api_alerts", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Эндпоинт работает!")
            print(f"📊 Всего тревог из API: {data.get('total_api_alerts', 0)}")
            print(f"🗺️ Тревог с координатами: {data.get('mapped_alerts', 0)}")
            print(f"⏰ Время получения: {time.ctime(data.get('timestamp', 0))}")
            
            markers = data.get('markers', [])
            if markers:
                print(f"\n📍 Примеры маркеров:")
                for i, marker in enumerate(markers[:3]):
                    print(f"   {i+1}. {marker.get('region', 'Unknown')} ({marker.get('lat', 0):.4f}, {marker.get('lng', 0):.4f})")
                    print(f"      Тип: {marker.get('threat_type', 'unknown')}")
                    print(f"      Время: {marker.get('timestamp', 'unknown')}")
            
            return True
            
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Сервер не запущен. Запустите приложение с помощью:")
        print("   python app.py")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_direct_api():
    """Тестируем прямой вызов функции API"""
    print("\n🔍 Тестирование прямого вызова API...")
    
    try:
        from ukraine_alert_api import get_api_alerts_for_map
        
        markers = get_api_alerts_for_map()
        print(f"✅ Получено маркеров: {len(markers)}")
        
        if markers:
            print(f"\n📋 Пример маркера:")
            example = markers[0]
            for key, value in example.items():
                if key != 'api_data':
                    print(f"   {key}: {value}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    print("🇺🇦 Тест интеграции Ukraine Alert API")
    print("=" * 50)
    
    # Тест прямого вызова API
    direct_ok = test_direct_api()
    
    # Тест эндпоинта
    endpoint_ok = test_api_endpoint()
    
    print("\n" + "=" * 50)
    print("🎯 Результаты:")
    print(f"   Прямой API: {'✅' if direct_ok else '❌'}")
    print(f"   Эндпоинт: {'✅' if endpoint_ok else '❌'}")
    
    if direct_ok and endpoint_ok:
        print("\n🚀 Интеграция готова!")
    elif direct_ok:
        print("\n⚠️ API работает, но нужно запустить сервер для тестирования эндпоинта")
    else:
        print("\n❌ Требуется отладка API")
