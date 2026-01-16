#!/bin/bash

# iOS Build Script for App Store Release
# Usage: ./build_ios_release.sh [version] [build_number]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
VERSION=${1:-"1.4.1"}
BUILD_NUMBER=${2:-"25"}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  iOS App Store Build Script${NC}"
echo -e "${GREEN}  Version: $VERSION+$BUILD_NUMBER${NC}"
echo -e "${GREEN}========================================${NC}"

# Navigate to project directory
cd "$(dirname "$0")"
cd neptun_alarm_app

# Step 1: Clean previous builds
echo -e "\n${YELLOW}Step 1: Cleaning previous builds...${NC}"
flutter clean
rm -rf ios/Pods
rm -rf ios/Podfile.lock
rm -rf ios/.symlinks
rm -rf ios/Flutter/Flutter.framework
rm -rf ios/Flutter/Flutter.podspec

# Step 2: Get dependencies
echo -e "\n${YELLOW}Step 2: Getting Flutter dependencies...${NC}"
flutter pub get

# Step 3: Update CocoaPods
echo -e "\n${YELLOW}Step 3: Installing CocoaPods dependencies...${NC}"
cd ios
pod install --repo-update
cd ..

# Step 4: Build iOS release
echo -e "\n${YELLOW}Step 4: Building iOS release...${NC}"
flutter build ios \
  --release \
  --build-name=$VERSION \
  --build-number=$BUILD_NUMBER \
  --dart-define=ENV=production \
  --obfuscate \
  --split-debug-info=build/debug-info

# Step 5: Archive for App Store
echo -e "\n${YELLOW}Step 5: Creating Xcode archive...${NC}"
cd ios
xcodebuild -workspace Runner.xcworkspace \
  -scheme Runner \
  -configuration Release \
  -archivePath build/Runner.xcarchive \
  archive \
  CODE_SIGN_IDENTITY="" \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGNING_ALLOWED=NO

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Build completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nNext steps:"
echo -e "1. Open Xcode: ${YELLOW}open ios/Runner.xcworkspace${NC}"
echo -e "2. Select 'Product' > 'Archive'"
echo -e "3. In Organizer, click 'Distribute App'"
echo -e "4. Choose 'App Store Connect' and follow the wizard"
echo -e "\nOr use Transporter app to upload the archive."

# Print build info
echo -e "\n${GREEN}Build Info:${NC}"
echo -e "  Version: $VERSION"
echo -e "  Build: $BUILD_NUMBER"
echo -e "  Archive: ios/build/Runner.xcarchive"
echo -e "  Debug symbols: build/debug-info/"
