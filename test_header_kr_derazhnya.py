from datetime import datetime
from app import process_message

msg = """**Хмельниччина:** Група КР курсом на Деражню ✙[ Напрямок ракет ](https://t.me/napramok)✙ ✙[Підтримати канал](https://send.monobank.ua/5Pwr3r52mg)✙"""
res = process_message(msg, mid=7788, date_str=datetime.utcnow().isoformat(), channel='test')
print('Type:', type(res))
if isinstance(res, list):
    print('Markers:', len(res))
    for r in res:
        print(r['place'], r['marker_icon'], r['source_match'])
else:
    print(res)
