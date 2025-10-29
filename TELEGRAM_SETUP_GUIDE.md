# 🤖 Telegram Bot Integration Guide

## Що це дає?

Інтеграція з офіційними DTEK Telegram ботами дозволяє отримувати **реальні графіки відключень** для всіх регіонів України:
- 🏙️ Київ - `@DTEKKyivBot`
- 🌆 Дніпро - `@DTEKDniproBot`
- 🌊 Одеса - `@DTEKOdesaBot`

## 📝 Покрокова інструкція

### Крок 1: Отримання Telegram API credentials

1. Відкрийте https://my.telegram.org/apps
2. Увійдіть зі своїм номером телефону Telegram
3. Натисніть **"API development tools"**
4. Заповніть форму створення додатку:
   - **App title**: `DTEK Schedule Bot`
   - **Short name**: `dtek_bot`
   - **URL**: `https://your-site.onrender.com` (або залиште порожнім)
   - **Platform**: `Other`
5. Натисніть **"Create application"**
6. Скопіюйте:
   - **api_id** (наприклад: `12345678`)
   - **api_hash** (наприклад: `abcdef1234567890abcdef1234567890`)

### Крок 2: Локальна авторизація

```bash
# Встановіть змінні середовища
export TELEGRAM_API_ID='ваш_api_id'
export TELEGRAM_API_HASH='ваш_api_hash'

# Запустіть скрипт авторизації
python3 setup_telegram.py
```

**Що відбудеться:**
1. Вас попросять ввести номер телефону Telegram
2. Telegram надішле код підтвердження
3. Введіть код
4. Створиться файл `dtek_session.session` (це ваша сесія)

### Крок 3: Тестування

```bash
# Тест з'єднання
python3 telegram_dtek_client.py
```

Якщо все працює, побачите:
```
✅ З'єднання встановлено!
📍 Тестуємо: Київ, Хрещатик, 1
✅ Черга: 1.1
📅 Графік: 12 записів
```

### Крок 4: Інтеграція в проект

Інтеграція вже готова! Система автоматично використовує Telegram Bot якщо:
1. Встановлені `TELEGRAM_API_ID` та `TELEGRAM_API_HASH`
2. Існує файл сесії `dtek_session.session`
3. YASNO API не підтримує регіон

**Каскадна система:**
```
1. YASNO API (Київ, Дніпро) → швидко ✅
2. Telegram Bot (всі інші міста) → якщо є credentials 🤖
3. Fallback schedule → якщо все інше не працює 📊
```

### Крок 5: Deployment на Render

#### A. Додати змінні середовища:

1. Відкрийте Dashboard → Your Service → Environment
2. Додайте:
   ```
   TELEGRAM_API_ID = ваш_api_id
   TELEGRAM_API_HASH = ваш_api_hash
   ```
3. Збережіть

#### B. Завантажити файл сесії:

**Варіант 1: Через SSH (якщо є)**
```bash
# На локальній машині
scp dtek_session.session render:/app/

# Або через git (якщо сесія не в .gitignore)
git add dtek_session.session -f
git commit -m "Add Telegram session"
git push
```

**Варіант 2: Створити сесію на сервері**
```bash
# Підключіться до Render Shell
python3 setup_telegram.py
# Пройдіть авторизацію
```

**Варіант 3: Використати змінну середовища (складніше)**
```bash
# Конвертувати сесію в base64
cat dtek_session.session | base64 > session_base64.txt

# Додати в Render Environment:
TELEGRAM_SESSION_BASE64 = <вміст session_base64.txt>

# Додати в app.py декодування:
import base64
if os.getenv('TELEGRAM_SESSION_BASE64'):
    with open('dtek_session.session', 'wb') as f:
        f.write(base64.b64decode(os.getenv('TELEGRAM_SESSION_BASE64')))
```

## 🔧 Налаштування

### Кешування

За замовчуванням:
- **YASNO API**: 1 година
- **Telegram Bot**: 2 години (бо повільніше)

Змінити в `blackout_api.py`:
```python
_telegram_cache = {
    'ttl': 7200  # Змініть на інше значення (секунди)
}
```

### Rate Limits

Telegram Bot API має обмеження:
- ~30 запитів на хвилину
- ~10,000 запитів на день

**Рекомендації:**
- Використовуйте довший TTL кешу (2-4 години)
- Не робіть запити для кожного користувача окремо
- Періодично оновлюйте популярні адреси через cron

## 📊 Моніторинг

### Логи

```python
# В app.py додайте
logger.info(f"📊 Cache stats: {len(_telegram_cache['data'])} entries")
logger.info(f"🤖 Telegram enabled: {_telegram_cache['enabled']}")
```

### Статистика використання

```python
# blackout_api.py
telegram_stats = {
    'requests': 0,
    'cache_hits': 0,
    'errors': 0
}

def get_telegram_stats():
    return telegram_stats
```

## ⚠️ Важливі нотатки

### Безпека

1. **Ніколи не комітьте в git:**
   - `dtek_session.session` ✅ (вже в .gitignore)
   - `TELEGRAM_API_HASH` ✅ (тільки в Environment Variables)

2. **Файл сесії:**
   - Це ваш доступ до Telegram
   - Не діліться ним
   - Якщо втратили - створіть новий через `setup_telegram.py`

### Обмеження

1. **Telegram Bot може:**
   - Не відповісти вчасно (timeout)
   - Змінити формат відповіді
   - Бути оффлайн

2. **Тому завжди є fallback:**
   - Система не впаде якщо бот не працює
   - Покаже типовий графік

### Оновлення сесії

Сесія живе ~1 рік. Якщо перестала працювати:

```bash
# Видалити стару
rm dtek_session.session

# Створити нову
python3 setup_telegram.py
```

## 🚀 Готово!

Тепер ваш проект:
1. ✅ Використовує YASNO API (Київ, Дніпро)
2. ✅ Використовує Telegram Bot (інші міста)
3. ✅ Має fallback графіки
4. ✅ Кешує результати
5. ✅ Автоматично вибирає найкраще джерело

## 🆘 Troubleshooting

### "telethon not installed"
```bash
pip install telethon
```

### "TELEGRAM_API_ID not found"
```bash
export TELEGRAM_API_ID='your_id'
export TELEGRAM_API_HASH='your_hash'
```

### "Session file not found"
```bash
python3 setup_telegram.py
```

### "Bot doesn't respond"
- Перевірте чи бот існує в Telegram
- Спробуйте написати боту вручну
- Можливо бот тимчасово недоступний

### "Rate limit exceeded"
- Збільшіть TTL кешу
- Зменшіть кількість запитів
- Зачекайте 10-15 хвилин

## 📚 Додаткові ресурси

- [Telethon Documentation](https://docs.telethon.dev/)
- [Telegram API](https://core.telegram.org/api)
- [DTEK Bots](https://t.me/DTEKKyivBot)
