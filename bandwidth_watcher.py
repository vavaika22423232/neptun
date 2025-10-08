#!/usr/bin/env python3
"""
Монитор трафика в реальном времени
Отслеживает использование исходящего трафика и выдает предупреждения
"""

import requests
import time
import json
from datetime import datetime

class BandwidthMonitor:
    def __init__(self, base_url='http://localhost:5000', admin_token='admin123'):
        self.base_url = base_url
        self.admin_token = admin_token
        self.monthly_limit_gb = 10  # Цель: снизить до 10GB в месяц
        self.daily_limit_gb = 0.5   # ~15GB в месяц максимум
        
    def get_stats(self):
        """Получить текущую статистику трафика"""
        try:
            url = f"{self.base_url}/admin/bandwidth_stats?token={self.admin_token}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Ошибка получения статистики: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Ошибка соединения: {e}")
            return None
    
    def format_bytes(self, bytes_value):
        """Форматировать байты в читаемый вид"""
        if bytes_value < 1024:
            return f"{bytes_value}B"
        elif bytes_value < 1024**2:
            return f"{bytes_value/1024:.1f}KB"
        elif bytes_value < 1024**3:
            return f"{bytes_value/1024**2:.1f}MB"
        else:
            return f"{bytes_value/1024**3:.2f}GB"
    
    def check_limits(self, stats):
        """Проверить лимиты и выдать предупреждения"""
        if not stats:
            return
            
        total_mb = stats.get('total_mb_sent', 0)
        total_gb = total_mb / 1024
        
        print(f"\n📊 СТАТИСТИКА ТРАФИКА [{datetime.now().strftime('%H:%M:%S')}]")
        print(f"   Всего отправлено: {self.format_bytes(stats.get('total_bytes_sent', 0))}")
        print(f"   Активных IP: {stats.get('active_ips', 0)}")
        
        # Предупреждения по лимитам
        if total_gb > self.daily_limit_gb:
            print(f"🚨 ПРЕВЫШЕН ДНЕВНОЙ ЛИМИТ! {total_gb:.2f}GB > {self.daily_limit_gb}GB")
        elif total_gb > self.daily_limit_gb * 0.8:
            print(f"⚠️  Приближение к дневному лимиту: {total_gb:.2f}GB / {self.daily_limit_gb}GB")
        else:
            print(f"✅ В пределах дневного лимита: {total_gb:.2f}GB / {self.daily_limit_gb}GB")
        
        # Топ потребители
        top_consumers = stats.get('top_consumers', [])
        if top_consumers:
            print(f"\n🔥 ТОП ПОТРЕБИТЕЛИ ТРАФИКА:")
            for i, consumer in enumerate(top_consumers[:5], 1):
                ip = consumer['ip']
                mb = consumer['mb']
                print(f"   {i}. {ip}: {mb:.1f}MB")
                
                if mb > 50:  # Больше 50MB с одного IP
                    print(f"      ⚠️  Подозрительно высокое потребление!")
    
    def monitor_loop(self):
        """Основной цикл мониторинга"""
        print("🚀 Запуск мониторинга трафика...")
        print(f"📈 Цель: максимум {self.monthly_limit_gb}GB в месяц")
        print(f"📊 Дневной лимит: {self.daily_limit_gb}GB")
        print("-" * 50)
        
        while True:
            try:
                stats = self.get_stats()
                self.check_limits(stats)
                
                # Пауза между проверками
                time.sleep(60)  # Проверка каждую минуту
                
            except KeyboardInterrupt:
                print("\n👋 Мониторинг остановлен пользователем")
                break
            except Exception as e:
                print(f"❌ Ошибка в цикле мониторинга: {e}")
                time.sleep(60)

def main():
    monitor = BandwidthMonitor()
    
    # Однократная проверка
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        stats = monitor.get_stats()
        monitor.check_limits(stats)
    else:
        # Постоянный мониторинг
        monitor.monitor_loop()

if __name__ == "__main__":
    import sys
    main()
