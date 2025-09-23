#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест правильности обработки направленных региональных угроз
"""

def parse_directional_threat(text):
    """Упрощенная версия функции для тестирования"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Паттерны направленных угроз
    directional_patterns = [
        # "на харківщина в напрямку чугуєва зі сходу"
        {
            'pattern': r'на\s+(харківщин[аи]|харків.*?област[ьі])\s+.*?напрямк[уи]\s+(\w+).*?(зі?\s+)?(сход[уи]|заход[уи]|півд[ня]|північ[і])',
            'region': 'kharkivska',
            'base_city': 'харків'
        },
        # "на чернігівщина - в напрямку н.п.понорниця з північного сходу"
        {
            'pattern': r'на\s+(чернігівщин[аи]|черніг.*?област[ьі]).*?напрямк[уи]\s+.*?(понорниц[яі]|н\.п\.понорниц[яі]).*?(півн.*?сход|північн.*?схід)',
            'region': 'chernihivska',
            'base_city': 'чернігів'
        },
        # "група ворожих бпла на південному заході від м.запоріжжя"
        {
            'pattern': r'(група.*?бпла|бпла).*?(на\s+)?(.+?)від\s+.*?(запоріжж[яі])',
            'region': 'zaporizka',
            'base_city': 'запоріжжя'
        }
    ]
    
    import re
    for pattern_info in directional_patterns:
        if re.search(pattern_info['pattern'], text_lower):
            return {
                'region': pattern_info['region'],
                'base_city': pattern_info['base_city'],
                'direction': extract_direction(text_lower),
                'original_text': text
            }
    
    return None

def extract_direction(text):
    """Извлекает направление из текста"""
    directions = {
        'зі сходу': 'east',
        'зі заходу': 'west',
        'з півночі': 'north',
        'з півдня': 'south',
        'з північного сходу': 'northeast',
        'з північного заходу': 'northwest',
        'з південного сходу': 'southeast',
        'з південного заходу': 'southwest',
        'на південному заході': 'southwest',
        'на північному заході': 'northwest',
        'курс - північно-західний': 'northwest',
        'курс північно-західний': 'northwest',
        'північно-західний': 'northwest',
        'південному заході': 'southwest'
    }
    
    for phrase, direction in directions.items():
        if phrase in text:
            return direction
    
    return None

def calculate_directional_coords(base_city, direction, distance_km=50):
    """Вычисляет координаты для направленной угрозы"""
    city_coords = {
        'харків': [49.9935, 36.2304],
        'чернігів': [51.4982, 31.2893],
        'запоріжжя': [47.8388, 35.1396]
    }
    
    base_lat = city_coords.get(base_city, [0, 0])[0]
    base_lng = city_coords.get(base_city, [0, 0])[1]
    
    if not base_lat or not base_lng:
        return None
    
    import math
    
    direction_offsets = {
        'north': [distance_km / 111, 0],
        'south': [-distance_km / 111, 0],
        'east': [0, distance_km / (111 * math.cos(base_lat * math.pi / 180))],
        'west': [0, -distance_km / (111 * math.cos(base_lat * math.pi / 180))],
        'northeast': [distance_km / 157, distance_km / (157 * math.cos(base_lat * math.pi / 180))],
        'northwest': [distance_km / 157, -distance_km / (157 * math.cos(base_lat * math.pi / 180))],
        'southeast': [-distance_km / 157, distance_km / (157 * math.cos(base_lat * math.pi / 180))],
        'southwest': [-distance_km / 157, -distance_km / (157 * math.cos(base_lat * math.pi / 180))]
    }
    
    offset = direction_offsets.get(direction)
    if not offset:
        return [base_lat, base_lng]  # Fallback to base city
    
    return [base_lat + offset[0], base_lng + offset[1]]

def test_directional_threats():
    """Тестирует обработку направленных угроз"""
    
    test_messages = [
        "ворожі бпла на харківщина в напрямку чугуєва зі сходу",
        "на чернігівщина - в напрямку н.п.понорниця з північного сходу",
        "група ворожих бпла на південному заході від м.запоріжжя, курс - північно-західний"
    ]
    
    print("🎯 Тест обработки направленных региональных угроз")
    print("=" * 65)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. Сообщение: {message}")
        print("-" * 60)
        
        # Парсим направленную угрозу
        threat = parse_directional_threat(message)
        
        if threat:
            print(f"✅ Обнаружена направленная угроза:")
            print(f"   Регион: {threat['region']}")
            print(f"   Базовый город: {threat['base_city']}")
            print(f"   Направление: {threat['direction']}")
            
            # Вычисляем координаты
            coords = calculate_directional_coords(threat['base_city'], threat['direction'])
            if coords:
                print(f"   Координаты: {coords[0]:.4f}, {coords[1]:.4f}")
                
                # Показываем смещение от центра города
                city_coords = {
                    'харків': [49.9935, 36.2304],
                    'чернігів': [51.4982, 31.2893],
                    'запоріжжя': [47.8388, 35.1396]
                }
                
                base = city_coords[threat['base_city']]
                offset_lat = coords[0] - base[0]
                offset_lng = coords[1] - base[1]
                
                print(f"   Смещение от центра города: {offset_lat:.4f}°, {offset_lng:.4f}°")
                print(f"   Примерное расстояние: ~50 км в направлении {threat['direction']}")
            else:
                print("   ❌ Не удалось вычислить координаты")
        else:
            print("❌ Направленная угроза не обнаружена")

if __name__ == "__main__":
    test_directional_threats()
