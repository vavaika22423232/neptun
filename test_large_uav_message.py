#!/usr/bin/env python3
# Test script for debugging large UAV course message parsing

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Import the parsing function
from app import process_message, CITY_COORDS, OBLAST_CENTERS

test_message = """Миколаївщина:
БпЛА курсом на Нечаяне
БпЛА курсом на Єланець
5х БпЛА курсом на Баштанку 
3х БпЛА курсом на Новий Буг 

Вінниччина:
БпЛА курсом на Пеньківку
2х БпЛА курсом на Станіславчик
3х БпЛА курсом на Шаргород 
2х БпЛА курсом на Вендичани 
БпЛА курсом на Мазурівку

Одещина:
4х БпЛА курсом на Ширяєве 

Дніпропетровщина:
3х БпЛА курсом на Кривий Ріг 
7х БпЛА курсом на Пʼятихатки 

Кіровоградщина:
8х БпЛА курсом на Світловодськ 
БпЛА курсом на Гайдамацьке
БпЛА курсом на Кропивницький 

Полтавщина:
БпЛА курсом на Кременчук 
2х БпЛА курсом на Великі Сорочинці 
БпЛА курсом на Глобине 

Черкащина:
БпЛА курсом на Драбів 

Сумщина:
2х БпЛА курсом на Степанівку
БпЛА курсом на Липову Долину 
БпЛА курсом на Конотоп 
БпЛА курсом на Білопілля 

Чернігівщина:
БпЛА курсом на Гончарівське
2х БпЛА курсом на Городню
3х БпЛА курсом на Ріпки
БпЛА курсом на Седнів
БпЛА курсом на Борзну 
2х БпЛА курсом на Кіпті

Київщина:
5х БпЛА курсом на Яготин
3х БпЛА курсом на водосховище 
БпЛА курсом на Васильків 
4х БпЛА курсом на Красятичі
БпЛА курсом на Фастів 
БпЛА курсом на Макарів 

Житомирщина:
2х БпЛА курсом на Коростень 
2х БпЛА курсом на Овруч 
БпЛА курсом на Нові Білокоровичі
БпЛА курсом на Олевськ
БпЛА курсом на Черняхів 
3х БпЛА курсом на Андрушівку
2х БпЛА курсом на Любар 
БпЛА курсом на Коростишів 

Хмельниччина:
БпЛА курсом на Нетішин 
БпЛА курсом на Адампіль
БпЛА курсом на Старокостянтинів 

Рівненщина:
БпЛА курсом на Рівне
2х БпЛА курсом на Деражне
БпЛА курсом на Костопіль
БпЛА курсом на Рокитне
4х БпЛА курсом на Дубровицю

Волинь:
БпЛА курсом на Камінь-Каширський

✙ Напрямок ракет  (https://t.me/napramok)✙
✙Підтримати канал (https://send.monobank.ua/5Pwr3r52mg)✙"""

def main():
    print("Testing large UAV course message parsing...")
    print(f"Message length: {len(test_message)} chars")
    print(f"Number of 'бпла' occurrences: {test_message.lower().count('бпла')}")
    print(f"Number of 'курс' occurrences: {test_message.lower().count('курс')}")
    
    # Check region headers
    print("\nChecking region headers:")
    for line in test_message.split('\n'):
        if line.strip().endswith(':'):
            clean_hdr = line.strip().lower()[:-1]
            in_oblast = clean_hdr in OBLAST_CENTERS
            print(f"  '{clean_hdr}' -> in OBLAST_CENTERS: {in_oblast}")
    
    # Test some city lookups
    print("\nChecking city coordinates:")
    test_cities = ['нечаяне', 'єланець', 'баштанка', 'пеньківка', 'станіславчик', 'вендичани']
    for city in test_cities:
        coords = CITY_COORDS.get(city)
        print(f"  '{city}' -> {coords}")
    
    # Run the parser
    print("\nRunning parser...")
    try:
        result = process_message(test_message, 'test_123', '2025-09-03', 'test_channel')
        print(f"Parser result: {len(result)} tracks")
        for i, track in enumerate(result[:10], 1):  # Show first 10
            print(f"  {i}. {track.get('place', 'N/A')} - {track.get('source_match', 'N/A')}")
        if len(result) > 10:
            print(f"  ... and {len(result) - 10} more tracks")
    except Exception as e:
        print(f"Parser error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
