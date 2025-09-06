#!/usr/bin/env python3
import re

full_text = '''Київщина:
БпЛА на Житомирщину з півночі  
БпЛА на Вишгород/Петрівці
БпЛА на Велика Димерка'''

# Оптимальный паттерн - до знаков препинания или до слов, которые явно не города
pattern = r"бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ\`\s/]+?)(?=\s+(?:з|на|до|від|через|повз|курсом|напрям)\s|[,\.\!\?;:\n]|$)"

results = re.findall(pattern, full_text.lower())
print(f"Оптимальный паттерн: {results}")

# Тестируем очистку результатов
cleaned = []
for city in results:
    city = city.strip()
    if city:
        cleaned.append(city)

print(f"Очищенные результаты: {cleaned}")

# Проверим каждый город на наличие координат
CITY_COORDS = {
    'кролевец': (51.5486, 33.3856),
    'конотоп': (51.2417, 33.2022), 
    'чернігів': (51.4982, 31.2893),
    'вишгород': (50.5840, 30.4890),
    'петрівці': (50.4167, 30.5833),
    'велика димерка': (50.8140, 30.8080),
}

print("\n--- Результат сопоставления ---")
for city in cleaned:
    if '/' in city:
        for subcity in city.split('/'):
            subcity = subcity.strip()
            coords = CITY_COORDS.get(subcity)
            status = "✅" if coords else "❌"
            print(f"{status} {subcity}: {coords}")
    else:
        coords = CITY_COORDS.get(city)
        status = "✅" if coords else "❌"
        print(f"{status} {city}: {coords}")
