#!/usr/bin/env python3
import re
import json
from datetime import datetime

# Минимальные необходимые функции и переменные
def clean_text(text):
    text = re.sub(r'\*\*[^*]*\*\*', '', text)  # Remove **bold** text
    text = re.sub(r'➡[^➡]*', '', text)  # Remove subscription prompts
    return text.strip()

def classify(text):
    return 'shahed', 'shahed.png'

# Словари (минимальные)
CITY_COORDS = {
    'кролевец': (51.5486, 33.3856),
    'конотоп': (51.2417, 33.2022),
    'чернігів': (51.4982, 31.2893),
    'вишгород': (50.5840, 30.4890),
    'петрівці': (50.4167, 30.5833),
    'велика димерка': (50.8140, 30.8080),
}

UA_CITY_NORMALIZE = {}

def test_uav_pattern():
    text = '''Сумщина:
БпЛА на Кролевец
БпЛА на Конотоп

Чернігівщина:
БпЛА на Чернігів

Київщина:
БпЛА на Житомирщину з півночі  
БпЛА на Вишгород/Петрівці
БпЛА на Велика Димерка

✙ Напрямок ракет ✙
✙Підтримати канал✙'''

    low_txt = text.lower()
    mid = 12345
    date_str = "2025-09-06 19:30:00"
    channel = "test"
    
    # Тестируем новый паттерн
    import re
    _re_rel = re
    uav_cities = _re_rel.findall(r"бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ\`\s/]+?)(?=\s+(?:з|на|до|від|через|повз|курсом|напрям)\s|[,\.\!\?;:\n]|$)", low_txt)
    print(f"Найденные города: {uav_cities}")
    
    if uav_cities:
        threats = []
        for idx, rc in enumerate(uav_cities):
            rc = rc.replace('\u02bc',"'").replace('ʼ',"'").replace("'","'").replace('`',"'")
            
            # Handle cities separated by slash (e.g., "вишгород/петрівці")
            cities_to_process = []
            if '/' in rc:
                cities_to_process.extend(rc.split('/'))
            else:
                cities_to_process.append(rc)
            
            print(f"Обрабатываем: {rc} -> {cities_to_process}")
            
            for city_idx, city in enumerate(cities_to_process):
                city = city.strip()
                if not city:
                    continue
                    
                base = UA_CITY_NORMALIZE.get(city, city)
                coords = CITY_COORDS.get(base)
                print(f"  Город: '{city}' -> base: '{base}' -> координаты: {coords}")
                
                if coords:
                    lat,lng = coords
                    threats.append({
                        'id': f"{mid}_uav_{idx}_{city_idx}", 'place': base.title(), 'lat': lat, 'lng': lng,
                        'threat_type': 'shahed', 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,
                        'marker_icon': 'shahed.png', 'source_match': 'uav_on_city'
                    })
        
        print(f"\n✅ Создано {len(threats)} угроз:")
        for i, threat in enumerate(threats):
            print(f"{i+1}. {threat['place']} ({threat['lat']}, {threat['lng']})")
        
        return threats
    
    return []

if __name__ == "__main__":
    test_uav_pattern()
