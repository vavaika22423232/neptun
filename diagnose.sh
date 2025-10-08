#!/bin/bash
# Скрипт диагностики приложения на GMhost

echo "🔍 ДИАГНОСТИКА ПРИЛОЖЕНИЯ НА СЕРВЕРЕ"
echo "===================================="

# Функция проверки процессов
check_processes() {
    echo "📊 Проверка запущенных процессов Python:"
    ps aux | grep python | grep -v grep || echo "❌ Процессы Python не найдены"
    echo ""
    
    echo "📊 Проверка процессов app.py:"
    ps aux | grep app.py | grep -v grep || echo "❌ app.py не запущен"
    echo ""
}

# Функция проверки портов
check_ports() {
    echo "🌐 Проверка занятых портов:"
    netstat -tulpn 2>/dev/null | grep :5000 || echo "❌ Порт 5000 не занят"
    echo ""
    
    echo "🌐 Все Python процессы на портах:"
    netstat -tulpn 2>/dev/null | grep python || echo "❌ Python не слушает портов"
    echo ""
}

# Функция проверки логов
check_logs() {
    echo "📝 Поиск логов приложения:"
    
    # Проверяем стандартные места логов
    if [ -f "app.log" ]; then
        echo "✅ Найден app.log:"
        tail -20 app.log
    else
        echo "❌ app.log не найден"
    fi
    echo ""
    
    if [ -f "server.log" ]; then
        echo "✅ Найден server.log:"
        tail -20 server.log
    else
        echo "❌ server.log не найден"
    fi
    echo ""
    
    # Системные логи
    echo "📝 Системные логи (последние записи):"
    journalctl --user -n 10 2>/dev/null || echo "❌ journalctl недоступен"
    echo ""
}

# Функция проверки файлов
check_files() {
    echo "📁 Проверка важных файлов:"
    
    files=("app.py" ".env" "messages.json" "requirements.txt")
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            size=$(ls -lh "$file" | awk '{print $5}')
            echo "✅ $file - найден ($size)"
        else
            echo "❌ $file - НЕ НАЙДЕН"
        fi
    done
    echo ""
}

# Функция проверки API
check_api() {
    echo "🌐 Проверка API endpoints:"
    
    # Проверяем локальный API
    if command -v curl &> /dev/null; then
        echo "📡 Проверка /api/messages:"
        curl -s -f http://localhost:5000/api/messages | head -200 || echo "❌ API недоступен"
        echo ""
        
        echo "📡 Проверка главной страницы:"
        curl -s -f http://localhost:5000/ | head -100 || echo "❌ Сайт недоступен"
        echo ""
    else
        echo "❌ curl не установлен, API проверить нельзя"
    fi
}

# Функция проверки зависимостей
check_dependencies() {
    echo "📦 Проверка Python зависимостей:"
    
    required=("flask" "telethon" "spacy" "requests" "pytz")
    for pkg in "${required[@]}"; do
        python3 -c "import $pkg; print('✅ $pkg - установлен')" 2>/dev/null || echo "❌ $pkg - НЕ УСТАНОВЛЕН"
    done
    echo ""
}

# Функция показа последних изменений messages.json
check_messages_file() {
    echo "📨 Анализ messages.json:"
    
    if [ -f "messages.json" ]; then
        size=$(ls -lh messages.json | awk '{print $5}')
        lines=$(wc -l < messages.json)
        echo "✅ messages.json найден: $size, $lines строк"
        
        # Показываем последние записи
        echo "📄 Последние записи в messages.json:"
        tail -10 messages.json
        echo ""
        
        # Проверяем дату последнего изменения
        mod_time=$(ls -l messages.json | awk '{print $6, $7, $8}')
        echo "🕐 Последнее изменение: $mod_time"
    else
        echo "❌ messages.json не найден"
    fi
    echo ""
}

# Функция создания тестового запуска
create_test_run() {
    echo "🧪 Создание тестового скрипта запуска:"
    
    cat > test_app.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
import logging

# Настройка детального логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

print("🚀 Тестовый запуск приложения с детальным логированием")
print("📝 Логи сохраняются в debug.log")

try:
    print("📦 Импорт модулей...")
    import app
    print("✅ app.py импортирован успешно")
    
    print("🔧 Проверка конфигурации...")
    if hasattr(app, 'API_ID') and app.API_ID:
        print(f"✅ TELEGRAM_API_ID: {app.API_ID}")
    else:
        print("❌ TELEGRAM_API_ID не настроен")
    
    if hasattr(app, 'client') and app.client:
        print("✅ Telegram клиент инициализирован")
    else:
        print("❌ Telegram клиент не инициализирован")
    
    print("🌐 Запуск Flask приложения на localhost:5001...")
    if hasattr(app, 'app'):
        app.app.run(host='127.0.0.1', port=5001, debug=True)
    else:
        print("❌ Flask app не найден")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
EOF
    
    chmod +x test_app.py
    echo "✅ Создан test_app.py для детальной диагностики"
    echo "🏃 Запустите: python3 test_app.py"
    echo ""
}

# Основная функция
main() {
    check_processes
    check_ports
    check_files
    check_messages_file
    check_dependencies
    check_logs
    check_api
    create_test_run
    
    echo "💡 РЕКОМЕНДАЦИИ:"
    echo "1. Если app.py не запущен: python3 app.py"
    echo "2. Для детальной диагностики: python3 test_app.py"
    echo "3. Для просмотра логов: tail -f debug.log"
    echo "4. Проверить .env файл на корректность API ключей"
    echo ""
    echo "🔍 Диагностика завершена!"
}

# Запуск
main "$@"
