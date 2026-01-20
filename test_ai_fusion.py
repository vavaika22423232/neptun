#!/usr/bin/env python3
"""
Тест AI-FIRST системи обробки повідомлень.

AI сам визначає:
- Кількість дронів
- Тип загрози
- Куди ставити маркер
- Коли переміщувати
- Коли видаляти
- Будувати траєкторії
"""

import os
import sys

# Додаємо шлях до app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Імпортуємо класи з app.py
from app import GROQ_ENABLED, ChannelIntelligenceFusion


def main():
    print("=" * 70)
    print("🤖 AI-FIRST FUSION SYSTEM TEST")
    print("=" * 70)
    print(f"\n📊 Groq AI: {'✅ ENABLED' if GROQ_ENABLED else '❌ DISABLED (fallback to regex)'}")
    print()

    # Створюємо систему
    fusion = ChannelIntelligenceFusion()

    # Тестові повідомлення - імітація реального потоку
    test_messages = [
        # === НОВИЙ ДРОН ===
        {
            'id': 'msg_001',
            'text': '🚨 УВАГА! 2х шахеди в Дніпропетровській області, курс на Дніпро',
            'channel': 'timofii_kucher',
            'date': '2026-01-19 03:30:00',
        },
        # === ТА Ж ЗАГРОЗА З ІНШОГО КАНАЛУ ===
        {
            'id': 'msg_002',
            'text': 'Дніпро! 2 шахеди, напрямок на місто',
            'channel': 'korabely_media',
            'date': '2026-01-19 03:31:00',
        },
        # === ПЕРЕМІЩЕННЯ ===
        {
            'id': 'msg_003',
            'text': 'Шахеди пройшли Дніпро, курс на Полтаву',
            'channel': 'kpszsu',
            'date': '2026-01-19 03:45:00',
        },
        # === ОДИН ЗБИТО ===
        {
            'id': 'msg_004',
            'text': 'Полтавська область: 1 шахед збито! Лишився 1',
            'channel': 'war_monitor',
            'date': '2026-01-19 03:55:00',
        },
        # === НОВИЙ ДРОН В ІНШОМУ РЕГІОНІ ===
        {
            'id': 'msg_005',
            'text': '⚠️ Миколаївська область: група до 5х БПЛА',
            'channel': 'vanek_nikolaev',
            'date': '2026-01-19 03:58:00',
        },
        # === ЗМІНА КУРСУ ===
        {
            'id': 'msg_006',
            'text': 'БПЛА змінили курс, напрямок на Одесу',
            'channel': 'korabely_media',
            'date': '2026-01-19 04:05:00',
        },
        # === КРИЛАТА РАКЕТА ===
        {
            'id': 'msg_007',
            'text': 'Пуск крилатої ракети! Калібр з моря, курс на Київ',
            'channel': 'kpszsu',
            'date': '2026-01-19 04:10:00',
        },
        # === БАЛІСТИКА ===
        {
            'id': 'msg_008',
            'text': '🚀 БАЛІСТИКА! Іскандер по Харкову!',
            'channel': 'monitor1654',
            'date': '2026-01-19 04:12:00',
        },
        # === ЗАГРОЗА МИНУЛА ===
        {
            'id': 'msg_009',
            'text': 'Шахед пролетів Полтаву, пішов далі на захід',
            'channel': 'monikppy',
            'date': '2026-01-19 04:15:00',
        },
        # === СТИЛЬ КУЧЕРА (короткі) ===
        {
            'id': 'msg_010',
            'text': '1х низько над містом',
            'channel': 'timofii_kucher',
            'date': '2026-01-19 04:20:00',
        },
        {
            'id': 'msg_011',
            'text': 'до 5х заходять',
            'channel': 'timofii_kucher',
            'date': '2026-01-19 04:25:00',
        },
    ]

    print("📨 ОБРОБКА ПОВІДОМЛЕНЬ:")
    print("-" * 70)

    for i, msg in enumerate(test_messages, 1):
        print(f"\n[{i}] Канал: @{msg['channel']}")
        print(f"    Текст: {msg['text'][:60]}...")

        # Обробка через AI-first систему
        result = fusion.process_message(msg)

        if result:
            sig = result['signature']
            print(f"    ✅ Дія: {result['action'].upper()}")
            print(f"    🎯 Тип: {sig.get('threat_type')} | Кількість: {sig.get('quantity')}")
            print(f"    📍 Регіони: {list(sig.get('regions', []))}")
            print(f"    ➡️ Напрямок: {sig.get('direction')}")
            print(f"    🤖 AI: {'✅' if sig.get('ai_analyzed') else '❌ regex'} | Action: {sig.get('action', 'create')}")
            if sig.get('target_coords'):
                print(f"    📌 Координати: {sig['target_coords']}")
        else:
            print("    ⚪ Не загроза або не розпізнано")

    # === ПІДСУМОК ===
    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТ ЗЛИТТЯ:")
    print("=" * 70)

    active_events = fusion.get_active_events()

    print(f"\n🔥 Активних подій: {len(active_events)}")

    for event in active_events:
        print(f"\n  📌 Event: {event['id']}")
        print(f"     Тип: {event['threat_type']} x{event['quantity']}")
        if event['quantity_destroyed'] > 0:
            print(f"     Збито: {event['quantity_destroyed']}")
        print(f"     Регіони: {event['regions']}")
        print(f"     Напрямок: {event['direction']}")
        print(f"     Статус: {event['status']}")
        print(f"     Джерел: {len({m['channel'] for m in event['messages']})}")
        print(f"     Впевненість: {event['confidence']:.0%}")

        # Траєкторія
        if len(event['trajectory']) > 1:
            print(f"     🛤️ Траєкторія: {len(event['trajectory'])} точок")
            trajectory = fusion.build_trajectory_from_event(event)
            if trajectory:
                print(f"        Відстань: {trajectory['total_distance_km']:.1f} км")

    # === МАРКЕРИ ===
    print("\n" + "-" * 70)
    print("🗺️ МАРКЕРИ ДЛЯ КАРТИ:")
    print("-" * 70)

    for event in active_events:
        marker = fusion.generate_marker_from_event(event)
        if marker:
            print(f"\n  📍 {marker['id']}")
            print(f"     Місце: {marker['place']}")
            print(f"     Координати: ({marker['lat']:.4f}, {marker['lng']:.4f})")
            print(f"     Текст: {marker['text']}")
            print(f"     Іконка: {marker['marker_icon']}")

    print("\n" + "=" * 70)
    print("✅ ТЕСТ ЗАВЕРШЕНО")
    print("=" * 70)

    if GROQ_ENABLED:
        print("\n💡 AI активний - повідомлення аналізуються через Groq LLM")
        print("   AI сам визначає: тип, кількість, координати, дії (create/move/remove)")
    else:
        print("\n⚠️ AI вимкнений - використовується fallback на regex")
        print("   Для повного функціоналу потрібен GROQ_API_KEY")

if __name__ == '__main__':
    main()
