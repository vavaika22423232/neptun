# Підготовка до публікації в Google Play та App Store

## Перед початком

- [ ] `flutter pub get`
- [ ] **Android:** `key.properties` створено (шлях до keystore, keyAlias, паролі)
- [ ] **iOS:** Xcode підпис налаштовано (Team, Provisioning Profile, Certificates)

---

## Google Play Console

### 1. Контент додатку
- [ ] **Рейтинг контенту** — заповнити анкету (відповіді на питання про насильство, страх тощо)
- [ ] **Цільова аудиторія** — 18+ (тривоги, війна)
- [ ] **Реклама** — «Так, додаток містить рекламу» (AdMob)
- [ ] **In-App Purchases** — Premium 150 грн

### 2. Безпека та конфіденційність
- [ ] **Політика конфіденційності:** https://neptun.in.ua/privacy
- [ ] **Data safety** — вказати зібрані дані:
  - Device ID (для push)
  - Location (опційно, для регіонів)
  - Analytics (Firebase, AdMob)
  - Немає продажу даних третім сторонам

### 3. Store listing
- [ ] **Назва:** Карта Тривог Neptun
- [ ] **Короткий опис** (80 символів)
- [ ] **Повний опис** (4000 символів)
- [ ] **Графіка:** Feature Graphic 1024×500, скріншоти 16:9 або 9:16
- [ ] **Іконка:** 512×512 PNG

### 4. Збірка Android
```bash
cd neptun_alarm_app
flutter build appbundle --release
```
Файл: `build/app/outputs/bundle/release/app-release.aab`

### 5. Завантаження
- [ ] Відкрити версію → Production / Internal testing
- [ ] Завантажити AAB
- [ ] Release notes українською
- [ ] Відправити на перевірку

---

## App Store Connect

### 1. App Information
- [ ] **Privacy Policy URL:** https://neptun.in.ua/privacy
- [ ] **Bundle ID:** com.neptunalarm.neptunAlarmApp
- [ ] **Primary Language:** Ukrainian

### 2. App Privacy (Nutrition Labels)
- [ ] **Data Types to Declare:**
  - Device ID (App functionality, Push notifications)
  - Location (App functionality, приблизне місцезнаходження)
  - Usage Data (Analytics)
  - Advertising Data (AdMob)
- [ ] **Data Linking:** Not linked to identity (або Linked, якщо є акаунт)
- [ ] **Tracking:** Yes (AdMob, ATT)

### 3. In-App Purchases
- [ ] **Product:** premium_150_uah (Non-Consumable)
- [ ] **Price:** 150 UAH
- [ ] **Localization:** українською

### 4. Store listing
- [ ] **Скріншоти:** iPhone 6.7", 6.5", 5.5"; iPad якщо підтримується
- [ ] **Опис:** українською
- [ ] **Ключові слова:** тривога, повітряна тривога, карта, Україна
- [ ] **Категорія:** Utilities або News
- [ ] **Віковий рейтинг:** 18+ (часто для тривог)

### 5. Збірка iOS
```bash
cd neptun_alarm_app
flutter clean && flutter pub get
cd ios && pod install --repo-update && cd ..
flutter build ios --release
```
Потім Xcode → Product → Archive → Distribute App → App Store Connect

### 6. Спеціальні вимоги Apple
- [ ] **App Tracking Transparency** — запит перед рекламою (вже є)
- [ ] **Background Modes** — remote-notification, fetch, audio (вже є)
- [ ] **Critical Alerts** — якщо використовується (entitlement)
- [ ] **Push Certificates** — налаштовано в Apple Developer

---

## Перевірка перед відправкою

| Android | iOS |
|---------|-----|
| `usesCleartextTraffic="false"` | App Transport Security налаштовано |
| ProGuard/R8 увімкнено | Bitcode вимкнено |
| Target SDK 34+ | iOS 13.0+ |
| AdMob testDeviceIds тільки в debug | Реальні Ad Units (не test) |
| Privacy link в додатку | Privacy link в додатку |

---

## Корисні посилання

- **Privacy:** https://neptun.in.ua/privacy
- **Terms:** https://neptun.in.ua/terms
- **Website:** https://neptun.in.ua
- **Telegram:** https://t.me/+Q0PcuV4OkuxmYjVi
