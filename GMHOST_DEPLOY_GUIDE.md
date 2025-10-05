# 🚀 Инструкция по переносу NEPTUN на GMhost

## Подготовка

1. **Купите хостинг на GMhost.com.ua**
   - Выберите тариф с поддержкой Python 3.11+
   - Убедитесь, что есть SSH доступ

2. **Подготовьте переменные окружения**
   - Telegram API credentials
   - Bot tokens
   - Другие секретные ключи

## Шаги установки

### Шаг 1: Загрузка файлов
```bash
# Через FTP/SFTP загрузите все файлы проекта в корневую директорию сайта
# Структура должна быть:
/public_html/
├── index.py          # CGI entry point
├── app.py            # Основное приложение
├── .htaccess         # Конфигурация Apache
├── requirements.txt  # Зависимости
├── templates/        # HTML шаблоны
├── static/          # Статические файлы (если есть)
└── install_gmhost.sh # Скрипт установки
```

### Шаг 2: Установка зависимостей
```bash
# Подключитесь по SSH к серверу
ssh your_username@your_domain.gmhost.com.ua

# Перейдите в директорию сайта
cd public_html

# Запустите скрипт установки
chmod +x install_gmhost.sh
./install_gmhost.sh
```

### Шаг 3: Настройка переменных окружения
```bash
# Создайте файл .env в корневой директории
nano .env

# Добавьте ваши переменные:
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
MESSAGES_MAX_COUNT=300
MONITOR_PERIOD_MINUTES=40
```

### Шаг 4: Настройка прав доступа
```bash
# Установите правильные права
chmod 755 index.py
chmod 755 app.py
chmod 644 .htaccess
chmod 600 .env
```

### Шаг 5: Тестирование
- Откройте ваш сайт в браузере
- Проверьте, что карта загружается
- Убедитесь, что все функции работают

## Возможные проблемы и решения

### 1. Ошибка импорта модулей
```bash
# Если модули не найдены, установите их в пользовательскую директорию:
pip3 install --user package_name
```

### 2. Проблемы с SpaCy
```bash
# Если украинская модель не устанавливается:
python3 -m spacy download uk_core_news_sm
```

### 3. Ошибки прав доступа
```bash
# Проверьте владельца файлов:
chown -R your_username:your_username /path/to/public_html/
```

### 4. Проблемы с .htaccess
- Убедитесь, что GMhost поддерживает mod_rewrite
- Проверьте синтаксис .htaccess файла

## Мониторинг

### Логи ошибок
```bash
# Проверьте логи Apache
tail -f /path/to/apache/error.log

# Логи Python приложения
tail -f logs/app.log
```

### Производительность
- Мониторьте использование CPU и памяти
- При необходимости увеличьте лимиты в настройках хостинга

## Обновления

### Обновление кода
```bash
# Загрузите новые файлы через FTP
# Или используйте git:
git pull origin main
```

### Обновление зависимостей
```bash
# Запустите скрипт установки заново
./install_gmhost.sh
```

## Контакты поддержки
- GMhost техподдержка: support@gmhost.com.ua
- Документация GMhost: https://gmhost.com.ua/help/
