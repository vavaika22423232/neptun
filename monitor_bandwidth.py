#!/usr/bin/env python3
"""
Bandwidth Monitor - отслеживание трафика в реальном времени
Помогает контролировать расходы на Render хостинге
"""

import requests
import time
import json
from datetime import datetime, timedelta

class BandwidthMonitor:
    def __init__(self, base_url="https://neptun-alerts.onrender.com"):
        self.base_url = base_url
        self.bandwidth_log = []
        
    def check_response_size(self, endpoint):
        """Проверяет размер ответа от эндпоинта."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=10)
            
            size_bytes = len(response.content)
            size_kb = size_bytes / 1024
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'status_code': response.status_code,
                'size_bytes': size_bytes,
                'size_kb': round(size_kb, 2),
                'headers': dict(response.headers)
            }
            
            self.bandwidth_log.append(log_entry)
            
            print(f"🌐 {endpoint}")
            print(f"   Size: {size_kb:.2f} KB ({size_bytes} bytes)")
            print(f"   Status: {response.status_code}")
            print(f"   Compression: {'gzip' if 'gzip' in response.headers.get('Content-Encoding', '') else 'none'}")
            print()
            
            return log_entry
            
        except Exception as e:
            print(f"❌ Error checking {endpoint}: {e}")
            return None
    
    def estimate_monthly_usage(self):
        """Оценивает месячное потребление трафика."""
        if not self.bandwidth_log:
            return
        
        # Средний размер ответа
        avg_size_kb = sum(entry['size_kb'] for entry in self.bandwidth_log) / len(self.bandwidth_log)
        
        # Предполагаемое количество запросов в день (консервативная оценка)
        requests_per_hour = 100  # популярный сайт
        requests_per_day = requests_per_hour * 24
        requests_per_month = requests_per_day * 30
        
        # Расчет трафика
        daily_kb = requests_per_day * avg_size_kb
        monthly_kb = requests_per_month * avg_size_kb
        monthly_gb = monthly_kb / (1024 * 1024)
        
        # Расчет стоимости ($15 за 100GB)
        cost_per_gb = 15 / 100
        estimated_cost = monthly_gb * cost_per_gb
        
        print("📊 ОЦЕНКА МЕСЯЧНОГО ТРАФИКА:")
        print(f"   Средний размер ответа: {avg_size_kb:.2f} KB")
        print(f"   Запросов в день: {requests_per_day:,}")
        print(f"   Трафик в день: {daily_kb/1024:.2f} MB")
        print(f"   Трафик в месяц: {monthly_gb:.2f} GB")
        print(f"   Предполагаемая стоимость: ${estimated_cost:.2f}/месяц")
        print()
        
        if estimated_cost > 50:
            print("⚠️  ВНИМАНИЕ: Высокие затраты на трафик!")
            print("   Рекомендуется дополнительная оптимизация")
        elif estimated_cost > 20:
            print("⚡ Умеренные затраты, можно оптимизировать")
        else:
            print("✅ Приемлемые затраты на трафик")
    
    def monitor_endpoints(self):
        """Мониторит основные эндпоинты."""
        endpoints = [
            '/',
            '/data',
            '/messages?limit=50',
            '/admin',
            '/static/svg_markers.js'
        ]
        
        print("🚀 Мониторинг трафика началс...")
        print("=" * 50)
        
        for endpoint in endpoints:
            self.check_response_size(endpoint)
            time.sleep(1)  # Небольшая пауза между запросами
        
        self.estimate_monthly_usage()
        
        # Сохраняем лог
        with open('bandwidth_monitor_log.json', 'w', encoding='utf-8') as f:
            json.dump(self.bandwidth_log, f, indent=2, ensure_ascii=False)
        
        print("💾 Лог сохранен в bandwidth_monitor_log.json")

if __name__ == "__main__":
    monitor = BandwidthMonitor()
    monitor.monitor_endpoints()
