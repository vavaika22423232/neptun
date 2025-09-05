#!/usr/bin/env python3
"""Test the problematic multi-region message that should produce many markers but doesn't."""

import sys
import os
sys.path.insert(0, '.')

from app import process_message

# The exact problematic text from user
text = """Сумщина:
БпЛА курсом на Суми
3х БпЛА курсом на Недригайлів 
5х БпЛА курсом на Конотоп 
5х БпЛА курсом на Терни
2х БпЛА курсом на Ромни 
БпЛА курсом на Путивль
БпЛА курсом на Глухів 

Чернігівщина:
БпЛА курсом на Чернігів 
3х БпЛА курсом на Корюківку 
20х БпЛА курсом на Ніжин
БпЛА курсом на Бахмач
10х БпЛА курсом на Десну
2х БпЛА курсом на Носівку
БпЛА курсом на Козелець
БпЛА курсом на Славутич

Полтавщина:
БпЛА курсом на Карлівку
БпЛА курсом на Миргород 

Черкащина:
БпЛА курсом на Черкаси

Київщина:
БпЛА курсом на Страхолісся
БпЛА курсом на Велику Димерку 
БпЛА курсом на Бишів
БпЛА курсом на Кагарлик 

Житомирщина:
БпЛА курсом на Білокоровичі

Харківщина:
БпЛА курсом на Зміїв
БпЛА курсом на Краснопалівку
БпЛА курсом на Ізюм
БпЛА курсом на Лозову 

Дніпропетровщина:
БпЛА курсом на Божедрівку
2х БпЛА курсом на Пʼятихатки 
БпЛА курсом на Кринички
БпЛА курсом на Межову 

Кіровоградщина:
4х БпЛА курсом на Петрове з Дніпропетровщини 

Запорізька область:
БпЛА курсом на Запоріжжя

Херсонщина:
5х БпЛА курсом на Брилівку

✙ Напрямок ракет  (https://t.me/napramok)✙
✙Підтримати канал (https://send.monobank.ua/5Pwr3r52mg)✙"""

if __name__ == '__main__':
    print("Testing problematic multi-region message...")
    print(f"Text length: {len(text)} chars")
    print("=" * 50)
    
    tracks = process_message(text, "test_123", "2025-09-02 12:00:00", "test_channel")
    
    print(f"Parser returned: {type(tracks)}")
    print(f"Number of tracks: {len(tracks) if isinstance(tracks, list) else 'N/A'}")
    
    if isinstance(tracks, list):
        print(f"\nAll tracks ({len(tracks)}):")
        for i, track in enumerate(tracks, 1):
            place = track.get('place', 'N/A')
            print(f"{i}. {place}")
        
        print("\nMissing cities check:")
        expected = ['суми', 'недригайлів', 'конотоп', 'терни', 'ромни', 'путивль', 'глухів', 
                   'чернігів', 'корюківку', 'ніжин', 'бахмач', 'десну', 'носівку', 'козелець', 'славутич',
                   'карлівку', 'миргород', 'черкаси', 'страхолісся', 'велику димерку', 'бишів', 'кагарлик',
                   'білокоровичі', 'зміїв', 'краснопалівку', 'ізюм', 'лозову', 'божедрівку', 'пʼятихатки',
                   'кринички', 'межову', 'петрове', 'запоріжжя', 'брилівку']

        found_cities = [track['place'].split(' [')[0].lower().split(' (')[0] for track in tracks]
        missing = [city for city in expected if city not in found_cities]
        print(f"Found cities: {len(found_cities)}")
        print(f"Expected cities: {len(expected)}")
        print(f"Missing cities: {missing}")
    else:
        print("Tracks is not a list!")
        print(tracks)
