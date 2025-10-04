#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Test coordinate lookup for cities from the new message

test_cities = [
    "Кролевець", "Шостку", "Понорницю", "Борзну", "Ніжин", "Ічню",
    "Кіпті", "Носівку", "Бобровицю", "Малу Дівицю", "Козелець",
    "Згурівку", "Яготин", "Димер", "Іванків", "Малин",
    "Комишню", "Оржицю", "Глобине", "Білики", "Кременчук", "Полтаву",
    "Машівку", "Карлівку", "Кобеляки", "Шарівку", "Ковʼяги",
    "Нову Водолагу", "Бірки", "Балаклію", "Чугуїв", "Краснопавлівку",
    "Сахновщину", "Зачепилівку", "Лозову", "Смілу", "Царичанку",
    "Самар", "Верхньодніпровськ", "Гірницьке", "Софіївку", "Пʼятихатки",
    "Покровське", "Камʼянець", "Інгулецьке", "Березнегуват"
]

# Load basic cleaning functions
import re

def clean_text(text_to_clean):
    if not text_to_clean:
        return text_to_clean
    # Basic normalization
    cleaned = re.sub(r'[\u200B-\u200D\uFEFF\u3164\u2060\u00A0\u1680\u180E\u2000-\u200F\u202A-\u202E\u2028\u2029\u205F\u3000]+', ' ', text_to_clean)
    return cleaned.strip()

def normalize_city_name(name):
    """Basic city name normalization"""
    if not name:
        return name
    
    # Remove common prefixes/suffixes
    name = name.strip()
    name = re.sub(r'^н\.?\s*п\.?\s*', '', name, flags=re.IGNORECASE)  # Remove н.п.
    name = re.sub(r'^с\.?\s*', '', name, flags=re.IGNORECASE)  # Remove с.
    name = re.sub(r'^м\.?\s*', '', name, flags=re.IGNORECASE)  # Remove м.
    
    # Convert to lowercase for consistency
    return name.lower().strip()

print("=== ТЕСТ ОБРАБОТКИ КООРДИНАТ ГОРОДОВ ===")
print(f"Всего городов для проверки: {len(test_cities)}")
print()

print("ОБРАБОТКА ИМЕН ГОРОДОВ:")
processed_cities = []
for city in test_cities:
    clean_city = clean_text(city)
    norm_city = normalize_city_name(clean_city)
    processed_cities.append((city, clean_city, norm_city))
    print(f"  '{city}' -> clean: '{clean_city}' -> norm: '{norm_city}'")

print(f"\nРезультат: {len(processed_cities)} обработанных городов")

# Check for potential issues
print("\n=== ПРОБЛЕМНЫЕ СЛУЧАИ ===")
issues = []
for orig, clean, norm in processed_cities:
    if "'" in orig or "ʼ" in orig:  # Apostrophes
        issues.append(f"Апостроф: '{orig}' -> '{norm}'")
    if len(norm) < 3:
        issues.append(f"Короткое имя: '{orig}' -> '{norm}'")
    if any(char in norm for char in '.,!?;'):
        issues.append(f"Знаки пунктуации: '{orig}' -> '{norm}'")

if issues:
    for issue in issues:
        print(f"  ⚠️  {issue}")
else:
    print("  ✅ Проблемных случаев не найдено")

print(f"\n=== СВОДКА ===")
print(f"Исходных городов: {len(test_cities)}")
print(f"Обработанных: {len(processed_cities)}")
print(f"Потенциальных проблем: {len(issues)}")

# Most likely issue: cities not in coordinate database
print(f"\n⚠️  НАИБОЛЕЕ ВЕРОЯТНАЯ ПРИЧИНА:")
print(f"Города не найдены в базе координат CITY_COORDS или SETTLEMENTS_INDEX")
print(f"Нужно проверить файлы city_ukraine.json и CITY_COORDS")
