#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демо-данные для тестирования Ukraine Alert API
"""

def get_demo_api_data():
    """Возвращает демо-данные для тестирования отображения API маркеров"""
    return [
        {
            "id": "demo_kyiv_air",
            "lat": 50.4501,
            "lng": 30.5234,
            "region": "м. Київ",
            "threat_type": "air_alert",
            "message": "🚨 м. Київ - AIR ALERT",
            "timestamp": "2025-09-29T18:40:00Z",
            "source": "ukraine_alert_api_demo",
            "region_type": "city",
            "api_data": {
                "region_id": "demo_kyiv",
                "alert_type": "AIR",
                "last_update": "2025-09-29T18:40:00Z"
            }
        },
        {
            "id": "demo_kharkiv_artillery", 
            "lat": 49.9935,
            "lng": 36.2304,
            "region": "м. Харків",
            "threat_type": "artillery",
            "message": "🚨 м. Харків - ARTILLERY",
            "timestamp": "2025-09-29T18:35:00Z",
            "source": "ukraine_alert_api_demo",
            "region_type": "city",
            "api_data": {
                "region_id": "demo_kharkiv",
                "alert_type": "ARTILLERY", 
                "last_update": "2025-09-29T18:35:00Z"
            }
        },
        {
            "id": "demo_dnipro_air",
            "lat": 48.4647,
            "lng": 35.0462,
            "region": "м. Дніпро",
            "threat_type": "air_alert",
            "message": "🚨 м. Дніпро - AIR ALERT",
            "timestamp": "2025-09-29T18:38:00Z",
            "source": "ukraine_alert_api_demo",
            "region_type": "city",
            "api_data": {
                "region_id": "demo_dnipro",
                "alert_type": "AIR",
                "last_update": "2025-09-29T18:38:00Z"
            }
        },
        {
            "id": "demo_odesa_air",
            "lat": 46.4825,
            "lng": 30.7233,
            "region": "м. Одеса",
            "threat_type": "air_alert", 
            "message": "🚨 м. Одеса - AIR ALERT",
            "timestamp": "2025-09-29T18:42:00Z",
            "source": "ukraine_alert_api_demo",
            "region_type": "city",
            "api_data": {
                "region_id": "demo_odesa",
                "alert_type": "AIR",
                "last_update": "2025-09-29T18:42:00Z"
            }
        },
        {
            "id": "demo_lviv_air",
            "lat": 49.8397,
            "lng": 24.0297,
            "region": "м. Львів",
            "threat_type": "air_alert",
            "message": "🚨 м. Львів - AIR ALERT", 
            "timestamp": "2025-09-29T18:45:00Z",
            "source": "ukraine_alert_api_demo",
            "region_type": "city",
            "api_data": {
                "region_id": "demo_lviv",
                "alert_type": "AIR",
                "last_update": "2025-09-29T18:45:00Z"
            }
        },
        {
            "id": "demo_mariupol_urban",
            "lat": 47.0956,
            "lng": 37.5431,
            "region": "м. Маріуполь",
            "threat_type": "urban_combat",
            "message": "🚨 м. Маріуполь - URBAN FIGHTS",
            "timestamp": "2025-09-29T17:30:00Z",
            "source": "ukraine_alert_api_demo", 
            "region_type": "city",
            "api_data": {
                "region_id": "demo_mariupol",
                "alert_type": "URBAN_FIGHTS",
                "last_update": "2025-09-29T17:30:00Z"
            }
        }
    ]

if __name__ == "__main__":
    data = get_demo_api_data()
    print(f"✅ Демо-данных: {len(data)}")
    for item in data:
        print(f"📍 {item['region']} ({item['lat']}, {item['lng']}) - {item['threat_type']}")
