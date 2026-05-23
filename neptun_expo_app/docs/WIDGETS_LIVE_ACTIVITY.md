# Home widgets & iOS Live Activity

Parity with Flutter `WidgetService` and `LiveActivityService`.

## Architecture

| Layer | Path |
|-------|------|
| JS API | `src/features/widgets/services/widgetService.ts` |
| Live Activity | `src/features/widgets/services/liveActivityService.ts` |
| FCM hook | `syncPlatformWidgetsFromAlert.ts` → `alertFeedbackService` |
| Native bridge | `modules/neptun-native-bridge` (Kotlin/Swift) + `src/features/widgets/native/neptunNativeBridge.ts` (JS) |
| Android widget UI | Copied from Flutter on prebuild (`plugins/withNeptunHomeWidget.js`) |

### Data contract (unchanged from Flutter `home_widget`)

Android: `SharedPreferences` file `HomeWidgetPreferences`  
iOS: App Group `group.com.neptunalarm.neptunAlarmApp`

Keys: `widget_region`, `widget_is_alarm`, `widget_threats_count`, `widget_timer_minutes`, `widget_total_alarms`, `widget_threat_type`, `widget_drones_count`, `widget_missiles_count`, `widget_kab_count`, `widget_ballistic_count`, `widget_total_threats`, `widget_last_update`, `widget_status_text`.

Premium gating: non‑PRO users see `widget_status_text = "Придбайте Premium"` (same as Flutter).

## Setup (required for native widgets)

```bash
cd neptun_expo_app
npm install
npx expo prebuild --clean
npx expo run:ios --device   # or run:android
npx expo start --dev-client
```

`withNeptunHomeWidget` copies `NeptunWidgetProvider.kt` and layouts from `neptun_alarm_app/android` and registers the receiver in `AndroidManifest.xml`.

### iOS widget extension (manual, one-time)

The **in-app bridge** updates App Group data and reloads timelines. For the **home screen widget UI** on iOS, copy the Flutter target into Xcode after prebuild:

1. Open `ios/*.xcworkspace`
2. Add target from `neptun_alarm_app/ios/NeptunWidget/` (same bundle / app group as Flutter)
3. Enable App Group `group.com.neptunalarm.neptunAlarmApp` on app + widget extension

Live Activity uses `ActivityKit` inside `NeptunNativeBridgeModule` (iOS 16.2+), matching `LiveActivityHelper.swift`.

## Wiring

- **Radar tab:** `useRadarFeedState` → `widgetService.syncFromRadarSnapshot`
- **FCM alerts:** `triggerAlertFeedback` → widget (Android) + Live Activity (iOS)
- **IAP:** `purchaseService.savePremiumStatus` → refresh or premium-required widget state
- **Deep links:** `neptun://alarm?open=radar` (unchanged)

## Performance

Widget updates are debounced by React Query radar refetch (30s) and only run when marker/alarm counts change. Native reload is a single broadcast / `WidgetCenter.reloadAllTimelines()`.
