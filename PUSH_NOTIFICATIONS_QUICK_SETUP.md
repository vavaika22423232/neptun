# ✅ ГОТОВО: Настройка Push-уведомлений

## 🎯 Что нужно сделать

### 1. Открыть Render Dashboard
Перейти на: https://dashboard.render.com/

### 2. Выбрать ваш Backend сервис
Найти сервис `neptun` или как он называется

### 3. Добавить переменную окружения

1. Перейти в **Environment** → **Environment Variables**
2. Нажать **Add Environment Variable**
3. Заполнить:

**Key:**
```
FIREBASE_CREDENTIALS
```

**Value:** (скопировать из файла `firebase_base64.txt`)
```
ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAiZHJvbi1hbGVydHMiLAogICJwcml2YXRlX2tleV9pZCI6ICIwNWRlNWQzMjMwYmJkMmM1NzRhNjM1NTA0ODI5YmRjZDc2YTU2NTk1IiwKICAicHJpdmF0ZV9rZXkiOiAiLS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tXG5NSUlFdlFJQkFEQU5CZ2txaGtpRzl3MEJBUUVGQUFTQ0JLY3dnZ1NqQWdFQUFvSUJBUURXUG94QkRRaHBTd0duXG5EOFlMM1JHbExhR0NwdG5PQlNWVkR6NUg3anZZYXNEZ2RLOHhKblVSMFp6YklwSDNnQU9GM2pEQ0NrR3BXOWZXXG5lZ2ZPOUdycmpUVFBPRVQxdTRvL1czRGRiVWExWFNSOXRZL3Y2UlQ4MHZCbVU1OG5sTFU0c3dWc0dzMWJMTGp4XG5HVU1FcWVhSVIrSG5mRnZzaGl4YlJUTEx2Yk9UTDBUSFJUSmpxU1RsN04wR3ROVGpINmd2VXVxUjhNUlZMZEZiXG54UFpTYTNFYnYrVWhnL09SQ0FFTm5kU1JPTkVUOXh6cVNWc21HN0Q1cnBPbFRHbG1haUF1aU1HN01WYS9xQWdvXG5jM1JDWnFxcnF0WDZyVnAxSDRiTWQzNlAwSWNoQnYvRjZJSXMzZk9WeTI2cUF2SGw4Tk0zcXhpbE5mcXFudEhkXG5lME5OMFpSWkFnTUJBQUVDZ2dFQUV4d2QwSWp1dTNoQzhTUXV0Y3piT21ZNU8za25LNnc1S2VsNUtiQ3Q5VE9EXG5KQmVQQk9MNW11N3lmeUswbUdTbEZuZG5nVXlwa2dkWGdqeFNTVkJ6TlFneHNnWVgzZW9EZm52cE02Yi85cG9VXG5tNE5BRDlYZmdiUk5yYzJVVmFoN0NGQUNQTTZnaTBXNjhxNXoxRGVxRU1xRjg1V2J4c1lxVzEzRWE4M3VTdTRlXG5UcnUvT0RNYWhieTlIakFPL25tbjJzbk5yNG9POVhDd3M0MUh0WFAveDNDdTA0dFlpTWFsUzFkSzhIdEJDZ1dCXG44WnUwU09IOGFWeklHRnAwNWttVldGbFRGMzJBTmlSOGoraTlmU3FRd0NhckR6cXYxTlgvTW11TG1HeUh5QTQxXG5TYlNGSnVoTXVwakxFdkdXWFlhUkNqQVFkNy91NkdNV0Y0WDEzMmN2alFLQmdRRHdCcHFlcXRMWm14WTBoNFBtXG5pSzVYMmQ4djkzbUlsVU02YnUyK2RPYjBYMjBRQXBURWF3VDJBYTd5QnY4UUszVVZsN0JoNmtRSmlucktHWWZGXG5MdnB0dUJ3Sms4ZjZrQW94Wnl6L0FzaUNuSXFnTVpWbVI4V2NMcUxpOGM0eHh0a3VRK3pFbnY3RHJjb3hGVUxaXG5hbURUZzVmbDdsWWZxdzBPMDVOaUNLYlpDd0tCZ1FEa2dMSmYwSjRBdjdKQ0FuSXN3Nm5sQ1NveHNPbmtKRDlIXG5mUW1rVXNkempJM2lGcGRyV0JhM3dLOTVqR3ZmdGtEV05meWpCZStSR1djeDZlWXd4a1N4bXJNcHhxbEViOEhzXG5PYmptdEx1YWkvWXdUU0JZUjZud2pkdDMxdTlHUDBhZWxJUXBpejB5bklNSFVYdi9sckFpQVJMR2QwVHVMaWFqXG5OQjY4UTRBT3F3S0JnSEhXRC9yMGRXK3krQU1OeW1iSnFEWU9KS1h4THZpeUllSlN2ZnE0SXRqL2NSQkl5Um1tXG4wQUdFcHQ0dXAwV1o5cnU0NTNSbzBML2RwNEsyUFFndDBhTzd6OEJURUdNcmNVb2c3dHc3QzdHMllLQzlJMmdRXG4zZzNHcUlZTnZJY3JFZEc1Y1UrSFFMaTVjYzE1a2V6ZllQQ3YxcGk4UXFoZVRhRWNneWZaaHBnbEFvR0FHUm1sXG4vbTV0SE1ueDY5eFc3R0hsNUxuWC83TmVUZWhKWnpIdUFEWHpvTmE4c3l3bUgrMkNPVmNhTDNEa1hLT3BoWjVTXG5qUm5XMGdxSFVtMU9FdWVFbmpuUEduU3ZIVXhsY2V4NVNpWnFRVFRFcTFPZGpQVDZUdWxXUlZpLzJlaVRlbEg0XG5IcFFqK2M1RmVtVlNDS1psM0taZmlKdUxYOXFEOWdPQXFNK0ZYcGNDZ1lFQXBxL0hxTWx2VzNnVnB2SDRZRUFSXG5vc2t2bEdLeXh5RnJUM1huWGFrd082TjhUT1c5MjQyYU41QS9wcDBvVEo4cE1iM25aSURnM1dQWHZWQzdQSlBHXG5SNU13UFBwMGhJRkI1dm1DUjltbjI1Ym5Rc1owRExjeTE1WnhPNDdpTXFrOVorQnlzTTNVNGpoOWdyUUNyQ2Y3XG5jVHpsemsrOVk2UTVDT2tIdVpCQ1pUdz1cbi0tLS0tRU5EIFBSSVZBVEUgS0VZLS0tLS1cbiIsCiAgImNsaWVudF9lbWFpbCI6ICJmaXJlYmFzZS1hZG1pbnNkay1mYnN2Y0Bkcm9uLWFsZXJ0cy5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgImNsaWVudF9pZCI6ICIxMTA5MjI0MzY5NTk2MDQxMDEyNjIiLAogICJhdXRoX3VyaSI6ICJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20vby9vYXV0aDIvYXV0aCIsCiAgInRva2VuX3VyaSI6ICJodHRwczovL29hdXRoMi5nb29nbGVhcGlzLmNvbS90b2tlbiIsCiAgImF1dGhfcHJvdmlkZXJfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIvdjEvY2VydHMiLAogICJjbGllbnRfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9yb2JvdC92MS9tZXRhZGF0YS94NTA5L2ZpcmViYXNlLWFkbWluc2RrLWZic3ZjJTQwZHJvbi1hbGVydHMuaWFtLmdzZXJ2aWNlYWNjb3VudC5jb20iLAogICJ1bml2ZXJzZV9kb21haW4iOiAiZ29vZ2xlYXBpcy5jb20iCn0K
```

4. Нажать **Save**

### 4. Дождаться перезапуска сервера

Render автоматически перезапустит сервис после добавления переменной (2-3 минуты).

### 5. Проверить логи

Открыть **Logs** и найти строку:
```
INFO: Firebase Admin SDK initialized successfully
```

## ✅ Проверка работы

1. Открыть приложение на телефоне
2. Перейти в **Налаштування** → **Регіони для тривог**
3. Выбрать свой регион (например, Київ)
4. Нажать **Зберегти**
5. Нажать **Тест сповіщення**

Должно прийти тестовое уведомление: 
```
🧪 Тестове сповіщення
Dron Alerts працює коректно!
```

## 🎉 Готово!

После настройки push-уведомления будут приходить автоматически при новых тревогах:

- 🚨 **Ракеты** (красные, критичные)
- ⚠️ **Дроны** (оранжевые)  
- 🔴 **Повітряна тривога** (красные)
- ✅ **Відбій** (зеленые)

Уведомления приходят **мгновенно** при появлении новых сообщений в Telegram!
