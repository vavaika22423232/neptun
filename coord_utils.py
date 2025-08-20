import math
from math import radians, degrees, cos, sin, asin, sqrt, atan2

def validate_coords(lat, lng):
    """
    Строгая валидация координат с учетом границ Украины и прилегающих территорий.
    """
    # Границы для Украины и прилегающих территорий с небольшим запасом
    LAT_MIN = 44.0  # Южная граница (Черное море)
    LAT_MAX = 53.0  # Северная граница
    LNG_MIN = 22.0  # Западная граница
    LNG_MAX = 41.0  # Восточная граница
    
    # Специальные зоны для военных объектов за пределами Украины
    SPECIAL_ZONES = [
        # Энгельс-2, Россия
        {'lat_min': 51.0, 'lat_max': 52.0, 'lng_min': 45.5, 'lng_max': 47.0},
        # Воронеж, Россия
        {'lat_min': 51.0, 'lat_max': 52.0, 'lng_min': 38.5, 'lng_max': 40.0},
    ]
    
    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        return False
        
    # Проверка на NaN и inf
    if not (isinstance(lat, (int, float)) and isinstance(lng, (int, float))):
        return False
    if math.isnan(lat) or math.isnan(lng) or math.isinf(lat) or math.isinf(lng):
        return False
        
    # Основная проверка для территории Украины
    if LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX:
        return True
        
    # Проверка специальных зон
    for zone in SPECIAL_ZONES:
        if zone['lat_min'] <= lat <= zone['lat_max'] and zone['lng_min'] <= lng <= zone['lng_max']:
            return True
            
    return False

def adjust_coords_for_clustering(lat, lng, existing_markers, min_distance_km=2):
    """
    Корректирует координаты, чтобы избежать наложения маркеров.
    """
    from math import radians, cos, sin, asin, sqrt
    
    def haversine(lat1, lon1, lat2, lon2):
        """
        Рассчитывает расстояние между двумя точками в км.
        """
        R = 6371  # радиус Земли в км
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return R * c
    
    def get_offset_coords(lat, lng, distance_km, angle):
        """
        Возвращает новые координаты, смещенные на заданное расстояние под заданным углом.
        """
        R = 6371  # радиус Земли в км
        d = distance_km / R  # угловое расстояние в радианах
        
        lat1 = radians(lat)
        lng1 = radians(lng)
        angle = radians(angle)
        
        lat2 = asin(sin(lat1) * cos(d) + cos(lat1) * sin(d) * cos(angle))
        lng2 = lng1 + atan2(sin(angle) * sin(d) * cos(lat1), cos(d) - sin(lat1) * sin(lat2))
        
        return degrees(lat2), degrees(lng2)
    
    if not existing_markers:
        return lat, lng
    
    # Проверяем расстояние до существующих маркеров
    for marker in existing_markers:
        dist = haversine(lat, lng, marker['lat'], marker['lng'])
        if dist < min_distance_km:
            # Если маркеры слишком близко, смещаем новый маркер
            angles = [0, 45, 90, 135, 180, 225, 270, 315]  # возможные углы смещения
            for angle in angles:
                new_lat, new_lng = get_offset_coords(lat, lng, min_distance_km, angle)
                # Проверяем, что новые координаты валидны и не конфликтуют с другими маркерами
                if validate_coords(new_lat, new_lng):
                    conflict = False
                    for m in existing_markers:
                        if haversine(new_lat, new_lng, m['lat'], m['lng']) < min_distance_km:
                            conflict = True
                            break
                    if not conflict:
                        return new_lat, new_lng
            
            # Если не нашли подходящее смещение, увеличиваем расстояние
            return adjust_coords_for_clustering(lat, lng, existing_markers, min_distance_km + 1)
    
    return lat, lng
