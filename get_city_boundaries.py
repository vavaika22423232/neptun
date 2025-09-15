#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для получения границ украинских городов из OpenStreetMap
через Overpass API и сохранения в GeoJSON формате
"""

import requests
import json
import time
from typing import Dict, List, Optional

class CityBoundariesCollector:
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.delay = 1  # Задержка между запросами в секундах
        
    def get_city_boundary(self, city_name: str, region: str = None) -> Optional[Dict]:
        """
        Получить границы города через Overpass API
        """
        # Запрос для поиска административных границ города
        query = f"""
        [out:json][timeout:25];
        (
          relation["name"="{city_name}"]["admin_level"~"^(8|9|10)$"]["place"~"^(city|town)$"];
          relation["name"="{city_name}"]["boundary"="administrative"]["admin_level"~"^(8|9|10)$"];
        );
        out geom;
        """
        
        try:
            response = requests.post(
                self.overpass_url,
                data={'data': query},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('elements'):
                # Преобразуем первый найденный элемент в GeoJSON
                element = data['elements'][0]
                return self.convert_to_geojson(element, city_name)
            
        except Exception as e:
            print(f"Ошибка при получении границ для {city_name}: {e}")
            
        return None
    
    def convert_to_geojson(self, osm_element: Dict, city_name: str) -> Dict:
        """
        Конвертировать OSM элемент в GeoJSON Feature
        """
        coordinates = []
        
        if osm_element.get('type') == 'relation':
            # Для отношений (relations) обрабатываем члены
            for member in osm_element.get('members', []):
                if member.get('type') == 'way' and member.get('geometry'):
                    way_coords = [[node['lon'], node['lat']] for node in member['geometry']]
                    coordinates.extend(way_coords)
        
        if coordinates:
            # Замыкаем полигон если нужно
            if coordinates[0] != coordinates[-1]:
                coordinates.append(coordinates[0])
            
            return {
                "type": "Feature",
                "properties": {
                    "name": city_name,
                    "osm_id": osm_element.get('id'),
                    "admin_level": osm_element.get('tags', {}).get('admin_level'),
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                }
            }
        
        return None
    
    def process_cities_from_json(self, json_file: str, output_file: str, limit: int = None):
        """
        Обработать города из существующего JSON файла
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            cities_data = json.load(f)
        
        # Получаем уникальные города
        unique_cities = {}
        for item in cities_data:
            if item['object_category'] in ['МІСТО', 'СМТ']:  # Только города и поселки городского типа
                city_name = item['object_name']
                region = item['region']
                unique_cities[city_name] = region
        
        print(f"Найдено {len(unique_cities)} уникальных городов")
        
        # Ограничиваем количество для тестирования
        if limit:
            unique_cities = dict(list(unique_cities.items())[:limit])
            print(f"Обрабатываем первые {limit} городов")
        
        features = []
        processed = 0
        
        for city_name, region in unique_cities.items():
            print(f"Обрабатываем: {city_name} ({region})")
            
            boundary = self.get_city_boundary(city_name, region)
            if boundary:
                features.append(boundary)
                print(f"✓ Найдены границы для {city_name}")
            else:
                print(f"✗ Границы не найдены для {city_name}")
            
            processed += 1
            time.sleep(self.delay)  # Уважаем лимиты API
            
            if processed % 10 == 0:
                print(f"Обработано {processed}/{len(unique_cities)} городов")
        
        # Сохраняем результат в GeoJSON
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        
        print(f"Сохранено {len(features)} границ городов в {output_file}")

def main():
    collector = CityBoundariesCollector()
    
    # Тестовый запуск на первых 5 городах
    collector.process_cities_from_json(
        'city_ukraine.json',
        'ukraine_city_boundaries.geojson',
        limit=5  # Уберите этот параметр для обработки всех городов
    )

if __name__ == "__main__":
    main()
