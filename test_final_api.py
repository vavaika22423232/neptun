#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальный тест Ukraine Alert API с получением реальных данных
"""

import requests
import json
from datetime import datetime

API_TOKEN = "57fe8a39:7698ad50f0f15d502b280a83019bab25"
BASE_URL = "https://api.ukrainealarm.com"

def get_current_alerts():
    """Получить текущие тревоги"""
    print("🚨 Получение текущих тревог...")
    
    headers = {"Authorization": API_TOKEN}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v3/alerts", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Получено тревог: {len(data)}")
            
            active_alerts = []
            for alert in data:
                if alert.get("activeAlerts"):
                    active_alerts.extend(alert["activeAlerts"])
                    
                    print(f"\n📍 {alert.get('regionName', 'Неизвестный регион')}")
                    print(f"   Тип: {alert.get('regionType', 'unknown')}")
                    print(f"   ID: {alert.get('regionId', 'unknown')}")
                    print(f"   Обновлено: {alert.get('lastUpdate', 'unknown')}")
                    
                    for active_alert in alert.get("activeAlerts", []):
                        alert_type = active_alert.get("type", "UNKNOWN")
                        last_update = active_alert.get("lastUpdate", "unknown")
                        print(f"   🔴 {alert_type} - {last_update}")
            
            print(f"\n📊 Итого активных тревог: {len(active_alerts)}")
            return data
            
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return None

def get_regions():
    """Получить список регионов"""
    print("\n🏘️ Получение списка регионов...")
    
    headers = {"Authorization": API_TOKEN}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v3/regions", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "states" in data:
                states = data["states"]
                print(f"✅ Получено областей: {len(states)}")
                
                # Показать первые несколько регионов
                for i, state in enumerate(states[:3]):
                    print(f"\n📍 {state.get('regionName', 'Неизвестная область')}")
                    print(f"   ID: {state.get('regionId', 'unknown')}")
                    print(f"   Тип: {state.get('regionType', 'unknown')}")
                    
                    # Показать детей (районы)
                    children = state.get("regionChildIds", [])
                    if children:
                        print(f"   Районов: {len(children)}")
                        if children:
                            first_child = children[0]
                            print(f"   Пример района: {first_child.get('regionName', 'unknown')}")
                
                return data
            else:
                print("❌ Неожиданный формат данных")
                return None
                
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return None

def get_status():
    """Получить статус API"""
    print("\n📈 Получение статуса API...")
    
    headers = {"Authorization": API_TOKEN}
    
    try:
        response = requests.get(f"{BASE_URL}/api/v3/alerts/status", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            last_action = data.get("lastActionIndex", 0)
            print(f"✅ Последнее действие: {last_action}")
            return last_action
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return None

if __name__ == "__main__":
    print("🇺🇦 Ukraine Alert API - Финальный тест")
    print("=" * 50)
    
    # Тестируем все основные функции
    status = get_status()
    regions = get_regions()
    alerts = get_current_alerts()
    
    print("\n" + "=" * 50)
    print("🎯 Результаты тестирования:")
    print(f"   Статус API: {'✅' if status else '❌'}")
    print(f"   Регионы: {'✅' if regions else '❌'}")
    print(f"   Тревоги: {'✅' if alerts else '❌'}")
    
    if alerts and regions:
        print("\n🚀 API готов к интеграции!")
