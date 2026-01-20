"""
Telegram service module.

Модуль для роботи з Telegram каналами:
- MessageParser - парсинг повідомлень на треки/загрози
- TelegramFetcher - отримання повідомлень з каналів
- BackfillManager - завантаження історичних повідомлень
"""
from services.telegram.fetcher import BackfillStatus, FetchedMessage, TelegramFetcher
from services.telegram.parser import MessageParser, ParsedMessage
from services.telegram.patterns import (
    BALLISTIC_PATTERNS,
    COURSE_PATTERNS,
    DRONE_PATTERNS,
    EXPLOSION_PATTERNS,
)

__all__ = [
    'MessageParser',
    'ParsedMessage',
    'TelegramFetcher',
    'FetchedMessage',
    'BackfillStatus',
    'DRONE_PATTERNS',
    'EXPLOSION_PATTERNS',
    'BALLISTIC_PATTERNS',
    'COURSE_PATTERNS',
]
