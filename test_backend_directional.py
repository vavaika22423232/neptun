#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест обработки направленных угроз в Python бэкенде
"""

import sys
import os
import json

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем функции из app.py
from app import spacy_enhanced_geocoding

def test_directional_threats():
    """Тест примеров направленных угроз"""
    
    test_cases = [
        {
            "text": "ворожі бпла на харківщина в напрямку чугуєва зі сходу",
            "description": "Пример 1: Харьковская область, направление на Чугуев с востока"
        },
        {
            "text": "на чернігівщина - в напрямку н.п.понорниця з північного сходу",
            "description": "Пример 2: Черниговская область, направление на Понорницу с северо-востока"
        },
        {
            "text": "група ворожих бпла на південному заході від м.запоріжжя, курс - північно-західний",
            "description": "Пример 3: БПЛА юго-западнее Запорожья, курс северо-западный"
        },
        {
            "text": "ракети на сході від києва",
            "description": "Пример 4: Ракеты восточнее Киева"
        },
        {
            "text": "шахеди на півночі від одеси, напрямок південний",
            "description": "Пример 5: Шахеды севернее Одессы, направление южное"
        }
    ]
    
    print("🧪 Тестирование обработки направленных угроз в Python бэкенде\n")
    
    for i, case in enumerate(test_cases, 1):
        print(f"📝 Тест {i}: {case['description']}")
        print(f"📄 Текст: {case['text']}")
        
        try:
            # Вызываем функцию геокодирования
            result = spacy_enhanced_geocoding(case['text'])
            
            print(f"📍 Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            # Проверяем, есть ли направленные угрозы в результате
            directional_found = False
            if result:
                for point in result:
                    if 'directional_threat' in point and point['directional_threat']:
                        directional_found = True
                        print(f"✅ Обнаружена направленная угроза:")
                        print(f"   - Направление: {point.get('direction', 'не определено')}")
                        print(f"   - Название: {point.get('name', 'не определено')}")
                        print(f"   - Базовые координаты: {point.get('base_coords', 'не определены')}")
                        print(f"   - Смещенные координаты: {point.get('coords', 'не определены')}")
                        break
                
                if not directional_found:
                    print("❌ Направленная угроза не обнаружена")
            else:
                print("❌ Результат пустой")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        print("-" * 80)
        print()

if __name__ == "__main__":
    test_directional_threats()
