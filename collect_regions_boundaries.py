#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для получения границ украинских областей (регионов)
"""

import requests
import json
import time
from typing import Dict, List, Optional
import random

class UkrainianRegionsBoundariesCollector:
    def __init__(self):
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.delay_min = 3  # Более длительная задержка для крупных запросов
        self.delay_max = 6
        self.headers = {
            'User-Agent': 'NEPTUN-Ukraine-App/1.0 (https://github.com/vavaika22423232/neptun)'
        }
        
    def get_random_delay(self):
        """Случайная задержка между запросами"""
        return random.uniform(self.delay_min, self.delay_max)
        
    def get_region_boundary(self, region_name: str) -> Optional[Dict]:
        """
        Получить границы области через Overpass API
        """
        # Запрос для областей (admin_level=4 для областей Украины)
        query = f"""
        [out:json][timeout:60];
        (
          relation["name"="{region_name}"]["boundary"="administrative"]["admin_level"="4"]["place"!="city"];
          relation["name"="{region_name} область"]["boundary"="administrative"]["admin_level"="4"];
          relation["name"="{region_name}"]["boundary"="administrative"]["admin_level"="6"];
        );
        out geom;
        """
        
        try:
            print(f"  Запрос границ для області: {region_name}")
            
            response = requests.post(
                self.overpass_url,
                data={'data': query},
                timeout=90,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            elements = data.get('elements', [])
            if elements:
                # Берем самый подходящий элемент (с наибольшим количеством членов)
                best_element = max(elements, key=lambda x: len(x.get('members', [])))
                geojson_feature = self.osm_to_geojson(best_element, region_name)
                
                if geojson_feature:
                    print(f"  ✓ Найдены границы для {region_name}")
                    return geojson_feature
                else:
                    print(f"  ✗ Не удалось преобразовать данные для {region_name}")
            else:
                print(f"  ✗ Границы не найдены для {region_name}")
                
        except Exception as e:
            print(f"  ✗ Ошибка для {region_name}: {e}")
            
        return None
    
    def osm_to_geojson(self, osm_element: Dict, region_name: str) -> Optional[Dict]:
        """
        Преобразовать OSM relation в GeoJSON Feature
        """
        try:
            if osm_element.get('type') != 'relation':
                return None
            
            # Собираем все координаты из members
            outer_ways = []
            inner_ways = []
            
            for member in osm_element.get('members', []):
                if member.get('type') == 'way' and member.get('geometry'):
                    way_coords = [[point['lon'], point['lat']] for point in member['geometry']]
                    
                    if member.get('role') == 'outer':
                        outer_ways.append(way_coords)
                    elif member.get('role') == 'inner':
                        inner_ways.append(way_coords)
                    else:
                        # Если роль не указана, считаем outer
                        outer_ways.append(way_coords)
            
            if not outer_ways:
                return None
            
            # Создаем геометрию
            coordinates = []
            
            # Добавляем внешние границы
            for way in outer_ways:
                if way[0] != way[-1]:
                    way.append(way[0])  # Замыкаем полигон
                coordinates.append(way)
            
            # Добавляем внутренние границы (дыры)
            for way in inner_ways:
                if way[0] != way[-1]:
                    way.append(way[0])
                coordinates.append(way)
            
            geometry = {
                "type": "Polygon",
                "coordinates": coordinates
            }
            
            # Если несколько внешних границ, создаем MultiPolygon
            if len(outer_ways) > 1:
                polygons = []
                for way in outer_ways:
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
                    "name": region_name,
                    "name_uk": region_name,
                    "osm_id": osm_element.get('id'),
                    "osm_type": "relation", 
                    "admin_level": osm_element.get('tags', {}).get('admin_level'),
                    "population": osm_element.get('tags', {}).get('population'),
                    "area": osm_element.get('tags', {}).get('area'),
                    "bounds": osm_element.get('bounds', {}),
                    "type": "region"
                },
                "geometry": geometry
            }
            
            return feature
            
        except Exception as e:
            print(f"    Ошибка преобразования для {region_name}: {e}")
            return None
    
    def process_ukrainian_regions(self):
        """
        Обработать все области Украины
        """
        ukrainian_regions = [
            "Вінницька область",
            "Волинська область", 
            "Дніпропетровська область",
            "Донецька область",
            "Житомирська область",
            "Закарпатська область",
            "Запорізька область",
            "Івано-Франківська область",
            "Київська область",
            "Кіровоградська область",
            "Луганська область",
            "Львівська область",
            "Миколаївська область",
            "Одеська область",
            "Полтавська область",
            "Рівненська область",
            "Сумська область",
            "Тернопільська область",
            "Харківська область",
            "Херсонська область",
            "Хмельницька область",
            "Черкаська область",
            "Чернівецька область",
            "Чернігівська область",
            "Автономна Республіка Крим"
        ]
        
        print(f"Обрабатываем {len(ukrainian_regions)} областей Украины")
        
        features = []
        successful = 0
        
        for i, region in enumerate(ukrainian_regions, 1):
            print(f"\n[{i}/{len(ukrainian_regions)}] Обрабатываем: {region}")
            
            boundary = self.get_region_boundary(region)
            if boundary:
                features.append(boundary)
                successful += 1
            
            # Задержка между запросами
            if i < len(ukrainian_regions):
                delay = self.get_random_delay()
                print(f"  Пауза {delay:.1f} сек...")
                time.sleep(delay)
        
        # Добавляем города особого статуса
        special_cities = ["Київ", "Севастополь"]
        for city in special_cities:
            print(f"\n[Спецстатус] Обрабатываем: {city}")
            boundary = self.get_city_as_region(city)
            if boundary:
                features.append(boundary)
                successful += 1
        
        # Сохраняем результат
        geojson = {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_regions": len(ukrainian_regions) + len(special_cities),
                "successful": successful,
                "source": "OpenStreetMap via Overpass API",
                "description": "Границы областей (регионов) Украины"
            }
        }
        
        output_file = 'ukraine_regions_boundaries.geojson'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        
        print(f"\n=== Результат ===")
        print(f"Обработано областей: {len(ukrainian_regions)}")
        print(f"Найдены границы: {successful}")
        print(f"Процент успеха: {successful/(len(ukrainian_regions) + len(special_cities))*100:.1f}%")
        print(f"Файл сохранен: {output_file}")
        
        return geojson
    
    def get_city_as_region(self, city_name: str) -> Optional[Dict]:
        """
        Получить границы города как региона (для городов спецстатуса)
        """
        query = f"""
        [out:json][timeout:45];
        (
          relation["name"="{city_name}"]["place"="city"]["admin_level"~"^(2|4|6)$"];
          relation["name"="{city_name}"]["boundary"="administrative"]["admin_level"~"^(2|4|6)$"];
        );
        out geom;
        """
        
        try:
            response = requests.post(
                self.overpass_url,
                data={'data': query},
                timeout=60,
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            elements = data.get('elements', [])
            if elements:
                element = elements[0]
                geojson_feature = self.osm_to_geojson(element, city_name)
                
                if geojson_feature:
                    # Помечаем как регион особого статуса
                    geojson_feature['properties']['type'] = 'special_city'
                    geojson_feature['properties']['name_uk'] = city_name
                    print(f"  ✓ Найдены границы для {city_name} (спецстатус)")
                    return geojson_feature
                    
        except Exception as e:
            print(f"  ✗ Ошибка для {city_name}: {e}")
            
        return None

def main():
    collector = UkrainianRegionsBoundariesCollector()
    
    print("=== Сбор границ областей Украины ===")
    print("Используем Overpass API (OpenStreetMap)")
    print("Это может занять 10-15 минут...")
    
    try:
        result = collector.process_ukrainian_regions()
        
        if result['features']:
            print(f"\n✓ Успешно получены границы для {len(result['features'])} регионов")
            print("Теперь можно использовать файл ukraine_regions_boundaries.geojson")
        else:
            print("\n✗ Границы регионов не найдены")
            
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        print(f"\nОшибка: {e}")

if __name__ == "__main__":
    main()
