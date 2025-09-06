#!/usr/bin/env python3
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Найдем строку 3285 и заменим её
for i, line in enumerate(lines):
    if 'uav_cities = _re_rel.findall' in line and 'a-zа-яіїєґ' in line:
        print(f"Найдена строка {i+1}: {repr(line)}")
        # Заменяем паттерн на поддерживающий пробелы
        old_line = line
        new_line = '        uav_cities = _re_rel.findall(r"бпла\\s+на\\s+([A-Za-zА-Яа-яЇїІіЄєҐґ\\-\\\'ʼ\\`\\s/]{3,40}?)(?=\\s|$|[,\\.\\!\\?;])", low_txt)\n'
        lines[i] = new_line
        print(f"Заменена на: {repr(new_line)}")
        break

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('✅ Паттерн обновлен!')
