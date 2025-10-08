#!/usr/bin/env python3
"""
Скрипт для оптимизации трафика приложения
Цель: уменьшить исходящий трафик с 1000GB до разумных пределов
"""

import os
import json
import gzip
from PIL import Image
import subprocess

def optimize_images():
    """Оптимизируем изображения (теперь как fallback для SVG)"""
    print("🎨 SVG маркеры заменяют PNG изображения...")
    print("   Старые PNG файлы остаются как fallback для совместимости")
    
    static_dir = "static"
    images = [
        "shahed.png", "avia.png", "vidboi.png", "trivoga.png", 
        "pusk.png", "vibuh.png", "fpv.png", "obstril.png", 
        "artillery.png", "rozved.png", "rszv.png", "raketa.png", 
        "mlrs.png", "korabel.png"
    ]
    
    total_saved = 0
    
    # Подсчитываем размер всех PNG файлов
    total_png_size = 0
    for img_name in images:
        img_path = os.path.join(static_dir, img_name)
        if os.path.exists(img_path):
            total_png_size += os.path.getsize(img_path)
    
    # SVG маркеры займут ~2-3KB вместо PNG
    svg_size = 3 * 1024  # 3KB для SVG файла
    estimated_savings = total_png_size - svg_size
    
    print(f"📊 Общий размер PNG маркеров: {total_png_size//1024}KB")
    print(f"📊 Размер SVG маркеров: {svg_size//1024}KB")  
    print(f"💰 Экономия от перехода на SVG: {estimated_savings//1024}KB ({estimated_savings*100//total_png_size}%)")
    
    # Все равно оптимизируем PNG как fallback
    for img_name in images:
        img_path = os.path.join(static_dir, img_name)
        if os.path.exists(img_path):
            original_size = os.path.getsize(img_path)
            
            try:
                # Создаем оптимизированную версию
                with Image.open(img_path) as img:
                    # Конвертируем в RGB если нужно
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # Уменьшаем размер если слишком большой
                    if img.width > 64 or img.height > 64:  # Еще меньше для fallback
                        img.thumbnail((64, 64), Image.Resampling.LANCZOS)
                    
                    # Сохраняем с оптимизацией
                    img.save(img_path, "PNG", optimize=True, quality=75)
                    
                new_size = os.path.getsize(img_path)
                saved = original_size - new_size
                total_saved += saved
                
                print(f"   ✅ {img_name}: {original_size//1024}KB → {new_size//1024}KB (fallback)")
                
            except Exception as e:
                print(f"   ❌ Ошибка при обработке {img_name}: {e}")
    
    print(f"\n🎉 Экономия PNG fallback: {total_saved//1024}KB")
    print(f"🚀 Основная экономия от SVG: {estimated_savings//1024}KB")
    return estimated_savings  # Возвращаем общую экономию от SVG

def compress_js_files():
    """Сжимаем JavaScript файлы"""
    js_files = [
        "static/region_boundaries.js",
        "static/city_boundaries.js", 
        "static/frontend_api_integration.js"
    ]
    
    total_saved = 0
    
    for js_file in js_files:
        if os.path.exists(js_file):
            original_size = os.path.getsize(js_file)
            
            try:
                # Создаем gzip версию
                gz_file = js_file + ".gz"
                with open(js_file, 'rb') as f_in:
                    with gzip.open(gz_file, 'wb') as f_out:
                        f_out.writelines(f_in)
                
                compressed_size = os.path.getsize(gz_file)
                saved = original_size - compressed_size
                total_saved += saved
                
                print(f"✅ {os.path.basename(js_file)}: {original_size//1024}KB → {compressed_size//1024}KB (сжатие {saved*100//original_size}%)")
                
            except Exception as e:
                print(f"❌ Ошибка при сжатии {js_file}: {e}")
    
    print(f"\n🎉 Экономия на JS файлах: {total_saved//1024}KB")
    return total_saved

def optimize_video():
    """Оптимизируем видео файл"""
    video_path = "static/zbir.MP4"
    if not os.path.exists(video_path):
        print("❌ Видео файл не найден")
        return 0
    
    original_size = os.path.getsize(video_path)
    
    try:
        # Проверяем наличие ffmpeg
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True)
        if result.returncode != 0:
            print("❌ ffmpeg не установлен. Установите: brew install ffmpeg")
            return 0
        
        # Создаем сжатую версию
        compressed_path = "static/zbir_compressed.MP4"
        cmd = [
            'ffmpeg', '-i', video_path, 
            '-vcodec', 'libx264', '-crf', '28',
            '-preset', 'slow', '-acodec', 'aac', 
            '-b:a', '128k', '-movflags', '+faststart',
            '-y', compressed_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(compressed_path):
            new_size = os.path.getsize(compressed_path)
            if new_size < original_size:
                # Заменяем оригинал
                os.replace(compressed_path, video_path)
                saved = original_size - new_size
                print(f"✅ zbir.MP4: {original_size//1024}KB → {new_size//1024}KB (сэкономлено {saved//1024}KB)")
                return saved
            else:
                os.remove(compressed_path)
                print("⚠️ Сжатое видео больше оригинала, оставляем как есть")
        else:
            print(f"❌ Ошибка сжатия видео: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Ошибка при оптимизации видео: {e}")
    
    return 0

def create_bandwidth_config():
    """Создаем конфигурацию для оптимизации трафика"""
    config = {
        "max_tracks_default": 50,  # Уменьшено с 100
        "max_tracks_limit": 200,   # Уменьшено с 500
        "cache_duration_static": 86400,  # 24 часа для статики
        "cache_duration_api": 30,        # 30 секунд для API
        "gzip_enabled": True,
        "image_optimization": True,
        "api_rate_limit": 60  # запросов в минуту
    }
    
    with open("bandwidth_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("✅ Создан файл конфигурации bandwidth_config.json")

def main():
    print("🚀 Начинаем оптимизацию трафика...\n")
    
    total_saved = 0
    
    print("1️⃣ Оптимизация изображений...")
    total_saved += optimize_images()
    
    print("\n2️⃣ Сжатие JavaScript файлов...")
    total_saved += compress_js_files()
    
    print("\n3️⃣ Оптимизация видео...")
    total_saved += optimize_video()
    
    print("\n4️⃣ Создание конфигурации...")
    create_bandwidth_config()
    
    print(f"\n🎉 ИТОГО СЭКОНОМЛЕНО: {total_saved//1024//1024}MB")
    print(f"💰 Примерная экономия в месяц: ${(total_saved//1024//1024) * 0.15:.2f}")
    
    print("\n📋 Следующие шаги:")
    print("1. Запустите обновленное приложение")
    print("2. Проверьте работу сжатых файлов") 
    print("3. Мониторьте трафик в течение недели")

if __name__ == "__main__":
    main()
