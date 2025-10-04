#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Test specific multi-regional UAV message from user

test_message = """Сумщина:
БпЛА курсом на Липову Долину 

Чернігівщина:
2х БпЛА курсом на Сосницю
БпЛА курсом на Батурин
2х БпЛА курсом на Борзну 
БпЛА курсом на Ічню
БпЛА курсом на Парафіївку
БпЛА курсом на Козелець
БпЛА курсом на Ягідне 
БпЛА курсом на Куликівку

Харківщина:
БпЛА курсом на Балаклію
6х БпЛА курсом на Нову Водолагу 
3х БпЛА курсом на Бірки 
2х БпЛА курсом на Донець
3х БпЛА курсом на Златопіль
2х БпЛА курсом на Сахновщину 
БпЛА курсом на Орільку
БпЛА курсом на Зачепилівку
БпЛА курсом на Слобожанське 
БпЛА курсом на Берестин
БпЛА курсом на Савинці 
БпЛА курсом на Краснокутськ
БпЛА курсом на Чугуїв 
БпЛА курсом на Андріївку

Полтавщина:
БпЛА курсом на Великі Сорочинці 
БпЛА курсом на Миргород 
БпЛА курсом на Полтаву 
БпЛА курсом на Карлівку
БпЛА курсом на Машівку
БпЛА курсом на Нові Санжари 
БпЛА курсом на Решетилівку 
БпЛА курсом на Глобине
БпЛА курсом на Котельву 

Дніпропетровщина:
БпЛА курсом на Софіївку
БпЛА курсом на Томаківку
БпЛА курсом на Петриківку
2х БпЛА курсом на Юріївку
БпЛА курсом на Магдалинівку 
БпЛА курсом на Царичанку 
2х БпЛА курсом на Верхньодніпровськ 
Розвідувальний БпЛА в районі Славгорода

Донеччина:
БпЛА курсом на Білозерське
ㅤ 
➡Підписатися"""

print("=== ТЕСТ КОНКРЕТНОГО СООБЩЕНИЯ ===")
print(f"Длина сообщения: {len(test_message)} символов")
print()

# Разбиваем на строки
text_lines = test_message.split('\n')
print(f"Количество строк: {len(text_lines)}")
print()

# Подсчитываем регионы
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
for i, uav_line in enumerate(uav_lines[:10], 1):  # Показываем первые 10
    print(f"  {i}. {uav_line}")
if len(uav_lines) > 10:
    print(f"  ... и еще {len(uav_lines) - 10} строк")
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
