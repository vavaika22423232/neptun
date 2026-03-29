# 🇺🇦 Neptun Alarm Map - Flutter App

Мобільний додаток для відображення повітряних тривог в Україні на інтерактивній карті.

## 📱 Функції

- ✅ Інтерактивна карта з маркерами тривог
- ✅ Автоматичне оновлення кожні 30 секунд
- ✅ Різні типи тривог (БпЛА, ракети, загальна тривога)
- ✅ Детальна інформація про кожне повідомлення
- ✅ Список всіх повідомлень
- ✅ Темна та світла теми
- ✅ Працює на Android та iOS

## 🚀 Швидкий старт

```bash
flutter pub get
flutter run
```

## 📦 Залежності

- flutter_map - OpenStreetMap
- http - API запити
- latlong2 - координати

## 🛠️ Збірка

Android: `flutter build apk --release`
iOS: `flutter build ios --release`

**macOS у Cursor:** якщо збірка падає з помилкою `resource fork, Finder information, or similar detritus not allowed` (CodeSign), це через атрибут `com.apple.provenance`, який Cursor додає до файлів. **Обхід:** запускай `flutter run -d macos` або `flutter build macos` з **системного Terminal.app** (не з вбудованого терміналу Cursor). Альтернатива — запуск на симуляторі iOS (наприклад, iPhone 17 Pro) з Cursor.

