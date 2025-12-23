"""
Neptun Alarm - Storage Service
JSON file and SQLite database storage
"""
import json
import sqlite3
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from core.config import (
    MESSAGES_FILE, CHAT_MESSAGES_FILE, DEVICES_FILE,
    VISITS_DB, ALARMS_DB, MAX_MESSAGES
)
from core.utils.helpers import get_kyiv_time

log = logging.getLogger(__name__)

# Thread locks for file access
_file_locks: Dict[str, threading.Lock] = {}


def _get_lock(filename: str) -> threading.Lock:
    """Get or create lock for file"""
    if filename not in _file_locks:
        _file_locks[filename] = threading.Lock()
    return _file_locks[filename]


class JSONStore:
    """Thread-safe JSON file storage"""
    
    def __init__(self, filename: str, default: Any = None):
        self.filename = filename
        self.path = Path(filename)
        self.default = default if default is not None else {}
        self.lock = _get_lock(filename)
        self._cache: Optional[Any] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 5  # seconds
    
    def load(self, use_cache: bool = True) -> Any:
        """Load data from file"""
        with self.lock:
            # Check cache
            if use_cache and self._cache is not None:
                if self._cache_time and (datetime.now() - self._cache_time).seconds < self._cache_ttl:
                    return self._cache
            
            try:
                if self.path.exists():
                    data = json.loads(self.path.read_text(encoding='utf-8'))
                    self._cache = data
                    self._cache_time = datetime.now()
                    return data
            except Exception as e:
                log.warning(f"Error loading {self.filename}: {e}")
            
            return self.default.copy() if isinstance(self.default, (dict, list)) else self.default
    
    def save(self, data: Any):
        """Save data to file"""
        with self.lock:
            try:
                self.path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                self._cache = data
                self._cache_time = datetime.now()
            except Exception as e:
                log.error(f"Error saving {self.filename}: {e}")
    
    def update(self, key: str, value: Any):
        """Update single key in dict store"""
        data = self.load()
        if isinstance(data, dict):
            data[key] = value
            self.save(data)
    
    def append(self, item: Any, max_items: int = None):
        """Append item to list store"""
        data = self.load()
        if isinstance(data, list):
            data.append(item)
            if max_items and len(data) > max_items:
                data = data[-max_items:]
            self.save(data)
    
    def clear_cache(self):
        """Clear in-memory cache"""
        self._cache = None
        self._cache_time = None


class MessageStore:
    """Storage for threat messages/markers"""
    
    def __init__(self):
        self.store = JSONStore(MESSAGES_FILE, default={'messages': [], 'tracks': []})
    
    def get_messages(self) -> List[Dict]:
        """Get all messages"""
        data = self.store.load()
        # Handle both old format (list) and new format (dict)
        if isinstance(data, list):
            return data
        return data.get('messages', [])
    
    def get_tracks(self) -> List[Dict]:
        """Get all tracks"""
        data = self.store.load()
        # Handle both old format (list) and new format (dict)
        if isinstance(data, list):
            return []
        return data.get('tracks', [])
    
    def add_message(self, message: Dict):
        """Add new message"""
        data = self.store.load()
        # Handle both old format (list) and new format (dict)
        if isinstance(data, list):
            messages = data
        else:
            messages = data.get('messages', [])
        
        # Check for duplicate
        for existing in messages:
            if existing.get('id') == message.get('id'):
                return False
        
        messages.insert(0, message)
        
        # Prune old messages
        if len(messages) > MAX_MESSAGES:
            messages = messages[:MAX_MESSAGES]
        
        data['messages'] = messages
        self.store.save(data)
        return True
    
    def add_track(self, track: Dict):
        """Add or update track"""
        data = self.store.load()
        tracks = data.get('tracks', [])
        
        # Check for existing track to merge
        for i, existing in enumerate(tracks):
            if self._should_merge(existing, track):
                tracks[i] = self._merge_tracks(existing, track)
                data['tracks'] = tracks
                self.store.save(data)
                return
        
        tracks.insert(0, track)
        data['tracks'] = tracks
        self.store.save(data)
    
    def _should_merge(self, existing: Dict, new: Dict) -> bool:
        """Check if tracks should be merged"""
        # Same type and close location
        if existing.get('type') != new.get('type'):
            return False
        
        if existing.get('location', '').lower() == new.get('location', '').lower():
            return True
        
        return False
    
    def _merge_tracks(self, existing: Dict, new: Dict) -> Dict:
        """Merge two track records"""
        existing['timestamp'] = new.get('timestamp', existing.get('timestamp'))
        existing['last_seen'] = get_kyiv_time().isoformat()
        
        # Update coordinates if new ones provided
        if new.get('lat') and new.get('lng'):
            existing['lat'] = new['lat']
            existing['lng'] = new['lng']
        
        # Update direction
        if new.get('direction'):
            existing['direction'] = new['direction']
        
        return existing
    
    def hide_message(self, message_id: str):
        """Mark message as hidden"""
        data = self.store.load()
        for msg in data.get('messages', []):
            if msg.get('id') == message_id:
                msg['hidden'] = True
                break
        self.store.save(data)
    
    def unhide_message(self, message_id: str):
        """Remove hidden flag"""
        data = self.store.load()
        for msg in data.get('messages', []):
            if msg.get('id') == message_id:
                msg['hidden'] = False
                break
        self.store.save(data)
    
    def prune_old(self, hours: int = 6):
        """Remove messages older than N hours"""
        data = self.store.load()
        cutoff = (get_kyiv_time() - timedelta(hours=hours)).isoformat()
        
        data['messages'] = [
            m for m in data.get('messages', [])
            if m.get('timestamp', '') > cutoff
        ]
        data['tracks'] = [
            t for t in data.get('tracks', [])
            if t.get('timestamp', '') > cutoff
        ]
        
        self.store.save(data)


class DeviceStore:
    """Storage for registered devices"""
    
    def __init__(self):
        self.store = JSONStore(DEVICES_FILE, default=[])
    
    def get_all(self) -> List[Dict]:
        """Get all devices"""
        return self.store.load()
    
    def get_by_id(self, device_id: str) -> Optional[Dict]:
        """Get device by ID"""
        for device in self.get_all():
            if device.get('device_id') == device_id:
                return device
        return None
    
    def register(self, device_id: str, fcm_token: str, platform: str = 'android', regions: List[str] = None):
        """Register or update device"""
        devices = self.get_all()
        now = get_kyiv_time().isoformat()
        
        # Find existing
        for device in devices:
            if device.get('device_id') == device_id:
                device['fcm_token'] = fcm_token
                device['platform'] = platform
                device['regions'] = regions or []
                device['last_seen'] = now
                self.store.save(devices)
                return device
        
        # New device
        device = {
            'device_id': device_id,
            'fcm_token': fcm_token,
            'platform': platform,
            'regions': regions or [],
            'registered_at': now,
            'last_seen': now
        }
        devices.append(device)
        self.store.save(devices)
        return device
    
    def update_regions(self, device_id: str, regions: List[str]):
        """Update device regions"""
        devices = self.get_all()
        for device in devices:
            if device.get('device_id') == device_id:
                device['regions'] = regions
                device['last_seen'] = get_kyiv_time().isoformat()
                self.store.save(devices)
                return True
        return False
    
    def remove(self, device_id: str):
        """Remove device by ID"""
        devices = self.get_all()
        devices = [d for d in devices if d.get('device_id') != device_id]
        self.store.save(devices)
    
    def remove_by_token(self, fcm_token: str):
        """Remove device by FCM token"""
        devices = self.get_all()
        devices = [d for d in devices if d.get('fcm_token') != fcm_token]
        self.store.save(devices)
    
    def get_for_region(self, region: str) -> List[Dict]:
        """Get devices subscribed to a region"""
        from core.data.regions import match_region
        return [
            d for d in self.get_all()
            if not d.get('regions') or match_region(region, d.get('regions', []))
        ]


class ChatStore:
    """Storage for chat messages"""
    
    def __init__(self):
        self.store = JSONStore(CHAT_MESSAGES_FILE, default=[])
    
    def get_messages(self, limit: int = 100) -> List[Dict]:
        """Get recent chat messages"""
        messages = self.store.load()
        return messages[-limit:] if len(messages) > limit else messages
    
    def add_message(self, text: str, author_ip: str, nickname: str = None) -> Dict:
        """Add new chat message"""
        from core.utils.helpers import generate_id
        
        message = {
            'id': generate_id(text),
            'text': text,
            'author_ip': author_ip,
            'nickname': nickname,
            'timestamp': get_kyiv_time().isoformat()
        }
        
        messages = self.store.load()
        messages.append(message)
        
        # Keep last 500 messages
        if len(messages) > 500:
            messages = messages[-500:]
        
        self.store.save(messages)
        return message


class SQLiteDB:
    """SQLite database wrapper"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = _get_lock(db_path)
    
    @contextmanager
    def connection(self):
        """Get database connection"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    
    def execute(self, sql: str, params: tuple = ()):
        """Execute SQL statement"""
        with self.connection() as conn:
            conn.execute(sql, params)
    
    def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute query and return results"""
        with self.connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        """Execute query and return single result"""
        results = self.query(sql, params)
        return results[0] if results else None


class VisitsDB(SQLiteDB):
    """Database for visitor tracking"""
    
    def __init__(self):
        super().__init__(VISITS_DB)
        self._init_tables()
    
    def _init_tables(self):
        """Create tables if not exist"""
        self.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id TEXT PRIMARY KEY,
                ip TEXT,
                first_seen REAL,
                last_seen REAL
            )
        """)
        self.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                marker_id TEXT,
                text TEXT,
                author_ip TEXT,
                timestamp REAL
            )
        """)
        self.execute("""
            CREATE TABLE IF NOT EXISTS comment_reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comment_id TEXT,
                emoji TEXT,
                user_ip TEXT,
                timestamp REAL
            )
        """)
    
    def record_visit(self, visitor_id: str, ip: str = None):
        """Record visitor"""
        now = datetime.now().timestamp()
        self.execute(
            "INSERT OR IGNORE INTO visits (id, ip, first_seen, last_seen) VALUES (?, ?, ?, ?)",
            (visitor_id, ip, now, now)
        )
        self.execute(
            "UPDATE visits SET last_seen = ?, ip = ? WHERE id = ?",
            (now, ip, visitor_id)
        )
    
    def get_visitor_count(self, hours: int = 24) -> int:
        """Get unique visitors in time period"""
        cutoff = (datetime.now() - timedelta(hours=hours)).timestamp()
        result = self.query_one(
            "SELECT COUNT(DISTINCT id) as count FROM visits WHERE last_seen > ?",
            (cutoff,)
        )
        return result['count'] if result else 0
    
    def get_active_sessions(self, minutes: int = 5) -> List[Dict]:
        """Get currently active sessions"""
        cutoff = (datetime.now() - timedelta(minutes=minutes)).timestamp()
        return self.query(
            "SELECT * FROM visits WHERE last_seen > ? ORDER BY last_seen DESC",
            (cutoff,)
        )


class AlarmsDB(SQLiteDB):
    """Database for alarm tracking"""
    
    def __init__(self):
        super().__init__(ALARMS_DB)
        self._init_tables()
    
    def _init_tables(self):
        """Create tables if not exist"""
        self.execute("""
            CREATE TABLE IF NOT EXISTS active_alarms (
                level TEXT,
                name TEXT,
                since REAL,
                last_update REAL,
                PRIMARY KEY (level, name)
            )
        """)
        self.execute("""
            CREATE TABLE IF NOT EXISTS alarm_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                name TEXT,
                event TEXT,
                timestamp REAL
            )
        """)
    
    def set_alarm(self, level: str, name: str):
        """Set/update alarm"""
        now = datetime.now().timestamp()
        self.execute("""
            INSERT INTO active_alarms (level, name, since, last_update)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(level, name) DO UPDATE SET last_update = ?
        """, (level, name, now, now, now))
        self.execute(
            "INSERT INTO alarm_events (level, name, event, timestamp) VALUES (?, ?, ?, ?)",
            (level, name, 'activated', now)
        )
    
    def clear_alarm(self, level: str, name: str):
        """Clear alarm"""
        now = datetime.now().timestamp()
        self.execute(
            "DELETE FROM active_alarms WHERE level = ? AND name = ?",
            (level, name)
        )
        self.execute(
            "INSERT INTO alarm_events (level, name, event, timestamp) VALUES (?, ?, ?, ?)",
            (level, name, 'deactivated', now)
        )
    
    def get_active(self, ttl_hours: int = 2) -> List[Dict]:
        """Get active alarms"""
        cutoff = (datetime.now() - timedelta(hours=ttl_hours)).timestamp()
        return self.query(
            "SELECT * FROM active_alarms WHERE last_update > ?",
            (cutoff,)
        )
    
    def prune_old(self, hours: int = 2):
        """Remove stale alarms"""
        cutoff = (datetime.now() - timedelta(hours=hours)).timestamp()
        self.execute("DELETE FROM active_alarms WHERE last_update < ?", (cutoff,))


# Global instances
message_store = MessageStore()
device_store = DeviceStore()
chat_store = ChatStore()
visits_db = VisitsDB()
alarms_db = AlarmsDB()
