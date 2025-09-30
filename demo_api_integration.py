#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальный демо интеграции Ukraine Alert API
"""

from ukraine_alert_api import get_api_alerts_for_map
import json

def demo_api_integration():
    """Демонстрация работы API интеграции"""
    print("🇺🇦 Ukraine Alert API - Финальная демонстрация")
    print("=" * 60)
    
    # Получаем маркеры
    markers = get_api_alerts_for_map()
    
    if not markers:
        print("❌ Маркеры не получены (возможно, проблема с API)")
        return
    
    print(f"✅ Получено маркеров: {len(markers)}")
    print(f"📊 Статистика по типам тревог:")
    
    # Статистика по типам
    types_count = {}
    regions_count = {}
    
    for marker in markers:
        threat_type = marker.get('threat_type', 'unknown')
        region = marker.get('region', 'Unknown')
        
        types_count[threat_type] = types_count.get(threat_type, 0) + 1
        regions_count[region] = regions_count.get(region, 0) + 1
    
    for threat_type, count in sorted(types_count.items()):
        icon = {
            'air_alert': '✈️',
            'artillery': '💥', 
            'urban_combat': '🏙️',
            'chemical': '☢️',
            'nuclear': '☢️'
        }.get(threat_type, '⚠️')
        print(f"   {icon} {threat_type}: {count}")
    
    print(f"\n📍 Примеры маркеров на карте:")
    for i, marker in enumerate(markers[:5]):
        print(f"   {i+1}. {marker['region']}")
        print(f"      📍 {marker['lat']:.4f}, {marker['lng']:.4f}")
        print(f"      🚨 {marker['threat_type']} - {marker['timestamp']}")
        print()
    
    print(f"📈 Покрытие: {len(markers)} из доступных тревог отображены на карте")
    
    # Показать JSON для первого маркера
    if markers:
        print("🔧 Пример JSON маркера:")
        example = {k: v for k, v in markers[0].items() if k != 'api_data'}
        print(json.dumps(example, indent=2, ensure_ascii=False))
    
    print("\n🚀 Интеграция готова к продакшену!")
    return markers

if __name__ == "__main__":
    demo_api_integration()
