#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграция границ городов в приложение NEPTUN
"""

import json
from typing import Dict, List, Optional

class CityBoundariesIntegrator:
    """
    Класс для интеграции границ городов в существующую систему
    """
    
    def __init__(self, geojson_file: str, cities_json_file: str):
        self.geojson_file = geojson_file
        self.cities_json_file = cities_json_file
        
    def load_boundaries(self) -> Dict:
        """Загрузить границы из GeoJSON файла"""
        try:
            with open(self.geojson_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Файл {self.geojson_file} не найден")
            return {"type": "FeatureCollection", "features": []}
    
    def load_cities(self) -> List[Dict]:
        """Загрузить список городов"""
        with open(self.cities_json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def create_city_boundaries_lookup(self) -> Dict[str, Dict]:
        """
        Создать словарь для быстрого поиска границ по названию города
        """
        boundaries = self.load_boundaries()
        lookup = {}
        
        for feature in boundaries.get('features', []):
            city_name = feature['properties'].get('name', '').upper()
            lookup[city_name] = feature
        
        return lookup
    
    def generate_js_boundaries_data(self, output_file: str = 'city_boundaries.js'):
        """
        Генерировать JavaScript файл с данными о границах для фронтенда
        """
        boundaries = self.load_boundaries()
        
        js_content = f"""
// Автоматически сгенерированный файл с границами городов
// Сгенерировано: {json.dumps(boundaries, ensure_ascii=False)}

window.CITY_BOUNDARIES = {json.dumps(boundaries, ensure_ascii=False, indent=2)};

/**
 * Получить границы города по названию
 * @param {{string}} cityName - Название города
 * @returns {{Object|null}} GeoJSON Feature с границами города
 */
window.getCityBoundary = function(cityName) {{
    if (!window.CITY_BOUNDARIES || !window.CITY_BOUNDARIES.features) {{
        return null;
    }}
    
    const normalizedName = cityName.toUpperCase().trim();
    
    return window.CITY_BOUNDARIES.features.find(feature => 
        feature.properties.name && 
        feature.properties.name.toUpperCase() === normalizedName
    ) || null;
}};

/**
 * Добавить границы города на карту
 * @param {{Object}} map - Объект карты Leaflet
 * @param {{string}} cityName - Название города
 * @param {{Object}} options - Опции стиля для полигона
 */
window.addCityBoundaryToMap = function(map, cityName, options = {{}}) {{
    const boundary = window.getCityBoundary(cityName);
    
    if (!boundary || !boundary.geometry) {{
        console.warn(`Границы для города "${{cityName}}" не найдены`);
        return null;
    }}
    
    const defaultOptions = {{
        color: '#3b82f6',
        weight: 2,
        opacity: 0.8,
        fillColor: '#3b82f6',
        fillOpacity: 0.1,
        className: 'city-boundary'
    }};
    
    const layerOptions = {{...defaultOptions, ...options}};
    
    try {{
        const layer = L.geoJSON(boundary, {{
            style: layerOptions,
            onEachFeature: function(feature, layer) {{
                if (feature.properties.name) {{
                    layer.bindPopup(`<b>${{feature.properties.name}}</b><br>Границы города`);
                }}
            }}
        }});
        
        layer.addTo(map);
        return layer;
        
    }} catch (error) {{
        console.error(`Ошибка при добавлении границ для ${{cityName}}:`, error);
        return null;
    }}
}};

/**
 * Показать границы всех доступных городов
 * @param {{Object}} map - Объект карты Leaflet
 * @param {{Object}} options - Опции стиля
 */
window.showAllCityBoundaries = function(map, options = {{}}) {{
    if (!window.CITY_BOUNDARIES || !window.CITY_BOUNDARIES.features) {{
        console.warn('Данные о границах городов не загружены');
        return null;
    }}
    
    const defaultOptions = {{
        color: '#6b7280',
        weight: 1,
        opacity: 0.6,
        fillColor: '#6b7280',
        fillOpacity: 0.05,
        className: 'all-city-boundaries'
    }};
    
    const layerOptions = {{...defaultOptions, ...options}};
    
    try {{
        const layer = L.geoJSON(window.CITY_BOUNDARIES, {{
            style: layerOptions,
            onEachFeature: function(feature, layer) {{
                if (feature.properties.name) {{
                    layer.bindPopup(`<b>${{feature.properties.name}}</b><br>Границы города`);
                }}
            }}
        }});
        
        layer.addTo(map);
        return layer;
        
    }} catch (error) {{
        console.error('Ошибка при показе всех границ:', error);
        return null;
    }}
}};

console.log('Загружены границы для', window.CITY_BOUNDARIES.features.length, 'городов');
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(js_content)
        
        print(f"JavaScript файл сохранен: {output_file}")
    
    def create_enhanced_cities_json(self, output_file: str = 'cities_with_boundaries.json'):
        """
        Создать расширенный JSON с информацией о наличии границ
        """
        cities = self.load_cities()
        boundaries_lookup = self.create_city_boundaries_lookup()
        
        enhanced_cities = []
        cities_with_boundaries = 0
        
        for city in cities:
            city_name = city['object_name']
            enhanced_city = city.copy()
            
            # Проверяем наличие границ
            if city_name.upper() in boundaries_lookup:
                enhanced_city['has_boundaries'] = True
                enhanced_city['boundary_available'] = True
                cities_with_boundaries += 1
            else:
                enhanced_city['has_boundaries'] = False
                enhanced_city['boundary_available'] = False
            
            enhanced_cities.append(enhanced_city)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_cities, f, ensure_ascii=False, indent=2)
        
        print(f"Расширенный файл сохранен: {output_file}")
        print(f"Города с границами: {cities_with_boundaries}/{len(cities)} ({cities_with_boundaries/len(cities)*100:.1f}%)")

def main():
    # Предполагаем, что у вас есть файл с границами
    integrator = CityBoundariesIntegrator(
        geojson_file='ukraine_city_boundaries.geojson',  # Создается первым скриптом
        cities_json_file='city_ukraine.json'             # Ваш существующий файл
    )
    
    print("=== Генерация JavaScript файла ===")
    integrator.generate_js_boundaries_data()
    
    print("\n=== Создание расширенного JSON ===")
    integrator.create_enhanced_cities_json()

if __name__ == "__main__":
    main()
