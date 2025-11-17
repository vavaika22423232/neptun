# Створення Release Build для Google Play

## 1. Створи keystore (один раз):
```bash
keytool -genkey -v -keystore neptun-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias neptun
```

Запитає:
- Password: (створи надійний, запиши!)
- Name, Organization: Neptun Alarm Map
- City, State, Country: Ukraine

## 2. Створи gradle.properties:
```
RELEASE_STORE_FILE=neptun-release-key.jks
RELEASE_STORE_PASSWORD=твій_пароль
RELEASE_KEY_ALIAS=neptun
RELEASE_KEY_PASSWORD=твій_пароль
```

## 3. Збери AAB:
```bash
./gradlew bundleRelease
```

Файл буде: `app/build/outputs/bundle/release/app-release.aab`

## 4. Завантаж в Google Play Console:
- Release > Production > Create new release
- Upload AAB file
- Add release notes
- Review and roll out
