#!/usr/bin/env python3

"""
PNG optimization script using Python PIL for slow internet connections
This script reduces file sizes while maintaining visual quality
"""

import os
import sys
from PIL import Image, ImageFile
from pathlib import Path
import shutil
from datetime import datetime

# Allow loading of truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

def optimize_png(input_path, output_path=None, quality=85, max_size=(800, 800)):
    """Optimize PNG file for web usage"""
    if output_path is None:
        output_path = input_path
    
    try:
        with Image.open(input_path) as img:
            # Convert to RGB if necessary (removes alpha channel for smaller size)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if 'transparency' in img.info:
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            
            # Resize if too large (most icons don't need to be huge)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                print(f"    📐 Resized from original size to {img.size}")
            
            # Optimize and save
            img.save(output_path, 'PNG', optimize=True, quality=quality)
            
    except Exception as e:
        print(f"    ❌ Error optimizing {input_path}: {e}")
        return False
    
    return True

def main():
    static_dir = Path('static')
    if not static_dir.exists():
        print("❌ Static directory not found")
        return
    
    # Create backup
    backup_dir = Path(f"static_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    backup_dir.mkdir(exist_ok=True)
    
    print("🔧 Optimizing PNG images for slow internet connections...")
    print(f"📦 Creating backup in {backup_dir}...")
    
    png_files = list(static_dir.glob('*.png'))
    if not png_files:
        print("❌ No PNG files found in static directory")
        return
    
    print(f"🔍 Found {len(png_files)} PNG files:")
    
    total_original = 0
    total_optimized = 0
    
    for png_file in png_files:
        if png_file.stat().st_size == 0:
            print(f"  ⚠️ Skipping empty file: {png_file.name}")
            continue
            
        # Backup original
        shutil.copy2(png_file, backup_dir / png_file.name)
        
        original_size = png_file.stat().st_size
        total_original += original_size
        
        print(f"  📄 Processing: {png_file.name} ({original_size // 1024}KB)")
        
        # Optimize
        if optimize_png(png_file):
            new_size = png_file.stat().st_size
            total_optimized += new_size
            
            if original_size > new_size:
                savings = original_size - new_size
                percent_savings = (savings * 100) // original_size
                print(f"    ✅ Saved {percent_savings}% ({savings // 1024}KB)")
            else:
                print(f"    📌 Already optimized")
        
    if total_original > 0:
        total_savings = total_original - total_optimized
        percent_total = (total_savings * 100) // total_original
        print(f"\n🎉 Optimization complete!")
        print(f"💡 Total savings: {percent_total}% ({total_savings // 1024}KB)")
        print(f"💾 Backup stored in: {backup_dir}")
        print(f"🚀 Images are now optimized for slow internet connections!")

if __name__ == '__main__':
    main()
