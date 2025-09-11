#!/usr/bin/env python3

"""
Create tiny placeholder images (64x64) for super-fast loading
"""

import os
from PIL import Image
from pathlib import Path

def create_placeholder(input_path, output_path, size=(32, 32)):
    """Create a tiny placeholder version of the image"""
    try:
        with Image.open(input_path) as img:
            # Convert to RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if 'transparency' in img.info:
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            
            # Create tiny thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save with maximum compression
            img.save(output_path, 'PNG', optimize=True, quality=20)
            
    except Exception as e:
        print(f"    ❌ Error creating placeholder for {input_path}: {e}")
        return False
    
    return True

def main():
    static_dir = Path('static')
    placeholder_dir = static_dir / 'placeholders'
    placeholder_dir.mkdir(exist_ok=True)
    
    print("🚀 Creating tiny placeholder images for instant loading...")
    
    png_files = list(static_dir.glob('*.png'))
    
    for png_file in png_files:
        if png_file.stat().st_size == 0:
            continue
            
        placeholder_path = placeholder_dir / png_file.name
        
        print(f"  📄 Creating placeholder: {png_file.name}")
        
        if create_placeholder(png_file, placeholder_path):
            original_size = png_file.stat().st_size
            placeholder_size = placeholder_path.stat().st_size
            reduction = (original_size - placeholder_size) * 100 // original_size
            print(f"    ✅ {reduction}% smaller ({placeholder_size // 1024}KB → {placeholder_size} bytes)")

    print(f"\n🎉 Placeholders created in: {placeholder_dir}")
    print(f"🚀 Super-fast loading enabled!")

if __name__ == '__main__':
    main()
