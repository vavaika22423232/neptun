import requests
import csv
query = """
[out:json][timeout:90];
area["ISO3166-1"="UA"][admin_level=2]->.ua;
(
  node["place"~"city|town|village|suburb"](area.ua);
);
out body;
"""
url = "http://overpass-api.de/api/interpreter"
print("Fetching from Overpass API... this takes ~30s")
r = requests.post(url, data={"data": query})
if r.status_code == 200:
    data = r.json()
    count = 0
    with open('/tmp/ua_cities.csv', 'w', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['name', 'oblast', 'raion', 'lat', 'lng', 'place_type'])
        for element in data['elements']:
            tags = element.get('tags', {})
            name = tags.get('name:uk', tags.get('name', ''))
            if not name: continue
            lat, lng = element.get('lat'), element.get('lon')
            place = tags.get('place', '')
            oblast = tags.get('addr:region', tags.get('is_in:province', ''))
            raion = tags.get('addr:district', tags.get('is_in:district', ''))
            writer.writerow([name, oblast, raion, lat, lng, place])
            count += 1
    print(f"Saved {count} items to /tmp/ua_cities.csv")
else:
    print("Failed", r.status_code)
