#!/bin/bash
# Скрипт автоматического развертывания с GitHub на GMhost

echo "🚀 АВТОМАТИЧЕСКОЕ РАЗВЕРТЫВАНИЕ С GITHUB"
echo "======================================="

# Переменные
REPO_URL="https://github.com/vavaika22423232/neptun.git"
PROJECT_DIR="neptun"
BRANCH="main"

# Функция для клонирования или обновления репозитория
deploy_from_github() {
    echo "📦 Получение кода с GitHub..."
    
    if [ -d "$PROJECT_DIR" ]; then
        echo "📁 Папка $PROJECT_DIR уже существует, обновляем..."
        cd "$PROJECT_DIR"
        git pull origin "$BRANCH"
        cd ..
    else
        echo "📥 Клонирование репозитория..."
        git clone "$REPO_URL" "$PROJECT_DIR"
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ Код успешно получен с GitHub"
    else
        echo "❌ Ошибка при получении кода с GitHub"
        exit 1
    fi
}

# Функция установки зависимостей
install_dependencies() {
    echo "📦 Установка зависимостей Python..."
    cd "$PROJECT_DIR"
    
    if [ -f "requirements.txt" ]; then
        pip3 install --user -r requirements.txt
        echo "✅ Зависимости установлены"
    else
        echo "⚠️  Файл requirements.txt не найден"
    fi
}

# Функция настройки окружения
setup_environment() {
    echo "🔧 Настройка окружения..."
    cd "$PROJECT_DIR"
    
    # Проверяем наличие .env файла
    if [ ! -f ".env" ]; then
        echo "⚠️  ВНИМАНИЕ: Файл .env не найден!"
        echo "📝 Создайте файл .env с настройками:"
        echo ""
        echo "TELEGRAM_API_ID=ваш_api_id"
        echo "TELEGRAM_API_HASH=ваш_api_hash"
        echo "TELEGRAM_SESSION=ваш_session_string"
        echo "GOOGLE_MAPS_KEY=ваш_google_key"
        echo "OPENCAGE_API_KEY=ваш_opencage_key"
        echo "PORT=5000"
        echo "HOST=0.0.0.0"
        echo ""
        echo "❗ Без .env файла приложение не запустится!"
        return 1
    else
        echo "✅ Файл .env найден"
    fi
    
    # Делаем скрипты исполняемыми
    chmod +x *.sh 2>/dev/null || true
    chmod +x *.py 2>/dev/null || true
    
    echo "✅ Окружение настроено"
}

# Функция запуска приложения
start_application() {
    echo "🚀 Запуск приложения..."
    cd "$PROJECT_DIR"
    
    echo "🌐 Приложение будет доступно на http://$(hostname -I | awk '{print $1}'):5000"
    echo "⏹️  Для остановки нажмите Ctrl+C"
    echo ""
    
    # Запускаем приложение
    python3 app.py
}

# Основная логика
main() {
    echo "🎯 Начинаем автоматическое развертывание..."
    
    # Проверяем наличие git
    if ! command -v git &> /dev/null; then
        echo "❌ Git не установлен. Установите git: apt install git"
        exit 1
    fi
    
    # Проверяем наличие python3
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 не установлен. Установите python3: apt install python3 python3-pip"
        exit 1
    fi
    
    deploy_from_github
    install_dependencies
    setup_environment
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Развертывание завершено успешно!"
        echo ""
        read -p "🚀 Запустить приложение сейчас? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            start_application
        else
            echo "📝 Для запуска позже используйте:"
            echo "cd $PROJECT_DIR && python3 app.py"
        fi
    else
        echo "❌ Ошибка при развертывании"
        exit 1
    fi
}

# Запуск основной функции
main "$@"
