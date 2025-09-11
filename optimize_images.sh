#!/bin/bash

# PNG optimization script for slow internet connections
# This script reduces file sizes while maintaining visual quality

echo "🔧 Optimizing PNG images for slow internet connections..."

# Check if required tools are available
command -v optipng >/dev/null 2>&1 || {
    echo "⚠️ optipng not found, installing..."
    if command -v brew >/dev/null 2>&1; then
        brew install optipng
    else
        echo "❌ Please install optipng manually"
        exit 1
    fi
}

# Create backup directory
BACKUP_DIR="static_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup in $BACKUP_DIR..."
cp static/*.png "$BACKUP_DIR/" 2>/dev/null || true

cd static

echo "🔍 Found PNG files:"
ls -la *.png 2>/dev/null || { echo "No PNG files found"; exit 0; }

echo ""
echo "📊 Original file sizes:"
du -h *.png 2>/dev/null | sort -hr

echo ""
echo "⚡ Optimizing files..."

# Optimize each PNG file
for file in *.png; do
    if [ -f "$file" ] && [ -s "$file" ]; then
        echo "  Processing: $file"
        original_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        
        # Use optipng for lossless compression
        optipng -o2 -quiet "$file" 2>/dev/null || {
            echo "    ⚠️ Failed to optimize $file, skipping"
            continue
        }
        
        new_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        
        if [ "$original_size" -gt 0 ]; then
            savings=$((original_size - new_size))
            percent_savings=$((savings * 100 / original_size))
            
            if [ "$percent_savings" -gt 0 ]; then
                echo "    ✅ Saved ${percent_savings}% ($(echo $savings | awk '{print int($1/1024)"KB"}')"
            else
                echo "    📌 Already optimized"
            fi
        fi
    fi
done

echo ""
echo "📊 Optimized file sizes:"
du -h *.png 2>/dev/null | sort -hr

echo ""
echo "🎉 PNG optimization complete!"
echo "💾 Backup stored in: ../$BACKUP_DIR"

# Calculate total savings
original_total=$(du -sb "../$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "0")
new_total=$(du -sb . 2>/dev/null | awk '/\.png$/{sum+=$1}END{print sum+0}')

if [ "$original_total" -gt 0 ] && [ "$new_total" -gt 0 ]; then
    total_savings=$((original_total - new_total))
    if [ "$total_savings" -gt 0 ]; then
        percent_total=$((total_savings * 100 / original_total))
        echo "💡 Total savings: ${percent_total}% ($(echo $total_savings | awk '{print int($1/1024)"KB"}')"
    fi
fi

echo ""
echo "🚀 Your images are now optimized for slow internet connections!"
