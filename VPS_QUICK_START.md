# ⚡ Быстрый запуск NEPTUN на GMhost VPS

## 🎉 VPS готов! Данные:
```
IP: 195.226.192.65
ОС: Ubuntu 20.04  
RAM: 4GB
CPU: 2 vCPU
Диск: 40GB
```

## 🚀 Быстрая установка (3 команды)

### 1. Подключение к VPS
```bash
ssh root@195.226.192.65
# Введите пароль из email
```

### 2. Автоматическая установка (одна команда!)
```bash
curl -sL https://raw.githubusercontent.com/vavaika22423232/neptun/main/install_vps_auto.sh | bash
```

### 3. Настройка и запуск (2 минуты)
```bash
# Настройка конфигурации
nano /var/www/neptun/.env
# Заполните Telegram API данные

# Запуск сайта
/root/neptun_control.sh start
```

## ✅ Готово! 
**Ваш сайт:** http://195.226.192.65

---

## 🎛️ Управление проектом

```bash
# Запуск/остановка
/root/neptun_control.sh start
/root/neptun_control.sh stop
/root/neptun_control.sh restart

# Мониторинг
/root/neptun_control.sh status
/root/neptun_control.sh logs

# Обновление
/root/neptun_control.sh update
```

## ⚙️ Что нужно заполнить в .env

Получите Telegram API на https://my.telegram.org:

```bash
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

MESSAGES_MAX_COUNT=300
MONITOR_PERIOD_MINUTES=40
```

## 🔧 Дополнительные настройки

### SSL сертификат (бесплатный)
```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d ваш_домен.com
```

### Настройка домена
В панели управления доменом добавьте A-запись:
```
@ -> 195.226.192.65
www -> 195.226.192.65
```

### Автоматические обновления
```bash
echo "0 4 * * 0 /root/neptun_control.sh update" | crontab -
```

## 📞 Поддержка
- GitHub Issues: https://github.com/vavaika22423232/neptun/issues
- GMhost: support@gmhost.com.ua

---
**🎯 Время установки: ~10 минут**  
**💰 Стоимость: от 6.99 USD/мес**
