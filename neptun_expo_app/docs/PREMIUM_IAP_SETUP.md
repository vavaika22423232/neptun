# Premium IAP (expo-iap)

Native in-app purchases mirror Flutter `PurchaseService` + `premium_provider.dart`.

## Product IDs

| SKU | Type |
|-----|------|
| `premium_150_uah` | One-time PRO (default paywall CTA) |
| `pro_monthly` | Subscription (optional) |
| Legacy: `premium_100_uah`, `premium`, `com.neptunalarm.premium` | Restore only |

## Server APIs

- `POST /api/verify-purchase` — receipt validation after purchase
- `GET/POST /api/premium/entitlement` — device entitlement sync

## Dev client rebuild (required)

`expo-iap` is a native module. After adding it:

```bash
cd neptun_expo_app
npx expo prebuild --clean
npx expo run:ios    # or eas build --profile development
npx expo run:android
```

Expo Go does **not** support IAP. Use a development build.

## Testing

- Use a **physical device** and sandbox / license-test accounts.
- Configure products in App Store Connect and Google Play Console with the SKUs above.
- Debug PRO without store: `EXPO_PUBLIC_DEBUG_PRO=true` in `.env` (dev only).

## Code map

| Flutter | Expo |
|---------|------|
| `purchase_service.dart` | `src/services/purchaseService.ts` |
| `premium_provider.dart` | `src/features/premium/hooks/usePremiumStore.ts` |
| `premium_paywall_screen.dart` | `src/screens/PremiumScreen.tsx` |
| StoreKit / Play Billing | `src/features/premium/services/nativeIap.ts` |
