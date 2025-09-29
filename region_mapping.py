#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Маппинг названий регионов из Ukraine Alert API к нашей системе координат
"""

import logging
from ukraine_alert_api import ukraine_api

log = logging.getLogger(__name__)

# Маппинг регионов API -> наши названия
REGION_NAME_MAPPING = {
    # Области (полные названия)
    "Вінницька область": "Вінниця",
    "Волинська область": "Луцьк", 
    "Дніпропетровська область": "Дніпро",
    "Донецька область": "Донецьк",
    "Житомирська область": "Житомир",
    "Закарпатська область": "Ужгород",
    "Запорізька область": "Запоріжжя",
    "Івано-Франківська область": "Івано-Франківськ",
    "Київська область": "Київ",
    "Кіровоградська область": "Кропивницький",
    "Луганська область": "Луганськ",
    "Львівська область": "Львів",
    "Миколаївська область": "Миколаїв",
    "Одеська область": "Одеса",
    "Полтавська область": "Полтава",
    "Рівненська область": "Рівне",
    "Сумська область": "Суми",
    "Тернопільська область": "Тернопіль",
    "Харківська область": "Харків",
    "Херсонська область": "Херсон",
    "Хмельницька область": "Хмельницький",
    "Черкаська область": "Черкаси",
    "Чернівецька область": "Чернівці",
    "Чернігівська область": "Чернігів",
    
    # Райони (частичное совпадение)
    "Вінницький район": "Вінниця",
    "Харківський район": "Харків",
    "Дніпровський район": "Дніпро", 
    "Полтавський район": "Полтава",
    "Сумський район": "Суми",
    "Чернігівський район": "Чернігів",
    "Кременчуцький район": "Кременчук",
    "Павлоградський район": "Павлоград",
    "Ізюмський район": "Ізюм",
    "Новомосковський район": "Новомосковськ",
    "Лозівський район": "Лозова",
    "Красноградський район": "Красноград",
    "Куп'янський район": "Куп'янськ",
    "Чугуївський район": "Чугуїв",
    "Звенигородський район": "Звенигородка",
    "Уманський район": "Умань",
    "Богодухівський район": "Богодухів",
    "Кам'янський район": "Кам'янське",
    "Охтирський район": "Охтирка",
    "Гайсинський район": "Гайсин",
    "Миргородський район": "Миргород",
    "Ніжинський район": "Ніжин",
    "Корюківський район": "Корюківка",
    "Роменський район": "Ромни",
    "Олександрійський район": "Олександрія",
    
    # Міста з повними назвами
    "м. Харків та Харківська територіальна громада": "Харків",
    "м. Марганець та Марганецька територіальна громада": "Марганець",
    
    # Громади
    "Червоногригорівська територіальна громада": "Червоноград",
    "Липецька територіальна громада": "Липець", 
    "Вовчанська територіальна громада": "Вовчанськ",
    
    # Альтернативные варианты для координат
    "Корюківський": "Корюківка",
    "Полтавський": "Полтава", 
    "Лозівський": "Лозова",
    "Куп'янський": "куп'янськ",  # в нижнем регистре в базе
    "Кам'янський": "кам'янське",  # в нижнем регистре в базе
    "Охтирський": "Охтирка",
    "Сумський": "Суми",
    
    # Дополнительные громады (приблизительные координаты через соседние города)
    "Червоногригорівська": "ромни",  # близко к Ромнам
    "Липецька": "суми",  # близко к Сумам
}

def smart_region_lookup(region_name, city_coords, name_region_map):
    """Умный поиск координат региона"""
    
    # 1. Точное совпадение в маппинге
    if region_name in REGION_NAME_MAPPING:
        mapped_name = REGION_NAME_MAPPING[region_name]
        # Поиск с учетом регистра
        for city_name in city_coords:
            if city_name.lower() == mapped_name.lower():
                return city_coords[city_name]
    
    # 2. Точное совпадение в координатах (с учетом регистра)
    for city_name in city_coords:
        if city_name.lower() == region_name.lower():
            return city_coords[city_name]
    
    # 3. Поиск по ключевым словам (с учетом регистра)
    key_words = extract_key_words(region_name)
    for key_word in key_words:
        for city_name in city_coords:
            if city_name.lower() == key_word.lower():
                return city_coords[city_name]
    
    # 4. Поиск в NAME_REGION_MAP
    for city, region in name_region_map.items():
        if any(word.lower() in city.lower() or word.lower() in region.lower() 
               for word in key_words):
            if city in city_coords:
                return city_coords[city]
    
    # 5. Частичное совпадение в координатах (улучшенный поиск)
    region_lower = region_name.lower()
    
    # Сначала ищем точные совпадения корня слова
    for key_word in key_words:
        key_lower = key_word.lower()
        for city_name in city_coords:
            city_lower = city_name.lower()
            # Более строгое сравнение
            if (len(key_lower) > 3 and 
                (key_lower in city_lower or city_lower in key_lower)):
                return city_coords[city_name]
    
    return None

def extract_key_words(region_name):
    """Извлечь ключевые слова из названия региона"""
    # Удаляем служебные слова
    stop_words = {
        'район', 'область', 'територіальна', 'громада', 'м.', 'та', 'і', 'та'
    }
    
    words = region_name.replace(',', ' ').split()
    key_words = []
    
    for word in words:
        clean_word = word.strip('.,()').lower()
        if clean_word not in stop_words and len(clean_word) > 2:
            key_words.append(word.strip('.,()'))
    
    return key_words

def test_region_mapping():
    """Тест маппинга регионов"""
    print("🗺️ Тестирование маппинга регионов...")
    
    # Получаем реальные тревоги
    alerts = ukraine_api.get_active_alerts()
    if not alerts:
        print("❌ Нет данных API для тестирования")
        return
    
    # Загружаем наши координаты (упрощенная версия)
    from app import CITY_COORDS, NAME_REGION_MAP
    
    found = 0
    total = 0
    
    print(f"\n📊 Анализ {len(alerts)} регионов:")
    
    for alert in alerts:
        region_name = alert.get("regionName", "")
        if not region_name:
            continue
            
        total += 1
        coords = smart_region_lookup(region_name, CITY_COORDS, NAME_REGION_MAP)
        
        if coords:
            found += 1
            print(f"✅ {region_name} -> {coords}")
        else:
            print(f"❌ {region_name} -> НЕ НАЙДЕНО")
            # Показываем ключевые слова для отладки
            key_words = extract_key_words(region_name)
            print(f"   Ключевые слова: {key_words}")
    
    print(f"\n📈 Результат: {found}/{total} ({found/total*100:.1f}%) регионов найдено")
    
    return found, total

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_region_mapping()
