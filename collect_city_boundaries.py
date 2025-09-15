#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Рабочий скрипт для получения границ украинских городов через Overpass API
"""

import requests
import json
import time
from typing import Dict, List, Optional
import random

class WorkingCityBoundariesCollector:
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.delay_min = 2  # Минимальная задержка
        self.delay_max = 5  # Максимальная задержка
        self.headers = {
            'User-Agent': 'NEPTUN-Ukraine-App/1.0 (https://github.com/vavaika22423232/neptun)'
        }
        
    def get_random_delay(self):
        """Случайная задержка между запросами"""
        return random.uniform(self.delay_min, self.delay_max)
        
    def get_city_boundary(self, city_name: str) -> Optional[Dict]:
        """
        Получить границы города через Overpass API
        """
        # Более точный запрос
        query = f"""
        [out:json][timeout:30];
        (
          relation["name"="{city_name}"]["place"~"^(city|town)$"];
          relation["name"="{city_name}"]["boundary"="administrative"]["admin_level"~"^(8|9|10)$"];
        );
        out geom;
        """
        
        try:
            print(f"  Запрос границ для: {city_name}")
            
            response = requests.post(
                self.overpass_url,
                data={'data': query},
                timeout=45,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            elements = data.get('elements', [])
            if elements:
                # Берем первый найденный элемент
                element = elements[0]
                geojson_feature = self.osm_to_geojson(element, city_name)
                
                if geojson_feature:
                    print(f"  ✓ Найдены границы для {city_name}")
                    return geojson_feature
                else:
                    print(f"  ✗ Не удалось преобразовать данные для {city_name}")
            else:
                print(f"  ✗ Границы не найдены для {city_name}")
                
        except Exception as e:
            print(f"  ✗ Ошибка для {city_name}: {e}")
            
        return None
    
    def osm_to_geojson(self, osm_element: Dict, city_name: str) -> Optional[Dict]:
        """
        Преобразовать OSM relation в GeoJSON Feature
        """
        try:
            if osm_element.get('type') != 'relation':
                return None
            
            # Собираем все координаты из members
            all_ways = []
            
            for member in osm_element.get('members', []):
                if member.get('type') == 'way' and member.get('role') == 'outer':
                    geometry = member.get('geometry', [])
                    if geometry:
                        way_coords = [[point['lon'], point['lat']] for point in geometry]
                        all_ways.append(way_coords)
            
            if not all_ways:
                return None
            
            # Создаем мультиполигон или простой полигон
            if len(all_ways) == 1:
                # Простой полигон
                coords = all_ways[0]
                # Замыкаем полигон если нужно
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                
                geometry = {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            else:
                # Мультиполигон
                polygons = []
                for way in all_ways:
                    if way[0] != way[-1]:
                        way.append(way[0])
                    polygons.append([way])
                
                geometry = {
                    "type": "MultiPolygon", 
                    "coordinates": polygons
                }
            
            feature = {
                "type": "Feature",
                "properties": {
                    "name": city_name,
                    "osm_id": osm_element.get('id'),
                    "osm_type": "relation",
                    "admin_level": osm_element.get('tags', {}).get('admin_level'),
                    "place": osm_element.get('tags', {}).get('place'),
                    "population": osm_element.get('tags', {}).get('population'),
                    "bounds": osm_element.get('bounds', {})
                },
                "geometry": geometry
            }
            
            return feature
            
        except Exception as e:
            print(f"    Ошибка преобразования для {city_name}: {e}")
            return None
    
    def process_major_cities(self):
        """
        Обработать основные украинские города
        """
        major_cities = [
            "Київ", "Харків", "Одеса", "Дніпро", "Донецьк", "Запоріжжя",
            "Львів", "Кривий Ріг", "Миколаїв", "Маріуполь", "Луганськ",
            "Вінниця", "Макіївка", "Севастополь", "Сімферополь", "Херсон",
            "Полтава", "Чернігів", "Черкаси", "Житомир", "Суми", "Хмельницький",
            "Чернівці", "Горлівка", "Рівне", "Кропивницький", "Івано-Франківськ",
            "Кременчук", "Тернопіль", "Луцьк"
        ]
        
        print(f"Обрабатываем {len(major_cities)} основных городов Украины")
        
        features = []
        successful = 0
        
        for i, city in enumerate(major_cities, 1):
            print(f"\n[{i}/{len(major_cities)}] Обрабатываем: {city}")
            
            boundary = self.get_city_boundary(city)
            if boundary:
                features.append(boundary)
                successful += 1
            
            # Случайная задержка между запросами
            if i < len(major_cities):
                delay = self.get_random_delay()
                print(f"  Пауза {delay:.1f} сек...")
                time.sleep(delay)
        
        # Сохраняем результат
        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_cities": len(major_cities),
                "successful": successful,
                "source": "OpenStreetMap via Overpass API"
            }
        }
        
        output_file = 'ukraine_major_cities_boundaries.geojson'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        
        print(f"\n=== Результат ===")
        print(f"Обработано городов: {len(major_cities)}")
        print(f"Найдены границы: {successful}")
        print(f"Процент успеха: {successful/len(major_cities)*100:.1f}%")
        print(f"Файл сохранен: {output_file}")
        
        return geojson

def main():
    collector = WorkingCityBoundariesCollector()
    
    print("=== Сбор границ основных украинских городов ===")
    print("Используем Overpass API (OpenStreetMap)")
    print("Это может занять несколько минут...")
    
    try:
        result = collector.process_major_cities()
        
        if result['features']:
            print(f"\n✓ Успешно получены границы для {len(result['features'])} городов")
            print("Теперь можно использовать файл ukraine_major_cities_boundaries.geojson")
        else:
            print("\n✗ Границы городов не найдены")
            
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        print(f"\nОшибка: {e}")

if __name__ == "__main__":
    main()
