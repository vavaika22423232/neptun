#!/bin/sh
# Manual fallback: Xcode builds already run ios/flutter_xcode_backend_wrapper.sh
# to symlink build/ off Desktop. Use this script if you only use CLI tools or
# need to fix a plain build/ directory after flutter clean.
#
# Flutter forces BUILD_DIR to <project>/build/ios; on macOS, products under
# Desktop/Documents/iCloud then fail codesign ("resource fork..."). Symlinking
# build/ to ~/Library/Caches avoids that.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/build"
CACHE="${HOME}/Library/Caches/neptun_alarm_flutter_build"

case "$(uname -s)" in
Darwin) ;;
*)
  echo "This workaround is only for macOS."
  exit 0
  ;;
esac

case "$ROOT" in
*/Desktop/*|*/Documents/*|*Mobile*Documents*) ;;
*)
  echo "Project path is not under Desktop, Documents, or iCloud Drive; skipping."
  exit 0
  ;;
esac

mkdir -p "$CACHE"

if [ -L "$BUILD" ]; then
  current="$(readlink "$BUILD")"
  if [ "$current" = "$CACHE" ]; then
    echo "build/ already links to the host cache."
    exit 0
  fi
  rm "$BUILD"
elif [ -d "$BUILD" ]; then
  echo "Moving existing build/ into host cache (merge)..."
  # Merge into cache so we do not lose partial outputs.
  ditto "$BUILD" "$CACHE" 2>/dev/null || cp -R "$BUILD/." "$CACHE/"
  rm -rf "$BUILD"
fi

ln -s "$CACHE" "$BUILD"
echo "Linked $BUILD -> $CACHE"
echo "You can run flutter run / Xcode builds as usual."
echo ""
echo "After \"flutter clean\", the build/ symlink is removed — run this script"
echo "again, then \"flutter pub get\". The cache at:"
echo "  $CACHE"
echo "is not deleted by flutter clean. To wipe it: rm -rf \"$CACHE\""
