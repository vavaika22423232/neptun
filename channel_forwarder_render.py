#!/usr/bin/env python3
"""
Channel Forwarder Bot для Render
Використовує STRING_SESSION для автоматичної авторизації
"""

import os
import asyncio
import logging
from datetime import datetime
import pytz
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Налаштування логування
logging.basicConfig(
    format='[%(levelname)s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфігурація з environment variables
API_ID = int(os.getenv('TELEGRAM_API_ID', '24031340'))
API_HASH = os.getenv('TELEGRAM_API_HASH', '2daaa58652e315ce52adb1090313d36a')
STRING_SESSION = os.getenv('TELEGRAM_SESSION', '')  # Буде створено окремим скриптом

# Вихідні канали
SOURCE_CHANNELS = os.getenv('SOURCE_CHANNELS', 'kpszsu,UkraineAlarmSignal,povitryanatrivogaaa,emonitor_ua,monikppy,war_monitor,napramok,raketa_trevoga,sectorv666,ukrainsiypposhnik,korabely_media,vanek_nikolaev,kherson_monitoring,gnilayachereha,timofii_kucher,monitor1654').split(',')

# Цільовий канал
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', 'mapstransler')

# Ініціалізація клієнта з StringSession
if STRING_SESSION:
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
else:
    logger.error("❌ TELEGRAM_SESSION не встановлено!")
    logger.error("Запустіть generate_string_session.py локально для отримання сесії")
    exit(1)


async def main():
    """Головна функція бота"""
    
    logger.info("🚀 Запуск Channel Forwarder Bot на Render...")
    
    # Київський часовий пояс
    kyiv_tz = pytz.timezone('Europe/Kiev')
    
    # Підключення до Telegram
    await client.start()
    
    if not await client.is_user_authorized():
        logger.error("❌ Сесія недійсна! Перегенеруйте STRING_SESSION")
        return
    
    me = await client.get_me()
    logger.info(f"✅ Авторизовано як: {me.first_name} ({me.phone})")
    
    # Перевірка доступу до каналів
    logger.info("🔍 Перевірка доступу до каналів...")
    
    try:
        target_entity = await client.get_entity(TARGET_CHANNEL)
        logger.info(f"✅ Цільовий канал: {target_entity.title}")
    except Exception as e:
        logger.error(f"❌ Не вдалося знайти цільовий канал {TARGET_CHANNEL}: {e}")
        return
    
    # Перевірка вихідних каналів
    valid_sources = []
    for channel in SOURCE_CHANNELS:
        channel = channel.strip()
        if not channel:
            continue
        try:
            entity = await client.get_entity(channel)
            valid_sources.append(channel)
            logger.info(f"✅ Вихідний канал: {entity.title} (@{channel})")
        except Exception as e:
            logger.warning(f"⚠️ Не вдалося знайти канал @{channel}: {e}")
    
    if not valid_sources:
        logger.error("❌ Жодного вихідного каналу не знайдено!")
        return
    
    logger.info(f"\n📊 Статистика:")
    logger.info(f"   Вихідних каналів: {len(valid_sources)}/{len(SOURCE_CHANNELS)}")
    logger.info(f"   Цільовий канал: @{TARGET_CHANNEL}")
    logger.info(f"\n🎯 Бот запущено на Render! Очікую нові повідомлення...\n")
    
    # Лічильник
    forwarded_count = 0
    
    @client.on(events.NewMessage(chats=valid_sources))
    async def handler(event):
        """Обробник нових повідомлень"""
        nonlocal forwarded_count
        
        try:
            message = event.message
            source_chat = await event.get_chat()
            source_name = getattr(source_chat, 'title', source_chat.username or 'Unknown')
            
            logger.info(f"📨 Нове повідомлення з @{source_chat.username or source_name}")
            
            # Формуємо текст
            kyiv_time = datetime.now(kyiv_tz)
            forward_text = f"📢 Джерело: @{source_chat.username or source_name}\n"
            forward_text += f"⏰ Час: {kyiv_time.strftime('%H:%M:%S %d.%m.%Y')} (Київ)\n"
            forward_text += f"{'─' * 40}\n\n"
            
            if message.text:
                forward_text += message.text
            
            # Пересилаємо
            try:
                if message.media:
                    await client.send_message(
                        TARGET_CHANNEL,
                        forward_text,
                        file=message.media
                    )
                else:
                    await client.send_message(
                        TARGET_CHANNEL,
                        forward_text
                    )
                
                forwarded_count += 1
                logger.info(f"✅ Переслано до @{TARGET_CHANNEL} (всього: {forwarded_count})")
                
            except Exception as e:
                logger.error(f"❌ Помилка при пересиланні: {e}")
                
        except Exception as e:
            logger.error(f"❌ Помилка обробки повідомлення: {e}")
    
    # Запуск
    logger.info("🔄 Бот працює на Render...")
    await client.run_until_disconnected()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n⏹️ Бот зупинено")
    except Exception as e:
        logger.error(f"\n\n❌ Критична помилка: {e}")
        raise
