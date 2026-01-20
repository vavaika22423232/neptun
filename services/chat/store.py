"""
Chat message storage service.
"""
import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from threading import RLock

log = logging.getLogger(__name__)


class ChatStore:
    """
    Thread-safe chat message storage.
    
    Features:
    - File-based persistence
    - Message limiting (max messages)
    - Timestamp filtering
    - Device ID tracking for ownership
    """
    
    def __init__(
        self,
        file_path: str = 'chat_messages.json',
        max_messages: int = 500,
    ):
        self._file_path = file_path
        self._max_messages = max_messages
        self._lock = RLock()
        self._messages: List[Dict] = []
        self._nicknames: Dict[str, str] = {}  # nickname -> device_id
        self._nicknames_file = file_path.replace('.json', '_nicknames.json')
        
        # Load on init
        self._load()
        self._load_nicknames()
    
    def _load(self) -> None:
        """Load messages from file."""
        try:
            if os.path.exists(self._file_path):
                with open(self._file_path, 'r', encoding='utf-8') as f:
                    self._messages = json.load(f)
                log.info(f"ChatStore: Loaded {len(self._messages)} messages from {self._file_path}")
        except Exception as e:
            log.error(f"ChatStore: Failed to load messages: {e}")
            self._messages = []
    
    def _save(self) -> None:
        """Save messages to file."""
        try:
            # Keep only last max_messages
            messages = self._messages[-self._max_messages:]
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"ChatStore: Failed to save messages: {e}")
    
    def _load_nicknames(self) -> None:
        """Load nicknames from file."""
        try:
            if os.path.exists(self._nicknames_file):
                with open(self._nicknames_file, 'r', encoding='utf-8') as f:
                    self._nicknames = json.load(f)
        except Exception as e:
            log.error(f"ChatStore: Failed to load nicknames: {e}")
            self._nicknames = {}
    
    def _save_nicknames(self) -> None:
        """Save nicknames to file."""
        try:
            with open(self._nicknames_file, 'w', encoding='utf-8') as f:
                json.dump(self._nicknames, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"ChatStore: Failed to save nicknames: {e}")
    
    def get_messages(
        self,
        after: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Get messages, optionally filtered by timestamp.
        
        Args:
            after: Only return messages after this timestamp
            limit: Maximum number of messages to return
            
        Returns:
            List of messages (newest last)
        """
        with self._lock:
            messages = self._messages.copy()
        
        # Filter by timestamp
        if after:
            messages = [m for m in messages if m.get('timestamp', 0) > after]
        
        # Return last N messages
        return messages[-limit:]
    
    def add_message(
        self,
        user_id: str,
        message: str,
        device_id: str = '',
        reply_to: Optional[str] = None,
        is_moderator: bool = False,
        timestamp: Optional[float] = None,
    ) -> Dict:
        """
        Add a new message.
        
        Args:
            user_id: User nickname
            message: Message text
            device_id: Device identifier
            reply_to: Optional message ID to reply to
            is_moderator: Whether sender is a moderator
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Created message dict
        """
        now = datetime.now()
        ts = timestamp or now.timestamp()
        
        new_message = {
            'id': str(uuid.uuid4()),
            'userId': user_id,
            'deviceId': device_id,
            'message': message[:1000],  # Limit message length
            'timestamp': ts,
            'time': datetime.fromtimestamp(ts).strftime('%H:%M'),
            'date': datetime.fromtimestamp(ts).strftime('%d.%m.%Y'),
            'isModerator': is_moderator,
        }
        
        # Handle reply
        if reply_to:
            with self._lock:
                original = next((m for m in self._messages if m.get('id') == reply_to), None)
                if original:
                    new_message['replyTo'] = {
                        'id': original.get('id'),
                        'userId': original.get('userId'),
                        'message': original.get('message', '')[:100],
                    }
        
        with self._lock:
            self._messages.append(new_message)
            self._save()
        
        log.info(f"ChatStore: Message from {user_id[:20]}: {message[:50]}...")
        return new_message
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a message by ID."""
        with self._lock:
            before_count = len(self._messages)
            self._messages = [m for m in self._messages if m.get('id') != message_id]
            
            if len(self._messages) < before_count:
                self._save()
                return True
            return False
    
    def get_message(self, message_id: str) -> Optional[Dict]:
        """Get a single message by ID."""
        with self._lock:
            return next((m for m in self._messages if m.get('id') == message_id), None)
    
    # =========================================================================
    # NICKNAMES
    # =========================================================================
    
    def register_nickname(self, nickname: str, device_id: str) -> bool:
        """
        Register a nickname for a device.
        
        Returns True if registered successfully.
        """
        nickname_lower = nickname.lower()
        
        with self._lock:
            # Check if taken by another device
            for existing, owner in self._nicknames.items():
                if existing.lower() == nickname_lower and owner != device_id:
                    return False
            
            # Remove old nickname for this device
            self._nicknames = {k: v for k, v in self._nicknames.items() if v != device_id}
            
            # Register new
            self._nicknames[nickname] = device_id
            self._save_nicknames()
        
        return True
    
    def check_nickname_available(self, nickname: str, device_id: str = '') -> bool:
        """Check if nickname is available."""
        nickname_lower = nickname.lower()
        
        with self._lock:
            for existing, owner in self._nicknames.items():
                if existing.lower() == nickname_lower:
                    return owner == device_id  # Available if same device
            return True
    
    def get_device_for_nickname(self, nickname: str) -> Optional[str]:
        """Get device ID for a nickname."""
        with self._lock:
            return self._nicknames.get(nickname)
    
    def validate_nickname_ownership(self, nickname: str, device_id: str) -> bool:
        """Check if device owns this nickname."""
        with self._lock:
            registered_device = self._nicknames.get(nickname)
            if registered_device and registered_device != device_id:
                return False
            return True
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def stats(self) -> Dict[str, Any]:
        """Return storage statistics."""
        with self._lock:
            return {
                'total_messages': len(self._messages),
                'max_messages': self._max_messages,
                'registered_nicknames': len(self._nicknames),
                'file_path': self._file_path,
            }
