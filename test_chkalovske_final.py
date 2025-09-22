#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальный тест для проверки корректности определения Чкаловського
После внедрения универсальной нормализации
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import spacy_enhanced_geocoding, normalize_ukrainian_toponym

def test_chkalovske_final():
    """Финальная проверка Чкаловського с универсальной нормализацией"""
    
    print("🔍 Тестируем финальное решение для Чкаловського")
    print("=" * 60)
    
    # Инициализируем NLP - происходит автоматически при импорте app.py
    
    # Тестовые сообщения
    test_messages = [
        "1 БпЛА на Чкаловське",
        "БпЛА курсом на Чкаловське", 
        "Удар по Чкаловському",
        "Вибухи в Чкаловському",
        "Обстріл Чкаловського району"
    ]
    
    print("📋 Тестируем различные падежи:")
    print()
    
    for i, message in enumerate(test_messages, 1):
        print(f"📝 Тест {i}: '{message}'")
        
        try:
            results = spacy_enhanced_geocoding(message)
            
            if results:
                for result in results:
                    name = result.get('name', 'Unknown')
                    normalized = result.get('normalized', 'None')
                    coords = result.get('coords')
                    
                    if 'чкалов' in name.lower():
                        print(f"   ✅ {name} → {normalized}")
                        if coords:
                            lat, lon = coords
                            print(f"      📍 Координаты: ({lat:.4f}, {lon:.4f})")
                            
                            # Проверяем область по координатам
                            if 49.5 <= lat <= 50.0 and 36.5 <= lon <= 37.5:
                                print(f"      🎯 ПРАВИЛЬНО: Харківська область")
                            elif 47.5 <= lat <= 48.5 and 37.5 <= lon <= 38.5:
                                print(f"      ❌ НЕПРАВИЛЬНО: Донецька область")
                            else:
                                print(f"      ❓ Інша область")
                        else:
                            print(f"      ⚠️  Координати не знайдені")
                        print()
            else:
                print(f"   ❌ Топоніми не знайдені")
                print()
                
        except Exception as e:
            print(f"   💥 Помилка: {e}")
            print()
    
    print("🧪 Тестуємо функцію нормалізації напряму:")
    print("-" * 40)
    
    test_variants = [
        "чкаловське",
        "чкаловський", 
        "чкаловського",
        "чкаловському"
    ]
    
    for variant in test_variants:
        normalized = normalize_ukrainian_toponym(variant, variant)  # original_text, lemmatized_name
        print(f"   '{variant}' → '{normalized}'")
    
    print()
    print("✨ Тест завершено!")

if __name__ == "__main__":
    test_chkalovske_final()
