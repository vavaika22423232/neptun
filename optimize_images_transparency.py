#!/usr/bin/env python3

"""
PNG optimization script with transparency preservation
This script reduces file sizes while maintaining transparency and visual quality
"""

import os
import sys
from PIL import Image, ImageFile
from pathlib import Path
import shutil
from datetime import datetime

# Allow loading of truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

def optimize_png_with_transparency(input_path, output_path=None, max_size=(800, 800)):
    """Optimize PNG file while preserving transparency"""
    if output_path is None:
        output_path = input_path
    
    try:
        with Image.open(input_path) as img:
            print(f"    📊 Original: {img.size}, mode: {img.mode}")
            
            # Preserve transparency based on original mode
            if img.mode == 'RGBA':
                # Keep RGBA mode for transparency
                optimized_img = img.copy()
            elif img.mode == 'P' and 'transparency' in img.info:
                # Convert palette with transparency to RGBA
                optimized_img = img.convert('RGBA')
            elif img.mode == 'LA':
                # Convert grayscale with alpha to RGBA
                optimized_img = img.convert('RGBA')
            else:
                # For images without transparency, keep as is
                optimized_img = img.copy()
            
            # Resize if too large
            if optimized_img.size[0] > max_size[0] or optimized_img.size[1] > max_size[1]:
                optimized_img.thumbnail(max_size, Image.Resampling.LANCZOS)
                print(f"    📐 Resized to: {optimized_img.size}")
            
            # Save with PNG optimization, preserving transparency
            optimized_img.save(output_path, 'PNG', optimize=True)
            print(f"    ✅ Saved: mode={optimized_img.mode}")
            
    except Exception as e:
        print(f"    ❌ Error optimizing {input_path}: {e}")
        return False
    
    return True

def get_file_size(file_path):
    """Get file size in bytes"""
    return os.path.getsize(file_path)

def format_bytes(bytes_size):
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} GB"

def optimize_directory():
    """Optimize all PNG files in static directory with transparency preservation"""
    static_dir = Path("static")
    backup_dir = Path("static_backup_20250911_182808")
    
    if not static_dir.exists():
        print("❌ Static directory not found!")
        return
        
    if not backup_dir.exists():
        print("❌ Backup directory not found!")
        return
    
    png_files = list(backup_dir.glob("*.png"))
    if not png_files:
        print("❌ No PNG files found in backup directory!")
        return
    
    print(f"🎯 Found {len(png_files)} PNG files to optimize with transparency preservation")
    print("-" * 80)
    
    total_original = 0
    total_optimized = 0
    processed = 0
    
    for png_file in png_files:
        output_file = static_dir / png_file.name
        original_size = get_file_size(png_file)
        total_original += original_size
        
        print(f"🖼️  Processing: {png_file.name}")
        print(f"    📦 Original size: {format_bytes(original_size)}")
        
        if optimize_png_with_transparency(str(png_file), str(output_file)):
            optimized_size = get_file_size(output_file)
            total_optimized += optimized_size
            savings = ((original_size - optimized_size) / original_size) * 100
            
            print(f"    💾 Optimized size: {format_bytes(optimized_size)}")
            print(f"    💰 Savings: {savings:.1f}%")
            processed += 1
        
        print()
    
    # Summary
    total_savings = ((total_original - total_optimized) / total_original) * 100
    print("=" * 80)
    print("📈 OPTIMIZATION SUMMARY WITH TRANSPARENCY:")
    print(f"   Files processed: {processed}/{len(png_files)}")
    print(f"   Original total: {format_bytes(total_original)}")
    print(f"   Optimized total: {format_bytes(total_optimized)}")
    print(f"   Total savings: {format_bytes(total_original - total_optimized)} ({total_savings:.1f}%)")
    print("=" * 80)
    
    if processed == len(png_files):
        print("✅ All PNG files optimized successfully with transparency preserved!")
    else:
        print(f"⚠️  {len(png_files) - processed} files had issues during optimization")

if __name__ == "__main__":
    print("🖼️  PNG Transparency-Preserving Optimization Tool")
    print("=" * 80)
    
    # Check if PIL is available
    try:
        from PIL import Image
        print("✅ PIL/Pillow is available")
    except ImportError:
        print("❌ PIL/Pillow not found. Install with: pip install Pillow")
        sys.exit(1)
    
    optimize_directory()
