# ⚡ Быстрый старт NEPTUN на GMhost

## 🚀 За 15 минут от регистрации до работающего сайта

### 1. Подготовка (2 минуты)
- [ ] Зарегистрируйтесь на gmhost.com.ua
- [ ] Выберите тариф с Python 3.11+
- [ ] Активируйте SSH доступ

### 2. Подключение (3 минуты)
```bash
# Подключитесь по SSH
ssh ваш_логин@ваш_домен.gmhost.com.ua

# Перейдите в директорию сайта
cd public_html
```

### 3. Загрузка проекта (5 минут)
```bash
# Клонируйте репозиторий
git clone https://github.com/vavaika22423232/neptun.git temp
cp -r temp/* . && cp temp/.htaccess . && rm -rf temp

# Установите зависимости
chmod +x install_gmhost.sh && ./install_gmhost.sh
```

### 4. Настройка (3 минуты)
```bash
# Создайте конфигурацию
cp env_example.txt .env
nano .env  # Заполните ваши данные

# Установите права
chmod 755 index.py app.py && chmod 600 .env
```

### 5. Проверка (2 минуты)
- [ ] Откройте ваш_домен.com в браузере
- [ ] Убедитесь, что карта загружается
- [ ] Проверьте отсутствие ошибок

## 🔧 Минимальная конфигурация .env

```bash
TELEGRAM_API_ID=ваш_api_id
TELEGRAM_API_HASH=ваш_api_hash
BOT_TOKEN=ваш_bot_token
MESSAGES_MAX_COUNT=300
MONITOR_PERIOD_MINUTES=40
```

## 🆘 Быстрое решение проблем

### Ошибка 500?
```bash
chmod 755 index.py app.py
```

### Модули не найдены?
```bash
./install_gmhost.sh
```

### Сайт не открывается?
```bash
tail -20 ~/logs/error.log
```

## 📞 Нужна помощь?
- Поддержка GMhost: support@gmhost.com.ua
- Подробная инструкция: GMHOST_SETUP_GUIDE.md
