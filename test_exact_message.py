#!/usr/bin/env python3
"""Test the exact message to verify no blocking filters prevent markers."""

import sys
sys.path.insert(0, '.')
from app import process_message

# The exact message provided by user
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
    print("=" * 60)
    print("TESTING EXACT USER MESSAGE")
    print("=" * 60)
    print(f"Text length: {len(text)} chars")
    print(f"Text contains 'бпла': {'бпла' in text.lower()}")
    print(f"Text contains 'курс': {'курс' in text.lower()}")
    print(f"Text contains donation links: {'monobank' in text.lower()}")
    print("")
    
    try:
        tracks = process_message(text, "test_123", "2025-09-02 12:00:00", "napramok")
        
        if tracks is None:
            print("❌ RESULT: None (completely blocked)")
        elif isinstance(tracks, list):
            print(f"✅ RESULT: {len(tracks)} tracks created")
            if len(tracks) == 0:
                print("❌ WARNING: Empty list returned")
            else:
                print("First few tracks:")
                for i, track in enumerate(tracks[:5]):
                    place = track.get('place', 'N/A')
                    threat = track.get('threat_type', 'N/A')
                    list_only = track.get('list_only', False)
                    suppress = track.get('suppress', False)
                    print(f"  {i+1}. {place} [{threat}] list_only={list_only} suppress={suppress}")
                if len(tracks) > 5:
                    print(f"  ... and {len(tracks)-5} more")
                    
                # Count markers vs list-only
                markers = [t for t in tracks if not t.get('list_only', False) and not t.get('suppress', False)]
                list_entries = [t for t in tracks if t.get('list_only', False)]
                suppressed = [t for t in tracks if t.get('suppress', False)]
                
                print(f"\nSUMMARY:")
                print(f"  Map markers: {len(markers)}")
                print(f"  List-only entries: {len(list_entries)}")
                print(f"  Suppressed entries: {len(suppressed)}")
        else:
            print(f"❌ UNEXPECTED RESULT TYPE: {type(tracks)}")
            print(tracks)
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
