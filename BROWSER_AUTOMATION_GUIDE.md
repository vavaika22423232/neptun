# 🌐 Browser Automation для DTEK API

## Що це таке?

Browser automation - це запуск справжнього браузера (Chromium/Firefox) через код для обходу захисту Incapsula/Imperva.

## 📦 Варіанти інструментів

### 1. Playwright (Рекомендовано) ⭐
```bash
pip install playwright
playwright install chromium
```

**Переваги:**
- ✅ Швидкий та стабільний
- ✅ Підтримка async/await
- ✅ Легкий перехоплення API запитів
- ✅ Автоматичне очікування елементів

**Недоліки:**
- ❌ Споживає ~200-300 MB RAM
- ❌ Потребує chromium на сервері

### 2. Selenium
```bash
pip install selenium
```

**Переваги:**
- ✅ Популярніший, більше документації
- ✅ Підтримка різних браузерів

**Недоліки:**
- ❌ Повільніший за Playwright
- ❌ Складніше перехоплення API

### 3. Puppeteer (Node.js)
```bash
npm install puppeteer
```

**Переваги:**
- ✅ Розроблений Google
- ✅ Швидкий

**Недоліки:**
- ❌ Потрібен Node.js
- ❌ Ваш проект на Python

## 🚀 Як це працює

```
1. Запускаємо браузер → Chromium
2. Відкриваємо сайт DTEK → Incapsula бачить справжній браузер ✅
3. Вводимо адресу → JavaScript виконується
4. Перехоплюємо API запит → Отримуємо JSON
5. Закриваємо браузер → Повертаємо дані
```

## 📝 Приклад використання

### Playwright (Sync)
```python
from dtek_browser_scraper import DTEKBrowserScraper

# Отримати графік для адреси
with DTEKBrowserScraper(region='kyiv', headless=True) as scraper:
    schedule = scraper.get_schedule_for_address("Київ, Хрещатик, 1")
    print(schedule)
```

### Playwright (Async)
```python
from playwright.async_api import async_playwright

async def get_schedule():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('https://www.dtek-krem.com.ua')
        await page.fill('input[placeholder*="адрес"]', 'Київ, Хрещатик, 1')
        
        # Перехоплення API
        async with page.expect_response('**/api/v1/schedule') as response_info:
            await page.click('button[type="submit"]')
            response = await response_info.value
            data = await response.json()
            
        await browser.close()
        return data
```

## 🔧 Інтеграція в blackout_api.py

```python
# blackout_api.py
from dtek_browser_scraper import DTEKBrowserScraper
import time

class BlackoutAPIClient:
    def __init__(self):
        self._browser_cache = {}
        self._cache_ttl = 7200  # 2 години
        
    def get_schedule_for_address(self, address, city):
        # 1. Спробувати YASNO API (швидко)
        if city.lower() in ['київ', 'kyiv', 'дніпро', 'dnipro']:
            return self._get_schedule_from_yasno(address, city)
            
        # 2. Перевірити кеш браузера
        cache_key = f"{city}:{address}"
        if cache_key in self._browser_cache:
            cached = self._browser_cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                return cached['data']
                
        # 3. Використати browser scraper (повільно, але працює)
        region_map = {
            'одеса': 'odesa',
            'одесса': 'odesa',
            'харків': 'kharkiv',
        }
        
        region = region_map.get(city.lower())
        if not region:
            return self._get_fallback_schedule()
            
        try:
            with DTEKBrowserScraper(region=region, headless=True) as scraper:
                schedule = scraper.get_schedule_for_address(address)
                
                # Кешуємо результат
                self._browser_cache[cache_key] = {
                    'data': schedule,
                    'timestamp': time.time()
                }
                
                return schedule
        except Exception as e:
            print(f"Browser scraper error: {e}")
            return self._get_fallback_schedule()
```

## ⚡ Оптимізація

### 1. Асинхронна обробка (Celery)
```python
# tasks.py
from celery import Celery
from dtek_browser_scraper import DTEKBrowserScraper

app = Celery('tasks', broker='redis://localhost:6379')

@app.task
def update_dtek_schedule(address, region):
    """Оновлення графіку в фоні"""
    with DTEKBrowserScraper(region=region) as scraper:
        schedule = scraper.get_schedule_for_address(address)
        # Зберегти в Redis/PostgreSQL
        return schedule

# Використання
from tasks import update_dtek_schedule

# Викликати в фоні
result = update_dtek_schedule.delay("Київ, Хрещатик, 1", "kyiv")
```

### 2. Пакетна обробка
```python
# Оновлюємо всі адреси раз на годину
def update_all_schedules():
    addresses = get_popular_addresses()  # З бази даних
    
    with DTEKBrowserScraper(region='kyiv') as scraper:
        for address in addresses:
            schedule = scraper.get_schedule_for_address(address)
            cache_schedule(address, schedule)  # Зберегти в Redis
```

### 3. Kubernetes/Docker оптимізація
```dockerfile
# Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Playwright вже встановлений в базовому image
COPY . .

CMD ["python", "app.py"]
```

## 🔐 Bypass Incapsula

### Важливі налаштування:
```python
browser = playwright.chromium.launch(
    headless=True,
    args=[
        '--disable-blink-features=AutomationControlled',  # Приховує webdriver
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',  # Тільки для dev
    ]
)

context = browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    locale='uk-UA',
    timezone_id='Europe/Kiev',
    permissions=['geolocation'],  # Якщо потрібно
)

# Видалити navigator.webdriver
page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    
    // Фіктивні плагіни
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
""")
```

## 📊 Порівняння підходів

| Підхід | Швидкість | Надійність | Складність | Вартість |
|--------|-----------|------------|------------|----------|
| YASNO API | ⚡⚡⚡ | ⭐⭐⭐ | ✅ | 💰 (безкоштовно) |
| Browser Automation | ⚡ | ⭐⭐ | ⚠️ | 💰💰💰 |
| Database Fallback | ⚡⚡⚡ | ⭐ | ✅ | 💰 |

## 🎯 Рекомендації

### Для production:
1. **Гібридний підхід:**
   - YASNO API для Києва/Дніпра (швидко) ✅
   - Browser automation для інших регіонів (рідко) ⚠️
   - Database fallback якщо все не працює ✅

2. **Кешування:**
   - YASNO: 1 година TTL
   - Browser scraper: 2-4 години TTL
   - Redis для кешу

3. **Асинхронність:**
   - Celery для фонового оновлення
   - WebSocket для real-time updates клієнтам

### Для Render.com:
```yaml
# render.yaml
services:
  - type: web
    name: blackout-app
    env: python
    buildCommand: |
      pip install -r requirements.txt
      playwright install chromium
    startCommand: gunicorn app:app
    envVars:
      - key: PLAYWRIGHT_BROWSERS_PATH
        value: /opt/render/.cache
```

## ⚠️ Обмеження

1. **Render.com безкоштовний план:**
   - ❌ Обмежена RAM (512 MB) - недостатньо для браузера
   - ❌ Обмежений CPU - повільна робота
   - ✅ Потрібен платний план ($7/місяць)

2. **Альтернативи:**
   - Railway.app (більше RAM на безкоштовному)
   - Fly.io (підтримує Docker з Playwright)
   - Heroku (дорожче)
   - VPS (DigitalOcean $4/місяць)

## 🚀 Наступні кроки

1. **Тестування:**
   ```bash
   python dtek_browser_scraper.py
   ```

2. **Інтеграція:**
   - Додати в `blackout_api.py`
   - Налаштувати кешування
   - Додати Celery для async

3. **Deployment:**
   - Оновити `requirements.txt`
   - Додати Playwright buildpack
   - Налаштувати Redis для кешу

## 📚 Корисні посилання

- [Playwright Documentation](https://playwright.dev/python/)
- [Selenium Documentation](https://selenium-python.readthedocs.io/)
- [Bypass Incapsula Guide](https://github.com/VeNoMouS/cloudscraper)
- [Playwright на Render](https://render.com/docs/playwright)
