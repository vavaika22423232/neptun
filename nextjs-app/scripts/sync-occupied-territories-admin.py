#!/usr/bin/env python3
"""Rebuild nextjs-app/public/ukraine_occupied_territories_admin.geojson from ukraine_oblasts.geojson.

Зараз вибираються лише АР Крим (UA.KR) та м. Севастополь (UA.SC) — повний адмінконтур
зі того самого GADM-набору, що й області на карті. Для материкових ТОТ потрібні окремі
полігони (лінія фронту змінюється); їх можна тримати у public/ukraine_occupied_territories_extra.geojson
(мерджиться з адміншаром у рантаймі) або додавати як нові features у цей файл після узгодження джерела."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "public" / "ukraine_oblasts.geojson"
DST = ROOT / "public" / "ukraine_occupied_territories_admin.geojson"
HASCS = frozenset({"UA.KR", "UA.SC"})


def main() -> None:
    with SRC.open(encoding="utf-8") as f:
        g = json.load(f)
    feats_out = []
    for feat in g.get("features", []):
        p = feat.get("properties") or {}
        if p.get("HASC_1") not in HASCS:
            continue
        feats_out.append(
            {
                "type": "Feature",
                "properties": {
                    "HASC_1": p.get("HASC_1"),
                    "name_uk": p.get("NL_NAME_1") or p.get("NAME_1"),
                    "layer": "temporarily_occupied_admin",
                },
                "geometry": feat["geometry"],
            }
        )
    out = {
        "type": "FeatureCollection",
        "name": "ukraine_occupied_territories_admin",
        "description": "АР Крим та м. Севастополь з ukraine_oblasts.geojson. Материкові ТОТ окремо не включені.",
        "features": feats_out,
    }
    DST.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {len(feats_out)} features -> {DST}")


if __name__ == "__main__":
    main()
