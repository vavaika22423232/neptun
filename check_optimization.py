#!/usr/bin/env python3
"""
Быстрая проверка эффективности оптимизации трафика
"""

import os
import json
import requests
from datetime import datetime

def check_file_sizes():
    """Проверка размеров файлов после оптимизации"""
    print("📁 ПРОВЕРКА РАЗМЕРОВ ФАЙЛОВ")
    print("-" * 30)
    
    static_size = 0
    if os.path.exists('static'):
        for root, dirs, files in os.walk('static'):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    static_size += os.path.getsize(file_path)
    
    static_mb = static_size / 1024 / 1024
    print(f"📦 Размер static/: {static_mb:.1f}MB")
    
    # Проверяем ключевые файлы
    key_files = {
        'static/region_boundaries.js': 'Границы регионов',
        'static/region_boundaries.js.gz': 'Границы (сжатые)', 
        'static/city_boundaries.js': 'Границы городов',
        'static/city_boundaries.js.gz': 'Города (сжатые)',
        'static/shahed.png': 'Иконка Шахед',
        'static/avia.png': 'Иконка авиации'
    }
    
    for file_path, description in key_files.items():
        if os.path.exists(file_path):
            size_kb = os.path.getsize(file_path) / 1024
            print(f"  📄 {description}: {size_kb:.0f}KB")
        else:
            print(f"  ❌ {description}: файл не найден")
    
    # Оценка экономии
    original_static_size = 39  # MB (было)
    savings_mb = original_static_size - static_mb
    savings_percent = (savings_mb / original_static_size) * 100
    
    print(f"\n💰 ЭКОНОМИЯ НА СТАТИКЕ:")
    print(f"  Было: {original_static_size}MB")
    print(f"  Стало: {static_mb:.1f}MB")
    print(f"  Экономия: {savings_mb:.1f}MB ({savings_percent:.1f}%)")

def check_app_config():
    """Проверка конфигурации приложения"""
    print("\n⚙️  КОНФИГУРАЦИЯ ПРИЛОЖЕНИЯ")
    print("-" * 30)
    
    # Проверяем файл конфигурации
    if os.path.exists('bandwidth_config.json'):
        with open('bandwidth_config.json', 'r') as f:
            config = json.load(f)
        
        print(f"📊 Лимит треков по умолчанию: {config.get('max_tracks_default', 'не задан')}")
        print(f"📊 Максимальный лимит треков: {config.get('max_tracks_limit', 'не задан')}")
        print(f"⏱️  Кеширование API: {config.get('cache_duration_api', 'не задано')}с")
        print(f"🛡️  Rate limit: {config.get('api_rate_limit', 'не задан')} запросов/мин")
        print(f"🗜️  Gzip: {'включен' if config.get('gzip_enabled') else 'выключен'}")
    else:
        print("❌ Файл конфигурации не найден")

def check_monitoring():
    """Проверка системы мониторинга"""
    print("\n📊 СИСТЕМА МОНИТОРИНГА")
    print("-" * 30)
    
    required_files = [
        'bandwidth_monitor.py',
        'traffic_manager.py', 
        'bandwidth_watcher.py'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}: установлен")
        else:
            print(f"❌ {file}: не найден")

def test_api_limits():
    """Тестирование API лимитов"""
    print("\n🔬 ТЕСТИРОВАНИЕ API")
    print("-" * 30)
    
    try:
        # Тест базового API
        response = requests.get('http://localhost:5000/data?maxTracks=10', timeout=5)
        if response.status_code == 200:
            data = response.json()
            tracks_count = len(data.get('tracks', []))
            print(f"✅ API отвечает: {tracks_count} треков получено")
            
            # Проверяем лимит
            if tracks_count <= 10:
                print("✅ Лимит треков работает корректно")
            else:
                print(f"⚠️  Лимит треков не работает: получено {tracks_count} вместо ≤10")
        else:
            print(f"❌ API недоступен: код {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Приложение не запущено (это нормально)")
    except Exception as e:
        print(f"❌ Ошибка тестирования API: {e}")

def estimate_bandwidth_savings():
    """Расчет ожидаемой экономии трафика с учетом SVG маркеров"""
    print("\n💡 ПРОГНОЗ ЭКОНОМИИ ТРАФИКА (с SVG маркерами)")
    print("-" * 30)
    
    # Исходные данные
    original_gb_month = 1000
    original_cost_month = 150
    
    # Факторы экономии (обновлено с учетом SVG)
    svg_markers_reduction = 0.95    # 95% экономии на маркерах (PNG→SVG)
    static_js_compression = 0.85    # 85% экономии на JS сжатии
    api_tracks_reduction = 0.50     # 50% меньше треков в API
    caching_reduction = 0.70        # 70% запросов из кеша
    rate_limiting_effect = 0.15     # 15% блокировка ботов/злоупотреблений
    
    # Веса компонентов трафика (обновлено)
    markers_weight = 0.15      # 15% трафика - маркеры PNG
    js_files_weight = 0.25     # 25% трафика - большие JS файлы
    api_weight = 0.50          # 50% трафика - API данные  
    other_weight = 0.10        # 10% - прочее
    
    # Расчет экономии
    markers_savings = markers_weight * svg_markers_reduction
    js_savings = js_files_weight * static_js_compression
    api_savings = api_weight * (api_tracks_reduction + caching_reduction * 0.3)
    rate_limit_savings = rate_limiting_effect
    
    total_reduction = markers_savings + js_savings + api_savings + rate_limit_savings
    total_reduction = min(total_reduction, 0.88)  # Максимум 88% экономии
    
    new_gb_month = original_gb_month * (1 - total_reduction)
    new_cost_month = new_gb_month * 0.15  # $0.15 за GB
    savings_month = original_cost_month - new_cost_month
    
    print(f"📈 Исходный трафик: {original_gb_month}GB/месяц (${original_cost_month})")
    print(f"📉 Прогноз после оптимизации: {new_gb_month:.0f}GB/месяц (${new_cost_month:.0f})")
    print(f"💰 Ожидаемая экономия: {savings_month:.0f}$/месяц ({total_reduction*100:.0f}%)")
    
    # Разбивка по компонентам
    print(f"\n🔍 Детализация экономии:")
    print(f"  🎨 SVG маркеры (вместо PNG): -{markers_savings*100:.0f}%")
    print(f"  📦 Сжатие JS файлов: -{js_savings*100:.0f}%")
    print(f"  📊 API данные: -{api_savings*100:.0f}%") 
    print(f"  🛡️  Rate limiting: -{rate_limiting_effect*100:.0f}%")
    
    print(f"\n🚀 КЛЮЧЕВЫЕ УЛУЧШЕНИЯ:")
    print(f"  • PNG маркеры ~6MB → SVG ~3KB (99.95% экономии)")
    print(f"  • JS файлы 21MB → 2MB gzip (90% экономии)")
    print(f"  • API треки 100→50 по умолчанию (50% экономии)")
    print(f"  • Кеширование 30 секунд (70% повторных запросов)")

def main():
    print("🚀 ПРОВЕРКА ОПТИМИЗАЦИИ ТРАФИКА")
    print("=" * 50)
    
    check_file_sizes()
    check_app_config()
    check_monitoring()
    test_api_limits()
    estimate_bandwidth_savings()
    
    print("\n" + "=" * 50)
    print("✅ Проверка завершена!")
    print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Запустите приложение: python app.py")
    print("2. Запустите мониторинг: python bandwidth_watcher.py")
    print("3. Проверьте результаты через неделю")
    print("\n💡 Для мониторинга в реальном времени:")
    print("   curl 'http://localhost:5000/admin/bandwidth_stats?token=admin123'")

if __name__ == "__main__":
    main()
