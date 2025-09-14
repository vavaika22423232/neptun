#!/usr/bin/env python3
import sys
sys.path.append('.')
from app import process_message

def test_shahed_launch_message():
    print("🔍 Тестируем сообщение о пусках Shahed...")
    
    test_message = """⚠️🛸Пуски БпЛА "Shahed" з аеродрому "Халіно", Курська область, з полігону "Орел-Південний", Орловська область, з полігону "Навля", Брянська область
Напрямок ракет
Підтримати канал"""
    
    print(f"📝 Тестовое сообщение:")
    print(f"{repr(test_message)}")
    print()
    
    result = process_message(test_message, "test_mid", "2024-09-14", "test_channel")
    
    print(f"🔍 Результат обработки:")
    if result is None:
        print("❌ Сообщение отфильтровано (возвращен None)")
        print("   Возможные причины:")
        print("   - Фильтрация по donation ('Підтримати канал')")
        print("   - Другие фильтры системы")
    elif isinstance(result, list) and len(result) == 0:
        print("❌ Пустой список угроз")
    else:
        print(f"✅ Найдено угроз: {len(result) if isinstance(result, list) else 'unknown'}")
        
        if isinstance(result, list):
            for i, threat in enumerate(result):
                print(f"\n   Угроза {i+1}:")
                print(f"      🏙️ Место: {threat.get('place', 'N/A')}")
                print(f"      📍 Координаты: ({threat.get('lat', 'N/A')}, {threat.get('lng', 'N/A')})")
                print(f"      🎯 Тип угрозы: {threat.get('threat_type', 'N/A')}")
                print(f"      🖼️ Иконка: {threat.get('marker_icon', 'N/A')}")
                print(f"      🔗 Источник: {threat.get('source_match', 'N/A')}")
                print(f"      📝 Текст: {threat.get('text', 'N/A')[:100]}...")
        else:
            print(f"      Результат: {result}")

if __name__ == "__main__":
    test_shahed_launch_message()
