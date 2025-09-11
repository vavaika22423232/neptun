#!/usr/bin/env python3

"""
Script to test if optimized transparent images are working correctly
"""

import os
from pathlib import Path

def test_image_transparency():
    """Test if current images have transparency"""
    static_dir = Path("static")
    test_files = ["shahed.png", "avia.png", "raketa.png"]
    
    print("🔍 Testing PNG transparency...")
    print("-" * 50)
    
    for filename in test_files:
        file_path = static_dir / filename
        if file_path.exists():
            # Use file command to check image format
            result = os.popen(f'file "{file_path}"').read().strip()
            
            print(f"📁 {filename}:")
            print(f"   {result}")
            
            if "RGBA" in result:
                print(f"   ✅ Has transparency")
            elif "RGB" in result:
                print(f"   ❌ No transparency (will show as gray squares)")
            else:
                print(f"   ⚠️  Unknown format")
            print()
    
    # Check placeholder files too
    placeholder_dir = static_dir / "placeholders"
    if placeholder_dir.exists():
        print("🔍 Testing placeholder transparency...")
        print("-" * 50)
        
        for filename in test_files:
            file_path = placeholder_dir / filename
            if file_path.exists():
                result = os.popen(f'file "{file_path}"').read().strip()
                
                print(f"📁 placeholders/{filename}:")
                print(f"   {result}")
                
                if "RGBA" in result:
                    print(f"   ✅ Has transparency")
                elif "RGB" in result:
                    print(f"   ❌ No transparency")
                print()

def show_cache_busting_info():
    """Show cache busting information"""
    print("💡 Cache Busting Information:")
    print("-" * 50)
    print("If you're still seeing gray squares on desktop:")
    print("1. The images have been updated with transparency")
    print("2. Your browser may be showing cached versions")
    print("3. Try these solutions:")
    print("   • Hard refresh: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)")
    print("   • Clear browser cache for the site")
    print("   • Open in private/incognito window")
    print("   • The app now uses ?v=20250911184500 parameters to force updates")
    print()
    print("📱 Mobile browsers typically handle cache better than desktop ones")

if __name__ == "__main__":
    print("🖼️  PNG Transparency Test Tool")
    print("=" * 60)
    
    test_image_transparency()
    show_cache_busting_info()
