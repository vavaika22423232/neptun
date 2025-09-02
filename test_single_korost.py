from app import process_message
from datetime import datetime
msg = "Житомирщина:\nБпЛА курсом на Коростень "
res = process_message(msg, 700002, datetime.utcnow().isoformat(), 'test')
print('RESULT TYPE:', type(res))
print(res)
if isinstance(res, list):
    for r in res:
        print(r['place'], r['lat'], r['lng'], r['source_match'])
