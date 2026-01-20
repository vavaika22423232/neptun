#!/usr/bin/env python3
"""
Тест читання та пересилання з @napramok
"""

import asyncio
from datetime import datetime

import pytz
from telethon import TelegramClient

API_ID = 24031340
API_HASH = '2daaa58652e315ce52adb1090313d36a'

async def test():
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start()

    kyiv_tz = pytz.timezone('Europe/Kiev')

    print("📖 Читаю останнє повідомлення з @napramok:\n")

    channel = await client.get_entity('napramok')

    async for msg in client.iter_messages(channel, limit=1):
        print(f"🆔 ID: {msg.id}")
        print(f"⏰ Час: {msg.date}")
        print(f"📝 Текст: {msg.text[:200] if msg.text else '(медіа)'}...")
        print()

        # Пересилаємо
        kyiv_time = datetime.now(kyiv_tz)
        text = "📢 Джерело: @napramok\n"
        text += f"⏰ Час: {kyiv_time.strftime('%H:%M:%S %d.%m.%Y')} (Київ)\n"
        text += f"{'─' * 40}\n\n"
        if msg.text:
            text += msg.text

        print("📤 Пересилаю в @mapstransler...")
        try:
            result = await client.send_message('mapstransler', text, file=msg.media if msg.media else None)
            print(f"✅ Відправлено! Message ID: {result.id}")
        except Exception as e:
            print(f"❌ Помилка: {e}")
            import traceback
            traceback.print_exc()

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test())
