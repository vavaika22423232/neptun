#!/usr/bin/env python3
"""
Швидкий тест - запуск з новою сесією (буде prompt для SMS коду)
"""

import asyncio
import logging
from datetime import datetime

import nest_asyncio
import pytz
from telethon import TelegramClient, events

# Виправлення для asyncio conflicts
try:
    nest_asyncio.apply()
except:
    pass

logging.basicConfig(
    format='[%(levelname)s] %(message)s',
    level=logging.INFO
)

API_ID = 24031340
API_HASH = '2daaa58652e315ce52adb1090313d36a'
PHONE = '+263781966038'

SOURCE_CHANNELS = ['UkraineAlarmSignal', 'kpszsu', 'war_monitor', 'napramok', 'raketa_trevoga', 'ukrainsiypposhnik']
TARGET_CHANNEL = 'mapstransler'

client = TelegramClient('test_session', API_ID, API_HASH)

async def test():
    print("╔════════════════════════════════════════════════════╗")
    print("║  🧪 ШВИДКИЙ ТЕСТ Channel Forwarder                 ║")
    print("╚════════════════════════════════════════════════════╝")
    print()
    print("⚠️  Буде запитано SMS код при першому запуску")
    print()

    await client.start(phone=PHONE)

    me = await client.get_me()
    print(f"✅ Авторизовано: {me.first_name} ({me.phone})")
    print()

    # Перевірка цільового каналу
    try:
        target = await client.get_entity(TARGET_CHANNEL)
        print(f"✅ Цільовий канал: {target.title}")
    except Exception as e:
        print(f"❌ Помилка доступу до @{TARGET_CHANNEL}: {e}")
        return

    # Перевірка вихідних каналів
    print()
    print("🔍 Перевірка вихідних каналів:")
    valid_sources = []
    for ch in SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(ch)
            valid_sources.append(ch)
            print(f"   ✅ {entity.title} (@{ch})")
        except Exception as e:
            print(f"   ❌ @{ch}: {e}")

    if not valid_sources:
        print("\n❌ Жодного каналу не знайдено!")
        return

    print()
    print(f"🎯 Моніторю {len(valid_sources)} каналів...")
    print("📨 Очікую нові повідомлення (Ctrl+C для зупинки)...")
    print()

    count = 0
    kyiv_tz = pytz.timezone('Europe/Kiev')

    print("🔧 DEBUG: Реєструю обробник подій...")

    @client.on(events.NewMessage(chats=valid_sources))
    async def handler(event):
        nonlocal count
        print(f"\n🔔 DEBUG: Обробник викликано! Event type: {type(event)}")
        try:
            msg = event.message
            chat = await event.get_chat()

            print(f"🔧 DEBUG: Chat ID: {chat.id}, Username: {chat.username}, Title: {getattr(chat, 'title', 'N/A')}")
            print(f"🔧 DEBUG: Message ID: {msg.id}, Has text: {bool(msg.text)}")

            kyiv_time = datetime.now(kyiv_tz)
            print(f"\n📨 [{kyiv_time.strftime('%H:%M:%S')}] Повідомлення з @{chat.username or chat.title}")
            print(f"   📝 Текст: {msg.text[:50] if msg.text else '(медіа)'}...")

            text = f"📢 Джерело: @{chat.username or chat.title}\n"
            text += f"⏰ {kyiv_time.strftime('%H:%M:%S %d.%m.%Y')} (Київ)\n"
            text += f"{'─' * 40}\n\n"
            if msg.text:
                text += msg.text

            print(f"   📤 Пересилаю в @{TARGET_CHANNEL}...")
            result = await client.send_message(TARGET_CHANNEL, text, file=msg.media if msg.media else None)
            count += 1
            print(f"   ✅ Переслано успішно! Message ID: {result.id} (всього: {count})\n")

        except Exception as e:
            print(f"   ❌ ПОМИЛКА при пересиланні: {e}")
            import traceback
            traceback.print_exc()

    print("🔧 DEBUG: Обробник зареєстровано!")

    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("\n\n⏹️ Тест зупинено")
