# 🚀 Пошаговая инструкция по настройке NEPTUN на GMhost после регистрации

## 1. После регистрации на GMhost.com.ua

### Шаг 1: Выбор тарифного плана
1. Войдите в **Панель управления GMhost**
2. Выберите тариф с поддержкой **Python 3.11+** (рекомендуется "Хостинг+" или выше)
3. Убедитесь, что в тарифе есть:
   - ✅ SSH доступ
   - ✅ Python 3.11+
   - ✅ Возможность установки pip пакетов
   - ✅ Минимум 1GB места на диске
   - ✅ Поддержка CGI/FastCGI

### Шаг 2: Настройка домена
1. В панели управления перейдите в **"Домены"**
2. Добавьте ваш домен или используйте поддомен от GMhost
3. Убедитесь, что домен привязан к вашему аккаунту

### Шаг 3: Получение SSH доступа
1. В панели управления найдите раздел **"SSH доступ"**
2. Скопируйте данные для подключения:
   ```
   Хост: ваш_домен.gmhost.com.ua
   Пользователь: ваш_логин
   Порт: 22 (или другой указанный)
   ```
3. Если SSH отключен - активируйте его в настройках

## 2. Подключение по SSH и первоначальная настройка

### Шаг 4: Подключение к серверу
```bash
# Подключение через SSH (замените на ваши данные)
ssh ваш_логин@ваш_домен.gmhost.com.ua

# Или если указан другой порт
ssh -p 2222 ваш_логин@ваш_домен.gmhost.com.ua
```

### Шаг 5: Изучение структуры каталогов
```bash
# Перейдите в домашнюю директорию
cd ~

# Посмотрите структуру
ls -la

# Обычно структура такая:
# public_html/  - корневая директория сайта
# logs/         - логи
# tmp/          - временные файлы
```

### Шаг 6: Переход в директорию сайта
```bash
# Перейдите в корневую директорию сайта
cd public_html

# Проверьте содержимое
ls -la
```

## 3. Загрузка файлов проекта NEPTUN

### Вариант A: Через Git (рекомендуется)
```bash
# Клонируйте репозиторий
git clone https://github.com/vavaika22423232/neptun.git temp_neptun

# Скопируйте файлы в public_html
cp -r temp_neptun/* .
cp -r temp_neptun/.htaccess .

# Удалите временную папку
rm -rf temp_neptun

# Проверьте, что файлы на месте
ls -la
```

### Вариант B: Через FTP/SFTP
1. Используйте FileZilla или WinSCP
2. Подключитесь к серверу по SFTP:
   ```
   Протокол: SFTP
   Хост: ваш_домен.gmhost.com.ua
   Пользователь: ваш_логин
   Пароль: ваш_пароль
   Порт: 22
   ```
3. Загрузите все файлы из проекта в папку `public_html/`

## 4. Установка Python зависимостей

### Шаг 7: Проверка версии Python
```bash
# Проверьте доступные версии Python
python3 --version
which python3

# Проверьте pip
pip3 --version
```

### Шаг 8: Запуск скрипта установки
```bash
# Сделайте скрипт исполняемым
chmod +x install_gmhost.sh

# Запустите установку
./install_gmhost.sh
```

### Если скрипт не работает - ручная установка:
```bash
# Установите зависимости вручную
pip3 install --user flask==3.0.3
pip3 install --user telethon==1.35.0
pip3 install --user pytz==2024.1
pip3 install --user requests==2.32.3
pip3 install --user spacy==3.8.7

# Установите украинскую модель SpaCy
pip3 install --user https://github.com/explosion/spacy-models/releases/download/uk_core_news_sm-3.8.0/uk_core_news_sm-3.8.0-py3-none-any.whl
```

## 5. Настройка переменных окружения

### Шаг 9: Создание файла .env
```bash
# Скопируйте пример конфигурации
cp env_example.txt .env

# Отредактируйте файл
nano .env
```

### Шаг 10: Заполнение .env файла
```bash
# Telegram API настройки (получите на https://my.telegram.org)
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Настройки производительности
MESSAGES_MAX_COUNT=300
MONITOR_PERIOD_MINUTES=40

# Настройки безопасности
ADMIN_AUTH_SECRET=your_secret_key_here
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=secure_password_123

# Настройки логирования
LOG_LEVEL=INFO
```

### Шаг 11: Установка прав доступа
```bash
# Установите правильные права на файлы
chmod 755 index.py
chmod 755 app.py
chmod 644 .htaccess
chmod 600 .env
chmod 644 *.json
chmod 755 templates/
chmod 644 templates/*.html
```

## 6. Проверка работы сайта

### Шаг 12: Тестирование через браузер
1. Откройте ваш сайт в браузере: `http://ваш_домен.com`
2. Проверьте, что:
   - ✅ Сайт загружается без ошибок
   - ✅ Карта отображается
   - ✅ Нет ошибок 500/404

### Шаг 13: Проверка логов
```bash
# Проверьте логи Apache
tail -f ~/logs/error.log

# Или посмотрите последние ошибки
tail -20 ~/logs/error.log
```

## 7. Возможные проблемы и решения

### Проблема: Ошибка 500 "Internal Server Error"
**Решение:**
```bash
# Проверьте права доступа
chmod 755 index.py
chmod 755 app.py

# Проверьте первую строку в index.py
head -1 index.py
# Должно быть: #!/usr/bin/env python3
```

### Проблема: "Module not found"
**Решение:**
```bash
# Проверьте установленные пакеты
pip3 list --user

# Переустановите пакет
pip3 install --user --force-reinstall flask
```

### Проблема: SpaCy модель не найдена
**Решение:**
```bash
# Попробуйте альтернативную установку
python3 -m spacy download uk_core_news_sm

# Или скачайте вручную
wget https://github.com/explosion/spacy-models/releases/download/uk_core_news_sm-3.8.0/uk_core_news_sm-3.8.0-py3-none-any.whl
pip3 install --user uk_core_news_sm-3.8.0-py3-none-any.whl
```

### Проблема: .htaccess не работает
**Решение:**
```bash
# Проверьте, что mod_rewrite включен
# Обратитесь в поддержку GMhost если нужно

# Альтернативный .htaccess:
cat > .htaccess << 'EOF'
DirectoryIndex index.py
Options +ExecCGI
AddHandler cgi-script .py
EOF
```

## 8. Мониторинг и обслуживание

### Регулярные проверки:
```bash
# Проверка дискового пространства
df -h

# Проверка логов ошибок
tail -50 ~/logs/error.log

# Обновление кода
git pull origin main
```

### Автоматические обновления:
```bash
# Создайте cron задачу для обновления (если нужно)
crontab -e

# Добавьте строку для ежедневного обновления в 3:00
0 3 * * * cd ~/public_html && git pull origin main
```

## 9. Контакты поддержки

- **GMhost техподдержка:** support@gmhost.com.ua
- **Telegram:** @gmhost_support
- **Телефон:** +380 (44) 123-45-67
- **Документация:** https://help.gmhost.com.ua

## 10. Чек-лист готовности

- [ ] Домен настроен и доступен
- [ ] SSH подключение работает
- [ ] Все файлы проекта загружены
- [ ] Python зависимости установлены
- [ ] Файл .env создан и заполнен
- [ ] Права доступа установлены правильно
- [ ] Сайт открывается в браузере
- [ ] Карта загружается и работает
- [ ] Логи не показывают критических ошибок

**🎉 Поздравляем! Ваш проект NEPTUN успешно развернут на GMhost!**
