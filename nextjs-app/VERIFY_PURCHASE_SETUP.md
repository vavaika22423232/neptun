# Налаштування верифікації покупок (Google Play)

API `/api/verify-purchase` перевіряє покупки через Google Play Developer API.

## Безпека за замовчуванням

- Якщо `GOOGLE_APPLICATION_CREDENTIALS` **не встановлено** → повертається `{ valid: false }`
- Клієнт Flutter при помилці мережі/сервера **не** дозволяє преміум (раніше дозволяв — виправлено)

## Налаштування Google Play

1. **Google Cloud Console**
   - Створити Service Account
   - Згенерувати JSON key
   - Зберегти шлях до файлу: `GOOGLE_APPLICATION_CREDENTIALS=/path/to/neptun-play.json`

2. **Google Play Console**
   - Settings → API access
   - Grant "View financial data" для цього Service Account

3. **Змінні середовища** (на сервері)
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/home/neptun/keys/neptun-play.json
   export GOOGLE_PLAY_PACKAGE_NAME=com.neptunalarm.neptun_alarm_app
   ```

## App Store (iOS)

1. App Store Connect → My Apps → (ваш додаток) → In-App Purchases → App-Specific Shared Secret (або загальний Shared Secret).
2. Додати в `.env`:
   ```
   APPLE_SHARED_SECRET=ваш_shared_secret
   ```
3. Після deploy iOS покупки верифікуються через `verifyReceipt` API.
