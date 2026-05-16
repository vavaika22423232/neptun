#!/bin/sh
# Flutter sets BUILD_DIR under the project; on macOS, Desktop/Documents/iCloud
# paths make codesign fail on App.framework. Keep project/build as a symlink to
# ~/Library/Caches so binaries are not on a TCC-protected volume path.
set -e
if [ "$(uname -s)" = "Darwin" ]; then
  case "${FLUTTER_APPLICATION_PATH:-}" in
    */Desktop/*|*/Documents/*|*Mobile*Documents*)
      _CACHE="${HOME}/Library/Caches/neptun_alarm_flutter_build"
      _BUILD="${FLUTTER_APPLICATION_PATH}/build"
      mkdir -p "${_CACHE}"
      if [ -e "${_BUILD}" ] && [ ! -L "${_BUILD}" ]; then
        ditto "${_BUILD}" "${_CACHE}" 2>/dev/null || cp -R "${_BUILD}/." "${_CACHE}/" 2>/dev/null || true
        rm -rf "${_BUILD}"
      fi
      if [ ! -e "${_BUILD}" ]; then
        ln -sf "${_CACHE}" "${_BUILD}"
      elif [ -L "${_BUILD}" ]; then
        _CUR=$(readlink "${_BUILD}")
        if [ "${_CUR}" != "${_CACHE}" ]; then
          rm "${_BUILD}"
          ln -sf "${_CACHE}" "${_BUILD}"
        fi
      fi
      ;;
  esac
fi
exec /bin/sh "${FLUTTER_ROOT}/packages/flutter_tools/bin/xcode_backend.sh" "$@"
