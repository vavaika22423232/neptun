from datetime import datetime
from app import process_message
msg = '''Чернігівщина:
БпЛА курсом на Короп
3х БпЛА курсом на Сосницю
БпЛА курсом на Олишівку
2х БпЛА курсом на Новгород-Сіверський 

Київщина: 
БпЛА курсом на Баришівку 
БпЛА повз Білу Церкву курсом на Сквиру 
БпЛА курсом на Димер 
БпЛА курсом на Бориспіль 
БпЛА курсом на Бровари 

Черкащина:
2х БпЛА курсом на Жашків 

Хмельниччина:
4х БпЛА курсом на Старокостянтинів

✙ Напрямок ракет  (https://t.me/napramok)✙
✙Підтримати канал (https://send.monobank.ua/5Pwr3r52mg)✙'''
res = process_message(msg, mid=7777, date_str=datetime.utcnow().isoformat(), channel='test')
print('Result type:', type(res))
if isinstance(res, list):
    print('Markers:', len(res))
    for r in res:
        print(r['place'], r['lat'], r['lng'])
else:
    print(res)
