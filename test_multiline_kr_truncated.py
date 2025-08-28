from datetime import datetime
from app import process_message

msg = '''Полтавщина:
рупа  курсом на овооржицьке
еркащина:
рупа  курсом на анів
2х рупи  курсом на игирин
Чернігівщина:
3х рупи  курсом на рилуки
'''

res = process_message(msg, mid=9999, date_str=datetime.utcnow().isoformat(), channel='test')
print('Result type:', type(res))
if isinstance(res, list):
    print('Markers:', len(res))
    for r in res:
        print(r['place'], r['count'], r['marker_icon'], r['lat'], r['lng'], r['source_match'])
else:
    print(res)
