from app import process_message
from datetime import datetime

text = """Сумщина:
БпЛА курсом на Терни 
5х БпЛА курсом на Шостку 
БпЛА курсом на Улянівку
БпЛА курсом на Тростянець 

Чернігівщина:
БпЛА курсом на Кіпті 
БпЛА курсом на Куликівку
БпЛА курсом на Березну 
3х БпЛА курсом на Понорницю 

Київщина:
БпЛА курсом на Васильків 
БпЛА курсом на Фастів 

Житомирщина:
БпЛА курсом на Коростень 

Харківщина:
2х БпЛА курсом на Балаклію
3х БпЛА курсом на Берестин
3х БпЛА курсом на Златопіль
3х БпЛА курсом на Зачепилівку
БпЛА курсом на Нову Водолагу 

Дніпропетровщина:
2х БпЛА курсом на Васильківку

✙ Напрямок ракет  (https://t.me/napramok)✙
✙Підтримати канал (https://send.monobank.ua/5Pwr3r52mg)✙"""

res = process_message(text, 600001, datetime.utcnow().isoformat(), 'test_channel')
if isinstance(res, list):
    print('TOTAL:', len(res))
    for r in res:
        print(r['place'], '| count:', r.get('count'), '| coords:', (r['lat'], r['lng']))
else:
    print('Returned:', res)
