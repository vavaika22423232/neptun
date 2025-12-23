"""
Neptun Alarm - Telegram Service
Fetches messages from Telegram channels
"""
import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from queue import Queue

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    AuthKeyDuplicatedError,
    FloodWaitError,
    SessionPasswordNeededError
)

from core.config import (
    TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION,
    DEFAULT_CHANNELS, FETCH_INTERVAL
)

log = logging.getLogger(__name__)


class TelegramService:
    """Service for fetching messages from Telegram channels"""
    
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.channels = DEFAULT_CHANNELS.copy()
        self.message_queue: Queue = Queue()
        self.last_fetch: Dict[str, datetime] = {}
        self.on_message: Optional[Callable] = None
        self._authorized = False
        
    @property
    def is_authorized(self) -> bool:
        return self._authorized
    
    def add_channel(self, channel: str):
        """Add channel to monitoring list"""
        if channel not in self.channels:
            self.channels.append(channel)
            log.info(f"Added channel: {channel}")
    
    def remove_channel(self, channel: str):
        """Remove channel from monitoring list"""
        if channel in self.channels:
            self.channels.remove(channel)
            log.info(f"Removed channel: {channel}")
    
    def start(self, on_message: Callable = None):
        """Start Telegram client in background thread"""
        if self.running:
            log.warning("Telegram service already running")
            return
        
        if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
            log.error("Telegram API credentials not configured")
            return
        
        self.on_message = on_message
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        log.info("Telegram service started")
    
    def stop(self):
        """Stop Telegram client"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        log.info("Telegram service stopped")
    
    def _run_loop(self):
        """Background thread event loop"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._main_loop())
        except Exception as e:
            log.error(f"Telegram loop error: {e}")
        finally:
            self.loop.close()
    
    async def _main_loop(self):
        """Main async loop"""
        # Initialize client
        try:
            if TELEGRAM_SESSION:
                self.client = TelegramClient(
                    StringSession(TELEGRAM_SESSION),
                    TELEGRAM_API_ID,
                    TELEGRAM_API_HASH
                )
            else:
                self.client = TelegramClient(
                    'neptun_session',
                    TELEGRAM_API_ID,
                    TELEGRAM_API_HASH
                )
            
            await self.client.connect()
            
            if await self.client.is_user_authorized():
                self._authorized = True
                log.info("Telegram authorized")
            else:
                log.warning("Telegram not authorized - session may be invalid")
                self._authorized = False
                
        except AuthKeyDuplicatedError:
            log.error("Telegram session duplicated - another instance running?")
            return
        except Exception as e:
            log.error(f"Telegram connection error: {e}")
            return
        
        # Fetch loop
        while self.running:
            if self._authorized:
                await self._fetch_messages()
            await asyncio.sleep(FETCH_INTERVAL)
        
        # Cleanup
        if self.client:
            await self.client.disconnect()
    
    async def _fetch_messages(self):
        """Fetch recent messages from all channels"""
        for channel in self.channels:
            try:
                messages = await self._fetch_channel(channel)
                for msg in messages:
                    if self.on_message:
                        self.on_message(msg)
                    else:
                        self.message_queue.put(msg)
            except FloodWaitError as e:
                log.warning(f"Rate limited, waiting {e.seconds}s")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                log.warning(f"Error fetching {channel}: {e}")
    
    async def _fetch_channel(self, channel: str) -> List[Dict]:
        """Fetch messages from a single channel"""
        if not self.client:
            return []
        
        messages = []
        cutoff = datetime.utcnow() - timedelta(hours=6)
        
        try:
            entity = await self.client.get_entity(channel)
            
            async for msg in self.client.iter_messages(entity, limit=50):
                if not msg.text:
                    continue
                
                if msg.date.replace(tzinfo=None) < cutoff:
                    break
                
                messages.append({
                    'id': str(msg.id),
                    'text': msg.text,
                    'channel': channel,
                    'timestamp': msg.date.isoformat(),
                    'date': msg.date
                })
            
            self.last_fetch[channel] = datetime.utcnow()
            
        except Exception as e:
            log.warning(f"Failed to fetch {channel}: {e}")
        
        return messages
    
    async def send_message(self, channel: str, text: str) -> bool:
        """Send message to channel (if bot)"""
        if not self.client or not self._authorized:
            return False
        
        try:
            entity = await self.client.get_entity(channel)
            await self.client.send_message(entity, text)
            return True
        except Exception as e:
            log.error(f"Failed to send message: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Get service status"""
        return {
            'running': self.running,
            'authorized': self._authorized,
            'channels': self.channels,
            'last_fetch': {
                k: v.isoformat() for k, v in self.last_fetch.items()
            }
        }


# Global instance
telegram_service = TelegramService()
