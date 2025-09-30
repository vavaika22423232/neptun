// Ukraine Alert API Integration для фронтенда
// Добавить этот код в templates/index.html в секцию JavaScript

// Функция для получения данных из Ukraine Alert API
async function fetchAPIAlerts() {
    try {
        console.log('🇺🇦 Загрузка данных из Ukraine Alert API...');
        
        const response = await fetch('/api_alerts');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        console.log(`📊 API данные:`, {
            total: data.total_api_alerts,
            mapped: data.mapped_alerts,
            markers: data.markers?.length || 0
        });
        
        return data.markers || [];
        
    } catch (error) {
        console.error('❌ Ошибка загрузки API данных:', error);
        return [];
    }
}

// Функция для объединения API данных с телеграм данными
async function loadCombinedData() {
    const timeRange = document.getElementById('timeRange')?.value || 120;
    
    try {
        // Загружаем данные параллельно
        const [telegramData, apiAlerts] = await Promise.all([
            fetch(`/data?timeRange=${timeRange}`).then(r => r.json()),
            fetchAPIAlerts()
        ]);
        
        console.log(`📡 Получено данных:`, {
            telegram: telegramData.geo_tracks?.length || 0,
            api: apiAlerts.length,
            events: telegramData.events?.length || 0
        });
        
        // Объединяем маркеры
        const combinedMarkers = [
            ...(telegramData.geo_tracks || []),
            ...apiAlerts.map(alert => ({
                ...alert,
                // Добавляем специальную метку для API маркеров
                isAPIAlert: true,
                // Конвертируем в формат совместимый с существующими маркерами
                threat_type: alert.threat_type,
                coordinates: [alert.lat, alert.lng],
                region_name: alert.region,
                message_text: alert.message,
                timestamp_dt: alert.timestamp
            }))
        ];
        
        // Обновляем карту
        updateMarkers(combinedMarkers);
        
        // Обновляем события (только телеграм события)
        if (telegramData.events) {
            updateEventsList(telegramData.events);
        }
        
        // Показываем статистику
        displayDataStatistics({
            telegramMarkers: telegramData.geo_tracks?.length || 0,
            apiAlerts: apiAlerts.length,
            totalMarkers: combinedMarkers.length,
            events: telegramData.events?.length || 0
        });
        
    } catch (error) {
        console.error('❌ Ошибка загрузки комбинированных данных:', error);
        // Fallback к обычным данным
        loadData();
    }
}

// Функция отображения статистики
function displayDataStatistics(stats) {
    // Создаем или обновляем элемент статистики
    let statsElement = document.getElementById('data-statistics');
    if (!statsElement) {
        statsElement = document.createElement('div');
        statsElement.id = 'data-statistics';
        statsElement.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-size: 12px;
            z-index: 1000;
            max-width: 200px;
        `;
        document.body.appendChild(statsElement);
    }
    
    statsElement.innerHTML = `
        <div><strong>📊 Данные на карте:</strong></div>
        <div>📱 Telegram: ${stats.telegramMarkers}</div>
        <div>🇺🇦 API тревоги: ${stats.apiAlerts}</div>
        <div><strong>📍 Всего: ${stats.totalMarkers}</strong></div>
        <div>📰 События: ${stats.events}</div>
        <small>Обновлено: ${new Date().toLocaleTimeString()}</small>
    `;
}

// Модифицируем существующую функцию updateMarkers для обработки API маркеров
const originalUpdateMarkers = window.updateMarkers;
window.updateMarkers = function(tracks) {
    if (!originalUpdateMarkers) {
        console.warn('⚠️ Оригинальная функция updateMarkers не найдена');
        return;
    }
    
    // Разделяем маркеры на телеграм и API
    const telegramTracks = tracks.filter(track => !track.isAPIAlert);
    const apiTracks = tracks.filter(track => track.isAPIAlert);
    
    console.log(`🗺️ Обновляем маркеры:`, {
        telegram: telegramTracks.length,
        api: apiTracks.length
    });
    
    // Сначала обновляем телеграм маркеры (оригинальная логика)
    originalUpdateMarkers(telegramTracks);
    
    // Затем добавляем API маркеры
    apiTracks.forEach(track => {
        const marker = L.marker([track.lat, track.lng])
            .bindPopup(`
                <div class="api-alert-popup">
                    <h4>🇺🇦 Офіційна тривога</h4>
                    <p><strong>${track.region}</strong></p>
                    <p>Тип: ${track.threat_type}</p>
                    <p>Час: ${new Date(track.timestamp).toLocaleString('uk-UA')}</p>
                    <small>Джерело: Ukraine Alert API</small>
                </div>
            `);
        
        // Используем специальные иконки для API маркеров
        const iconClass = `api-${track.threat_type}`;
        marker.setIcon(getAPIAlertIcon(track.threat_type));
        
        if (window.markersLayer) {
            window.markersLayer.addLayer(marker);
        }
    });
};

// Функция для получения иконок API тревог
function getAPIAlertIcon(threatType) {
    const iconMap = {
        'air_alert': '✈️',
        'artillery': '💥',
        'urban_combat': '🏙️',
        'chemical': '☢️',
        'nuclear': '☢️'
    };
    
    const emoji = iconMap[threatType] || '🚨';
    
    return L.divIcon({
        html: `<div style="
            background: #ff4444;
            border: 2px solid #fff;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        ">${emoji}</div>`,
        className: 'api-alert-marker',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
}

// Заменяем стандартную загрузку данных на комбинированную
if (typeof loadData === 'function') {
    // Сохраняем оригинальную функцию
    window.originalLoadData = loadData;
    
    // Заменяем на комбинированную версию
    window.loadData = loadCombinedData;
    
    console.log('🔄 Ukraine Alert API интеграция активирована');
}

// Автоматическое обновление каждые 30 секунд
setInterval(() => {
    console.log('🔄 Автообновление данных...');
    loadCombinedData();
}, 30000);

console.log('🇺🇦 Ukraine Alert API фронтенд модуль загружен');
