#!/usr/bin/env python3
"""
Скрипт для ручной авторизации в Telegram
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

# Загружаем переменные из .env
def load_env():
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip(); v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v

load_env()

API_ID = int(os.getenv('TELEGRAM_API_ID', '0') or '0')
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
PHONE = input("Введите номер телефона (с +): ")

print(f"API_ID: {API_ID}")
print(f"API_HASH: {API_HASH[:10]}...")
print(f"Phone: {PHONE}")

async def main():
    # Создаем клиент с пустой сессией
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    try:
        print("Подключаемся к Telegram...")
        await client.connect()
        
        print("Проверяем авторизацию...")
        if not await client.is_user_authorized():
            print("Не авторизованы. Начинаем процесс авторизации...")
            
            # Отправляем код
            await client.send_code_request(PHONE)
            
            # Запрашиваем код у пользователя
            code = input("Введите код из SMS/Telegram: ")
            
            try:
                # Пытаемся войти с кодом
                await client.sign_in(PHONE, code)
            except Exception as e:
                print(f"Ошибка при входе с кодом: {e}")
                # Возможно, нужен пароль двухфакторной аутентификации
                password = input("Введите пароль двухфакторной аутентификации (если есть): ")
                if password:
                    await client.sign_in(password=password)
        
        print("Успешно авторизованы!")
        
        # Получаем строковую сессию
        session_string = client.session.save()
        print("\n" + "="*50)
        print("НОВАЯ TELEGRAM_SESSION:")
        print(session_string)
        print("="*50)
        
        # Сохраняем в файл для удобства
        with open('new_session.txt', 'w') as f:
            f.write(session_string)
        print("Сессия сохранена в файл new_session.txt")
        
        # Проверяем, что сессия работает
        me = await client.get_me()
        print(f"Вы вошли как: {me.first_name} {me.last_name or ''} (@{me.username or 'без username'})")
        
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
