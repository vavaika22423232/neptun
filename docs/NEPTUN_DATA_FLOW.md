# Neptun: потік даних карти

Один екран для орієнтації в репозиторії. Деталі в коментарях до файлів.

## Telegram → сервер

1. **Python worker** (поза цим репо або в `nextjs-app/worker`) читає канали, парсить текст, геокодує, формує JSON маркера. Бажано: стабільний **`track_id`** на один фізичний рух/хвилю; **`observations[]`** поповнювати кожним підтвердженим пунктом з часом (не лише останню точку); **`speed_kmh`** узгоджувати з типом загрози (сервер усе одно клампить до профілю руху).
2. **POST `/api/ingest`** (`nextjs-app/src/app/api/ingest/route.ts`) — Zod/валідація, `normalizeAirBalloonThreatType`, **`normalizeIngestMotionFields`** (кламп `speed_kmh`), `validateIngestMarker` → `normalizeIngestMarkerRegionCoords`, `normalizeDeclaredNonUaOriginCoords`. **PATCH** ingest також прогоняє **`normalizeIngestMotionPatch`** для оновлень швидкості.
3. **`tracked-target-store.ts`** — RAM + Redis; V3 Track-Only engine (`TargetTrackerEngine`); `ingestMarkerEvidence`; SSE `track_update`.

## Публічна карта

4. **`marker-publication.ts`** — єдине місце для правил «чи показувати сиру строку на карті» (`markerPassesPublicMapRawFilter`) та «чи слати в SSE при ingest» (`ingestShouldBroadcastMarker`). Опційно **`minConfidenceUav`** у `admin_settings.json` — нижчий поріг саме для класу БПЛА.
5. **`build-markers.ts`** — фільтр через `markerPassesPublicMapRawFilter`, дедуп, `computeMarkerDisplayPolicy`, сортування.
6. **GET `/api/data`** — збирає `buildMarkers` і віддає клієнтам / Flutter.

## Спостережуваність

7. **GET `/api/health`** — `pipeline.regionMismatchSnaps`, `pipeline.foreignOriginFixes` (лічильники на процес Node).

## Де правити політику

- Поріг confidence: `admin/data.ts`, адмін UI / `admin_settings.json`.
- Гео-узгодженість області: `ukraine-oblast-validate.ts`.
- Закордонний origin vs координати в UA: `declared-non-ua-origin-normalize.ts`.
- Просторова кореляція (fusion): `tracked-target-store.ts`, `TargetTrackerEngine`.
