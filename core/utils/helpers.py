"""
Neptun Alarm - Utility Functions
Common helper functions used across the application
"""
import re
import math
import hashlib
from datetime import datetime
from typing import Optional, Tuple, List
import pytz

KYIV_TZ = pytz.timezone('Europe/Kyiv')


def get_kyiv_time() -> datetime:
    """Get current time in Kyiv timezone"""
    return datetime.now(KYIV_TZ)


def format_kyiv_time(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to Kyiv timezone string"""
    if dt.tzinfo is None:
        dt = KYIV_TZ.localize(dt)
    return dt.astimezone(KYIV_TZ).strftime(fmt)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers"""
    R = 6371  # Earth radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate bearing between two points in degrees"""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    
    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon)
    
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def bearing_to_direction(bearing: float) -> str:
    """Convert bearing to cardinal direction"""
    directions = ['Пн', 'ПнСх', 'Сх', 'ПдСх', 'Пд', 'ПдЗх', 'Зх', 'ПнЗх']
    index = round(bearing / 45) % 8
    return directions[index]


def direction_to_bearing(direction: str) -> Optional[float]:
    """Convert cardinal direction to bearing"""
    direction_map = {
        'пн': 0, 'північ': 0, 'північний': 0,
        'пнсх': 45, 'північносхідний': 45,
        'сх': 90, 'схід': 90, 'східний': 90,
        'пдсх': 135, 'південносхідний': 135,
        'пд': 180, 'південь': 180, 'південний': 180,
        'пдзх': 225, 'південнозахідний': 225,
        'зх': 270, 'захід': 270, 'західний': 270,
        'пнзх': 315, 'північнозахідний': 315,
    }
    return direction_map.get(direction.lower().replace('-', '').replace(' ', ''))


def generate_id(text: str, timestamp: datetime = None) -> str:
    """Generate unique ID from text and timestamp"""
    if timestamp is None:
        timestamp = get_kyiv_time()
    content = f"{text}_{timestamp.isoformat()}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def normalize_city_name(name: str) -> str:
    """Normalize Ukrainian city name for comparison"""
    if not name:
        return ""
    
    name = name.lower().strip()
    
    # Remove common suffixes
    suffixes = ['ська', 'ський', 'ське', 'ого', 'ому', 'ої', 'ій']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    
    return name


def extract_speed(text: str) -> Optional[int]:
    """Extract speed from text (km/h)"""
    patterns = [
        r'швидкість[:\s]*(\d+)',
        r'(\d+)\s*км/?год',
        r'(\d+)\s*km/?h',
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    return None


def extract_altitude(text: str) -> Optional[int]:
    """Extract altitude from text (meters)"""
    patterns = [
        r'висота[:\s]*(\d+)',
        r'(\d+)\s*м\b',
        r'(\d+)\s*метр',
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    return None


def extract_direction(text: str) -> Optional[str]:
    """Extract direction from text"""
    # Direction keywords
    direction_patterns = [
        r'курс[:\s]*(на\s+)?(\w+)',
        r'напрямок[:\s]*(на\s+)?(\w+)',
        r'рух[:\s]*(на\s+)?(\w+)',
        r'у\s+напрямку\s+(\w+)',
    ]
    
    for pattern in direction_patterns:
        match = re.search(pattern, text.lower())
        if match:
            direction = match.group(2) if match.lastindex >= 2 else match.group(1)
            if direction:
                bearing = direction_to_bearing(direction)
                if bearing is not None:
                    return bearing_to_direction(bearing)
    return None


def clean_html(text: str) -> str:
    """Remove HTML tags from text"""
    return re.sub(r'<[^>]+>', '', text)


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def is_valid_coordinates(lat: float, lng: float) -> bool:
    """Check if coordinates are valid for Ukraine"""
    # Ukraine bounding box (approximate)
    return 44.0 <= lat <= 52.5 and 22.0 <= lng <= 40.5


def parse_timestamp(text: str) -> Optional[datetime]:
    """Parse various timestamp formats"""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None
