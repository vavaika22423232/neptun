# NEPTUN Monetization — Environment & Store Setup

## Required env (backend `nextjs-app`)

| Variable | Purpose |
|----------|---------|
| `REDIS_URL` | Entitlements, rules, alert history, dedupe |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON for Play Developer API |
| `GOOGLE_PLAY_PACKAGE_NAME` | Default: `com.neptunalarm.neptun_alarm_app` |
| `APPLE_SHARED_SECRET` | App Store receipt verify (legacy) + subscriptions |
| `ALARM_API_KEY` | Ukraine Alarm API (history ingestion) |
| `FIREBASE_CREDENTIALS` or `FIREBASE_CREDENTIALS_FILE` | FCM (optional push gate) |
| `DATA_DIR` | Device registry for FCM (`/data` on server) |
| `NEPTUN_POSTGRES_URL` | Optional: apply `migrations/001_monetization_platform.sql` |

## Feature flags (backend)

Set to `false` to disable remotely via `/api/v1/config/monetization`:

- `MONETIZATION_ENABLE_PAYWALL`
- `MONETIZATION_ENABLE_PRO_PLUS`
- `MONETIZATION_ENABLE_MAX`
- `MONETIZATION_ENABLE_SMART_NOTIFICATIONS`
- `MONETIZATION_ENABLE_MY_RADAR`
- `MONETIZATION_ENABLE_HISTORY`
- `MONETIZATION_ENABLE_TELEGRAM_ADMIN`
- `MONETIZATION_ENABLE_REWARDED`

## Google Play Console

Create **subscriptions** (not one-time):

1. `neptun_pro_monthly_69` — 69 UAH/month  
2. `neptun_pro_plus_monthly_129` — 129 UAH/month  
3. `neptun_max_monthly_199` — 199 UAH/month  

Keep legacy **in-app** products for restore:

- `premium_150_uah` (lifetime)

Enable **Google Play Android Developer API** for the service account and link Play Console.

## App Store Connect

Same product IDs as subscriptions. Configure Shared Secret for receipt validation.

Legacy: `premium_150_uah` non-consumable / lifetime if still sold.

## Client verify flow

1. User purchases → `purchaseService` gets token  
2. `POST /api/v1/purchases/google/verify` or `apple/verify` with `deviceId`  
3. Backend verifies with store API → Redis entitlement  
4. `GET /api/v1/me/entitlements` → UI + `adService.syncAdsFromEntitlements`

## Without credentials

Verification returns `misconfigured` / `transient` — **no PRO is granted**. Users keep cached entitlements until expiry only if previously verified.
