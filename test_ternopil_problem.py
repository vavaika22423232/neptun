#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест проблемного сообщения с Тернопільщиной
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message, logging
import datetime

# Проблемное сообщение
TEST_MESSAGE = "бпла на півночі тернопільщини ➡️ курсом на південно-західний напрямок."

print("=== ТЕСТ ПРОБЛЕМНОГО СООБЩЕНИЯ С ТЕРНОПІЛЬЩИНОЙ ===")
print("Сообщение:")
print(TEST_MESSAGE)
print("\n" + "="*50)

print("=== АНАЛИЗ СТРУКТУРЫ ===")
print(f"Содержит 'тернопільщини': {'тернопільщини' in TEST_MESSAGE.lower()}")
print(f"Содержит 'бпла': {'бпла' in TEST_MESSAGE.lower()}")
print(f"Содержит 'курсом': {'курсом' in TEST_MESSAGE.lower()}")
print(f"Содержит 'напрямок': {'напрямок' in TEST_MESSAGE.lower()}")

print("\n" + "="*50)

try:
    result = process_message(TEST_MESSAGE, "test_ternopil", datetime.datetime.now().isoformat(), "test_channel")
    
    print(f"\n=== РЕЗУЛЬТАТ ОБРАБОТКИ ===")
    print(f"Количество меток: {len(result) if result else 0}")
    
    if result and isinstance(result, list):
        for i, track in enumerate(result, 1):
            place = track.get('place', 'Unknown')
            lat = track.get('lat', 'N/A')
            lng = track.get('lng', 'N/A')
            source = track.get('source_match', 'Unknown source')
            text = track.get('text', 'No text')
            print(f"  {i}. {place} ({lat}, {lng})")
            print(f"     Источник: {source}")
            print(f"     Текст: {text}")
            
        # Проверяем координаты
        if result:
            track = result[0]
            lat, lng = track.get('lat'), track.get('lng')
            
            print(f"\n=== АНАЛИЗ КООРДИНАТ ===")
            print(f"Координаты: {lat}, {lng}")
            
            # Примерные координаты областей
            ternopil_region = (49.5, 25.6)  # Тернополь
            ivano_frankivsk_region = (48.9, 24.7)  # Ивано-Франковск
            
            print(f"Тернопольская область (примерно): {ternopil_region}")
            print(f"Ивано-Франковская область (примерно): {ivano_frankivsk_region}")
            
            if lat and lng:
                # Вычисляем расстояние до центров областей
                def distance(lat1, lng1, lat2, lng2):
                    return ((lat1 - lat2)**2 + (lng1 - lng2)**2)**0.5
                
                dist_ternopil = distance(lat, lng, *ternopil_region)
                dist_ivano = distance(lat, lng, *ivano_frankivsk_region)
                
                print(f"Расстояние до Тернополя: {dist_ternopil:.3f}")
                print(f"Расстояние до Ивано-Франковска: {dist_ivano:.3f}")
                
                if dist_ternopil < dist_ivano:
                    print("✅ Метка ближе к Тернопольской области")
                else:
                    print("❌ Метка ближе к Ивано-Франковской области (ПРОБЛЕМА!)")
            
    else:
        print("❌ Нет результатов")
        
except Exception as e:
    print(f"❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("=== ОЖИДАЕМЫЙ РЕЗУЛЬТАТ ===")
print("Должна быть создана метка в Тернопольской области,")
print("так как сообщение говорит о 'півночі тернопільщини'")
print("Но получаем метку в Ивано-Франковской области")
