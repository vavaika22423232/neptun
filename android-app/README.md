# 🚀 NEPTUN Alarm Map - Android Application

Android додаток для відстеження повітряних тривог та військових загроз в Україні в реальному часі.

## 📱 Особливості

- ✅ Інтеграція з NEPTUN API (neptun.onrender.com)
- ✅ Google Maps з маркерами подій
- ✅ Автоматичне оновлення кожні 30 секунд
- ✅ Dark theme (NEPTUN design)
- ✅ Kotlin + Jetpack Compose
- ✅ Material Design 3
- ✅ MVVM Architecture

## 🛠 Технології

- **Kotlin** - основна мова
- **Jetpack Compose** - сучасний UI framework
- **Google Maps SDK** - відображення карти
- **Retrofit** - HTTP клієнт для API
- **Coroutines** - асинхронність
- **ViewModel** - управління станом
- **Material Design 3** - дизайн система

## 📦 Структура проекту

```
android-app/
├── app/
│   ├── src/
│   │   └── main/
│   │       ├── java/com/neptun/alarmmap/
│   │       │   ├── MainActivity.kt
│   │       │   ├── NeptunApplication.kt
│   │       │   ├── data/
│   │       │   │   ├── api/
│   │       │   │   │   ├── NeptunApiService.kt
│   │       │   │   │   └── RetrofitClient.kt
│   │       │   │   ├── model/
│   │       │   │   │   └── Models.kt
│   │       │   │   └── repository/
│   │       │   │       └── AlarmRepository.kt
│   │       │   └── ui/
│   │       │       ├── screens/
│   │       │       │   └── MapScreen.kt
│   │       │       ├── theme/
│   │       │       │   ├── Color.kt
│   │       │       │   ├── Theme.kt
│   │       │       │   └── Type.kt
│   │       │       └── viewmodel/
│   │       │           └── MapViewModel.kt
│   │       ├── res/
│   │       │   ├── values/
│   │       │   │   ├── colors.xml
│   │       │   │   ├── strings.xml
│   │       │   │   └── themes.xml
│   │       │   └── mipmap/ (icons)
│   │       └── AndroidManifest.xml
│   └── build.gradle.kts
├── build.gradle.kts
└── settings.gradle.kts
```

## ⚙️ Налаштування

### 1. Встановіть Android Studio
Завантажте і встановіть [Android Studio Hedgehog](https://developer.android.com/studio)

### 2. Отримайте Google Maps API Key

1. Перейдіть на [Google Cloud Console](https://console.cloud.google.com/)
2. Створіть новий проект або виберіть існуючий
3. Увімкніть **Maps SDK for Android**
4. Створіть API ключ в розділі "Credentials"
5. Обмежте ключ для Android apps

### 3. Додайте API ключ

Створіть файл `local.properties` в корені проекту:

```properties
MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY_HERE
```

### 4. Відкрийте проект

1. Відкрийте Android Studio
2. File → Open → виберіть папку `android-app`
3. Дочекайтеся sync проекту

### 5. Запустіть додаток

1. Підключіть Android пристрій або запустіть емулятор
2. Натисніть Run ▶️ в Android Studio
3. Виберіть пристрій для запуску

## 🌐 API Endpoint

Додаток підключається до:
```
https://neptun.onrender.com/api/events
```

**Формат відповіді:**
```json
{
  "events": [
    {
      "id": "evt_123",
      "lat": 50.45,
      "lng": 30.52,
      "text": "Загроза ракетної атаки",
      "type": "ракета",
      "source": "@war_monitor",
      "ts": "2025-11-13T12:00:00",
      "expire": 1699876800
    }
  ],
  "active_alarms": [
    {
      "region": "Київська область",
      "active": true,
      "start_ts": "2025-11-13T11:30:00"
    }
  ]
}
```

## 🎨 Дизайн

### Кольорова схема NEPTUN:
- **Primary Blue**: `#3B82F6`
- **Cyan**: `#06B6D4`
- **Dark Background**: `#0F172A`
- **Dark Surface**: `#1E293B`

### Типи маркерів:
- 🔴 **Червоний** - ракетна загроза
- 🟠 **Оранжевий** - БПЛА
- 🟡 **Жовтий** - авіація
- 🟣 **Фіолетовий** - артилерія
- 🌹 **Рожевий** - вибухи
- 🔵 **Синій** - інші події

## 📲 Функціонал

### Реалізовано ✅
- [x] Відображення карти України
- [x] Маркери подій з API
- [x] Автоматичне оновлення (30 сек)
- [x] Підрахунок активних тривог
- [x] Pull-to-refresh
- [x] Обробка помилок
- [x] Dark theme
- [x] Loading states

### Планується 🚧
- [ ] Push-повідомлення про тривоги
- [ ] Фільтри за типом події
- [ ] Історія подій
- [ ] Збереження в локальну БД
- [ ] Offline режим
- [ ] Власна локація користувача
- [ ] Детальна інформація про подію
- [ ] Налаштування радіусу сповіщень

## 🔧 Troubleshooting

### Google Maps не відображається
1. Перевірте `MAPS_API_KEY` в `local.properties`
2. Перевірте що Maps SDK for Android увімкнено в Google Cloud Console
3. Перевірте SHA-1 fingerprint в Google Cloud Console

### API помилка
1. Перевірте інтернет з'єднання
2. Переконайтесь що https://neptun.onrender.com доступний
3. Перевірте логи: `adb logcat | grep Neptun`

### Build помилка
1. File → Invalidate Caches → Invalidate and Restart
2. Очистіть build: `./gradlew clean`
3. Перевірте версію Kotlin в `build.gradle.kts`

## 📝 Вимоги

- **Android Studio** Hedgehog або новіше
- **JDK** 8 або новіше
- **Android SDK** 34
- **Min Android Version** 7.0 (API 24)
- **Target Android Version** 14 (API 34)

## 🚀 Build для Production

```bash
# Debug APK
./gradlew assembleDebug

# Release APK (потрібен keystore)
./gradlew assembleRelease

# Android App Bundle для Google Play
./gradlew bundleRelease
```

## 📄 Ліцензія

Проект NEPTUN - моніторинг повітряних тривог України.

## 👨‍💻 Розробник

Інтеграція з основним веб-додатком NEPTUN (neptun.onrender.com)

## 🔗 Корисні посилання

- [NEPTUN Web App](https://neptun.onrender.com)
- [Android Developers](https://developer.android.com)
- [Jetpack Compose](https://developer.android.com/jetpack/compose)
- [Google Maps Android SDK](https://developers.google.com/maps/documentation/android-sdk)
- [Material Design 3](https://m3.material.io)

---

Made with ❤️ for Ukraine 🇺🇦
