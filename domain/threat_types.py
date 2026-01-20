"""
Threat type enumeration.

Централізоване визначення типів загроз.
Всі regex patterns, пріоритети та іконки в одному місці.
"""
from enum import Enum
from typing import Optional, List, Tuple
import re


class ThreatType(Enum):
    """
    Типи загроз з пріоритетами для відображення.
    Чим менше число - тим вищий пріоритет.
    """
    BALLISTIC = ("ballistic", 1, "icon_balistic.svg")
    MISSILE = ("missile", 2, "icon_missile.svg")
    SHAHED = ("shahed", 3, "icon_drone.svg")
    DRONE = ("drone", 4, "icon_drone.svg")
    AVIATION = ("aviation", 5, "icon_aviation.svg")
    HELICOPTER = ("helicopter", 6, "icon_helicopter.svg")
    RECON = ("recon", 7, "icon_recon.svg")
    UNKNOWN = ("unknown", 99, "default.png")
    
    def __init__(self, type_id: str, priority: int, icon: str):
        self.type_id = type_id
        self.priority = priority
        self.icon = icon


# Compiled regex patterns for threat detection
# Order matters - first match wins
THREAT_PATTERNS: List[Tuple[ThreatType, re.Pattern]] = [
    # Ballistic - highest priority
    (ThreatType.BALLISTIC, re.compile(
        r'балістик|іскандер|точка-у|kn-23|kh-47|kinzhal|кинжал|балістичн',
        re.IGNORECASE
    )),
    
    # Missiles
    (ThreatType.MISSILE, re.compile(
        r'калібр|крилат|х-101|х-555|х-59|х-22|х-32|ракет[аи]|кр\s|missile',
        re.IGNORECASE
    )),
    
    # Shahed/Geran (specific drone type)
    (ThreatType.SHAHED, re.compile(
        r'shahed|шахед|герань|geran|моп[её]д|moped',
        re.IGNORECASE
    )),
    
    # Generic UAV/Drone
    (ThreatType.DRONE, re.compile(
        r'бпла|дрон|uav|ударн.*безпілот|безпілотник|орлан|ланцет|lancet',
        re.IGNORECASE
    )),
    
    # Aviation
    (ThreatType.AVIATION, re.compile(
        r'авіа|миг-31|су-34|су-35|ту-95|ту-22|ту-160|a-50|mig|su-3[45]|стратег',
        re.IGNORECASE
    )),
    
    # Helicopter
    (ThreatType.HELICOPTER, re.compile(
        r'вертол|гелікоптер|ми-8|ми-24|ка-52|helicopter',
        re.IGNORECASE
    )),
    
    # Reconnaissance
    (ThreatType.RECON, re.compile(
        r'розвід|supercam|orlan|zala|reconnaissance',
        re.IGNORECASE
    )),
]


def detect_threat_type(text: str) -> ThreatType:
    """
    Визначає тип загрози з тексту повідомлення.
    
    Args:
        text: Текст повідомлення
        
    Returns:
        ThreatType enum value
        
    Example:
        >>> detect_threat_type("Шахеди в напрямку Києва")
        ThreatType.SHAHED
    """
    if not text:
        return ThreatType.UNKNOWN
    
    for threat_type, pattern in THREAT_PATTERNS:
        if pattern.search(text):
            return threat_type
    
    return ThreatType.UNKNOWN


def get_threat_icon(threat_type: ThreatType) -> str:
    """Get icon filename for threat type."""
    return threat_type.icon


def get_threat_priority(threat_type: ThreatType) -> int:
    """Get display priority (lower = more important)."""
    return threat_type.priority


# Direction patterns for trajectory extraction
DIRECTION_PATTERNS = {
    'північ': 0,
    'північний схід': 45,
    'схід': 90,
    'південний схід': 135,
    'південь': 180,
    'південний захід': 225,
    'захід': 270,
    'північний захід': 315,
}

# Course/direction indicators in text
COURSE_INDICATORS = re.compile(
    r'курс(?:ом)?\s+(?:на\s+)?|напрям(?:ок|ку)?\s+(?:на\s+)?|рухається\s+(?:на|в|до)\s+',
    re.IGNORECASE
)
