# iOS Configuration Summary

## Що налаштовано:

### 1. Info.plist
- ✅ 40+ SKAdNetwork ідентифікаторів для реклами
- ✅ App Transport Security з довіреними доменами
- ✅ Дозволи геолокації (WhenInUse, Always)
- ✅ Background Modes (fetch, remote-notification, processing)
- ✅ Privacy descriptions (tracking, location)
- ✅ Time Sensitive notifications
- ✅ Critical Alerts

### 2. Podfile
- ✅ iOS 13.0 minimum deployment target
- ✅ Bitcode disabled (менший розмір)
- ✅ Оптимізація розміру в Release
- ✅ Modular headers
- ✅ M1 Mac simulator fix

### 3. AppDelegate.swift
- ✅ Background Tasks API
- ✅ Method Channel для Flutter (ua.neptun.app/ios)
- ✅ Haptic Feedback (light, medium, heavy, success, warning, error)
- ✅ Badge count management
- ✅ FCM token handling
- ✅ Provisional notifications
- ✅ Foreground notification display

### 4. Entitlements
- ✅ aps-environment (development/production)
- ✅ Critical Alerts
- ✅ Time Sensitive notifications

### 5. Flutter Services (iOS support)
- ✅ AdService - test ads for iOS (TODO: create real ad units)
- ✅ NotificationService - повна iOS підтримка
- ✅ PurchaseService - in_app_purchase працює на обох платформах
- ✅ ReviewService - App Store ID для iOS
- ✅ TtsService - iOS audio category налаштований
- ✅ AlarmTrackingService - працює на обох платформах
- ✅ BlackoutService - працює на обох платформах

### 6. Нові файли
- ✅ `lib/services/ios_platform_service.dart` - haptics, badges
- ✅ `lib/widgets/ios_widgets.dart` - Cupertino widgets

## TODO перед публікацією в App Store:

1. **Створити iOS Ad Units в AdMob Console:**
   - App Open Ad
   - Banner Ad
   - Rewarded Ad

2. **Після публікації в App Store:**
   - Оновити App Store ID в `review_service.dart`

3. **В App Store Connect:**
   - Налаштувати In-App Purchases (premium_150_uah)
   - Завантажити скріншоти для iPhone/iPad
   - Заповнити App Privacy questionnaire

4. **Apple Developer:**
   - Запросити Critical Alerts entitlement (якщо потрібно)
   - Налаштувати Push Certificates

## Збірка для App Store:

```bash
./build_ios_release.sh 1.4.1 25
```

Або вручну:
```bash
cd neptun_alarm_app
flutter clean
flutter pub get
cd ios
pod install --repo-update
cd ..
flutter build ios --release
```

Потім відкрити Xcode:
```bash
open ios/Runner.xcworkspace
```

І зробити Archive → Distribute App → App Store Connect.
