#!/bin/bash

# 🛑 ОСТАНОВКА ОПТИМИЗИРОВАННОЙ СИСТЕМЫ NEPTUN

echo "🛑 Остановка системы Neptun..."
echo "==============================="

# Останавливаем процессы по сохраненным PID
if [ -f ".neptun_app.pid" ]; then
    APP_PID=$(cat .neptun_app.pid)
    if kill -0 $APP_PID 2>/dev/null; then
        echo "🌐 Остановка Flask приложения (PID: $APP_PID)..."
        kill $APP_PID
    fi
    rm .neptun_app.pid
fi

if [ -f ".neptun_monitor.pid" ]; then
    MONITOR_PID=$(cat .neptun_monitor.pid)
    if kill -0 $MONITOR_PID 2>/dev/null; then
        echo "📊 Остановка мониторинга (PID: $MONITOR_PID)..."
        kill $MONITOR_PID
    fi
    rm .neptun_monitor.pid
fi

if [ -f ".neptun_manager.pid" ]; then
    MANAGER_PID=$(cat .neptun_manager.pid)
    if kill -0 $MANAGER_PID 2>/dev/null; then
        echo "🤖 Остановка автоуправления (PID: $MANAGER_PID)..."
        kill $MANAGER_PID
    fi
    rm .neptun_manager.pid
fi

# Дополнительная очистка процессов Python
echo "🧹 Очистка оставшихся процессов..."
pkill -f "python.*app.py" 2>/dev/null
pkill -f "python.*bandwidth_watcher.py" 2>/dev/null

echo ""
echo "✅ Система Neptun остановлена"
echo "📊 Для просмотра итоговой статистики запустите: python check_optimization.py"
