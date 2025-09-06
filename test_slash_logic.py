#!/usr/bin/env python3
# Тестируем новую логику обработки слэша
import re

text = """Сумщина:
БпЛА на Кролевец
БпЛА на Конотоп

Чернігівщина:
БпЛА на Чернігів

Київщина:
БпЛА на Житомирщину з півночі  
БпЛА на Вишгород/Петрівці
БпЛА на Велика Димерка"""

low_txt = text.lower()
uav_cities = re.findall(r"бпла\s+на\s+([a-zа-яіїєґ'ʼ'`\-/]{3,40})", low_txt)
print('Original uav_cities:', uav_cities)

# Новая логика обработки
all_cities = []
for idx, rc in enumerate(uav_cities):
    rc = rc.replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
    
    if '/' in rc:
        cities = rc.split('/')
        for city in cities:
            city = city.strip()
            if city:
                all_cities.append(city)
                print(f'Found city from slash: "{city}"')
    else:
        all_cities.append(rc)
        print(f'Found single city: "{rc}"')

print(f'Total cities to process: {all_cities}')

# Проверим, есть ли координаты в нашей базе
CITY_COORDS = {
    'кролевец': (51.5486, 33.3856),
    'конотоп': (51.2417, 33.2022),
    'чернігів': (51.4982, 31.2893),
    'вишгород': (50.5840, 30.4890),
    'петрівці': (50.4167, 30.5833),
    'велика': None,  # будет проблема
    'велика димерка': (50.8140, 30.8080),
}

print('\n--- Проверка координат ---')
for city in all_cities:
    coords = CITY_COORDS.get(city)
    if coords:
        print(f'✅ {city}: {coords}')
    else:
        print(f'❌ {city}: НЕ НАЙДЕН')
