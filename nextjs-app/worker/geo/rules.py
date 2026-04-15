"""
Validation rules: point-in-polygon, bounding box, Ukraine boundary check.

Uses a pure-Python ray-casting algorithm for polygon checks — zero external deps.
"""

import json
import logging
import os
from typing import Optional

log = logging.getLogger(__name__)

# ── Ukraine bounding box ─────────────────────────────────────────────────────

UKRAINE_LAT_MIN = 43.0
UKRAINE_LAT_MAX = 53.8
UKRAINE_LNG_MIN = 21.0
UKRAINE_LNG_MAX = 41.5

# ── Oblast bounding boxes (from visicom_geocoder.py) ─────────────────────────
# Format: (min_lat, max_lat, min_lng, max_lng)

OBLAST_BBOX = {
    'Київська область':           (49.0, 52.0, 29.0, 32.5),
    'Харківська область':          (48.5, 50.5, 35.0, 38.5),
    'Одеська область':             (45.0, 48.5, 28.5, 31.5),  # max_lng: exclude Kryvyi Rih (33.39°)
    'Дніпропетровська область':    (47.5, 49.5, 32.5, 36.5),  # min_lng: include Kryvyi Rih (33.39°)
    'Запорізька область':          (46.5, 48.5, 34.0, 37.0),
    'Львівська область':           (48.5, 50.5, 22.5, 25.5),
    'Миколаївська область':        (46.0, 48.5, 30.5, 33.5),
    'Херсонська область':          (45.5, 47.5, 32.0, 35.5),
    'Полтавська область':          (48.5, 50.5, 32.5, 35.5),
    'Сумська область':             (50.0, 52.5, 32.0, 36.0),
    'Чернігівська область':        (50.5, 52.5, 30.0, 33.5),
    'Вінницька область':           (48.0, 50.0, 27.0, 30.0),
    'Житомирська область':         (49.5, 51.5, 27.0, 30.5),
    'Черкаська область':           (48.5, 50.0, 30.5, 33.0),
    'Кіровоградська область':      (47.5, 49.5, 31.0, 34.0),
    'Донецька область':            (47.0, 49.5, 36.5, 39.0),
    'Луганська область':           (47.5, 50.0, 38.0, 40.5),
    'Хмельницька область':         (48.5, 50.5, 25.5, 28.5),
    'Рівненська область':          (50.0, 52.0, 25.0, 27.5),
    'Волинська область':           (50.5, 52.5, 23.5, 26.0),
    'Тернопільська область':       (48.5, 50.5, 24.5, 26.5),
    'Івано-Франківська область':   (47.5, 49.5, 23.5, 25.5),
    'Закарпатська область':        (47.5, 49.5, 22.0, 24.5),
    'Чернівецька область':         (47.5, 49.0, 24.5, 27.0),
    'АР Крим':                     (44.0, 46.5, 32.5, 36.5),
}

# ── Oblast polygons (loaded lazily from GeoJSON) ─────────────────────────────

# Ukrainian -> English GeoJSON name mapping
OBLAST_NAME_MAP = {
    'Київська область': 'Kyiv Oblast',
    'Харківська область': 'Kharkiv Oblast',
    'Одеська область': 'Odessa Oblast',
    'Дніпропетровська область': 'Dnipropetrovsk Oblast',
    'Запорізька область': 'Zaporizhia Oblast',
    'Львівська область': 'Lviv Oblast',
    'Миколаївська область': 'Mykolaiv Oblast',
    'Херсонська область': 'Kherson Oblast',
    'Полтавська область': 'Poltava Oblast',
    'Сумська область': 'Sumy Oblast',
    'Чернігівська область': 'Chernihiv Oblast',
    'Вінницька область': 'Vinnytsia Oblast',
    'Житомирська область': 'Zhytomyr Oblast',
    'Черкаська область': 'Cherkasy Oblast',
    'Кіровоградська область': 'Kirovohrad Oblast',
    'Донецька область': 'Donetsk Oblast',
    'Луганська область': 'Luhansk Oblast',
    'Хмельницька область': 'Khmelnytskyi Oblast',
    'Рівненська область': 'Rivne Oblast',
    'Волинська область': 'Volyn Oblast',
    'Тернопільська область': 'Ternopil Oblast',
    'Івано-Франківська область': 'Ivano-Frankivsk Oblast',
    'Закарпатська область': 'Zakarpattia Oblast',
    'Чернівецька область': 'Chernivtsi Oblast',
}

_oblast_polygons: Optional[dict] = None
OBLASTS_GEOJSON_PATH = os.path.join(os.path.dirname(__file__), 'polygons', 'oblasts.geojson')


def _load_polygons() -> dict:
    """Load oblast polygons from GeoJSON. Returns {oblast_name: [polygon_rings]}."""
    global _oblast_polygons
    if _oblast_polygons is not None:
        return _oblast_polygons

    _oblast_polygons = {}

    if not os.path.exists(OBLASTS_GEOJSON_PATH):
        log.warning(f"Oblast polygons not found at {OBLASTS_GEOJSON_PATH}. Falling back to bbox only.")
        return _oblast_polygons

    try:
        with open(OBLASTS_GEOJSON_PATH, encoding='utf-8') as f:
            data = json.load(f)

        for feature in data.get('features', []):
            props = feature.get('properties', {})
            # Try various property name conventions
            name = (
                props.get('shapeName') or
                props.get('name') or
                props.get('NAME_1') or
                props.get('ADM1_UA') or
                ''
            )
            geom = feature.get('geometry', {})
            geom_type = geom.get('type', '')
            coords = geom.get('coordinates', [])

            if not name or not coords:
                continue

            # Normalize to list of polygon rings
            if geom_type == 'Polygon':
                rings = [coords[0]]  # outer ring
            elif geom_type == 'MultiPolygon':
                rings = [poly[0] for poly in coords]  # outer ring of each
            else:
                continue

            _oblast_polygons[name] = rings

        log.info(f"Loaded {len(_oblast_polygons)} oblast polygons")
    except Exception as e:
        log.error(f"Failed to load oblast polygons: {e}")

    return _oblast_polygons


# ── Point-in-polygon (ray casting) ──────────────────────────────────────────

def point_in_polygon(lat: float, lng: float, polygon: list) -> bool:
    """
    Ray-casting algorithm. `polygon` is a list of [lng, lat] pairs (GeoJSON convention).
    Returns True if point is inside.
    """
    n = len(polygon)
    inside = False
    j = n - 1

    for i in range(n):
        xi, yi = polygon[i]  # lng, lat (GeoJSON order)
        xj, yj = polygon[j]

        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i

    return inside


def point_in_oblast(lat: float, lng: float, oblast_name: str) -> bool:
    """Check if a point is inside a named oblast polygon."""
    polygons = _load_polygons()

    # Try Ukrainian → English mapping first
    english_name = OBLAST_NAME_MAP.get(oblast_name, '')
    rings = polygons.get(english_name)
    if not rings:
        # Direct match
        rings = polygons.get(oblast_name)
    if not rings:
        # Partial match fallback
        for key, val in polygons.items():
            if oblast_name.lower() in key.lower() or key.lower() in oblast_name.lower():
                rings = val
                break

    if not rings:
        return False

    return any(point_in_polygon(lat, lng, ring) for ring in rings)


# ── Validation functions ─────────────────────────────────────────────────────

def is_in_ukraine(lat: float, lng: float) -> bool:
    """Fast check: is point within Ukraine's bounding box?"""
    return (UKRAINE_LAT_MIN <= lat <= UKRAINE_LAT_MAX and
            UKRAINE_LNG_MIN <= lng <= UKRAINE_LNG_MAX)


def is_in_oblast_bbox(lat: float, lng: float, oblast: str) -> bool:
    """Check if point is within the bounding box of an oblast."""
    bbox = OBLAST_BBOX.get(oblast)
    if not bbox:
        return True  # no data = no penalty
    min_lat, max_lat, min_lng, max_lng = bbox
    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng


def find_oblast_for_coords(lat: float, lng: float) -> Optional[str]:
    """
    Find which oblast contains the given coordinates.
    Uses bbox first, then polygon for disambiguation when bboxes overlap.
    Returns oblast name or None if outside Ukraine / unknown.
    """
    if not is_in_ukraine(lat, lng):
        return None
    bbox_matches = []
    for oblast_name, bbox in OBLAST_BBOX.items():
        min_lat, max_lat, min_lng, max_lng = bbox
        if min_lat <= lat <= max_lat and min_lng <= lng <= max_lng:
            bbox_matches.append(oblast_name)
    if not bbox_matches:
        return None
    if len(bbox_matches) == 1:
        return bbox_matches[0]
    # Multiple bboxes overlap (e.g. Cherkasy/Kirovohrad border) — use polygon
    for oblast_name in bbox_matches:
        if point_in_oblast(lat, lng, oblast_name):
            return oblast_name
    return bbox_matches[0]  # fallback to first bbox match


# Розширення bbox (~50–55 км) — пограничні НП та похибка геокодера
OBLAST_CONTEXT_PAD_DEG = 0.5


def resolve_oblast_bbox_key(oblast_hint: Optional[str]) -> Optional[str]:
    """Повертає ключ з OBLAST_BBOX або None, якщо підказка не розпізнана."""
    if not oblast_hint or not oblast_hint.strip():
        return None
    h = oblast_hint.strip()
    if h in OBLAST_BBOX:
        return h
    hlow = h.lower().replace(' область', '').replace(' області', '').replace(' обл.', '').replace(' обл', '').strip()
    if not hlow:
        return None
    for key in OBLAST_BBOX:
        kl = key.lower().replace(' область', '').strip()
        if hlow == kl:
            return key
    for key in OBLAST_BBOX:
        kl = key.lower().replace(' область', '').strip()
        if kl.startswith(hlow):
            return key
    for key in OBLAST_BBOX:
        kl = key.lower().replace(' область', '').strip()
        if len(hlow) >= 6 and hlow.startswith(kl[: min(12, len(kl))]):
            return key
    return None


def point_in_expanded_oblast_bbox(
    lat: float,
    lng: float,
    oblast_key: str,
    pad_deg: float = OBLAST_CONTEXT_PAD_DEG,
) -> bool:
    """Точка в межах bbox області + поле для прикордоння."""
    bbox = OBLAST_BBOX.get(oblast_key)
    if not bbox:
        return True
    mn_lat, mx_lat, mn_lng, mx_lng = bbox
    return (
        mn_lat - pad_deg <= lat <= mx_lat + pad_deg
        and mn_lng - pad_deg <= lng <= mx_lng + pad_deg
    )


def oblast_bbox_center_latlng(oblast_key: str) -> Optional[tuple[float, float]]:
    bb = OBLAST_BBOX.get(oblast_key)
    if not bb:
        return None
    mn_lat, mx_lat, mn_lng, mx_lng = bb
    return ((mn_lat + mx_lat) / 2.0, (mn_lng + mx_lng) / 2.0)


def validate_candidate(
    candidate,  # LocationCandidate
    oblast_hint: Optional[str],
    channel_context: Optional[dict] = None,
) -> list[tuple[float, str]]:
    """
    Validate a candidate against rules. Returns list of (score_delta, reason).
    """
    penalties: list[tuple[float, str]] = []
    lat, lng = candidate.lat, candidate.lng
    src = (getattr(candidate, 'source', '') or '')

    # Синтетична точка в морі — не штрафувати «поза полігоном області»
    if 'synthetic_black_sea' in src:
        penalties.append((+4.0, "+4 Black Sea ingress (water)"))
        return penalties

    # 1. Ukraine boundary check
    if not is_in_ukraine(lat, lng):
        penalties.append((-10.0, "outside Ukraine boundary"))
        return penalties  # no point checking further

    # 2. Oblast polygon check
    if oblast_hint:
        if point_in_oblast(lat, lng, oblast_hint):
            penalties.append((+5.0, f"+5 point inside {oblast_hint} polygon"))
        elif is_in_oblast_bbox(lat, lng, oblast_hint):
            penalties.append((+3.0, f"+3 point inside {oblast_hint} bbox"))
        else:
            penalties.append((-5.0, f"-5 point outside expected {oblast_hint}"))

    # 3. If candidate has its own oblast, check consistency
    if candidate.oblast and oblast_hint and candidate.oblast != oblast_hint:
        if not is_in_oblast_bbox(lat, lng, oblast_hint):
            penalties.append((-3.0, f"-3 candidate oblast {candidate.oblast} != expected {oblast_hint}"))

    return penalties


# ── GADM HASC_1 codes (must match nextjs-app/public/ukraine_oblasts.geojson) ──
# Used by Next.js ingest (`resolved_oblast_hasc`, spatial correlator).
OBLAST_UKR_NAME_TO_HASC: dict[str, str] = {
    'Київська область': 'UA.KV',
    'Харківська область': 'UA.KK',
    'Одеська область': 'UA.OD',
    'Дніпропетровська область': 'UA.DP',
    'Запорізька область': 'UA.ZP',
    'Львівська область': 'UA.LV',
    'Миколаївська область': 'UA.MY',
    'Херсонська область': 'UA.KS',
    'Полтавська область': 'UA.PL',
    'Сумська область': 'UA.SM',
    'Чернігівська область': 'UA.CH',
    'Вінницька область': 'UA.VI',
    'Житомирська область': 'UA.ZT',
    'Черкаська область': 'UA.CK',
    'Кіровоградська область': 'UA.KH',
    'Донецька область': 'UA.DT',
    'Луганська область': 'UA.LH',
    'Хмельницька область': 'UA.KM',
    'Рівненська область': 'UA.RV',
    'Волинська область': 'UA.VO',
    'Тернопільська область': 'UA.TP',
    'Івано-Франківська область': 'UA.IF',
    'Закарпатська область': 'UA.ZK',
    'Чернівецька область': 'UA.CV',
    'АР Крим': 'UA.KR',
}

# Colloquial "-щина" / short forms when resolve_oblast_bbox_key misses (Telegram style).
_SPOKEN_OBLAST_TO_CANONICAL: dict[str, str] = {
    'харківщина': 'Харківська область',
    'київщина': 'Київська область',
    'чернігівщина': 'Чернігівська область',
    'одесщина': 'Одеська область',
    'одещина': 'Одеська область',
    'дніпропетровщина': 'Дніпропетровська область',
    'полтавщина': 'Полтавська область',
    'волинь': 'Волинська область',
    'буковина': 'Чернівецька область',
}


def oblast_uk_name_to_hasc(oblast_hint: Optional[str]) -> Optional[str]:
    """Map a Ukrainian oblast label (as in OBLAST_BBOX keys) to GADM HASC_1, e.g. UA.KK."""
    key = resolve_oblast_bbox_key(oblast_hint)
    if not key and oblast_hint:
        low = oblast_hint.strip().lower().replace('́', '').replace('̀', '')
        key = _SPOKEN_OBLAST_TO_CANONICAL.get(low)
    if not key:
        return None
    return OBLAST_UKR_NAME_TO_HASC.get(key)
