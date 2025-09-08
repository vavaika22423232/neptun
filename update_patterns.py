#!/usr/bin/env python3

import re

# Функція для зміни всіх шаблонів
def update_patterns():
    with open('/Users/vladimirmalik/Desktop/render2/app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern 1: Line ~4540
    old_pattern1 = r"(\d+)\[xх\]?\s\*бпла\.\*\?курс\(\?\:ом\)\?\s\+на\s\+\(\[A-Za-zА-Яа-яЇїІіЄєҐґ\\-\\\\'ʼ\`\\s\]\{3,40\}\?\)"
    new_pattern1 = r"(\d+)[xх]?\s*бпла.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\\-\\'ʼ\`\\s]{3,40}?)"
    
    # Pattern 2: Line ~4546
    old_pattern2 = r"бпла\.\*\?курс\(\?\:ом\)\?\s\+на\s\+\(\[A-Za-zА-Яа-яЇїІіЄєҐґ\\-\\\\'ʼ\`\\s\]\{3,40\}\?\)"
    new_pattern2 = r"бпла.*?курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ\\-\\'ʼ\`\\s]{3,40}?)"
    
    print("Оновлюємо patterns для підтримки н.п. префіксу...")
    
    # Заміна через пошук рядків що містять специфічні фрази
    lines = content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        # Шукаємо рядки з курс патернами
        if 'бпла.*?курс(?:ом)?' in line and '([A-Za-zА-Яа-яЇїІіЄєҐґ' in line:
            # Додаємо н.п. підтримку
            if '(?:н\\.п\\.?\\s*)?' not in line:
                updated_line = line.replace(
                    r'курс(?:ом)?\s+на\s+([A-Za-zА-Яа-яЇїІіЄєҐґ',
                    r'курс(?:ом)?\s+на\s+(?:н\.п\.?\s*)?([A-Za-zА-Яа-яЇїІіЄєҐґ'
                )
                if updated_line != line:
                    lines[i] = updated_line
                    updated = True
                    print(f"Оновлено рядок {i+1}")
    
    if updated:
        # Записуємо назад
        with open('/Users/vladimirmalik/Desktop/render2/app.py', 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print("✅ Файл оновлено!")
    else:
        print("❌ Нічого не оновлено")

if __name__ == '__main__':
    update_patterns()
