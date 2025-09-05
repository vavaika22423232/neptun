import os
import sys
print('TEST START')
os.environ['PARSER_TEST']='1'
from datetime import datetime
print('BEFORE IMPORT APP')
import app
print('AFTER IMPORT APP')
process_message = app.process_message
print('process_message first line:', process_message.__code__.co_firstlineno)
print('stdout isatty', getattr(sys.stdout,'isatty',lambda:None)())

samples = [
    ("ворожба (сумська обл.) загроза застосування бпла. перейдіть в укриття!", 'SampleChannel'),
    ("**⚠️ Херсон (Херсонська обл.)** ЗМІ повідомляють про вибухи. Будьте обережні!", 'SampleChannel'),
    ("**🟢 Нікополь (Дніпропетровська обл.)** Відбій загрози обстрілу. Будьте обережні!", 'SampleChannel'),
    ("**🟢 Марганець (Дніпропетровська обл.)** Відбій загрози обстрілу. Будьте обережні!", 'SampleChannel'),
    ("**⚠️ Дружківка (Донецька обл.)** ЗМІ повідомляють про вибухи. Будьте обережні!", 'SampleChannel'),
    ("**🛸 Херсон (Херсонська обл.)** Загроза застосування БПЛА. Перейдіть в укриття!", 'SampleChannel'),
]

now = datetime.utcnow().isoformat()
print('NOW=', now)
for idx,(text, ch) in enumerate(samples, start=1):
    res = process_message(text, 9100+idx, now, ch)
    print('--- INPUT ---')
    print(text)
    print('PARSED:', res)
print('TEST DONE')
