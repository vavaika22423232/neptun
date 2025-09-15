#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Альтернативные источники геоданных для границ украинских городов
"""

import requests
import json
from typing import Dict, List

class AlternativeDataSources:
    """
    Класс для работы с альтернативными источниками геоданных
    """
    
    @staticmethod
    def download_ukraine_geojson():
        """
        Скачать готовые границы украинских регионов/городов с GitHub
        """
        sources = {
            'ukraine_regions': 'https://raw.githubusercontent.com/hpfast/ukraine-geojson/main/ukraine-regions.geojson',
            'ukraine_cities': 'https://raw.githubusercontent.com/hpfast/ukraine-geojson/main/ukraine-cities.geojson',
            'ukraine_districts': 'https://raw.githubusercontent.com/hpfast/ukraine-geojson/main/ukraine-districts.geojson'
        }
        
        for name, url in sources.items():
            try:
                print(f"Скачиваем {name}...")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                filename = f"{name}.geojson"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(response.json(), f, ensure_ascii=False, indent=2)
                
                print(f"✓ Сохранено: {filename}")
                
            except Exception as e:
                print(f"✗ Ошибка при скачивании {name}: {e}")
    
    @staticmethod 
    def get_nominatim_boundary(city_name: str, country: str = "Ukraine") -> Dict:
        """
        Получить границы города через Nominatim API
        """
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': f"{city_name}, {country}",
            'format': 'geojson',
            'polygon_geojson': 1,
            'addressdetails': 1,
            'limit': 1
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('features'):
                return data['features'][0]
                
        except Exception as e:
            print(f"Ошибка Nominatim для {city_name}: {e}")
        
        return None

def main():
    print("=== Скачивание готовых геоданных ===")
    AlternativeDataSources.download_ukraine_geojson()
    
    print("\n=== Тест Nominatim API ===")
    # Тест получения границ через Nominatim
    test_cities = ["Київ", "Львів", "Харків", "Одеса"]
    
    for city in test_cities:
        print(f"Тестируем {city}...")
        boundary = AlternativeDataSources.get_nominatim_boundary(city)
        if boundary:
            print(f"✓ Найдены границы для {city}")
        else:
            print(f"✗ Границы не найдены для {city}")

if __name__ == "__main__":
    main()
