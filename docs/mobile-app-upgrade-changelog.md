# Changelog: mobile app upgrade (NEPTUN)

## 2026-05-08 — Радар: RadarRepository + Riverpod

### Поведінка

- При збої мережі **збережені маркери** з останнього успішного запиту; повтор з [Refresh] / таймером 30 с.
- Хвилини історії з **одного джерела** — [ProGate.mapThreatHistoryMinutes] після `watch` [premiumProvider].

### Код

- `lib/features/radar/domain/radar_snapshot.dart`, `lib/features/radar/data/radar_repository.dart`.
- `lib/features/radar/presentation/providers/radar_feed_provider.dart` — `radarFeedProvider`, `radarRepositoryProvider`, `radarMapHistoryMinutesProvider`.
- `lib/pages/tabs/radar_tab.dart` → `ConsumerStatefulWidget` (залишено лише локальний UI: панель вкладок, фільтри, Telegram-банер).
- Експорт у `lib/core/providers/providers.dart`.

### Тести

- `test/radar_repository_test.dart`.

---

## 2026-05-08 — Радар: аналітичний блок, фільтри, маршрути

### Зміни для користувача

- Вкладка **Радар → Стрічка**: блок **«Що зараз по небу»** — кількість подій у вікні історії (як у FREE/PRO), топ-локації з останніх маркерів, кількість областей із активною тривогою з API, індикатор фази **SSE** («На звʼязку», повторне підключення тощо).
- **Швидкі фільтри** стрічки: Усі · БПЛА · Ракети · Авіація · Тривоги · Вибухи (мапінг на `threatType` із бекенду).
- Спокійне підсвічування, якщо у вікні є **ракетна/ балістична** активність (без «кіберпафосу», лише інформативна рамка).
- Дії **Розширений радар** (`/radar-full`) та **PRO** з цього ж блоку; без блокування базової стрічки.
- Помилка завантаження стрічки: людзяний текст без «техносміття» в релізі; деталь сирої помилки лише в **debug** у банері.
- Порожній стан, якщо фільтр відсік усі події: окреме повідомлення.

### Архітектура / код

- `lib/core/router/route_paths.dart` — константи шляхів; `app_router.dart` переведено на них.
- Домен: `lib/features/radar/domain/radar_quick_filter.dart`.
- UI: `lib/features/radar/presentation/widgets/radar_overview_strip.dart`.
- `radar_feed_logic.dart` — `radarMarkerTimestamp`, фільтр у `buildSortedRadarFeedEntries`.
- `NeptunErrorBanner` — опційне поле `detail` (другий рядок).
- Навігація на `RoutePaths` у мапі / профілі: `map_situation_status_strip`, `map_threat_marker_sheet`, `profile_tab`.

### Тести

- `test/radar_quick_filter_test.dart` — мапінг категорій фільтра.

### Перевірки

- `dart analyze`, `flutter test`.

### Що далі

- Кеш `RadarSnapshot` на диск для офлайну / stale banner.
- Локалізація рядків Радару через ARB.

---

## 2026-05-08 — Аудит дорожньої карти, дизайн-система light-first, фікс роутера

### Документація

- `docs/mobile-app-upgrade-audit.md` — розширено повним аудитом по архітектурі, UX, performance, backend-зв’язках і фазовому плану (Priority 1–4).
- `docs/backend-mobile-upgrade-plan.md` — додано секцію **інвентарю** наявних API в `nextjs-app`.

### Продукт / дизайн-система

- `NeptunLightSurfaces` — токени поверхонь для світлої теми (canvas, elevated, border, muted foreground).
- `NeptunStatus.warning` — семантичний amber замість нейтрального stone (спокійне попередження).
- `lib/design/app_kit.dart` — продуктові аліаси (`AppCard`, `AppButton`, …) + реекспорт у `design_exports.dart`.

### Роутинг

- Прибрано **дубльований** маршрут `/alerts` у `app_router.dart` (GoRouter: один `path` — одне визначення).

### Перевірки

- `dart analyze` / `flutter test` (після змін).

---

## 2026-05-07 — Карта: WebView ⇄ Flutter bridge + нативний bottom sheet загрози

### Зміни для користувача

- Тап по **маркеру загрози** в embedded карті: якщо встановлений канал **`NeptunApp`**, застосунок відкриває **нативний** bottom sheet замість Leaflet / MapLibre HTML popup (**адмін-прапорець** лишає HTML popup із діями модерації).
- У sheet: тип, статус (**активне / приблизно / застаріле** через `track_state` / час), місце / напрям (траєкторія), час, упевненість, дії **Радар**, **Сповіщення**, **Поділитись**.
- Сервер **`neptun.in.ua`** має бути оновлений разом із застосунком інакше тап показує **старий HTML popup** (зворотна сумісність).

### Файли

| Шар | Файл |
|-----|------|
| Next.js | `nextjs-app/src/lib/map/flutter-app-bridge.ts` |
| Next.js | `nextjs-app/src/components/Map/MapLibreContainer.tsx` |
| Next.js | `nextjs-app/src/components/Map/MapContainer.tsx` |
| Flutter | `neptun_alarm_app/lib/features/map/presentation/widgets/map_threat_marker_sheet.dart` |
| Flutter | `neptun_alarm_app/lib/pages/tabs/map_tab.dart` |

### Перевірки

- Flutter: `dart analyze`, `flutter test`.
- Next.js на змінені файли: `npx eslint …` — OK.

### Ризик / деплой

- **Спільний реліз** web + mobile бажаний (bridge JS на сайті не активний без Flutter; Flutter без сайту лише попап у WebView).

---

## 2026-05-07 — Карта: HUD «Ситуація зараз» + експорт стану живого каналу

### Зміни для користувача

- Поверх **WebView карти**: спокійна панель **«Ситуація зараз»** — статус зв’язку / каналу оновлень, відносний час останнього **значущого** оновлення з SSE (alarm / маркери, **без** частих `track_update`).
- Об’єднано з **effective online** (`OfflineBanner`): при відсутності мережі або недоступному API текст пояснює, що карта може бути неактуальною.
- Кнопка **фільтрів** відкриває **`/radar-full`** (розширений радар).

### Файли

| Файл | Дія |
|------|-----|
| `neptun_alarm_app/lib/features/map/domain/map_realtime_link_status.dart` | Новий тип фаз SSE + timestamp |
| `neptun_alarm_app/lib/features/map/presentation/widgets/map_situation_status_strip.dart` | Віджет HUD |
| `neptun_alarm_app/lib/services/data_stream_service.dart` | `mapRealtimeLink` (`ValueNotifier`), оновлення фаз та refresh |
| `neptun_alarm_app/lib/pages/tabs/map_tab.dart` | HUD поверх шару завантаження / помилки |

### Що лишилось (карта)

- Кеш останніх загроз у Flutter-шарі (окремий таймінг від native_map).
- Локалізація рядків HUD / sheet через ARB.

### Перевірки

- `dart analyze`, `flutter test` — OK.

---

## 2026-05-07 — Навігація: 4 вкладки, регіони всередині «Радар»

### Зміни для користувача

- Нижня панель: **Карта · Радар · Чат · Профіль** (без окремої п’ятої вкладки «Регіони»).
- На екрані **Радар** з’явився перемикач **«Стрічка»** / **«Регіони»** (сповіщення та вибір областей).
- Старе посилання **`/regions`** перенаправляє на **`/radar?view=regions`**.
- Додано повноекранний маршрут **`/alerts`** з повним `Scaffold` для вибору регіонів (deep link / майбутні інтеграції).

### Файли

| Файл | Дія |
|------|-----|
| `neptun_alarm_app/lib/core/router/app_router.dart` | Редірект `/regions`, маршрут `/alerts`, видалено shell-гілку `/regions`, 4 `StatefulShellBranch` |
| `neptun_alarm_app/lib/pages/app_shell.dart` | 4 destination, заголовки/іконки, `showChatActions` для індексу **2** |
| `neptun_alarm_app/lib/services/ad_service.dart` | Пропуск інтерстиціалу при вході в чат: індекс **2** |
| `neptun_alarm_app/lib/pages/tabs/radar_tab.dart` | `SegmentedButton` + `IndexedStack`, вбудований `AlertsPage` |
| `neptun_alarm_app/lib/pages/messages_page.dart` | Параметр `embedded` для тіла без другого `Scaffold` |
| `neptun_alarm_app/lib/pages/tabs/profile_tab.dart` | `go('/radar?view=regions')`, оновлений коментар |
| `docs/mobile-app-upgrade-audit.md` | Новий |
| `docs/backend-mobile-upgrade-plan.md` | Новий |
| `docs/mobile-app-upgrade-changelog.md` | Новий |

### Видалено / поведінка

- Окрема вкладка **«Регіони»** з bottom nav.

### Backend changes

- Не обов’язкові для цього коміту. Рекомендації — у `docs/backend-mobile-upgrade-plan.md`.

### Що лишилось зробити (коротко)

- Повна дизайн-система **App\*** / локалізація ARB.
- Карта: bottom sheet загрози, bridge з WebView, кеш маркерів.
- Чат: серверна модерація та узгоджені ендпоінти.
- Тести: router redirects, `AlertsPage` embedded vs fullscreen.

### Ризики

- Закладки користувачів на **`/regions`**: поведінка змінена на редірект (очікувано).
- Будь-який **хардкод індексу таба** поза оновленими файлами потребує ручної перевірки (пошук `currentIndex ==` / `goBranch`).

### Перевірки

- `dart analyze` (neptun_alarm_app): **без зауважень**.
