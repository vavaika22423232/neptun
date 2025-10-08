#!/bin/bash

# 🔧 БЫСТРОЕ ИСПРАВЛЕНИЕ ПРОБЛЕМ
# Этот скрипт автоматически найдет и исправит большинство проблем

echo "🔍 NEPTUN QUICK FIX - Автоматическое исправление проблем"
echo "=================================================="

# Функция для проверки команды
check_command() {
    if command -v $1 >/dev/null 2>&1; then
        echo "✅ $1 найден"
    else
        echo "❌ $1 не найден"
        return 1
    fi
}

# Функция для проверки файла
check_file() {
    if [ -f "$1" ]; then
        echo "✅ Файл $1 существует"
        return 0
    else
        echo "❌ Файл $1 не найден"
        return 1
    fi
}

# Функция для проверки процесса
check_process() {
    if pgrep -f "$1" > /dev/null; then
        echo "✅ Процесс $1 запущен"
        return 0
    else
        echo "❌ Процесс $1 не запущен"
        return 1
    fi
}

echo ""
echo "🔍 Шаг 1: Проверка системных требований"
echo "----------------------------------------"

check_command python3
check_command pip3
check_command git

echo ""
echo "🔍 Шаг 2: Проверка файлов проекта"
echo "--------------------------------"

check_file "app.py"
check_file "requirements.txt"
check_file ".env"

# Проверяем размер messages.json
if [ -f "messages.json" ]; then
    SIZE=$(stat -f%z messages.json 2>/dev/null || stat -c%s messages.json 2>/dev/null || echo "0")
    if [ "$SIZE" -gt 100 ]; then
        echo "✅ messages.json ($SIZE байт) - содержит данные"
    else
        echo "⚠️  messages.json ($SIZE байт) - слишком мал или пуст"
        NEED_FETCH_MESSAGES=1
    fi
else
    echo "❌ messages.json не найден"
    NEED_FETCH_MESSAGES=1
fi

echo ""
echo "🔍 Шаг 3: Проверка запущенных процессов"
echo "---------------------------------------"

check_process "app.py"
APP_RUNNING=$?

check_process "app_debug.py"
DEBUG_RUNNING=$?

# Проверяем порт 5000
if netstat -tulpn 2>/dev/null | grep -q ":5000 " || ss -tulpn 2>/dev/null | grep -q ":5000 "; then
    echo "✅ Порт 5000 занят"
    PORT_5000_BUSY=1
else
    echo "❌ Порт 5000 свободен"
    PORT_5000_BUSY=0
fi

echo ""
echo "🔍 Шаг 4: Проверка зависимостей"
echo "-------------------------------"

# Проверяем установленные пакеты
python3 -c "import flask" 2>/dev/null && echo "✅ Flask установлен" || echo "❌ Flask не установлен"
python3 -c "import telethon" 2>/dev/null && echo "✅ Telethon установлен" || echo "❌ Telethon не установлен"
python3 -c "import requests" 2>/dev/null && echo "✅ Requests установлен" || echo "❌ Requests не установлен"

echo ""
echo "🔧 АВТОМАТИЧЕСКИЕ ИСПРАВЛЕНИЯ"
echo "============================"

# Исправление 1: Установка зависимостей
echo ""
echo "🔧 Установка недостающих зависимостей..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --quiet
    echo "✅ Зависимости установлены"
else
    echo "⚠️  requirements.txt не найден, устанавливаем базовые пакеты..."
    pip3 install flask telethon requests beautifulsoup4 --quiet
    echo "✅ Базовые пакеты установлены"
fi

# Исправление 2: Создание .env если его нет
if [ ! -f ".env" ]; then
    echo ""
    echo "🔧 Создание файла .env..."
    cat > .env << 'EOF'
TELEGRAM_API_ID=24031340
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_SESSION=your_session_string_here
EOF
    echo "✅ Файл .env создан"
    echo "⚠️  ВНИМАНИЕ: Отредактируйте .env файл с вашими данными!"
fi

# Исправление 3: Сбор сообщений если messages.json пуст
if [ "$NEED_FETCH_MESSAGES" = "1" ]; then
    echo ""
    echo "🔧 Запуск сбора сообщений Telegram..."
    if [ -f "telegram_fetcher_v2.py" ]; then
        timeout 30 python3 telegram_fetcher_v2.py || echo "Тайм-аут сбора сообщений"
    elif [ -f "telegram_fetcher.py" ]; then
        timeout 30 python3 telegram_fetcher.py || echo "Тайм-аут сбора сообщений"
    fi
    echo "✅ Сбор сообщений завершен (или прерван по тайм-ауту)"
fi

# Исправление 4: Завершение старых процессов и перезапуск
if [ "$APP_RUNNING" = "0" ] || [ "$DEBUG_RUNNING" = "0" ]; then
    echo ""
    echo "🔧 Завершение старых процессов приложения..."
    pkill -f "python.*app.py" 2>/dev/null || true
    pkill -f "python.*app_debug.py" 2>/dev/null || true
    sleep 2
    echo "✅ Старые процессы завершены"
fi

# Исправление 5: Запуск приложения
if [ "$PORT_5000_BUSY" = "0" ]; then
    echo ""
    echo "🚀 Запуск приложения..."
    
    if [ -f "app_debug.py" ]; then
        echo "Запускаем диагностическую версию..."
        nohup python3 app_debug.py > app_startup.log 2>&1 &
        APP_PID=$!
        echo "✅ app_debug.py запущен (PID: $APP_PID)"
    elif [ -f "app.py" ]; then
        echo "Запускаем основную версию..."
        nohup python3 app.py > app_startup.log 2>&1 &
        APP_PID=$!
        echo "✅ app.py запущен (PID: $APP_PID)"
    else
        echo "❌ Не найден ни app.py ни app_debug.py"
    fi
else
    echo ""
    echo "⚠️  Порт 5000 уже занят, приложение возможно уже запущено"
fi

echo ""
echo "⏳ Ожидание запуска приложения..."
sleep 5

echo ""
echo "🔍 ФИНАЛЬНАЯ ПРОВЕРКА"
echo "==================="

# Проверяем что приложение запустилось
if pgrep -f "python.*app" > /dev/null; then
    echo "✅ Процесс Python запущен"
else
    echo "❌ Процесс Python не найден"
fi

# Проверяем порт
if netstat -tulpn 2>/dev/null | grep -q ":5000 " || ss -tulpn 2>/dev/null | grep -q ":5000 "; then
    echo "✅ Порт 5000 занят"
else
    echo "❌ Порт 5000 все еще свободен"
fi

# Проверяем API
echo "🌐 Тестирование API..."
if command -v curl >/dev/null 2>&1; then
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/messages | grep -q "200"; then
        echo "✅ API отвечает (200 OK)"
    else
        echo "❌ API не отвечает или возвращает ошибку"
    fi
else
    echo "⚠️  curl не найден, пропускаем тест API"
fi

# Показываем логи если есть проблемы
if [ -f "app_startup.log" ]; then
    echo ""
    echo "📋 Последние строки лога запуска:"
    tail -10 app_startup.log
fi

echo ""
echo "🎉 ГОТОВО!"
echo "========="
echo ""
echo "Если приложение запустилось успешно, откройте в браузере:"
echo "🌐 http://your-server:5000/"
echo ""
echo "Для мониторинга используйте:"
echo "📊 ./check_logs.sh monitor"
echo ""
echo "Для полной диагностики запустите:"
echo "🔍 ./diagnose.sh"
echo ""

# Показываем что делать дальше
if pgrep -f "python.*app" > /dev/null; then
    echo "✅ Приложение работает!"
    echo ""
    echo "Следующие шаги:"
    echo "1. Откройте сайт в браузере"
    echo "2. Проверьте что карта загружается"
    echo "3. Убедитесь что метки появляются"
    echo ""
    echo "Если меток нет - проверьте настройки Telegram в .env файле"
else
    echo "❌ Приложение не запустилось"
    echo ""
    echo "Попробуйте:"
    echo "1. Проверить .env файл: nano .env"
    echo "2. Запустить диагностику: ./diagnose.sh"
    echo "3. Посмотреть детальные логи: ./check_logs.sh show"
    echo "4. Запустить вручную: python3 app_debug.py"
fi

echo ""
echo "=================================================="
echo "🔧 QUICK FIX завершен"
