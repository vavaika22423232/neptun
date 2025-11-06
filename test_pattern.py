import re

text = '⚠️3-4х БПЛА на Павлоград'
pat_simple_na = re.compile(r'(\d+(?:-\d+)?)?[xх×]?\s*бпла\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\-\'ʼ`\s]{3,40}?)(?=[,\.\n;:!\?]|$)', re.IGNORECASE)

match = pat_simple_na.search(text)
if match:
    print('✅ MATCH FOUND!')
    print(f'Count: {match.group(1)}')
    print(f'City: {match.group(2)}')
else:
    print('❌ No match')

# Also test the raw message without emoji
text2 = '3-4х БПЛА на Павлоград'
match2 = pat_simple_na.search(text2)
if match2:
    print('\n✅ MATCH FOUND (without emoji)!')
    print(f'Count: {match2.group(1)}')
    print(f'City: {match2.group(2)}')
