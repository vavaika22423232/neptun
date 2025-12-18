#!/usr/bin/env python3
"""
Читання останніх повідомлень з каналів для перевірки
"""

import asyncio
from telethon import TelegramClient
from datetime import datetime

API_ID = 24031340
API_HASH = '2daaa58652e315ce52adb1090313d36a'

async def test():
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start()
    
    print("📖 Читаю останні 3 повідомлення з @kpszsu:\n")
    
    channel = await client.get_entity('kpszsu')
    
    async for message in client.iter_messages(channel, limit=3):
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🆔 ID: {message.id}")
        print(f"⏰ Час: {message.date}")
        print(f"📝 Текст: {message.text[:200] if message.text else '(медіа)'}...")
        print()
    
    print("\n🧪 Тепер відправлю останнє повідомлення в @mapstransler для тесту...")
    
    async for message in client.iter_messages(channel, limit=1):
        text = f"📢 Джерело: @kpszsu\n"
        text += f"⏰ {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}\n"
        text += f"{'─' * 40}\n\n"
        if message.text:
            text += message.text
        
        try:
            result = await client.send_message('mapstransler', text, file=message.media if message.media else None)
            print(f"✅ Відправлено! Message ID: {result.id}")
        except Exception as e:
            print(f"❌ Помилка: {e}")
            import traceback
            traceback.print_exc()
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test())
