#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Test new multi-regional UAV message from user

test_message = """Сумщина:
БпЛА курсом на Кролевець 
3х БпЛА курсом на Шостку

Чернігівщина:
2х БпЛА курсом на Понорницю
5х БпЛА курсом на Борзну 
5х БпЛА курсом на Ніжин
БпЛА курсом на Ічню
БпЛА курсом на Кіпті
БпЛА курсом на Носівку 
БпЛА курсом на Бобровицю 
3х БпЛА курсом на Малу Дівицю 
БпЛА курсом на Козелець

Київщина:
БпЛА курсом на Згурівку
БпЛА курсом на Яготин 
БпЛА курсом на Димер
БпЛА курсом на Іванків 

Житомирщина:
БпЛА курсом на Малин з Київщини 

Полтавщина:
БпЛА курсом на Комишню
БпЛА курсом на Оржицю
БпЛА курсом на Глобине 
2х БпЛА курсом на Білики 
БпЛА курсом на Кременчук 
3х БпЛА курсом на Полтаву 
4х БпЛА курсом на Машівку
БпЛА курсом на Карлівку
3х БпЛА курсом на Кобеляки 

Харківщина:
БпЛА курсом на Шарівку
БпЛА курсом на Ковʼяги 
5х БпЛА курсом на Нову Водолагу 
БпЛА курсом на Бірки
БпЛА курсом на Балаклію 
БпЛА курсом на Чугуїв
БпЛА курсом на Краснопавлівку
БпЛА курсом на Сахновщину 
БпЛА курсом на Зачепилівку
БпЛА курсом на Лозову 

Черкащина:
БпЛА курсом на Смілу 

Дніпропетровщина:
2х БпЛА курсом на Царичанку 
БпЛА курсом на Самар
БпЛА курсом на Верхньодніпровськ 
2х БпЛА курсом на Гірницьке
БпЛА курсом на Софіївку
11х БпЛА курсом на Пʼятихатки 
БпЛА курсом на Покровське 

Кіровоградщина:
БпЛА курсом на Камʼянець 
3х БпЛА курсом на Інгулецьке 

Миколаївщина:
6х БпЛА курсом на Березнегуват
ㅤ 
➡Підписатися"""

print("=== ТЕСТ НОВОГО МНОГОРЕГИОНАЛЬНОГО СООБЩЕНИЯ ===")
print(f"Длина сообщения: {len(test_message)} символов")
print()

# Разбиваем на строки
text_lines = test_message.split('\n')
print(f"Количество строк: {len(text_lines)}")
print()

# Подсчитываем регионы с новой логикой
region_count = 0
region_lines = []
for line in text_lines:
    line_lower = line.lower().strip()
    if any(region in line_lower for region in ['щина:', 'ччина:', 'щина]', 'ччина]', 'область:', 'край:']) or (
        ('щина' in line_lower or 'ччина' in line_lower) and line_lower.endswith(':')
    ):
        region_count += 1
        region_lines.append(line.strip())

print(f"Найдено регионов: {region_count}")
for i, region_line in enumerate(region_lines, 1):
    print(f"  {i}. {region_line}")
print()

# Подсчитываем упоминания БпЛА
uav_count = 0
uav_lines = []
for line in text_lines:
    line_lower = line.lower().strip()
    if 'бпла' in line_lower and ('курс' in line_lower or 'на ' in line_lower):
        uav_count += 1
        uav_lines.append(line.strip())

print(f"Найдено упоминаний БпЛА с курсом: {uav_count}")
for i, uav_line in enumerate(uav_lines[:15], 1):  # Показываем первые 15
    print(f"  {i}. {uav_line}")
if len(uav_lines) > 15:
    print(f"  ... и еще {len(uav_lines) - 15} строк")
print()

# Проверяем условие многорегиональности
should_trigger = region_count >= 2 and uav_count >= 3
print(f"Условие многорегиональности:")
print(f"  Регионов >= 2: {region_count} >= 2 = {region_count >= 2}")
print(f"  БпЛА >= 3: {uav_count} >= 3 = {uav_count >= 3}")
print(f"  Должно сработать: {should_trigger}")
print()

if should_trigger:
    print("✅ СООБЩЕНИЕ ДОЛЖНО ОБРАБАТЫВАТЬСЯ КАК МНОГОРЕГИОНАЛЬНОЕ!")
else:
    print("❌ Сообщение НЕ соответствует критериям многорегиональности")

# Дополнительная проверка - анализируем проблемные регионы
print("\n=== ДЕТАЛЬНЫЙ АНАЛИЗ РЕГИОНОВ ===")
problematic_regions = []
for line in text_lines:
    line_stripped = line.strip()
    if line_stripped and ':' in line_stripped and len(line_stripped) < 30:
        line_lower = line_stripped.lower()
        is_detected = any(region in line_lower for region in ['щина:', 'ччина:', 'щина]', 'ччина]', 'область:', 'край:']) or (
            ('щина' in line_lower or 'ччина' in line_lower) and line_lower.endswith(':')
        )
        print(f"'{line_stripped}' -> {'✅' if is_detected else '❌'}")
        if not is_detected and ('щина' in line_lower or 'область' in line_lower or 'край' in line_lower):
            problematic_regions.append(line_stripped)

if problematic_regions:
    print(f"\n⚠️  ПРОБЛЕМНЫЕ РЕГИОНЫ: {problematic_regions}")
