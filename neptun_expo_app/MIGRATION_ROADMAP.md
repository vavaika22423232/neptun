# Flutter → React Native Full Migration Roadmap

**Source:** `neptun_alarm_app` (Flutter 3.10+, Riverpod, GoRouter)  
**Target:** `neptun_expo_app` (Expo 54, TypeScript, Expo Router, Zustand, React Query, MapLibre)  
**Goal:** Identical UX/behavior — engine migration, not redesign.

---

## Phase 0 — Audit (complete)

| Flutter surface | Files / systems | RN status |
|-----------------|-----------------|-----------|
| 4-tab shell | `app_shell.dart`, `TacticalNavBar` | Chrome + offline banner + presence/SSE bootstrap + sleep route; ads/battery prompt pending |
| Map (production) | WebView embed `neptun.in.ua/?embed=1` | **WebView embed default** (`EmbedMapWebView`); MapLibre via `EXPO_PUBLIC_MAP_ENGINE=native` |
| Map (native legacy) | `native_map_page.dart`, flutter_map | Partially ported in `TacticalMap.tsx` |
| Radar | `radar_tab` + feed widgets + `RadarRepository` | **Grouped tab UI** (`RadarScreen` + `useRadarFeedState`) + `ThreatDashboardScreen` (`/radar-full`) |
| Chat | `chat_tab` ~1800 LOC | ~85% — settings, gallery, chrome search, moderator 7-tap; themes/recording polish left |
| Profile hub | 15+ stack routes | **Profile tab + settings + trust/feedback routes** (FCM topics Phase 4) |
| SSE | `DataStreamService` | `dataStreamService.ts` parity |
| Push | FCM + local + channels + TTS | FCM pipeline + `expo-speech` TTS + haptics; widgets/Live Activity pending |
| IAP | `PurchaseService` + server verify | `expo-iap` + `purchaseService` + paywall buy/restore (`docs/PREMIUM_IAP_SETUP.md`) |
| Widgets / Live Activity | Android + iOS native | JS bridge + Android copy plugin; iOS widget extension manual copy (`docs/WIDGETS_LIVE_ACTIVITY.md`) |
| PRO gate | `ProGate` | `src/core/pro/proGate.ts` (this slice) |

---

## Phase 1 — Core foundation (in progress)

- [x] `prefsKeys` mirror of Flutter `PrefsKeys`
- [x] `proGate` mirror of Flutter `ProGate`
- [x] `routePaths`, `pushDeepLink`, `appRedirect` (testable)
- [x] MMKV-backed `persistentStorage` + storage adapter
- [x] `AppBootstrapGate` — first launch + `neptun://` deep links
- [x] Onboarding — `src/features/onboarding/` (4 pages, regions + push permission, mirrors Flutter first-launch flow)
- [x] `notificationService` skeleton (Expo Notifications + device register API)
- [x] `eas.json` OTA channels
- [x] Expo push register + `PATCH /api/devices/preferences` (`notificationPrefsController`)
- [x] FCM topic builder + `fcmTopicService` (`region_*` topics, unsubscribe sweep, iOS APNS retry)
- [ ] Firebase native rebuild with `google-services.json` / `GoogleService-Info.plist` (see `docs/PUSH_FCM_SETUP.md`)
- [x] Offline banner + API reachability (`OfflineBanner`, `useEffectiveOnline` — health fetch, no NetInfo native dep)
- [x] App shell bootstrap: SSE, presence ping, online counter (`TabsShell`, `useAppShellBootstrap`)
- [x] Purchase entitlement GET/POST sync + native IAP (`purchaseService.ts`, `expo-iap`)
- [x] JWT auth refresh loop (`authService` — login, refresh, revoke, `getAuthHeaders`)
- [x] `remoteConfigService` + `useRemoteConfig` (server-driven flags via `/api/app-requirements`)
- [x] `ProFeatureGate` wired to analytics / heatmap / history

---

## Phase 2 — Realtime & map engine (in progress)

| Module | Flutter | RN status |
|--------|---------|-----------|
| Map tab WebView | `map_tab.dart` | `EmbedMapWebView.tsx` + `NeptunApp` bridge |
| Status strip | `map_situation_status_strip.dart` | `MapSituationStatusStrip.tsx` |
| Threat sheet | `map_threat_marker_sheet.dart` | `MapThreatMarkerSheet.tsx` |
| Moderator embed | `ModeratorService` | `moderatorService.ts` |
| `/radar-full` route | `RoutePaths.radarFull` | `app/radar-full.tsx` |
| Daily briefing | `BriefingPage` + `BriefingService` | `BriefingScreen` + `briefingService` + morning local notif (8–10, once/day) |

| Module | Flutter | RN target |
|--------|---------|-------------|
| SSE hub | `data_stream_service.dart` | Extend typed events + link phase HUD |
| Map data | `map_data_service.dart` | `mapDataService.ts` (done) |
| Marker motion | Server `track_update` + interpolation | **Done:** `patchTrack` → explicit from/to motion → `TacticalMap` |
| Viewport cull | Flutter map bounds filter | **Done:** `onRegionDidChange` + padded bounds |
| District fills | `UkraineDistrictPaths` | **Done:** `districtGeoLoader.ts` + `npm run sync:map-geo` |
| Oblast polygons | SVG paths + GeoJSON | Wire `assets/geo/*.geojson` shape layers |
| Threat icons | `ThreatIconManager` | Skia or MapLibre symbol layers + `assets/icons/` |
| Clustering / culling | flutter_map layers | Shape-source clustering + viewport cull |
| Alarm pulse | `PulseAlarmLayer` | `useAlarmPulse` fill-opacity loop on oblast/district layers |
| Detail sheets | `threat_detail_sheet`, `region_detail_sheet` | `MapThreatMarkerSheet`, `RegionDetailSheet`, `NeptunBottomSheet` |
| Ballistic overlay | `BallisticAlertService` | `ballisticAlertService` + map overlays (embed + native) |
| Oblast GeoJSON | `ukraine_oblast_geo_loader.dart` | `oblastGeoLoader.ts` + MapLibre fill layers (native engine) |

**Performance targets:** shape sources only (no per-marker Views), 60fps camera, batch `track_update` at 10–20 Hz max to JS bridge.

---

## Phase 3 — Tab parity (UI clone)

### Map tab
- Option A: WebView embed for pixel-perfect parity with web map
- Option B: Native MapLibre (current) — match Flutter **native** map behavior
- Status strip, layer toggles, moderator embed auth, `threat_marker_tap` sheet

### Radar tab
- [x] Grouped threat cards (`radar_tab.dart`) — `RadarThreatGroupCard`, `ThreatTrackMeta` chips
- [x] Stale cache banner, shimmer loading, pull-to-refresh, 30s poll, tab-focus refresh
- [x] PRO history window (30 / 120 min), SSE `alarm_update` count patch
- [x] Dismissible Telegram inline row (`RadarTelegramInlineRow` + pref)
- [x] `/radar-full` → `ThreatDashboardScreen`
- [ ] Legacy feed path (`radar_feed_tile`, quick filters) — optional; Flutter tab no longer uses feed layout

### Chat tab
- Settings sheet, gallery, recording UX, highlight search, admin 7-tap
- [x] Voice record/playback via `expo-audio` (`useChatVoiceAudio` — replaces deprecated `expo-av`)

### Profile tab
- Notification prefs → `PATCH /api/devices/preferences`
- [x] Region picker (`RegionsScreen` / `AlertsPage`)
- [x] Medical card + emergency bag + safety tips (`SafetyScreen`)
- [x] Shelters OSM search (`SheltersScreen` + `expo-location`)
- Trust, feedback routes (done)

---

## Phase 4 — Platform systems

| System | Flutter | RN approach |
|--------|---------|-------------|
| Push | `firebase_messaging` + `flutter_local_notifications` | `expo-notifications` + FCM (EAS credentials) |
| Deep links | `push_deep_link.dart` | `pushDeepLink.ts` + Expo Linking |
| TTS | `flutter_tts` | `expo-speech` (UA voice) |
| IAP | `in_app_purchase` | `expo-iap` or `react-native-iap` + entitlement API |
| Widgets | `home_widget` | `widgetService` + `neptun-native-bridge` + `withNeptunHomeWidget` |
| Live Activity | MethodChannel | `liveActivityService` + ActivityKit in `neptun-native-bridge` |
| Ads | AdMob | `react-native-google-mobile-ads` |
| Analytics | Firebase Analytics | `@react-native-firebase/analytics` |
| Remote config | — | Firebase Remote Config + EAS env |
| Sentry | `sentry_flutter` | `@sentry/react-native` |
| Presence | `presence_service.dart` | Background task + AppState intervals |

---

## Phase 5 — OTA & server-driven config

- **EAS Update:** `eas.json` channels `preview` / `production`
- **Runtime:** `otaUpdateService.checkAndFetchOnStartup()` from `AppBootstrapGate` (configured in `app.json`)
- **Remote:** `GET /api/app-requirements` (version gate — done), feature flags JSON endpoint (future)
- **Map style:** host style JSON URL in remote config → hot swap MapLibre style

---

## Dart → RN mapping

| Flutter | React Native |
|---------|--------------|
| Riverpod | Zustand + React Query |
| GoRouter | Expo Router |
| GetIt | Module singletons / context |
| SharedPreferences | MMKV (`persistentStorage`) |
| flutter_secure_storage | expo-secure-store |
| WebView | react-native-webview |
| flutter_map | @rnmapbox/maps (MapLibre) |
| Reanimated (implicit) | react-native-reanimated |
| MethodChannel | expo-modules / native config plugins |

---

## File tree (target)

```
neptun_expo_app/
├── app/                    # Expo Router screens
├── src/
│   ├── core/
│   │   ├── navigation/     # routePaths, pushDeepLink, appRedirect
│   │   └── pro/            # proGate
│   ├── config/             # api, prefsKeys, constants, remoteConfig
│   ├── features/
│   │   ├── map/            # engine, hooks, components, motion
│   │   ├── radar/
│   │   ├── chat/
│   │   ├── notifications/
│   │   └── premium/
│   ├── components/         # design system
│   ├── hooks/
│   ├── services/           # API, SSE, storage, platform
│   ├── stores/             # Zustand (per feature)
│   └── types/
├── assets/                 # icons, geo (from Flutter)
├── eas.json
└── MIGRATION.md            # parity matrix (living doc)
```

---

## Incremental delivery order

1. Core foundation ← **current**
2. Map engine (motion, polygons, sheets, icons)
3. Radar feed clone
4. Push + deep links + region subscriptions
5. Profile + alerts + notification prefs
6. Premium IAP + server entitlement
7. Secondary screens (heatmap, history, analytics, trust, shelters…)
8. Widgets + Live Activity
9. Performance pass (memory, battery, marker volume)
10. Production EAS + store submission

---

## Setup (developers)

```bash
cd neptun_expo_app
npm install
export EXPO_PUBLIC_API_BASE_URL=https://neptun.in.ua
export EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN=<token>
npx expo prebuild   # native MapLibre
npm run ios | npm run android
npm run typecheck
```

OTA:

```bash
npx eas update --channel production --message "describe change"
```

---

## Quality gates

- `npm run typecheck` — strict TS, no `any` in new modules
- Unit tests: `pushDeepLink`, `appRedirect`, `parseThreatMarker`, `radar` filters
- Manual: 4-tab navigation, SSE reconnect, map 500+ markers, push tap routes

**Rule:** No placeholders for business logic. If Flutter has it, RN must have it before calling a phase “done”.
