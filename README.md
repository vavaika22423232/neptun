# NEPTUN Alerts (Render deployment)

Сполучає мінімальний Flask backend + Telegram fetch loop для розгортання на Render.

## Швидкий старт локально

1. Створити та активувати venv (опційно)
2. Встановити залежності:
```
pip install -r requirements.txt
```
3. Експортувати змінні середовища (Windows PowerShell приклад):
```
$env:TELEGRAM_API_ID="123456"; $env:TELEGRAM_API_HASH="xxxxxxxx"; $env:TELEGRAM_CHANNELS="UkraineAlarmSignal,war_monitor"; $env:GOOGLE_MAPS_KEY="AIza..."
```
4. Запуск:
```
python app.py
```
5. Відкрити http://localhost:8080

## Render

- Репозиторій підключити до Render
- У Dashboard -> New Web Service -> вибрати repo
- Build Command: `pip install -r requirements.txt`
- Start Command: `python app.py`
- Додати env vars TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_CHANNELS, GOOGLE_MAPS_KEY
	(рекомендовано також TELEGRAM_SESSION – див. нижче)
	Опційно: OPENCAGE_API_KEY для геокодування міст.

## Подальші кроки
- Перенести повний фронтенд (CSS/HTML/JS) з оригінального index.html у raw_index_source.json (css/body/script)
- Повернути складну логіку розбору повідомлень (NER, geocoding) з локальної версії поступово (врахувати ліміти памʼяті плану Render)
- Додати кешування та health метрики

## TELEGRAM_SESSION (авторизація без інтерактиву на Render)

1. Локально встанови залежності (вже є Telethon)
2. Запусти скрипт генерації:
```
python generate_session.py
```
3. Введи API_ID / API_HASH, підтверди код з Telegram (та 2FA пароль якщо є).
4. Отримаєш довгий рядок STRING_SESSION – додай його в Render як env var `TELEGRAM_SESSION`.
5. Перезапусти сервіс (Deploy). Якщо бачиш у логах: `Telegram client NOT authorized` – значить змінна не підхопилась.

Без TELEGRAM_SESSION на Render (free) сесія в файлі може не зберігатися між рестартами.

## OpenCage Геокодування

Додай ключ як `OPENCAGE_API_KEY` в перемінні середовища (Render Dashboard → Environment).
Легка логіка:
- Спочатку шукає прямі координати в тексті `NN.NNN,MM.MMM`.
- Якщо немає — знаходить перший збіг по списку великих міст і геокодує через OpenCage (кеш 30 днів в `opencage_cache.json`).

## Чекліст перед пушем на GitHub

1. Створи приватний репозиторій.
2. Додай `.env.example` (не коміть `.env`).
3. Перевір що `.gitignore` містить секретні файли (`.env`, JSON кеші).
4. Запусти локально `python generate_session.py` → додай `TELEGRAM_SESSION` в Render.
5. (Опційно) Додай `OPENCAGE_API_KEY`.
6. Пуш → Подивись логи Render.

## Мінімальні логи при старті
В логах очікуй:
```
Initializing Telegram client...
 * Serving Flask app
Added track from <channel> #<id>
```
Якщо бачиш `NOT authorized` – перевір `TELEGRAM_SESSION`.

## Ліцензія
MIT (або уточніть).
