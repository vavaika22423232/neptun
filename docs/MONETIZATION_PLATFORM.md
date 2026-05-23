# NEPTUN Monetization Platform

## 1. What existed in the project

| Layer | Before |
|-------|--------|
| **Mobile** | Expo app (`neptun_expo_app`), binary Free/PRO, lifetime IAP `premium_150_uah`, stub `pro_monthly`, `purchaseService`, `adService`, `ProFeatureGate` on some screens |
| **Backend** | Next.js (`nextjs-app`), Redis entitlement hash per `deviceId`, `/api/verify-purchase`, `/api/premium/entitlement`, Google **one-time** product API only |
| **DB** | No SQL migrations; optional PostgreSQL for admin tracks only |
| **Push** | FCM + `devices.json`, region topics — not plan-aware rules engine |

## 2. Architecture implemented

```
Mobile (Expo)
  entitlementsService ──► GET /api/v1/me/entitlements
  purchaseService     ──► verify + legacy /api/premium/entitlement
  FeatureGate         ──► minPlan: pro | pro_plus | max
  PremiumTierPaywall  ──► 3 SKUs

Backend (Next.js)
  lib/monetization/plans.ts          → feature matrix per plan
  lib/monetization/entitlement-store.ts → Redis + user bootstrap
  lib/monetization/verify-purchase.ts
  app/api/v1/*                       → new canonical APIs

Legacy routes kept working (/api/premium/entitlement, /api/verify-purchase)
```

### Plans (only these three subscriptions + legacy lifetime)

| Plan | Price | Product IDs |
|------|-------|-------------|
| PRO | 69 грн/міс | `neptun_pro_monthly_69` |
| PRO+ | 129 грн/міс | `neptun_pro_plus_monthly_129` |
| MAX | 199 грн/міс | `neptun_max_monthly_199` |
| Lifetime (legacy) | one-time | `premium_150_uah` → entitlements ≈ PRO+ |

## 3. Backend endpoints (v1)

| Method | Path | Status |
|--------|------|--------|
| POST | `/api/v1/users/bootstrap` | ✅ |
| GET | `/api/v1/me/entitlements` | ✅ |
| POST | `/api/v1/purchases/google/verify` | ✅ |
| POST | `/api/v1/purchases/apple/verify` | ✅ |
| POST | `/api/v1/purchases/restore` | ✅ |
| GET | `/api/v1/subscriptions/status` | ✅ |
| GET | `/api/v1/config/monetization` | ✅ |
| GET | `/api/v1/me` | ✅ |
| GET/POST | `/api/v1/notification-rules` | ✅ PRO gate |
| PATCH/DELETE | `/api/v1/notification-rules/:id` | ✅ |
| GET | `/api/v1/my-radar`, `/api/v1/my-radar/summary` | ✅ PRO gate |
| POST/PATCH/DELETE | `/api/v1/my-radar/locations` | ✅ |
| GET | `/api/v1/alerts/current`, `/api/v1/alerts/history`, `/api/v1/alerts/:id` | ✅ plan-enforced history |
| GET | `/api/v1/regions/:id/stats` | ✅ PRO+ analytics |
| GET | `/api/v1/reports/daily`, `weekly`, `user-summary` | ✅ |
| GET | `/api/v1/admin-tools/telegram/templates` | ✅ MAX gate |
| POST | `/api/v1/admin-tools/telegram/generate-summary` | ✅ rule-based, rate limited |

**Google subscriptions:** `purchases.subscriptionsv2.get` + legacy `subscriptions.get` for monthly SKUs.

**Planned next:** Apple subscription renewals/webhooks, FCM pipeline hook for `push-notification-gate`, rewarded ad UI, PostgreSQL mirror job.

## 4. Database migrations

File: `nextjs-app/migrations/001_monetization_platform.sql`

Tables: `monetization_users`, `monetization_devices`, `monetization_subscriptions`, `monetization_notification_rules`, `monetization_alert_events`, `monetization_my_radar_locations`, `monetization_region_stats_daily`, `monetization_feature_flags`

**Runtime today:** Redis is primary; apply SQL when `NEPTUN_POSTGRES_URL` is set (mirror job can be added next).

## 5. Mobile screens / modules

| Item | Path | Status |
|------|------|--------|
| 3-tier paywall | `PremiumTierPaywall.tsx` | ✅ |
| Entitlements service | `entitlementsService.ts` | ✅ |
| `useEntitlements` + `FeatureGate` | `features/monetization/` | ✅ |
| Monetization analytics | `monetizationAnalytics.ts` | ✅ |
| Product IDs | `iapProducts.ts` | ✅ |
| IAP load 3 subs | `nativeIap.ts` | ✅ |

| Smart Notifications | `SmartNotificationsScreen.tsx` | ✅ server rules |
| My Radar | `MyRadarScreen.tsx` | ✅ |
| History (server) | `AlarmHistoryScreen.tsx` | ✅ `/api/v1/alerts/history` |
| Telegram Admin | `TelegramAdminScreen.tsx` | ✅ MAX |

## 6. What works end-to-end now

- Server returns unified `entitlements` JSON with `plan` + `features`
- Bootstrap + sync on app start
- PRO/PRO+/MAX product IDs recognized server-side
- Legacy lifetime users keep access (mapped to PRO+ features)
- Paywall shows 3 tiers (UA copy)
- Feature gates by `minPlan` (sleep mode, radar-full, map trajectories, chat media)
- Ads still hidden via `isPremium` boolean (any paid plan)
- Telegram summaries: rule-based, no fake AI
- Notification rules API with plan limits

## 7. Requires Google / Apple credentials

| Capability | Env / setup |
|------------|-------------|
| Google one-time verify | `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_PLAY_PACKAGE_NAME` |
| Google **subscription** verify | Same + enable Play Developer API; **implement `purchases.subscriptions.get` next** |
| Apple verify | `APPLE_SHARED_SECRET`, StoreKit JWS certs |
| PostgreSQL mirror | `NEPTUN_POSTGRES_URL` |

Without credentials: verify returns `misconfigured` / `transient` — **client does not grant PRO** (fixed earlier).

## 8. Store product IDs to create

**Google Play & App Store (same IDs):**

- `neptun_pro_monthly_69`
- `neptun_pro_plus_monthly_129`
- `neptun_max_monthly_199`

**Keep for restore:** `premium_150_uah`, `premium_100_uah`, `premium`, `com.neptunalarm.premium`, `pro_monthly`

## 9. Environment variables

```bash
# Existing IAP
GOOGLE_APPLICATION_CREDENTIALS=
GOOGLE_PLAY_PACKAGE_NAME=com.neptunalarm.neptun_alarm_app
APPLE_SHARED_SECRET=

# Redis (required)
REDIS_URL=

# Optional PostgreSQL
NEPTUN_POSTGRES_URL=

# Feature flags
MONETIZATION_ENABLE_PAYWALL=true
MONETIZATION_ENABLE_PRO_PLUS=true
MONETIZATION_ENABLE_MAX=true
MONETIZATION_ENABLE_TELEGRAM_ADMIN=true
```

## 10. Pre-release testing

1. Fresh install → bootstrap → `plan: free`
2. Purchase PRO sub (sandbox) → entitlements `plan: pro`, ads off
3. Restore purchases on second device
4. Legacy lifetime user → still entitled
5. MAX user → telegram generate-summary 200; PRO user → 403
6. Notification rules: PRO max 3 rules; PRO+ max 10
7. Denied push permission UI (Profile)
8. Paywall analytics events in Firebase

## 11. Next phase

1. Google Play **subscription** verification + `expiresAt` from renewal
2. Apple subscription / StoreKit 2 renewal webhooks
3. `/api/v1/alerts/history` with server-side `historyDays` enforcement
4. Mobile: Smart Notifications, My Radar, History UI wired to v1 APIs
5. Rewarded ad-free 4h (`setAdFreeUntil` wiring)
6. Push pipeline integration with notification rules engine
7. PostgreSQL sync worker from Redis
