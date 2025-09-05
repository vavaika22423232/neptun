from datetime import datetime
from app import process_message

msg = """Хотінь (Сумська область) | Суми (Сумська область)
Загроза застосування БпЛА
"""
res = process_message(msg, mid=8888, date_str=datetime.utcnow().isoformat(), channel='test')
print('Markers:', len(res) if isinstance(res, list) else 'n/a')
if isinstance(res, list):
    for r in res:
        print(r)
