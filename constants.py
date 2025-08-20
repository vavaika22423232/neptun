# Центры областей Украины
OBLAST_CENTERS = {
    'черниговская': (51.4982, 31.2893),
    'чернігівська': (51.4982, 31.2893),
    'киевская': (50.4501, 30.5234),
    'київська': (50.4501, 30.5234),
    # ... остальные области добавляются аналогично ...
}

# Приоритетные локации с координатами
PRIORITY_LOCATIONS = {
    # Областные центры
    "київ": (50.4501, 30.5234),
    "одеса": (46.4825, 30.7233),
    "львів": (49.8397, 24.0297),
    "харків": (49.9935, 36.2304),
    # ... остальные локации добавляются аналогично ...
}

# Приоритетные топонимы для областей
DNZP_PRIORITY = {
    "славгород": "Дніпропетровська область",
    "чаплі": "Дніпропетровська область",
    # ... остальные топонимы добавляются аналогично ...
}

def normalize_place_name(name):
    """Нормализует название места для сравнения"""
    import re
    from unidecode import unidecode
    
    # Функция очистки названия от артефактов
    def clean_name(n):
        n = n.lower().strip()
        n = re.sub(r'\s+', ' ', n)  # множественные пробелы
        n = n.replace('`', "'")  # разные апострофы
        n = n.replace('´', "'")
        n = n.replace('"', "'")
        n = re.sub(r'[\(\)\[\]\{\}]', '', n)  # скобки
        return n
    
    name = clean_name(unidecode(name))
    return name

def get_region_for_place(place):
    """Определяет область для места"""
    normalized = normalize_place_name(place)
    
    # Проверяем прямое совпадение
    region = DNZP_PRIORITY.get(normalized)
    if region:
        return region
    
    # Проверяем по словарю городов
    from city_to_region import CITY_TO_REGION
    region = CITY_TO_REGION.get(normalized)
    if region:
        return region
    
    return None
