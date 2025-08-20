import logging
import json
import os
from typing import Optional, Tuple
from coord_utils import validate_coords

# Настройка логирования
logger = logging.getLogger(__name__)

# Загрузка кэшей и конфигурации
def load_cache(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return {}
    return {}

import os
DATA_DIR = os.environ.get('DATA_DIR', '/data')
GEOCODING_CACHE = load_cache(os.path.join(DATA_DIR, 'geocoding_cache.json'))
MANUAL_COORDS = load_cache(os.path.join(DATA_DIR, 'manual_coords.json'))

def save_geocoding_cache():
    with open(os.path.join(DATA_DIR, 'geocoding_cache.json'), 'w', encoding='utf-8') as f:
        json.dump(GEOCODING_CACHE, f, ensure_ascii=False, indent=2)

# Импорт констант
from constants import (
    PRIORITY_LOCATIONS,
    DNZP_PRIORITY,
    normalize_place_name,
    get_region_for_place
)

# Импорт функции геокодирования
from opencage import geocode_place_opencage

def get_location_coords(place: str) -> Optional[Tuple[float, float]]:
    """
    Получает координаты для места с учетом различных источников данных.
    
    Args:
        place: название места
        
    Returns:
        tuple[float, float]|None: кортеж (lat, lng) или None если координаты не найдены
    """
    # Нормализуем название места
    normalized = normalize_place_name(place)
    
    # 1. Проверяем приоритетные локации
    if normalized in PRIORITY_LOCATIONS:
        return PRIORITY_LOCATIONS[normalized]
    
    # 2. Проверяем ручные координаты
    if normalized in MANUAL_COORDS:
        return MANUAL_COORDS[normalized]
    
    # 3. Проверяем кэш геокодирования
    if normalized in GEOCODING_CACHE:
        return GEOCODING_CACHE[normalized]
    
    # 4. Проверяем регион и специальные зоны
    region = get_region_for_place(place)
    
    query = place
    if region:
        query = f"{place}, {region}"
    elif normalized in DNZP_PRIORITY:
        query = f"{place}, {DNZP_PRIORITY[normalized]}"
    
    # 5. Пробуем геокодирование
    coords = geocode_place_opencage(query)
    
    if coords and validate_coords(*coords):
        # Сохраняем в кэш
        GEOCODING_CACHE[normalized] = coords
        return coords
    
    # 6. Логируем неудачу для ручного добавления
    logger.warning(f"Could not find coordinates for: {place}")
    with open(os.path.join(DATA_DIR, 'not_found_places.log'), 'a', encoding='utf-8') as f:
        f.write(f"{place}|{region if region else 'unknown'}\n")
    
    return None
