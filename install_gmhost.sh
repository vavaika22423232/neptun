#!/bin/bash

# Скрипт установки зависимостей для NEPTUN на GMhost
# Запустите этот скрипт через SSH на сервере GMhost

set -e  # Остановить при ошибке

echo "🚀 Установка зависимостей для NEPTUN на GMhost..."
echo "📍 Текущая директория: $(pwd)"

# Проверяем версию Python
echo "🐍 Проверяем Python..."
python3 --version || { echo "❌ Python3 не найден!"; exit 1; }
pip3 --version || { echo "❌ pip3 не найден!"; exit 1; }

# Создаем необходимые директории
echo "📁 Создаем директории..."
mkdir -p logs
mkdir -p data
mkdir -p tmp

# Устанавливаем pip пакеты локально с проверкой
echo "📦 Устанавливаем Python пакеты..."
packages=(
    "flask==3.0.3"
    "telethon==1.35.0" 
    "pytz==2024.1"
    "requests==2.32.3"
    "spacy==3.8.7"
)

for package in "${packages[@]}"; do
    echo "  ⬇️ Устанавливаем $package..."
    pip3 install --user "$package" || {
        echo "  ⚠️ Не удалось установить $package, пробуем без версии..."
        pip3 install --user "${package%%==*}" || echo "  ❌ Ошибка установки $package"
    }
done

# Устанавливаем украинскую модель SpaCy
echo "🇺🇦 Устанавливаем украинскую модель SpaCy..."
SPACY_MODEL_URL="https://github.com/explosion/spacy-models/releases/download/uk_core_news_sm-3.8.0/uk_core_news_sm-3.8.0-py3-none-any.whl"
pip3 install --user "$SPACY_MODEL_URL" || {
    echo "  ⚠️ Альтернативная установка SpaCy модели..."
    python3 -m spacy download uk_core_news_sm || echo "  ❌ Не удалось установить SpaCy модель"
}

# Проверяем наличие критически важных файлов
echo "🔍 Проверяем файлы проекта..."
required_files=("app.py" "index.py" ".htaccess")
for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "  ✅ $file найден"
    else
        echo "  ❌ $file НЕ НАЙДЕН!"
        echo "  💡 Убедитесь, что все файлы проекта загружены"
    fi
done

# Устанавливаем права доступа
echo "🔐 Устанавливаем права доступа..."
chmod 755 index.py 2>/dev/null && echo "  ✅ index.py - 755" || echo "  ⚠️ index.py не найден"  
chmod 755 app.py 2>/dev/null && echo "  ✅ app.py - 755" || echo "  ⚠️ app.py не найден"
chmod 644 .htaccess 2>/dev/null && echo "  ✅ .htaccess - 644" || echo "  ⚠️ .htaccess не найден"
chmod 600 .env 2>/dev/null && echo "  ✅ .env - 600" || echo "  💡 .env не найден (создайте из env_example.txt)"
chmod 755 templates/ 2>/dev/null && echo "  ✅ templates/ - 755" || echo "  💡 templates/ не найден"

# Проверяем установленные пакеты
echo "🔍 Проверяем установленные пакеты..."
python3 -c "import flask; print('  ✅ Flask импортируется')" || echo "  ❌ Flask НЕ работает"
python3 -c "import telethon; print('  ✅ Telethon импортируется')" || echo "  ❌ Telethon НЕ работает" 
python3 -c "import spacy; print('  ✅ SpaCy импортируется')" || echo "  ❌ SpaCy НЕ работает"
python3 -c "import spacy; nlp=spacy.load('uk_core_news_sm'); print('  ✅ Украинская модель SpaCy работает')" || echo "  ⚠️ Украинская модель SpaCy НЕ работает"

echo ""
echo "✅ Установка завершена!"
echo ""
echo "� Следующие шаги:"
echo "1. Создайте файл .env из env_example.txt"
echo "2. Заполните ваши Telegram API данные в .env"  
echo "3. Откройте ваш сайт в браузере для проверки"
echo ""
echo "🆘 При проблемах:"
echo "- Проверьте логи: tail -20 ~/logs/error.log"
echo "- Свяжитесь с поддержкой GMhost: support@gmhost.com.ua"
echo ""
