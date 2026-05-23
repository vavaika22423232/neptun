# Development client (native modules)

The Expo app uses **custom native modules** that are **not** in Expo Go. After adding or updating any of these, rebuild the iOS/Android binary:

| Module | Package | Used for |
|--------|---------|----------|
| FCM | `@react-native-firebase/messaging` | Push, topics, background handler |
| Analytics | `@react-native-firebase/analytics` | Screen / event tracking |
| AdMob | `react-native-google-mobile-ads` | Banner + app-open ads |
| MapLibre | `@rnmapbox/maps` | Native map (`EXPO_PUBLIC_MAP_ENGINE=native`) |
| IAP | `expo-iap` | Premium purchase / restore |
| Speech | `expo-speech` | Alert TTS |
| Haptics | `expo-haptics` | Threat alert vibration |
| Store review | `expo-store-review` | In-app review prompt |
| Audio | `expo-audio` | Chat voice record/playback |
| Location | `expo-location` | Shelters nearby search (GPS) |

## Rebuild

```bash
cd neptun_expo_app
npm install
npx expo prebuild --clean
npx expo run:ios --device
# or
npx expo run:android
```

Start Metro with the dev client (not Expo Go):

```bash
npx expo start --dev-client
```

## JS-only reload vs native rebuild

| Change | Action |
|--------|--------|
| TypeScript / React UI | Reload Metro (`r`) |
| New npm native dependency | **prebuild + run:ios/android** |
| `app.json` plugins / permissions | **prebuild + run:ios/android** |
| Firebase / AdMob config files | Rebuild + verify plist/json in native project |

## Graceful degradation

If the binary is stale, the app **must not crash**. Native probes live in:

- `src/utils/nativeModuleGuard.ts` — TurboModules (AdMob, Firebase)
- `src/utils/lazyExpoNative.ts` — Expo Speech, Haptics, Store Review
- `src/utils/lazyGoogleMobileAds.ts` — AdMob JS entry (after native probe)

Missing modules disable that feature until you rebuild.

## Credentials

- `google-services.json` (Android) and `GoogleService-Info.plist` (iOS) in `neptun_expo_app/`
- `EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN` for native MapLibre
- See also: `docs/PUSH_FCM_SETUP.md`, `docs/ADMOB_SETUP.md`, `docs/MAP_NATIVE_ENGINE.md`
