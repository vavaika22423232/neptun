#!/usr/bin/env python3
"""
Перевірка прав доступу до каналів
"""

import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel

API_ID = 24031340
API_HASH = '2daaa58652e315ce52adb1090313d36a'

SOURCE_CHANNELS = ['UkraineAlarmSignal', 'kpszsu', 'war_monitor', 'napramok', 'raketa_trevoga', 'ukrainsiypposhnik']
TARGET_CHANNEL = 'mapstransler'

async def check():
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start()
    
    me = await client.get_me()
    print(f"✅ Авторизовано: {me.first_name} ({me.phone})\n")
    
    # Перевірка ЦІЛЬОВОГО каналу (де треба мати права адміна)
    print("🎯 ЦІЛЬОВИЙ КАНАЛ (куди пересилаємо):")
    print("=" * 60)
    try:
        target = await client.get_entity(TARGET_CHANNEL)
        print(f"📢 Назва: {target.title}")
        print(f"🆔 Username: @{target.username if target.username else 'немає'}")
        print(f"👥 ID: {target.id}")
        
        # Перевіряємо, чи можемо писати
        if isinstance(target, Channel):
            if target.broadcast and not target.megagroup:
                print(f"📻 Тип: Канал (broadcast)")
            elif target.megagroup:
                print(f"💬 Тип: Супергрупа")
            
            # Отримуємо наші права
            full = await client.get_permissions(target)
            print(f"\n🔑 Ваші права:")
            print(f"   • Писати повідомлення: {'✅' if full.post_messages else '❌'}")
            print(f"   • Редагувати повідомлення: {'✅' if full.edit_messages else '❌'}")
            print(f"   • Адміністратор: {'✅' if full.is_admin else '❌'}")
            
            if not full.post_messages:
                print(f"\n❌ ПРОБЛЕМА: Ви не можете писати в @{TARGET_CHANNEL}!")
                print(f"   Рішення: додайте акаунт {me.phone} як адміна каналу")
        
    except Exception as e:
        print(f"❌ Помилка доступу: {e}\n")
    
    # Перевірка ВИХІДНИХ каналів (звідки читаємо)
    print("\n\n📡 ВИХІДНІ КАНАЛИ (звідки читаємо):")
    print("=" * 60)
    
    for ch_name in SOURCE_CHANNELS:
        try:
            channel = await client.get_entity(ch_name)
            print(f"\n✅ @{ch_name}")
            print(f"   📢 {channel.title}")
            print(f"   🆔 ID: {channel.id}")
            
            # Перевіряємо підписку
            try:
                participant = await client.get_permissions(channel, me)
                if participant:
                    print(f"   👤 Підписано: ✅")
                else:
                    print(f"   👤 Підписано: ❌ (треба підписатися!)")
            except:
                print(f"   👤 Підписано: невідомо")
                
        except Exception as e:
            print(f"\n❌ @{ch_name}: {e}")
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(check())
