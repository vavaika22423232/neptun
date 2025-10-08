#!/usr/bin/env python3
"""
Автоматическое управление трафиком
Блокирует IP-адреса с высоким потреблением
"""

import json
import requests
import os
from datetime import datetime

def block_high_traffic_ips():
    """Блокирует IP с высоким потреблением трафика"""
    
    # Получаем статистику
    try:
        response = requests.get('http://localhost:5000/admin/bandwidth_stats?token=admin123', timeout=10)
        if response.status_code != 200:
            print(f"❌ Не удалось получить статистику: {response.status_code}")
            return
        
        stats = response.json()
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return
    
    # Загружаем текущий список заблокированных IP
    blocked_ips_file = 'blocked_ips.json'
    try:
        with open(blocked_ips_file, 'r') as f:
            blocked_ips = set(json.load(f))
    except FileNotFoundError:
        blocked_ips = set()
    
    # Анализируем потребителей трафика
    top_consumers = stats.get('top_consumers', [])
    new_blocks = []
    
    for consumer in top_consumers:
        ip = consumer['ip']
        mb_used = consumer['mb']
        
        # Критерии для блокировки:
        # 1. Более 100MB трафика с одного IP за час
        # 2. IP не localhost/admin
        if mb_used > 100 and ip not in ['127.0.0.1', 'localhost', '::1']:
            if ip not in blocked_ips:
                blocked_ips.add(ip)
                new_blocks.append(ip)
                print(f"🚫 ЗАБЛОКИРОВАН IP: {ip} (потребление: {mb_used:.1f}MB)")
    
    # Сохраняем обновленный список
    if new_blocks:
        with open(blocked_ips_file, 'w') as f:
            json.dump(list(blocked_ips), f, indent=2)
        
        print(f"✅ Заблокировано {len(new_blocks)} новых IP-адресов")
        print(f"📊 Всего заблокировано: {len(blocked_ips)} IP")
    else:
        print("✅ Подозрительной активности не обнаружено")

def optimize_app_config():
    """Автоматически оптимизирует конфигурацию приложения"""
    
    config_file = 'bandwidth_config.json'
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    
    # Получаем текущую статистику
    try:
        response = requests.get('http://localhost:5000/admin/bandwidth_stats?token=admin123', timeout=10)
        if response.status_code == 200:
            stats = response.json()
            total_mb = stats.get('total_mb_sent', 0)
            
            # Если трафик высокий - ужесточаем лимиты
            if total_mb > 500:  # Более 500MB
                config['max_tracks_default'] = 25  # Уменьшаем еще больше
                config['max_tracks_limit'] = 100
                config['api_rate_limit'] = 30  # Более строгий лимит
                print("🔧 Активирован режим экономии трафика")
            else:
                config['max_tracks_default'] = 50
                config['max_tracks_limit'] = 200
                config['api_rate_limit'] = 60
                print("🔧 Нормальный режим работы")
            
            # Сохраняем конфигурацию
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
    except Exception as e:
        print(f"❌ Ошибка оптимизации конфигурации: {e}")

def generate_report():
    """Генерирует отчет по использованию трафика"""
    
    try:
        response = requests.get('http://localhost:5000/admin/bandwidth_stats?token=admin123', timeout=10)
        if response.status_code != 200:
            print(f"❌ Не удалось получить статистику для отчета")
            return
        
        stats = response.json()
        
        # Создаем отчет
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_mb_sent': stats.get('total_mb_sent', 0),
            'total_gb_sent': stats.get('total_mb_sent', 0) / 1024,
            'active_ips': stats.get('active_ips', 0),
            'top_consumers': stats.get('top_consumers', [])[:10],
            'projected_monthly_gb': (stats.get('total_mb_sent', 0) / 1024) * 30,  # Примерная проекция
            'status': 'OK' if stats.get('total_mb_sent', 0) < 500 else 'HIGH_USAGE'
        }
        
        # Сохраняем отчет
        report_file = f"bandwidth_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📋 Отчет сохранен: {report_file}")
        print(f"📊 Текущее потребление: {report['total_gb_sent']:.2f}GB")
        print(f"📈 Прогноз на месяц: {report['projected_monthly_gb']:.1f}GB")
        
        if report['projected_monthly_gb'] > 15:
            print("🚨 ПРЕДУПРЕЖДЕНИЕ: Прогноз превышает 15GB в месяц!")
        
    except Exception as e:
        print(f"❌ Ошибка генерации отчета: {e}")

def main():
    print("🛡️  Автоматическое управление трафиком")
    print("=" * 40)
    
    print("\n1️⃣ Блокировка IP с высоким потреблением...")
    block_high_traffic_ips()
    
    print("\n2️⃣ Оптимизация конфигурации...")
    optimize_app_config()
    
    print("\n3️⃣ Генерация отчета...")
    generate_report()
    
    print("\n✅ Управление трафиком завершено")

if __name__ == "__main__":
    main()
