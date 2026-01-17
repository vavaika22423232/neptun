#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test the trajectory parser with sample messages"""

import sys
sys.path.insert(0, '.')

# Test messages
test_messages = [
    '🛵 БпЛА з півночі на Суми.',
    '🛵 Група БпЛА на сході Миколаївщини курсом на Кіровоградщину.',
    '🛵 БпЛА з Херсонщини на Миколаївщину.',
    '🛵 БпЛА курсом на м.Запоріжжя з північно-східного напрямку.',
    '🛵 Харків: БпЛА на місто з північно-східного напрямку.',
    '🛵 БпЛА з Херсонщини на Миколаївщину, напрямок м.Миколаїв.',
    '🛵 БпЛА на півдні Миколаївщини.',
    '🛵 БпЛА на Дніпропетровщині, напрямок Синельникове.',
    '🛵 БпЛА на сході Херсонщини, курс південно-західний.',
    '🛵 Харків: БпЛА з півночі.',
    '🛵 БпЛА на сході Сумщини, напрямок н.п.Лебедин.',
    '🛵 БпЛА на межі Сумської та Чернігівської областей, курс південний.',
    # Additional complex examples for AI
    '🛵 Група ударних БпЛА на Полтавщині прямує в напрямку Кременчука.',
    '🛵 Шахеди над Вінницькою областю летять на Київ.',
    '🛵 5 БпЛА в районі Умані, курс на Черкаси.',
]

print('Testing trajectory parser...\n')

from app import parse_trajectory_from_message, GROQ_ENABLED

if GROQ_ENABLED:
    print('✅ Groq AI is ENABLED - using intelligent parsing\n')
else:
    print('⚠️ Groq AI is DISABLED - using regex fallback only\n')

success = 0
failed = 0

for i, msg in enumerate(test_messages, 1):
    result = parse_trajectory_from_message(msg)
    if result:
        success += 1
        ai_marker = '🤖' if result.get('kind', '').startswith('ai_') else '📝'
        print(f'{ai_marker} ✅ {i}. "{msg[:55]}..."')
        print(f'   Kind: {result.get("kind")}')
        print(f'   Source: {result.get("source_name")} -> Target: {result.get("target_name")}')
        print(f'   Start: [{result.get("start")[0]:.4f}, {result.get("start")[1]:.4f}]')
        print(f'   End:   [{result.get("end")[0]:.4f}, {result.get("end")[1]:.4f}]')
    else:
        failed += 1
        print(f'❌ {i}. "{msg[:55]}..." - NO MATCH')
    print()

print(f'\n=== Results: {success} success, {failed} failed ===')
print(f'🤖 = AI parsed, 📝 = Regex parsed')
