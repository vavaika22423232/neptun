#!/usr/bin/env python3
# -*- coding: utf-8 -*-

test_message = """Миколаївщина:
БпЛА курсом на Первомайськ 
БпЛА курсом на Братське 

Вінниччина:
БпЛА курсом на Чечельник

✙ Напрямок ракет  (https://t.me/napramok)✙
✙Підтримати канал (https://send.monobank.ua/5Pwr3r52mg)✙"""

# Проверим что происходит с donation filtering
low_full = test_message.lower()
DONATION_KEYS = [
    'монобанк','monobank','mono.bank','privat24','приват24','реквізит','реквизит','донат','donat','iban','paypal','patreon','send.monobank.ua','jar/','банка: http','карта(','карта(monobank)','карта(privat24)'
]

print("Исходный текст:")
print(test_message)
print(f"\nДлина: {len(test_message)}")

donation_present = any(k in low_full for k in DONATION_KEYS)
print(f"\nDonation present: {donation_present}")

# Угрозы
threat_tokens = ['бпла','дрон','шахед','shahed','geran','ракета','ракети','missile','iskander','s-300','s300','каб','артил','града','смерч','ураган','mlrs']
has_threat_word = any(tok in low_full for tok in threat_tokens)
print(f"Threat words: {has_threat_word}")

if donation_present and has_threat_word:
    print("\nУдаляю строки с донатами...")
    kept_lines = []
    for ln in test_message.splitlines():
        ll = ln.lower()
        should_remove = any(k in ll for k in DONATION_KEYS)
        print(f"Строка: '{ln}' -> удалить: {should_remove}")
        if should_remove:
            continue
        kept_lines.append(ln)
    
    cleaned_text = '\n'.join(kept_lines)
    print(f"\nОчищенный текст:\n{cleaned_text}")
    print(f"Длина очищенного: {len(cleaned_text)}")
