#!/usr/bin/env python3
import re

threat_type_pattern = r'(?:БПЛА|КАБ|Ракета|Ракети|Шахед|Дрон|Дрони)'
mapstransler_pattern2 = rf'^[^\w]*{threat_type_pattern}\s+([А-ЯІЇЄЁа-яіїєё\'\'\-\s/]+)[^(]*\(([^)]+обл[^)]*)\)'

test_messages = [
    'БПЛА Вільнянськ (Запорізька обл.)',
    'БПЛА Умань (Черкаська обл.)',
    'БПЛА Суми (Сумська обл.)',
    'БПЛА Шахтарське (Дніпропетровська обл.)',
    'БПЛА Славгород (Дніпропетровська обл.)',
    'БПЛА Долинська (Кіровоградська обл.)',
    'БПЛА Очаків (Миколаївська обл.)',
]

for msg in test_messages:
    m = re.search(mapstransler_pattern2, msg, re.IGNORECASE)
    if m:
        print(f'OK: {msg}')
        print(f'    city="{m.group(1).strip()}", oblast="{m.group(2).strip()}"')
    else:
        print(f'FAIL: {msg}')
