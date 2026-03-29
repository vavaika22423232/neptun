# Чеклист випуску v2.0.2

## Версія
- **versionName:** 2.0.2
- **versionCode / buildNumber:** 42

> Детальний чеклист публікації в магазинах: [STORE_PUBLISHING.md](STORE_PUBLISHING.md)

## Перед збіркою

- [ ] `flutter pub get`
- [ ] `key.properties` на місці (Android) — шлях до keystore, keyAlias, паролі
- [ ] iOS: підпис у Xcode налаштовано (Team, Provisioning Profile)

## Збірка

### Android (Google Play)
```bash
cd neptun_alarm_app
flutter build appbundle --release
```
Файл: `build/app/outputs/bundle/release/app-release.aab`

### iOS (App Store)
```bash
flutter build ipa --release
```
Або відкрити `ios/Runner.xcworkspace` в Xcode → Product → Archive

## Google Play Console

- [ ] Завантажити AAB
- [ ] Оновити опис змін (Release notes) — українською
- [ ] Data Safety, Privacy Policy, рейтинг контенту
- [ ] Відправити на перевірку

## App Store Connect

- [ ] Завантажити IPA (Transporter або Xcode)
- [ ] App Privacy (Nutrition Labels), Privacy Policy
- [ ] Додати «Що нового» — українською
- [ ] Відправити на перевірку

## Що нового в 2.0.2

- **Виправлено втрату Premium** — Premium більше не скидається при помилках мережі чи верифікації
- **Відновлення покупок** — покращено обробку «Відновити покупки», підтримка старих product ID
- **Помилка «елемент уже ваш»** — тепер показує успіх замість помилки
- Офлайн-очередь повідомлень — зберігаються при відсутності мережі
- Фото в чаті — галерея, камера, підтримка HEIC (iPhone)
- Покращена темна тема чату — чужі повідомлення добре видно
- Посилання на політику конфіденційності та умови в Профілі

### Release notes для магазинів (текст «Що нового»)

> Якщо ви купували Premium і він зник — оновіть додаток та натисніть «Відновити покупки» на сторінці Premium. Ми виправили проблему зі скиданням статусу.
