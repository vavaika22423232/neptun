#!/usr/bin/env python3

"""
Create transparent placeholder images for progressive loading
"""

import os
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path

def create_transparent_placeholder(input_path, output_path, size=(32, 32)):
    """Create a small transparent placeholder from source image"""
    try:
        with Image.open(input_path) as img:
            # Convert to RGBA to ensure transparency support
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Create thumbnail
            placeholder = img.copy()
            placeholder.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Apply slight blur for smooth placeholder effect
            placeholder = placeholder.filter(ImageFilter.GaussianBlur(radius=0.5))
            
            # Make sure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save with maximum PNG compression but preserve transparency
            placeholder.save(output_path, 'PNG', optimize=True)
            
            print(f"    ✅ Created transparent placeholder: {placeholder.size}, mode: {placeholder.mode}")
            return True
            
    except Exception as e:
        print(f"    ❌ Error creating placeholder: {e}")
        return False

def create_all_transparent_placeholders():
    """Create transparent placeholders for all PNG files"""
    static_dir = Path("static")
    placeholder_dir = Path("static/placeholders")
    
    # Create placeholder directory
    placeholder_dir.mkdir(exist_ok=True)
    
    png_files = list(static_dir.glob("*.png"))
    if not png_files:
        print("❌ No PNG files found in static directory!")
        return
    
    print(f"🎯 Creating transparent placeholders for {len(png_files)} PNG files")
    print("-" * 60)
    
    success_count = 0
    
    for png_file in png_files:
        placeholder_path = placeholder_dir / png_file.name
        
        print(f"🖼️  Processing: {png_file.name}")
        
        if create_transparent_placeholder(str(png_file), str(placeholder_path)):
            # Show file sizes
            original_size = os.path.getsize(png_file)
            placeholder_size = os.path.getsize(placeholder_path)
            reduction = ((original_size - placeholder_size) / original_size) * 100
            
            print(f"    📦 Original: {original_size:,} bytes")
            print(f"    📦 Placeholder: {placeholder_size:,} bytes ({reduction:.1f}% reduction)")
            success_count += 1
        
        print()
    
    print("=" * 60)
    print(f"✅ Successfully created {success_count}/{len(png_files)} transparent placeholders")
    print("=" * 60)

if __name__ == "__main__":
    print("🖼️  Transparent Placeholder Generator")
    print("=" * 60)
    create_all_transparent_placeholders()
