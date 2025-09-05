from datetime import datetime
from app import process_message
msg = '''Чернігівщина:
1 ракета на Холми
2 ракети на Лубни
'''
res = process_message(msg, mid=8888, date_str=datetime.utcnow().isoformat(), channel='test')
print('Result type:', type(res))
if isinstance(res, list):
    print('Markers:', len(res))
    for r in res:
        print(r['place'], r['marker_icon'], r['lat'], r['lng'])
else:
    print(res)
