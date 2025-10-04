#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Quick test of the new problematic message

test_message = """Сумщина:
БпЛА курсом на Ріпки
БпЛА курсом на Степанівку

Чернігівщина:
БпЛА курсом на Короп
8х БпЛА курсом на Борзну 
БпЛА курсом на Малу Дівицю 
БпЛА курсом на Прилуки 
БпЛА курсом на Гончарівське 
БпЛА курсом на Носівку
3х БпЛА курсом на Бобровицю 

Київщина:
БпЛА курсом на Яготин 
3х БпЛА курсом на Переяслав 
БпЛА курсом на Березань 
2х БпЛА курсом на Баришівку 
БпЛА курсом на Ржищів 

Житомирщина:
БпЛА курсом на Малин 
БпЛА курсом на Коростень

Полтавщина:
БпЛА курсом на Чутове
2х БпЛА курсом на Карлівку
БпЛА курсом на Машівку
БпЛА курсом на Кобеляки 
БпЛА курсом на Градизьк 
3х БпЛА курсом на Глобине 
БпЛА курсом на Котельву 

Харківщина:
БпЛА курсом на Покотилівку
БпЛА курсом на Коломак 
2х БпЛА курсом на Нову Водолагу 
2х БпЛА курсом на Бірки
БпЛА курсом на Берестин
4х БпЛА курсом на Златопіль
БпЛА курсом на Барвінкове 
2х БпЛА курсом на Андріївку
БпЛА курсом на Краснопавлівку

Черкащина:
БпЛА курсом на Цвіткове
БпЛА курсом на Чигирин
2х БпЛА курсом на Черкаси 
БпЛА курсом на Золотоношу 
БпЛА курсом на Смілу 
БпЛА курсом на Канів 

Дніпропетровщина:
БпЛА курсом на Вільногірськ
5х БпЛА курсом на Пʼятихатки 
БпЛА курсом на Лихівку
4х БпЛА курсом на Царичанку 
2х БпЛА курсом на Юріївку
БпЛА курсом на Петропавлівку 

Кіровоградщина:
БпЛА курсом на Знамʼянку 
БпЛА курсом на Бобринець
3х БпЛА курсом на Інгулецьке 
6х БпЛА курсом на Петрове 
БпЛА курсом на Павлиш 

Миколаївщина:
8х БпЛА курсом на Снігурівку

✙ Напрямок ракет ✙
✙Підтримати канал✙"""

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

print("=== ТЕСТ НОВОГО СООБЩЕНИЯ ===")

# Подсчитываем регионы
text_lines = test_message.split('\n')
region_count = 0
region_lines = []
for line in text_lines:
    line_lower = line.lower().strip()
    if any(region in line_lower for region in ['щина:', 'ччина:', 'щина]', 'ччина]', 'область:', 'kraj:']) or (
        ('щина' in line_lower or 'ччина' in line_lower) and line_lower.endswith(':')
    ):
        region_count += 1
        region_lines.append(line.strip())

print(f"Найдено регионов: {region_count}")
for i, region_line in enumerate(region_lines, 1):
    print(f"  {i}. {region_line}")

# Подсчитываем БпЛА
uav_count = 0
uav_lines = []
for line in text_lines:
    line_lower = line.lower().strip()
    if 'бпла' in line_lower and ('курс' in line_lower or 'на ' in line_lower):
        uav_count += 1
        uav_lines.append(line.strip())

print(f"\nНайдено упоминаний БпЛА с курсом: {uav_count}")

# Проверяем условие многорегиональности
should_trigger = region_count >= 2 and uav_count >= 3
print(f"\nУсловие многорегиональности:")
print(f"  Регионов >= 2: {region_count} >= 2 = {region_count >= 2}")
print(f"  БпЛА >= 3: {uav_count} >= 3 = {uav_count >= 3}")
print(f"  Должно сработать: {should_trigger}")

if should_trigger:
    print("✅ СООБЩЕНИЕ ДОЛЖНО ОБРАБАТЫВАТЬСЯ КАК МНОГОРЕГИОНАЛЬНОЕ!")

# Тестируем преобразование падежей на проблемных городах
print(f"\n=== ПРОБЛЕМЫ С ПРЕОБРАЗОВАНИЕМ ПАДЕЖЕЙ ===")
problem_cities = ["карлівку", "ріпки", "степанівку", "короп", "малин", "знамʼянку"]

for city_acc in problem_cities:
    city_nom = convert_accusative_to_nominative(city_acc)
    print(f"  '{city_acc}' -> '{city_nom}'")

print(f"\n⚠️  ОСНОВНАЯ ПРОБЛЕМА:")
print(f"Города не найдены в локальной базе CITY_COORDS,")
print(f"система пытается искать через Nominatim API, но названия неправильные")
print(f"Нужно добавить больше городов в базу координат или улучшить Nominatim запросы")
