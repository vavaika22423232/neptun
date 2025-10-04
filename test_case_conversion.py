#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Test accusative to nominative case conversion

test_cases = [
    ("Кролевець", "кролевець"),      # no change
    ("Шостку", "шостк"),             # у -> remove
    ("Понорницю", "понорниць"),      # цю -> ць
    ("Борзну", "борзн"),             # у -> remove
    ("Ніжин", "ніжин"),              # no change
    ("Ічню", "ічн"),                 # ю -> remove
    ("Малу Дівицю", "алу дівиць"),   # цю -> ць
    ("Згурівку", "згурівк"),         # ку -> к
    ("Яготин", "яготин"),            # no change
    ("Димер", "димер"),              # no change
    ("Полтаву", "полтав"),           # у -> remove
    ("Машівку", "машівк"),           # ку -> к
    ("Сахновщину", "сахновщина"),    # щину -> щина
    ("Смілу", "сміл"),               # у -> remove
    ("Самар", "амар"),               # no change but wrong!
    ("Софіївку", "софіївк"),         # ку -> к
]

def convert_accusative_to_nominative(city_norm):
    """Convert Ukrainian city name from accusative to nominative case"""
    if city_norm.endswith('у') and len(city_norm) > 3:
        return city_norm[:-1]
    elif city_norm.endswith('ю') and len(city_norm) > 3:
        return city_norm[:-1]
    elif city_norm.endswith('ку') and len(city_norm) > 4:
        return city_norm[:-2] + 'к'
    elif city_norm.endswith('цю') and len(city_norm) > 4:
        return city_norm[:-2] + 'ць'
    elif city_norm.endswith('щину') and len(city_norm) > 6:
        return city_norm[:-4] + 'щина'
    else:
        return city_norm

print("=== ТЕСТ ПРЕОБРАЗОВАНИЯ ПАДЕЖЕЙ ===")
print("Винительный падеж -> Именительный падеж")
print()

correct = 0
total = len(test_cases)

for original, expected in test_cases:
    original_lower = original.lower()
    result = convert_accusative_to_nominative(original_lower)
    is_correct = result == expected
    status = "✅" if is_correct else "❌"
    
    print(f"{status} '{original}' -> '{result}' (ожидалось: '{expected}')")
    
    if is_correct:
        correct += 1

print(f"\nРезультат: {correct}/{total} правильных преобразований ({correct/total*100:.1f}%)")

# Test some specific problematic cases
print(f"\n=== ПРОБЛЕМНЫЕ СЛУЧАИ ===")
problematic = [
    "Малин",      # Не должно меняться, но обрезается префиксом "м."
    "Самар",      # Не должно меняться, но обрезается префиксом "с."
    "Смілу",      # "с." отрезается неправильно
]

for city in problematic:
    result = convert_accusative_to_nominative(city.lower())
    print(f"  '{city}' -> '{result}'")

print(f"\n⚠️  ДОПОЛНИТЕЛЬНАЯ ПРОБЛЕМА:")
print(f"Некоторые города теряют первые буквы из-за неправильного удаления префиксов 'м.', 'с.' и т.д.")
print(f"Эта проблема НЕ в падежах, а в функции normalize_city_name()")
