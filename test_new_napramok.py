#!/usr/bin/env python3
"""Test the new napramok message to verify all 31 markers appear."""

import sys
sys.path.insert(0, '.')

# The new message from user
text = """Сумщина:
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

print("=" * 60)
print("TESTING NEW NAPRAMOK MESSAGE")
print("=" * 60)
print(f"Expected cities: 31")
print("Testing coordinates...")

try:
    from app import process_message
    
    tracks = process_message(text, "test_new", "2025-09-02 12:00:00", "napramok")
    
    if tracks and isinstance(tracks, list):
        markers = [t for t in tracks if not t.get('list_only', False) and not t.get('suppress', False)]
        print(f"\n🎯 RESULT: {len(markers)} map markers created!")
        
        if len(markers) >= 31:
            print("✅ SUCCESS: All expected markers present!")
        else:
            print(f"⚠️  WARNING: Expected 31+, got {len(markers)}")
            
        print(f"\nTotal tracks: {len(tracks)}")
        print(f"Map markers: {len(markers)}")
        print(f"List entries: {len([t for t in tracks if t.get('list_only', False)])}")
        
    else:
        print("❌ ERROR: No tracks returned or wrong type")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
