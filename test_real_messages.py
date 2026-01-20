#!/usr/bin/env python3
"""
Тест парсингу реальних повідомлень з українських Telegram каналів
"""

from datetime import datetime

from app import CHANNEL_FUSION

# Очистити попередні тести
CHANNEL_FUSION.fused_events.clear()
CHANNEL_FUSION.message_to_event.clear()

# Реальні приклади повідомлень з різних каналів
REAL_MESSAGES = [
    # === kpszsu (ПС ЗСУ) ===
    {
        'id': 'kpszsu_1',
        'channel': 'kpszsu',
        'text': '‼️ Загроза застосування балістичного озброєння з південного напрямку!',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },
    {
        'id': 'kpszsu_2',
        'channel': 'kpszsu',
        'text': '🔴 Ударні БПЛА типу "Shahed" з Криму. Курс - північний.',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },
    {
        'id': 'kpszsu_3',
        'channel': 'kpszsu',
        'text': '⚡️ Пуск крилатих ракет з акваторії Чорного моря!',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },

    # === vanek_nikolaev (Миколаївська область) ===
    {
        'id': 'vanek_1',
        'channel': 'vanek_nikolaev',
        'text': '🚨 Шахеди на підльоті до Миколаєва! Залишайтесь в укриттях!',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },
    {
        'id': 'vanek_2',
        'channel': 'vanek_nikolaev',
        'text': 'БПЛА над містом, рухається на північ',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },

    # === gnilayachereha (Запорізька область) ===
    {
        'id': 'zp_1',
        'channel': 'gnilayachereha',
        'text': '⚠️ В області чутно вибухи. Працює ППО.',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },
    {
        'id': 'zp_2',
        'channel': 'gnilayachereha',
        'text': 'Група шахедів 5 одиниць рухається через область. Напрямок Дніпро.',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },

    # === timofii_kucher (Дніпропетровська область) ===
    {
        'id': 'dp_1',
        'channel': 'timofii_kucher',
        'text': '🔴 УВАГА! Дрони наближаються до області з південного сходу!',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },
    {
        'id': 'dp_2',
        'channel': 'timofii_kucher',
        'text': 'Ворожі БПЛА над Кривим Рогом. Курс на Дніпро.',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },

    # === monitor1654 (Харківська область) ===
    {
        'id': 'kh_1',
        'channel': 'monitor1654',
        'text': '⚡️ КАБи по Харкову! Всім в укриття!',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },
    {
        'id': 'kh_2',
        'channel': 'monitor1654',
        'text': 'Загроза балістики з Бєлгородського напрямку',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },

    # === korabely_media (Південь) ===
    {
        'id': 'south_1',
        'channel': 'korabely_media',
        'text': '🚀 Пуск ракет з Криму! Херсонська, Миколаївська області - загроза!',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },
    {
        'id': 'south_2',
        'channel': 'korabely_media',
        'text': 'Шахеди над Одеською областю. Кількість до 10. Курс на Київ.',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },

    # === napramok ===
    {
        'id': 'napr_1',
        'channel': 'napramok',
        'text': '➡️ Шахед над Вінницькою областю, напрямок - Житомир',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },

    # === raketa_trevoga ===
    {
        'id': 'rak_1',
        'channel': 'raketa_trevoga',
        'text': '🚨 БАЛІСТИКА! Харків, Дніпро - в укриття терміново!',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },

    # === Складні повідомлення ===
    {
        'id': 'complex_1',
        'channel': 'emonitor_ua',
        'text': '''🔴 ОНОВЛЕННЯ ЗАГРОЗ:

• 12 шахедів в повітрі
• Курс: Миколаїв → Кіровоград → Київ
• 3 збито над Черкащиною
• Група розділилась на 2 частини

⚠️ Очікуваний час підльоту до Києва: 40 хв''',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },
    {
        'id': 'complex_2',
        'channel': 'monikppy',
        'text': '❗️Група "Герань-2" (6 од.) пройшла Полтавську обл. Курс на Київ. 2 знищено ППО.',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    },
]

print('=' * 70)
print('ТЕСТ ПАРСИНГУ РЕАЛЬНИХ ПОВІДОМЛЕНЬ')
print('=' * 70)
print()

for msg in REAL_MESSAGES:
    sig = CHANNEL_FUSION.extract_message_signature(msg)

    print(f'📨 [{msg["channel"]}]')
    print(f'   Текст: {msg["text"][:80]}{"..." if len(msg["text"]) > 80 else ""}')
    print('   ─────────────────────────────────')
    print(f'   🎯 Тип загрози: {sig["threat_type"] or "❌ не визначено"}')
    print(f'   📍 Регіони: {list(sig["regions"]) if sig["regions"] else "❌ не визначено"}')
    print(f'   ➡️  Напрямок: {sig["direction"] or "❌ не визначено"}')
    print(f'   🔢 Кількість: {sig["quantity"]}')
    print(f'   🏷️  Ключові слова: {list(sig["keywords"]) if sig["keywords"] else "-"}')
    print()

print('=' * 70)
print('ПІДСУМОК')
print('=' * 70)

# Статистика
total = len(REAL_MESSAGES)
with_threat = sum(1 for m in REAL_MESSAGES if CHANNEL_FUSION.extract_message_signature(m)['threat_type'])
with_region = sum(1 for m in REAL_MESSAGES if CHANNEL_FUSION.extract_message_signature(m)['regions'])
with_direction = sum(1 for m in REAL_MESSAGES if CHANNEL_FUSION.extract_message_signature(m)['direction'])

print(f'Всього повідомлень: {total}')
print(f'Визначено тип загрози: {with_threat}/{total} ({100*with_threat//total}%)')
print(f'Визначено регіон: {with_region}/{total} ({100*with_region//total}%)')
print(f'Визначено напрямок: {with_direction}/{total} ({100*with_direction//total}%)')
print()

if with_threat < total * 0.7:
    print('⚠️  УВАГА: Потрібно покращити парсинг типів загроз!')
if with_region < total * 0.8:
    print('⚠️  УВАГА: Потрібно покращити парсинг регіонів!')
