#!/bin/bash
echo "🔐 Получение Telegram Session"
echo ""
echo "Тебе нужны API_ID и API_HASH от Telegram"
echo ""
echo "📋 Где взять:"
echo "1. Зайди на https://my.telegram.org/apps"
echo "2. Войди с номером телефона"
echo "3. Создай приложение (любое название)"
echo "4. Скопируй API ID и API Hash"
echo ""
read -p "Введи API_ID: " api_id
read -p "Введи API_HASH: " api_hash
echo ""
export TELEGRAM_API_ID=$api_id
export TELEGRAM_API_HASH=$api_hash
python3 generate_session.py
