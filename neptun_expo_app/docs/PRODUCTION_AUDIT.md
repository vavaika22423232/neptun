# NEPTUN Expo App — Production Audit (May 2026)

Scope: `neptun_expo_app` (React Native Expo). Flutter app not modified.

## Executive summary

The app has a solid foundation: Expo Router, centralized theme, SSE real-time (`dataStreamService`), React Query on radar, MMKV/AsyncStorage prefs, offline banner, and parity tests for navigation/push. This pass fixes **critical navigation, purchase verification, API client, and push deduplication** bugs and adds **global error boundary, app config, logging, and QA documentation**.

**Production readiness:** ~82% — critical paths stabilized; remaining: voice chat native impl, radar/map threat endpoint consolidation, secondary screen theme migration.

### Pass 2 (latest)

| Area | Change |
|------|--------|
| Alarms API | **Fixed** — `alarmsDataService` dedupes `/api/alarms/all` for map + AppContext |
| PRO map | **Fixed** — trajectories gated; default off for free users |
| PRO chat | **Fixed** — image/voice attach requires PRO; message validation (length/spam) |
| PRO routes | **Fixed** — sleep mode + extended radar behind `ProFeatureGate` |
| Notifications | **Improved** — denied-permission + missing-token UI in Profile settings |
| Storage | **Added** — `safeStorage.ts` helpers |
| Tests | **Added** — `test:core` (pro catalog, theme mode, chat validation) |
| PRO tests | `proFeatureCatalog.ts` split for Node-safe unit tests |

---

## Phase 1 — Audit findings

### Navigation (HIGH fixed)

| Issue | Severity | Status |
|-------|----------|--------|
| Profile → `/alerts` (no route file) | HIGH | **Fixed** — `navigateToFlutterPath(RoutePaths.alerts)` |
| Widget deep links only on cold start | HIGH | **Fixed** — `Linking.addEventListener('url')` |
| Duplicate cold-start push nav (Expo + FCM) | MEDIUM | **Fixed** — `navigateInitialOnce` dedupe |
| Push/tab nav used `push` stacking tabs | MEDIUM | **Fixed** — `navigateToHref` uses `replace` for tabs |
| Hidden `regions` tab — no chrome/header | MEDIUM | **Fixed** — chrome entry for regions |
| No 404 screen | LOW | **Fixed** — `app/+not-found.tsx` |
| Dead `AppNavigator.tsx` | LOW | Open — unused, safe to archive |

### API / Backend (HIGH partial)

| Issue | Severity | Status |
|-------|----------|--------|
| `apiRequest` overwrote caller `AbortSignal` | HIGH | **Fixed** |
| Non-JSON error bodies could throw on parse | MEDIUM | **Fixed** — `safeJson` |
| Entitlement GET raw `fetch` without timeout | HIGH | **Fixed** — `apiGet` |
| Purchase verify returned true on network failure | CRITICAL | **Fixed** — returns `false` |
| No GET retry | MEDIUM | **Added** — `apiGet` one retry |
| Duplicate `/api/alarms/all` map + AppContext | HIGH | **Fixed** — `alarmsDataService` |
| Radar `/api/threats` vs map `/data` dual poll | HIGH | Open |
| Version gate fail-open on network error | MEDIUM | Open |

### Real-time (MEDIUM partial)

| Issue | Severity | Status |
|-------|----------|--------|
| Chat SSE `onError` never fired | MEDIUM | **Fixed** — `dataStreamService.onError` |
| Chat `typing` events not subscribed | MEDIUM | **Fixed** |
| Duplicate `getInitialMessage` in FCM configure | MEDIUM | **Fixed** |
| `wsCompatibleUrl` unused (no WebSocket) | INFO | By design — SSE only |

### PRO / Monetization (CRITICAL partial)

| Issue | Severity | Status |
|-------|----------|--------|
| Verify purchase grants PRO on transient failure | CRITICAL | **Fixed** |
| Restore skipped server verify | HIGH | **Partial** — verify when token present |
| `AlreadyOwned` granted PRO locally | HIGH | **Fixed** — sync entitlement first |
| Sleep mode ungated (free users block pushes) | HIGH | **Fixed** — `ProFeatureGate` on route |
| Map trajectories / radar-full ungated | HIGH | **Fixed** |
| Chat media ungated | HIGH | **Fixed** — client gate + server flag |
| Many `ProFeature` enum values unused in UI | MEDIUM | Open |

### Ads (MEDIUM open)

| Issue | Severity | Status |
|-------|----------|--------|
| `setAdFreeUntil` never called | MEDIUM | Open |
| No iOS ATT | MEDIUM | Documented |
| No banner retry | LOW | Open |
| PRO hides ads | OK | Working |

### Notifications (MEDIUM open)

| Issue | Severity | Status |
|-------|----------|--------|
| Permission denied — no explainer UI | MEDIUM | **Fixed** — Profile settings tile → system settings |
| Device register errors silent | MEDIUM | Open |
| “Connected” UI vs backend register | MEDIUM | Open |
| FCM + Expo cold start dedupe | MEDIUM | **Fixed** |

### Theme (MEDIUM open)

| Issue | Severity | Status |
|-------|----------|--------|
| Chat bubble black text | HIGH | **Fixed** (prior session) |
| Module-level `StyleSheet` frozen colors | MEDIUM | Partial — many chat sub-screens remain |
| `SleepModeScreen` uses legacy `palette` | LOW | Open |

### Chat (MEDIUM open)

| Issue | Severity | Status |
|-------|----------|--------|
| Voice recording/playback stub | HIGH | Open — requires dev client + native audio |
| SSE reconnect + 12s/55s polling fallback | OK | Working |
| Duplicate message guard on SSE | OK | `applySsePayloadToMessages` |

### Map / Radar (functional, optimize later)

- Map: live SSE + 30s ETag polling, malformed coords filtered in parsers
- Radar: React Query + SSE alarm patch, timeline tests exist
- Open: duplicate events, shared alarm cache, performance on many markers

### Storage

- MMKV with AsyncStorage hydrate — OK
- JSON parse protection in `persistentStorage.getStringList` — OK
- Recommend: central `safeStorageGetJson` helper (open)

### Performance

- Radar uses React Query; map uses intervals — OK for v1
- Open: memoize heavy feed cards, FlashList migration for chat

### Crash risks

- Native module probes (`lazyExpoNative`, `lazyGoogleMobileAds`) — OK pattern
- **Added** global `AppErrorBoundary`

---

## Phase 2–3 — Implemented global systems

| System | File |
|--------|------|
| Error boundary | `src/components/AppErrorBoundary.tsx` |
| API client (typed errors, timeout, retry GET) | `src/services/apiClient.ts` |
| App config | `src/config/appConfig.ts` |
| Internal logging | `src/core/logging/appLogger.ts` |
| Navigation helper | `src/core/navigation/navigate.ts` |
| Network banner | `src/components/OfflineBanner.tsx` (existing) |
| 404 route | `app/+not-found.tsx` |

---

## Phase 5 — Manual QA checklist

1. [ ] Fresh install → onboarding → regions → notifications prompt
2. [ ] App restart preserves theme + region selection
3. [ ] Offline launch → offline banner, cached radar/map where available
4. [ ] Slow internet → API timeout messages, no white screen
5. [ ] Notification permission denied → settings path still usable
6. [ ] Permission granted → token registered (check Profile diagnostics)
7. [ ] Light / dark / system theme on Map, Radar, Chat, Profile
8. [ ] Map marker tap → detail sheet
9. [ ] Radar event → details → open on map
10. [ ] Chat send text / handle send failure
11. [ ] Profile → Regions (must open `/(tabs)/regions`, not 404)
12. [ ] PRO user — no ads, gated screens unlock
13. [ ] Non-PRO — paywall on history/analytics/heatmap/sleep mode
14. [ ] Ad load failure — app usable without banner
15. [ ] Notification tap → correct tab (single navigation)
16. [ ] `neptun://alarm?open=radar` with app in foreground
17. [ ] Background → foreground → SSE reconnect
18. [ ] Android physical device
19. [ ] iOS physical device + IAP restore
20. [ ] Purchase cancel / network error does not grant PRO

### Automated tests (run locally)

```bash
cd neptun_expo_app
npm run typecheck
npm run test:navigation
npm run test:api
npm run test:radar
npm run test:notifications
```

---

## Remaining risks (prioritized)

1. **PRO gating drift** — trajectories, extended radar, chat media not enforced client-side
2. **Voice chat stub** — hide or ship native `expo-audio` implementation
3. **Duplicate network polling** — consolidate alarms/threats fetches
4. **Secondary screens theme debt** — frozen `StyleSheet` with `chat.text` at module scope
5. **iOS ATT** before personalized ads production release
6. **Version gate fail-open** — product decision for offline installs

---

## Files changed (this pass)

- `src/services/apiClient.ts` — rewrite
- `src/services/apiClient.test.ts` — new
- `src/services/purchaseService.ts`
- `src/services/dataStreamService.ts`
- `src/services/chatSseService.ts`
- `src/services/notificationService.ts`
- `src/features/notifications/services/fcmMessagingService.ts`
- `src/components/AppBootstrapGate.tsx`
- `src/components/AppErrorBoundary.tsx` — new
- `src/core/navigation/navigate.ts` — new
- `src/core/logging/appLogger.ts` — new
- `src/config/appConfig.ts` — new
- `src/screens/ProfileScreen.tsx`
- `app/_layout.tsx`
- `app/+not-found.tsx` — new
- `app/sleep-mode.tsx`
- `app/(tabs)/_layout.tsx`
- `docs/PRODUCTION_AUDIT.md` — new
