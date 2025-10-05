#!/bin/bash

# Скрипт установки зависимостей для GMhost
# Запустите этот скрипт через SSH на сервере GMhost

echo "🚀 Установка зависимостей для NEPTUN на GMhost..."

# Устанавливаем pip пакеты локально
pip3 install --user flask==3.0.3
pip3 install --user telethon==1.35.0
pip3 install --user pytz==2024.1
pip3 install --user requests==2.32.3
pip3 install --user spacy==3.8.7

# Устанавливаем украинскую модель SpaCy
echo "📦 Устанавливаем украинскую модель SpaCy..."
pip3 install --user https://github.com/explosion/spacy-models/releases/download/uk_core_news_sm-3.8.0/uk_core_news_sm-3.8.0-py3-none-any.whl

# Создаем необходимые директории
mkdir -p logs
mkdir -p data

# Устанавливаем права доступа
chmod 755 index.py
chmod 755 app.py
chmod 644 .htaccess

echo "✅ Установка завершена!"
echo "💡 Теперь загрузите файлы проекта в корневую директорию сайта"
