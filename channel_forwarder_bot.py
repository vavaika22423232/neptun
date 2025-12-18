"""
Альтернативна версія: Використання Bot API (токен)
Працює без номера телефону, але має обмеження на пересилання
"""

import asyncio
import logging
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Налаштування логування
logging.basicConfig(
    format='[%(levelname)s/%(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфігурація
BOT_TOKEN = '8511265361:AAG3h9ZbT0vNn1g73m6fdfrUkjf0OJX8X54'
TARGET_CHANNEL = '@mapstransler'  # Куди пересилати

# ID каналів звідки копіювати (потрібно отримати вручну)
# Використайте @username_to_id_bot щоб отримати ID каналів
SOURCE_CHANNEL_IDS = [
    # Додайте ID каналів тут після отримання
    # Наприклад: -1001234567890
]

# ВАЖЛИВО: Бот повинен бути адміністратором в цільовому каналі!


async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник повідомлень для пересилання"""
    
    try:
        message = update.message or update.channel_post
        
        if not message:
            return
        
        # Перевірка чи це повідомлення з вихідного каналу
        chat_id = message.chat.id
        
        if SOURCE_CHANNEL_IDS and chat_id not in SOURCE_CHANNEL_IDS:
            return
        
        # Формуємо текст
        source_name = message.chat.title or message.chat.username or 'Unknown'
        
        forward_text = f"📢 Джерело: {source_name}\n"
        forward_text += f"⏰ Час: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}\n"
        forward_text += f"{'─' * 40}\n\n"
        
        if message.text:
            forward_text += message.text
        
        # Пересилаємо
        if message.photo:
            await context.bot.send_photo(
                chat_id=TARGET_CHANNEL,
                photo=message.photo[-1].file_id,
                caption=forward_text
            )
        elif message.video:
            await context.bot.send_video(
                chat_id=TARGET_CHANNEL,
                video=message.video.file_id,
                caption=forward_text
            )
        elif message.document:
            await context.bot.send_document(
                chat_id=TARGET_CHANNEL,
                document=message.document.file_id,
                caption=forward_text
            )
        else:
            await context.bot.send_message(
                chat_id=TARGET_CHANNEL,
                text=forward_text
            )
        
        logger.info(f"✅ Переслано з {source_name}")
        
    except Exception as e:
        logger.error(f"❌ Помилка пересилання: {e}")


async def main():
    """Головна функція"""
    
    logger.info("🚀 Запуск Bot API Forwarder...")
    
    # Створення додатку
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Додаємо обробник для всіх повідомлень
    app.add_handler(MessageHandler(
        filters.ALL,
        forward_message
    ))
    
    logger.info("✅ Бот запущено!")
    logger.info("⚠️ ВАЖЛИВО: Додайте бота як адміністратора в канали!")
    logger.info(f"🎯 Пересилання до: {TARGET_CHANNEL}")
    
    # Запуск
    await app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️ Бот зупинено")
