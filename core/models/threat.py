"""
Neptun Alarm - Data Models
Pydantic models for type safety and validation
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ThreatType(Enum):
    """Types of threats tracked by the system"""
    DRONE = "drone"           # БпЛА, Шахед
    MISSILE = "missile"       # Ракета, Калібр
    AIRCRAFT = "aircraft"     # МіГ, Су, літак
    BALLISTIC = "ballistic"   # Балістика
    UNKNOWN = "unknown"


class AlarmLevel(Enum):
    """Alarm levels"""
    OBLAST = "oblast"
    RAION = "raion"
    HROMADA = "hromada"


@dataclass
class Coordinates:
    """Geographic coordinates"""
    lat: float
    lng: float
    
    def to_dict(self) -> Dict:
        return {"lat": self.lat, "lng": self.lng}
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Coordinates":
        return cls(lat=data["lat"], lng=data["lng"])


@dataclass
class ThreatMarker:
    """A threat marker on the map"""
    id: str
    threat_type: ThreatType
    location: str
    coords: Optional[Coordinates] = None
    direction: Optional[str] = None
    speed: Optional[int] = None
    altitude: Optional[int] = None
    source_channel: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    raw_text: str = ""
    is_hidden: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.threat_type.value,
            "location": self.location,
            "lat": self.coords.lat if self.coords else None,
            "lng": self.coords.lng if self.coords else None,
            "direction": self.direction,
            "speed": self.speed,
            "altitude": self.altitude,
            "channel": self.source_channel,
            "timestamp": self.timestamp.isoformat(),
            "text": self.raw_text,
            "hidden": self.is_hidden
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ThreatMarker":
        coords = None
        if data.get("lat") and data.get("lng"):
            coords = Coordinates(lat=data["lat"], lng=data["lng"])
        
        return cls(
            id=data.get("id", ""),
            threat_type=ThreatType(data.get("type", "unknown")),
            location=data.get("location", ""),
            coords=coords,
            direction=data.get("direction"),
            speed=data.get("speed"),
            altitude=data.get("altitude"),
            source_channel=data.get("channel", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            raw_text=data.get("text", ""),
            is_hidden=data.get("hidden", False)
        )


@dataclass
class Alarm:
    """An active alarm in a region"""
    level: AlarmLevel
    name: str  # Oblast/raion name
    since: datetime
    last_update: datetime
    
    def to_dict(self) -> Dict:
        return {
            "level": self.level.value,
            "name": self.name,
            "since": self.since.timestamp(),
            "last": self.last_update.timestamp()
        }


@dataclass
class Device:
    """A registered device for push notifications"""
    device_id: str
    fcm_token: str
    platform: str  # android, ios, web
    regions: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "device_id": self.device_id,
            "fcm_token": self.fcm_token,
            "platform": self.platform,
            "regions": self.regions,
            "registered_at": self.registered_at.isoformat(),
            "last_seen": self.last_seen.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Device":
        return cls(
            device_id=data["device_id"],
            fcm_token=data["fcm_token"],
            platform=data.get("platform", "android"),
            regions=data.get("regions", []),
            registered_at=datetime.fromisoformat(data["registered_at"]) if data.get("registered_at") else datetime.now(),
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else datetime.now()
        )


@dataclass
class ChatMessage:
    """A chat message"""
    id: str
    text: str
    author_ip: str
    timestamp: datetime = field(default_factory=datetime.now)
    nickname: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "text": self.text,
            "author_ip": self.author_ip,
            "timestamp": self.timestamp.isoformat(),
            "nickname": self.nickname
        }


@dataclass
class Comment:
    """A comment on a marker"""
    id: str
    marker_id: str
    text: str
    author_ip: str
    timestamp: datetime = field(default_factory=datetime.now)
    reactions: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "marker_id": self.marker_id,
            "text": self.text,
            "author_ip": self.author_ip,
            "timestamp": self.timestamp.isoformat(),
            "reactions": self.reactions
        }
