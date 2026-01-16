# Cloudflare CDN Setup для NEPTUN

## Шаг 1: Додати домен в Cloudflare

1. Зайдіть на https://dash.cloudflare.com
2. Натисніть **"Add a Site"**
3. Введіть `neptun.in.ua`
4. Виберіть план **Free**
5. Cloudflare покаже DNS записи - скопіюйте їх

## Шаг 2: Змінити NS сервери у реєстратора домену

Cloudflare надасть 2 nameservers, наприклад:
- `ada.ns.cloudflare.com`
- `lee.ns.cloudflare.com`

Замініть їх у вашого реєстратора (де купували домен).

## Шаг 3: Налаштувати DNS записи

В Cloudflare DNS → Records, додайте:

| Type  | Name | Content                              | Proxy |
|-------|------|--------------------------------------|-------|
| CNAME | @    | neptun-alerts.onrender.com           | ✅ ON  |
| CNAME | www  | neptun-alerts.onrender.com           | ✅ ON  |
| CNAME | api  | neptun-alerts.onrender.com           | ✅ ON  |

⚠️ **Proxy status повинен бути ORANGE (Proxied)** - це включає CDN!

## Шаг 4: Налаштувати SSL/TLS

1. Перейдіть в **SSL/TLS → Overview**
2. Виберіть **Full (strict)**

## Шаг 5: Налаштувати Cache Rules

### Кешування статики (7 днів)
1. Перейдіть в **Rules → Cache Rules**
2. Створіть правило:
   - **Name:** Cache Static Assets
   - **When:** URI Path starts with `/static/`
   - **Then:** 
     - Cache eligibility: Eligible for cache
     - Edge TTL: 7 days
     - Browser TTL: 7 days

### Кешування API (30 секунд)
1. Створіть правило:
   - **Name:** Cache API Short
   - **When:** URI Path starts with `/api/alarms` OR `/data` OR `/api/chat/messages`
   - **Then:**
     - Cache eligibility: Eligible for cache  
     - Edge TTL: 30 seconds
     - Browser TTL: 10 seconds

### Bypass для динамічного контенту
1. Створіть правило:
   - **Name:** Bypass Dynamic
   - **When:** URI Path starts with `/stream` OR `/presence` OR `/admin`
   - **Then:**
     - Cache eligibility: Bypass cache

## Шаг 6: Налаштувати Page Rules (опціонально)

1. **Rules → Page Rules**
2. Створіть правило для `*neptun.in.ua/static/*`:
   - Cache Level: Cache Everything
   - Edge Cache TTL: 1 month

## Шаг 7: Speed оптимізації

1. Перейдіть в **Speed → Optimization**
2. Увімкніть:
   - ✅ Auto Minify (JavaScript, CSS, HTML)
   - ✅ Brotli compression
   - ✅ Early Hints
   - ✅ Rocket Loader (optional)

## Шаг 8: Security

1. **Security → Settings**:
   - Security Level: Medium
   - Challenge Passage: 30 minutes
   - Browser Integrity Check: ON

2. **Security → Bots**:
   - Bot Fight Mode: ON

## Перевірка роботи

Після налаштування (15-30 хв на DNS propagation):

```bash
# Перевірити CF заголовки
curl -I https://neptun.in.ua/api/alarms/all

# Має бути:
# cf-cache-status: HIT (або MISS перший раз)
# cf-ray: xxxxx-XXX
# server: cloudflare
```

## Очікуваний результат

| Метрика | Без CF | З CF |
|---------|--------|------|
| Latency EU | 200-400ms | 20-50ms |
| Latency US | 500-800ms | 50-100ms |
| Bandwidth | 100% | 20-40% |
| DDoS protection | ❌ | ✅ |

## Моніторинг

В Cloudflare Dashboard → Analytics:
- Cache Hit Ratio (target: >70%)
- Bandwidth Saved
- Requests by Country
- Threats Blocked
