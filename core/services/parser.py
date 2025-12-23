"""
Neptun Alarm - Message Parser
Parses Telegram messages to extract threat information
"""
import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass

from core.models.threat import ThreatMarker, ThreatType, Coordinates
from core.utils.helpers import (
    generate_id, extract_speed, extract_altitude, 
    extract_direction, get_kyiv_time
)
from core.services.geocoding import geocode
from core.data.regions import OBLAST_CENTERS, normalize_region_name

log = logging.getLogger(__name__)


# Threat type patterns
THREAT_PATTERNS = {
    ThreatType.DRONE: [
        r'бпла', r'шахед', r'shahed', r'дрон', r'герань',
        r'ударн\w+ бпла', r'розвід\w+ бпла', r'бла',
        r'mohajer', r'мохаджер', r'орлан', r'lancet', r'ланцет'
    ],
    ThreatType.MISSILE: [
        r'ракет[аи]', r'крилат[аі]', r'калібр', r'х-\d+',
        r'кр\b', r'томагавк', r'іскандер', r'точка-у',
        r'cruise', r'missile'
    ],
    ThreatType.BALLISTIC: [
        r'баліст', r'ballistic', r'кн-\d+', r'іскандер-м',
        r'fateh', r'shahab'
    ],
    ThreatType.AIRCRAFT: [
        r'міг-\d+', r'су-\d+', r'ту-\d+', r'іл-\d+',
        r'літак', r'бомбардувальник', r'винищувач',
        r'стратегічн\w+ авіац'
    ],
}

# Location extraction patterns
LOCATION_PATTERNS = [
    # "в напрямку Києва"
    r'(?:в\s+)?напрямку?\s+([А-ЯІЇЄҐа-яіїєґ\']+(?:[\s-][А-ЯІЇЄҐа-яіїєґ\']+)?)',
    # "над Миколаївом"
    r'над\s+([А-ЯІЇЄҐа-яіїєґ\']+(?:[\s-][А-ЯІЇЄҐа-яіїєґ\']+)?)',
    # "в районі Одеси"
    r'(?:в\s+)?район[іуа]\s+([А-ЯІЇЄҐа-яіїєґ\']+(?:[\s-][А-ЯІЇЄҐа-яіїєґ\']+)?)',
    # "на Харківщині"
    r'на\s+([А-ЯІЇЄҐа-яіїєґ\']+щин[іуа])',
    # "м. Київ" or "м.Київ"
    r'м\.?\s*([А-ЯІЇЄҐа-яіїєґ\']+)',
    # "Дніпропетровська область"
    r'([А-ЯІЇЄҐа-яіїєґ\']+)\s+(?:област[іь]|обл\.)',
    # "Київ:"
    r'^([А-ЯІЇЄҐа-яіїєґ\']+)\s*:',
    # City at start of sentence with threat info
    r'^([А-ЯІЇЄҐа-яіїєґ\']{3,})\s*[-–—]\s*(?:бпла|ракет|загроз)',
]

# Direction patterns
DIRECTION_PATTERNS = [
    r'курс[:\s]+(?:на\s+)?([а-яіїєґ]+)',
    r'напрям(?:ок)?[:\s]+(?:на\s+)?([а-яіїєґ]+)',
    r'рух[:\s]+(?:на\s+)?([а-яіїєґ]+)',
    r'летить\s+(?:на\s+)?([а-яіїєґ]+)',
    r'прямує\s+(?:на\s+|до\s+)?([а-яіїєґ]+)',
]


def detect_threat_type(text: str) -> ThreatType:
    """Detect threat type from message text"""
    text_lower = text.lower()
    
    # Check patterns in order of specificity
    for threat_type, patterns in THREAT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return threat_type
    
    return ThreatType.UNKNOWN


def extract_locations(text: str) -> List[str]:
    """Extract location mentions from text"""
    locations = []
    
    for pattern in LOCATION_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            location = match.strip()
            # Filter out common false positives
            if len(location) >= 3 and location.lower() not in ['для', 'від', 'або', 'при', 'що']:
                locations.append(location)
    
    return list(set(locations))  # Remove duplicates


def extract_course_direction(text: str) -> Optional[str]:
    """Extract course/direction from text"""
    text_lower = text.lower()
    
    for pattern in DIRECTION_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            direction = match.group(1)
            # Map to cardinal direction
            direction_map = {
                'північ': 'Пн', 'північний': 'Пн',
                'південь': 'Пд', 'південний': 'Пд',
                'схід': 'Сх', 'східний': 'Сх',
                'захід': 'Зх', 'західний': 'Зх',
                'північносхідний': 'ПнСх', 'північно-східний': 'ПнСх',
                'північнозахідний': 'ПнЗх', 'північно-західний': 'ПнЗх',
                'південносхідний': 'ПдСх', 'південно-східний': 'ПдСх',
                'південнозахідний': 'ПдЗх', 'південно-західний': 'ПдЗх',
            }
            return direction_map.get(direction, direction[:2].capitalize())
    
    return None


def extract_count(text: str) -> int:
    """Extract count of threats from text"""
    # "5 БПЛА", "група з 3 дронів"
    patterns = [
        r'(\d+)\s*(?:бпла|дрон|шахед|ракет)',
        r'група\s+(?:з\s+)?(\d+)',
        r'до\s+(\d+)\s+(?:бпла|дрон)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    
    return 1


def is_alert_cancellation(text: str) -> bool:
    """Check if message is about alert cancellation"""
    cancellation_patterns = [
        r'відбій',
        r'знято\s+(?:тривогу|загрозу)',
        r'загроза\s+минула',
        r'чисте\s+небо',
        r'all\s+clear',
    ]
    
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in cancellation_patterns)


def parse_message(
    text: str, 
    message_id: str = None,
    channel: str = "",
    timestamp: datetime = None
) -> List[ThreatMarker]:
    """
    Parse a Telegram message and extract threat markers
    
    Args:
        text: Message text
        message_id: Original message ID
        channel: Source channel
        timestamp: Message timestamp
        
    Returns:
        List of ThreatMarker objects
    """
    if not text or len(text) < 10:
        return []
    
    # Skip cancellation messages
    if is_alert_cancellation(text):
        return []
    
    markers = []
    timestamp = timestamp or get_kyiv_time()
    
    # Detect threat type
    threat_type = detect_threat_type(text)
    if threat_type == ThreatType.UNKNOWN:
        return []  # Skip if no threat detected
    
    # Extract locations
    locations = extract_locations(text)
    if not locations:
        return []
    
    # Extract additional info
    direction = extract_course_direction(text)
    speed = extract_speed(text)
    altitude = extract_altitude(text)
    count = extract_count(text)
    
    # Create markers for each location
    for location in locations:
        # Try to geocode
        coords = None
        
        # First check oblast centers
        location_lower = location.lower()
        if location_lower in OBLAST_CENTERS:
            lat, lng = OBLAST_CENTERS[location_lower]
            coords = Coordinates(lat=lat, lng=lng)
        else:
            # Try geocoding
            result = geocode(location)
            if result:
                coords = Coordinates(lat=result[0], lng=result[1])
        
        # Create marker
        marker_id = message_id or generate_id(f"{location}_{threat_type.value}", timestamp)
        
        marker = ThreatMarker(
            id=marker_id,
            threat_type=threat_type,
            location=location,
            coords=coords,
            direction=direction,
            speed=speed,
            altitude=altitude,
            source_channel=channel,
            timestamp=timestamp,
            raw_text=text[:500]  # Truncate long texts
        )
        
        markers.append(marker)
    
    return markers


def parse_multiline_message(text: str, channel: str = "") -> List[ThreatMarker]:
    """
    Parse message with multiple threats (one per line)
    Common format: "Миколаїв - БПЛА на північ"
    """
    markers = []
    
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        
        # Skip header lines
        if line.startswith('#') or line.startswith('⚠️'):
            continue
            
        line_markers = parse_message(line, channel=channel)
        markers.extend(line_markers)
    
    return markers
