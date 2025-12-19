# Firebase Push Notifications - Налаштування

## ✅ Що вже готово:

1. **Flutter додаток:**
   - Firebase Core, Messaging, Local Notifications інтегровано
   - Сторінка налаштувань з вибором 25 областей України
   - Автоматична реєстрація FCM token
   - Обробка уведомлень у foreground та background
   - 3 вкладки: Карта, Тривоги, Налаштування

2. **Backend (app.py):**
   - `/api/register-device` - реєстрація пристрою
   - `/api/update-regions` - оновлення областей
   - `/api/test-notification` - тестове уведомлення
   - Автоматична відправка при нових загрозах
   - Збереження токенів у `devices.json`

3. **Конфігурація:**
   - `google-services.json` для Android ✅
   - `GoogleService-Info.plist` для iOS ✅
   - Android manifest з дозволами ✅
   - Gradle plugins додані ✅

## 🔧 Що потрібно зробити:

### Крок 1: Отримати Firebase Service Account JSON

1. Перейди в Firebase Console: https://console.firebase.google.com/
2. Обери свій проект `dron-alerts`
3. Перейди в **Project Settings** (⚙️ → Project settings)
4. Вкладка **Service Accounts**
5. Натисни **Generate new private key**
6. Збережи файл як `firebase-credentials.json`

### Крок 2: Додати credentials в Render

**Варіант A: Environment Variable (рекомендовано для продакшну)**

1. Відкрий файл `firebase-credentials.json`
2. Скопіюй весь вміст
3. Закодуй в base64:
   ```bash
   cat firebase-credentials.json | base64
   ```
4. В Render Dashboard → твій web service
5. Environment → Add Environment Variable
6. Назва: `FIREBASE_CREDENTIALS`
7. Значення: вставити base64 код
8. Save changes → Render auto-redeploy

**Варіант B: Локальний файл (для тестування)**

Помісти `firebase-credentials.json` в корінь проекту (поруч з `app.py`)

⚠️ **НЕ** коміть цей файл в git! Він вже в `.gitignore`

### Крок 3: Перевірка роботи

1. **Білд APK:**
   ```bash
   cd neptun_alarm_app
   flutter build apk --release
   ```

2. **Встанови APK на Android:**
   ```bash
   cp build/app/outputs/flutter-apk/app-release.apk ~/Desktop/dron-alerts-v1.0.3.apk
   ```

3. **В додатку:**
   - Відкрий вкладку "Налаштування"
   - Увімкни сповіщення
   - Вибери області (наприклад, Київ, Дніпро)
   - Натисни "Надіслати тестове сповіщення"
   - Маєш отримати уведомлення! 🎉

4. **Перевір backend:**
   - Відкрий https://neptun.in.ua
   - Перевір логи Render - має бути: `INFO: Firebase Admin SDK initialized successfully`
   - Має бути файл `devices.json` з твоїм токеном

### Крок 4: Тестування реальних уведомлень

1. Зачекай нової загрози в Telegram каналі
2. Backend автоматично:
   - Отримає повідомлення
   - Визначить область
   - Знайде всі пристрої, підписані на цю область
   - Відправить FCM уведомлення

3. Ти отримаєш push-уведомлення навіть якщо додаток закритий! 📱

## 🎨 Що бачить користувач:

1. **Налаштування:**
   - Перемикач "Увімкнути сповіщення"
   - Статус підключення (зелена галочка + обрізаний token)
   - Кнопка тестового уведомлення
   - Список всіх 25 областей з чекбоксами
   - Кнопки "Усі" / "Скасувати"
   - Інфо-картка з поясненням

2. **Уведомлення:**
   - 🚨 Критичні (ракети) - високий пріоритет
   - ⚠️ Звичайні (дрони) - нормальний пріоритет
   - Назва: тип загрози
   - Текст: місце
   - Клік → відкриває карту

## 📊 Статистика (в логах backend):

```
INFO: Registered device abc123... with 3 regions
INFO: Notification sent to device abc123...: projects/...
INFO: Sent 5/6 notifications for region: Київ
```

## 🔒 Безопасність:

- ✅ Credentials в environment variable (не в коді)
- ✅ Валідація FCM token перед збереженням
- ✅ Автоматична очистка неактивних пристроїв (>30 днів)
- ✅ HTTPS only для API
- ✅ Логи успішних/неуспішних відправлень

## 🎯 Наступні кроки (опціонально):

1. Збільшити версію в `pubspec.yaml`: `1.0.3+4`
2. Побудувати новий AAB: `flutter build appbundle --release`
3. Завантажити в Google Play Console
4. Користувачі отримають update через InAppUpdate

## 🐛 Troubleshooting:

**Уведомлення не приходять:**
- Перевір Render logs: `Firebase Admin SDK initialized successfully`
- Перевір що файл `devices.json` створений
- Перевір що область написана правильно (наприклад "Київ", не "Kiev")

**Помилка Firebase initialization:**
- Перевір що `FIREBASE_CREDENTIALS` правильно закодований в base64
- Перевір що в Service Account JSON правильний project_id

**Додаток крашиться:**
- Перевір що `google-services.json` в `android/app/`
- Перевір що `GoogleService-Info.plist` в `ios/Runner/`
- Запусти `flutter clean && flutter pub get`

## 📱 Версії:

- Flutter: як є
- Firebase Core: 3.15.2
- Firebase Messaging: 15.2.10
- Flutter Local Notifications: 18.0.1
- Backend: firebase-admin>=6.5.0

Готово! 🚀
