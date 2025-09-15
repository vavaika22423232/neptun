#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание JavaScript файла с границами областей для NEPTUN приложения
"""

import json
import os

def create_regions_boundaries_js():
    """
    Создать JavaScript файл с данными о границах областей
    """
    geojson_file = 'ukraine_regions_boundaries.geojson'
    
    if not os.path.exists(geojson_file):
        print(f"Файл {geojson_file} не найден!")
        return
    
    # Загружаем данные о границах
    with open(geojson_file, 'r', encoding='utf-8') as f:
        boundaries_data = json.load(f)
    
    print(f"Загружено границ для {len(boundaries_data['features'])} областей")
    
    # Создаем JavaScript файл
    js_content = f'''/**
 * Границы украинских областей для NEPTUN приложения
 * Данные получены из OpenStreetMap через Overpass API
 * Создано: {boundaries_data.get("metadata", {}).get("created", "автоматически")}
 */

// Данные о границах областей
window.REGION_BOUNDARIES = {json.dumps(boundaries_data, ensure_ascii=False, indent=2)};

/**
 * Получить границы области по названию
 * @param {{string}} regionName - Название области
 * @returns {{Object|null}} GeoJSON Feature с границами области
 */
window.getRegionBoundary = function(regionName) {{
    if (!window.REGION_BOUNDARIES || !window.REGION_BOUNDARIES.features) {{
        console.warn('Дані про границі областей не завантажені');
        return null;
    }}
    
    const normalizedName = regionName.toUpperCase().trim();
    
    return window.REGION_BOUNDARIES.features.find(feature => 
        feature.properties.name && 
        feature.properties.name.toUpperCase().includes(normalizedName.replace(' ОБЛАСТЬ', ''))
    ) || null;
}};

/**
 * Добавить границы области на карту
 * @param {{Object}} map - Объект карты Leaflet
 * @param {{string}} regionName - Название области
 * @param {{Object}} options - Опции стиля для полигона
 * @returns {{Object|null}} Leaflet layer или null
 */
window.addRegionBoundaryToMap = function(map, regionName, options = {{}}) {{
    const boundary = window.getRegionBoundary(regionName);
    
    if (!boundary || !boundary.geometry) {{
        console.warn(`Границі для області "${{regionName}}" не знайдено`);
        return null;
    }}
    
    const defaultOptions = {{
        color: '#f59e0b',
        weight: 3,
        opacity: 0.9,
        fillColor: '#f59e0b',
        fillOpacity: 0.2,
        className: 'region-boundary',
        interactive: true
    }};
    
    const layerOptions = {{...defaultOptions, ...options}};
    
    try {{
        const layer = L.geoJSON(boundary, {{
            style: layerOptions,
            onEachFeature: function(feature, layer) {{
                const props = feature.properties;
                let popupContent = `<div style="min-width: 220px;">
                    <h3 style="margin: 0 0 8px 0; color: #d97706;">
                        🏛️ ${{props.name}}
                    </h3>`;
                
                if (props.population) {{
                    const pop = parseInt(props.population).toLocaleString('uk-UA');
                    popupContent += `<p style="margin: 4px 0;"><strong>Населення:</strong> ${{pop}}</p>`;
                }}
                
                if (props.admin_level) {{
                    popupContent += `<p style="margin: 4px 0;"><strong>Адмін. рівень:</strong> ${{props.admin_level}}</p>`;
                }}
                
                if (props.type === 'special_city') {{
                    popupContent += `<p style="margin: 4px 0;"><strong>Статус:</strong> Місто зі спеціальним статусом</p>`;
                }}
                
                if (props.osm_id) {{
                    popupContent += `<p style="margin: 4px 0; font-size: 0.8em; color: #666;">
                        <strong>OSM ID:</strong> ${{props.osm_id}}
                    </p>`;
                }}
                
                popupContent += `</div>`;
                
                layer.bindPopup(popupContent);
                
                // Добавляем подсветку при наведении
                layer.on('mouseover', function(e) {{
                    e.target.setStyle({{
                        weight: 4,
                        opacity: 1,
                        fillOpacity: 0.3
                    }});
                }});
                
                layer.on('mouseout', function(e) {{
                    e.target.setStyle(layerOptions);
                }});
            }}
        }});
        
        layer.addTo(map);
        
        // Добавляем в глобальный реестр слоев если он существует
        if (window.regionBoundaryLayers) {{
            window.regionBoundaryLayers[regionName] = layer;
        }} else {{
            window.regionBoundaryLayers = {{}};
            window.regionBoundaryLayers[regionName] = layer;
        }}
        
        console.log(`Додано границі області: ${{regionName}}`);
        return layer;
        
    }} catch (error) {{
        console.error(`Помилка при додаванні границь для ${{regionName}}:`, error);
        return null;
    }}
}};

/**
 * Удалить границы области с карты
 * @param {{Object}} map - Объект карты Leaflet
 * @param {{string}} regionName - Название области
 */
window.removeRegionBoundaryFromMap = function(map, regionName) {{
    if (window.regionBoundaryLayers && window.regionBoundaryLayers[regionName]) {{
        map.removeLayer(window.regionBoundaryLayers[regionName]);
        delete window.regionBoundaryLayers[regionName];
        console.log(`Видалено границі області: ${{regionName}}`);
    }}
}};

/**
 * Показать границы всех доступных областей
 * @param {{Object}} map - Объект карты Leaflet
 * @param {{Object}} options - Опции стиля
 */
window.showAllRegionBoundaries = function(map, options = {{}}) {{
    if (!window.REGION_BOUNDARIES || !window.REGION_BOUNDARIES.features) {{
        console.warn('Дані про границі областей не завантажені');
        return null;
    }}
    
    const defaultOptions = {{
        color: '#f59e0b',
        weight: 2,
        opacity: 0.8,
        fillColor: '#f59e0b',
        fillOpacity: 0.15,
        className: 'all-region-boundaries'
    }};
    
    const layerOptions = {{...defaultOptions, ...options}};
    
    try {{
        const layer = L.geoJSON(window.REGION_BOUNDARIES, {{
            style: function(feature) {{
                // Разные цвета для разных типов регионов
                if (feature.properties.type === 'special_city') {{
                    return {{
                        ...layerOptions,
                        color: '#dc2626',
                        fillColor: '#dc2626'
                    }};
                }}
                return layerOptions;
            }},
            onEachFeature: function(feature, layer) {{
                const props = feature.properties;
                let popupContent = `<b>${{props.name}}</b><br>`;
                
                if (props.population) {{
                    popupContent += `Населення: ${{parseInt(props.population).toLocaleString('uk-UA')}}<br>`;
                }}
                
                if (props.type === 'special_city') {{
                    popupContent += `<em>Спеціальний статус</em>`;
                }}
                
                layer.bindPopup(popupContent);
                
                // Подсветка при наведении
                layer.on('mouseover', function(e) {{
                    e.target.setStyle({{
                        weight: 3,
                        opacity: 1,
                        fillOpacity: 0.4
                    }});
                }});
                
                layer.on('mouseout', function(e) {{
                    e.target.setStyle(e.target.options.style || layerOptions);
                }});
            }}
        }});
        
        layer.addTo(map);
        
        // Добавляем в глобальный реестр
        if (!window.regionBoundaryLayers) {{
            window.regionBoundaryLayers = {{}};
        }}
        window.regionBoundaryLayers['_all_regions'] = layer;
        
        console.log('Показано границі всіх областей');
        return layer;
        
    }} catch (error) {{
        console.error('Помилка при показі всіх границь областей:', error);
        return null;
    }}
}};

/**
 * Скрыть все границы областей
 * @param {{Object}} map - Объект карты Leaflet
 */
window.hideAllRegionBoundaries = function(map) {{
    if (window.regionBoundaryLayers) {{
        Object.keys(window.regionBoundaryLayers).forEach(regionName => {{
            map.removeLayer(window.regionBoundaryLayers[regionName]);
        }});
        window.regionBoundaryLayers = {{}};
        console.log('Приховано всі границі областей');
    }}
}};

/**
 * Получить список всех доступных областей
 * @returns {{Array}} Массив названий областей
 */
window.getAvailableRegions = function() {{
    if (!window.REGION_BOUNDARIES || !window.REGION_BOUNDARIES.features) {{
        return [];
    }}
    
    return window.REGION_BOUNDARIES.features.map(feature => feature.properties.name);
}};

/**
 * Проверить, доступны ли границы для области
 * @param {{string}} regionName - Название области
 * @returns {{boolean}} true если границы доступны
 */
window.hasRegionBoundary = function(regionName) {{
    return window.getRegionBoundary(regionName) !== null;
}};

/**
 * Найти область по названию города или населенного пункта
 * @param {{string}} cityName - Название города
 * @returns {{string|null}} Название области или null
 */
window.findRegionByCity = function(cityName) {{
    // Простое сопоставление основных городов с областями
    const cityToRegion = {{
        'Київ': 'Київська область',
        'Харків': 'Харківська область', 
        'Одеса': 'Одеська область',
        'Дніпро': 'Дніпропетровська область',
        'Львів': 'Львівська область',
        'Запоріжжя': 'Запорізька область',
        'Вінниця': 'Вінницька область',
        'Луцьк': 'Волинська область',
        'Житомир': 'Житомирська область',
        'Ужгород': 'Закарпатська область',
        'Івано-Франківськ': 'Івано-Франківська область',
        'Кропивницький': 'Кіровоградська область',
        'Луганськ': 'Луганська область',
        'Миколаїв': 'Миколаївська область',
        'Полтава': 'Полтавська область',
        'Рівне': 'Рівненська область',
        'Суми': 'Сумська область',
        'Тернопіль': 'Тернопільська область',
        'Херсон': 'Херсонська область',
        'Хмельницький': 'Хмельницька область',
        'Черкаси': 'Черкаська область',
        'Чернівці': 'Чернівецька область',
        'Чернігів': 'Чернігівська область'
    }};
    
    return cityToRegion[cityName] || null;
}};

// Инициализация
console.log('✓ Модуль границь областей завантажено');
console.log('Доступні границі для областей:', window.getAvailableRegions());
'''
    
    # Сохраняем JavaScript файл
    with open('static/region_boundaries.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print("✓ JavaScript файл создан: static/region_boundaries.js")
    
    # Также создаем копию в корне для разработки
    with open('region_boundaries.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print("✓ Копия создана: region_boundaries.js")
    
    return len(boundaries_data['features'])

def create_regions_list():
    """
    Создать простой список областей с границами
    """
    geojson_file = 'ukraine_regions_boundaries.geojson'
    
    if not os.path.exists(geojson_file):
        print(f"Файл {geojson_file} не найден!")
        return
    
    with open(geojson_file, 'r', encoding='utf-8') as f:
        boundaries_data = json.load(f)
    
    regions = []
    for feature in boundaries_data['features']:
        props = feature['properties']
        region_info = {
            'name': props['name'],
            'name_uk': props.get('name_uk', props['name']),
            'population': props.get('population'),
            'osm_id': props.get('osm_id'),
            'admin_level': props.get('admin_level'),
            'type': props.get('type', 'region'),
            'bounds': props.get('bounds')
        }
        regions.append(region_info)
    
    # Сортируем по названию
    regions.sort(key=lambda x: x['name'])
    
    with open('regions_with_boundaries.json', 'w', encoding='utf-8') as f:
        json.dump(regions, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Список областей создан: regions_with_boundaries.json ({len(regions)} областей)")

def main():
    print("=== Создание файлов для интеграции границ областей ===")
    
    # Создаем папку static если её нет
    if not os.path.exists('static'):
        os.makedirs('static')
        print("✓ Создана папка static/")
    
    regions_count = create_regions_boundaries_js()
    create_regions_list()
    
    print(f"\\n=== Готово! ===")
    print(f"Обработано областей: {regions_count}")
    print("\\nФайлы для использования:")
    print("1. static/region_boundaries.js - для production")
    print("2. region_boundaries.js - для разработки")
    print("3. regions_with_boundaries.json - список областей")
    
    print("\\nКак использовать в index.html:")
    print("1. Добавьте <script src='static/region_boundaries.js'></script>")
    print("2. Используйте функции:")
    print("   - addRegionBoundaryToMap(map, 'Дніпропетровська область')")
    print("   - showAllRegionBoundaries(map)")
    print("   - getRegionBoundary('Львівська область')")

if __name__ == "__main__":
    main()
