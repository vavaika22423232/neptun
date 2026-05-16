# Backend / API — план підтримки мобільного NEPTUN

Оновлено: 2026-05-08. Мета: стабільний realtime, передбачувані REST контракти, безпечний чат і керовані push.

---

## 0. Інвентар (вже є в `nextjs-app`)

| Призначення | Реалізація зараз |
|-------------|------------------|
| Реєстрація FCM та регіонів | `POST /api/register-device` (`src/app/api/register-device/route.ts`, `RegisterDeviceSchema`) |
| Чат | `src/app/api/chat/*` |
| Premium / entitlement | `src/app/api/premium/*`, `verify-purchase` |
| Карта / маркери | `GET /api/data`, ingest, SSE gateway |
| Health | `GET /api/health` |

Нові canonical маршрути бажано додавати під **`/api/v1/...`** з fallback або розширенням існуючих схем, щоб не ламати production-клієнтів.

---

## 1. Realtime (SSE / WebSocket)

| Зміна | Навіщо |
|-------|--------|
| Один **первинний** стрім для маркерів/подій (за можливості) | Менше дубльованих з’єднань на клієнті |
| **Exponential backoff** + max retry + **heartbeat** | Менше «завислих» мертвих з’єднань |
| Підтримка **Last-Event-ID** (або cursor) | Пропуски подій після реконекту |
| **Gzip/Brotli** на HTTP upgrade path | Менший трафік |
| Невеликі JSON payload-и; **дельти** замість повних знімків де можливо | Батарея / мережа |

## 2. REST: маркери та здоров’я

- **`GET /api/v1/markers`** (або поточний шлях з версіонуванням): пагінація, поля `id`, `type`, `region`, `lat`, `lng`, `updated_at`, `expires_at`, `confidence`, `source`, `status`.
- Заголовки **`ETag`** + **`Cache-Control`** для статусних ендпоінтів.
- **`GET /api/health`** (або розширення): latency percentiles pipeline, realtime connections.

## 3. Чат

Нові або уточнені ендпоінти (узгодити з існуючим Next.js):

- `POST /api/chat/report` — скарга на повідомлення / користувача.
- `POST /api/chat/moderate` — адмін/модератор (або webhook).
- `POST /api/chat/mute` — мут по device/session.
- `GET /api/chat/rules` — текст правил для клієнта.

Сервер: **rate limit** (наприклад, N повідомлень / хв), антиспам по часу та довжині, пагінація історії.

## 4. Пристрої та push

| Метод | Призначення |
|-------|-------------|
| `POST /api/devices/register` | FCM/APNs token, platform, appVersion, locale, timezone |
| `PATCH /api/devices/preferences` | Категорії загроз, регіони, тихі години, premium |
| `DELETE /api/devices/token` | Вихід / відписка |
| `POST /api/notifications/test` | Перевірка доставки (з rate limit) |
| `GET /api/notifications/preferences` | Синхронізація з клієнта |

Поле **premium** на сервері — для пріоритетних каналів / менш агресивного throttling (не для приховування критичних тривог).

## 5. Помилки та версіонування

- Єдиний формат: `{ "error": { "code", "message", "details?" } }`.
- Префікс **`/api/v1/`** для нових маршрутів; старі — deprecated window.

## 6. Observability

- Structured logs (request id, device id hash).
- Метрики: підключення SSE, відсоток 4xx/5xx на чаті, час відповіді маркерів.

## 7. Безпечне впровадження

1. Додати ендпоінти за фіче-флагами.
2. Мобільний клієнт: graceful fallback, якщо 404.
3. Навантажувальні тести на rate limits.

---

*Реалізація в `nextjs-app/` узгоджується з наявними `src/app/api/*` маршрутами; конкретні файли додавати після узгодження з production.*
