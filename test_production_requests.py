#!/usr/bin/env python3
"""
Simple test script to check production parsing via requests.
"""

import requests
import json

def test_production_parse():
    url = "https://neptun-7ua9.onrender.com/debug_parse"
    
    # Simple message first
    simple_message = "БпЛА курсом на Суми"
    
    data = {
        "text": simple_message,
        "mid": "test_simple", 
        "date": "2025-09-02 12:00:00",
        "channel": "napramok"
    }
    
    print("Testing simple message...")
    print(f"Text: {simple_message}")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Tracks count: {result.get('count', 'N/A')}")
            print(f"Success: {result.get('ok', 'N/A')}")
            
            if result.get('tracks'):
                for i, track in enumerate(result['tracks'][:3]):
                    place = track.get('place', 'N/A')
                    icon = track.get('marker_icon', 'N/A')
                    print(f"  {i+1}. {place} [{icon}]")
                    
            return result.get('count', 0)
        else:
            print(f"Error: {response.text}")
            return 0
            
    except Exception as e:
        print(f"Exception: {e}")
        return 0

def test_full_message():
    url = "https://neptun-7ua9.onrender.com/debug_parse"
    
    full_message = """Сумщина:
4х БпЛА курсом на Недригайлів 
БпЛА курсом на Липову Долину 
БпЛА курсом на Конотоп 

Чернігівщина:
БпЛА курсом на Прилуки  
3х БпЛА курсом на Корюківку 
15х БпЛА курсом на Ніжин
5х БпЛА курсом на Десну
БпЛА курсом на Кіпті
4х БпЛА курсом на Ічню
БпЛА курсом на Гончарівське 

Полтавщина:
БпЛА курсом на Гадяч 
2х БпЛА курсом на Кременчук 
2х БпЛА курсом на Миргород 

Черкащина:
БпЛА курсом на Цвіткове

Київщина:
5х БпЛА курсом на Страхолісся
3х БпЛА курсом на Білу Церкву 
2х БпЛА курсом на Київ
2х БпЛА курсом на Бровари 
БпЛА курсом на Бишів 

Житомирщина:
БпЛА курсом на Коростень 
БпЛА курсом на Чоповичі
БпЛА курсом на Звягель 
БпЛА курсом на Радомишль 

Харківщина:
2х БпЛА курсом на Сахновщину 

Дніпропетровщина:
БпЛА курсом на Камʼянське 
2х БпЛА курсом на Солоне 

Кіровоградщина:
2х БпЛА курсом на Кропивницький 
БпЛА курсом на Піщаний Брід
4х БпЛА курсом на Бобринець
БпЛА курсом на Петрове

Херсонщина:
15х БпЛА курсом на Тендрівську косу

✙ Напрямок ракет  (https://t.me/napramok)✙
✙Підтримати канал (https://send.monobank.ua/5Pwr3r52mg)✙"""
    
    data = {
        "text": full_message,
        "mid": "test_full",
        "date": "2025-09-02 12:00:00", 
        "channel": "napramok"
    }
    
    print("\n" + "="*60)
    print("Testing full napramok message...")
    print(f"Expected cities: 31")
    
    try:
        response = requests.post(url, json=data, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            count = result.get('count', 0)
            print(f"🎯 TRACKS CREATED: {count}")
            
            if count >= 31:
                print("✅ SUCCESS: All expected markers!")
            elif count > 0:
                print(f"⚠️  PARTIAL: Expected 31, got {count}")
            else:
                print("❌ FAILED: No tracks created")
                
            return count
        else:
            print(f"Error: {response.text}")
            return 0
            
    except Exception as e:
        print(f"Exception: {e}")
        return 0

if __name__ == "__main__":
    print("🧪 PRODUCTION PARSING TEST")
    print("="*60)
    
    # Test simple message first
    simple_count = test_production_parse()
    
    # Test full message
    full_count = test_full_message()
    
    print("\n" + "="*60)
    print("📊 SUMMARY:")
    print(f"Simple message tracks: {simple_count}")
    print(f"Full message tracks: {full_count}")
    
    if full_count >= 31:
        print("🎉 SUCCESS: Full message parsing works!")
    elif simple_count > 0:
        print("🔧 PARTIAL: Simple works, full message has issues")
    else:
        print("💥 CRITICAL: Basic parsing not working")
