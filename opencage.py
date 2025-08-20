import requests
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

OPENCAGE_API_KEY = os.getenv('OPENCAGE_API_KEY', '30263924aa374a45a8b1b0469cb8d347')
import os
DATA_DIR = os.environ.get('DATA_DIR', '/data')
CACHE_FILE = os.path.join(DATA_DIR, 'opencage_cache.json')
CACHE_TTL = 60 * 60 * 24 * 30  # 30 days

def geocode_place_opencage(place):
    """
    Геокодирует место через OpenCage API с кэшированием.
    
    Args:
        place: название места для геокодирования
        
    Returns:
        tuple[float, float]|None: координаты (lat, lng) или None если не найдено
    """
    # Загрузка кэша
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
    
    # Проверка кэша
    key = place.strip().lower()
    now = int(time.time())
    
    if key in cache:
        entry = cache[key]
        if entry['coords'] and (now - entry.get('ts', 0) < CACHE_TTL):
            return tuple(entry['coords'])
        if entry['coords'] is None and (now - entry.get('ts', 0) < 3600):
            return None
    
    # Запрос к API
    try:
        url = 'https://api.opencagedata.com/geocode/v1/json'
        params = {
            'q': place,
            'key': OPENCAGE_API_KEY,
            'language': 'uk',
            'limit': 1,
            'countrycode': 'ua'  # ограничиваем поиск Украиной
        }
        
        resp = requests.get(url, params=params, timeout=7)
        
        if resp.status_code == 200:
            data = resp.json()
            if data['results']:
                loc = data['results'][0]['geometry']
                coords = (loc['lat'], loc['lng'])
                
                # Сохраняем в кэш
                cache[key] = {'ts': now, 'coords': coords}
                with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, ensure_ascii=False, indent=2)
                
                return coords
            
            # Не найдено
            cache[key] = {'ts': now, 'coords': None}
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            return None
            
    except Exception as e:
        logger.error(f"OpenCage geocoding error for '{place}': {e}")
    
    # Сохраняем неудачный результат
    cache[key] = {'ts': now, 'coords': None}
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    return None
