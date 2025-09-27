#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест обработки сообщения с несколькими городами в подготовке к пускам БПЛА
"""

import sys
sys.path.append('.')

try:
    from app import process_message, spacy_enhanced_geocoding, SPACY_AVAILABLE
    print(f"SpaCy available: {SPACY_AVAILABLE}")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

def test_multi_city_preparation():
    test_message = "Підготовка до пусків БПЛА з Шаталово, Орла, Брянська, Міллерево"
    
    print("=== ТЕСТ: Сообщение с несколькими городами ===")
    print(f"Сообщение: {test_message}")
    print()
    
    # Test SpaCy if available
    if SPACY_AVAILABLE:
        print("=== ТЕСТ SpaCy ===")
        try:
            spacy_results = spacy_enhanced_geocoding(test_message)
            print(f"SpaCy результаты: {len(spacy_results) if spacy_results else 0} городов")
            
            if spacy_results:
                for i, city in enumerate(spacy_results):
                    print(f"  {i+1}. {city['name']} - {city['coords']} (уверенность: {city.get('confidence', 'N/A')})")
            else:
                print("  SpaCy не нашел городов")
        except Exception as e:
            print(f"  SpaCy ошибка: {e}")
        print()
    
    # Test main process_message function
    print("=== ТЕСТ process_message ===")
    try:
        results = process_message(test_message, "test_multi_prep", "2025-09-27 12:00:00", "test")
        
        print(f"Результаты process_message: {len(results)} меток")
        
        if results:
            for i, result in enumerate(results):
                print(f"  {i+1}. Город: {result.get('city', 'N/A')}")
                print(f"     Координаты: {result.get('lat', 'N/A')}, {result.get('lng', 'N/A')}")
                print(f"     Тип угрозы: {result.get('threat_type', 'N/A')}")
                print(f"     Текст: {result.get('text', 'N/A')}")
                print()
        else:
            print("  Метки не созданы")
            
    except Exception as e:
        print(f"  Ошибка process_message: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_city_preparation()
