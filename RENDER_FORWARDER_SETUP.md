# 🚀 Channel Forwarder на Render - Інструкція

## Швидкий старт (3 кроки)

### Крок 1: Локально - Генерація STRING_SESSION

```bash
cd /Users/vladimirmalik/Desktop/render2
python3 generate_string_session.py
```

**Що станеться:**
1. Відкриється авторизація Telegram
2. Введете код з SMS на +263781966038
3. Можливо 2FA пароль
4. Отримаєте довгий STRING_SESSION

**Приклад виводу:**
```
✅ Успішно авторизовано!

╔════════════════════════════════════════════════════╗
║  📋 Ваш STRING_SESSION (скопіюйте):               ║
╚════════════════════════════════════════════════════╝

1AgAOMTQ5LjE1NC4xNjcuNTEBu+... (дуже довгий рядок)
```

**👉 СКОПІЮЙТЕ цей рядок!**

---

### Крок 2: Render Dashboard - Додати Environment Variables

1. Відкрийте https://dashboard.render.com
2. Виберіть ваш сервіс (neptun)
3. Перейдіть в **Environment** → **Environment Variables**
4. Додайте наступні змінні:

#### Обов'язкові:

```
TELEGRAM_SESSION = [вставте ваш STRING_SESSION]
TELEGRAM_API_ID = 24031340
TELEGRAM_API_HASH = 2daaa58652e315ce52adb1090313d36a
```

#### Опціональні (якщо хочете змінити):

```
SOURCE_CHANNELS = UkraineAlarmSignal,kpszsu,war_monitor,napramok,raketa_trevoga,ukrainsiypposhnik
TARGET_CHANNEL = mapstransler
```

5. **Save Changes**

---

### Крок 3: Запуск на Render

#### Варіант A: Окремий Worker (рекомендовано)

1. В Render Dashboard → **Background Workers**
2. Натисніть **Add Background Worker**
3. Налаштування:
   ```
   Name: channel-forwarder
   Start Command: python channel_forwarder_render.py
   ```
4. **Create Background Worker**

#### Варіант B: В одному процесі з Flask

Відредагуйте `Procfile`:
```
web: python app.py & python channel_forwarder_render.py
```

**Примітка:** Не рекомендується, краще окремий worker.

---

## 🔧 Налаштування render.yaml

Якщо використовуєте `render.yaml`, додайте worker:

```yaml
services:
  # Основний Web сервіс
  - type: web
    name: neptun
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python app.py
    envVars:
      - key: TELEGRAM_API_ID
        value: 24031340
      - key: TELEGRAM_API_HASH
        value: 2daaa58652e315ce52adb1090313d36a
      - key: TELEGRAM_SESSION
        sync: false  # Додайте вручну в Dashboard
      - key: SOURCE_CHANNELS
        value: UkraineAlarmSignal,kpszsu,war_monitor,napramok,raketa_trevoga,ukrainsiypposhnik
      - key: TARGET_CHANNEL
        value: mapstransler
  
  # Channel Forwarder Worker
  - type: worker
    name: channel-forwarder
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python channel_forwarder_render.py
    envVars:
      - key: TELEGRAM_API_ID
        value: 24031340
      - key: TELEGRAM_API_HASH
        value: 2daaa58652e315ce52adb1090313d36a
      - key: TELEGRAM_SESSION
        sync: false
      - key: SOURCE_CHANNELS
        value: UkraineAlarmSignal,kpszsu,war_monitor,napramok,raketa_trevoga,ukrainsiypposhnik
      - key: TARGET_CHANNEL
        value: mapstransler
```

---

## 📊 Перевірка роботи

### Логи на Render

1. Dashboard → Ваш сервіс → **Logs**
2. Шукайте:

```
🚀 Запуск Channel Forwarder Bot на Render...
✅ Авторизовано як: User (+263781966038)
✅ Цільовий канал: Maps Transler
✅ Вихідний канал: Ukraine Alarm Signal (@UkraineAlarmSignal)
...
🎯 Бот запущено на Render! Очікую нові повідомлення...

📨 Нове повідомлення з @UkraineAlarmSignal
✅ Переслано до @mapstransler (всього: 1)
```

### Якщо бачите помилки:

#### "TELEGRAM_SESSION не встановлено"
- Додайте `TELEGRAM_SESSION` в Environment Variables
- Перезапустіть сервіс

#### "Сесія недійсна"
- Перегенеруйте STRING_SESSION локально
- Оновіть в Environment Variables

#### "Не вдалося знайти канал"
- Перевірте що підписані на всі канали
- Перевірте що ви адмін @mapstransler

---

## 🔐 Безпека

### ⚠️ ВАЖЛИВО:

1. **НЕ коммітьте** STRING_SESSION в Git!
2. ✅ `.gitignore` вже налаштований
3. ✅ Додавайте SESSION тільки через Render Dashboard
4. ✅ Зберігайте резервну копію SESSION в безпечному місці

### Резервна копія SESSION:

```bash
# Зберегти у файл (НЕ коммітити!)
echo "TELEGRAM_SESSION=ваш_session" > .env.session.backup

# Додати в .gitignore
echo ".env.session.backup" >> .gitignore
```

---

## 🛠️ Troubleshooting

### Бот не пересилає повідомлення

1. **Перевірте логи** - чи є повідомлення `📨 Нове повідомлення`?
2. **Перевірте канали** - чи підписані на всі вихідні?
3. **Перевірте права** - чи ви адмін @mapstransler?
4. **Перезапустіть** worker на Render

### "Session expired" після рестарту Render

**Причина:** Нормально! StringSession зберігається в env var.

**Якщо дійсно expired:**
1. Перегенеруйте SESSION локально
2. Оновіть `TELEGRAM_SESSION` в Render
3. Перезапустіть

### Worker не запускається

1. Перевірте Build Logs
2. Перевірте що `telethon` встановлено
3. Перевірте Start Command: `python channel_forwarder_render.py`

---

## 📈 Моніторинг

### Metrics на Render:

- CPU/Memory usage
- Restart count
- Uptime

### Логи:

```bash
# Дивитися логи в реальному часі
Render Dashboard → Logs → Auto-scroll
```

### Alerts:

Налаштуйте в Render:
- Email при падінні worker
- Slack/Discord notifications

---

## 💰 Вартість

### Free Plan:
- ✅ Web сервіс (750 годин/місяць)
- ❌ Worker не включено безкоштовно

### Starter Plan ($7/міс):
- ✅ Web сервіс
- ✅ 1 Background Worker
- ✅ Достатньо для forwarder бота

### Альтернатива (безкоштовно):

Запустіть локально або на своєму сервері:
```bash
python3 channel_forwarder.py  # Локальна версія
```

---

## 🎯 Фінальний чеклист

Перед деплоєм:

- [ ] Згенеровано STRING_SESSION локально
- [ ] Додано `TELEGRAM_SESSION` в Render env vars
- [ ] Додано `TELEGRAM_API_ID` та `TELEGRAM_API_HASH`
- [ ] Створено Background Worker в Render
- [ ] Перевірено що підписані на всі вихідні канали
- [ ] Перевірено що є адміном @mapstransler
- [ ] Протестовано локально (опціонально)
- [ ] Перевірено логи на Render

---

## 🚀 Готово!

Після налаштування бот буде:
- ✅ Працювати 24/7 на Render
- ✅ Автоматично пересилати повідомлення
- ✅ Рестартувати при падінні
- ✅ Логувати всі події

**Успіхів! 🎉**

---

## 📞 Підтримка

Проблеми? Перевірте:
1. Логи на Render
2. Environment Variables
3. Статус worker
4. Підключення до інтернету (Render side)

---

*Версія 1.0 для Render - 5 грудня 2024*
