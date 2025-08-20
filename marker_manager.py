import json
import logging
import time
from coord_utils import validate_coords, adjust_coords_for_clustering

logger = logging.getLogger(__name__)

class MarkerManager:
    def __init__(self):
        self.existing_markers = []
        self.hidden_markers = self.load_hidden_markers()
import os

class MarkerManager:
    def __init__(self):
        self.data_dir = os.environ.get('DATA_DIR', '/data')
        self.existing_markers = []
        self.hidden_markers = self.load_hidden_markers()

    def load_hidden_markers(self):
        path = os.path.join(self.data_dir, 'hidden_markers.json')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_hidden_markers(self):
        path = os.path.join(self.data_dir, 'hidden_markers.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.hidden_markers, f, ensure_ascii=False, indent=2)
    
    def load_hidden_markers(self):
        try:
            path = os.path.join(self.data_dir, 'hidden_markers.json')
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def save_hidden_markers(self):
        path = os.path.join(self.data_dir, 'hidden_markers.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.hidden_markers, f, ensure_ascii=False, indent=2)
    
    def is_marker_hidden(self, lat, lng, text, source):
        """Проверяет, скрыт ли маркер пользователем"""
        marker_key = f"{round(lat, 3)},{round(lng, 3)}|{text}|{source}"
        return marker_key in self.hidden_markers
    
    def hide_marker(self, lat, lng, text, source):
        """Скрывает маркер по запросу пользователя"""
        marker_key = f"{round(lat, 3)},{round(lng, 3)}|{text}|{source}"
        if marker_key not in self.hidden_markers:
            self.hidden_markers.append(marker_key)
            self.save_hidden_markers()
    
    def add_marker(self, lat, lng, text, threat_type=None, source=None, direction=None):
        """
        Добавляет новый маркер с проверкой валидности и кластеризацией
        
        Args:
            lat, lng: координаты
            text: текст сообщения
            threat_type: тип угрозы (shahed, raketa, avia и т.д.)
            source: источник сообщения
            direction: направление движения (для шахедов/ракет)
        
        Returns:
            dict с информацией о маркере или None если маркер невалиден
        """
        # Базовая валидация
        if not validate_coords(lat, lng):
            logger.warning(f"Invalid coordinates: {lat}, {lng}")
            return None
            
        # Проверка на скрытый маркер
        if self.is_marker_hidden(lat, lng, text, source):
            logger.info(f"Marker is hidden by user: {lat}, {lng}")
            return None
            
        # Корректировка координат для избежания наложения
        adj_lat, adj_lng = adjust_coords_for_clustering(lat, lng, self.existing_markers)
        
        # Создаем маркер с дополнительной информацией
        marker = {
            'lat': adj_lat,
            'lng': adj_lng,
            'text': text,
            'threat_type': threat_type or 'unknown',
            'source': source,
            'timestamp': int(time.time())
        }
        
        # Добавляем информацию о направлении движения для определенных типов угроз
        if direction and threat_type in ['shahed', 'raketa', 'avia']:
            try:
                dir_lat, dir_lng = direction
                if validate_coords(dir_lat, dir_lng):
                    marker['lat2'] = dir_lat
                    marker['lng2'] = dir_lng
            except (ValueError, TypeError):
                pass
        
        self.existing_markers.append(marker)
        return marker
    
    def clear_old_markers(self, max_age_minutes=120):
        """Очищает старые маркеры"""
        current_time = time.time()
        self.existing_markers = [
            m for m in self.existing_markers
            if (current_time - m['timestamp']) < (max_age_minutes * 60)
        ]
    
    def get_markers(self, time_range_minutes=120, threat_type=None):
        """
        Возвращает отфильтрованные маркеры
        
        Args:
            time_range_minutes: максимальный возраст маркеров в минутах
            threat_type: фильтр по типу угрозы
        """
        current_time = time.time()
        markers = []
        
        for marker in self.existing_markers:
            # Проверка времени
            if (current_time - marker['timestamp']) > (time_range_minutes * 60):
                continue
                
            # Проверка типа угрозы
            if threat_type and marker['threat_type'] != threat_type:
                continue
                
            markers.append(marker)
        
        return markers
