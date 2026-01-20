# Архітектура Neptun 2.0

## Статус: ✅ Модульна архітектура реалізована

**Тести:** 128 passed  
**Модулів:** 50+ Python файлів  
**Оригінал:** app.py (30,259 рядків) → Модульна структура

---

## Структура проекту

```
neptun/
├── app.py                    # Legacy monolith (30K lines) - НЕ ЧІПАТИ
├── app_new.py                # ✅ Новий entry point (модульний)
├── config.py                 # ✅ Централізована конфігурація
│
├── domain/                   # ✅ Бізнес-логіка (чисті функції)
│   ├── __init__.py
│   ├── models.py            # Dataclasses: Track, Coordinates, TrackStatus
│   ├── geo.py               # Географічні функції: haversine, bearing
│   └── threat_types.py      # ThreatType enum, категорії загроз
│
├── services/                 # ✅ Сервісний шар
│   ├── geocoding/           # Геокодинг з fallback chain
│   │   ├── __init__.py     # Exports
│   │   ├── base.py         # GeocoderInterface ABC, GeocodingResult
│   │   ├── local.py        # LocalGeocoder (25K+ населених пунктів)
│   │   ├── photon.py       # PhotonGeocoder (komoot.io API)
│   │   ├── opencage.py     # OpenCageGeocoder (backup)
│   │   ├── chain.py        # GeocoderChain (Chain of Responsibility)
│   │   └── cache.py        # GeocodeCache (positive + negative caching)
│   │
│   ├── telegram/            # Telegram парсинг
│   │   ├── __init__.py
│   │   ├── patterns.py     # THREAT_PATTERNS, ThreatPatterns class
│   │   ├── parser.py       # MessageParser
│   │   └── fetcher.py      # TelegramFetcher (Telethon wrapper)
│   │
│   ├── tracks/              # Сховище треків
│   │   ├── __init__.py
│   │   ├── store.py        # TrackStore (thread-safe, TTL, backup)
│   │   └── processor.py    # TrackProcessor (background geocoding)
│   │
│   ├── alarms/              # Ukraine Alarm API
│   │   ├── __init__.py
│   │   ├── client.py       # AlarmClient (ukrainealarm.com)
│   │   ├── state.py        # AlarmState (region states)
│   │   └── monitor.py      # AlarmMonitor (background polling)
│   │
│   ├── processing/          # Message pipeline
│   │   ├── __init__.py
│   │   └── pipeline.py     # MessagePipeline (parse → geocode → store)
│   │
│   └── realtime/            # Real-time updates
│       └── __init__.py     # RealtimeService, SSE channels
│
├── api/                      # ✅ Flask Blueprints (6 total)
│   ├── __init__.py         # Blueprint exports
│   ├── data.py             # /data - основні дані для карти
│   ├── health.py           # /health, /ready, /live
│   ├── alarms.py           # /api/alarms - стан тривог
│   ├── tracks.py           # /api/tracks - REST API треків
│   ├── sse.py              # /api/sse - Server-Sent Events
│   └── admin.py            # /admin - адміністрування
│
├── utils/                    # ✅ Thread-safe утиліти
│   ├── __init__.py
│   ├── threading.py        # AtomicValue, ThreadSafeDict, TTLCache
│   └── rate_limiter.py     # TokenBucketLimiter, SlidingWindowLimiter
│
└── tests/                    # ✅ Тести (128 passed)
    ├── conftest.py         # Pytest fixtures
    ├── test_geocoding.py   # 33 тестів геокодингу
    ├── test_tracks.py      # 25 тестів TrackStore/Processor
    ├── test_telegram.py    # 7 тестів патернів
    ├── test_utils.py       # 32 тестів utilities
    ├── test_api.py         # 26 тестів API endpoints
    └── test_message_store.py # 3 тестів
```

---

## Архітектурні патерни

### 1. Chain of Responsibility (Геокодинг)
```python
# services/geocoding/chain.py
chain = GeocoderChain([
    LocalGeocoder(city_coords),      # Priority 10 - найшвидший
    PhotonGeocoder(),                 # Priority 50 - безкоштовний API
    OpenCageGeocoder(api_key),        # Priority 100 - платний backup
])

result = chain.geocode("Київ")  # Спробує по черзі
```

### 2. Thread-Safe Containers
```python
# utils/threading.py
state = AtomicValue(initial_data)      # Atomic get/set/update
cache = ThreadSafeDict()                # Thread-safe dictionary
ttl_cache = TTLCache(default_ttl=60)    # Auto-expiring cache
```

### 3. Dependency Injection
```python
# app_new.py - все передається явно
track_store = TrackStore(file_path="tracks.json")
geocoder = GeocoderChain([LocalGeocoder(), PhotonGeocoder()])
processor = TrackProcessor(store=track_store, geocoder=geocoder)

init_data_api(track_store=track_store, geocoder=geocoder)
```

### 4. Blueprint Pattern (Flask)
```python
# api/tracks.py
tracks_bp = Blueprint('tracks', __name__, url_prefix='/api/tracks')

@tracks_bp.route('/active')
def get_active_tracks():
    store = current_app.extensions['track_store']
    return jsonify(store.get_active(since=cutoff))
```

---

## API Endpoints

### Data API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/data` | GET | Основні дані для карти |
| `/health` | GET | Health check |
| `/ready` | GET | Readiness probe |
| `/live` | GET | Liveness probe |

### Tracks API (`/api/tracks`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Активні треки |
| `/active` | GET | Активні за останній час |
| `/history` | GET | Історія з пагінацією |
| `/stats` | GET | Статистика |
| `/by-type` | GET | Групування по типу |
| `/by-region` | GET | Групування по області |
| `/geojson` | GET | GeoJSON FeatureCollection |
| `/<id>` | GET | Окремий трек |
| `/<id>` | DELETE | Видалення (auth) |
| `/<id>/hide` | POST | Приховання (auth) |

### Alarms API (`/api/alarms`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/state` | GET | Поточний стан тривог |
| `/regions` | GET | Список областей |
| `/history` | GET | Історія тривог |

### Admin API (`/admin`)
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/stats` | GET | X-Admin-Secret | Системна статистика |
| `/markers` | GET | X-Admin-Secret | Всі маркери |
| `/marker` | POST | X-Admin-Secret | Додати маркер |

---

## Сервіси

### TrackStore
Thread-safe сховище треків з автоматичним:
- TTL (видалення застарілих)
- Backup/restore (JSON файли)
- Max count enforcement
- Hide/unhide функціонал

```python
store = TrackStore(
    file_path="tracks.json",
    retention_minutes=60,
    max_count=500,
)

store.add(entry)
store.get_active(since=datetime)
store.stats()  # {'count': N, 'by_type': {...}, 'by_oblast': {...}}
```

### TrackProcessor
Background processor для геокодингу:
```python
processor = TrackProcessor(
    store=track_store,
    geocoder=geocoder_chain,
    batch_size=10,
)

processor.start()       # Background thread
processor.is_running()  # True
processor.stats()       # {'processed': N, 'geocoded': N, ...}
processor.stop()
```

### RealtimeService
Server-Sent Events для live updates:
```python
realtime = RealtimeService()

# Subscribe
realtime.subscribe('tracks', client_queue)

# Publish
realtime.publish('tracks', {'type': 'new', 'data': track})
```

---

## Конфігурація

```python
# config.py
class Config:
    # Telegram
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_CHANNELS: List[str]
    
    # APIs
    ALARM_API_TOKEN: str
    OPENCAGE_API_KEY: str
    
    # Storage
    TRACKS_FILE: str = 'tracks.json'
    RETENTION_MINUTES: int = 60
    
    # Rate limits
    GEOCODE_RATE: float = 1.0  # per second
    ALARM_POLL_INTERVAL: int = 30  # seconds
```

---

## Тестування

```bash
# Всі тести
python3 -m pytest tests/ -v

# Конкретний модуль
python3 -m pytest tests/test_geocoding.py -v

# З coverage
python3 -m pytest tests/ --cov=services --cov-report=html
```

### Поточний статус
```
128 passed ✅
- test_geocoding.py: 33 tests
- test_tracks.py: 25 tests  
- test_utils.py: 32 tests
- test_api.py: 26 tests
- test_telegram.py: 7 tests
- test_message_store.py: 3 tests
```

---

## Міграція з app.py

### Етап 1: Паралельна робота ✅
- `app.py` - production (не чіпати!)
- `app_new.py` - development/testing

### Етап 2: Поступовий перехід
1. Додати feature flags для нових endpoints
2. Перенаправити трафік на нові blueprints
3. Моніторити помилки

### Етап 3: Повна міграція
1. Замінити `app.py` на `app_new.py`
2. Видалити legacy код
3. Очистити невикористані залежності

---

## Продуктивність

### Оптимізації
- **Thread-safe containers** - без глобальних мутексів
- **TTL caching** - автоматичне очищення
- **Batch geocoding** - зменшення API calls
- **Connection pooling** - для HTTP requests
- **Lazy loading** - завантаження по потребі

### Метрики
- Startup time: ~2 sec
- Memory: ~150-200 MB
- Geocoding: ~10 req/sec (з кешем)
- SSE latency: <100ms

---

## Залежності

```txt
# Core
flask>=2.0
telethon>=1.28

# Geocoding
requests>=2.28

# Utils
python-dateutil>=2.8

# Testing
pytest>=7.0
pytest-cov>=4.0
```

---

## Контакти

- **Проект:** neptun.in.ua
- **GitHub:** [repository]
- **Документація:** /docs
