# Routes module - Flask blueprints for modular route organization
# This module splits the large app.py into logical components
#
# Structure:
#   routes/
#   ├── __init__.py      - This file, exports all blueprints
#   ├── config.py        - Shared configuration and utilities
#   ├── alarms.py        - UkraineAlarm API proxy, alarm monitoring
#   ├── payments.py      - WayForPay, Monobank integration  
#   ├── blackout.py      - Power outage schedules (YASNO)
#   ├── chat.py          - Anonymous chat functionality
#   ├── family.py        - Family safety SOS system
#   ├── admin.py         - Admin panel and management
#   ├── pages.py         - Static pages, SEO routes
#   ├── devices.py       - Device registration, FCM tokens
#   ├── geocoding.py     - Ukrainian settlement geocoding (Photon, Nominatim, Groq AI)
#   ├── messages.py      - Message storage, loading, deduplication
#   ├── analytics.py     - Visit tracking, statistics
#   ├── telegram.py      - Telegram FCM notifications for threats
#   ├── comments.py      - Anonymous comments with reactions
#   └── stream.py        - SSE real-time updates

from flask import Blueprint

# Import all blueprints
from .alarms import alarms_bp, start_alarm_monitoring, init_firebase_messaging
from .payments import payments_bp
from .blackout import blackout_bp
from .chat import chat_bp
from .family import family_bp, init_family_store
from .admin import admin_bp
from .pages import pages_bp
from .devices import devices_bp, init_device_store

# New modules
from .geocoding import (
    geocoding_bp,
    ensure_city_coords,
    ensure_city_coords_with_message_context,
    geocode_with_context,
    geocode_with_photon,
    geocode_with_nominatim,
    validate_ukraine_coords,
    normalize_ukrainian_toponym,
    get_kyiv_directional_coordinates,
    extract_location_with_groq_ai,
    UA_CITIES,
    UA_CITY_NORMALIZE,
    OBLAST_CENTERS,
    CITY_COORDS,
)
from .messages import (
    messages_bp,
    load_messages,
    save_messages,
    _prune_messages,
    maybe_merge_track,
    load_hidden,
    save_hidden,
    load_blocked,
    save_blocked,
    _should_send_notification,
)
from .analytics import (
    analytics_bp,
    init_visits_db,
    record_visit_sql,
    sql_unique_counts,
    _load_visit_stats,
    _save_visit_stats,
    _update_recent_visits,
    _load_recent_visits,
    _save_recent_visits,
    _seed_recent_from_sql,
)
from .telegram import (
    telegram_bp,
    send_telegram_threat_notification,
    is_region_telegram_notified,
    update_ballistic_state,
    get_ballistic_state,
    load_dynamic_channels,
    save_dynamic_channels,
    init_firebase_messaging as init_telegram_firebase,
)
from .comments import (
    comments_bp,
    init_comments_db,
    save_comment_record,
    load_recent_comments,
    load_comment_reactions,
    toggle_comment_reaction,
    preload_comments,
    COMMENTS,
)
from .stream import (
    stream_bp,
    broadcast_new,
    broadcast_control,
    broadcast_alarm,
    broadcast_message,
    broadcast_presence,
    get_subscriber_count,
    SUBSCRIBERS,
)

__all__ = [
    # Blueprints
    'alarms_bp',
    'payments_bp', 
    'blackout_bp',
    'chat_bp',
    'family_bp',
    'admin_bp',
    'pages_bp',
    'devices_bp',
    'geocoding_bp',
    'messages_bp',
    'analytics_bp',
    'telegram_bp',
    'comments_bp',
    'stream_bp',
    # Initialization functions
    'start_alarm_monitoring',
    'init_firebase_messaging',
    'init_family_store',
    'init_device_store',
    'init_visits_db',
    'init_comments_db',
    'init_telegram_firebase',
    'preload_comments',
    # Geocoding
    'ensure_city_coords',
    'ensure_city_coords_with_message_context',
    'geocode_with_context',
    'geocode_with_photon',
    'geocode_with_nominatim',
    'validate_ukraine_coords',
    'normalize_ukrainian_toponym',
    'get_kyiv_directional_coordinates',
    'extract_location_with_groq_ai',
    'UA_CITIES',
    'UA_CITY_NORMALIZE',
    'OBLAST_CENTERS',
    'CITY_COORDS',
    # Messages
    'load_messages',
    'save_messages',
    '_prune_messages',
    'maybe_merge_track',
    'load_hidden',
    'save_hidden',
    'load_blocked',
    'save_blocked',
    '_should_send_notification',
    # Analytics
    'record_visit_sql',
    'sql_unique_counts',
    '_load_visit_stats',
    '_save_visit_stats',
    '_update_recent_visits',
    '_load_recent_visits',
    '_save_recent_visits',
    '_seed_recent_from_sql',
    # Telegram
    'send_telegram_threat_notification',
    'is_region_telegram_notified',
    'update_ballistic_state',
    'get_ballistic_state',
    'load_dynamic_channels',
    'save_dynamic_channels',
    # Comments
    'save_comment_record',
    'load_recent_comments',
    'load_comment_reactions',
    'toggle_comment_reaction',
    'COMMENTS',
    # Stream
    'broadcast_new',
    'broadcast_control',
    'broadcast_alarm',
    'broadcast_message',
    'broadcast_presence',
    'get_subscriber_count',
    'SUBSCRIBERS',
]
