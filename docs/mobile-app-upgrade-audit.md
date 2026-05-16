# NEPTUN Mobile — аудит архітектури, UX, backend (Flutter + API)

**Оновлено:** 2026-05-08  
**Ціль:** перехід від «розкиданого» застосунку до преміального світлого light-first продукту з передбачуваною навігацією, realtime і монетизацією без шкоди безпечному ядру (карта + тривоги).

Цей документ закриває **ЕТАП 1** дорожньої карти й узгоджений з реалізацією в репозиторії (Git truth).

---

## 1. Архітектура Flutter

### 1.1 Вхідна точка і життєвий цикл

| Файл / шар | Оцінка | Коментар |
|------------|--------|----------|
| `lib/main.dart` | Добре | `runZonedGuarded`, відкладена ініціалізація, `ProviderScope`, обхід відомих WebView-помилок |
| `initServiceLocator` + GetIt | Добре | Зрозумілі синглетони для SSE, покупок, чату |
| `FlutterError.onError` | Ризик | Частину помилок «ковтає» — зручно для UX, гірше для Sentry (потрібен фільтр / sampling) |

**Техборг:** тонкий розподіл «що синхронно до першого кадру» vs «фон»: документувати в одному місці (`AGENTS.md` / цей файл).

### 1.2 Роутинг і навігація

| Елемент | Стан |
|---------|------|
| `GoRouter` + `StatefulShellRoute.indexedStack` | Основний shell: **Карта · Радар · Чат · Профіль** |
| Редіректи | `/regions` → `RoutePaths.radarRegionsView` |
| Онбординг | `PrefsKeys.firstLaunch`, редірект на `RoutePaths.onboarding` |
| Константи шляхів | **Зроблено 2026-05-08:** `lib/core/router/route_paths.dart`, `AppRouter` використовує `RoutePaths.*` |
| `/alerts` | **Без дубля** — один маршрут у `GoRouter` |

- **Riverpod** — регіони, чат-контролер, тема, connectivity тощо.
- **Locator** — реклама, SSE (`DataStreamService`), покупки, чат-сервіс.
- **ValueNotifier / ChangeNotifier** — у частині legacy-сервісів.

**Проблема:** змішано «глобальні» сервіси без єдиного шару **Repository → Notifier/UI**. Це Priority 1 для стабільності тестів і скорочення дублю підписок SSE.

Цільова модель (етап впровадження):

- `MapSessionController` / `MapRealtimeRepository` — фази каналу, last refresh, офлайн.
- `RadarController` / **RadarFeedNotifier** — **зроблено 2026-05-08** (`radar_feed_provider` + `RadarRepository`); далі — кеш знімка на диск.
- `ChatController` (вже частково) — повний цикл стану messenger.
- `PremiumController` — entitlement + локальний кеш + синхрон з API.
- `NotificationPrefsController` — регіони, типи подій, тихі години.

### 1.4 Шари та структура каталогів

**Фактично:** суміш `pages/`, `services/`, `features/*`, `widgets/`, `design/`.

**Ціль:** не дублювати все одразу, а нові фічі вести в `lib/features/<name>/{data,domain,presentation}`; поступово розрізати god-файли (`map_tab`, `notification_service`, `data_stream_service`).

### 1.5 Карта

- Основний досвід: **WebView** (Leaflet / MapLibre на сайті) + **bridge `NeptunApp`** для тапів по загрозах → нативний bottom sheet.
- Є **flutter_map** в залежностями — простір для Phase B/C (overlay / повна заміна).
- HUD **«Ситуація зараз»**: `map_situation_status_strip` + `DataStreamService.mapRealtimeLink`.

**Техборг:** кеш загроз у Dart-шарі поверх `MapOfflineCache`, дедуп маркерів на клієнті, узгодження TTL із сервером.

### 1.6 Чат, premium, реклама

- Чат: `ChatService`, `chat_controller`, API Next.js (`/api/chat/*`), crowd vote-mute.
- Premium: `PurchaseService`, paywall screens, частково server entitlement.
- Реклама: `AdService` — синхронізувати частоту з **індексом вкладки чату (2)** і аларм-подіями (не показувати в критичні моменти).

---

## 2. UI / UX

### 2.1 Дизайн-система

- Токени: `NeptunSpacing`, `NeptunRadius`, `NeptunStatus`, тема через `DiaryColors` + `AppTheme`.
- Світла тема за замовчуванням (`theme_provider`: dark лише якщо `dark_theme`).
- Додано **`NeptunLightSurfaces`** — явні токени canvas / elevated для light-first продукту.
- Компонентний шар-аліас **`lib/design/app_kit.dart`** (`AppCard` = `NeptunCard`, тощо) + реекспорт у `design_exports.dart`.

### 2.2 Проблеми UX (продукт)

| Проблема | Дія |
|---------|-----|
| Тексти розкидані по коду | Підключити flutter gen-l10n (ARB), українська базова мова |
| Onboarding екранним PageView але з «атмосферною» анімацією | Спрощувати motion; зберегти 4 кроки: цінність → регіони → нотифікації → PRO preview |
| Чат первинний з візуальною складністю | Чат уже не перший таб — зберегти чистий messenger-стиль, правила перед першим відправленням |

### 2.3 Стани UX (обов’язкові)

Існуючі: shimmer, частина empty/error через `NeptunEmptyState` / `NeptunErrorState`.

Потрібно уніфікувати на всіх головних списках: **loading / empty / error / offline-with-stale**.

---

## 3. Performance

| Ризик | Мітигація |
|------|-----------|
| WebView repaint + рекламний рядок | Рознесено listenable у `AppShell` (реклама не перебудовує карту) |
| IndexedStack тримає всі вкладки | Прийнятно; уникати `setState` у батьках табів без потреби |
| SSE події часті (`track_update`) | HUD ігнорує дрібні оновлення для timestamp «значущого» оновлення |
| Cold start | Вже є deferred init — профілювання на low-end Android |

---

## 4. Backend / API (узагальнено)

Детально — **`docs/backend-mobile-upgrade-plan.md`**.

Ключові висновки аудиту:

- Реєстрація пристрою вже є: **`POST /api/register-device`** (`nextjs-app/src/app/api/register-device/route.ts`) з полями token, regions, device_id, platform.
- Для дорожньої карти потрібні розширення: preferences (тип загроз), тихі години, premium-прапор, окремий PATCH/DELETE — можна версіонувати під `/api/v1/devices/*` без поломки клієнта (fallback).

---

## 5. Продукт і монетизація

**Безкоштовний рівень:** жива карта, базовий радар, базові push за регіонами, участь у чаті з модераційними межами.

**PRO (цінність, не шантаж):** без реклами, розширена історія/фільтри, пріоритетні/тонкі налаштування сповіщень, «радар-преміум» блоки без блокування тривожної інформації за paywall.

---

## 6. Видалити / переписати / залишити

| Дія | Приклади |
|-----|----------|
| **Видалити** | Мертві дублікати маршрутів; невикористані «тактичні» заглушки після переходу на світлу естетику |
| **Переписати** | Великі вкладені `Navigator` там, де вже є go_router shell; god-сервіси на репозиторії |
| **Залишити** | StatefulShellRoute, SSE як джерело алармів, bridge для карти до повної native-фази |

---

## 7. Фазований план впровадження (пріоритети з брифу)

### Priority 1 (фундамент)

1. **Константи маршрутів** — зроблено (`route_paths.dart` + `AppRouter`); решта посилань у коді переводити поступово за потреби deep link.
2. **Design tokens** light-first (`NeptunLightSurfaces`, семантика `warning` = amber).
3. **App_kit** як публічний шар компонентів для нових екранів.
4. Карта: стабілізація bridge + HUD + кешування плануємо окремими PR.

### Priority 2

- Радар: **частково 2026-05-08** — зведення «що зараз по небу», швидкі фільтри типів, зв’язок з фазою SSE, людяна помилка завантаження, тести фільтра; далі — `RadarRepository` + Riverpod, глибший timeline.
- Нотифікації UI + синх розширених prefs з backend (ефірно за feature-flag).
- Onboarding-копірайт і зменшення візуального шуму.

### Priority 3

- Чат: rate limit уже частково на сервері; вирівняти report/mute UX.
- Локалізація ARB + ru/en за потреби.
- Інтеграційні тести роутера / дедупу маркерів.

### Priority 4

- Motion polish (reduce motion поважається частково — розширити).
- Експериментальні PRO-функції за remote config.

---

*Документ оновлюється при зміні архітектури або масових екранних рефакторингах.*
