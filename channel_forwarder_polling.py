#!/usr/bin/env python3
"""
Channel Forwarder з polling (опитування)
Перевіряє канали кожні 30 секунд
"""

import asyncio
import logging
from datetime import datetime, timedelta
import pytz
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import nest_asyncio

# Виправлення для asyncio
nest_asyncio.apply()

logging.basicConfig(
    format='[%(levelname)s/%(asctime)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфігурація
API_ID = int(os.getenv('TELEGRAM_API_ID', '24031340'))
API_HASH = os.getenv('TELEGRAM_API_HASH', '2daaa58652e315ce52adb1090313d36a')
PHONE = '+263781966038'
STRING_SESSION = os.getenv('TELEGRAM_SESSION', '')

SOURCE_CHANNELS = os.getenv('SOURCE_CHANNELS', 'UkraineAlarmSignal,kpszsu,war_monitor,napramok,raketa_trevoga,ukrainsiypposhnik').split(',')
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', 'mapstransler')

# Інтервал опитування (секунди)
POLL_INTERVAL = 30

# Словник для зберігання ID останніх переслані повідомлень
last_message_ids = {}

client = TelegramClient('test_session', API_ID, API_HASH)


async def check_and_forward():
    """Перевірка нових повідомлень та пересилання"""
    kyiv_tz = pytz.timezone('Europe/Kiev')
    forwarded_count = 0
    
    for channel in SOURCE_CHANNELS:
        channel = channel.strip()
        if not channel:
            continue
            
        try:
            entity = await client.get_entity(channel)
            
            # Отримуємо останнє повідомлення
            async for message in client.iter_messages(entity, limit=1):
                # Перевіряємо, чи вже пересилали це повідомлення
                if channel not in last_message_ids:
                    # Перший запуск - зберігаємо ID і пропускаємо
                    last_message_ids[channel] = message.id
                    logger.info(f"📌 {channel}: збережено початковий ID {message.id}")
                    continue
                
                if message.id > last_message_ids[channel]:
                    # Нове повідомлення!
                    logger.info(f"🆕 Нове повідомлення в @{channel}: ID {message.id}")
                    
                    # Формуємо текст
                    kyiv_time = datetime.now(kyiv_tz)
                    text = f"📢 Джерело: @{channel}\n"
                    text += f"⏰ {kyiv_time.strftime('%H:%M:%S %d.%m.%Y')} (Київ)\n"
                    text += f"{'─' * 40}\n\n"
                    
                    if message.text:
                        text += message.text
                    
                    # Пересилаємо
                    try:
                        if message.media:
                            await client.send_message(
                                TARGET_CHANNEL,
                                text,
                                file=message.media
                            )
                        else:
                            await client.send_message(
                                TARGET_CHANNEL,
                                text
                            )
                        
                        # Оновлюємо ID
                        last_message_ids[channel] = message.id
                        forwarded_count += 1
                        logger.info(f"✅ Переслано з @{channel} в @{TARGET_CHANNEL}")
                        
                    except Exception as e:
                        logger.error(f"❌ Помилка пересилання з @{channel}: {e}")
                
        except Exception as e:
            logger.error(f"❌ Помилка перевірки @{channel}: {e}")
    
    if forwarded_count > 0:
        logger.info(f"📊 Переслано {forwarded_count} повідомлень")


async def main():
    """Головна функція"""
    logger.info("🚀 Запуск Channel Forwarder (Polling mode)...")
    
    await client.start()
    
    me = await client.get_me()
    logger.info(f"✅ Авторизовано: {me.first_name} ({me.phone})")
    
    # Перевірка цільового каналу
    try:
        target = await client.get_entity(TARGET_CHANNEL)
        logger.info(f"✅ Цільовий канал: {target.title} (@{TARGET_CHANNEL})")
    except Exception as e:
        logger.error(f"❌ Не вдалося знайти @{TARGET_CHANNEL}: {e}")
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
            logger.warning(f"⚠️ Не вдалося знайти @{channel}: {e}")
    
    if not valid_sources:
        logger.error("❌ Жодного каналу не знайдено!")
        return
    
    logger.info(f"\n📊 Моніторю {len(valid_sources)} каналів")
    logger.info(f"⏱️  Перевірка кожні {POLL_INTERVAL} секунд")
    logger.info(f"🎯 Пересилання в @{TARGET_CHANNEL}\n")
    
    # Головний цикл опитування
    while True:
        try:
            await check_and_forward()
            await asyncio.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"❌ Помилка в циклі: {e}")
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n⏹️ Бот зупинено")
    except Exception as e:
        logger.error(f"\n\n❌ Критична помилка: {e}")
        raise
