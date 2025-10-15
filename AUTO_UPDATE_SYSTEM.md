# Система автоматичного оновлення графіків відключень ⚡

## Огляд

Додаток **NEPTUN** автоматично оновлює графіки відключень з офіційних джерел кожну годину:
- 🔷 **ДТЕК** (Київ, Одеса, Дніпро, Донецьк)
- 🔶 **Укренерго** (загальнодержавні дані)

## Архітектура

### 1. Schedule Updater (`schedule_updater.py`)
Основний модуль для оновлення графіків:

```python
class ScheduleUpdater:
    - update_all_schedules()        # Оновлення з усіх джерел
    - _update_dtek_schedules()      # ДТЕК регіони
    - _update_ukrenergo_schedules() # Укренерго API
    - get_schedule_for_address()    # Пошук для адреси
```

### 2. Background Scheduler (APScheduler)
Запускається автоматично при старті Flask:

```python
# Ініціалізація в app.py
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(
    func=schedule_updater.update_all_schedules,
    trigger='interval',
    hours=1,  # Кожну годину
    replace_existing=True
)
scheduler.start()
```

### 3. Кешування даних
- ✅ Зберігання останніх графіків у пам'яті
- ✅ Перевірка актуальності (max 1 година)
- ✅ Автоматичне оновлення при застарінні

## API Endpoints

### `/api/live_schedules`
Отримання поточних графіків з кешу:

```json
{
  "success": true,
  "schedules": {
    "dtek": {
      "kyiv": { "1.1": [...], "1.2": [...], ... },
      "odesa": { "2.1": [...], "2.2": [...], ... }
    },
    "ukrenergo": { ... },
    "last_update": "2025-10-15T14:30:00"
  },
  "next_update": "через годину"
}
```

### `/api/schedule_status`
Статус системи автооновлення:

```json
{
  "available": true,
  "last_update": "2025-10-15T14:30:00",
  "cache_valid": true,
  "next_update": "через годину",
  "scheduler_running": true
}
```

### `/api/get_schedule` (оновлено)
Пошук графіку для адреси (пріоритет - live дані):

```
GET /api/get_schedule?city=Одеса&street=Спортивна&building=3/2

Response:
{
  "found": true,
  "address": "с. Лиманка, вул. Спортивна 3/2",
  "city": "с. Лиманка",
  "group": "2.1",
  "provider": "ДТЕК Одеські електромережі",
  "schedule": [...],
  "last_update": "2025-10-15T14:30:00",
  "source": "live_dtek"
}
```

## Джерела даних

### ДТЕК (Web Scraping)
```python
dtek_regions = {
    'kyiv': 'https://www.dtek-krem.com.ua',
    'odesa': 'https://www.dtek-oem.com.ua',
    'dnipro': 'https://www.dtek-dnem.com.ua',
    'donetsk': 'https://www.dtek-donec.com.ua'
}
```

**Метод**: BeautifulSoup4 парсинг HTML сторінок з графіками

### Укренерго (REST API)
```python
ukrenergo_api = 'https://www.ukrenergo.energy/api'
endpoints = ['/outages', '/schedule', '/power-system-status']
```

**Метод**: REST API запити з JSON відповідями

## Черги та підгрупи

Система підтримує **6 підгруп черг**:

| Черга | Активне відключення | Можливе відключення |
|-------|---------------------|---------------------|
| **1.1** | 12:00 - 16:00 | 04:00-08:00, 20:00-24:00 |
| **1.2** | 08:00 - 12:00 | 00:00-04:00, 16:00-20:00 |
| **2.1** | 16:00 - 20:00 | 08:00-12:00, 20:00-24:00 |
| **2.2** | 20:00 - 24:00 | 00:00-04:00, 12:00-16:00 |
| **3.1** | 00:00 - 04:00 | 08:00-12:00, 20:00-24:00 |
| **3.2** | 16:00 - 20:00 | 04:00-08:00, 12:00-16:00 |

## Логування

### Формат логів
```
[2025-10-15 14:00:00] INFO: 🔄 Starting schedule update
[2025-10-15 14:00:02] INFO:   Fetching DTEK kyiv...
[2025-10-15 14:00:03] INFO:     ✓ kyiv: 6 subgroups
[2025-10-15 14:00:04] INFO:   Fetching Ukrenergo data...
[2025-10-15 14:00:05] INFO:     ✓ Ukrenergo /outages: success
[2025-10-15 14:00:05] INFO: ✅ Schedule update completed successfully
[2025-10-15 14:00:05] INFO:    DTEK regions: 4
[2025-10-15 14:00:05] INFO:    Ukrenergo data: available
```

### Типи повідомлень
- ✅ `INFO`: успішні операції
- ⚠️ `WARNING`: не критичні проблеми
- ❌ `ERROR`: помилки, потребують уваги

## Fallback стратегія

Якщо live оновлення недоступні:

1. **Спроба 1**: Live DTEK scraper
2. **Спроба 2**: Blackout API client (geocoding)
3. **Спроба 3**: Статична база (150+ адрес)

```python
# Пріоритет джерел
if SCHEDULE_UPDATER_AVAILABLE:
    result = schedule_updater.get_schedule_for_address(...)
elif BLACKOUT_API_AVAILABLE:
    result = blackout_client.get_schedule_for_address(...)
else:
    result = get_schedule_fallback(...)  # Static DB
```

## Моніторинг на UI

На сторінці `/blackouts` відображається:

```
🔄 Графіки оновлюються автоматично кожну годину з ДТЕК та Укренерго
   Останнє оновлення: 14:30 • Наступне: через годину
```

**Анімації**:
- 🔵 Пульсація - система працює нормально
- 🔄 Обертання - оновлення в процесі

## Налаштування

### Частота оновлень
```python
# app.py - змінити hours на потрібне значення
scheduler.add_job(
    func=schedule_updater.update_all_schedules,
    trigger='interval',
    hours=1,  # <-- Змінити тут (наприклад, 0.5 для 30 хв)
)
```

### Час кешу
```python
# schedule_updater.py
schedule_updater.is_cache_valid(max_age_hours=1)  # <-- Змінити тут
```

### Таймаути запитів
```python
# schedule_updater.py - в методах _update_*
response = requests.get(url, timeout=10)  # <-- Змінити тут
```

## Graceful Shutdown

Система коректно завершує роботу:

```python
# Обробники сигналів
atexit.register(shutdown_scheduler)
signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)
```

При зупинці:
1. Scheduler завершує поточні задачі
2. Зберігає останні дані в кеш
3. Закриває всі з'єднання

## Deployment

### Render.com / Heroku
```yaml
# render.yaml
services:
  - type: web
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python app.py
```

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

### Системні вимоги
- Python 3.9+
- 512 MB RAM (мінімум)
- Інтернет з'єднання
- Відкриті порти для DTEK/Ukrenergo

## Troubleshooting

### Scheduler не запускається
```bash
# Перевірка логів
grep "Scheduler started" app.log
grep "SCHEDULE_UPDATER_AVAILABLE" app.log
```

### Графіки не оновлюються
```bash
# Перевірка статусу
curl http://localhost:5000/api/schedule_status

# Ручне оновлення
curl -X POST http://localhost:5000/api/live_schedules
```

### DTEK недоступний
- Сайти можуть блокувати scraping
- Використовуйте User-Agent headers
- Додайте затримки між запитами
- Fallback на статичні дані

## Розширення

### Додати нове джерело
```python
# schedule_updater.py
def _update_new_source(self) -> Dict[str, Any]:
    """Оновлення з нового джерела"""
    try:
        response = requests.get('https://api.example.com/schedules')
        data = response.json()
        return self._parse_new_source(data)
    except Exception as e:
        logger.error(f"New source error: {e}")
        return {}

# Додати в update_all_schedules()
new_source_data = self._update_new_source()
self.schedules_cache['new_source'] = new_source_data
```

### Додати webhook notifications
```python
# schedule_updater.py
def update_all_schedules(self):
    result = super().update_all_schedules()
    
    # Відправити webhook
    requests.post(
        'https://hooks.example.com/schedule-updated',
        json={'timestamp': datetime.now().isoformat()}
    )
    
    return result
```

## Безпека

### Rate Limiting
```python
# Обмеження на DTEK scraping
time.sleep(2)  # 2 секунди між запитами
```

### User-Agent Rotation
```python
headers = {
    'User-Agent': random.choice(USER_AGENTS),
    'Accept-Language': 'uk-UA,uk;q=0.9'
}
```

### Error Handling
```python
@retry(tries=3, delay=5, backoff=2)
def _update_dtek_schedules(self):
    # Automatic retry on failure
    pass
```

## Автор
Vladimir Malik (vavaika22423232)

## Ліцензія
MIT License - використовуйте вільно!

---

**Примітка**: Система автоматично адаптується до доступності джерел даних і завжди намагається надати найактуальнішу інформацію користувачам.
