#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ukraine Alert API Integration
Интеграция с официальным API тревог Украины
"""

import requests
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json

log = logging.getLogger(__name__)

class UkraineAlertAPI:
    """Класс для работы с Ukraine Alert API"""
    
    def __init__(self, api_token: str = "57fe8a39:7698ad50f0f15d502b280a83019bab25"):
        self.api_token = api_token
        self.base_url = "https://api.ukrainealarm.com"  # Правильный URL API
        self.headers = {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
            "User-Agent": "UkraineAlertMonitor/1.0"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Кэш для регионов
        self.regions_cache = {}
        self.regions_cache_time = 0
        self.cache_ttl = 3600  # 1 час
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Выполнить запрос к API"""
        try:
            url = f"{self.base_url}{endpoint}"
            log.debug(f"API Request: {url}")
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            log.error(f"API request failed for {endpoint}: {e}")
            return None
        except json.JSONDecodeError as e:
            log.error(f"JSON decode error for {endpoint}: {e}")
            return None
    
    def get_active_alerts(self) -> List[Dict]:
        """Получить все активные тревоги"""
        data = self._make_request("/api/v3/alerts")
        if data and isinstance(data, list):
            return data
        return []
    
    def get_region_alert(self, region_id: str) -> Optional[Dict]:
        """Получить статус конкретного региона"""
        data = self._make_request(f"/api/v3/alerts/{region_id}")
        if data and isinstance(data, list) and data:
            return data[0]
        return None
    
    def get_regions(self) -> Dict:
        """Получить список всех регионов с кэшированием"""
        current_time = time.time()
        
        # Проверить кэш
        if (self.regions_cache and 
            current_time - self.regions_cache_time < self.cache_ttl):
            return self.regions_cache
        
        # Обновить кэш
        data = self._make_request("/api/v3/regions")
        if data:
            self.regions_cache = data
            self.regions_cache_time = current_time
            return data
        
        return self.regions_cache  # Вернуть старый кэш при ошибке
    
    def get_alert_history_by_date(self, date_str: str) -> List[Dict]:
        """Получить историю тревог по дате (формат: YYYYMMDD)"""
        params = {"date": date_str}
        data = self._make_request("/api/v3/alerts/dateHistory", params)
        if data and isinstance(data, list):
            return data
        return []
    
    def get_region_history(self, region_id: str) -> List[Dict]:
        """Получить последние 25 тревог региона"""
        params = {"regionId": region_id}
        data = self._make_request("/api/v3/alerts/regionHistory", params)
        if data and isinstance(data, list):
            return data
        return []
    
    def get_status(self) -> Optional[int]:
        """Получить номер последней модификации для проверки обновлений"""
        data = self._make_request("/api/v3/alerts/status")
        if data and "lastActionIndex" in data:
            return data["lastActionIndex"]
        return None
    
    def setup_webhook(self, webhook_url: str) -> bool:
        """Настроить webhook для уведомлений"""
        try:
            payload = {"webHookUrl": webhook_url}
            response = self.session.post(
                f"{self.base_url}/api/v3/webhook", 
                json=payload, 
                timeout=10
            )
            response.raise_for_status()
            log.info(f"Webhook setup successful: {webhook_url}")
            return True
            
        except requests.exceptions.RequestException as e:
            log.error(f"Webhook setup failed: {e}")
            return False
    
    def convert_to_our_format(self, alert_data: Dict) -> Dict:
        """Конвертировать данные API в наш формат"""
        try:
            # Маппинг типов тревог
            alert_type_map = {
                "AIR": "air_alert",
                "ARTILLERY": "artillery",
                "URBAN_FIGHTS": "urban_fight", 
                "CHEMICAL": "chemical",
                "NUCLEAR": "nuclear",
                "INFO": "info",
                "CUSTOM": "custom",
                "UNKNOWN": "unknown"
            }
            
            # Маппинг типов регионов
            region_type_map = {
                "State": "oblast",
                "District": "raion", 
                "Community": "community",
                "CityOrVillage": "city",
                "CityDistrict": "district"
            }
            
            converted = {
                "region_id": alert_data.get("regionId"),
                "region_name": alert_data.get("regionName"),
                "region_type": region_type_map.get(alert_data.get("regionType"), "unknown"),
                "last_update": alert_data.get("lastUpdate"),
                "alerts": []
            }
            
            # Конвертировать активные тревоги
            active_alerts = alert_data.get("activeAlerts", [])
            for alert in active_alerts:
                converted_alert = {
                    "type": alert_type_map.get(alert.get("type"), "unknown"),
                    "last_update": alert.get("lastUpdate"),
                    "region_id": alert.get("regionId")
                }
                converted["alerts"].append(converted_alert)
            
            return converted
            
        except Exception as e:
            log.error(f"Conversion error: {e}")
            return {}
    
    def get_alerts_for_map(self) -> List[Dict]:
        """Получить тревоги в формате для отображения на карте"""
        alerts = self.get_active_alerts()
        map_alerts = []
        
        for alert_data in alerts:
            converted = self.convert_to_our_format(alert_data)
            if converted and converted["alerts"]:
                # Только активные тревоги
                for alert in converted["alerts"]:
                    map_alert = {
                        "id": f"api_{converted['region_id']}_{alert['type']}",
                        "region": converted["region_name"],
                        "region_type": converted["region_type"],
                        "alert_type": alert["type"],
                        "timestamp": alert["last_update"],
                        "source": "ukraine_alert_api"
                    }
                    map_alerts.append(map_alert)
        
        return map_alerts


# Глобальный экземпляр API
ukraine_api = UkraineAlertAPI()


def get_api_alerts_for_map():
    """Получить тревоги из API в формате для карты"""
    alerts = ukraine_api.get_active_alerts()
    if not alerts:
        return []
    
    map_markers = []
    current_time = time.time()
    
    # Импортируем функцию маппинга
    try:
        from region_mapping import smart_region_lookup
        from app import CITY_COORDS, NAME_REGION_MAP
    except ImportError:
        log.warning("Region mapping not available, using basic lookup")
        smart_region_lookup = None
        CITY_COORDS = {}
        NAME_REGION_MAP = {}
    
    for alert_data in alerts:
        region_name = alert_data.get("regionName", "Unknown")
        region_id = alert_data.get("regionId", "unknown")
        region_type = alert_data.get("regionType", "unknown")
        
        # Получаем координаты с помощью умного маппинга
        coords = None
        if smart_region_lookup:
            coords = smart_region_lookup(region_name, CITY_COORDS, NAME_REGION_MAP)
        
        # Пропускаем регионы без координат
        if not coords:
            log.debug(f"No coordinates found for region: {region_name}")
            continue
            
        active_alerts = alert_data.get("activeAlerts", [])
        
        for alert in active_alerts:
            alert_type = alert.get("type", "UNKNOWN")
            last_update = alert.get("lastUpdate", "")
            
            # Маппинг типов для иконок
            icon_type = {
                "AIR": "air_alert",
                "ARTILLERY": "artillery", 
                "URBAN_FIGHTS": "urban_combat",
                "CHEMICAL": "chemical",
                "NUCLEAR": "nuclear"
            }.get(alert_type, "general")
            
            # Создаем маркер с координатами
            marker = {
                "id": f"api_{region_id}_{alert_type}",
                "lat": coords[0],
                "lng": coords[1],
                "region": region_name,
                "threat_type": icon_type,
                "message": f"🚨 {region_name} - {alert_type}",
                "timestamp": last_update,
                "source": "ukraine_alert_api",
                "region_type": region_type.lower(),
                "api_data": {
                    "region_id": region_id,
                    "alert_type": alert_type,
                    "last_update": last_update
                }
            }
            
            map_markers.append(marker)
    
    return map_markers


def test_api_connection():
    """Тестовая функция для проверки подключения к API"""
    print("🔍 Тестирование Ukraine Alert API...")
    
    # Тест получения статуса
    status = ukraine_api.get_status()
    print(f"📊 Статус API: {status}")
    
    # Тест получения активных тревог
    alerts = ukraine_api.get_active_alerts()
    print(f"🚨 Активных тревог: {len(alerts) if alerts else 0}")
    
    # Тест получения регионов
    regions = ukraine_api.get_regions()
    if regions and "states" in regions:
        print(f"🏘️ Регионов в базе: {len(regions['states'])}")
    
    # Показать пример данных
    if alerts:
        print("\n📋 Пример данных тревоги:")
        example = alerts[0] if alerts else {}
        for key, value in example.items():
            print(f"   {key}: {value}")
    
    return bool(alerts)


if __name__ == "__main__":
    # Тестирование API
    logging.basicConfig(level=logging.DEBUG)
    test_api_connection()
