#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание JavaScript файла с границами городов для NEPTUN приложения
"""

import json
import os

def create_city_boundaries_js():
    """
    Создать JavaScript файл с данными о границах городов
    """
    geojson_file = 'ukraine_major_cities_boundaries.geojson'
    
    if not os.path.exists(geojson_file):
        print(f"Файл {geojson_file} не найден!")
        return
    
    # Загружаем данные о границах
    with open(geojson_file, 'r', encoding='utf-8') as f:
        boundaries_data = json.load(f)
    
    print(f"Загружено границ для {len(boundaries_data['features'])} городов")
    
    # Создаем JavaScript файл
    js_content = f'''/**
 * Границы украинских городов для NEPTUN приложения
 * Данные получены из OpenStreetMap через Overpass API
 * Создано: {boundaries_data.get("metadata", {}).get("created", "автоматически")}
 */

// Данные о границах городов
window.CITY_BOUNDARIES = {json.dumps(boundaries_data, ensure_ascii=False, indent=2)};

/**
 * Получить границы города по названию
 * @param {{string}} cityName - Название города
 * @returns {{Object|null}} GeoJSON Feature с границами города
 */
window.getCityBoundary = function(cityName) {{
    if (!window.CITY_BOUNDARIES || !window.CITY_BOUNDARIES.features) {{
        console.warn('Данные о границах городов не загружены');
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
 * @returns {{Object|null}} Leaflet layer или null
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
        fillOpacity: 0.15,
        className: 'city-boundary',
        interactive: true
    }};
    
    const layerOptions = {{...defaultOptions, ...options}};
    
    try {{
        const layer = L.geoJSON(boundary, {{
            style: layerOptions,
            onEachFeature: function(feature, layer) {{
                const props = feature.properties;
                let popupContent = `<div style="min-width: 200px;">
                    <h3 style="margin: 0 0 8px 0; color: #1e40af;">
                        🏙️ ${{props.name}}
                    </h3>`;
                
                if (props.population) {{
                    const pop = parseInt(props.population).toLocaleString('uk-UA');
                    popupContent += `<p style="margin: 4px 0;"><strong>Населення:</strong> ${{pop}}</p>`;
                }}
                
                if (props.admin_level) {{
                    popupContent += `<p style="margin: 4px 0;"><strong>Адмін. рівень:</strong> ${{props.admin_level}}</p>`;
                }}
                
                if (props.osm_id) {{
                    popupContent += `<p style="margin: 4px 0; font-size: 0.8em; color: #666;">
                        <strong>OSM ID:</strong> ${{props.osm_id}}
                    </p>`;
                }}
                
                popupContent += `</div>`;
                
                layer.bindPopup(popupContent);
            }}
        }});
        
        layer.addTo(map);
        
        // Добавляем в глобальный реестр слоев если он существует
        if (window.cityBoundaryLayers) {{
            window.cityBoundaryLayers[cityName] = layer;
        }} else {{
            window.cityBoundaryLayers = {{}};
            window.cityBoundaryLayers[cityName] = layer;
        }}
        
        console.log(`Добавлены границы города: ${{cityName}}`);
        return layer;
        
    }} catch (error) {{
        console.error(`Ошибка при добавлении границ для ${{cityName}}:`, error);
        return null;
    }}
}};

/**
 * Удалить границы города с карты
 * @param {{Object}} map - Объект карты Leaflet
 * @param {{string}} cityName - Название города
 */
window.removeCityBoundaryFromMap = function(map, cityName) {{
    if (window.cityBoundaryLayers && window.cityBoundaryLayers[cityName]) {{
        map.removeLayer(window.cityBoundaryLayers[cityName]);
        delete window.cityBoundaryLayers[cityName];
        console.log(`Удалены границы города: ${{cityName}}`);
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
        fillOpacity: 0.08,
        className: 'all-city-boundaries'
    }};
    
    const layerOptions = {{...defaultOptions, ...options}};
    
    try {{
        const layer = L.geoJSON(window.CITY_BOUNDARIES, {{
            style: layerOptions,
            onEachFeature: function(feature, layer) {{
                const props = feature.properties;
                const popupContent = `<b>${{props.name}}</b><br>
                    ${{props.population ? 'Населення: ' + parseInt(props.population).toLocaleString('uk-UA') : ''}}`;
                layer.bindPopup(popupContent);
            }}
        }});
        
        layer.addTo(map);
        
        // Добавляем в глобальный реестр
        if (!window.cityBoundaryLayers) {{
            window.cityBoundaryLayers = {{}};
        }}
        window.cityBoundaryLayers['_all_boundaries'] = layer;
        
        console.log('Показаны границы всех городов');
        return layer;
        
    }} catch (error) {{
        console.error('Ошибка при показе всех границ:', error);
        return null;
    }}
}};

/**
 * Скрыть все границы городов
 * @param {{Object}} map - Объект карты Leaflet
 */
window.hideAllCityBoundaries = function(map) {{
    if (window.cityBoundaryLayers) {{
        Object.keys(window.cityBoundaryLayers).forEach(cityName => {{
            map.removeLayer(window.cityBoundaryLayers[cityName]);
        }});
        window.cityBoundaryLayers = {{}};
        console.log('Скрыты все границы городов');
    }}
}};

/**
 * Получить список всех доступных городов с границами
 * @returns {{Array}} Массив названий городов
 */
window.getAvailableCities = function() {{
    if (!window.CITY_BOUNDARIES || !window.CITY_BOUNDARIES.features) {{
        return [];
    }}
    
    return window.CITY_BOUNDARIES.features.map(feature => feature.properties.name);
}};

/**
 * Проверить, доступны ли границы для города
 * @param {{string}} cityName - Название города
 * @returns {{boolean}} true если границы доступны
 */
window.hasCityBoundary = function(cityName) {{
    return window.getCityBoundary(cityName) !== null;
}};

// Инициализация
console.log('✓ Модуль границ городов загружен');
console.log('Доступны границы для городов:', window.getAvailableCities());
'''
    
    # Сохраняем JavaScript файл
    with open('static/city_boundaries.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print("✓ JavaScript файл создан: static/city_boundaries.js")
    
    # Также создаем копию в корне для разработки
    with open('city_boundaries.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print("✓ Копия создана: city_boundaries.js")
    
    return len(boundaries_data['features'])

def create_cities_list():
    """
    Создать простой список городов с границами
    """
    geojson_file = 'ukraine_major_cities_boundaries.geojson'
    
    if not os.path.exists(geojson_file):
        print(f"Файл {geojson_file} не найден!")
        return
    
    with open(geojson_file, 'r', encoding='utf-8') as f:
        boundaries_data = json.load(f)
    
    cities = []
    for feature in boundaries_data['features']:
        props = feature['properties']
        city_info = {
            'name': props['name'],
            'population': props.get('population'),
            'osm_id': props.get('osm_id'),
            'admin_level': props.get('admin_level'),
            'bounds': props.get('bounds')
        }
        cities.append(city_info)
    
    # Сортируем по населению
    cities.sort(key=lambda x: int(x['population'] or 0), reverse=True)
    
    with open('cities_with_boundaries.json', 'w', encoding='utf-8') as f:
        json.dump(cities, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Список городов создан: cities_with_boundaries.json ({len(cities)} городов)")

def main():
    print("=== Создание файлов для интеграции границ городов ===")
    
    # Создаем папку static если её нет
    if not os.path.exists('static'):
        os.makedirs('static')
        print("✓ Создана папка static/")
    
    cities_count = create_city_boundaries_js()
    create_cities_list()
    
    print(f"\\n=== Готово! ===")
    print(f"Обработано городов: {cities_count}")
    print("\\nФайлы для использования:")
    print("1. static/city_boundaries.js - для production")
    print("2. city_boundaries.js - для разработки")
    print("3. cities_with_boundaries.json - список городов")
    
    print("\\nКак использовать в index.html:")
    print("1. Добавьте <script src='static/city_boundaries.js'></script>")
    print("2. Используйте функции:")
    print("   - addCityBoundaryToMap(map, 'Київ')")
    print("   - showAllCityBoundaries(map)")
    print("   - getCityBoundary('Львів')")

if __name__ == "__main__":
    main()
