#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import process_message

def test_multiple_regions():
    print("=== Testing Multiple Regions Message ===")
    
    message = """Миколаївщина:
10 шахедів біля Вознесенська та район
3 шахеди біля Миколаєва
Полтавщина:
8 шахедів біля Лебедина/Охтирки на Полтаву
6 шахедів через Камʼянське/Кременчук район на Полтаву
1 шахед біля Полтави
1 шахед біля Кременчука
Чернігівщина:
6 шахедів з боку Конотопу
Кіровоградщина:
1 шахед на Новоукраїнку
Дніпропетровщина:
1 шахед біля Дніпровського району
ㅤ
➡Підписатися"""
    
    print(f"Message: {message}")
    print()
    
    markers = process_message(message, mid=12345, date_str='2025-09-17', channel='test')
    
    print(f"Found {len(markers)} markers:")
    for i, marker in enumerate(markers, 1):
        print(f"{i}. {marker['place']} at ({marker['lat']}, {marker['lng']}) - {marker['source_match']}")
        print(f"   Threat type: {marker['threat_type']}")
        print()
    
    print("=== Analysis ===")
    cities_found = [m['place'].lower() for m in markers]
    expected_mapping = {
        'вознесенськ': ['вознесенська'],
        'миколаїв': ['миколаєва', 'миколаїв'], 
        'лебедин': ['лебедин', 'лебедина'],
        'охтирка': ['охтирка', 'охтирки'],
        'полтава': ['полтава', 'полтави'],
        'кременчук': ['кременчук', 'кременчука'],
        'конотоп': ['конотоп', 'конотопу'],
        'новоукраїнка': ['новоукраїнка', 'новоукраїнку'],
        'дніпро': ['дніпро', 'дніпра']
    }
    
    found_count = 0
    for expected, variants in expected_mapping.items():
        found = any(any(variant in city or city in variant for variant in variants) for city in cities_found)
        if found:
            found_count += 1
            print(f"✅ {expected.title()}")
        else:
            print(f"❌ {expected.title()}")
    
    success_rate = (found_count / len(expected_mapping)) * 100
    print(f"\n📊 Success Rate: {found_count}/{len(expected_mapping)} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("🎉 EXCELLENT: Geographic processing working well!")
    elif success_rate >= 60:
        print("✅ GOOD: Most cities processed correctly")
    else:
        print("⚠️ NEEDS IMPROVEMENT: Many cities missed")

if __name__ == "__main__":
    test_multiple_regions()
