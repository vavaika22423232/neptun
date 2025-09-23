#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест парсинга направлений шахедов и визуализации поворота иконок
"""

# Тестовые примеры сообщений с направлениями
test_messages = [
    "🇺🇦 Чернігів ←півдня — 1х БпЛА курсом на Гончароське",
    "🇺🇦 Славутич ←сходу — 2х БпЛА курсом на Ніжин", 
    "🇺🇦 Київ ←заходу — 1х БпЛА",
    "🇺🇦 Суми ←півночі — БпЛА курсом на Охтирку",
    "🇺🇦 Харків ←півд-сходу — 3х БпЛА",
    "🇺🇦 Полтава ←півн-заходу — БпЛА курсом на Кременчук"
]

def get_rotation_angle(direction):
    """
    Определяет угол поворота иконки по направлению откуда прилетает угроза
    Логика: если угроза ←півдня, то она летит на север (90°)
    """
    if not direction:
        return 0
    
    dir_lower = direction.lower()
    
    # Комбинированные направления (8 сторон света) - проверяем сначала
    if 'півд' in dir_lower and ('сход' in dir_lower or 'сх' in dir_lower):
        return 135  # с юго-востока → на северо-запад
    if 'півд' in dir_lower and ('зах' in dir_lower or 'зх' in dir_lower):
        return 45   # с юго-запада → на северо-восток  
    if ('північ' in dir_lower or 'півн' in dir_lower) and ('сход' in dir_lower or 'сх' in dir_lower):
        return 225  # с северо-востока → на юго-запад
    if ('північ' in dir_lower or 'півн' in dir_lower) and ('зах' in dir_lower or 'зх' in dir_lower):
        return 315  # с северо-запада → на юго-восток
    
    # Основные направления (4 стороны света)
    if 'півд' in dir_lower:
        return 90   # с юга → на север
    if 'північ' in dir_lower or 'півн' in dir_lower:
        return 270  # с севера → на юг  
    if 'сход' in dir_lower or 'сх' in dir_lower:
        return 180  # с востока → на запад
    if 'зах' in dir_lower or 'заход' in dir_lower:
        return 0    # с запада → на восток
    
    return 0

def parse_direction_from_message(message):
    """Извлекает направление из сообщения по символу ←"""
    if '←' not in message:
        return None
    
    # Находим часть после ←
    direction_part = message.split('←')[1]
    
    # Берем слово до следующего пробела или знака
    direction = direction_part.split()[0].split('—')[0].strip()
    
    return direction

def test_direction_parsing():
    """Тестирует парсинг направлений и углов поворота"""
    print("🧪 Тест парсинга направлений шахедов\n")
    print("=" * 60)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. Сообщение: {message}")
        
        # Извлекаем направление
        direction = parse_direction_from_message(message)
        print(f"   Направление: {direction}")
        
        # Определяем угол поворота
        angle = get_rotation_angle(direction)
        print(f"   Угол поворота: {angle}°")
        
        # Визуальное представление
        arrow_map = {
            0: "→",      # восток
            45: "↗",     # северо-восток  
            90: "↑",     # север
            135: "↖",    # северо-запад
            180: "←",    # запад
            225: "↙",    # юго-запад
            270: "↓",    # юг
            315: "↘"     # юго-восток
        }
        
        arrow = arrow_map.get(angle, "?")
        print(f"   Визуальное направление: {arrow}")
        print(f"   CSS: transform: rotate({angle}deg);")

if __name__ == "__main__":
    test_direction_parsing()
