#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест полного потока: от парсинга до фронтенда
"""

import sys
import os
import json

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем функции из app.py
from app import process_message

def test_full_flow():
    """Тестирует полный поток от текста до финального JSON"""
    
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
    
    print("🔄 Тестирование полного потока обработки сообщений\n")
    
    for i, case in enumerate(test_cases, 1):
        print(f"📝 Тест {i}: {case['description']}")
        print(f"📄 Текст: {case['text']}")
        
        try:
            # Используем process_message как точку входа
            markers = process_message(
                text=case['text'],
                mid=f"test_{i}",
                date_str="2025-01-23 10:00:00",
                channel="test"
            )
            
            print(f"📍 Результат: {len(markers)} маркеров")
            
            for j, marker in enumerate(markers):
                print(f"   Маркер {j+1}:")
                print(f"   - place: {marker.get('place', 'N/A')}")
                print(f"   - coordinates: [{marker.get('lat', 'N/A')}, {marker.get('lng', 'N/A')}]")
                print(f"   - threat_type: {marker.get('threat_type', 'N/A')}")
                
                # Проверяем поля направленной угрозы
                if marker.get('directional_threat'):
                    print(f"   ✅ НАПРАВЛЕННАЯ УГРОЗА:")
                    print(f"      - direction: {marker.get('direction', 'N/A')}")
                    print(f"      - base_coords: {marker.get('base_coords', 'N/A')}")
                else:
                    print(f"   ❌ Направленная угроза не обнаружена")
                
                print()
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 70)
        print()

if __name__ == "__main__":
    test_full_flow()
