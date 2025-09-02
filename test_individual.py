import requests

tests = [
    'БпЛА курсом на Недригайлів',
    'БпЛА курсом на Конотоп', 
    'БпЛА курсом на Прилуки',
    'БпЛА курсом на Ніжин'
]

url = 'https://neptun-7ua9.onrender.com/debug_parse'

for i, text in enumerate(tests):
    data = {'text': text, 'mid': f'test_{i}', 'date': '2025-09-02 12:00:00', 'channel': 'napramok'}
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        count = result.get('count', 0)
        if count > 0:
            place = result['tracks'][0].get('place', 'N/A')
            print(f'{text} → {count} tracks, place: {place}')
        else:
            print(f'{text} → 0 tracks')
    except Exception as e:
        print(f'{text} → Error: {e}')
