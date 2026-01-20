"""
Centralized application configuration.

Всі налаштування в одному місці. Завантажує з .env файлу
та змінних оточення. Імутабельний після ініціалізації.
"""
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger(__name__)


def _load_dotenv(path: str = '.env') -> None:
    """Load environment from .env file."""
    if not os.path.exists(path):
        return

    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue

                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                # Don't override existing env vars
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        log.warning(f"Failed to load .env: {e}")


# Load .env before creating config
_load_dotenv()


def _env_bool(key: str, default: bool = False) -> bool:
    """Get boolean from environment."""
    val = os.getenv(key, '').lower()
    if val in ('true', '1', 'yes', 'on'):
        return True
    if val in ('false', '0', 'no', 'off'):
        return False
    return default


def _env_int(key: str, default: int) -> int:
    """Get integer from environment."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    """Get float from environment."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_list(key: str, default: list[str], sep: str = ',') -> list[str]:
    """Get list from environment (comma-separated)."""
    val = os.getenv(key, '')
    if not val:
        return default
    return [x.strip() for x in val.split(sep) if x.strip()]


@dataclass(frozen=True)
class TelegramConfig:
    """Telegram API configuration."""
    api_id: Optional[int] = field(
        default_factory=lambda: _env_int('TELEGRAM_API_ID', 0) or _env_int('API_ID', 0) or None
    )
    api_hash: Optional[str] = field(
        default_factory=lambda: os.getenv('TELEGRAM_API_HASH') or os.getenv('API_HASH')
    )
    session_string: Optional[str] = field(
        default_factory=lambda: os.getenv('TELEGRAM_SESSION')
    )
    bot_token: Optional[str] = field(
        default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN')
    )

    # Channels to monitor
    channels: list[str] = field(
        default_factory=lambda: _env_list('TELEGRAM_CHANNELS', ['mapstransler'])
    )

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.api_id and self.api_hash)

    @property
    def has_session(self) -> bool:
        """Check if session string is available."""
        return bool(self.session_string)


@dataclass(frozen=True)
class GeocodingConfig:
    """Geocoding configuration."""
    # OpenCage
    opencage_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv('OPENCAGE_API_KEY')
    )

    # Google Maps
    google_maps_key: Optional[str] = field(
        default_factory=lambda: os.getenv('GOOGLE_MAPS_KEY') or os.getenv('GOOGLE_MAPS_API_KEY')
    )

    # Nominatim
    nominatim_enabled: bool = field(
        default_factory=lambda: _env_bool('NOMINATIM_ENABLED', False)
    )
    nominatim_url: str = field(
        default_factory=lambda: os.getenv('NOMINATIM_URL', 'https://nominatim.openstreetmap.org/search')
    )
    nominatim_timeout: float = field(
        default_factory=lambda: _env_float('NOMINATIM_TIMEOUT', 5.0)
    )

    # Photon
    photon_enabled: bool = field(
        default_factory=lambda: _env_bool('PHOTON_ENABLED', True)
    )
    photon_url: str = field(
        default_factory=lambda: os.getenv('PHOTON_URL', 'https://photon.komoot.io/api/')
    )
    photon_timeout: float = field(
        default_factory=lambda: _env_float('PHOTON_TIMEOUT', 5.0)
    )

    # Cache settings
    cache_positive_ttl: int = field(
        default_factory=lambda: _env_int('GEOCODE_CACHE_TTL', 86400 * 30)  # 30 days
    )
    cache_negative_ttl: int = field(
        default_factory=lambda: _env_int('GEOCODE_NEGATIVE_TTL', 86400 * 3)  # 3 days
    )

    # Memory optimization
    memory_optimized: bool = field(
        default_factory=lambda: _env_bool('MEMORY_OPTIMIZED', False)
    )


@dataclass(frozen=True)
class StorageConfig:
    """Storage paths configuration."""
    # Persistent data directory (e.g., /data on Render)
    persistent_dir: str = field(
        default_factory=lambda: os.getenv('PERSISTENT_DATA_DIR', '/data')
    )

    @property
    def is_persistent_available(self) -> bool:
        """Check if persistent storage is available."""
        return os.path.isdir(self.persistent_dir)

    def get_path(self, filename: str) -> str:
        """Get full path for a file, using persistent dir if available."""
        if self.is_persistent_available:
            return os.path.join(self.persistent_dir, filename)
        return filename

    @property
    def messages_file(self) -> str:
        return self.get_path('messages.json')

    @property
    def chat_messages_file(self) -> str:
        return self.get_path('chat_messages.json')

    @property
    def hidden_markers_file(self) -> str:
        return self.get_path('hidden_markers.json')

    @property
    def stats_file(self) -> str:
        return self.get_path('visits_stats.json')

    @property
    def geocode_cache_file(self) -> str:
        return 'geocode_cache.json'  # Always local (can be regenerated)

    @property
    def negative_cache_file(self) -> str:
        return 'negative_geocode_cache.json'


@dataclass(frozen=True)
class MessageConfig:
    """Message handling configuration."""
    # Retention
    retention_minutes: int = field(
        default_factory=lambda: _env_int('MESSAGES_RETENTION_MINUTES', 1440)  # 24h
    )
    max_count: int = field(
        default_factory=lambda: _env_int('MESSAGES_MAX_COUNT', 500)
    )

    # Backfill
    backfill_enabled: bool = field(
        default_factory=lambda: _env_bool('BACKFILL_ENABLED', True)
    )
    backfill_limit: int = field(
        default_factory=lambda: _env_int('BACKFILL_LIMIT', 100)
    )
    backfill_geocode: bool = field(
        default_factory=lambda: _env_bool('BACKFILL_GEOCODE', False)
    )


@dataclass(frozen=True)
class AlarmConfig:
    """Alarm API configuration."""
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv('ALARM_API_KEY') or os.getenv('UKRAINEALARM_API_KEY')
    )
    api_url: str = field(
        default_factory=lambda: os.getenv('ALARM_API_URL', 'https://api.ukrainealarm.com/api/v3')
    )

    # Polling
    poll_interval: int = field(
        default_factory=lambda: _env_int('ALARM_POLL_INTERVAL', 30)  # seconds
    )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


@dataclass(frozen=True)
class FirebaseConfig:
    """Firebase push notifications configuration."""
    credentials_base64: Optional[str] = field(
        default_factory=lambda: os.getenv('FIREBASE_CREDENTIALS_BASE64')
    )
    credentials_file: Optional[str] = field(
        default_factory=lambda: os.getenv('FIREBASE_CREDENTIALS_FILE')
    )

    @property
    def is_configured(self) -> bool:
        return bool(self.credentials_base64 or self.credentials_file)


@dataclass(frozen=True)
class ServerConfig:
    """Server configuration."""
    host: str = field(
        default_factory=lambda: os.getenv('HOST', '0.0.0.0')
    )
    port: int = field(
        default_factory=lambda: _env_int('PORT', 10000)
    )
    debug: bool = field(
        default_factory=lambda: _env_bool('FLASK_DEBUG', False)
    )

    # Rate limiting
    rate_limit_enabled: bool = field(
        default_factory=lambda: _env_bool('RATE_LIMIT_ENABLED', True)
    )
    rate_limit_per_minute: int = field(
        default_factory=lambda: _env_int('RATE_LIMIT_PER_MINUTE', 60)
    )

    # CORS
    cors_origins: list[str] = field(
        default_factory=lambda: _env_list('CORS_ORIGINS', ['*'])
    )


@dataclass(frozen=True)
class Config:
    """Main application configuration."""
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    geocoding: GeocodingConfig = field(default_factory=GeocodingConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    messages: MessageConfig = field(default_factory=MessageConfig)
    alarms: AlarmConfig = field(default_factory=AlarmConfig)
    firebase: FirebaseConfig = field(default_factory=FirebaseConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for debugging, hides secrets)."""
        return {
            'telegram': {
                'api_id': bool(self.telegram.api_id),
                'api_hash': bool(self.telegram.api_hash),
                'session': bool(self.telegram.session_string),
                'channels': self.telegram.channels,
            },
            'geocoding': {
                'opencage': bool(self.geocoding.opencage_api_key),
                'google': bool(self.geocoding.google_maps_key),
                'nominatim_enabled': self.geocoding.nominatim_enabled,
                'photon_enabled': self.geocoding.photon_enabled,
                'memory_optimized': self.geocoding.memory_optimized,
            },
            'storage': {
                'persistent_dir': self.storage.persistent_dir,
                'persistent_available': self.storage.is_persistent_available,
            },
            'messages': {
                'retention_minutes': self.messages.retention_minutes,
                'max_count': self.messages.max_count,
                'backfill_enabled': self.messages.backfill_enabled,
                'backfill_limit': self.messages.backfill_limit,
            },
            'alarms': {
                'configured': self.alarms.is_configured,
                'poll_interval': self.alarms.poll_interval,
            },
            'firebase': {
                'configured': self.firebase.is_configured,
            },
            'server': {
                'host': self.server.host,
                'port': self.server.port,
                'debug': self.server.debug,
            },
        }


# Global singleton config
_config: Optional[Config] = None


def get_config() -> Config:
    """Get application configuration singleton."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Force reload configuration (for testing)."""
    global _config
    _config = Config()
    return _config
