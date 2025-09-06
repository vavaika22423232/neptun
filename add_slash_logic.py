#!/usr/bin/env python3
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найдем блок, который нужно заменить (строки 3286-3300)
start_line = None
end_line = None

for i, line in enumerate(lines):
    if 'if uav_cities:' in line and start_line is None:
        start_line = i
        print(f"Найден начало блока в строке {i+1}")
    if start_line is not None and 'return threats' in line:
        end_line = i
        print(f"Найден конец блока в строке {i+1}")
        break

if start_line is not None and end_line is not None:
    print(f"Заменяем строки {start_line+1}-{end_line+1}")
    
    # Новый код с обработкой слэша
    new_lines = [
        "        if uav_cities:\n",
        "            threats = []\n",
        "            for idx, rc in enumerate(uav_cities):\n",
        "                rc = rc.replace('\\u02bc',\"'\").replace('ʼ',\"'\").replace(''',\"'\").replace('`',\"'\")\n",
        "                \n",
        "                # Handle cities separated by slash (e.g., \"вишгород/петрівці\")\n",
        "                cities_to_process = []\n",
        "                if '/' in rc:\n",
        "                    cities_to_process.extend(rc.split('/'))\n",
        "                else:\n",
        "                    cities_to_process.append(rc)\n",
        "                \n",
        "                for city_idx, city in enumerate(cities_to_process):\n",
        "                    city = city.strip()\n",
        "                    if not city:\n",
        "                        continue\n",
        "                        \n",
        "                    base = UA_CITY_NORMALIZE.get(city, city)\n",
        "                    coords = CITY_COORDS.get(base)\n",
        "                    if not coords and 'SETTLEMENTS_INDEX' in globals():\n",
        "                        coords = (globals().get('SETTLEMENTS_INDEX') or {}).get(base)\n",
        "                    if coords:\n",
        "                        lat,lng = coords\n",
        "                        threats.append({\n",
        "                            'id': f\"{mid}_uav_{idx}_{city_idx}\", 'place': base.title(), 'lat': lat, 'lng': lng,\n",
        "                            'threat_type': 'shahed', 'text': clean_text(text)[:500], 'date': date_str, 'channel': channel,\n",
        "                            'marker_icon': 'shahed.png', 'source_match': 'uav_on_city'\n",
        "                        })\n",
        "            if threats:\n",
        "                return threats\n"
    ]
    
    # Заменяем блок
    lines[start_line:end_line+1] = new_lines
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print('✅ Логика обработки слэша добавлена!')
else:
    print('❌ Не найден блок для замены')
