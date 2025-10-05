#!/bin/bash

echo "🚀 Начинается автоматическая установка NEPTUN на VPS..."
echo "📍 IP адрес: $(curl -s ifconfig.me)"
echo "💾 Система: $(lsb_release -d -s)"

# Обновление системы
echo "📦 Обновление системы Ubuntu..."
apt update && apt upgrade -y

# Установка Python 3.11
echo "🐍 Установка Python 3.11..."
apt install software-properties-common -y
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install python3.11 python3.11-pip python3.11-venv python3.11-dev -y

# Установка веб-сервера и утилит
echo "🌐 Установка Nginx, Supervisor и утилит..."
apt install nginx supervisor git nano htop curl wget unzip -y

# Проверка версий
echo "✅ Установленные версии:"
python3.11 --version
nginx -v
echo "Supervisor: $(supervisord -v)"

# Клонирование проекта
echo "📥 Скачивание проекта NEPTUN с GitHub..."
cd /var/www
rm -rf neptun 2>/dev/null
git clone https://github.com/vavaika22423232/neptun.git
cd neptun

# Виртуальное окружение
echo "📦 Создание виртуального окружения Python..."
python3.11 -m venv venv
source venv/bin/activate

# Установка зависимостей
echo "📦 Установка Python зависимостей..."
pip install --upgrade pip
pip install flask==3.0.3
pip install telethon==1.35.0
pip install pytz==2024.1
pip install requests==2.32.3
pip install spacy==3.8.7

# Установка украинской модели SpaCy
echo "🇺🇦 Установка украинской модели SpaCy..."
pip install https://github.com/explosion/spacy-models/releases/download/uk_core_news_sm-3.8.0/uk_core_news_sm-3.8.0-py3-none-any.whl

# Проверка установки SpaCy
echo "🔍 Проверка SpaCy модели..."
python3.11 -c "import spacy; nlp = spacy.load('uk_core_news_sm'); print('✅ SpaCy украинская модель работает!')" || echo "❌ Проблема с SpaCy моделью"

# Права доступа
echo "🔐 Настройка прав доступа..."
chown -R www-data:www-data /var/www/neptun
chmod +x /var/www/neptun/app.py

# Конфигурация Nginx
echo "⚙️ Настройка Nginx веб-сервера..."
cat > /etc/nginx/sites-available/neptun << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Основное приложение
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Статические файлы
    location /static/ {
        alias /var/www/neptun/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Логи
    access_log /var/log/nginx/neptun_access.log;
    error_log /var/log/nginx/neptun_error.log;
}
EOF

# Активация сайта
ln -s /etc/nginx/sites-available/neptun /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Проверка конфигурации Nginx
nginx -t || echo "❌ Ошибка в конфигурации Nginx"

# Конфигурация Supervisor
echo "⚙️ Настройка автозапуска через Supervisor..."
cat > /etc/supervisor/conf.d/neptun.conf << 'EOF'
[program:neptun]
command=/var/www/neptun/venv/bin/python /var/www/neptun/app.py
directory=/var/www/neptun
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/neptun.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
environment=PATH="/var/www/neptun/venv/bin"
EOF

# Создание скрипта запуска
echo "🔧 Создание скрипта управления..."
cat > /root/neptun_control.sh << 'EOF'
#!/bin/bash

case "$1" in
    start)
        echo "🚀 Запуск NEPTUN..."
        systemctl restart nginx
        systemctl enable nginx
        supervisorctl reread
        supervisorctl update
        supervisorctl start neptun
        systemctl enable supervisor
        echo "✅ NEPTUN запущен!"
        ;;
    stop)
        echo "⏹️ Остановка NEPTUN..."
        supervisorctl stop neptun
        systemctl stop nginx
        echo "✅ NEPTUN остановлен"
        ;;
    restart)
        echo "🔄 Перезапуск NEPTUN..."
        supervisorctl restart neptun
        systemctl restart nginx
        echo "✅ NEPTUN перезапущен"
        ;;
    status)
        echo "📊 Статус NEPTUN:"
        systemctl status nginx --no-pager -l
        supervisorctl status neptun
        echo "🌐 Сайт доступен на: http://$(curl -s ifconfig.me)"
        ;;
    logs)
        echo "📜 Логи NEPTUN:"
        tail -50 /var/log/neptun.log
        ;;
    update)
        echo "🔄 Обновление NEPTUN..."
        cd /var/www/neptun
        git pull origin main
        source venv/bin/activate
        pip install -r requirements.txt --upgrade 2>/dev/null || echo "requirements.txt не найден"
        supervisorctl restart neptun
        echo "✅ NEPTUN обновлен"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|update}"
        exit 1
        ;;
esac
EOF

chmod +x /root/neptun_control.sh

# Копирование примера конфигурации
echo "📝 Создание примера конфигурации..."
cp env_example.txt .env

# Создание файла с информацией
cat > /root/neptun_info.txt << EOF
🎉 NEPTUN установлен на VPS!

📍 IP адрес: $(curl -s ifconfig.me)
🌐 Адрес сайта: http://$(curl -s ifconfig.me)
📁 Директория проекта: /var/www/neptun
📜 Логи приложения: /var/log/neptun.log
📜 Логи Nginx: /var/log/nginx/neptun_*.log

🎛️ Управление:
/root/neptun_control.sh start    - Запуск
/root/neptun_control.sh stop     - Остановка  
/root/neptun_control.sh restart  - Перезапуск
/root/neptun_control.sh status   - Статус
/root/neptun_control.sh logs     - Просмотр логов
/root/neptun_control.sh update   - Обновление

⚙️ Настройка:
1. Отредактируйте: nano /var/www/neptun/.env
2. Заполните Telegram API данные
3. Запустите: /root/neptun_control.sh start

📞 Поддержка:
- Telegram API: https://my.telegram.org
- GitHub: https://github.com/vavaika22423232/neptun
- GMhost: support@gmhost.com.ua
EOF

echo ""
echo "🎉 Установка NEPTUN завершена!"
echo ""
cat /root/neptun_info.txt
echo ""
echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
echo "1. Настройте .env: nano /var/www/neptun/.env"
echo "2. Запустите проект: /root/neptun_control.sh start"
echo ""
