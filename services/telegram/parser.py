"""
Telegram message parser.

Парсить повідомлення з Telegram каналів на структуровані дані
про загрози, курси руху, локації тощо.
"""
import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from services.telegram.patterns import (
    BALLISTIC_PATTERNS,
    CRUISE_MISSILE_PATTERNS,
    ROCKET_PATTERNS,
    DRONE_PATTERNS,
    KAB_PATTERNS,
    EXPLOSION_PATTERNS,
    ALARM_PATTERNS,
    ALL_CLEAR_PATTERNS,
    MIG_PATTERNS,
    COURSE_PATTERNS,
    OBLAST_PATTERN,
    DISTRICT_PATTERN,
    CITY_PATTERNS,
    COUNT_PATTERNS,
    DIRECTION_MAP,
    NOISE_WORDS,
    EMOJI_PATTERN,
)


@dataclass
class CourseInfo:
    """Extracted course/direction information."""
    source: Optional[str] = None
    target: Optional[str] = None
    direction: Optional[str] = None  # Cardinal direction (N, NE, etc.)
    direction_ukr: Optional[str] = None  # Ukrainian name
    course_type: str = 'unknown'  # full_course, target_only, directional


@dataclass
class ThreatInfo:
    """Detected threat type information."""
    threat_type: str  # ballistic, cruise_missile, rocket, drone, kab, explosion, alarm, all_clear, mig
    confidence: float  # 0.0 - 1.0
    emoji: str = '⚠️'
    display_name: str = ''


@dataclass
class LocationInfo:
    """Extracted location information."""
    oblast: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    raw_text: Optional[str] = None


@dataclass 
class ParsedMessage:
    """Fully parsed Telegram message."""
    raw_text: str
    timestamp: datetime
    channel: Optional[str] = None
    message_id: Optional[int] = None
    
    # Detected threat
    threat: Optional[ThreatInfo] = None
    
    # Course information
    course: Optional[CourseInfo] = None
    
    # Location
    location: Optional[LocationInfo] = None
    
    # Additional info
    count: int = 1  # Number of objects (e.g., "3х БПЛА")
    is_all_clear: bool = False  # Відбій тривоги
    
    # For raw storage
    needs_geocoding: bool = True
    geocoded: bool = False
    coordinates: Optional[Tuple[float, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            'raw_text': self.raw_text,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'channel': self.channel,
            'message_id': self.message_id,
            'count': self.count,
            'is_all_clear': self.is_all_clear,
            'needs_geocoding': self.needs_geocoding,
            'geocoded': self.geocoded,
        }
        
        if self.threat:
            result['threat_type'] = self.threat.threat_type
            result['threat_confidence'] = self.threat.confidence
            result['emoji'] = self.threat.emoji
        
        if self.course:
            result['source'] = self.course.source
            result['target'] = self.course.target
            result['direction'] = self.course.direction
            result['course_type'] = self.course.course_type
        
        if self.location:
            result['oblast'] = self.location.oblast
            result['district'] = self.location.district
            result['city'] = self.location.city
        
        if self.coordinates:
            result['lat'] = self.coordinates[0]
            result['lng'] = self.coordinates[1]
        
        return result


class MessageParser:
    """
    Parser for Telegram messages about threats.
    
    Thread-safe, stateless parser that extracts structured data from
    raw message text.
    """
    
    # Threat type configuration: (patterns, confidence, emoji, display_name)
    THREAT_TYPES = {
        'ballistic': (BALLISTIC_PATTERNS, 1.0, '🎯', 'Балістика'),
        'cruise_missile': (CRUISE_MISSILE_PATTERNS, 0.95, '🚀', 'Крилата ракета'),
        'rocket': (ROCKET_PATTERNS, 0.9, '🚀', 'Ракета'),
        'drone': (DRONE_PATTERNS, 0.85, '🛩️', 'БПЛА'),
        'kab': (KAB_PATTERNS, 0.9, '💣', 'КАБ'),
        'explosion': (EXPLOSION_PATTERNS, 0.95, '💥', 'Вибух'),
        'alarm': (ALARM_PATTERNS, 0.8, '🚨', 'Тривога'),
        'all_clear': (ALL_CLEAR_PATTERNS, 0.95, '✅', 'Відбій'),
        'mig': (MIG_PATTERNS, 0.9, '✈️', 'МіГ-31'),
    }
    
    # Priority order for threat detection
    THREAT_PRIORITY = [
        'ballistic',      # Highest priority - immediate danger
        'all_clear',      # Check before other threats
        'cruise_missile',
        'kab',
        'mig',
        'rocket',
        'drone',
        'explosion',
        'alarm',
    ]
    
    def __init__(self):
        """Initialize parser."""
        pass  # Stateless
    
    def parse(
        self,
        text: str,
        timestamp: Optional[datetime] = None,
        channel: Optional[str] = None,
        message_id: Optional[int] = None,
    ) -> ParsedMessage:
        """
        Parse a Telegram message.
        
        Args:
            text: Raw message text
            timestamp: Message timestamp
            channel: Source channel name
            message_id: Telegram message ID
            
        Returns:
            ParsedMessage with extracted information
        """
        timestamp = timestamp or datetime.utcnow()
        
        # Create base message
        parsed = ParsedMessage(
            raw_text=text,
            timestamp=timestamp,
            channel=channel,
            message_id=message_id,
        )
        
        # Clean text for analysis
        text_clean = self._clean_text(text)
        text_lower = text_clean.lower()
        
        # Detect threat type
        parsed.threat = self._detect_threat(text_lower)
        
        # Check if all clear
        parsed.is_all_clear = (
            parsed.threat is not None and 
            parsed.threat.threat_type == 'all_clear'
        )
        
        # Extract course information
        parsed.course = self._extract_course(text_lower)
        
        # Extract location
        parsed.location = self._extract_location(text_clean)
        
        # Extract count
        parsed.count = self._extract_count(text_lower)
        
        # Determine if needs geocoding
        parsed.needs_geocoding = self._needs_geocoding(parsed)
        
        return parsed
    
    def parse_batch(
        self,
        messages: List[Dict[str, Any]],
    ) -> List[ParsedMessage]:
        """
        Parse a batch of messages.
        
        Args:
            messages: List of dicts with 'text', 'date', 'channel', 'id' keys
            
        Returns:
            List of ParsedMessage objects
        """
        results = []
        for msg in messages:
            text = msg.get('text') or msg.get('message') or ''
            if not text:
                continue
            
            # Parse timestamp
            ts = msg.get('date') or msg.get('timestamp')
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                except ValueError:
                    ts = datetime.utcnow()
            elif not isinstance(ts, datetime):
                ts = datetime.utcnow()
            
            parsed = self.parse(
                text=text,
                timestamp=ts,
                channel=msg.get('channel'),
                message_id=msg.get('id') or msg.get('message_id'),
            )
            results.append(parsed)
        
        return results
    
    def _clean_text(self, text: str) -> str:
        """Remove emojis and extra whitespace."""
        # Remove emojis
        text = EMOJI_PATTERN.sub(' ', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text.strip()
    
    def _detect_threat(self, text_lower: str) -> Optional[ThreatInfo]:
        """
        Detect threat type from text.
        
        Returns highest-priority matching threat type.
        """
        for threat_type in self.THREAT_PRIORITY:
            patterns, confidence, emoji, display_name = self.THREAT_TYPES[threat_type]
            
            for pattern in patterns:
                if pattern.search(text_lower):
                    return ThreatInfo(
                        threat_type=threat_type,
                        confidence=confidence,
                        emoji=emoji,
                        display_name=display_name,
                    )
        
        return None
    
    def _extract_course(self, text_lower: str) -> Optional[CourseInfo]:
        """Extract course/direction information from text."""
        
        # Try structured course patterns first
        for pattern_name, pattern, (src_idx, tgt_idx) in COURSE_PATTERNS:
            matches = pattern.findall(text_lower)
            if matches:
                match = matches[0]
                
                if isinstance(match, tuple):
                    if src_idx >= 0:
                        source = self._clean_location(match[src_idx])
                    else:
                        source = None
                    
                    if tgt_idx >= 0 and tgt_idx < len(match):
                        target = self._clean_location(match[tgt_idx])
                    else:
                        target = None
                else:
                    source = None
                    target = self._clean_location(match)
                
                course_type = 'full_course' if source and target else (
                    'target_only' if target else 'unknown'
                )
                
                return CourseInfo(
                    source=source,
                    target=target,
                    course_type=course_type,
                )
        
        # Try directional patterns
        for direction_ukr, direction_eng in DIRECTION_MAP.items():
            if direction_ukr in text_lower:
                return CourseInfo(
                    direction=direction_eng,
                    direction_ukr=direction_ukr,
                    course_type='directional',
                )
        
        return None
    
    def _extract_location(self, text: str) -> Optional[LocationInfo]:
        """Extract location (oblast, district, city) from text."""
        location = LocationInfo()
        
        # Extract oblast
        oblast_match = OBLAST_PATTERN.search(text)
        if oblast_match:
            location.oblast = oblast_match.group(1).strip()
        
        # Extract district
        district_match = DISTRICT_PATTERN.search(text)
        if district_match:
            location.district = district_match.group(1).strip()
        
        # Extract city
        for pattern in CITY_PATTERNS:
            city_match = pattern.search(text)
            if city_match:
                city = city_match.group(1).strip()
                # Filter out noise words and short matches
                if city.lower() not in NOISE_WORDS and len(city) > 2:
                    location.city = city
                    break
        
        # Return None if nothing found
        if not any([location.oblast, location.district, location.city]):
            return None
        
        location.raw_text = text[:200]  # Keep original for reference
        return location
    
    def _extract_count(self, text_lower: str) -> int:
        """Extract count of objects (e.g., "3х БПЛА")."""
        for pattern in COUNT_PATTERNS:
            match = pattern.search(text_lower)
            if match:
                try:
                    count = int(match.group(1))
                    if 1 <= count <= 100:  # Sanity check
                        return count
                except (ValueError, IndexError):
                    pass
        return 1
    
    def _clean_location(self, text: str) -> Optional[str]:
        """Clean location name from noise words."""
        if not text:
            return None
        
        text = text.strip()
        words = text.split()
        
        # Filter noise words
        clean_words = [
            w for w in words 
            if w.lower() not in NOISE_WORDS
        ]
        
        if not clean_words:
            return None
        
        result = ' '.join(clean_words).strip()
        
        # Capitalize first letter
        if result:
            result = result[0].upper() + result[1:]
        
        return result if len(result) > 1 else None
    
    def _needs_geocoding(self, parsed: ParsedMessage) -> bool:
        """Determine if message needs geocoding."""
        # Don't geocode all-clear messages
        if parsed.is_all_clear:
            return False
        
        # Need geocoding if we have location or course info
        if parsed.location:
            return True
        
        if parsed.course and (parsed.course.source or parsed.course.target):
            return True
        
        return False
    
    def is_relevant_message(self, text: str) -> bool:
        """
        Quick check if message is relevant (contains threat info).
        
        Use this for filtering before full parsing.
        """
        text_lower = text.lower()
        
        # Quick keyword check
        keywords = [
            'бпла', 'дрон', 'шахед', 'ракет', 'балістик', 
            'каб', 'вибух', 'тривог', 'відбій', 'загроз',
            'крилат', 'міг', 'aviabomb', 'shahed',
        ]
        
        return any(kw in text_lower for kw in keywords)
