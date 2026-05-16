#!/usr/bin/env bash
# Оновлює ios/Flutter/Generated.xcconfig (Version / Build у Xcode) з version у pubspec.yaml.
set -euo pipefail
cd "$(dirname "$0")"
flutter pub get
flutter build ios --config-only
echo "OK: FLUTTER_BUILD_NAME / FLUTTER_BUILD_NUMBER у ios/Flutter/Generated.xcconfig відповідають pubspec."
