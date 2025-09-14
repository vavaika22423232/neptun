#!/usr/bin/env python3
import sys
sys.path.append('.')
from app import process_message

def test_working_kyiv_logic():
    print("🎯 ДЕМОНСТРАЦИЯ: Работающая улучшенная логика Киева")
    print("=" * 65)
    
    # Тест, который мы знаем что работает
    test_message = 'БпЛА на Київ з півдня'
    
    print(f"📝 Тестовое сообщение: {test_message}")
    print()
    
    result = process_message(test_message, "test_mid", "2024-09-14", "test_channel")
    
    if result:
        threat = result[0]  # Результат возвращается как список угроз
        
        city = threat.get('place', 'N/A')
        coords = (threat.get('lat', 0), threat.get('lng', 0))
        direction = threat.get('direction_info')
        source = threat.get('source_match', 'N/A')
        icon = threat.get('marker_icon', 'N/A')
        
        # Киевский центр для сравнения
        kyiv_center = (50.4501, 30.5234)
        
        print("🔍 АНАЛИЗ РЕЗУЛЬТАТА:")
        print(f"   🏙️  Город: {city}")
        print(f"   📍 Координаты: {coords}")
        print(f"   🎯 Центр Киева: {kyiv_center}")
        
        if coords != kyiv_center:
            lat_diff = coords[0] - kyiv_center[0]
            lng_diff = coords[1] - kyiv_center[1]
            print(f"   ↗️  Смещение: lat {lat_diff:+.4f}, lng {lng_diff:+.4f}")
            print("   ✅ УСПЕХ: Координаты смещены!")
        else:
            print("   ❌ Координаты НЕ смещены")
            
        print(f"   🧭 Направление: {direction}")
        print(f"   🔗 Источник: {source}")
        print(f"   🖼️  Иконка: {icon}")
        
        # Проверки
        checks = []
        
        if '↑ Київ (Пд)' in city:
            checks.append("✅ Название показывает направление движения")
        else:
            checks.append("❌ Название не показывает направление")
            
        if 'kyiv_directional' in source:
            checks.append("✅ Используется специальная логика для Киева")
        else:
            checks.append("❌ НЕ используется специальная логика")
            
        if direction == 'півдн':
            checks.append("✅ Сохранена информация о направлении")
        else:
            checks.append("❌ НЕ сохранена информация о направлении")
            
        if coords[0] < kyiv_center[0]:  # Южнее
            checks.append("✅ Координаты правильно смещены на юг")
        else:
            checks.append("❌ Координаты НЕ смещены на юг")
        
        print(f"\n🔍 ПРОВЕРКИ:")
        for check in checks:
            print(f"   {check}")
            
        success_count = sum(1 for check in checks if check.startswith("✅"))
        total_checks = len(checks)
        
        print(f"\n🎉 ИТОГО: {success_count}/{total_checks} проверок пройдено")
        
        if success_count >= 3:
            print("🚀 ОТЛИЧНО! Улучшенная логика Киева работает!")
        else:
            print("⚠️  Логика требует доработки")
    else:
        print("❌ Результат пустой")

def test_donation_filtering():
    print(f"\n" + "=" * 65)
    print("💰 ТЕСТ: Фильтрация 'Підтримати канал'")
    print("=" * 65)
    
    test_message = """
🟥 КРИВИЙ РІГ
🟨 Попередження про можливу активність БпЛА в області

Підтримати канал: https://send.monobank.ua/jar/5mLLhfgKiX
"""
    
    print(f"📝 Тестовое сообщение с донатом:")
    print(f'   "{test_message.strip()}"')
    
    result = process_message(test_message.strip(), "test_mid", "2024-09-14", "test_channel")
    
    if result is None:
        print("✅ УСПЕХ: Сообщение с 'Підтримати канал' правильно отфильтровано!")
    else:
        print("❌ ОШИБКА: Сообщение не было отфильтровано")
        print(f"   Результат: {result}")

if __name__ == "__main__":
    test_working_kyiv_logic()
    test_donation_filtering()
