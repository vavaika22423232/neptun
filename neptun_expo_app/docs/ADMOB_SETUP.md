# AdMob — banner + app open (Flutter `AdService` parity)

## Features

| Flutter | React Native |
|---------|----------------|
| Banner above tab bar | `AdBannerSlot` in `app/(tabs)/_layout.tsx` |
| App Open (cold start + resume) | `adService.ts` + `AppState` |
| Premium hides ads | `purchaseService` → `adService.setPremiumStatus` |
| Ad-free bonus | `PrefsKeys.adFreeUntil` |
| Session gate for cold start | `adService.markSessionActive()` from shell bootstrap |

## Unit IDs

Production IDs match Flutter `ad_service.dart`. In `__DEV__`, Google test unit IDs are used.

App IDs (in `app.json` plugin):

- Android: `ca-app-pub-1995509849440582~8995763934`
- iOS: `ca-app-pub-1995509849440582~7835319378`

## Native rebuild required

```bash
cd neptun_expo_app
npx expo prebuild
npx expo run:ios --device
# or
npx expo run:android
```

Do **not** use Expo Go — AdMob requires a custom dev client.

## iOS ATT

Flutter requests App Tracking Transparency in `main()` before ads. Add `expo-tracking-transparency` in a follow-up slice if needed for personalized ads on iOS 14+.

## Verify

1. Free user → banner appears above bottom tabs after load  
2. PRO purchase → banner disappears immediately  
3. Background app 15s+ → app open ad on resume (production rules; relaxed in `__DEV__`)
