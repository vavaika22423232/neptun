#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import process_message

def test_extended_multi_regional_message():
    """Test the extended multi-regional UAV message with 6 regions."""
    
    text = """Сумщина:
БпЛА курсом на Боромлю
2х БпЛА курсом на Тростянець
2х БпЛА курсом на Кириківку
БпЛА курсом на Охтирку 
2х БпЛА курсом на Липову Долину 
БпЛА курсом на Миколаївку
БпЛА курсом на Лебедин 
3х БпЛА курсом на Чупахівку

Полтавщина:
3х БпЛА курсом на Котельву 
3х БпЛА курсом на Миргород 
БпЛА курсом на Машівку
5х БпЛА курсом на Полтаву 
БпЛА курсом на Решетилівку 
2х БпЛА курсом на Хорол
БпЛА курсом на Кременчук 
3х БпЛА курсом на Кобеляки 
11х БпЛА курсом на Лубни
БпЛА курсом на Пирятин 

Чернігівщина:
2х БпЛА курсом на Срібне 
БпЛА курсом на Ічню

Харківщина:
3х БпЛА курсом на Шевченкове
БпЛА курсом на Златопіль
БпЛА курсом на Берестин

Дніпропетровщина:
БпЛА курсом на Магдалинівку 
БпЛА курсом на Лихівку

Черкащина:
2х БпЛА курсом на Черкаси 
7х БпЛА курсом на Смілу
БпЛА курсом на Драбів"""

    print("=== Обработка расширенного многорегионального сообщения (6 регионов) ===")
    print(f"Текст сообщения:\n{text}\n")
    
    result = process_message(text, "test_msg_extended", "2025-09-19 23:05:00", "test_channel")
    
    print(f"Результат обработки: {type(result)}")
    
    if isinstance(result, list):
        print(f"Количество меток: {len(result)}")
        
        # Подсчитываем города по регионам из исходного текста
        expected_counts = {
            'Сумщина': 8,      # Боромля, Тростянець, Кириківка, Охтирка, Липова Долина, Миколаївка, Лебедин, Чупахівка
            'Полтавщина': 10,  # Котельва, Миргород, Машівка, Полтава, Решетилівка, Хорол, Кременчук, Кобеляки, Лубни, Пирятин
            'Чернігівщина': 2, # Срібне, Ічня
            'Харківщина': 3,   # Шевченкове, Златопіль, Берестин
            'Дніпропетровщина': 2, # Магдалинівка, Лихівка
            'Черкащина': 3     # Черкаси, Сміла, Драбів
        }
        
        total_expected = sum(expected_counts.values())
        print(f"Ожидалось городов: {total_expected}")
        
        # Группируем по регионам
        regions = {}
        not_found = []
        
        for item in result:
            if 'text' in item and 'lat' in item and 'lng' in item:
                # Определяем регион по первой строке текста
                first_line = item['text'].split('\n')[0] if '\n' in item['text'] else item['text']
                
                region = 'Неопределенно'
                if 'сумщин' in first_line.lower():
                    region = 'Сумщина'
                elif 'полтавщин' in first_line.lower():
                    region = 'Полтавщина'  
                elif 'чернігівщин' in first_line.lower():
                    region = 'Чернігівщина'
                elif 'харківщин' in first_line.lower():
                    region = 'Харківщина'
                elif 'дніпропетровщин' in first_line.lower():
                    region = 'Дніпропетровщина'
                elif 'черкащин' in first_line.lower():
                    region = 'Черкащина'
                
                if region not in regions:
                    regions[region] = []
                regions[region].append(item)
            else:
                not_found.append(item)
        
        print("\n=== Результаты по регионам ===")
        for region_name, expected_count in expected_counts.items():
            actual_count = len(regions.get(region_name, []))
            status = "✅" if actual_count == expected_count else "❌"
            print(f"{status} {region_name}: {actual_count}/{expected_count} городов")
            
            if region_name in regions:
                for i, item in enumerate(regions[region_name], 1):
                    city = item.get('text', '').split(' на ')[-1].split('\n')[0] if ' на ' in item.get('text', '') else 'неизвестно'
                    lat = item.get('lat', 'нет')
                    lng = item.get('lng', 'нет')
                    print(f"  {i}. {city}: ({lat}, {lng})")
        
        # Неопределенные регионы
        if 'Неопределенно' in regions:
            print(f"\n⚠️  Неопределенный регион: {len(regions['Неопределенно'])} городов")
            for i, item in enumerate(regions['Неопределенно'], 1):
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
        
        # Общая статистика
        success_rate = (len(result) / total_expected) * 100 if total_expected > 0 else 0
        print(f"\n📊 Общая статистика:")
        print(f"   Обработано: {len(result)}/{total_expected} городов ({success_rate:.1f}%)")
        print(f"   Регионов: {len([r for r in regions.keys() if r != 'Неопределенно'])}/6")
            
    else:
        print("Ошибка: результат не является списком")
        print(f"Результат: {result}")

if __name__ == "__main__":
    test_extended_multi_regional_message()
