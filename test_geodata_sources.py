#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Рабочие источники геоданных для украинских городов
"""

import requests
import json
import time
from typing import Dict, List

def test_working_sources():
    """
    Тестируем рабочие источники геоданных
    """
    
    # 1. Альтернативные GitHub репозитории
    github_sources = [
        {
            'name': 'ukraine-geojson (другая структура)',
            'url': 'https://raw.githubusercontent.com/dmytro-parfenov/ukraine-geojson/master/ukraine.geojson'
        },
        {
            'name': 'ukraine-administrative-divisions',
            'url': 'https://raw.githubusercontent.com/youchenlee/ukraine-administrative-divisions/main/ukraine.geojson'
        },
        {
            'name': 'ukraine regions (OpenData)',
            'url': 'https://raw.githubusercontent.com/OpenDataUA/ukraine-datasets/main/geodata/regions.geojson'
        }
    ]
    
    print("=== Тестируем GitHub источники ===")
    for source in github_sources:
        try:
            print(f"Тестируем: {source['name']}")
            response = requests.get(source['url'], timeout=10)
            print(f"  Статус: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                features_count = len(data.get('features', []))
                print(f"  ✓ Найдено {features_count} объектов")
                
                # Сохраняем рабочий источник
                filename = f"ukraine_data_{source['name'].replace(' ', '_').lower()}.geojson"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  ✓ Сохранено в {filename}")
                
            else:
                print(f"  ✗ Ошибка {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ Ошибка: {e}")
        
        time.sleep(1)  # Пауза между запросами
    
    # 2. Тестируем OpenStreetMap Overpass API (более мягкий подход)
    print("\n=== Тестируем Overpass API ===")
    
    # Простой запрос для одного большого города
    test_overpass_query = """
    [out:json][timeout:25];
    (
      relation["name"="Київ"]["place"="city"];
    );
    out geom;
    """
    
    try:
        print("Тестируем Overpass API для Киева...")
        response = requests.post(
            'https://overpass-api.de/api/interpreter',
            data={'data': test_overpass_query},
            timeout=30,
            headers={'User-Agent': 'NEPTUN-App/1.0'}
        )
        
        if response.status_code == 200:
            data = response.json()
            elements_count = len(data.get('elements', []))
            print(f"  ✓ Overpass API работает, найдено {elements_count} элементов")
            
            if elements_count > 0:
                with open('test_kyiv_boundary.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print("  ✓ Тестовые данные сохранены в test_kyiv_boundary.json")
        else:
            print(f"  ✗ Overpass API недоступен: {response.status_code}")
            
    except Exception as e:
        print(f"  ✗ Ошибка Overpass API: {e}")

def download_natural_earth():
    """
    Скачать данные Natural Earth (мировые данные включая Украину)
    """
    print("\n=== Скачиваем Natural Earth данные ===")
    
    natural_earth_urls = [
        {
            'name': 'populated_places',
            'url': 'https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson'
        },
        {
            'name': 'admin_0_countries',
            'url': 'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/countries.geojson'
        }
    ]
    
    for source in natural_earth_urls:
        try:
            print(f"Скачиваем: {source['name']}")
            response = requests.get(source['url'], timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Фильтруем только Украину
                ukraine_features = []
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    name = props.get('NAME', '').lower()
                    country = props.get('COUNTRY', '').lower()
                    
                    if 'ukraine' in name or 'україна' in name or country == 'ukraine':
                        ukraine_features.append(feature)
                
                if ukraine_features:
                    ukraine_data = {
                        "type": "FeatureCollection",
                        "features": ukraine_features
                    }
                    
                    filename = f"ukraine_{source['name']}.geojson"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(ukraine_data, f, ensure_ascii=False, indent=2)
                    
                    print(f"  ✓ Найдено {len(ukraine_features)} украинских объектов")
                    print(f"  ✓ Сохранено в {filename}")
                else:
                    print("  ✗ Украинские данные не найдены")
            else:
                print(f"  ✗ Ошибка {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ Ошибка: {e}")

if __name__ == "__main__":
    test_working_sources()
    download_natural_earth()
