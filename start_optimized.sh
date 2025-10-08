#!/bin/bash

# 🚀 БЫСТРЫЙ ЗАПУСК ОПТИМИЗИРОВАННОГО ПРИЛОЖЕНИЯ
# Автоматический запуск с мониторингом трафика

echo "🚀 Запуск оптимизированной системы Neptun..."
echo "================================================"

# Проверяем виртуальное окружение
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "📦 Активация виртуального окружения..."
    source .venv/bin/activate
fi

# Проверяем зависимости
echo "🔍 Проверка зависимостей..."
python -c "import requests, PIL" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Установка недостающих зависимостей..."
    pip install requests Pillow
fi

# Проверяем оптимизацию файлов
echo "⚡ Проверка оптимизации файлов..."
if [ ! -f "bandwidth_config.json" ]; then
    echo "🔧 Запуск первичной оптимизации..."
    python optimize_bandwidth.py
fi

# Запускаем приложение в фоне
echo "🌐 Запуск Flask приложения..."
python app.py &
APP_PID=$!

# Ждем запуска приложения
echo "⏳ Ожидание запуска сервера..."
sleep 5

# Проверяем что приложение запустилось
curl -s "http://localhost:5000" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Приложение успешно запущено (PID: $APP_PID)"
else
    echo "❌ Ошибка запуска приложения"
    kill $APP_PID 2>/dev/null
    exit 1
fi

# Запускаем мониторинг трафика в фоне
echo "📊 Запуск мониторинга трафика..."
python bandwidth_watcher.py &
MONITOR_PID=$!

echo "📈 Мониторинг запущен (PID: $MONITOR_PID)"

# Запускаем автоматическое управление (каждые 30 минут)
echo "🛡️  Настройка автоматического управления..."
(
    while true; do
        sleep 1800  # 30 минут
        echo "🔧 Автоматическая оптимизация $(date)"
        python traffic_manager.py
    done
) &
MANAGER_PID=$!

echo "🤖 Автоуправление настроено (PID: $MANAGER_PID)"

# Создаем файл с PID процессов для остановки
echo "$APP_PID" > .neptun_app.pid
echo "$MONITOR_PID" > .neptun_monitor.pid  
echo "$MANAGER_PID" > .neptun_manager.pid

echo ""
echo "🎉 СИСТЕМА УСПЕШНО ЗАПУЩЕНА!"
echo "================================================"
echo "🌐 Приложение: http://localhost:5000"
echo "📊 Статистика: http://localhost:5000/admin/bandwidth_stats?token=admin123"
echo ""
echo "🔄 Процессы:"
echo "   - Flask app (PID: $APP_PID)"
echo "   - Мониторинг (PID: $MONITOR_PID)"  
echo "   - Автоуправление (PID: $MANAGER_PID)"
echo ""
echo "🛑 Для остановки запустите: ./stop_neptun.sh"
echo "📊 Для проверки статуса: ./status_neptun.sh"
echo ""
echo "💡 Прогноз экономии: с 1000GB/месяц до ~280GB/месяц"
echo "💰 Ожидаемая экономия: ~$108/месяц"

# Показываем текущую статистику
echo ""
echo "📈 Начальная статистика:"
python check_optimization.py | grep -A10 "💡 ПРОГНОЗ ЭКОНОМИИ"

echo ""
echo "✨ Система готова к работе!"
echo "   Мониторинг активен, автоматическая оптимизация настроена."
