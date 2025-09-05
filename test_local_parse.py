from datetime import datetime
from app import process_message

samples = [
    ("ворожба (сумська обл.) загроза застосування бпла. перейдіть в укриття!", 'SampleChannel'),
    ("**⚠️ Херсон (Херсонська обл.)** ЗМІ повідомляють про вибухи. Будьте обережні!", 'SampleChannel'),
    ("**🟢 Нікополь (Дніпропетровська обл.)** Відбій загрози обстрілу. Будьте обережні!", 'SampleChannel'),
    ("**🟢 Марганець (Дніпропетровська обл.)** Відбій загрози обстрілу. Будьте обережні!", 'SampleChannel'),
    ("**⚠️ Дружківка (Донецька обл.)** ЗМІ повідомляють про вибухи. Будьте обережні!", 'SampleChannel'),
    ("**🛸 Херсон (Херсонська обл.)** Загроза застосування БПЛА. Перейдіть в укриття!", 'SampleChannel'),
]

now = datetime.utcnow().isoformat()
for idx,(text, ch) in enumerate(samples, start=1):
    res = process_message(text, 9000+idx, now, ch)
    print('--- INPUT ---')
    print(text)
    print('PARSED:', res)
