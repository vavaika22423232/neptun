from datetime import datetime
from app import process_message

sample = (
"Чернігівщина:\n"
"2х БпЛА курсом на Олишівку\n"
"БпЛА курсом на Гончарівське \n"
"БпЛА курсом на Малу Дівицю \n\n"
"Київщина: \n"
"БпЛА курсом на Згурівку\n"
"БпЛА курсом на Велику Димерку \n"
"БпЛА курсом на Яготин\n"
"БпЛА курсом на Бориспіль \n"
"БпЛА курсом на Узин\n"
"БпЛА курсом на Ставище \n"
"БпЛА курсом на Березань\n\n"
"Київ:\n"
"БпЛА курсом на Жуляни \n"
"3х БпЛА курсом на Бортничі\n\n"
"Хмельниччина:\n"
"БпЛА курсом на Старокостянтинів \n"
"2х БпЛА курсом на Адампіль\n"
"БпЛА курсом на Старий Остропіль\n\n"
"✙ Напрямок ракет  (https://t.me/napramok)✙\n"
"✙Підтримати канал (https://send.monobank.ua/5Pwr3r52mg)✙\n"
)

res = process_message(sample, mid=123456, date_str=datetime.utcnow().isoformat(), channel='test')
print('Type:', type(res))
if isinstance(res, list):
    print('Count:', len(res))
    for r in res:
        print(r['id'], r['place'], r['lat'], r['lng'])
else:
    print(res)
