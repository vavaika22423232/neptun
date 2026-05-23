# Firebase Analytics (Phase 4)

Mirrors Flutter `FirebaseAnalytics` in `main.dart` and `open_neptun_telegram.dart`.

## Features

- **Screen views:** `useAnalyticsScreenTracking()` in `AppBootstrapGate` (Expo Router `pathname`)
- **Telegram CTA:** `openNeptunTelegramChannel(source)` → event `telegram_cta_tap` with `source` param
- **Lazy load:** `analyticsService` — no crash if native module missing (rebuild required)

## Native setup

Already included in `app.json` plugins:

```json
"@react-native-firebase/app",
"@react-native-firebase/analytics",
"@react-native-firebase/messaging"
```

Uses the same `google-services.json` / `GoogleService-Info.plist` as FCM.

Rebuild after adding analytics:

```bash
cd neptun_expo_app
npx expo run:ios --device
```

## Sources for `telegram_cta_tap`

| `source` | UI |
|----------|-----|
| `app_bar` | Shell chrome Telegram row |
| `radar_banner` | `RadarTelegramInlineRow` |
| `profile` | Profile → Telegram канал |
