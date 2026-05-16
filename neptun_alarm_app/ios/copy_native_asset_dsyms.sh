#!/bin/sh
# Dart native assets (e.g. package objective_c) embed a framework without a dSYM.
# Xcode 16+ / App Store Connect validation requires a dSYM whose UUID matches the binary.
# dsymutil produces a bundle with the correct UUID (symbols may be minimal).

set -u

OBJC_BIN="${TARGET_BUILD_DIR}/${WRAPPER_NAME}/Frameworks/objective_c.framework/objective_c"
if [ ! -f "$OBJC_BIN" ]; then
  exit 0
fi

mkdir -p "${DWARF_DSYM_FOLDER_PATH}"
DSYM_OUT="${DWARF_DSYM_FOLDER_PATH}/objective_c.framework.dSYM"
rm -rf "$DSYM_OUT"

if ! /usr/bin/dsymutil "$OBJC_BIN" -o "$DSYM_OUT" 2>/dev/null; then
  echo "warning: copy_native_asset_dsyms: dsymutil failed for objective_c.framework" >&2
  exit 0
fi

if [ ! -d "$DSYM_OUT" ]; then
  echo "warning: copy_native_asset_dsyms: missing ${DSYM_OUT}" >&2
fi
