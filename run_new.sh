#!/bin/bash
# run_new.sh - Запуск нової модульної архітектури

set -e

echo "🚀 Neptun 2.0 - Модульна архітектура"
echo "======================================"

# Перевірка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не знайдено"
    exit 1
fi

# Перевірка залежностей
echo "📦 Перевірка залежностей..."
python3 -c "import flask" 2>/dev/null || {
    echo "❌ Flask не встановлено. Виконайте: pip install flask"
    exit 1
}

# Запуск тестів
echo ""
echo "🧪 Запуск тестів..."
python3 -m pytest tests/ -v --tb=short -q 2>&1 | tail -20

# Перевірка результату тестів
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo ""
    echo "❌ Тести не пройшли! Виправте помилки перед запуском."
    exit 1
fi

echo ""
echo "✅ Всі тести пройшли!"
echo ""

# Вибір режиму
MODE=${1:-"dev"}

case $MODE in
    "dev")
        echo "🔧 Запуск в режимі розробки..."
        export FLASK_ENV=development
        export FLASK_DEBUG=1
        python3 app_new.py
        ;;
    "prod")
        echo "🏭 Запуск в продакшн режимі..."
        export FLASK_ENV=production
        gunicorn -w 4 -b 0.0.0.0:5000 app_new:app
        ;;
    "test")
        echo "🧪 Тільки тести (вже виконано)"
        ;;
    *)
        echo "Використання: ./run_new.sh [dev|prod|test]"
        exit 1
        ;;
esac
