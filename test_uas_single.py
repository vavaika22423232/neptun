from datetime import datetime, timezone
from app import process_message
samples = [
    "**🛸 Дружківка (Донецька обл.)** Загроза застосування БПЛА. Перейдіть в укриття!",
    "2025-08-30 00:52:35\tUkraineAlarmSignal\t**🛸 Бердичів (Житомирська обл.)** Загроза застосування БПЛА. Перейдіть в укриття!",
]
for i,s in enumerate(samples,1):
    res = process_message(s, mid=9000+i, date_str=datetime.now(timezone.utc).isoformat(), channel='UkraineAlarmSignal')
    print('CASE', i, '->', type(res), res)
