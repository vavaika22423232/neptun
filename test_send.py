#!/usr/bin/env python3
"""
Тест відправки повідомлення в канал
"""

import asyncio
from telethon import TelegramClient

API_ID = 24031340
API_HASH = '2daaa58652e315ce52adb1090313d36a'
TARGET_CHANNEL = 'mapstransler'

async def test():
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start()
    
    me = await client.get_me()
    print(f"✅ Авторизовано: {me.first_name} ({me.phone})\n")
    
    print(f"📤 Спроба відправити тестове повідомлення в @{TARGET_CHANNEL}...")
    
    try:
        result = await client.send_message(TARGET_CHANNEL, "🧪 Тестове повідомлення від бота пересилання\n⏰ Перевірка прав доступу")
        print(f"✅ Успішно відправлено! Message ID: {result.id}")
    except Exception as e:
        print(f"❌ Помилка: {e}")
        import traceback
        traceback.print_exc()
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test())
