#!/usr/bin/env bash
# Build embedded Photon DB for Ukraine (Photon 1.x) from GraphHopper JSON dump.
# ~260 MB download; fits small VPS disks (unlike ~30 GB Europe tar.bz2).
# Requires: docker, zstd, wget. Host Java is not required.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

DUMP_URL="${PHOTON_DUMP_URL:-https://download1.graphhopper.com/public/europe/ukraine/photon-dump-ukraine-1.0-latest.jsonl.zst}"
JAR_URL="${PHOTON_JAR_URL:-https://github.com/komoot/photon/releases/download/1.0.1/photon-1.0.1.jar}"
IMPORT_JAVA_XMX="${PHOTON_IMPORT_XMX:-2500m}"
DATA_DIR="$ROOT/photon_data"

data_ok() {
  # Photon 1.x embedded OpenSearch uses photon_data/node_1/; older dumps used nodes/indices
  [[ -d "$DATA_DIR/node_1/data" || -d "$DATA_DIR/nodes" || -d "$DATA_DIR/indices" ]]
}

needs_setup() {
  if [[ "${FORCE_PHOTON_DOWNLOAD:-0}" == "1" ]]; then
    return 0
  fi
  if data_ok; then
    echo "Photon data OK at $DATA_DIR — skip (set FORCE_PHOTON_DOWNLOAD=1 to rebuild)."
    return 1
  fi
  return 0
}

if ! needs_setup; then
  exit 0
fi

echo "Building Photon index from: $DUMP_URL"
command -v docker >/dev/null || { echo "docker not found" >&2; exit 1; }
command -v zstd >/dev/null || { echo "zstd not found (apt install zstd)" >&2; exit 1; }
command -v wget >/dev/null || { echo "wget not found" >&2; exit 1; }

DUMP="$ROOT/.photon-dump-ukraine.jsonl.zst.tmp"
JAR="$ROOT/.photon-import.jar.tmp"

rm -rf "$DATA_DIR"
wget -nv -O "$DUMP" "$DUMP_URL"
wget -nv -O "$JAR" "$JAR_URL"

set +o pipefail
zstd --stdout -d "$DUMP" | docker run --rm -i \
  -v "$ROOT:/work" -w /work \
  eclipse-temurin:21-jre \
  java "-Xmx${IMPORT_JAVA_XMX}" -jar "/work/$(basename "$JAR")" import -import-file -
imp_err=("${PIPESTATUS[@]}")
set -o pipefail
rm -f "$DUMP" "$JAR"

if [[ "${imp_err[0]}" -ne 0 ]] || [[ "${imp_err[1]}" -ne 0 ]]; then
  echo "Photon import failed (zstd exit=${imp_err[0]} docker exit=${imp_err[1]})" >&2
  exit 1
fi

if ! data_ok; then
  echo "Import finished but $DATA_DIR looks invalid (no node_1/data)" >&2
  exit 1
fi

echo "Photon data ready at $DATA_DIR"
