# NEPTUN Alarm Map - Google Play Checklist

## ✅ Виконано для модерації

### 1. Безпека та конфіденційність
- ✅ `usesCleartextTraffic="false"` - тільки HTTPS з'єднання
- ✅ Network Security Config створено
- ✅ Safe Browsing увімкнено в WebView
- ✅ Mixed Content заблоковано
- ✅ Політика конфіденційності створена (PRIVACY_POLICY.md)
- ✅ Видалено WRITE_EXTERNAL_STORAGE (не потрібно)

### 2. Налаштування додатку
- ✅ targetSdk = 34 (Android 14)
- ✅ minSdk = 24 (Android 7.0)
- ✅ Code obfuscation (ProGuard)
- ✅ Resource shrinking
- ✅ Backup rules налаштовано
- ✅ Data extraction rules налаштовано

### 3. Іконки та ресурси
- ⚠️ ПОТРІБНО: Створити іконку додатку (ic_launcher)
  - Розміри: 48dp, 72dp, 96dp, 144dp, 192dp, 512dp
  - Adaptive icon для Android 8+
  - Круглі іконки (ic_launcher_round)

### 4. Метадані для Google Play Console
- ⚠️ ПОТРІБНО: Скріншоти (мінімум 2):
  - Phone: 16:9 (1920x1080px) або 9:16 (1080x1920px)
  - 7-inch tablet (опціонально)
  - 10-inch tablet (опціонально)

- ⚠️ ПОТРІБНО: Feature Graphic (обов'язково):
  - Розмір: 1024x500px
  - JPG або PNG

- ⚠️ ПОТРІБНО: Опис додатку:
  - Коротий опис (до 80 символів)
  - Повний опис (до 4000 символів)

### 5. Категорії та зміст
- Рекомендована категорія: **News & Magazines** або **Tools**
- Content rating: Teen або Everyone (після заповнення анкети)
- Target audience: Дорослі користувачі в Україні

### 6. Підписання APK/AAB
⚠️ КРИТИЧНО: Створити release keystore:
```bash
keytool -genkey -v -keystore neptun-release.keystore \\
  -alias neptun -keyalg RSA -keysize 2048 -validity 10000
```

Додати в build.gradle.kts:
```kotlin
signingConfigs {
    create("release") {
        storeFile = file("../neptun-release.keystore")
        storePassword = "YOUR_PASSWORD"
        keyAlias = "neptun"
        keyPassword = "YOUR_PASSWORD"
    }
}
```

### 7. Побудова релізної версії
```bash
cd android-app
./gradlew bundleRelease  # Для AAB (рекомендовано)
# або
./gradlew assembleRelease  # Для APK
```

Файли будуть у:
- `app/build/outputs/bundle/release/app-release.aab`
- `app/build/outputs/apk/release/app-release.apk`

### 8. Тестування перед публікацією
- [ ] Перевірити на різних версіях Android (24-34)
- [ ] Протестувати WebView на реальному пристрої
- [ ] Перевірити push-повідомлення
- [ ] Перевірити права доступу
- [ ] Internal testing в Google Play Console

### 9. URL політики конфіденційності
⚠️ ОБОВ'ЯЗКОВО: Завантажити PRIVACY_POLICY.md на:
- GitHub Pages (безкоштовно)
- Ваш сайт neptun.in.ua/privacy-policy
- Google Sites

### 10. Контактна інформація
- Email для підтримки: neptun.alarms@gmail.com
- Website: https://neptun.in.ua

## Наступні кроки:

1. **Створити іконки додатку** (найважливіше!)
2. **Створити keystore для підпису** (критично!)
3. **Зробити скріншоти** на емуляторі або реальному пристрої
4. **Опублікувати політику конфіденційності** на neptun.in.ua
5. **Заповнити всю інформацію в Google Play Console**
6. **Internal testing** - протестувати з 20+ користувачами 14 днів
7. **Публікація** - подати на розгляд

## Час розгляду Google Play
- Перша публікація: 2-7 днів
- Оновлення: 1-3 дні
- Internal testing: миттєво

## Поширені причини відхилення:
- ❌ Немає політики конфіденційності
- ❌ usesCleartextTraffic=true
- ❌ Низька якість скріншотів
- ❌ Невідповідність опису та функціоналу
- ❌ Відсутній вміст для всіх вікових груп
