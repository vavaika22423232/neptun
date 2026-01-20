"""
Pure geographic functions.

Математичні функції для роботи з координатами.
Без зовнішніх залежностей, повністю детерміновані.
"""
import math
from typing import Optional

# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0


def haversine(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """
    Calculate great-circle distance between two points.

    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)

    Returns:
        Distance in kilometers

    Example:
        >>> haversine(50.4501, 30.5234, 49.8397, 24.0297)
        469.45  # Kyiv to Lviv
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) *
        math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def calculate_bearing(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> float:
    """
    Calculate initial bearing from point 1 to point 2.

    Args:
        lat1, lon1: Start point coordinates (degrees)
        lat2, lon2: End point coordinates (degrees)

    Returns:
        Bearing in degrees (0-360, where 0=North, 90=East)

    Example:
        >>> calculate_bearing(50.45, 30.52, 49.84, 24.03)
        251.3  # Kyiv to Lviv is ~West-Southwest
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = (
        math.cos(lat1_rad) * math.sin(lat2_rad) -
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
    )

    bearing = math.atan2(x, y)
    bearing_deg = math.degrees(bearing)

    # Normalize to 0-360
    return (bearing_deg + 360) % 360


def destination_point(
    lat: float, lon: float,
    bearing: float, distance_km: float
) -> tuple[float, float]:
    """
    Calculate destination point given start, bearing and distance.

    Args:
        lat, lon: Start point (degrees)
        bearing: Direction in degrees (0=North)
        distance_km: Distance to travel in kilometers

    Returns:
        Tuple of (latitude, longitude) of destination

    Example:
        >>> destination_point(50.45, 30.52, 180, 100)
        (49.55, 30.52)  # 100km South of Kyiv
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing)

    angular_distance = distance_km / EARTH_RADIUS_KM

    lat2 = math.asin(
        math.sin(lat_rad) * math.cos(angular_distance) +
        math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
    )

    lon2 = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(lat2)
    )

    return (math.degrees(lat2), math.degrees(lon2))


def is_within_ukraine(lat: float, lon: float) -> bool:
    """
    Check if coordinates are within Ukraine's approximate bounding box.

    Args:
        lat, lon: Coordinates to check

    Returns:
        True if point is within Ukraine bounds
    """
    # Ukraine bounding box (approximate)
    MIN_LAT, MAX_LAT = 44.0, 52.5
    MIN_LON, MAX_LON = 22.0, 40.5

    return MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON


def bearing_to_direction(bearing: float) -> str:
    """
    Convert bearing angle to compass direction name (Ukrainian).

    Args:
        bearing: Angle in degrees (0-360)

    Returns:
        Ukrainian direction name

    Example:
        >>> bearing_to_direction(45)
        "північний схід"
    """
    directions = [
        (0, "північ"),
        (45, "північний схід"),
        (90, "схід"),
        (135, "південний схід"),
        (180, "південь"),
        (225, "південний захід"),
        (270, "захід"),
        (315, "північний захід"),
        (360, "північ"),
    ]

    # Normalize bearing to 0-360
    bearing = bearing % 360

    # Find closest direction
    min_diff = 360
    result = "невідомо"

    for angle, name in directions:
        diff = abs(bearing - angle)
        if diff < min_diff:
            min_diff = diff
            result = name

    return result


def midpoint(
    lat1: float, lon1: float,
    lat2: float, lon2: float
) -> tuple[float, float]:
    """
    Calculate midpoint between two coordinates.

    Simple average, not great-circle midpoint (sufficient for short distances).
    """
    return ((lat1 + lat2) / 2, (lon1 + lon2) / 2)


def normalize_coordinates(
    lat: Optional[float], lon: Optional[float],
    precision: int = 4
) -> Optional[tuple[float, float]]:
    """
    Normalize and validate coordinates.

    Args:
        lat, lon: Raw coordinates
        precision: Decimal places to round to

    Returns:
        Tuple of (lat, lon) or None if invalid
    """
    if lat is None or lon is None:
        return None

    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return None

    if not is_within_ukraine(lat, lon):
        return None

    return (round(lat, precision), round(lon, precision))
