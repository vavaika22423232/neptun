# Flutter to React Native Migration

## Current Slice

See **`MIGRATION_ROADMAP.md`** for the full phased plan (10 phases, Dart→RN mapping, quality gates).

This Expo app is now structured as the React Native migration target for the Flutter `neptun_alarm_app`.

### Phase 1 foundation (latest)

- `src/core/navigation/` — `pushDeepLink`, `appRedirect`, `routePaths` (Flutter parity tests: `npm run test:navigation`)
- `src/core/pro/proGate.ts` — PRO feature gates
- `src/config/prefsKeys.ts` — SharedPreferences key parity
- `src/services/persistentStorage.ts` — MMKV + AsyncStorage hydrate
- `src/components/AppBootstrapGate.tsx` — onboarding redirect + `neptun://` deep links + push tap routing
- `src/features/onboarding/` + `OnboardingScreen.tsx` — 4-page flow (welcome → regions → notifications → ready), `PrefsKeys.firstLaunch`, region selection + `notificationService.updateRegions`
- `src/services/notificationService.ts` — Expo push registration skeleton
- `eas.json` — OTA channels (development / preview / production)

Migrated or corrected in this slice:

- Expo Router root and tab navigation aligned to Flutter `AppShell`.
- Shared `Dron Alerts` top chrome and 4-item tactical bottom navigation (`Карта`, `Радар`, `Чат`, `Профіль`).
- `Регіони` is no longer a primary bottom tab; it remains a routed module.
- Dark NEPTUN theme tokens, typography, cards, and shell surfaces.
- Typed API endpoints matching Flutter `ApiConfig`.
- Secure/local storage compatibility for device id, nickname, moderator secret, first launch, PRO, sleep mode, and cached map state.
- Version gate equivalent to Flutter `AppVersionGateService`.
- Sleep mode notification filtering equivalent to Flutter `SleepModeService`.
- Chat bootstrap, nickname registration, message fetch/send, SSE message application, reactions, edit/delete, reports, local block list, image upload, voice upload, and voice playback.
- Live map data service with ETag support, offline cache fallback, alarm parsing, marker parsing, ballistic region extraction, and marker counts.
- Singleton SSE hub equivalent to Flutter `DataStreamService`.
- Native MapLibre tactical map with clustered threat markers, live status HUD, trajectory lines, dark raster style, filter chips, app-state reconnect, **SSE motion interpolation** (`markerMotionEngine`), **viewport + count culling**, bearing arrows. See `docs/MAP_NATIVE_ENGINE.md`.
- Radar, regions, profile, premium, analytics, heatmap, sleep mode, WebView, moderation, and complaints screens as routed RN modules.
- Flutter map/chat icon and geo assets copied into Expo assets.
- EAS Update-ready app config with runtime API base URL and server-driven feature surface.

## Parity Matrix

| Flutter module | RN status | Required parity work |
| --- | --- | --- |
| `pages/app_shell.dart` | In progress | Shell + offline banner + engagement modals + **AdMob banner / app open** (`adService`); iOS ATT optional follow-up. |
| `pages/tabs/map_tab.dart` + map widgets | In progress | **WebView embed default** (`docs/MAP_EMBED.md`). **Native MapLibre** (`docs/MAP_NATIVE_ENGINE.md`): motion, cull, oblast/district alarms + **pulse**, trajectories. Still: offline tiles, Skia icons. |
| `pages/tabs/radar_tab.dart` + radar widgets | In progress | **Grouped threat tab** (`RadarScreen`, `useRadarFeedState`, shimmer, stale banner, PRO 30/120 min, pull-to-refresh). Legacy feed widgets kept for reference; `/radar-full` dashboard done. |
| `pages/tabs/chat_tab.dart` + chat widgets | In progress | Settings screen, image gallery, search via chrome, 7-tap moderator login, ban list; remaining: recording drag polish, chat background themes in-thread. |
| `pages/tabs/profile_tab.dart` + `settings_section.dart` | In progress | `ProfileScreen`, `SettingsSection`, `PremiumBanner`, trust/feedback routes — FCM topic subscribe + TTS playback Phase 4. |
| Premium/paywall | In progress | `expo-iap` buy/restore + paywall UI; rebuild per `docs/PREMIUM_IAP_SETUP.md`. |
| Analytics / heatmap | In progress | `PersonalAnalyticsScreen` + `HeatmapScreen` with oblast map (`AlarmHeatmapMap`); Firebase Analytics pending. |
| Notifications/background | In progress | FCM + TTS + haptics + **pending ballistic FCM** on cold start; rebuild dev client for native FCM/Analytics/Speech. |
| Localization | Not complete | User-facing copy is mixed and not centralized; needs a localization layer matching Flutter strings. |
| Home widget + Live Activity | In progress | `widgetService`, `liveActivityService`, `neptun-native-bridge`, Android prebuild copy — see `docs/WIDGETS_LIVE_ACTIVITY.md`. |
| Analytics/remote config | In progress | `analyticsService` + screen tracking + `telegram_cta_tap`; rebuild dev client for native Analytics. Remote config via `/api/app-requirements`. |

## Architecture

- `app/`: Expo Router entrypoints.
- `src/components/`: reusable design primitives.
- `src/config/`: API, links, constants, chat themes.
- `src/features/map/`: tactical map engine, live data hooks, MapLibre components, parsing utilities, Zustand state.
- `src/services/`: API client, auth, chat, SSE, storage, purchases, sleep mode, version gate.
- `src/types/`: TypeScript domain contracts mirrored from Dart models.

## Performance Notes

- Map markers are rendered as MapLibre shape sources and layers, avoiding per-marker React views.
- Clustering is enabled natively at the source layer.
- SSE `track_update` patches state in place without full refetch.
- HTTP polling remains as a low-frequency fallback and uses ETags.
- Offline cache hydration keeps the map usable when API calls fail.
- React Query is installed and configured for future server-state modules.
- The migration keeps the WebView dependency available for parity fallbacks while native MapLibre becomes the main map engine.

## Next Migration Modules

- Full push registration, topic subscriptions, and background handlers.
- Native IAP: rebuild dev client after `expo-iap` (`docs/PREMIUM_IAP_SETUP.md`).
- Full moderator/admin screens.
- Offline tile packs and culling tuned against production marker volumes.
- Firebase Analytics/Crash/Sentry parity once native credentials are available.
