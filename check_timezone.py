#!/usr/bin/env python3
"""
Перевірка часового поясу
"""

import asyncio
from telethon import TelegramClient
from datetime import datetime
import pytz

API_ID = 24031340
API_HASH = '2daaa58652e315ce52adb1090313d36a'

async def check():
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start()
    
    # Читаємо останнє повідомлення
    channel = await client.get_entity('kpszsu')
    
    async for msg in client.iter_messages(channel, limit=1):
        print("⏰ ПОРІВНЯННЯ ЧАСУ:")
        print("=" * 60)
        print(f"📅 Час повідомлення в Telegram: {msg.date}")
        print(f"📅 Час повідомлення (UTC): {msg.date.strftime('%H:%M:%S %d.%m.%Y')}")
        
        # Конвертуємо в київський час
        kyiv_tz = pytz.timezone('Europe/Kiev')
        kyiv_time = msg.date.astimezone(kyiv_tz)
        print(f"🇺🇦 Час повідомлення (Київ): {kyiv_time.strftime('%H:%M:%S %d.%m.%Y')}")
        
        print()
        print(f"🖥️  Поточний час системи: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}")
        print(f"🌍 Поточний час UTC: {datetime.utcnow().strftime('%H:%M:%S %d.%m.%Y')}")
        
        kyiv_now = datetime.now(kyiv_tz)
        print(f"🇺🇦 Поточний час (Київ): {kyiv_now.strftime('%H:%M:%S %d.%m.%Y')}")
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(check())
