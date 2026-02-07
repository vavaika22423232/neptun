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
    'Одеська область':             (45.0, 48.5, 28.5, 34.0),
    'Дніпропетровська область':    (47.5, 49.5, 33.5, 36.5),
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
