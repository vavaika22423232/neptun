#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_detailed_multi_regional_message():
    """Test the detailed multi-regional UAV message."""
    
    text = """Сумщина:
БпЛА курсом на Ромни
5х БпЛА курсом на Чупахівку
БпЛА курсом на Ромни
4х БпЛА курсом на Липову Долину 

Полтавщина:
БпЛА курсом на Полтаву 
3х БпЛА курсом на Кременчук 
2х БпЛА курсом на Машівку
10х БпЛА курсом на Кобеляки 
2х БпЛА курсом на Горішні Плавні 
БпЛА курсом на Гадяч 
2х БпЛА курсом на Котельву 
2х БпЛА курсом на Зіньків
3х БпЛА курсом на Шишаки 
2х БпЛА курсом на Решетилівку 
10х БпЛА курсом на Пирятин по межі Сумщини та Чернігівщини 

Харківщина:
БпЛА курсом на Харків 
4х БпЛА курсом на Берестин
5х БпЛА курсом на Зачепилівку
БпЛА курсом на Сахновщину 

Дніпропетровщина:
БпЛА курсом на Самар
БпЛА курсом на Дніпро

✙ Напрямок ракет ✙
✙Підтримати канал✙"""

    print("=== Обработка детального многорегионального сообщения ===")
    print(f"Текст сообщения:\n{text}\n")
    
    result = process_message(text, "test_msg_detailed", "2025-09-19 22:30:00", "test_channel")
    
    print(f"Результат обработки: {type(result)}")
    
    if isinstance(result, list):
        print(f"Количество меток: {len(result)}")
        
        # Группируем по регионам
        regions = {}
        for item in result:
            if 'text' in item:
                first_line = item['text'].split('\n')[0] if '\n' in item['text'] else item['text']
                if 'сумщин' in first_line.lower():
                    region = 'Сумщина'
                elif 'полтавщин' in first_line.lower():
                    region = 'Полтавщина'  
                elif 'харківщин' in first_line.lower():
                    region = 'Харківщина'
                elif 'дніпропетровщин' in first_line.lower():
                    region = 'Дніпропетровщина'
                else:
                    region = 'Неизвестно'
                
                if region not in regions:
                    regions[region] = []
                regions[region].append(item)
        
        print("\n=== Метки по регионам ===")
        for region, items in regions.items():
            print(f"\n{region}: {len(items)} меток")
            for i, item in enumerate(items, 1):
                city = item.get('text', '').split(' на ')[-1].split('\n')[0] if ' на ' in item.get('text', '') else 'неизвестно'
                lat = item.get('lat', 'нет')
                lng = item.get('lng', 'нет')
                print(f"  {i}. {city}: ({lat}, {lng})")
        
        # Проверяем на дубликаты координат
        coords_seen = set()
        duplicates = []
        for item in result:
            coord_key = f"{item.get('lat')},{item.get('lng')}"
            if coord_key in coords_seen:
                duplicates.append(coord_key)
            coords_seen.add(coord_key)
        
        if duplicates:
            print(f"\n⚠️  Найдены дубликаты координат: {len(duplicates)}")
            for dup in set(duplicates):
                print(f"  - {dup}")
        else:
            print("\n✅ Дубликатов координат не найдено")
            
    else:
        print("Ошибка: результат не является списком")
        print(f"Результат: {result}")

if __name__ == "__main__":
    test_detailed_multi_regional_message()
