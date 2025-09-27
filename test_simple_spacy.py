#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Упрощенный тест для диагностики проблемы с несколькими городами
"""

import sys
sys.path.append('.')

def test_simple_spacy():
    try:
        from app import spacy_enhanced_geocoding, SPACY_AVAILABLE
        print(f"SpaCy available: {SPACY_AVAILABLE}")
    except ImportError as e:
        print(f"Import error: {e}")
        return
    
    if not SPACY_AVAILABLE:
        print("SpaCy not available, skipping test")
        return

    test_message = "Підготовка до пусків БПЛА з Шаталово, Орла, Брянська, Міллерево"
    
    print("=== ТЕСТ SpaCy enhanced geocoding ===")
    print(f"Сообщение: {test_message}")
    print()
    
    try:
        results = spacy_enhanced_geocoding(test_message)
        print(f"SpaCy нашел {len(results) if results else 0} результатов:")
        
        if results:
            cities_with_coords = []
            for i, result in enumerate(results):
                coords_str = f"{result['coords']}" if result['coords'] else "None"
                print(f"  {i+1}. {result['name']} -> {coords_str}")
                
                if result['coords']:
                    cities_with_coords.append(result)
            
            print(f"\nГорода с координатами: {len(cities_with_coords)}")
            for city in cities_with_coords:
                print(f"  - {city['name']}: {city['coords']}")
                
        return results
        
    except Exception as e:
        print(f"Ошибка SpaCy: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_manual_classification():
    """Тестируем классификацию отдельно"""
    try:
        from app import classify  # This should be defined somewhere
        
        test_message = "Підготовка до пусків БПЛА з Шаталово, Орла, Брянська, Міллерево"
        
        print("\n=== ТЕСТ classify function ===")
        print(f"Сообщение: {test_message}")
        
        threat_type, icon = classify(test_message)
        print(f"Классификация: {threat_type}, {icon}")
        
    except Exception as e:
        print(f"Ошибка классификации: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    spacy_results = test_simple_spacy()
    test_manual_classification()
