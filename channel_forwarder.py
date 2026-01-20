#!/usr/bin/env python3
"""
Telegram Channel Forwarder Bot
Пересилає повідомлення з вихідних каналів до цільового каналу
"""

import asyncio
import logging
from datetime import datetime

import pytz
from telethon import TelegramClient, events
from telethon.tl.types import Message

# Налаштування логування
logging.basicConfig(
    format='[%(levelname)s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфігурація API
API_ID = 24031340
API_HASH = '2daaa58652e315ce52adb1090313d36a'
PHONE = '+263781966038'
SESSION_NAME = 'channel_forwarder'

# Вихідні канали (звідки копіюємо)
SOURCE_CHANNELS = [
    # Офіційні/головні
    'kpszsu',               # ПС ЗСУ - найвища довіра
    'UkraineAlarmSignal',   # Офіційні тривоги
    'povitryanatrivogaaa',  # Повітряна тривога

    # Загальнонаціональні моніторинги
    'emonitor_ua',          # E-Monitor
    'monikppy',             # Моніторинг ППО
    'war_monitor',          # Військовий моніторинг
    'napramok',             # Напрямок руху
    'raketa_trevoga',       # Ракетна тривога
    'sectorv666',           # Sector V
    'ukrainsiypposhnik',    # Повітряні сили

    # Регіональні (південь)
    'korabely_media',       # Південь: Херсон, Миколаїв, Одеса
    'vanek_nikolaev',       # Миколаївська область
    'kherson_monitoring',   # Херсонська область

    # Регіональні (схід/центр)
    'gnilayachereha',       # Запорізька область
    'timofii_kucher',       # Дніпропетровська область
    'monitor1654',          # Харківська область
]

# Цільовий канал (куди пересилаємо)
TARGET_CHANNEL = 'mapstransler'  # або '@mapstransler'

# Ініціалізація клієнта
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


async def main():
    """Головна функція бота"""

    logger.info("🚀 Запуск Channel Forwarder Bot...")

    # Київський часовий пояс
    kyiv_tz = pytz.timezone('Europe/Kiev')

    # Підключення до Telegram
    await client.start(phone=PHONE)

    logger.info("✅ Підключено до Telegram")

    # Перевірка доступу до каналів
    logger.info("🔍 Перевірка доступу до каналів...")

    try:
        target_entity = await client.get_entity(TARGET_CHANNEL)
        logger.info(f"✅ Цільовий канал знайдено: {target_entity.title}")
    except Exception as e:
        logger.error(f"❌ Не вдалося знайти цільовий канал {TARGET_CHANNEL}: {e}")
        logger.error("Переконайтеся що ви є адміністратором каналу!")
        return

    # Перевірка вихідних каналів
    valid_sources = []
    for channel in SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(channel)
            valid_sources.append(channel)
            logger.info(f"✅ Вихідний канал знайдено: {entity.title} (@{channel})")
        except Exception as e:
            logger.warning(f"⚠️ Не вдалося знайти канал @{channel}: {e}")

    if not valid_sources:
        logger.error("❌ Жодного вихідного каналу не знайдено!")
        return

    logger.info("\n📊 Статистика:")
    logger.info(f"   Вихідних каналів: {len(valid_sources)}/{len(SOURCE_CHANNELS)}")
    logger.info(f"   Цільовий канал: @{TARGET_CHANNEL}")
    logger.info("\n🎯 Бот запущено! Очікую нові повідомлення...\n")

    # Лічильник пересланих повідомлень
    forwarded_count = 0

    @client.on(events.NewMessage(chats=valid_sources))
    async def handler(event):
        """Обробник нових повідомлень"""
        nonlocal forwarded_count

        try:
            message: Message = event.message
            source_chat = await event.get_chat()

            # Отримуємо назву вихідного каналу
            source_name = getattr(source_chat, 'title', source_chat.username or 'Unknown')

            logger.info(f"📨 Нове повідомлення з @{source_chat.username or source_name}")

            # Формуємо текст для пересилання
            kyiv_time = datetime.now(kyiv_tz)
            forward_text = f"📢 Джерело: @{source_chat.username or source_name}\n"
            forward_text += f"⏰ Час: {kyiv_time.strftime('%H:%M:%S %d.%m.%Y')} (Київ)\n"
            forward_text += f"{'─' * 40}\n\n"

            # Додаємо оригінальний текст
            if message.text:
                forward_text += message.text

            # Пересилаємо повідомлення
            try:
                # Якщо є медіа, пересилаємо з медіа
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

    # Запуск клієнта (нескінченний цикл)
    logger.info("🔄 Бот працює... (Ctrl+C для зупинки)")
    await client.run_until_disconnected()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n⏹️ Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"\n\n❌ Критична помилка: {e}")
