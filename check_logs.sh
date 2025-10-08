#!/bin/bash
# Быстрая проверка логов приложения

echo "📝 ПРОСМОТР ЛОГОВ ПРИЛОЖЕНИЯ"
echo "============================"

# Функция поиска и показа логов
show_logs() {
    echo "🔍 Поиск файлов логов..."
    
    # Список возможных файлов логов
    log_files=("app_debug.log" "debug.log" "app.log" "server.log" "error.log" "access.log")
    
    found_logs=false
    
    for log_file in "${log_files[@]}"; do
        if [ -f "$log_file" ]; then
            echo ""
            echo "📄 НАЙДЕН: $log_file"
            echo "----------------------------------------"
            echo "📊 Размер: $(ls -lh $log_file | awk '{print $5}')"
            echo "🕐 Изменен: $(ls -l $log_file | awk '{print $6, $7, $8}')"
            echo ""
            echo "📝 Последние 20 строк:"
            tail -20 "$log_file"
            echo "----------------------------------------"
            found_logs=true
        fi
    done
    
    if [ "$found_logs" = false ]; then
        echo "❌ Файлы логов не найдены"
        echo ""
        echo "💡 Возможные причины:"
        echo "1. Приложение не запущено"
        echo "2. Логи пишутся в другое место"
        echo "3. Нет прав на создание файлов"
    fi
}

# Функция проверки процессов
check_running() {
    echo "🔍 Проверка запущенных процессов:"
    
    if ps aux | grep -v grep | grep "python.*app"; then
        echo "✅ Найдены Python процессы с app"
    else
        echo "❌ Python процессы с app не найдены"
    fi
    echo ""
}

# Функция мониторинга в реальном времени
monitor_logs() {
    echo "👁️  МОНИТОРИНГ ЛОГОВ В РЕАЛЬНОМ ВРЕМЕНИ"
    echo "======================================="
    echo "💡 Нажмите Ctrl+C для выхода"
    echo ""
    
    # Ищем активный лог файл
    for log_file in "app_debug.log" "debug.log" "app.log"; do
        if [ -f "$log_file" ]; then
            echo "📱 Отслеживание: $log_file"
            tail -f "$log_file"
            return
        fi
    done
    
    echo "❌ Активные лог файлы не найдены"
    echo "🚀 Запустите приложение с логированием: python3 app_debug.py"
}

# Основная логика
case "${1:-show}" in
    "show")
        check_running
        show_logs
        ;;
    "monitor"|"watch")
        monitor_logs
        ;;
    "help")
        echo "Использование:"
        echo "  $0 show     - показать существующие логи (по умолчанию)"
        echo "  $0 monitor  - мониторинг логов в реальном времени"
        echo "  $0 watch    - то же что monitor"
        ;;
    *)
        echo "❌ Неизвестная команда: $1"
        echo "Используйте: $0 help"
        ;;
esac
