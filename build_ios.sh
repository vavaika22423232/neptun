#!/bin/bash

# Create Xcode project structure
PROJECT_NAME="NeptunAlarmMap"
PROJECT_DIR="$HOME/Desktop/render2/${PROJECT_NAME}iOS"

# Clean old build
rm -rf "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/$PROJECT_NAME"

# Copy source files
cp ios-app/*.swift "$PROJECT_DIR/$PROJECT_NAME/" 2>/dev/null || true

# Create Info.plist
cat > "$PROJECT_DIR/$PROJECT_NAME/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key>
    <string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>$(PRODUCT_NAME)</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSRequiresIPhoneOS</key>
    <true/>
    <key>UILaunchScreen</key>
    <dict/>
    <key>NSLocationWhenInUseUsageDescription</key>
    <string>Додаток потребує доступ до вашого місцезнаходження для показу тривог</string>
</dict>
</plist>
PLIST

echo "✅ Project structure created at $PROJECT_DIR"
echo "📱 Open in Xcode: open $PROJECT_DIR"

