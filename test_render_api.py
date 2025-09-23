#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест направленных угроз через API Render
"""

import requests
import json

def test_render_directional_threats():
    """Тестирует обработку направленных угроз на продакшене"""
    
    # URL API для геокодинга
    base_url = "https://neptun-latest.onrender.com"
    
    test_cases = [
        {
            "text": "ворожі бпла на харківщина в напрямку чугуєва зі сходу",
            "description": "Харьковщина → Чугуев с востока"
        },
        {
            "text": "група ворожих бпла на південному заході від м.запоріжжя, курс - північно-західний",
            "description": "БПЛА юго-западнее Запорожья, курс северо-западный"
        }
    ]
    
    print("🌐 Тестирование направленных угроз на продакшене Render\n")
    
    for i, case in enumerate(test_cases, 1):
        print(f"📝 Тест {i}: {case['description']}")
        print(f"📄 Текст: {case['text']}")
        
        try:
            # Используем правильный API эндпоинт для тестирования
            url = f"{base_url}/debug_parse"
            
            # Данные в формате debug_parse API
            payload = {
                "text": case['text'],
                "channel": "test",
                "date": "2025-01-23 10:00:00"
            }
            
            print(f"🔄 Отправляем запрос на {url}...")
            
            response = requests.post(
                url, 
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Получен ответ: {response.status_code}")
                
                # Ищем направленные угрозы в результате
                tracks = result.get('tracks', [])
                directional_found = False
                
                for track in tracks:
                    if 'directional_threat' in track and track['directional_threat']:
                        directional_found = True
                        print(f"🎯 Найдена направленная угроза:")
                        print(f"   - Название: {track.get('place', 'не определено')}")
                        print(f"   - Направление: {track.get('direction', 'не определено')}")
                        print(f"   - Координаты: [{track.get('lat', 'N/A')}, {track.get('lng', 'N/A')}]")
                        if 'base_coords' in track:
                            base = track['base_coords']
                            print(f"   - Базовые координаты: [{base[0]}, {base[1]}]")
                        break
                
                if not directional_found:
                    print("❌ Направленная угроза не найдена в ответе")
                    if tracks:
                        print(f"   Найдено треков: {len(tracks)}")
                        for track in tracks[:2]:  # Показываем первые 2
                            print(f"   - {track.get('place', 'no place')}: {track.get('threat_type', 'no type')}")
                    else:
                        print("   Треки не найдены")
                        
            else:
                print(f"❌ Ошибка запроса: {response.status_code}")
                print(f"   Ответ: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print("❌ Таймаут запроса (30 секунд)")
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка сети: {e}")
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
        
        print("-" * 70)
        print()

if __name__ == "__main__":
    test_render_directional_threats()
