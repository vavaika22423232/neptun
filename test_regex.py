#!/usr/bin/env python3
import re

test_message = '🛸 Конотопський район (Сумська обл.)\nКурс БПЛА. Прямуйте в укриття!'

# Test the regex pattern
pattern = r'([A-Za-zА-Яа-яЇїІіЄєҐґ\-]{4,})\s+район\s*\(([^)]*обл[^)]*)\)'

print(f"Test message: {repr(test_message)}")
print(f"Regex pattern: {pattern}")

match = re.search(pattern, test_message)
if match:
    print(f"✅ REGEX MATCH FOUND!")
    print(f"Group 1 (district): '{match.group(1)}'")
    print(f"Group 2 (oblast): '{match.group(2)}'")
else:
    print("❌ NO REGEX MATCH")

# Also test normalized district name
if match:
    raion_token = match.group(1).strip().lower()
    raion_base = re.sub(r'(ському|ского|ського|ский|ськiй|ськой|ським|ском)$', 'ський', raion_token)
    print(f"Raion token: '{raion_token}'")
    print(f"Raion base: '{raion_base}'")
