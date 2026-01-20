"""
API blueprints for Flask application.

Модульні blueprints для Flask routes:
- data_bp - /data endpoint для отримання треків
- alarms_bp - /alarms endpoint для статусу тривог
- health_bp - /health endpoints для моніторингу
- admin_bp - /admin endpoints для адміністрування
- tracks_bp - /api/tracks endpoints для треків
- sse_bp - /api/sse endpoints для Server-Sent Events
- chat_bp - /api/chat endpoints для чату
"""
from api.admin import admin_bp
from api.alarms import alarms_bp
from api.chat import chat_bp
from api.data import data_bp
from api.health import health_bp
from api.sse import sse_bp
from api.tracks import tracks_bp

__all__ = [
    'data_bp',
    'health_bp',
    'alarms_bp',
    'admin_bp',
    'tracks_bp',
    'sse_bp',
    'chat_bp',
]
