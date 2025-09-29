#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создаем простую демо страницу для отображения API маркеров
"""

import requests
import json

def create_api_demo_page():
    """Создает HTML страницу для демонстрации API маркеров"""
    
    # Получаем данные API
    try:
        response = requests.get('http://localhost:5000/api_alerts')
        if response.status_code == 200:
            api_data = response.json()
            markers = api_data.get('markers', [])
        else:
            markers = []
    except:
        markers = []
    
    html = f"""
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ukraine Alert API - Демо маркеры</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <style>
        body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; }}
        #map {{ height: 600px; border: 2px solid #333; border-radius: 8px; }}
        .info {{ background: #f0f0f0; padding: 15px; margin-bottom: 20px; border-radius: 8px; }}
        .marker-info {{ background: white; padding: 10px; margin: 5px 0; border-radius: 5px; border-left: 4px solid #007cba; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat {{ background: #007cba; color: white; padding: 10px 15px; border-radius: 5px; text-align: center; }}
        .refresh-btn {{ background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }}
        .refresh-btn:hover {{ background: #218838; }}
    </style>
</head>
<body>
    <h1>🇺🇦 Ukraine Alert API - Демонстрация маркеров</h1>
    
    <div class="stats">
        <div class="stat">
            <div><strong>{len(markers)}</strong></div>
            <div>Маркерів на карті</div>
        </div>
        <div class="stat">
            <div><strong>{len(set(m.get('threat_type', 'unknown') for m in markers))}</strong></div>
            <div>Типів загроз</div>
        </div>
        <div class="stat">
            <div><strong>{len(set(m.get('region', 'unknown') for m in markers))}</strong></div>
            <div>Регіонів</div>
        </div>
    </div>
    
    <button class="refresh-btn" onclick="location.reload()">🔄 Оновити дані</button>
    
    <div id="map"></div>
    
    <div class="info">
        <h3>📍 Маркери на карті:</h3>
"""
    
    # Добавляем информацию о маркерах
    for i, marker in enumerate(markers[:10]):  # Показываем первые 10
        threat_icon = {
            'air_alert': '✈️',
            'artillery': '💥',
            'urban_combat': '🏙️',
            'chemical': '☢️',
            'nuclear': '☢️'
        }.get(marker.get('threat_type', 'unknown'), '🚨')
        
        html += f"""
        <div class="marker-info">
            <strong>{threat_icon} {marker.get('region', 'Unknown')}</strong><br>
            Координати: {marker.get('lat', 0):.4f}, {marker.get('lng', 0):.4f}<br>
            Тип загрози: {marker.get('threat_type', 'unknown')}<br>
            Час: {marker.get('timestamp', 'unknown')}
        </div>
        """
    
    if len(markers) > 10:
        html += f"<p><em>... та ще {len(markers) - 10} маркерів</em></p>"
    
    html += """
    </div>

    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <script>
        // Инициализация карты
        const map = L.map('map').setView([48.3794, 31.1656], 6);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        // Данные маркеров
        const markers = """ + json.dumps(markers) + """;
        
        // Добавляем маркеры на карту
        markers.forEach(marker => {
            const threatIcons = {
                'air_alert': '✈️',
                'artillery': '💥', 
                'urban_combat': '🏙️',
                'chemical': '☢️',
                'nuclear': '☢️'
            };
            
            const icon = threatIcons[marker.threat_type] || '🚨';
            
            const markerIcon = L.divIcon({
                html: `<div style="
                    background: #ff4444;
                    border: 2px solid #fff;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                ">${icon}</div>`,
                className: 'api-alert-marker',
                iconSize: [40, 40],
                iconAnchor: [20, 20]
            });
            
            L.marker([marker.lat, marker.lng], {icon: markerIcon})
                .bindPopup(`
                    <div>
                        <h4>🇺🇦 ${marker.region}</h4>
                        <p><strong>Тип:</strong> ${marker.threat_type}</p>
                        <p><strong>Час:</strong> ${new Date(marker.timestamp).toLocaleString('uk-UA')}</p>
                        <p><strong>Джерело:</strong> Ukraine Alert API</p>
                    </div>
                `)
                .addTo(map);
        });
        
        console.log(`🇺🇦 Завантажено ${markers.length} маркерів з Ukraine Alert API`);
    </script>
</body>
</html>
    """
    
    return html

if __name__ == "__main__":
    html = create_api_demo_page()
    with open('/Users/vladimirmalik/Desktop/render2/api_demo.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ Демо страница создана: api_demo.html")
    print("🌐 Откройте файл в браузере для просмотра API маркеров")
