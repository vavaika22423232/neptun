# Push notifications — FCM setup (Phase 4)

The RN app mirrors Flutter `NotificationService`:

- **Topics:** `region_kharkivska`, `all_regions`, … (`fcmTopicService.ts`)
- **Foreground FCM:** `FirebaseMessaging.onMessage` → filter pipeline → `expo-notifications` local display (`fcmMessagingService.ts`)
- **Background / killed:** `setBackgroundMessageHandler` registered in `index.ts` before `expo-router/entry`
- **Tap navigation:** `onMessageOpenedApp` + `getInitialMessage` → `pushDeepLink.ts`
- **Filters:** threat types, quiet hours, sleep mode (background), region ID filter, dedup (30s)
- **Backend:** `POST /api/register-device` with FCM token; `PATCH /api/devices/preferences`

## Native credentials (required for production FCM)

Firebase config files are copied from the Flutter app (same Firebase project):

- `neptun_expo_app/google-services.json` (Android)
- `neptun_expo_app/GoogleService-Info.plist` (iOS)

Referenced in `app.json` via `googleServicesFile`.

Rebuild dev client after any native plugin or credential change (`expo-speech`, `expo-haptics`, Firebase, IAP):

```bash
cd neptun_expo_app
npx expo prebuild
npx expo run:ios --device
# or
npx expo run:android
```

**Do not use Expo Go** for this app — native modules (Speech, FCM, MapLibre, IAP) require a custom dev client.

If you see `Cannot find native module 'ExpoSpeech'`, the JS bundle is newer than the installed binary; run `npx expo run:ios` again (not just `expo start`).

## Without Firebase native modules

- `expo-notifications` still handles permission, Expo push token fallback, and deep links from local notifications.
- FCM topic subscribe and foreground `onMessage` are skipped until `@react-native-firebase/messaging` is linked in a dev/production build.

## Verify

```bash
npm run test:notifications
npm run typecheck
npm start
```

1. Select regions in **Регіони** → topics persist in MMKV and subscribe via FCM.
2. With app in foreground, send a test push → local notification should appear (not silently dropped).
3. Tap notification → app opens correct tab (map / radar / chat / regions).

## Architecture

| File | Role |
|------|------|
| `index.ts` | Registers background FCM handler, then loads Expo Router |
| `registerFcmBackground.ts` | Wires `setBackgroundMessageHandler` |
| `fcmMessagingService.ts` | Foreground display + opened/initial navigation |
| `fcmMessagePipeline.ts` | Flutter-parity gating (region, threat, quiet, dedup) |
| `ttsService.ts` + `formatTtsMessage.ts` | Ukrainian TTS via `expo-speech` after alert |
| `alertFeedbackService.ts` | TTS + `expo-haptics` vibration patterns |
| `notificationService.ts` | Permissions, channels, register device, topics |
