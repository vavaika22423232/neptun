#!/bin/bash

# 📊 ПРОВЕРКА СТАТУСА СИСТЕМЫ NEPTUN

echo "📊 СТАТУС СИСТЕМЫ NEPTUN"
echo "========================"

# Проверяем процессы
echo "🔄 Проверка процессов:"

if [ -f ".neptun_app.pid" ]; then
    APP_PID=$(cat .neptun_app.pid)
    if kill -0 $APP_PID 2>/dev/null; then
        echo "✅ Flask приложение работает (PID: $APP_PID)"
        APP_RUNNING=true
    else
        echo "❌ Flask приложение не работает"
        APP_RUNNING=false
    fi
else
    echo "❌ Flask приложение не запущен"
    APP_RUNNING=false
fi

if [ -f ".neptun_monitor.pid" ]; then
    MONITOR_PID=$(cat .neptun_monitor.pid)
    if kill -0 $MONITOR_PID 2>/dev/null; then
        echo "✅ Мониторинг активен (PID: $MONITOR_PID)"
    else
        echo "❌ Мониторинг не работает"
    fi
else
    echo "❌ Мониторинг не запущен"
fi

if [ -f ".neptun_manager.pid" ]; then
    MANAGER_PID=$(cat .neptun_manager.pid)
    if kill -0 $MANAGER_PID 2>/dev/null; then
        echo "✅ Автоуправление активно (PID: $MANAGER_PID)"
    else
        echo "❌ Автоуправление не работает"
    fi
else
    echo "❌ Автоуправление не запущено"
fi

echo ""

# Проверяем доступность веб-интерфейса
if $APP_RUNNING; then
    echo "🌐 Проверка веб-интерфейса:"
    curl -s "http://localhost:5000" > /dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Веб-интерфейс доступен: http://localhost:5000"
    else
        echo "❌ Веб-интерфейс недоступен"
    fi
    
    # Проверяем API статистики
    echo ""
    echo "📈 Получение статистики трафика:"
    curl -s "http://localhost:5000/admin/bandwidth_stats?token=admin123" | head -c 200
    echo "..."
fi

echo ""
echo "📊 Размеры файлов:"
du -sh static 2>/dev/null || echo "Папка static не найдена"

echo ""
echo "⚙️  Конфигурация:"
if [ -f "bandwidth_config.json" ]; then
    echo "✅ Конфигурация загружена"
    cat bandwidth_config.json | grep -E "(max_tracks|api_rate)" || true
else
    echo "❌ Файл конфигурации не найден"
fi

echo ""
echo "🛡️  Заблокированные IP:"
if [ -f "blocked_ips.json" ]; then
    BLOCKED_COUNT=$(cat blocked_ips.json | jq length 2>/dev/null || echo "?")
    echo "📋 Всего заблокировано: $BLOCKED_COUNT IP-адресов"
else
    echo "📋 Заблокированных IP нет"
fi

echo ""
echo "📋 РЕКОМЕНДАЦИИ:"
if ! $APP_RUNNING; then
    echo "🚀 Запустите систему: ./start_optimized.sh"
else
    echo "✅ Система работает нормально"
    echo "📊 Мониторинг: http://localhost:5000/admin/bandwidth_stats?token=admin123"
    echo "📈 Подробная проверка: python check_optimization.py"  
fi
