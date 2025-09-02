import requests

url = 'https://neptun-7ua9.onrender.com/debug_parse'
data = {
    'text': '''Сумщина:
БпЛА курсом на Недригайлів 
БпЛА курсом на Конотоп 

Чернігівщина:
БпЛА курсом на Прилуки  
БпЛА курсом на Ніжин''',
    'mid': 'test_short',
    'date': '2025-09-02 12:00:00',
    'channel': 'napramok'
}

try:
    response = requests.post(url, json=data, timeout=30)
    result = response.json()
    print(f'Short test - Tracks: {result.get("count", 0)}')
    if result.get('tracks'):
        for track in result['tracks'][:5]:
            place = track.get('place', 'N/A')
            icon = track.get('marker_icon', 'N/A')
            print(f'  - {place} [{icon}]')
except Exception as e:
    print(f'Error: {e}')
