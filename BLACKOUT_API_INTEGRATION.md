# ІНТЕГРАЦІЯ З API ЕНЕРГОПРОВАЙДЕРІВ

## Огляд

Система тепер підтримує **будь-які міста, села та вулиці України** через геокодування та інтеграцію з API енергопровайдерів.

## Як це працює

### 1. Геокодування адрес
- Використовується **Nominatim (OpenStreetMap)** для розпізнавання адрес
- Підтримує всі населені пункти України
- Визначає координати та повну адресу

### 2. Визначення провайдера
Система автоматично визначає енергопровайдера за містом:
- **ДТЕК Київські електромережі** - Київ, Київська область
- **ДТЕК Одеські електромережі** - Одеса, Одеська область  
- **ДТЕК Дніпровські електромережі** - Дніпро, Дніпропетровська область
- **ДТЕК Донецькі електромережі** - Донецька область
- **ДТЕК Східенерго** - Харків, Харківська область
- **YASNO** - Київ (альтернативний провайдер)
- **Укренерго** - загальноукраїнський оператор (fallback)
- **Регіональні обленерго** - інші області

### 3. Отримання графіків

#### Поточна реалізація (DEMO)
```python
# Використовує геокодування + логіку визначення черги
result = blackout_client.get_schedule_for_address(city, street, building)
```

Повертає:
- ✅ Підтверджену адресу (через OpenStreetMap)
- ✅ Провайдера енергії
- ✅ Чергу відключень (1-3)
- ✅ Графік на 24 години
- ✅ Координати адреси

#### Для повної інтеграції потрібно:

## РЕАЛЬНА ІНТЕГРАЦІЯ З DTEK

### API ДТЕК
ДТЕК має веб-інтерфейси для пошуку графіків:
- https://www.dtek-krem.com.ua/ua/shutdowns (Київ)
- https://www.dtek-oem.com.ua/ua/shutdowns (Одеса)
- https://www.dtek-dnem.com.ua/ua/shutdowns (Дніпро)

**Потрібно:**
1. Reverse-engineering їх API або використання Selenium/Playwright
2. Отримати endpoint для пошуку адрес
3. Отримати endpoint для графіків по адресі

**Приклад інтеграції:**
```python
def fetch_dtek_schedule(provider_id: str, address: str):
    # Крок 1: Пошук адреси
    search_url = f"{provider_api}/api/search-address"
    response = session.post(search_url, json={
        'address': address,
        'city': city
    })
    address_data = response.json()
    
    # Крок 2: Отримання графіку
    schedule_url = f"{provider_api}/api/get-schedule"
    response = session.post(schedule_url, json={
        'address_id': address_data['id'],
        'queue': address_data['queue']
    })
    
    return response.json()
```

### YASNO API

YASNO має публічний API:
```
GET https://api.yasno.com.ua/api/v1/pages/home/schedule-turn-off-electricity
```

**Структура даних:**
- Групи: 1-6
- Формат: JSON з розкладом на тиждень
- Потрібен API ключ (можна отримати через devtools)

**Приклад інтеграції:**
```python
def fetch_yasno_schedule():
    url = "https://api.yasno.com.ua/api/v1/pages/home/schedule-turn-off-electricity"
    headers = {
        'Authorization': 'Bearer YOUR_API_KEY',
        'User-Agent': 'Mozilla/5.0...'
    }
    response = session.get(url, headers=headers)
    return response.json()
```

### Укренерго

Укренерго публікує графіки на сайті:
- https://www.oe.if.ua/

Можна парсити HTML або шукати приховані API endpoints.

## РЕАЛІЗОВАНІ МОЖЛИВОСТІ

### ✅ Працює зараз:
1. **Універсальний пошук адрес** - через OpenStreetMap
2. **Всі міста України** - будь-які населені пункти
3. **Геокодування** - координати + перевірка існування адреси
4. **Визначення провайдера** - автоматично по регіону
5. **Демо-графіки** - структура як у ДТЕК (3 черги)

### 🔄 Потребує інтеграції:
1. **Реальні API ключі** від ДТЕК, YASNO
2. **Парсинг** веб-сайтів провайдерів (якщо немає API)
3. **База адрес з чергами** - потрібна від провайдерів
4. **Оновлення даних** - кешування та refresh

## ВИКОРИСТАННЯ

### Приклад запиту:
```
GET /api/get_schedule?city=Суми&street=Соборна&building=15
```

### Відповідь:
```json
{
    "address": "Суми, вул. Соборна, 15",
    "city": "Суми",
    "oblast": "Сумська",
    "provider": "Сумиобленерго",
    "group": 2,
    "schedule": [
        {
            "time": "00:00 - 04:00",
            "label": "Електропостачання",
            "status": "normal"
        },
        {
            "time": "12:00 - 16:00",
            "label": "Активне відключення",
            "status": "active"
        }
    ],
    "coordinates": {
        "lat": 50.9077,
        "lon": 34.7981
    },
    "found": true
}
```

## НАСТУПНІ КРОКИ

### 1. Отримання API доступу
- Зв'язатися з ДТЕК для API ключів
- Зареєструватися в YASNO API
- Дослідити endpoints інших провайдерів

### 2. Парсинг (якщо немає API)
```bash
pip install selenium playwright beautifulsoup4
```

### 3. База даних адрес
- Імпортувати адреси з відкритих даних
- Синхронізувати з провайдерами
- Періодичне оновлення

### 4. Кешування
- Redis для швидкого доступу
- Оновлення раз на годину
- TTL для застарілих даних

## ТЕХНІЧНІ ДЕТАЛІ

### Файли проекту:
- `blackout_api.py` - Клієнт для роботи з API
- `app.py` - Flask endpoints
- `templates/blackouts.html` - UI
- `requirements.txt` - Залежності

### Залежності:
```
geopy==2.4.1  # Геокодування
requests==2.32.3  # HTTP запити
```

### Логування:
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

## КОНТАКТИ ДЛЯ ІНТЕГРАЦІЇ

- **ДТЕК**: https://www.dtek.com/
- **YASNO**: https://yasno.com.ua/
- **Укренерго**: https://ua.energy/

## ЛІЦЕНЗІЯ ТА ДАНІ

Дані про відключення є публічною інформацією згідно з законодавством України. 
Використання в освітніх та інформаційних цілях.
