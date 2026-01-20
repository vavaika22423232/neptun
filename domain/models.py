"""
Domain models - pure data structures.

Всі моделі immutable де можливо (frozen=True).
Без бізнес-логіки, тільки дані та валідація.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from enum import Enum

from .threat_types import ThreatType


@dataclass(frozen=True)
class Coordinates:
    """
    Immutable координати.
    
    frozen=True гарантує що координати не змінюватимуться після створення.
    """
    lat: float
    lon: float
    
    def __post_init__(self):
        if not (-90 <= self.lat <= 90):
            raise ValueError(f"Invalid latitude: {self.lat}")
        if not (-180 <= self.lon <= 180):
            raise ValueError(f"Invalid longitude: {self.lon}")
    
    def as_tuple(self) -> Tuple[float, float]:
        return (self.lat, self.lon)
    
    def rounded(self, precision: int = 4) -> 'Coordinates':
        return Coordinates(
            round(self.lat, precision),
            round(self.lon, precision)
        )


@dataclass(frozen=True)
class Trajectory:
    """
    Траєкторія руху загрози.
    
    start: початкова точка
    end: кінцева точка (може бути прогнозована)
    bearing: напрямок в градусах (0=північ)
    predicted: чи це прогноз
    """
    start: Coordinates
    end: Coordinates
    bearing: float
    predicted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'start': [self.start.lat, self.start.lon],
            'end': [self.end.lat, self.end.lon],
            'bearing': self.bearing,
            'predicted': self.predicted,
        }


class TrackStatus(Enum):
    """Статус трека/загрози."""
    ACTIVE = "active"           # Активна загроза
    PASSED = "passed"           # Пройшла через регіон
    DESTROYED = "destroyed"     # Збита
    LOST = "lost"               # Втрачена з радарів
    EXPIRED = "expired"         # Вичерпано TTL


@dataclass
class Track:
    """
    Основна сутність - трек загрози на карті.
    
    Mutable тому що оновлюється по мірі надходження нових даних.
    """
    id: str
    threat_type: ThreatType
    coordinates: Coordinates
    place: str
    text: str
    timestamp: datetime
    source_channel: str
    
    # Optional fields
    trajectory: Optional[Trajectory] = None
    course_direction: Optional[str] = None
    count: int = 1
    status: TrackStatus = TrackStatus.ACTIVE
    
    # Metadata
    manual: bool = False
    pending_geo: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON response."""
        result = {
            'id': self.id,
            'lat': self.coordinates.lat,
            'lng': self.coordinates.lon,
            'place': self.place,
            'text': self.text,
            'date': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'channel': self.source_channel,
            'threat_type': self.threat_type.type_id,
            'marker_icon': self.threat_type.icon,
            'count': self.count,
            'manual': self.manual,
        }
        
        if self.trajectory:
            result['trajectory'] = self.trajectory.to_dict()
        
        if self.course_direction:
            result['course_direction'] = self.course_direction
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        """Deserialize from stored dict."""
        coords = Coordinates(
            float(data.get('lat', 0)),
            float(data.get('lng', 0))
        )
        
        threat_type_str = data.get('threat_type', 'unknown')
        try:
            threat_type = ThreatType[threat_type_str.upper()]
        except (KeyError, AttributeError):
            threat_type = ThreatType.UNKNOWN
        
        timestamp = datetime.strptime(
            data.get('date', ''),
            '%Y-%m-%d %H:%M:%S'
        ) if data.get('date') else datetime.now()
        
        return cls(
            id=str(data.get('id', '')),
            threat_type=threat_type,
            coordinates=coords,
            place=data.get('place', ''),
            text=data.get('text', ''),
            timestamp=timestamp,
            source_channel=data.get('channel', ''),
            count=data.get('count', 1),
            manual=data.get('manual', False),
            pending_geo=data.get('pending_geo', False),
        )


@dataclass(frozen=True)
class RawMessage:
    """
    Сире повідомлення з Telegram до обробки.
    
    Immutable - створюється один раз при отриманні.
    """
    id: str
    text: str
    timestamp: datetime
    channel: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'text': self.text,
            'date': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'channel': self.channel,
            'pending_geo': True,
        }


@dataclass(frozen=True)
class AlarmState:
    """
    Стан тривоги для регіону.
    
    Immutable - при зміні створюється новий об'єкт.
    """
    region_id: str
    region_name: str
    is_active: bool
    started_at: Optional[datetime]
    last_update: datetime
    alarm_type: Optional[str] = None  # 'air', 'artillery', etc.
    
    def with_update(self, is_active: bool) -> 'AlarmState':
        """Create new state with updated active status."""
        return AlarmState(
            region_id=self.region_id,
            region_name=self.region_name,
            is_active=is_active,
            started_at=self.started_at if is_active else None,
            last_update=datetime.now(),
            alarm_type=self.alarm_type if is_active else None,
        )


@dataclass(frozen=True)
class BallisticThreat:
    """
    Стан балістичної загрози.
    
    Замість 3 окремих глобальних змінних - один immutable об'єкт.
    """
    is_active: bool
    region: Optional[str]
    timestamp: Optional[datetime]
    
    @classmethod
    def inactive(cls) -> 'BallisticThreat':
        return cls(is_active=False, region=None, timestamp=None)
    
    @classmethod
    def active(cls, region: Optional[str] = None) -> 'BallisticThreat':
        return cls(is_active=True, region=region, timestamp=datetime.now())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'active': self.is_active,
            'region': self.region,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class ChatMessage:
    """Повідомлення в чаті."""
    id: str
    message_type: str  # 'threat_start', 'threat_end', 'system', 'user'
    text: str
    timestamp: datetime
    region: Optional[str] = None
    threat_type: Optional[str] = None
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.message_type,
            'text': self.text,
            'timestamp': self.timestamp.isoformat(),
            'region': self.region,
            'threat_type': self.threat_type,
            'user_id': self.user_id,
        }


@dataclass
class GeocodingResult:
    """Результат геокодування."""
    query: str
    coordinates: Optional[Coordinates]
    place_name: str
    source: str  # 'local', 'nominatim', 'photon', 'ai'
    confidence: float = 1.0
    region: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.coordinates is not None


@dataclass(frozen=True)
class BackfillProgress:
    """Прогрес backfill операції."""
    in_progress: bool
    started_at: Optional[datetime]
    channels_done: int
    channels_total: int
    messages_processed: int
    current_channel: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'in_progress': self.in_progress,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'channels_done': self.channels_done,
            'channels_total': self.channels_total,
            'messages_processed': self.messages_processed,
            'current_channel': self.current_channel,
        }


# Alias for Track - used in processing pipeline
Marker = Track
