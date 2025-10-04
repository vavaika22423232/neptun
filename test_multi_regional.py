#!/usr/bin/env python3
# Test script for multi-regional message processing

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

✙ Напрямок ракет ✙
✙Підтримати канал✙"""

def test_multi_regional_detection():
    text_lines = test_message.split('\n')
    
    print("=== Multi-Regional Detection Test ===")
    print(f"Total lines: {len(text_lines)}")
    
    # Test region detection
    region_count = sum(1 for line in text_lines if any(region in line.lower() for region in ['щина:', 'щина]', 'область:', 'край:']) or (
        'щина' in line.lower() and line.lower().strip().endswith(':')
    ) or any(region in line.lower() for region in ['щина)', 'щини', 'щину', 'одещина', 'чернігівщина', 'дніпропетровщина', 'харківщина', 'київщина']))
    
    print(f"Region count: {region_count}")
    
    # Find region lines
    region_lines = []
    for line in text_lines:
        if any(region in line.lower() for region in ['щина:', 'щина]', 'область:', 'край:']) or (
            'щина' in line.lower() and line.lower().strip().endswith(':')
        ) or any(region in line.lower() for region in ['щина)', 'щини', 'щину', 'одещина', 'чернігівщина', 'дніпропетровщина', 'харківщина', 'київщина']):
            region_lines.append(line)
    
    print("Region lines:")
    for i, line in enumerate(region_lines, 1):
        print(f"  {i}. '{line}'")
    
    # Test UAV detection
    uav_count = sum(1 for line in text_lines if 'бпла' in line.lower() and ('курс' in line.lower() or 'на ' in line.lower()))
    print(f"UAV course lines count: {uav_count}")
    
    # Test condition
    should_trigger = region_count >= 2 and uav_count >= 3
    print(f"Should trigger multi-regional: {should_trigger}")
    
    # Show some UAV lines
    uav_lines = [line for line in text_lines if 'бпла' in line.lower() and ('курс' in line.lower() or 'на ' in line.lower())]
    print(f"First 5 UAV lines:")
    for i, line in enumerate(uav_lines[:5], 1):
        print(f"  {i}. '{line}'")

if __name__ == "__main__":
    test_multi_regional_detection()
