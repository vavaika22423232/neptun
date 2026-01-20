"""
Chat moderation service.
"""
import json
import logging
import os
from threading import RLock
from typing import Any, Optional

log = logging.getLogger(__name__)


# Forbidden words for nicknames
FORBIDDEN_NICKNAME_WORDS = [
    'neptun', 'нептун', 'neptune',
    'admin', 'адмін', 'administrator',
    'moderator', 'модератор', 'mod',
    'support', 'підтримка',
    'system', 'система',
]


class ChatModerator:
    """
    Chat moderation service.

    Features:
    - User banning
    - Moderator management
    - Nickname validation
    - Message filtering
    """

    def __init__(
        self,
        banned_file: str = 'chat_banned_users.json',
        moderators_file: str = 'chat_moderators.json',
    ):
        self._banned_file = banned_file
        self._moderators_file = moderators_file
        self._lock = RLock()
        self._banned: dict[str, dict] = {}  # device_id -> ban info
        self._moderators: list[str] = []  # list of device_ids

        self._load()

    def _load(self) -> None:
        """Load banned users and moderators from files."""
        # Load banned
        try:
            if os.path.exists(self._banned_file):
                with open(self._banned_file, encoding='utf-8') as f:
                    self._banned = json.load(f)
        except Exception as e:
            log.error(f"ChatModerator: Failed to load banned users: {e}")
            self._banned = {}

        # Load moderators
        try:
            if os.path.exists(self._moderators_file):
                with open(self._moderators_file, encoding='utf-8') as f:
                    self._moderators = json.load(f)
        except Exception as e:
            log.error(f"ChatModerator: Failed to load moderators: {e}")
            self._moderators = []

    def _save_banned(self) -> None:
        """Save banned users to file."""
        try:
            with open(self._banned_file, 'w', encoding='utf-8') as f:
                json.dump(self._banned, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"ChatModerator: Failed to save banned users: {e}")

    def _save_moderators(self) -> None:
        """Save moderators to file."""
        try:
            with open(self._moderators_file, 'w', encoding='utf-8') as f:
                json.dump(self._moderators, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"ChatModerator: Failed to save moderators: {e}")

    # =========================================================================
    # BANNING
    # =========================================================================

    def is_banned(self, device_id: str) -> bool:
        """Check if device is banned."""
        if not device_id:
            return False
        with self._lock:
            return device_id in self._banned

    def ban_user(
        self,
        device_id: str,
        reason: str = 'Порушення правил чату',
        banned_by: str = '',
        nickname: str = '',
    ) -> bool:
        """
        Ban a user.

        Returns True if banned successfully.
        """
        if not device_id:
            return False

        with self._lock:
            self._banned[device_id] = {
                'reason': reason,
                'banned_by': banned_by,
                'nickname': nickname,
                'timestamp': __import__('time').time(),
            }
            self._save_banned()

        log.info(f"ChatModerator: Banned user {device_id[:20]} ({nickname}): {reason}")
        return True

    def unban_user(self, device_id: str) -> bool:
        """
        Unban a user.

        Returns True if unbanned successfully.
        """
        with self._lock:
            if device_id in self._banned:
                del self._banned[device_id]
                self._save_banned()
                log.info(f"ChatModerator: Unbanned user {device_id[:20]}")
                return True
            return False

    def get_banned_users(self) -> dict[str, dict]:
        """Get all banned users."""
        with self._lock:
            return self._banned.copy()

    # =========================================================================
    # MODERATORS
    # =========================================================================

    def is_moderator(self, device_id: str) -> bool:
        """Check if device is a moderator."""
        if not device_id:
            return False
        with self._lock:
            return device_id in self._moderators

    def add_moderator(self, device_id: str) -> bool:
        """Add a moderator."""
        if not device_id:
            return False

        with self._lock:
            if device_id not in self._moderators:
                self._moderators.append(device_id)
                self._save_moderators()
                log.info(f"ChatModerator: Added moderator {device_id[:20]}")
                return True
            return False

    def remove_moderator(self, device_id: str) -> bool:
        """Remove a moderator."""
        with self._lock:
            if device_id in self._moderators:
                self._moderators.remove(device_id)
                self._save_moderators()
                log.info(f"ChatModerator: Removed moderator {device_id[:20]}")
                return True
            return False

    def get_moderators(self) -> list[str]:
        """Get list of moderator device IDs."""
        with self._lock:
            return self._moderators.copy()

    # =========================================================================
    # NICKNAME VALIDATION
    # =========================================================================

    @staticmethod
    def is_nickname_forbidden(nickname: str) -> bool:
        """Check if nickname contains forbidden words."""
        nickname_lower = nickname.lower()
        for word in FORBIDDEN_NICKNAME_WORDS:
            if word in nickname_lower:
                return True
        return False

    @staticmethod
    def validate_nickname(nickname: str) -> Optional[str]:
        """
        Validate nickname.

        Returns error message or None if valid.
        """
        if not nickname:
            return 'Нікнейм не може бути порожнім'

        if len(nickname) < 3:
            return 'Нікнейм має бути мінімум 3 символи'

        if len(nickname) > 20:
            return 'Нікнейм не може бути довше 20 символів'

        if ChatModerator.is_nickname_forbidden(nickname):
            return 'Цей нікнейм заборонено'

        return None

    # =========================================================================
    # STATS
    # =========================================================================

    def stats(self) -> dict[str, Any]:
        """Return moderation statistics."""
        with self._lock:
            return {
                'banned_users': len(self._banned),
                'moderators': len(self._moderators),
            }
